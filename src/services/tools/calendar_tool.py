"""
Calendar Tool — Creates a Google Calendar event for human escalation.
Uses Google Calendar API v3 via service account credentials.
Only triggers when requires_supervisor=True.
Docs: https://developers.google.com/calendar/api/v3/reference/events/insert
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from src.services.tools.base_tool import BaseTool, ToolResult


class CalendarTool(BaseTool):
    """Schedules a human follow-up meeting in Google Calendar."""

    def __init__(self):
        super().__init__("CalendarTool")
        self.calendar_id = os.getenv("CALENDAR_ID", "primary")
        self.credentials_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

    def execute(self, payload: Dict[str, Any]) -> ToolResult:
        """
        payload keys:
            - query (str): Original user query
            - department (str): Department name
            - priority (str): BAJA / MEDIA / ALTA / CRÍTICA
            - requires_supervisor (bool): Must be True for this tool to be useful
            - attendee_email (str, optional): User email to invite
        """
        department = payload.get("department", "Soporte")
        query = payload.get("query", "Consulta sin descripción")[:120]
        attendee_email = payload.get("attendee_email", "")

        # Schedule the meeting 30 min from now by default
        start_time = datetime.now(timezone.utc) + timedelta(hours=1)
        end_time = start_time + timedelta(minutes=30)

        event_summary = f"[{department}] Escalación: {query}"
        event_body = {
            "summary": event_summary,
            "description": f"Consulta escalada automáticamente por el sistema Multi-Agent.\n\nConsulta: {query}",
            "start": {"dateTime": start_time.isoformat(), "timeZone": "America/Argentina/Buenos_Aires"},
            "end": {"dateTime": end_time.isoformat(), "timeZone": "America/Argentina/Buenos_Aires"},
            "attendees": [{"email": attendee_email}] if attendee_email else [],
        }

        if self.is_dry_run or not self.credentials_file:
            return ToolResult(
                tool_name=self.name,
                success=True,
                message=f"Meeting would be scheduled: '{event_summary}' at {start_time.strftime('%Y-%m-%d %H:%M UTC')}",
                data={
                    "event_summary": event_summary,
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "attendee": attendee_email or "not provided",
                    "calendar_id": self.calendar_id
                },
                dry_run=True
            )

        # --- LIVE call ---
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            scopes = ["https://www.googleapis.com/auth/calendar"]
            creds = service_account.Credentials.from_service_account_file(
                self.credentials_file, scopes=scopes
            )
            service = build("calendar", "v3", credentials=creds)
            event = service.events().insert(calendarId=self.calendar_id, body=event_body).execute()

            return ToolResult(
                tool_name=self.name,
                success=True,
                message=f"Meeting created: {event.get('htmlLink')}",
                data={"event_id": event.get("id"), "link": event.get("htmlLink")}
            )
        except ImportError:
            return ToolResult(
                tool_name=self.name,
                success=False,
                message="google-api-python-client not installed. Add it to requirements.txt.",
                data={}
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                success=False,
                message=f"Failed to create calendar event: {e}",
                data={"error": str(e)}
            )
