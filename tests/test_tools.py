"""
Tests for agent tools — run in dry-run mode (no real API calls needed).
All tools should succeed even without credentials configured.
"""
import sys
import os
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

# Force dry-run mode for all tests
os.environ["DRY_RUN"] = "true"

from src.services.tools.jira_tool import JiraTool
from src.services.tools.email_tool import EmailTool
from src.services.tools.slack_tool import SlackTool
from src.services.tools.calendar_tool import CalendarTool
from src.services.tools.kb_updater_tool import KBUpdaterTool
from src.services.tools.tool_executor import ToolExecutor


# ── Shared test payload ───────────────────────────────────────────────────────

BASE_PAYLOAD = {
    "query": "Mi laptop no conecta a la VPN de la empresa",
    "department": "TECNOLOGIA",
    "response_text": "El problema es un conflicto con el cliente VPN. Reinstale la versión 5.x.",
    "next_steps": ["Desinstalar VPN", "Descargar versión 5.x", "Reiniciar equipo"],
    "priority": "ALTA",
    "requires_supervisor": False,
    "evaluation_score": 0.85,
    "to_email": "usuario@empresa.com",
    "attendee_email": "supervisor@empresa.com",
}

CRITICAL_PAYLOAD = {**BASE_PAYLOAD, "priority": "CRÍTICA", "requires_supervisor": True}
LOW_SCORE_PAYLOAD = {**BASE_PAYLOAD, "evaluation_score": 0.5}


# ── Individual tool tests ─────────────────────────────────────────────────────

def test_jira_tool_dry_run():
    result = JiraTool().execute(BASE_PAYLOAD)
    print(f"\n{result}")
    assert result.success is True
    assert result.dry_run is True
    assert result.data["project"] == os.getenv("JIRA_PROJECT_KEY", "SUPPORT")
    assert result.data["priority"] == "High"  # ALTA → High


def test_email_tool_dry_run():
    result = EmailTool().execute(BASE_PAYLOAD)
    print(f"\n{result}")
    assert result.success is True
    assert result.dry_run is True
    assert "usuario@empresa.com" in result.message


def test_slack_tool_dry_run():
    result = SlackTool().execute(BASE_PAYLOAD)
    print(f"\n{result}")
    assert result.success is True
    assert result.dry_run is True
    assert "tecnologia" in result.data["channel"]


def test_calendar_tool_dry_run():
    result = CalendarTool().execute(CRITICAL_PAYLOAD)
    print(f"\n{result}")
    assert result.success is True
    assert result.dry_run is True
    assert "TECNOLOGIA" in result.data["event_summary"]


def test_kb_updater_low_score_skipped():
    """Cases with low evaluation score should NOT be saved."""
    result = KBUpdaterTool().execute(LOW_SCORE_PAYLOAD)
    print(f"\n{result}")
    assert result.success is False
    assert "threshold" in result.message


def test_kb_updater_high_score_dry_run():
    """Cases with high evaluation score should be saved (dry-run)."""
    result = KBUpdaterTool().execute(BASE_PAYLOAD)
    print(f"\n{result}")
    assert result.success is True
    assert result.dry_run is True
    assert result.data["score"] == 0.85


# ── ToolExecutor integration test ─────────────────────────────────────────────

def test_tool_executor_alta_priority():
    """On ALTA priority: Email + Slack + Jira + KB should run."""
    executor = ToolExecutor()
    results = executor.run(BASE_PAYLOAD)

    tool_names = [r.tool_name for r in results]
    print(f"\nTools executed: {tool_names}")

    assert "EmailTool" in tool_names
    assert "SlackTool" in tool_names
    assert "JiraTool" in tool_names
    assert "KBUpdaterTool" in tool_names
    assert all(r.success for r in results)


def test_tool_executor_critica_with_supervisor():
    """On CRÍTICA with supervisor: All 5 tools should run."""
    executor = ToolExecutor()
    results = executor.run(CRITICAL_PAYLOAD)

    tool_names = [r.tool_name for r in results]
    print(f"\nTools executed: {tool_names}")

    assert "EmailTool" in tool_names
    assert "SlackTool" in tool_names
    assert "JiraTool" in tool_names
    assert "CalendarTool" in tool_names
    assert "KBUpdaterTool" in tool_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
