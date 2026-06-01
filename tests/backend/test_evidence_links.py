"""Evidence Links and deep-link resolver — Issue #10.

Tests verify:
- Evidence Links can be created for all target types
- Evidence Links resolve to target data
- Unavailable targets show clear states
- Portable citations are generated
- Batch resolve works
- Auth is required
"""

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_artifact(client: AsyncClient, admin_token: str) -> int:
    """Upload a minimal valid PCAP and return the artifact id."""
    pcap_magic = b"\xd4\xc3\xb2\xa1" + b"\x00" * 60
    resp = await client.post(
        "/api/captures/upload",
        files={"file": ("test.pcap", pcap_magic, "application/octet-stream")},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_link(client: AsyncClient, admin_token: str, target_type: str,
                       artifact_id: int | None = None, target_params: dict | None = None) -> dict:
    body: dict = {"target_type": target_type}
    if artifact_id is not None:
        body["artifact_id"] = artifact_id
    if target_params is not None:
        body["target_params"] = target_params
    resp = await client.post(
        "/api/evidence-links",
        json=body,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# 1. Create Evidence Links for each target type
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_evidence_link_for_packet_subset(
    client: AsyncClient, admin_token: str
):
    """Evidence Link for packet subset with optional filter."""
    artifact_id = await _create_artifact(client, admin_token)
    link = await _create_link(
        client, admin_token, "packets", artifact_id,
        {"filter": "tcp.port == 80"},
    )
    assert link["target_type"] == "packets"
    assert link["artifact_id"] == artifact_id
    assert link["target_params"]["filter"] == "tcp.port == 80"
    assert link["citation_text"] is not None
    assert "tcp.port == 80" in link["citation_text"]


@pytest.mark.asyncio
async def test_create_evidence_link_for_frame_detail(
    client: AsyncClient, admin_token: str
):
    """Evidence Link for a single frame."""
    artifact_id = await _create_artifact(client, admin_token)
    link = await _create_link(
        client, admin_token, "frame", artifact_id,
        {"frame_number": 42},
    )
    assert link["target_type"] == "frame"
    assert link["target_params"]["frame_number"] == 42
    assert "Frame 42" in link["citation_text"]


@pytest.mark.asyncio
async def test_create_evidence_link_for_flow(
    client: AsyncClient, admin_token: str
):
    """Evidence Link for a conversation/flow."""
    artifact_id = await _create_artifact(client, admin_token)
    link = await _create_link(
        client, admin_token, "flow", artifact_id,
        {"conv_id": 1},
    )
    assert link["target_type"] == "flow"
    assert "Flow 1" in link["citation_text"]


@pytest.mark.asyncio
async def test_create_evidence_link_for_follow_stream(
    client: AsyncClient, admin_token: str
):
    """Evidence Link for a followed stream."""
    artifact_id = await _create_artifact(client, admin_token)
    link = await _create_link(
        client, admin_token, "stream", artifact_id,
        {"stream_index": 0, "protocol": "TCP"},
    )
    assert link["target_type"] == "stream"
    assert "TCP stream" in link["citation_text"]


@pytest.mark.asyncio
async def test_create_evidence_link_for_timeline_window(
    client: AsyncClient, admin_token: str
):
    """Evidence Link for a timeline window."""
    artifact_id = await _create_artifact(client, admin_token)
    link = await _create_link(
        client, admin_token, "timeline", artifact_id,
        {"time_start": 0.0, "time_end": 5.0},
    )
    assert link["target_type"] == "timeline"
    assert "0.0" in link["citation_text"]
    assert "5.0" in link["citation_text"]


@pytest.mark.asyncio
async def test_create_evidence_link_for_graph_edge(
    client: AsyncClient, admin_token: str
):
    """Evidence Link for a graph edge."""
    artifact_id = await _create_artifact(client, admin_token)
    link = await _create_link(
        client, admin_token, "graph_edge", artifact_id,
        {"edge_id": 1},
    )
    assert link["target_type"] == "graph_edge"
    assert "Graph edge 1" in link["citation_text"]


@pytest.mark.asyncio
async def test_create_evidence_link_for_claim(
    client: AsyncClient, admin_token: str
):
    """Evidence Link for a claim."""
    link = await _create_link(
        client, admin_token, "claim", None,
        {"claim_id": 7},
    )
    assert link["target_type"] == "claim"
    assert "Claim 7" in link["citation_text"]


# ---------------------------------------------------------------------------
# 2. Resolve Evidence Links
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_link_returns_target_data(
    client: AsyncClient, admin_token: str
):
    """Resolving a link returns the target type and params."""
    artifact_id = await _create_artifact(client, admin_token)
    link = await _create_link(
        client, admin_token, "frame", artifact_id,
        {"frame_number": 5},
    )
    link_id = link["id"]

    resp = await client.get(
        f"/api/evidence-links/{link_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["resolved"] is True
    assert data["resolution_data"]["target_type"] == "frame"
    assert data["resolution_data"]["frame_number"] == 5
    assert data["deep_link"].startswith("smartshark://")


# ---------------------------------------------------------------------------
# 3. Unavailable targets
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unavailable_artifact_shows_deleted_state(
    client: AsyncClient, admin_token: str
):
    """Link to non-existent artifact shows deleted unavailability."""
    link = await _create_link(
        client, admin_token, "frame", 9999,
        {"frame_number": 1},
    )
    link_id = link["id"]

    resp = await client.get(
        f"/api/evidence-links/{link_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["resolved"] is False
    assert data["resolution_data"]["unavailability_reason"] == "deleted"


@pytest.mark.asyncio
async def test_missing_index_shows_unavailable_state(
    client: AsyncClient, admin_token: str
):
    """Link to artifact without capture index shows missing_index for timeline."""
    artifact_id = await _create_artifact(client, admin_token)
    link = await _create_link(
        client, admin_token, "timeline", artifact_id,
        {"time_start": 0.0, "time_end": 5.0},
    )
    link_id = link["id"]

    resp = await client.get(
        f"/api/evidence-links/{link_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["resolved"] is False
    assert data["resolution_data"]["unavailability_reason"] == "missing_index"


# ---------------------------------------------------------------------------
# 4. Portable citation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portable_citation_is_generated(
    client: AsyncClient, admin_token: str
):
    """Reportable evidence links have portable textual citations."""
    artifact_id = await _create_artifact(client, admin_token)
    link = await _create_link(
        client, admin_token, "packets", artifact_id,
        {"filter": "dns"},
    )
    link_id = link["id"]

    resp = await client.get(
        f"/api/evidence-links/{link_id}/citation",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert "dns" in resp.json()["citation"]


# ---------------------------------------------------------------------------
# 5. Batch resolve
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_batch_resolve_works(
    client: AsyncClient, admin_token: str
):
    """Batch resolve returns resolutions for all valid link IDs."""
    artifact_id = await _create_artifact(client, admin_token)
    link1 = await _create_link(
        client, admin_token, "frame", artifact_id,
        {"frame_number": 1},
    )
    link2 = await _create_link(
        client, admin_token, "flow", artifact_id,
        {"conv_id": 2},
    )

    resp = await client.post(
        "/api/evidence-links/batch-resolve",
        json={"link_ids": [link1["id"], link2["id"], 9999]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    # Non-existent ID 9999 is skipped, so only 2 resolutions
    assert len(data["resolutions"]) == 2


# ---------------------------------------------------------------------------
# 6. Auth guard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unauthenticated_create_rejected(client: AsyncClient):
    resp = await client.post(
        "/api/evidence-links",
        json={"target_type": "packets", "target_params": {}},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthenticated_resolve_rejected(client: AsyncClient):
    resp = await client.get("/api/evidence-links/1")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_resolve_nonexistent_link_returns_404(
    client: AsyncClient, admin_token: str
):
    resp = await client.get(
        "/api/evidence-links/9999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404
