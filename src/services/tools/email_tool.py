"""
Email Tool — Sends a summary email via SMTP.
Uses Python's built-in smtplib (no extra dependency needed).
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any
from src.services.tools.base_tool import BaseTool, ToolResult


class EmailTool(BaseTool):
    """Sends an email with the specialist's response summary."""

    def __init__(self):
        super().__init__("EmailTool")
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.email_from = os.getenv("EMAIL_FROM", "soporte@empresa.com")

    def _build_html(self, payload: Dict[str, Any]) -> str:
        response_text = payload.get("response_text", "")

        return f"""
        <html><body style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;">
            <div style="padding: 20px; border: 1px solid #eee; border-radius: 8px;">
                <p style="white-space: pre-wrap;">{response_text}</p>
            </div>
            <footer style="margin-top: 20px; font-size: 12px; color: #888;">
                <p>Este es un mensaje automático del Sistema de Soporte IA.</p>
            </footer>
        </body></html>
        """

    def execute(self, payload: Dict[str, Any]) -> ToolResult:
        """
        payload keys:
            - query (str): Original user query
            - response_text (str): Specialist response
            - next_steps (list): List of next steps
            - priority (str): BAJA / MEDIA / ALTA / CRÍTICA
            - department (str): Department name
            - to_email (str): Recipient email address
        """
        to_email = payload.get("to_email", "")

        if self.is_dry_run or not self.smtp_user:
            return ToolResult(
                tool_name=self.name,
                success=True,
                message=f"Email would be sent to '{to_email or 'user@example.com'}' containing the specialist response text.",
                data={"to": to_email, "subject": f"[{payload.get('department', 'Soporte')}] Respuesta a su consulta"},
                dry_run=True
            )

        if not to_email:
            return ToolResult(
                tool_name=self.name,
                success=False,
                message="No recipient email provided in payload (to_email).",
                data={}
            )

        # --- LIVE call ---
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[{payload.get('department', 'Soporte')}] Respuesta a su consulta"
            msg["From"] = self.email_from
            msg["To"] = to_email
            msg.attach(MIMEText(self._build_html(payload), "html"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.email_from, to_email, msg.as_string())

            return ToolResult(
                tool_name=self.name,
                success=True,
                message=f"Email sent successfully to {to_email}",
                data={"to": to_email}
            )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                success=False,
                message=f"Failed to send email: {e}",
                data={"error": str(e)}
            )
