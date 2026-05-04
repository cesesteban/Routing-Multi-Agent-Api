import json
import time
import os
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langfuse.langchain import CallbackHandler
from langfuse import Langfuse
from src.services.ai.rag_service import RAGManager
from src.core.config import Config
from src.core.utils import get_metrics, calculate_cost
from src.core.constants import AGENT_ROLES, VALID_DEPARTMENTS

# Intentar importar proveedores opcionales
try:
    from langchain_groq import ChatGroq
except ImportError:
    ChatGroq = None

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None

try:
    from langchain_google_vertexai import ChatVertexAI
except ImportError:
    ChatVertexAI = None

# 2. Modelos de Datos (Pydantic)
class RouterResponse(BaseModel):
    """Modelo para la respuesta del coordinador de ruteo."""
    chain_of_thought: List[str] = Field(description="4 pasos de razonamiento (Señales, Estrategia, Riesgos, Clasificación)")
    intent: str = Field(description="Categoría destino (RRHH, TECNOLOGIA, FINANZAS, RECLAMOS, GENERAL)")
    confidence: float = Field(description="Nivel de certidumbre en la clasificación (0.0-1.0)")
    reason: str = Field(description="Justificación breve del destino elegido")

class SpecialistResponse(BaseModel):
    """Modelo para la respuesta detallada de los especialistas."""
    chain_of_thought: List[str] = Field(description="4 pasos de razonamiento (Análisis, Estrategia, Riesgos, Solución)")
    response_text: str = Field(description="Respuesta directa al usuario")
    next_steps: List[str] = Field(description="Tareas o seguimiento recomendado")
    priority: str = Field(description="Nivel de urgencia detectado (BAJA, MEDIA, ALTA, CRÍTICA)")
    requires_supervisor: bool = Field(description="Define si el caso debe ser escalado a un humano de inmediato")
    avoid: List[str] = Field(description="Lo que se decidió NO decir o evitar en esta respuesta")
    tone_notes: List[str] = Field(description="Notas sobre el tono aplicado (ej. empático, formal)")
    why_it_works: List[str] = Field(description="Justificación técnica de por qué esta respuesta es efectiva para el usuario")

class CriticResponse(BaseModel):
    """Modelo para la auditoría técnica de las respuestas."""
    is_valid: bool = Field(description="Define si la respuesta cumple con los estándares de calidad")
    issues: List[str] = Field(description="Problemas detectados (ambigüedad, tono incorrecto, falta de datos)")
    suggestions: str = Field(description="Sugerencias de mejora para el especialista")
    score: float = Field(description="Calificación de calidad (0.0-1.0)")

class EvaluatorResponse(BaseModel):
    """Modelo para la evaluación automática de RAG en Langfuse."""
    accuracy_score: int = Field(description="Puntaje de precisión del 1 al 10")
    relevance_score: int = Field(description="Puntaje de relevancia del 1 al 10")
    groundedness_score: int = Field(description="Puntaje de fundamentación del 1 al 10")
    final_score: float = Field(description="Puntaje final promedio del 1 al 10")
    justification: str = Field(description="Justificación detallada del puntaje asignado")



# 4. Factory de LLM
def get_llm(model_name: str = None, base_url: str = None):
    provider = Config.LLM_PROVIDER
    model = model_name or Config.MODEL_NAME
    
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        return ChatOpenAI(api_key=api_key, model_name=model, temperature=0).with_fallbacks([
            ChatOpenAI(api_key=api_key, model_name="gpt-4o-mini", temperature=0)
        ])
    elif provider == "groq":
        if not ChatGroq:
            raise ImportError("Error: 'langchain-groq' no está instalado.")
        return ChatGroq(api_key=Config.GROQ_API_KEY, model_name=model, temperature=0)
    elif provider == "gemini":
        if not ChatGoogleGenerativeAI:
            raise ImportError("Error: 'langchain-google-genai' no está instalado.")
        return ChatGoogleGenerativeAI(google_api_key=Config.GOOGLE_API_KEY, model=model, temperature=0)
    elif provider == "vertexai":
        if not ChatVertexAI:
            raise ImportError("Error: 'langchain-google-vertexai' no está instalado.")
        return ChatVertexAI(
            project=Config.GOOGLE_CLOUD_PROJECT,
            location=Config.GOOGLE_CLOUD_REGION,
            model_name=model,
            temperature=0
        )
    elif provider == "lm_studio":
        return ChatOpenAI(
            base_url=base_url or Config.LM_STUDIO_BASE_URL,
            api_key="lm-studio",
            model_name=model,
            temperature=0
        )
    else:
        raise ValueError(f"Proveedor LLM no soportado: {provider}")

