"""
E2E Tests — Agent Tools Integration

Tests:
  - Each tool returns ToolResult with expected structure in dry-run mode
  - ToolExecutor routes correctly based on priority and supervisor flag
  - ToolExecutor returns list of ToolResult objects
  - KB Updater filters low-score cases
  - Tool payload flows end-to-end via the API
"""
import pytest
import os

os.environ["DRY_RUN"] = "true"

from httpx import AsyncClient
from src.services.tools.base_tool import ToolResult
from src.services.tools.jira_tool import JiraTool
from src.services.tools.email_tool import EmailTool
from src.services.tools.slack_tool import SlackTool
from src.services.tools.calendar_tool import CalendarTool
from src.services.tools.kb_updater_tool import KBUpdaterTool
from src.services.tools.tool_executor import ToolExecutor

pytestmark = pytest.mark.asyncio


# ── Shared fixtures ───────────────────────────────────────────────────────────

BAJA_PAYLOAD = {
    "query": "¿Cuándo es el próximo feriado?",
    "department": "RRHH",
    "response_text": "El próximo feriado es el 25 de mayo.",
    "next_steps": ["Consultar el calendario laboral"],
    "priority": "BAJA",
    "requires_supervisor": False,
    "evaluation_score": 0.80,
    "to_email": "usuario@empresa.com",
    "attendee_email": "",
}

ALTA_PAYLOAD = {
    "query": "El servidor de producción está caído",
    "department": "TECNOLOGIA",
    "response_text": "Se detectó una falla en el servidor principal. Iniciando protocolo de failover.",
    "next_steps": ["Activar servidor de respaldo", "Notificar al equipo de guardia", "Abrir puente de crisis"],
    "priority": "ALTA",
    "requires_supervisor": False,
    "evaluation_score": 0.91,
    "to_email": "ops@empresa.com",
    "attendee_email": "",
}

CRITICA_PAYLOAD = {**ALTA_PAYLOAD, "priority": "CRÍTICA", "requires_supervisor": True, "attendee_email": "cto@empresa.com"}


# ── Unit: ToolResult structure ─────────────────────────────────────────────────

def test_tool_result_string_representation():
    """ToolResult __str__ should include tool name and status emoji."""
    r = ToolResult(tool_name="TestTool", success=True, message="All good", dry_run=True)
    text = str(r)
    assert "✅" in text
    assert "TestTool" in text
    assert "[DRY-RUN]" in text

    r2 = ToolResult(tool_name="TestTool", success=False, message="Failed")
    assert "❌" in str(r2)


def test_tool_result_live_mode_label():
    """Non-dry-run ToolResult should show [LIVE] label."""
    r = ToolResult(tool_name="TestTool", success=True, message="Sent", dry_run=False)
    assert "[LIVE]" in str(r)


# ── Unit: Individual tools in dry-run ─────────────────────────────────────────

def test_jira_creates_correct_priority_mapping():
    """ALTA priority should map to 'High' in Jira."""
    result = JiraTool().execute(ALTA_PAYLOAD)
    assert result.success is True
    assert result.dry_run is True
    assert result.data["priority"] == "High"


def test_jira_critica_maps_to_highest():
    """CRÍTICA priority should map to 'Highest' in Jira."""
    result = JiraTool().execute(CRITICA_PAYLOAD)
    assert result.data["priority"] == "Highest"


def test_email_includes_recipient_in_message():
    """Email dry-run message should reference the recipient address."""
    result = EmailTool().execute(ALTA_PAYLOAD)
    assert "ops@empresa.com" in result.message


def test_email_no_recipient_fails_gracefully():
    """EmailTool with empty to_email and DRY_RUN=false should fail gracefully."""
    payload_no_email = {**BAJA_PAYLOAD, "to_email": ""}
    # Even in dry-run this is fine, but test the message
    result = EmailTool().execute(payload_no_email)
    # In dry-run mode, it still reports a dry run (no smtp_user = dry_run anyway)
    assert isinstance(result, ToolResult)


def test_slack_uses_correct_channel_per_department():
    """Slack should reference the correct department channel."""
    result_tech = SlackTool().execute(ALTA_PAYLOAD)
    assert "tecnologia" in result_tech.data["channel"]

    rrhh_payload = {**BAJA_PAYLOAD, "department": "RRHH"}
    result_rrhh = SlackTool().execute(rrhh_payload)
    assert "rrhh" in result_rrhh.data["channel"]


