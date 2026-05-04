"""
Jira Tool — Creates a support ticket in Jira.
Uses the Jira REST API v3.
Docs: https://developer.atlassian.com/cloud/jira/platform/rest/v3/
"""
import os
import requests
from typing import Dict, Any
from src.services.tools.base_tool import BaseTool, ToolResult


# Priority mapping from internal system to Jira
PRIORITY_MAP = {
    "BAJA": "Low",
    "MEDIA": "Medium",
    "ALTA": "High",
    "CRÍTICA": "Highest",
}

# Default Jira assignee by department
ASSIGNEE_MAP = {
    "TECNOLOGIA": os.getenv("JIRA_ASSIGNEE_TECH", "tech-team"),
    "RECLAMOS": os.getenv("JIRA_ASSIGNEE_RECLAMOS", "support-team"),
    "RRHH": os.getenv("JIRA_ASSIGNEE_RRHH", "hr-team"),
    "FINANZAS": os.getenv("JIRA_ASSIGNEE_FINANZAS", "finance-team"),
    "GENERAL": os.getenv("JIRA_ASSIGNEE_GENERAL", "support-team"),
}


class JiraTool(BaseTool):
    """Creates a Jira issue from a specialist response."""

    def __init__(self):
        super().__init__("JiraTool")
        self.base_url = os.getenv("JIRA_BASE_URL", "")
        self.email = os.getenv("JIRA_EMAIL", "")
        self.api_token = os.getenv("JIRA_API_TOKEN", "")
        self.project_key = os.getenv("JIRA_PROJECT_KEY", "SUPPORT")

    def execute(self, payload: Dict[str, Any]) -> ToolResult:
        """
        payload keys:
            - query (str): Original user query
            - response_text (str): Specialist response
            - priority (str): BAJA / MEDIA / ALTA / CRÍTICA
            - department (str): TECNOLOGIA / RECLAMOS / etc.
            - intent (str): detected intent
        """
        if self.is_dry_run or not self.base_url:
            return ToolResult(
                tool_name=self.name,
                success=True,
                message=f"Ticket would be created in project {self.project_key} with priority {payload.get('priority', 'MEDIA')}",
                data={
                    "project": self.project_key,
                    "summary": payload.get("query", "")[:100],
                    "priority": PRIORITY_MAP.get(payload.get("priority", "MEDIA"), "Medium"),
                    "assignee": ASSIGNEE_MAP.get(payload.get("department", "GENERAL")),
                },
                dry_run=True
            )

        # --- LIVE call ---
        url = f"{self.base_url}/rest/api/3/issue"
        headers = {"Content-Type": "application/json"}
        auth = (self.email, self.api_token)

        jira_priority = PRIORITY_MAP.get(payload.get("priority", "MEDIA"), "Medium")
        summary = f"[{payload.get('department', 'GENERAL')}] {payload.get('query', 'Consulta')[:100]}"
        description = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": payload.get("response_text", "")}]
                }
            ]
        }

        body = {
            "fields": {
                "project": {"key": self.project_key},
                "summary": summary,
                "description": description,
                "issuetype": {"name": "Support"},
                "priority": {"name": jira_priority},
            }
        }

        try:
            response = requests.post(url, json=body, headers=headers, auth=auth, timeout=10)
            response.raise_for_status()
            data = response.json()
            return ToolResult(
                tool_name=self.name,
                success=True,
                message=f"Ticket created: {data.get('key')} — {self.base_url}/browse/{data.get('key')}",
                data=data
            )
        except requests.RequestException as e:
            return ToolResult(
                tool_name=self.name,
                success=False,
                message=f"Failed to create Jira ticket: {e}",
                data={"error": str(e)}
            )
