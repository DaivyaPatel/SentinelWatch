"""
Test: Authentication endpoints.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_health_check():
    """Health endpoint should return 200 with status=healthy."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "uptime_seconds" in data


@pytest.mark.anyio
async def test_root():
    """Root endpoint should return welcome message."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "docs" in data


@pytest.mark.anyio
async def test_register_missing_fields():
    """Registration with missing fields should return 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register",
            json={"username": "test"},  # Missing email and password
        )
        assert response.status_code == 422


@pytest.mark.anyio
async def test_login_invalid_credentials():
    """Login with invalid credentials should return 400."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent", "password": "wrong"},
        )
        assert response.status_code == 400


@pytest.mark.anyio
async def test_protected_endpoint_no_token():
    """Accessing a protected endpoint without a token should return 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/drones")
        assert response.status_code == 401


@pytest.mark.anyio
async def test_drones_list_unauthorized():
    """Drones list without auth should return 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/drones")
        assert response.status_code == 401


@pytest.mark.anyio
async def test_incidents_list_unauthorized():
    """Incidents list without auth should return 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/incidents")
        assert response.status_code == 401
