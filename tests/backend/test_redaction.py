"""Tests for Issue #14: Raw-Context Exploration with Redaction Policy.

Covers:
- Admin can configure Redaction Policy and raw-context sharing mode
- Sensitive values are masked according to the policy before AI requests
- Analyst confirmation is required when raw sharing is allowed
- Verifone intelliNAC profile tightens payment-sensitive redaction
- Raw-context output cannot become Verified or Likely without tool-grounded evidence
"""

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Redaction Policy CRUD (admin only)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_default_redaction_policy(client: AsyncClient, admin_token: str):
    """Admin can get redaction policy with safe defaults."""
    resp = await client.get("/api/admin/redaction-policy", headers={
        "Authorization": f"Bearer {admin_token}",
    })
    assert resp.status_code == 200
    policy = resp.json()
    assert policy["mask_payloads"] is True
    assert policy["mask_credentials"] is True
    assert policy["mask_auth_headers"] is True
    assert policy["mask_pan_values"] is True
    assert policy["anonymize_ips"] is False
    assert policy["anonymize_macs"] is False
    assert policy["mask_dns_suffix"] is False
    assert policy["raw_sharing_allowed"] is False
    assert policy["profile"] == "general"


@pytest.mark.asyncio
async def test_admin_can_update_redaction_policy(client: AsyncClient, admin_token: str):
    """Admin can update redaction policy fields."""
    resp = await client.put("/api/admin/redaction-policy", json={
        "anonymize_ips": True,
        "raw_sharing_allowed": True,
    }, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    policy = resp.json()
    assert policy["anonymize_ips"] is True
    assert policy["raw_sharing_allowed"] is True
    # Non-updated fields retain defaults
    assert policy["mask_payloads"] is True


@pytest.mark.asyncio
async def test_analyst_cannot_access_redaction_policy(client: AsyncClient, admin_token: str):
    """Non-admin cannot read or update redaction policy."""
    # Create analyst
    await client.post("/api/auth/analysts", json={"username": "analyst1", "password": "pw"},
                      headers={"Authorization": f"Bearer {admin_token}"})
    analyst_token = (await client.post("/api/auth/login",
                      json={"username": "analyst1", "password": "pw"})).json()["access_token"]

    get_resp = await client.get("/api/admin/redaction-policy", headers={
        "Authorization": f"Bearer {analyst_token}",
    })
    assert get_resp.status_code == 403

    put_resp = await client.put("/api/admin/redaction-policy", json={"anonymize_ips": True},
                                headers={"Authorization": f"Bearer {analyst_token}"})
    assert put_resp.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_redaction_policy_rejected(client: AsyncClient):
    """Unauthenticated access to redaction policy is rejected."""
    get_resp = await client.get("/api/admin/redaction-policy")
    assert get_resp.status_code == 401

    put_resp = await client.put("/api/admin/redaction-policy", json={})
    assert put_resp.status_code == 401


# ---------------------------------------------------------------------------
# Redaction masking
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_payloads_masked_by_default(client: AsyncClient, admin_token: str):
    """Payloads are masked with [REDACTED PAYLOAD] when policy says so."""
    resp = await client.post("/api/raw-context/redact", json={
        "content": "GET /api HTTP/1.1\r\n\r\n{\"secret\": \"data\"}",
    }, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "[REDACTED PAYLOAD]" in data["redacted_content"]
    assert "{\"secret\": \"data\"}" not in data["redacted_content"]


@pytest.mark.asyncio
async def test_credentials_masked(client: AsyncClient, admin_token: str):
    """Credentials/tokens/cookies/API keys are masked."""
    content = "Authorization: Bearer sk-abc123\ntoken=xxyyzz\napi_key=mysecretkey\nCookie: session=abc123"
    resp = await client.post("/api/raw-context/redact", json={
        "content": content,
    }, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    redacted = resp.json()["redacted_content"]
    assert "sk-abc123" not in redacted
    assert "xxyyzz" not in redacted
    assert "mysecretkey" not in redacted
    assert "session=abc123" not in redacted


@pytest.mark.asyncio
async def test_auth_headers_masked(client: AsyncClient, admin_token: str):
    """Authorization headers are masked with [REDACTED AUTH]."""
    content = "Authorization: Basic dXNlcjpwYXNz"
    resp = await client.post("/api/raw-context/redact", json={
        "content": content,
    }, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    redacted = resp.json()["redacted_content"]
    assert "[REDACTED AUTH]" in redacted
    assert "dXNlcjpwYXNz" not in redacted


@pytest.mark.asyncio
async def test_pan_values_masked(client: AsyncClient, admin_token: str):
    """PAN/card-like 16-digit values are masked."""
    content = "Card number: 4111111111111111 and another 5500000000000004"
    resp = await client.post("/api/raw-context/redact", json={
        "content": content,
    }, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    redacted = resp.json()["redacted_content"]
    assert "[REDACTED PAN]" in redacted
    assert "4111111111111111" not in redacted
    assert "5500000000000004" not in redacted


@pytest.mark.asyncio
async def test_ip_anonymization_when_enabled(client: AsyncClient, admin_token: str):
    """IP addresses are anonymized when policy enables it."""
    # Enable IP anonymization
    await client.put("/api/admin/redaction-policy", json={"anonymize_ips": True},
                     headers={"Authorization": f"Bearer {admin_token}"})

    content = "Source: 192.168.1.1 -> Dest: 10.0.0.5"
    resp = await client.post("/api/raw-context/redact", json={
        "content": content,
    }, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    redacted = resp.json()["redacted_content"]
    assert "192.168.1.1" not in redacted
    assert "10.0.0.5" not in redacted
    assert "[IP-" in redacted


@pytest.mark.asyncio
async def test_ip_anonymization_off_by_default(client: AsyncClient, admin_token: str):
    """IP addresses are NOT anonymized when policy disables it (default)."""
    content = "Source: 192.168.1.1 -> Dest: 10.0.0.5"
    resp = await client.post("/api/raw-context/redact", json={
        "content": content,
    }, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    redacted = resp.json()["redacted_content"]
    assert "192.168.1.1" in redacted
    assert "10.0.0.5" in redacted


@pytest.mark.asyncio
async def test_mac_anonymization_when_enabled(client: AsyncClient, admin_token: str):
    """MAC addresses are anonymized when policy enables it."""
    await client.put("/api/admin/redaction-policy", json={"anonymize_macs": True},
                     headers={"Authorization": f"Bearer {admin_token}"})

    content = "MAC: aa:bb:cc:dd:ee:ff"
    resp = await client.post("/api/raw-context/redact", json={
        "content": content,
    }, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    redacted = resp.json()["redacted_content"]
    assert "aa:bb:cc:dd:ee:ff" not in redacted
    assert "[MAC-" in redacted


# ---------------------------------------------------------------------------
# Verifone intelliNAC profile
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verifone_profile_stricter_payment_masking(client: AsyncClient, admin_token: str):
    """Verifone intelliNAC profile adds stricter payment-sensitive redaction."""
    await client.put("/api/admin/redaction-policy", json={
        "profile": "verifone-intellinac",
    }, headers={"Authorization": f"Bearer {admin_token}"})

    # Payment terminal ID-like values should be masked under Verifone profile
    content = "Terminal ID: 12345678 PAN: 4111111111111111 Auth Code: AB12CD"
    resp = await client.post("/api/raw-context/redact", json={
        "content": content,
    }, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    redacted = resp.json()["redacted_content"]
    assert "[REDACTED PAN]" in redacted
    assert "12345678" not in redacted  # Terminal ID masked
    assert "AB12CD" not in redacted    # Auth code masked


# ---------------------------------------------------------------------------
# Raw-context sharing and submission
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_raw_sharing_disabled_by_default(client: AsyncClient, admin_token: str):
    """Raw-context submission is rejected when sharing is disabled."""
    resp = await client.post("/api/raw-context/submit", json={
        "content": "Some raw packet data",
        "context_category": "raw-context",
        "confirm_sharing": True,
    }, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 403
    assert "not allowed" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_analyst_raw_context_requires_confirmation(client: AsyncClient, admin_token: str):
    """Analyst must confirm sharing when raw sharing is enabled."""
    # Enable raw sharing
    await client.put("/api/admin/redaction-policy", json={"raw_sharing_allowed": True},
                     headers={"Authorization": f"Bearer {admin_token}"})

    # Submit without confirmation
    resp = await client.post("/api/raw-context/submit", json={
        "content": "Some raw packet data",
        "context_category": "raw-context",
        "confirm_sharing": False,
    }, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 400
    assert "confirmation" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_raw_context_submission_logs_ai_request(client: AsyncClient, admin_token: str):
    """Raw-context submission creates an AI request log entry."""
    # Enable raw sharing
    await client.put("/api/admin/redaction-policy", json={"raw_sharing_allowed": True},
                     headers={"Authorization": f"Bearer {admin_token}"})

    resp = await client.post("/api/raw-context/submit", json={
        "content": "GET /api HTTP/1.1\r\nAuthorization: Bearer secret",
        "context_category": "raw-context",
        "confirm_sharing": True,
    }, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["logged"] is True
    assert data["request_log_id"] is not None

    # Verify log entry is visible
    log_resp = await client.get("/api/admin/ai-request-log", headers={
        "Authorization": f"Bearer {admin_token}",
    })
    assert log_resp.status_code == 200
    logs = log_resp.json()
    assert len(logs) >= 1
    entry = logs[-1]
    assert entry["context_category"] == "raw-context"
    assert entry["redacted"] is True


@pytest.mark.asyncio
async def test_raw_context_output_marked_exploratory(client: AsyncClient, admin_token: str):
    """Raw-context output is marked exploratory — cannot be verified/likely."""
    await client.put("/api/admin/redaction-policy", json={"raw_sharing_allowed": True},
                     headers={"Authorization": f"Bearer {admin_token}"})

    resp = await client.post("/api/raw-context/submit", json={
        "content": "Packet shows TCP retransmission",
        "context_category": "raw-context",
        "confirm_sharing": True,
    }, headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["exploratory"] is True
    assert "must be verified" in data["warning"].lower()


# ---------------------------------------------------------------------------
# AI Request Log (admin only)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ai_request_log_admin_only(client: AsyncClient, admin_token: str):
    """AI request log is only visible to admin."""
    # Create analyst
    await client.post("/api/auth/analysts", json={"username": "logviewer", "password": "pw"},
                      headers={"Authorization": f"Bearer {admin_token}"})
    analyst_token = (await client.post("/api/auth/login",
                      json={"username": "logviewer", "password": "pw"})).json()["access_token"]

    resp = await client.get("/api/admin/ai-request-log", headers={
        "Authorization": f"Bearer {analyst_token}",
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_raw_context_rejected(client: AsyncClient):
    """Unauthenticated raw-context submission is rejected."""
    resp = await client.post("/api/raw-context/submit", json={
        "content": "data",
        "context_category": "raw-context",
        "confirm_sharing": True,
    })
    assert resp.status_code == 401

    resp2 = await client.post("/api/raw-context/redact", json={"content": "data"})
    assert resp2.status_code == 401
