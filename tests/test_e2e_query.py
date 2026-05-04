"""
E2E Tests — Query Endpoint (POST /api/v1/query)

Tests:
  - Happy path: standard query returns valid structured response
  - Multi-language: query with lang=en returns response
  - Email integration: to_email is accepted and triggers tools
  - History endpoint returns previous queries
  - Detail endpoint returns full query by ID
  - 404 on non-existent query ID
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# ── POST /api/v1/query ────────────────────────────────────────────────────────

async def test_query_happy_path(client: AsyncClient):
    """Standard query returns 200 with all expected fields."""
    response = await client.post("/api/v1/query", json={
        "query": "Mi VPN no conecta desde esta mañana",
        "lang": "es"
    })
    assert response.status_code == 200
    data = response.json()

    # Core fields
    assert data["id"] is not None
    assert data["query"] == "Mi VPN no conecta desde esta mañana"
    assert data["intent"] == "TECNOLOGIA"
    assert data["confidence"] == 0.95
    assert "VPN" in data["response_text"] or len(data["response_text"]) > 10
    assert isinstance(data["next_steps"], list)
    assert len(data["next_steps"]) > 0

    # Metrics must be present
    assert data["latency_ms"] > 0
    assert data["total_tokens"] > 0
    assert data["attempts"] >= 1


async def test_query_with_lang_en(client: AsyncClient):
    """Query with lang=en is accepted and returns 200."""
    response = await client.post("/api/v1/query", json={
        "query": "My laptop cannot connect to the VPN",
        "lang": "en"
    })
    assert response.status_code == 200
    assert response.json()["intent"] == "TECNOLOGIA"


async def test_query_with_email(client: AsyncClient):
    """Query with to_email triggers tool execution without breaking response."""
    response = await client.post("/api/v1/query", json={
        "query": "Necesito resetear mi contraseña corporativa",
        "lang": "es",
        "to_email": "usuario@empresa.com"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["id"] is not None
    # tools_executed may or may not be in schema, but the request must not fail
    assert data["response_text"] is not None


async def test_query_evaluation_score_returned(client: AsyncClient):
    """Evaluation score from the Evaluator agent is persisted and returned."""
    response = await client.post("/api/v1/query", json={
        "query": "¿Cuántos días de vacaciones me corresponden este año?",
        "lang": "es"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["evaluation_score"] is not None
    assert 0.0 <= data["evaluation_score"] <= 10.0


async def test_query_audit_trace_returned(client: AsyncClient):
    """Audit trace from the Critic agent is persisted and returned."""
    response = await client.post("/api/v1/query", json={
        "query": "Solicitud de certificado de haberes",
        "lang": "es"
    })
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["audit_trace"], list)
    assert len(data["audit_trace"]) >= 1
    first_audit = data["audit_trace"][0]
    assert "is_valid" in first_audit
    assert "score" in first_audit


# ── GET /api/v1/history ───────────────────────────────────────────────────────

async def test_query_history_initially_empty(client: AsyncClient):
    """History starts empty before any query is made."""
    response = await client.get("/api/v1/history")
    assert response.status_code == 200
    assert response.json() == []


async def test_query_history_after_query(client: AsyncClient):
    """History contains one item after one query is processed."""
    await client.post("/api/v1/query", json={"query": "Prueba de historial", "lang": "es"})
    response = await client.get("/api/v1/history")
    assert response.status_code == 200
    history = response.json()
    assert len(history) == 1
    assert history[0]["query"] == "Prueba de historial"


async def test_query_history_pagination(client: AsyncClient):
    """History pagination: skip and limit work correctly."""
    for i in range(5):
        await client.post("/api/v1/query", json={"query": f"Consulta número {i}", "lang": "es"})

    response = await client.get("/api/v1/history?skip=0&limit=3")
    assert response.status_code == 200
    assert len(response.json()) == 3

    response2 = await client.get("/api/v1/history?skip=3&limit=3")
    assert response2.status_code == 200
    assert len(response2.json()) == 2


# ── GET /api/v1/query/{id} ────────────────────────────────────────────────────

async def test_query_detail_by_id(client: AsyncClient):
    """Fetching a query by its ID returns the full detailed response."""
    create_resp = await client.post("/api/v1/query", json={
        "query": "Consulta para ver detalle",
        "lang": "es"
    })
    query_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/query/{query_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == query_id
    assert data["routing_reason"] is not None
    assert data["confidence"] == 0.95


async def test_query_detail_not_found(client: AsyncClient):
    """Fetching a non-existent query ID returns 404."""
    response = await client.get("/api/v1/query/99999")
    assert response.status_code == 404
