import os
import json
from typing import Tuple, Dict, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from src.core.constants import FORBIDDEN_PATTERNS

class SafetyDeepResponse(BaseModel):
    is_adversarial: bool = Field(description="Si la consulta es maliciosa")
    risk_level: str = Field(description="Nivel de riesgo detectado")
    reason: str = Field(description="Explicación técnica")
    policy_violated: str = Field(description="Política violada")

class SafetyGuard:
    def __init__(self, llm=None, rag=None):
        self.llm = llm.with_structured_output(SafetyDeepResponse) if llm else None
        self.rag = rag
        
    def is_adversarial(self, query: str) -> Tuple[bool, str]:
        """L1: Detección rápida de patrones prohibidos."""
        query_lower = query.lower()
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in query_lower:
                return True, f"L1: Amenaza detectada (Patrón prohibido): {pattern}"
                
        return False, ""

    def is_adversarial_deep(self, query: str) -> Tuple[bool, str]:
        """L2: Auditoría profunda utilizando RAG y LLM."""
        if not self.llm or not self.rag:
            print("  [Safety] Deep check omitido: Dependencias no inicializadas.")
            return False, ""
            
        print("  [Safety] Ejecutando auditoría profunda con RAG...")
        
        # 1. Recuperar contexto de seguridad relevante
        context = self.rag.retrieve_context(query, "SEGURIDAD")
        
        # 2. Cargar prompt de auditoría
        with open("prompts/safety_prompt.md", "r", encoding="utf-8") as f:
            template = f.read()
            
        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | self.llm
        
        # 3. Ejecutar evaluación
        try:
            result = chain.invoke({"query": query, "context": context})
            if result.is_adversarial:
                return True, f"L2: {result.risk_level} - {result.reason} (Política: {result.policy_violated})"
        except Exception as e:
            print(f"  [Error Safety Deep] {e}")
            
        return False, ""

    @staticmethod
    def fallback_response(reason: str) -> Dict[str, Any]:
        """Respuesta de seguridad predefinida."""
        return {
            "response_text": "Lo sentimos, la solicitud ha sido bloqueada por nuestros sistemas de seguridad avanzados.",
            "next_steps": ["Contactar al equipo de Ciberseguridad", "Revisar las políticas de uso aceptable"],
            "priority": "CRITICAL",
            "requires_supervisor": True,
            "safety_reason": reason
        }