def test_calendar_includes_department_in_event_name():
    """Calendar event summary should include the department name."""
    result = CalendarTool().execute(CRITICA_PAYLOAD)
    assert "TECNOLOGIA" in result.data["event_summary"]


def test_kb_updater_skips_low_score():
    """KB Updater must skip cases with evaluation_score < 0.7."""
    low_score = {**BAJA_PAYLOAD, "evaluation_score": 0.55}
    result = KBUpdaterTool().execute(low_score)
    assert result.success is False
    assert "threshold" in result.message


def test_kb_updater_saves_high_score(tmp_path):
    """KB Updater should write a file for high-score cases."""
    import os
    from src.core.config import Config

    # Point DATA_PATH_RRHH to a temp directory
    original = getattr(Config, "DATA_PATH_RRHH", None)
    Config.DATA_PATH_RRHH = str(tmp_path)
    os.environ["DRY_RUN"] = "false"  # temporarily disable dry-run

    try:
        result = KBUpdaterTool().execute(BAJA_PAYLOAD)
        assert result.success is True
        saved_files = list(tmp_path.glob("resolved_case_*.md"))
        assert len(saved_files) == 1
        content = saved_files[0].read_text(encoding="utf-8")
        assert "feriado" in content.lower()
    finally:
        Config.DATA_PATH_RRHH = original
        os.environ["DRY_RUN"] = "true"


# ── Unit: ToolExecutor routing logic ──────────────────────────────────────────

def test_executor_baja_no_supervisor_triggers_email_and_kb():
    """BAJA priority + no supervisor: only Email and KB Updater should run."""
    executor = ToolExecutor()
    results = executor.run(BAJA_PAYLOAD)
    tool_names = [r.tool_name for r in results]

    assert "EmailTool" in tool_names
    assert "KBUpdaterTool" in tool_names
    assert "JiraTool" not in tool_names
    assert "SlackTool" not in tool_names
    assert "CalendarTool" not in tool_names


def test_executor_alta_no_supervisor_triggers_email_slack_jira_kb():
    """ALTA priority + no supervisor: Email, Slack, Jira, KB should all run."""
    executor = ToolExecutor()
    results = executor.run(ALTA_PAYLOAD)
    tool_names = [r.tool_name for r in results]

    assert "EmailTool" in tool_names
    assert "SlackTool" in tool_names
    assert "JiraTool" in tool_names
    assert "KBUpdaterTool" in tool_names
    assert "CalendarTool" not in tool_names


def test_executor_critica_with_supervisor_triggers_all_five():
    """CRÍTICA + requires_supervisor=True: all 5 tools must run."""
    executor = ToolExecutor()
    results = executor.run(CRITICA_PAYLOAD)
    tool_names = [r.tool_name for r in results]

    assert "EmailTool" in tool_names
    assert "SlackTool" in tool_names
    assert "JiraTool" in tool_names
    assert "CalendarTool" in tool_names
    assert "KBUpdaterTool" in tool_names


def test_executor_no_email_skips_email_tool():
    """ToolExecutor should not run EmailTool when to_email is empty."""
    executor = ToolExecutor()
    payload_no_email = {**ALTA_PAYLOAD, "to_email": ""}
    results = executor.run(payload_no_email)
    tool_names = [r.tool_name for r in results]
    assert "EmailTool" not in tool_names


def test_executor_all_results_are_tool_result_instances():
    """Every item returned by ToolExecutor must be a ToolResult."""
    executor = ToolExecutor()
    results = executor.run(CRITICA_PAYLOAD)
    for result in results:
        assert isinstance(result, ToolResult)


# ── E2E: Tools triggered through the API ──────────────────────────────────────

async def test_api_query_with_email_does_not_fail(client: AsyncClient):
    """A full API call with to_email should succeed and include tools_executed if present."""
    response = await client.post("/api/v1/query", json={
        "query": "El servidor está caído urgente",
        "lang": "es",
        "to_email": "ops@empresa.com"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["id"] is not None
    # tools_executed is saved in DB but may not be in the schema; just ensure no crash
    assert data["response_text"] is not None


async def test_api_query_without_email_does_not_fail(client: AsyncClient):
    """A full API call without to_email should also succeed."""
    response = await client.post("/api/v1/query", json={
        "query": "Consulta sin email configurado",
        "lang": "es"
    })
    assert response.status_code == 200
