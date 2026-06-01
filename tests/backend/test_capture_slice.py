"""Tests for Issue #18: Implement capture slicing and slice-as-artifact flow."""

import pytest
from httpx import AsyncClient


async def _upload_pcap(client: AsyncClient, admin_token: str) -> dict:
    """Helper: upload a valid PCAP and return the artifact JSON."""
    pcap_magic = bytes([0xd4, 0xc3, 0xb2, 0xa1]) + b"\x00" * 60
    response = await client.post(
        "/api/captures/upload",
        files={"file": ("test.pcap", pcap_magic, "application/octet-stream")},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_create_slice_by_time_range(client: AsyncClient, admin_token: str):
    """Analyst can create a slice view by time range."""
    artifact = await _upload_pcap(client, admin_token)
    artifact_id = artifact["id"]

    response = await client.post(
        f"/api/captures/{artifact_id}/slices",
        json={
            "criteria_type": "time_range",
            "criteria_params": {
                "time_start": "2026-01-01T00:00:00Z",
                "time_end": "2026-01-01T01:00:00Z",
            },
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["source_artifact_id"] == artifact_id
    assert data["criteria_type"] == "time_range"
    assert data["criteria_params"]["time_start"] == "2026-01-01T00:00:00Z"
    assert data["exported_artifact_id"] is None


@pytest.mark.asyncio
async def test_create_slice_by_display_filter(client: AsyncClient, admin_token: str):
    """Analyst can create a slice view by display filter."""
    artifact = await _upload_pcap(client, admin_token)
    artifact_id = artifact["id"]

    response = await client.post(
        f"/api/captures/{artifact_id}/slices",
        json={
            "criteria_type": "display_filter",
            "criteria_params": {"filter_text": "tcp.port == 80"},
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["criteria_type"] == "display_filter"
    assert data["criteria_params"]["filter_text"] == "tcp.port == 80"


@pytest.mark.asyncio
async def test_create_slice_by_endpoint_pair(client: AsyncClient, admin_token: str):
    """Analyst can create a slice view by endpoint pair."""
    artifact = await _upload_pcap(client, admin_token)
    artifact_id = artifact["id"]

    response = await client.post(
        f"/api/captures/{artifact_id}/slices",
        json={
            "criteria_type": "endpoint_pair",
            "criteria_params": {"src_ip": "192.168.1.1", "dst_ip": "10.0.0.1"},
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["criteria_type"] == "endpoint_pair"
    assert data["criteria_params"]["src_ip"] == "192.168.1.1"


@pytest.mark.asyncio
async def test_create_slice_by_conversation(client: AsyncClient, admin_token: str):
    """Analyst can create a slice view by conversation."""
    artifact = await _upload_pcap(client, admin_token)
    artifact_id = artifact["id"]

    response = await client.post(
        f"/api/captures/{artifact_id}/slices",
        json={
            "criteria_type": "conversation",
            "criteria_params": {"conversation_id": "1"},
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["criteria_type"] == "conversation"
    assert data["criteria_params"]["conversation_id"] == "1"


@pytest.mark.asyncio
async def test_slice_view_links_back_to_original_artifact(client: AsyncClient, admin_token: str):
    """Slice views preserve links back to the original Capture Artifact."""
    artifact = await _upload_pcap(client, admin_token)
    artifact_id = artifact["id"]

    response = await client.post(
        f"/api/captures/{artifact_id}/slices",
        json={
            "criteria_type": "display_filter",
            "criteria_params": {"filter_text": "dns"},
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    data = response.json()
    assert data["source_artifact_id"] == artifact_id

    # Fetch the slice and confirm link
    get_resp = await client.get(
        f"/api/captures/{artifact_id}/slices/{data['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["source_artifact_id"] == artifact_id


@pytest.mark.asyncio
async def test_export_slice_as_new_capture_artifact(client: AsyncClient, admin_token: str):
    """Analyst can export a slice as a new Capture Artifact."""
    artifact = await _upload_pcap(client, admin_token)
    artifact_id = artifact["id"]

    # Create slice
    slice_resp = await client.post(
        f"/api/captures/{artifact_id}/slices",
        json={
            "criteria_type": "time_range",
            "criteria_params": {
                "time_start": "2026-01-01T00:00:00Z",
                "time_end": "2026-01-01T00:30:00Z",
            },
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    slice_id = slice_resp.json()["id"]

    # Export
    export_resp = await client.post(
        f"/api/captures/{artifact_id}/slices/{slice_id}/export",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert export_resp.status_code == 200
    data = export_resp.json()
    assert data["is_new"] is True
    assert data["artifact_id"] is not None
    assert data["content_hash"] is not None
    # The exported artifact should be a different record
    assert data["artifact_id"] != artifact_id


@pytest.mark.asyncio
async def test_exported_slice_has_own_content_identity(client: AsyncClient, admin_token: str):
    """Exported slice has its own content identity (unique content hash)."""
    artifact = await _upload_pcap(client, admin_token)
    artifact_id = artifact["id"]
    source_hash = artifact["content_hash"]

    # Create and export slice
    slice_resp = await client.post(
        f"/api/captures/{artifact_id}/slices",
        json={
            "criteria_type": "display_filter",
            "criteria_params": {"filter_text": "http"},
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    slice_id = slice_resp.json()["id"]

    export_resp = await client.post(
        f"/api/captures/{artifact_id}/slices/{slice_id}/export",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    data = export_resp.json()
    # Content hash must differ from source (different content = different hash)
    assert data["content_hash"] != source_hash


@pytest.mark.asyncio
async def test_evidence_links_distinguish_original_vs_exported(client: AsyncClient, admin_token: str):
    """Evidence Links clearly identify original versus exported slice artifact."""
    artifact = await _upload_pcap(client, admin_token)
    artifact_id = artifact["id"]

    # Create and export slice
    slice_resp = await client.post(
        f"/api/captures/{artifact_id}/slices",
        json={
            "criteria_type": "endpoint_pair",
            "criteria_params": {"src_ip": "10.0.0.1", "dst_ip": "10.0.0.2"},
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    slice_id = slice_resp.json()["id"]

    export_resp = await client.post(
        f"/api/captures/{artifact_id}/slices/{slice_id}/export",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    data = export_resp.json()
    exported_artifact_id = data["artifact_id"]

    # The slice now links to both source and exported artifact
    slice_get = await client.get(
        f"/api/captures/{artifact_id}/slices/{slice_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    slice_data = slice_get.json()
    assert slice_data["source_artifact_id"] == artifact_id
    assert slice_data["exported_artifact_id"] == exported_artifact_id
    assert slice_data["source_artifact_id"] != slice_data["exported_artifact_id"]


@pytest.mark.asyncio
async def test_list_slices_for_artifact(client: AsyncClient, admin_token: str):
    """List slices for an artifact."""
    artifact = await _upload_pcap(client, admin_token)
    artifact_id = artifact["id"]

    # Create two slices
    await client.post(
        f"/api/captures/{artifact_id}/slices",
        json={
            "criteria_type": "time_range",
            "criteria_params": {
                "time_start": "2026-01-01T00:00:00Z",
                "time_end": "2026-01-01T01:00:00Z",
            },
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await client.post(
        f"/api/captures/{artifact_id}/slices",
        json={
            "criteria_type": "display_filter",
            "criteria_params": {"filter_text": "tcp"},
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    response = await client.get(
        f"/api/captures/{artifact_id}/slices",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_slice_for_nonexistent_artifact_returns_404(client: AsyncClient, admin_token: str):
    """Slice for non-existent artifact returns 404."""
    response = await client.post(
        "/api/captures/99999/slices",
        json={
            "criteria_type": "time_range",
            "criteria_params": {
                "time_start": "2026-01-01T00:00:00Z",
                "time_end": "2026-01-01T01:00:00Z",
            },
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_slice_access_rejected(client: AsyncClient):
    """Unauthenticated access to slice endpoints is rejected."""
    # Create
    resp = await client.post(
        "/api/captures/1/slices",
        json={
            "criteria_type": "time_range",
            "criteria_params": {
                "time_start": "2026-01-01T00:00:00Z",
                "time_end": "2026-01-01T01:00:00Z",
            },
        },
    )
    assert resp.status_code == 401

    # List
    resp = await client.get("/api/captures/1/slices")
    assert resp.status_code == 401

    # Get
    resp = await client.get("/api/captures/1/slices/1")
    assert resp.status_code == 401

    # Export
    resp = await client.post("/api/captures/1/slices/1/export")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_invalid_criteria_params_rejected(client: AsyncClient, admin_token: str):
    """Missing required params for criteria type returns 422."""
    artifact = await _upload_pcap(client, admin_token)
    artifact_id = artifact["id"]

    response = await client.post(
        f"/api/captures/{artifact_id}/slices",
        json={
            "criteria_type": "time_range",
            "criteria_params": {"wrong_field": "value"},
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_duplicate_export_returns_existing_artifact(client: AsyncClient, admin_token: str):
    """Exporting the same slice twice returns the same artifact (idempotent)."""
    artifact = await _upload_pcap(client, admin_token)
    artifact_id = artifact["id"]

    slice_resp = await client.post(
        f"/api/captures/{artifact_id}/slices",
        json={
            "criteria_type": "display_filter",
            "criteria_params": {"filter_text": "dns"},
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    slice_id = slice_resp.json()["id"]

    # First export
    first = await client.post(
        f"/api/captures/{artifact_id}/slices/{slice_id}/export",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert first.json()["is_new"] is True
    first_artifact_id = first.json()["artifact_id"]

    # Second export — should return existing
    second = await client.post(
        f"/api/captures/{artifact_id}/slices/{slice_id}/export",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert second.json()["is_new"] is False
    assert second.json()["artifact_id"] == first_artifact_id
