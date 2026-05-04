import hashlib
import json
from typing import List, Dict, Any

class ContextEngineer:
    """
    Capa de pre-procesamiento para limpiar y normalizar las consultas del usuario
    antes de enviarlas al sistema multi-agente.
    """
    
    @staticmethod
    def _dedupe_text(text: str) -> str:
        """Elimina palabras duplicadas consecutivas por error de escritura."""
        words = text.split()
        if not words:
            return ""
        result = [words[0]]
        for word in words[1:]:
            if word.lower() != result[-1].lower():
                result.append(word)
        return " ".join(result)

    @staticmethod
    def build_context_packet(query: str) -> Dict[str, Any]:
        """
        Limpia la consulta y genera un paquete de contexto con hash de trazabilidad.
        """
        # 1. Limpieza básica
        clean_query = query.strip()
        clean_query = ContextEngineer._dedupe_text(clean_query)
        
        # 2. Generación de Hash para caché o trazabilidad
        query_hash = hashlib.sha256(clean_query.lower().encode()).hexdigest()[:12]
        
        return {
            "original_query": query,
            "clean_query": clean_query,
            "context_hash": query_hash,
            "metadata": {
                "length": len(clean_query),
                "is_empty": len(clean_query) == 0
            }
        }
