"""
Slack Tool — Sends a notification to a Slack channel via Incoming Webhook.
No OAuth required. Configure one webhook URL per department channel.
Docs: https://api.slack.com/messaging/webhooks
"""
import os
import requests
from typing import Dict, Any
from src.services.tools.base_tool import BaseTool, ToolResult


# Map departments to their Slack webhook env var names
WEBHOOK_ENV_MAP = {
    "RRHH": "SLACK_WEBHOOK_RRHH",
    "TECNOLOGIA": "SLACK_WEBHOOK_TECNOLOGIA",
    "FINANZAS": "SLACK_WEBHOOK_FINANZAS",
    "RECLAMOS": "SLACK_WEBHOOK_RECLAMOS",
    "GENERAL": "SLACK_WEBHOOK_GENERAL",
    "SEGURIDAD": "SLACK_WEBHOOK_SEGURIDAD",
}

PRIORITY_EMOJI = {
    "BAJA": "🟢",
    "MEDIA": "🟡",
    "ALTA": "🟠",
    "CRÍTICA": "🔴",
}


class SlackTool(BaseTool):
    """Sends a Slack notification to the department channel."""

    def __init__(self):
        super().__init__("SlackTool")

    def _get_webhook(self, department: str) -> str:
        env_key = WEBHOOK_ENV_MAP.get(department, "SLACK_WEBHOOK_GENERAL")
        return os.getenv(env_key, "")

    def _build_blocks(self, payload: Dict[str, Any]) -> list:
        """Build rich Slack Block Kit message."""
        department = payload.get("department", "GENERAL")
        query = payload.get("query", "")[:300]
        response_text = payload.get("response_text", "")[:500]
        priority = payload.get("priority", "MEDIA")
        requires_supervisor = payload.get("requires_supervisor", False)
        next_steps = payload.get("next_steps", [])
        emoji = PRIORITY_EMOJI.get(priority, "⚪")

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"🤖 Nueva consulta — {department}", "emoji": True}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Prioridad:*\n{emoji} {priority}"},
                    {"type": "mrkdwn", "text": f"*Escalación:*\n{'⚠️ Sí' if requires_supervisor else '✅ No'}"}
                ]
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Consulta:*\n_{query}_"}
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Respuesta del agente:*\n{response_text}"}
            }
        ]

        if next_steps:
            steps_text = "\n".join(f"• {step}" for step in next_steps[:3])
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Próximos pasos:*\n{steps_text}"}
            })

        return blocks

    def execute(self, payload: Dict[str, Any]) -> ToolResult:
        """
        payload keys:
            - query (str): Original user query
            - response_text (str): Specialist response
            - priority (str): BAJA / MEDIA / ALTA / CRÍTICA
            - department (str): Department name
            - requires_supervisor (bool): Whether escalation is needed
            - next_steps (list): Recommended next steps
        """
        department = payload.get("department", "GENERAL")
        webhook_url = self._get_webhook(department)

        if self.is_dry_run or not webhook_url:
            channel_name = f"#{department.lower()}-support"
            return ToolResult(
                tool_name=self.name,
                success=True,
                message=f"Slack notification would be sent to {channel_name} with priority {payload.get('priority', 'MEDIA')}.",
                data={"channel": channel_name, "blocks_count": len(self._build_blocks(payload))},
                dry_run=True
            )

        # --- LIVE call ---
        body = {
            "text": f"Nueva consulta de {department}: {payload.get('query', '')[:100]}",
            "blocks": self._build_blocks(payload)
        }

        try:
            response = requests.post(webhook_url, json=body, timeout=10)
            response.raise_for_status()
            return ToolResult(
                tool_name=self.name,
                success=True,
                message=f"Slack notification sent to #{department.lower()}-support channel.",
                data={"status_code": response.status_code}
            )
        except requests.RequestException as e:
            return ToolResult(
                tool_name=self.name,
                success=False,
                message=f"Failed to send Slack notification: {e}",
                data={"error": str(e)}
            )
