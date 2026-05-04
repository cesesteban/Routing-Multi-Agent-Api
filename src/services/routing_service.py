from src.core.config import Config
from src.services.ai.agent_service import MultiAgentSystem
from src.services.security.safety_service import SafetyGuard
from src.services.ai.context_service import ContextEngineer
from src.services.tools.tool_executor import ToolExecutor
from src.core.constants import VALID_DEPARTMENTS
from src.core.exceptions import ProviderException
from src.repositories.query_repository import QueryRepository
from typing import Dict, Any
import time


class RoutingService:
    def __init__(self, query_repo: QueryRepository):
        self.query_repo = query_repo
        self.system = MultiAgentSystem()
        self.safety = SafetyGuard(llm=self.system.nano_llm, rag=self.system.rag)
        self.context_eng = ContextEngineer()
        self.tool_executor = ToolExecutor()

    async def process_query(self, query: str, lang: str = "es", to_email: str = "") -> Dict[str, Any]:
        """Procesa una consulta a través de todo el flujo multi-agente y la persiste en DB."""

        # 1. Pre-procesamientos (Limpieza y Seguridad)
        ctx = self.context_eng.build_context_packet(query)
        clean_query = ctx["clean_query"]

        # Seguridad L1 y L2
        is_unsafe, reason = self.safety.is_adversarial(clean_query)
        if not is_unsafe:
            is_unsafe, reason = self.safety.is_adversarial_deep(clean_query)

        if is_unsafe:
            fallback = self.safety.fallback_response(reason)
            record_data = {
                "query": query,
                "intent": "SAFETY_BLOCKED",
                "confidence": 1.0,
                "routing_reason": reason,
                "response_text": fallback["response_text"],
                "next_steps": fallback["next_steps"],
                "priority": fallback["priority"],
                "model_used": Config.MODEL_NANO,
                "context_hash": ctx["context_hash"]
            }
            return await self.query_repo.create(record_data)

        # 2. Orquestación Multi-Agente
        routing_result = self.system.route_query(clean_query, lang=lang)
        intent_data = routing_result["data"]

        # 3. Ciclo Especialista - Auditor
        attempts = 0
        max_attempts = 3
        feedback = ""
        audit_history = []
        context_used = ""
        final_data = None

        while attempts < max_attempts:
            attempts += 1
            specialist_result = self.system.handle_specialist(clean_query, intent_data, feedback=feedback, lang=lang)
            final_data = specialist_result["data"]
            context_used = specialist_result.get("context_used", "")

            audit_result = self.system.audit_and_refine(clean_query, final_data, lang=lang)
            critic_data = audit_result["data"]
            audit_history.append(critic_data.model_dump())

            if critic_data.is_valid:
                break
            else:
                feedback = f"Issues detectados: {', '.join(critic_data.issues)}. Sugerencia: {critic_data.suggestions}"

        # 4. Agente Evaluador RAG
        eval_result = self.system.evaluate_response(clean_query, final_data.response_text, lang=lang)
        evaluation = eval_result["data"]

        # 5. Cálculo de Métricas
        total_metrics = {
            "total_tokens": routing_result["metrics"]["total_tokens"] + (specialist_result["metrics"]["total_tokens"] * attempts) + (audit_result["metrics"]["total_tokens"] * attempts),
            "latency_ms": round(routing_result["metrics"]["latency_ms"] + (specialist_result["metrics"]["latency_ms"] * attempts) + (audit_result["metrics"]["latency_ms"] * attempts) + eval_result["metrics"]["latency_ms"], 2),
            "estimated_cost_usd": round(routing_result["metrics"]["estimated_cost_usd"] + (specialist_result["metrics"]["estimated_cost_usd"] * attempts) + (audit_result["metrics"]["estimated_cost_usd"] * attempts), 5)
        }

        record_data = {
            "query": query,
            "intent": intent_data.intent,
            "confidence": intent_data.confidence,
            "routing_reason": intent_data.reason,
            "response_text": final_data.response_text,
            "priority": final_data.priority,
            "next_steps": final_data.next_steps,
            "audit_trace": audit_history,
            "evaluation_score": evaluation.final_score,
            "evaluation_justification": evaluation.justification,
            "latency_ms": total_metrics["latency_ms"],
            "total_tokens": total_metrics["total_tokens"],
            "estimated_cost_usd": total_metrics["estimated_cost_usd"],
            "model_used": Config.MODEL_POWERFUL,
            "attempts": attempts,
            "context_hash": ctx["context_hash"]
        }

        # 6. Ejecución de Tools (post-respuesta, no bloquea el resultado)
        try:
            tool_payload = {
                "query": clean_query,
                "department": intent_data.intent,
                "response_text": final_data.response_text,
                "next_steps": final_data.next_steps,
                "priority": final_data.priority,
                "requires_supervisor": final_data.requires_supervisor,
                "evaluation_score": evaluation.final_score,
                "to_email": to_email,
                "attendee_email": to_email,
            }
            tool_results = self.tool_executor.run(tool_payload)
            for r in tool_results:
                print(f"  {r}")
        except Exception as e:
            print(f"  [ToolExecutor ERROR] Tools fallaron silenciosamente: {e}")

        return await self.query_repo.create(record_data)