# 5. Sistema Multi-Agente
class MultiAgentSystem:
    def __init__(self):
        Config.validate()
        
        # Inicialización de modelos (Jerarquizada)
        self.nano_llm = get_llm(Config.MODEL_NANO, Config.LM_STUDIO_NANO_URL)
        self.powerful_llm = get_llm(Config.MODEL_POWERFUL, Config.LM_STUDIO_POWERFUL_URL)
        
        # Mantener raw_llm por compatibilidad (apunta al potente)
        self.raw_llm = self.powerful_llm 
        
        self.rag = RAGManager()
        
        # Inicialización de Langfuse
        self.langfuse_handler = None
        self.langfuse_client = None
        if Config.LANGFUSE_PUBLIC_KEY and Config.LANGFUSE_SECRET_KEY:
            # El handler lee automáticamente de las variables de entorno
            self.langfuse_handler = CallbackHandler()
            self.langfuse_client = Langfuse(
                public_key=Config.LANGFUSE_PUBLIC_KEY,
                secret_key=Config.LANGFUSE_SECRET_KEY,
                host=Config.LANGFUSE_HOST
            )
        
        # Inicialización con Salida Estructurada Jerarquizada
        self.router_llm = self.nano_llm.with_structured_output(RouterResponse)
        self.specialist_llm = self.powerful_llm.with_structured_output(SpecialistResponse)
        self.critic_llm = self.powerful_llm.with_structured_output(CriticResponse)
        self.evaluator_llm = self.powerful_llm.with_structured_output(EvaluatorResponse)

    def _get_langfuse_config(self, trace_id: Optional[str] = None) -> dict:
        """Construye el config de callbacks de LangChain.
        
        Si se provee trace_id, crea un handler vinculado a esa traza raíz
        para que todos los spans aparezcan anidados bajo el mismo trace en Langfuse.
        Si no hay trace_id, usa el handler global (crea una traza nueva por invocación).
        """
        if not self.langfuse_handler:
            return {}
        if trace_id:
            # Handler con trace_id explícito → span hijo de la traza raíz
            return {"callbacks": [CallbackHandler(trace_id=trace_id)]}
        # Handler global → genera su propia traza
        return {"callbacks": [self.langfuse_handler]}

    def route_query(self, query: str, lang: str = "es", trace_id: Optional[str] = None) -> Dict[str, Any]:
        """Clasifica la intención del usuario utilizando el prompt del coordinador."""
        with open("prompts/router_prompt.md", "r", encoding="utf-8") as f:
            template_text = f.read()
            
        prompt = ChatPromptTemplate.from_template(template_text)
        chain = prompt | self.router_llm
        
        start_time = time.time()
        
        config = self._get_langfuse_config(trace_id)
        content = chain.invoke({"query": query, "language": "Spanish" if lang == "es" else "English"}, config=config)
        
        metrics = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "tokens_prompt": len(query) // 4,
            "tokens_completion": 50,
            "total_tokens": (len(query) // 4) + 50,
            "latency_ms": round((time.time() - start_time) * 1000, 2),
            "estimated_cost_usd": 0.001 
        }
        
        return {"data": content, "metrics": metrics}

    def handle_specialist(self, query: str, routing: RouterResponse, feedback: str = "", lang: str = "es", trace_id: Optional[str] = None) -> Dict[str, Any]:
        """Deriva la consulta al especialista adecuado según la intención detectada."""
        config_role = AGENT_ROLES.get(routing.intent, AGENT_ROLES["GENERAL"])
        
        # Recuperación RAG (Habilitado para todas las categorías)
        context = ""
        if routing.intent in VALID_DEPARTMENTS:
            print(f"  [RAG] Recuperando contexto para {routing.intent}...")
            context = self.rag.retrieve_context(query, routing.intent)
        
        with open("prompts/specialist_prompt.md", "r", encoding="utf-8") as f:
            template_text = f.read()
            
        prompt = ChatPromptTemplate.from_template(template_text)
        chain = prompt | self.specialist_llm
        
        start_time = time.time()
        llm_config = self._get_langfuse_config(trace_id)
        
        content = chain.invoke({
            "role_description": config_role["role"],
            "tone": config_role["tone"],
            "query": query,
            "intent": routing.intent,
            "reason": routing.reason,
            "context": context if context else "No se encontró información específica en la base de datos.",
            "feedback": feedback,
            "language": "Spanish" if lang == "es" else "English"
        }, config=llm_config)
        
        metrics = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "tokens_prompt": len(query) // 4,
            "tokens_completion": 100,
            "total_tokens": (len(query) // 4) + 100,
            "latency_ms": round((time.time() - start_time) * 1000, 2),
            "estimated_cost_usd": 0.002
        }
        
        return {"data": content, "metrics": metrics, "context_used": context}

    def audit_and_refine(self, query: str, specialist_data: SpecialistResponse, lang: str = "es", trace_id: Optional[str] = None) -> Dict[str, Any]:
        """Realiza una auditoría técnica y refina la respuesta si es necesario (Feedback Loop)."""
        with open("prompts/critic_prompt.md", "r", encoding="utf-8") as f:
            template_text = f.read()
            
        prompt = ChatPromptTemplate.from_template(template_text)
        chain = prompt | self.critic_llm
        
        start_time = time.time()
        llm_config = self._get_langfuse_config(trace_id)
        
        audit_result = chain.invoke({
            "query": query,
            "response_text": specialist_data.response_text,
            "reasoning": "\n".join(specialist_data.chain_of_thought),
            "language": "Spanish" if lang == "es" else "English"
        }, config=llm_config)
        
        metrics = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "tokens_prompt": 200,
            "tokens_completion": 50,
            "total_tokens": 250,
            "latency_ms": round((time.time() - start_time) * 1000, 2),
            "estimated_cost_usd": 0.0005
        }
        
        return {"data": audit_result, "metrics": metrics}

    def evaluate_response(self, query: str, response_text: str, lang: str = "es", trace_id: Optional[str] = None) -> Dict[str, Any]:
        """Agente Evaluador que asigna puntaje y lo envía a Langfuse."""
        with open("prompts/evaluator_prompt.md", "r", encoding="utf-8") as f:
            template_text = f.read()
            
        prompt = ChatPromptTemplate.from_template(template_text)
        chain = prompt | self.evaluator_llm
        
        start_time = time.time()
        llm_config = self._get_langfuse_config(trace_id)
        
        eval_result = chain.invoke({
            "query": query,
            "response_text": response_text,
            "language": "Spanish" if lang == "es" else "English"
        }, config=llm_config)
        
        # Registrar puntaje en Langfuse vinculado a la traza raíz
        if self.langfuse_client and trace_id:
            try:
                self.langfuse_client.score(
                    trace_id=trace_id,               # ← vinculado a la traza correcta
                    name="rag_quality",
                    value=eval_result.final_score,
                    data_type="NUMERIC",
                    comment=eval_result.justification
                )
                print(f"  [Langfuse] Score {eval_result.final_score:.2f} vinculado a trace_id={trace_id}")
            except Exception as e:
                print(f"  [Error Langfuse Score] {e}")
        elif self.langfuse_client and not trace_id:
            print("  [Langfuse] Score NO enviado: trace_id no disponible.")
        
        metrics = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "latency_ms": round((time.time() - start_time) * 1000, 2)
        }
        
        return {"data": eval_result, "metrics": metrics}
