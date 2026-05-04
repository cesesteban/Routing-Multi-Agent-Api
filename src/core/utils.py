import time
from typing import Dict, Any
from src.core.constants import COST_INPUT_1M, COST_OUTPUT_1M

def calculate_cost(tokens_in: int, tokens_out: int) -> float:
    """Calcula el costo estimado basado en el uso de tokens."""
    return (tokens_in / 1_000_000 * COST_INPUT_1M) + (tokens_out / 1_000_000 * COST_OUTPUT_1M)

def get_metrics(response: Any, start_time: float) -> Dict[str, Any]:
    """Extrae métricas de uso y latencia de una respuesta del LLM."""
    # Soporte para extracción de metadatos de tokens y latencia
    metadata = getattr(response, "response_metadata", {})
    token_usage = metadata.get("token_usage", {})
    prompt_tokens = token_usage.get("prompt_tokens", 0)
    completion_tokens = token_usage.get("completion_tokens", 0)
    total_tokens = token_usage.get("total_tokens", 0)
    latency = (time.time() - start_time) * 1000
    
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tokens_prompt": prompt_tokens,
        "tokens_completion": completion_tokens,
        "total_tokens": total_tokens,
        "latency_ms": round(latency, 2),
        "estimated_cost_usd": calculate_cost(prompt_tokens, completion_tokens)
    }
