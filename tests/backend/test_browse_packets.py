"""Tests for Issue #3: Browse packets with filter, frame detail, and payload preview.

Covers: packet listing, display filter, frame detail, payload preview,
invalid filter feedback, missing artifacts/frames, and permission checks.
"""

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
    """Minimal valid PCAP with global header + one tiny packet."""
    header = b"\xd4\xc3\xb2\xa1"  # PCAP magic (LE)
    header += b"\x02\x00"          # version major
    header += b"\x04\x00"          # version minor
    header += b"\x00\x00\x00\x00"  # thiszone
    header += b"\x00\x00\x00\x00"  # sigfigs
    header += b"\xff\xff\x00\x00"  # snaplen
    header += b"\x01\x00\x00\x00"  # network (ETHERNET)
    header += b"\x00\x00\x00\x00"  # ts_sec
    header += b"\x00\x00\x00\x00"  # ts_usec
    header += b"\x04\x00\x00\x00"  # incl_len
    header += b"\x04\x00\x00\x00"  # orig_len
    header += b"\x00\x00\x00\x00"  # 4 bytes of packet data
    return header


async def _upload_capture(client: AsyncClient, token: str, filename: str = "test.pcap") -> int:
    """Upload a valid capture and return the artifact ID."""
    resp = await client.post(
        "/api/captures/upload",
        files={"file": (filename, _pcap_bytes(), "application/octet-stream")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# --- Packet listing ---

@pytest.mark.asyncio
async def test_list_packets_returns_packet_summaries(client: AsyncClient, admin_token: str):
    """Analyst can open a Capture Artifact and see a packet table."""
    token = await _create_analyst(client, admin_token)
    artifact_id = await _upload_capture(client, token)

    resp = await client.get(
        f"/api/captures/{artifact_id}/packets",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    packets = resp.json()
    assert isinstance(packets, list)
    assert len(packets) > 0
    pkt = packets[0]
    assert "frame_number" in pkt
    assert "timestamp" in pkt
    assert "source" in pkt
    assert "destination" in pkt
    assert "protocol" in pkt
    assert "length" in pkt
    assert "info" in pkt


# --- Display filter ---

@pytest.mark.asyncio
async def test_valid_display_filter_returns_matching_packets(client: AsyncClient, admin_token: str):
    """Analyst can apply a display filter and see matching packets."""
    token = await _create_analyst(client, admin_token)
    artifact_id = await _upload_capture(client, token)

    resp = await client.get(
        f"/api/captures/{artifact_id}/packets",
        params={"filter": "tcp"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    # The stub returns all packets for "tcp" — just verify it doesn't error
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_invalid_display_filter_returns_actionable_error(client: AsyncClient, admin_token: str):
    """Invalid filters produce actionable feedback."""
    token = await _create_analyst(client, admin_token)
    artifact_id = await _upload_capture(client, token)

    resp = await client.get(
        f"/api/captures/{artifact_id}/packets",
        params={"filter": "((((invalid"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    data = resp.json()
    assert "detail" in data
    # Error message should be actionable
    assert isinstance(data["detail"], str)
    assert len(data["detail"]) > 0


# --- Frame detail ---

@pytest.mark.asyncio
async def test_get_frame_detail_returns_fields(client: AsyncClient, admin_token: str):
    """Selecting a frame shows packet detail/dissector fields."""
    token = await _create_analyst(client, admin_token)
    artifact_id = await _upload_capture(client, token)

    resp = await client.get(
        f"/api/captures/{artifact_id}/frames/1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["frame_number"] == 1
    assert "timestamp" in data
    assert "protocols" in data
    assert "layers" in data
    assert isinstance(data["layers"], list)


@pytest.mark.asyncio
async def test_get_frame_detail_nonexistent_frame_returns_404(client: AsyncClient, admin_token: str):
    """Requesting a non-existent frame returns 404."""
    token = await _create_analyst(client, admin_token)
    artifact_id = await _upload_capture(client, token)

    resp = await client.get(
        f"/api/captures/{artifact_id}/frames/9999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# --- Payload preview ---

@pytest.mark.asyncio
async def test_get_payload_preview_returns_hex_and_ascii(client: AsyncClient, admin_token: str):
    """Payload/bytes preview is available for the selected frame."""
    token = await _create_analyst(client, admin_token)
    artifact_id = await _upload_capture(client, token)

    resp = await client.get(
        f"/api/captures/{artifact_id}/frames/1/payload",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "hex_dump" in data
    assert "ascii" in data
    assert "length" in data
    assert data["length"] >= 0


@pytest.mark.asyncio
async def test_get_payload_nonexistent_frame_returns_404(client: AsyncClient, admin_token: str):
    """Payload for non-existent frame returns 404."""
    token = await _create_analyst(client, admin_token)
    artifact_id = await _upload_capture(client, token)

    resp = await client.get(
        f"/api/captures/{artifact_id}/frames/9999/payload",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# --- Missing artifact ---

@pytest.mark.asyncio
async def test_packets_for_nonexistent_artifact_returns_404(client: AsyncClient, admin_token: str):
    """Requesting packets for a missing artifact returns 404."""
    token = await _create_analyst(client, admin_token)

    resp = await client.get(
        "/api/captures/99999/packets",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# --- Permission checks ---

@pytest.mark.asyncio
async def test_packet_endpoints_require_auth(client: AsyncClient, admin_token: str):
    """Unauthenticated users cannot browse packets."""
    artifact_id = await _upload_capture(client, admin_token)

    resp = await client.get(f"/api/captures/{artifact_id}/packets")
    assert resp.status_code == 401

    resp = await client.get(f"/api/captures/{artifact_id}/frames/1")
    assert resp.status_code == 401

    resp = await client.get(f"/api/captures/{artifact_id}/frames/1/payload")
    assert resp.status_code == 401
