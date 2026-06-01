"""Tracer bullet tests for Issue #1: Bootstrap local Smartshark workspace.

Proves the end-to-end path: admin seed -> login -> JWT -> role-based access.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_seeded_on_first_run(client: AsyncClient):
    """First-run seeds an admin account that can log in."""
    response = await client.post("/api/auth/login", json={
        "username": "admin",
        "password": "admin",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_admin_token_returns_admin_role(client: AsyncClient):
    """Admin JWT resolves to admin role via /me."""
    response = await client.post("/api/auth/login", json={
        "username": "admin",
        "password": "admin",
    })
    token = response.json()["access_token"]

    me = await client.get("/api/auth/me", headers={
        "Authorization": f"Bearer {token}",
    })
    assert me.status_code == 200
    assert me.json()["role"] == "admin"
    assert me.json()["username"] == "admin"


@pytest.mark.asyncio
async def test_admin_can_create_analyst(client: AsyncClient, admin_token: str):
    """Admin can create an Analyst Account."""
    response = await client.post(
        "/api/auth/analysts",
        json={"username": "alice", "password": "secret123"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "alice"
    assert data["role"] == "analyst"


@pytest.mark.asyncio
async def test_analyst_can_log_in(client: AsyncClient, admin_token: str):
    """Created analyst can authenticate and sees analyst role."""
    await client.post(
        "/api/auth/analysts",
        json={"username": "bob", "password": "pw"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    response = await client.post("/api/auth/login", json={
        "username": "bob",
        "password": "pw",
    })
    assert response.status_code == 200
    token = response.json()["access_token"]

    me = await client.get("/api/auth/me", headers={
        "Authorization": f"Bearer {token}",
    })
    assert me.json()["role"] == "analyst"


@pytest.mark.asyncio
async def test_analyst_cannot_access_admin_settings(client: AsyncClient, admin_token: str):
    """Permission checks prevent Analysts from entering Admin-only settings."""
    await client.post(
        "/api/auth/analysts",
        json={"username": "eve", "password": "pw"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    analyst_token = (await client.post("/api/auth/login", json={
        "username": "eve", "password": "pw",
    })).json()["access_token"]

    response = await client.get("/api/admin/ai-provider", headers={
        "Authorization": f"Bearer {analyst_token}",
    })
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_view_ai_provider_settings(client: AsyncClient, admin_token: str):
    """AI provider settings exist as an Admin-only configuration area."""
    response = await client.get("/api/admin/ai-provider", headers={
        "Authorization": f"Bearer {admin_token}",
    })
    assert response.status_code == 200
    data = response.json()
    assert "provider" in data
    assert "model" in data


@pytest.mark.asyncio
async def test_admin_can_update_ai_provider_settings(client: AsyncClient, admin_token: str):
    """Admin can update AI provider configuration."""
    response = await client.put("/api/admin/ai-provider", json={
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "api_key": "sk-test-key",
    }, headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "anthropic"
    assert data["model"] == "claude-sonnet-4-20250514"
    assert data["api_key_set"] is True


@pytest.mark.asyncio
async def test_invalid_login_rejected(client: AsyncClient):
    """Wrong credentials return 401."""
    response = await client.post("/api/auth/login", json={
        "username": "admin",
        "password": "wrong",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_duplicate_analyst_rejected(client: AsyncClient, admin_token: str):
    """Duplicate username returns 409."""
    await client.post(
        "/api/auth/analysts",
        json={"username": "dup", "password": "pw"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    response = await client.post(
        "/api/auth/analysts",
        json={"username": "dup", "password": "pw2"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 409
