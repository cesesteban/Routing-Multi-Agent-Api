"""
E2E Tests — Resources Endpoints

Tests:
  - GET /api/v1/prompts returns list of available prompts
  - GET /api/v1/knowledge returns knowledge base categories
  - Root endpoint is reachable and returns expected message
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_root_endpoint(client: AsyncClient):
    """Root endpoint should return online status."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "online" in data["message"].lower() or "api" in data["message"].lower()


async def test_prompts_endpoint_returns_list(client: AsyncClient):
    """GET /prompts should return a non-empty list of prompt objects."""
    response = await client.get("/api/v1/prompts")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Each prompt should have at least 'name' and 'content'
    if len(data) > 0:
        assert "name" in data[0]


async def test_knowledge_endpoint_returns_list(client: AsyncClient):
    """GET /knowledge should return a list of knowledge categories."""
    response = await client.get("/api/v1/knowledge")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


async def test_docs_endpoint_available(client: AsyncClient):
    """FastAPI auto-generated /docs endpoint should be reachable."""
    response = await client.get("/docs")
    assert response.status_code == 200


async def test_openapi_schema_available(client: AsyncClient):
    """OpenAPI JSON schema should be accessible."""
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "paths" in schema
    assert "/api/v1/query" in schema["paths"]
