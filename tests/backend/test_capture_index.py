"""Tests for Issue #5: Add Capture Index pre-scan and timeline metrics.

Covers: index creation with protocol mix/endpoints/time range, timeline metrics
(packets/sec, bytes/sec, TCP retransmissions, TCP resets, DNS activity),
Pre-Scan summary, 404 handling, and permission checks.
"""

import io
import pytest
from httpx import AsyncClient


# --- Helpers ---

async def _create_analyst(client: AsyncClient, admin_token: str, username: str = "analyst1", password: str = "pw") -> str:
    """Create an analyst and return their token."""
    await client.post(
        "/api/auth/analysts",
        json={"username": username, "password": password},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    resp = await client.post("/api/auth/login", json={"username": username, "password": password})
    return resp.json()["access_token"]


def _pcap_bytes() -> bytes:
    """Minimal valid PCAP content."""
    header = b"\xd4\xc3\xb2\xa1"
    header += b"\x02\x00\x04\x00"
    header += b"\x00\x00\x00\x00"
    header += b"\x00\x00\x00\x00"
    header += b"\xff\xff\x00\x00"
    header += b"\x01\x00\x00\x00"
    header += b"\x00\x00\x00\x00"
    header += b"\x00\x00\x00\x00"
    header += b"\x04\x00\x00\x00"
    header += b"\x04\x00\x00\x00"
    header += b"\x00\x00\x00\x00"
    return header


async def _upload_artifact(client: AsyncClient, token: str) -> int:
    """Upload a valid PCAP and return the artifact ID."""
    resp = await client.post(
        "/api/captures/upload",
        files={"file": ("test.pcap", _pcap_bytes(), "application/octet-stream")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201)
    return resp.json()["id"]


# --- Index creation tests ---

@pytest.mark.asyncio
async def test_create_index_records_protocol_mix(client: AsyncClient, admin_token: str):
    """Capture Index records protocol mix."""
    token = await _create_analyst(client, admin_token)
    artifact_id = await _upload_artifact(client, token)

    resp = await client.post(
        f"/api/captures/{artifact_id}/index",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "protocol_mix" in data
    # Stub data has TCP, HTTP, DNS
    protocols = data["protocol_mix"]
    assert "TCP" in protocols
    assert "DNS" in protocols


@pytest.mark.asyncio
async def test_create_index_records_endpoints(client: AsyncClient, admin_token: str):
    """Capture Index records top endpoints."""
    token = await _create_analyst(client, admin_token)
    artifact_id = await _upload_artifact(client, token)

    resp = await client.post(
        f"/api/captures/{artifact_id}/index",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "top_endpoints" in data
    assert len(data["top_endpoints"]) > 0
    # Stub data includes 192.168.1.1, 192.168.1.2, 8.8.8.8
    endpoints = data["top_endpoints"]
    ips = [e["address"] for e in endpoints]
    assert "192.168.1.1" in ips


@pytest.mark.asyncio
async def test_create_index_records_time_range(client: AsyncClient, admin_token: str):
    """Capture Index records time range (start and end)."""
    token = await _create_analyst(client, admin_token)
    artifact_id = await _upload_artifact(client, token)

    resp = await client.post(
        f"/api/captures/{artifact_id}/index",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["time_range_start"] is not None
    assert data["time_range_end"] is not None
    assert data["total_packets"] > 0
    assert data["total_bytes"] > 0


@pytest.mark.asyncio
async def test_create_index_records_conversations(client: AsyncClient, admin_token: str):
    """Capture Index records conversations count."""
    token = await _create_analyst(client, admin_token)
    artifact_id = await _upload_artifact(client, token)

    resp = await client.post(
        f"/api/captures/{artifact_id}/index",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["conversations_count"] > 0


# --- Timeline tests ---

@pytest.mark.asyncio
async def test_timeline_shows_packets_per_second(client: AsyncClient, admin_token: str):
    """Timeline shows packets per second."""
    token = await _create_analyst(client, admin_token)
    artifact_id = await _upload_artifact(client, token)

    # First create the index
    await client.post(
        f"/api/captures/{artifact_id}/index",
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        f"/api/captures/{artifact_id}/timeline",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    buckets = resp.json()
    assert len(buckets) > 0
    assert "packets_per_sec" in buckets[0]
    assert buckets[0]["packets_per_sec"] > 0


@pytest.mark.asyncio
async def test_timeline_shows_bytes_per_second(client: AsyncClient, admin_token: str):
    """Timeline shows bytes per second."""
    token = await _create_analyst(client, admin_token)
    artifact_id = await _upload_artifact(client, token)

    await client.post(
        f"/api/captures/{artifact_id}/index",
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        f"/api/captures/{artifact_id}/timeline",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    buckets = resp.json()
    assert "bytes_per_sec" in buckets[0]
    assert buckets[0]["bytes_per_sec"] > 0


@pytest.mark.asyncio
async def test_timeline_shows_tcp_retransmissions(client: AsyncClient, admin_token: str):
    """Timeline shows TCP retransmissions when present."""
    token = await _create_analyst(client, admin_token)
    artifact_id = await _upload_artifact(client, token)

    await client.post(
        f"/api/captures/{artifact_id}/index",
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        f"/api/captures/{artifact_id}/timeline",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    buckets = resp.json()
    # Stub data includes TCP retransmissions
    assert "tcp_retransmissions" in buckets[0]


@pytest.mark.asyncio
async def test_timeline_shows_tcp_resets(client: AsyncClient, admin_token: str):
    """Timeline shows TCP resets when present."""
    token = await _create_analyst(client, admin_token)
    artifact_id = await _upload_artifact(client, token)

    await client.post(
        f"/api/captures/{artifact_id}/index",
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        f"/api/captures/{artifact_id}/timeline",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    buckets = resp.json()
    assert "tcp_resets" in buckets[0]


@pytest.mark.asyncio
async def test_timeline_shows_dns_activity(client: AsyncClient, admin_token: str):
    """Timeline shows DNS query/response/timeout activity when present."""
    token = await _create_analyst(client, admin_token)
    artifact_id = await _upload_artifact(client, token)

    await client.post(
        f"/api/captures/{artifact_id}/index",
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        f"/api/captures/{artifact_id}/timeline",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    buckets = resp.json()
    assert "dns_queries" in buckets[0]
    assert "dns_responses" in buckets[0]
    assert "dns_timeouts" in buckets[0]
    # Stub data has 1 query and 1 response
    total_queries = sum(b["dns_queries"] for b in buckets)
    total_responses = sum(b["dns_responses"] for b in buckets)
    assert total_queries > 0
    assert total_responses > 0


# --- Pre-Scan summary ---

@pytest.mark.asyncio
async def test_prescan_summary_available(client: AsyncClient, admin_token: str):
    """Pre-Scan summary is available for analysis modes."""
    token = await _create_analyst(client, admin_token)
    artifact_id = await _upload_artifact(client, token)

    await client.post(
        f"/api/captures/{artifact_id}/index",
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = await client.get(
        f"/api/captures/{artifact_id}/prescan",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "protocol_mix" in data
    assert "top_endpoints" in data
    assert "conversations_count" in data
    assert "time_range_start" in data
    assert "time_range_end" in data
    assert "total_packets" in data
    assert "total_bytes" in data
    assert "summary" in data


# --- Get existing index ---

@pytest.mark.asyncio
async def test_get_index_returns_stored_data(client: AsyncClient, admin_token: str):
    """GET index after creation returns the same data."""
    token = await _create_analyst(client, admin_token)
    artifact_id = await _upload_artifact(client, token)

    create_resp = await client.post(
        f"/api/captures/{artifact_id}/index",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_resp.status_code == 201

    get_resp = await client.get(
        f"/api/captures/{artifact_id}/index",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == create_resp.json()["id"]


# --- Error cases ---

@pytest.mark.asyncio
async def test_index_for_nonexistent_artifact_returns_404(client: AsyncClient, admin_token: str):
    """Indexing a non-existent artifact returns 404."""
    token = await _create_analyst(client, admin_token)

    resp = await client.post(
        "/api/captures/99999/index",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_timeline_without_index_returns_404(client: AsyncClient, admin_token: str):
    """Requesting timeline before indexing returns 404."""
    token = await _create_analyst(client, admin_token)
    artifact_id = await _upload_artifact(client, token)

    resp = await client.get(
        f"/api/captures/{artifact_id}/timeline",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_prescan_without_index_returns_404(client: AsyncClient, admin_token: str):
    """Requesting prescan before indexing returns 404."""
    token = await _create_analyst(client, admin_token)
    artifact_id = await _upload_artifact(client, token)

    resp = await client.get(
        f"/api/captures/{artifact_id}/prescan",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# --- Permission checks ---

@pytest.mark.asyncio
async def test_unauthenticated_index_rejected(client: AsyncClient):
    """Unauthenticated users cannot create an index."""
    resp = await client.post("/api/captures/1/index")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthenticated_timeline_rejected(client: AsyncClient):
    """Unauthenticated users cannot access timeline."""
    resp = await client.get("/api/captures/1/timeline")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthenticated_prescan_rejected(client: AsyncClient):
    """Unauthenticated users cannot access prescan."""
    resp = await client.get("/api/captures/1/prescan")
    assert resp.status_code == 401
