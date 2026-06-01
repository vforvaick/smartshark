"""Tests for Issue #4: Build conversations, follow-stream, and flow navigation.

Covers: conversation listing, conversation packet subset, follow-stream
with frame references, unsupported stream types, missing artifacts, and
permission checks.
"""

import pytest
from httpx import AsyncClient


# --- Helpers ---

async def _create_analyst(
    client: AsyncClient,
    admin_token: str,
    username: str = "analyst1",
    password: str = "pw",
) -> str:
    """Create an analyst and return their token."""
    await client.post(
        "/api/auth/analysts",
        json={"username": username, "password": password},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    resp = await client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
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


async def _upload_capture(
    client: AsyncClient, token: str, filename: str = "test.pcap"
) -> int:
    """Upload a valid capture and return the artifact ID."""
    resp = await client.post(
        "/api/captures/upload",
        files={"file": (filename, _pcap_bytes(), "application/octet-stream")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# --- Conversation listing ---


@pytest.mark.asyncio
async def test_list_conversations_returns_flows(
    client: AsyncClient, admin_token: str
):
    """Analyst can view conversations/flows for a Capture Artifact."""
    token = await _create_analyst(client, admin_token)
    artifact_id = await _upload_capture(client, token)

    resp = await client.get(
        f"/api/captures/{artifact_id}/conversations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    conversations = resp.json()
    assert isinstance(conversations, list)
    assert len(conversations) > 0

    conv = conversations[0]
    assert "id" in conv
    assert "src_addr" in conv
    assert "src_port" in conv
    assert "dst_addr" in conv
    assert "dst_port" in conv
    assert "protocol" in conv
    assert "packet_count" in conv
    assert "byte_count" in conv


# --- Conversation packet subset ---


@pytest.mark.asyncio
async def test_select_conversation_returns_packet_subset(
    client: AsyncClient, admin_token: str
):
    """Selecting a conversation opens its packet subset."""
    token = await _create_analyst(client, admin_token)
    artifact_id = await _upload_capture(client, token)

    # Get conversations first
    convs_resp = await client.get(
        f"/api/captures/{artifact_id}/conversations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert convs_resp.status_code == 200
    conversations = convs_resp.json()
    assert len(conversations) > 0

    conv_id = conversations[0]["id"]

    # Get packets for that conversation
    packets_resp = await client.get(
        f"/api/captures/{artifact_id}/conversations/{conv_id}/packets",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert packets_resp.status_code == 200
    packets = packets_resp.json()
    assert isinstance(packets, list)
    assert len(packets) > 0
    # Every packet should have the standard fields
    pkt = packets[0]
    assert "frame_number" in pkt
    assert "source" in pkt
    assert "destination" in pkt
    assert "protocol" in pkt


# --- Follow TCP stream ---


@pytest.mark.asyncio
async def test_follow_tcp_stream_returns_segments_with_frame_refs(
    client: AsyncClient, admin_token: str
):
    """Analyst can follow a supported stream from a packet or flow."""
    token = await _create_analyst(client, admin_token)
    artifact_id = await _upload_capture(client, token)

    resp = await client.post(
        f"/api/captures/{artifact_id}/follow-stream",
        json={"stream_index": 0, "stream_type": "tcp"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "stream_type" in data
    assert data["stream_type"] == "tcp"
    assert "segments" in data
    assert isinstance(data["segments"], list)
    assert len(data["segments"]) > 0

    seg = data["segments"][0]
    assert "direction" in seg
    assert "data" in seg
    assert "frame_numbers" in seg
    assert isinstance(seg["frame_numbers"], list)
    assert len(seg["frame_numbers"]) > 0


@pytest.mark.asyncio
async def test_follow_stream_output_links_back_to_frames(
    client: AsyncClient, admin_token: str
):
    """Follow-stream output links back to relevant frames."""
    token = await _create_analyst(client, admin_token)
    artifact_id = await _upload_capture(client, token)

    resp = await client.post(
        f"/api/captures/{artifact_id}/follow-stream",
        json={"stream_index": 0, "stream_type": "tcp"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    # Collect all frame numbers from segments
    all_frame_numbers = []
    for seg in data["segments"]:
        all_frame_numbers.extend(seg["frame_numbers"])

    assert len(all_frame_numbers) > 0

    # Each referenced frame should be resolvable via the frame detail endpoint
    for frame_num in all_frame_numbers:
        frame_resp = await client.get(
            f"/api/captures/{artifact_id}/frames/{frame_num}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert frame_resp.status_code == 200, (
            f"Frame {frame_num} referenced by stream but not found"
        )


# --- Unsupported stream type ---


@pytest.mark.asyncio
async def test_unsupported_stream_type_fails_gracefully(
    client: AsyncClient, admin_token: str
):
    """Unsupported stream types fail gracefully."""
    token = await _create_analyst(client, admin_token)
    artifact_id = await _upload_capture(client, token)

    resp = await client.post(
        f"/api/captures/{artifact_id}/follow-stream",
        json={"stream_index": 0, "stream_type": "sctp"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    data = resp.json()
    assert "detail" in data
    assert "sctp" in data["detail"].lower() or "unsupported" in data["detail"].lower()


# --- Missing conversation ---


@pytest.mark.asyncio
async def test_conversation_packets_for_invalid_conv_id_returns_404(
    client: AsyncClient, admin_token: str
):
    """Requesting packets for a non-existent conversation returns 404."""
    token = await _create_analyst(client, admin_token)
    artifact_id = await _upload_capture(client, token)

    resp = await client.get(
        f"/api/captures/{artifact_id}/conversations/999/packets",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# --- Missing artifact ---


@pytest.mark.asyncio
async def test_conversations_for_nonexistent_artifact_returns_404(
    client: AsyncClient, admin_token: str
):
    """Conversations for a non-existent artifact returns 404."""
    token = await _create_analyst(client, admin_token)

    resp = await client.get(
        "/api/captures/99999/conversations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# --- Unauthenticated access ---


@pytest.mark.asyncio
async def test_conversation_endpoints_require_auth(
    client: AsyncClient, admin_token: str
):
    """Unauthenticated users cannot access conversation endpoints."""
    artifact_id = await _upload_capture(client, admin_token)

    resp = await client.get(f"/api/captures/{artifact_id}/conversations")
    assert resp.status_code == 401

    resp = await client.get(
        f"/api/captures/{artifact_id}/conversations/0/packets"
    )
    assert resp.status_code == 401

    resp = await client.post(
        f"/api/captures/{artifact_id}/follow-stream",
        json={"stream_index": 0, "stream_type": "tcp"},
    )
    assert resp.status_code == 401
