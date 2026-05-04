"""
conftest.py — Shared fixtures for the entire test suite.

Provides:
- async SQLite in-memory DB for isolation
- FastAPI TestClient with overridden DB dependency
- Mocked MultiAgentSystem so tests run without a real LLM
- Mocked RAGManager so tests run without ChromaDB files
"""
import sys
import os
import pytest
import pytest_asyncio

# Ensure project root is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Force dry-run mode so tools never make real external calls
os.environ.setdefault("DRY_RUN", "true")
os.environ.setdefault("LLM_PROVIDER", "lm_studio")

from unittest.mock import MagicMock, AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.database.session import Base, get_db
from main import app


# ── In-memory SQLite async engine ─────────────────────────────────────────────

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture(scope="function", autouse=False)
async def test_db():
    """Create all tables in-memory before each test, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db():
    """Replace the real DB session with the in-memory test session."""
    async with TestSessionLocal() as session:
        yield session


# ── Mocked LLM responses ───────────────────────────────────────────────────────

def make_mock_system():
    """
    Returns a MultiAgentSystem mock with pre-configured responses
    for Router, Specialist, Auditor and Evaluator agents.
    """
    from src.services.ai.agent_service import (
        RouterResponse, SpecialistResponse, CriticResponse, EvaluatorResponse
    )

    mock = MagicMock()

    mock.route_query.return_value = {
        "data": RouterResponse(
            chain_of_thought=["Señal detectada", "Estrategia definida", "Sin riesgos", "Clasificado como TECNOLOGIA"],
            intent="TECNOLOGIA",
            confidence=0.95,
            reason="La consulta menciona problemas de conectividad y VPN."
        ),
        "metrics": {"total_tokens": 150, "latency_ms": 300.0, "estimated_cost_usd": 0.0002}
    }

    mock.handle_specialist.return_value = {
        "data": SpecialistResponse(
            chain_of_thought=["Análisis", "Estrategia", "Sin riesgos", "Solución clara"],
            response_text="El problema de VPN se resuelve reinstalando el cliente en su versión más reciente.",
            next_steps=["Desinstalar el cliente VPN actual", "Descargar la versión 5.x", "Reiniciar el equipo"],
            priority="ALTA",
            requires_supervisor=False,
            avoid=["Evitar tecnicismos innecesarios"],
            tone_notes=["Tono empático y directo"],
            why_it_works=["Solución probada en casos similares"]
        ),
        "context_used": "Contexto RAG simulado",
        "metrics": {"total_tokens": 400, "latency_ms": 800.0, "estimated_cost_usd": 0.0008}
    }

    mock.audit_and_refine.return_value = {
        "data": CriticResponse(
            is_valid=True,
            issues=[],
            suggestions="La respuesta es clara y completa.",
            score=0.92
        ),
        "metrics": {"total_tokens": 200, "latency_ms": 400.0, "estimated_cost_usd": 0.0004}
    }

    mock.evaluate_response.return_value = {
        "data": EvaluatorResponse(
            accuracy_score=9,
            relevance_score=9,
            groundedness_score=8,
            final_score=0.87,
            justification="Respuesta precisa, relevante y fundamentada en contexto RAG."
        ),
        "metrics": {"total_tokens": 100, "latency_ms": 200.0, "estimated_cost_usd": 0.0001}
    }

    mock.nano_llm = MagicMock()
    mock.rag = MagicMock()
    mock.rag.retrieve_context.return_value = ""

    return mock


# ── FastAPI test client with all overrides ─────────────────────────────────────

@pytest_asyncio.fixture(scope="function")
async def client(test_db):
    """
    Async HTTP client for the FastAPI app, with:
    - In-memory SQLite DB
    - Mocked MultiAgentSystem (no LLM needed)
    - DRY_RUN=true (no real tool calls)
    """
    app.dependency_overrides[get_db] = override_get_db

    mock_system = make_mock_system()

    with patch("src.services.routing_service.MultiAgentSystem", return_value=mock_system):
        with patch("src.services.routing_service.SafetyGuard") as mock_safety_cls:
            mock_safety = MagicMock()
            mock_safety.is_adversarial.return_value = (False, "")
            mock_safety.is_adversarial_deep.return_value = (False, "")
            mock_safety_cls.return_value = mock_safety

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def client_unsafe(test_db):
    """Client that simulates an adversarial/unsafe query detection."""
    app.dependency_overrides[get_db] = override_get_db

    mock_system = make_mock_system()

    with patch("src.services.routing_service.MultiAgentSystem", return_value=mock_system):
        with patch("src.services.routing_service.SafetyGuard") as mock_safety_cls:
            mock_safety = MagicMock()
            mock_safety.is_adversarial.return_value = (True, "L1: Amenaza detectada (Patrón prohibido): ignore all previous instructions")
            mock_safety.is_adversarial_deep.return_value = (False, "")
            mock_safety.fallback_response.return_value = {
                "response_text": "Solicitud bloqueada por seguridad.",
                "next_steps": ["Contactar a Ciberseguridad"],
                "priority": "CRITICAL"
            }
            mock_safety_cls.return_value = mock_safety

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                yield ac

    app.dependency_overrides.clear()
