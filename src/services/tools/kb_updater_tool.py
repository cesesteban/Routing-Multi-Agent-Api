"""
KB Updater Tool — Saves a resolved case as a Markdown file into the department's data folder.
This closes the RAG feedback loop: resolved cases become new knowledge for future queries.
"""
import os
from datetime import datetime, timezone
from typing import Dict, Any
from src.services.tools.base_tool import BaseTool, ToolResult
from src.core.config import Config


# Map departments to their data folder config attr
DATA_PATH_MAP = {
    "RRHH": "DATA_PATH_RRHH",
    "TECNOLOGIA": "DATA_PATH_TECH",
    "FINANZAS": "DATA_PATH_FINANZAS",
    "RECLAMOS": "DATA_PATH_RECLAMOS",
    "GENERAL": "DATA_PATH_GENERAL",
    "SEGURIDAD": "DATA_PATH_SEGURIDAD",
}


class KBUpdaterTool(BaseTool):
    """Writes a resolved case into the department's knowledge base folder."""

    def __init__(self):
        super().__init__("KBUpdaterTool")

    def _build_document(self, payload: Dict[str, Any]) -> str:
        """Build a Markdown document from the resolved case."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        query = payload.get("query", "")
        response_text = payload.get("response_text", "")
        next_steps = payload.get("next_steps", [])
        priority = payload.get("priority", "MEDIA")
        department = payload.get("department", "GENERAL")

        steps_md = "\n".join(f"- {step}" for step in next_steps)

        return f"""# Caso Resuelto — {department}

**Fecha:** {timestamp}
**Prioridad:** {priority}

## Consulta Original
{query}

## Respuesta del Especialista
{response_text}

## Próximos Pasos
{steps_md}

---
*Generado automáticamente por el sistema Multi-Agent RAG*
"""

    def execute(self, payload: Dict[str, Any]) -> ToolResult:
        """
        payload keys:
            - query (str): Original user query
            - response_text (str): Specialist response
            - next_steps (list): Recommended actions
            - priority (str): BAJA / MEDIA / ALTA / CRÍTICA
            - department (str): Department name
            - evaluation_score (float): Score from Evaluator agent (0.0-1.0)
        """
        department = payload.get("department", "GENERAL")
        evaluation_score = payload.get("evaluation_score", 0.0)

        # Only store cases with high evaluation score (good quality)
        if evaluation_score < 0.7:
            return ToolResult(
                tool_name=self.name,
                success=False,
                message=f"Case skipped: evaluation score {evaluation_score:.2f} is below threshold (0.70).",
                data={"score": evaluation_score}
            )

        # Resolve the data folder path
        path_attr = DATA_PATH_MAP.get(department, "DATA_PATH_GENERAL")
        data_path = getattr(Config, path_attr, None)

        timestamp_slug = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"resolved_case_{timestamp_slug}.md"
        content = self._build_document(payload)

        if self.is_dry_run or not data_path:
            return ToolResult(
                tool_name=self.name,
                success=True,
                message=f"Case would be saved as '{filename}' in {department} knowledge base (score: {evaluation_score:.2f}).",
                data={"filename": filename, "department": department, "score": evaluation_score, "preview": content[:200]},
                dry_run=True
            )

        # --- LIVE: write the file ---
        try:
            os.makedirs(data_path, exist_ok=True)
            full_path = os.path.join(data_path, filename)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

            return ToolResult(
                tool_name=self.name,
                success=True,
                message=f"Case saved to knowledge base: {full_path}",
                data={"path": full_path, "filename": filename, "score": evaluation_score}
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                success=False,
                message=f"Failed to write to knowledge base: {e}",
                data={"error": str(e)}
            )
