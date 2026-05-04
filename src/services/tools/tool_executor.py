"""
Tool Executor — Decides which tools to run based on the specialist response metadata.
This is deterministic: no LLM involved in the decision.

Logic:
    - ALWAYS: EmailTool (if to_email provided)
    - priority in [ALTA, CRÍTICA] OR requires_supervisor: JiraTool + SlackTool
    - requires_supervisor: CalendarTool
    - evaluation_score >= 0.7: KBUpdaterTool
"""
from typing import Dict, Any, List
from src.services.tools.base_tool import ToolResult
from src.services.tools.jira_tool import JiraTool
from src.services.tools.email_tool import EmailTool
from src.services.tools.slack_tool import SlackTool
from src.services.tools.calendar_tool import CalendarTool
from src.services.tools.kb_updater_tool import KBUpdaterTool


class ToolExecutor:
    """Orchestrates tool execution based on specialist response metadata."""

    def __init__(self):
        self.jira = JiraTool()
        self.email = EmailTool()
        self.slack = SlackTool()
        self.calendar = CalendarTool()
        self.kb_updater = KBUpdaterTool()

    def run(self, payload: Dict[str, Any]) -> List[ToolResult]:
        """
        Evaluate the payload and run the appropriate tools.

        payload keys (from RoutingService):
            - query (str)
            - department (str)
            - response_text (str)
            - next_steps (list)
            - priority (str): BAJA / MEDIA / ALTA / CRÍTICA
            - requires_supervisor (bool)
            - evaluation_score (float): 0.0 to 1.0
            - to_email (str, optional)
            - attendee_email (str, optional)
        """
        results: List[ToolResult] = []
        priority = payload.get("priority", "MEDIA")
        requires_supervisor = payload.get("requires_supervisor", False)
        evaluation_score = payload.get("evaluation_score", 0.0)
        to_email = payload.get("to_email", "")

        print(f"\n  [ToolExecutor] Running tools for department={payload.get('department')} | priority={priority} | supervisor={requires_supervisor}")

        # 1. Email — always if recipient is available
        if to_email:
            result = self.email.execute(payload)
            results.append(result)
            print(f"  {result}")

        # 2. Slack + Jira — on high priority or escalation
        if priority in ("ALTA", "CRÍTICA") or requires_supervisor:
            result = self.slack.execute(payload)
            results.append(result)
            print(f"  {result}")

            result = self.jira.execute(payload)
            results.append(result)
            print(f"  {result}")

        # 3. Calendar — only when human intervention needed
        if requires_supervisor:
            result = self.calendar.execute(payload)
            results.append(result)
            print(f"  {result}")

        # 4. KB Updater — only for high-quality responses
        if evaluation_score >= 0.7:
            result = self.kb_updater.execute(payload)
            results.append(result)
            print(f"  {result}")

        if not results:
            print("  [ToolExecutor] No tools were triggered for this case.")

        return results
