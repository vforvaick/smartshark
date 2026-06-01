"""Tests for Issue #19: Admin capture lifecycle and audit log.

Covers: archive, restore, hard-delete, evidence link unavailable states,
audit log entries, and permission boundaries.
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


async def _upload_artifact(client: AsyncClient, token: str, filename: str = "test.pcap") -> dict:
    """Upload a PCAP and return the artifact JSON."""
    resp = await client.post(
        "/api/captures/upload",
        files={"file": (filename, _pcap_bytes(), "application/octet-stream")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201)
    return resp.json()


# --- Archive tests ---

@pytest.mark.asyncio
async def test_admin_can_archive_artifact(client: AsyncClient, admin_token: str):
    """Admin can archive a Capture Artifact."""
    artifact = await _upload_artifact(client, admin_token)
    artifact_id = artifact["id"]

    resp = await client.post(
        f"/api/admin/captures/{artifact_id}/archive",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "archived"
    assert data["id"] == artifact_id


@pytest.mark.asyncio
async def test_archived_captures_hidden_from_normal_lists(client: AsyncClient, admin_token: str):
    """Archived captures are hidden from normal lists."""
    await _upload_artifact(client, admin_token, "visible.pcap")

    # List should show the artifact
    list_resp = await client.get(
        "/api/captures",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1

    # Archive the first one
    first_id = list_resp.json()[0]["id"]
    await client.post(
        f"/api/admin/captures/{first_id}/archive",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # List should now be empty (or not contain the archived one)
    list_resp2 = await client.get(
        "/api/captures",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    ids = [a["id"] for a in list_resp2.json()]
    assert first_id not in ids


@pytest.mark.asyncio
async def test_archived_captures_resolvable_as_archived(client: AsyncClient, admin_token: str):
    """Archived captures are still resolvable via GET, showing archived status."""
    artifact = await _upload_artifact(client, admin_token)
    artifact_id = artifact["id"]

    await client.post(
        f"/api/admin/captures/{artifact_id}/archive",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.get(
        f"/api/captures/{artifact_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"


# --- Restore tests ---

@pytest.mark.asyncio
async def test_admin_can_restore_archived_artifact(client: AsyncClient, admin_token: str):
    """Admin can restore an archived Capture Artifact back to ready."""
    artifact = await _upload_artifact(client, admin_token)
    artifact_id = artifact["id"]

    await client.post(
        f"/api/admin/captures/{artifact_id}/archive",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.post(
        f"/api/admin/captures/{artifact_id}/restore",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


# --- Hard delete tests ---

@pytest.mark.asyncio
async def test_hard_delete_requires_confirmation(client: AsyncClient, admin_token: str):
    """Hard delete fails without confirmed=true query param."""
    artifact = await _upload_artifact(client, admin_token)
    artifact_id = artifact["id"]

    resp = await client.delete(
        f"/api/admin/captures/{artifact_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400
    assert "confirm" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_hard_delete_with_confirmation_removes_artifact(client: AsyncClient, admin_token: str):
    """Hard delete with confirmed=true removes the artifact."""
    artifact = await _upload_artifact(client, admin_token)
    artifact_id = artifact["id"]

    resp = await client.delete(
        f"/api/admin/captures/{artifact_id}?confirmed=true",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200

    # Artifact should no longer exist
    get_resp = await client.get(
        f"/api/captures/{artifact_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_hard_delete_marks_evidence_links_unavailable(client: AsyncClient, admin_token: str):
    """Evidence Links to hard-deleted artifacts show unavailable state."""
    artifact = await _upload_artifact(client, admin_token)
    artifact_id = artifact["id"]

    # Create an evidence link pointing to this artifact
    link_resp = await client.post(
        "/api/evidence-links",
        json={
            "target_type": "packets",
            "artifact_id": artifact_id,
            "target_params": {"filter": "tcp.analysis.retransmission"},
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert link_resp.status_code == 201
    link_id = link_resp.json()["id"]

    # Hard delete the artifact
    await client.delete(
        f"/api/admin/captures/{artifact_id}?confirmed=true",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Evidence link should now be unavailable
    link_get = await client.get(
        f"/api/evidence-links/{link_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert link_get.status_code == 200
    link_data = link_get.json()
    assert link_data["link"]["is_available"] is False
    assert "delet" in link_data["link"]["unavailability_reason"].lower()
    # Citation text should still be present (textual citation fallback)
    assert link_data["link"]["citation_text"] is not None


# --- Audit log tests ---

@pytest.mark.asyncio
async def test_audit_log_records_archive(client: AsyncClient, admin_token: str):
    """Audit Log records archive action."""
    artifact = await _upload_artifact(client, admin_token)
    artifact_id = artifact["id"]

    await client.post(
        f"/api/admin/captures/{artifact_id}/archive",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    log_resp = await client.get(
        "/api/admin/audit-log",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert log_resp.status_code == 200
    entries = log_resp.json()
    archive_entries = [e for e in entries if e["action"] == "archive_artifact"]
    assert len(archive_entries) >= 1
    entry = archive_entries[-1]
    assert entry["target_type"] == "capture_artifact"
    assert entry["target_id"] == artifact_id


@pytest.mark.asyncio
async def test_audit_log_records_restore(client: AsyncClient, admin_token: str):
    """Audit Log records restore action."""
    artifact = await _upload_artifact(client, admin_token)
    artifact_id = artifact["id"]

    await client.post(
        f"/api/admin/captures/{artifact_id}/archive",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await client.post(
        f"/api/admin/captures/{artifact_id}/restore",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    log_resp = await client.get(
        "/api/admin/audit-log",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert log_resp.status_code == 200
    entries = log_resp.json()
    restore_entries = [e for e in entries if e["action"] == "restore_artifact"]
    assert len(restore_entries) >= 1


@pytest.mark.asyncio
async def test_audit_log_records_hard_delete(client: AsyncClient, admin_token: str):
    """Audit Log records hard-delete action."""
    artifact = await _upload_artifact(client, admin_token)
    artifact_id = artifact["id"]

    await client.delete(
        f"/api/admin/captures/{artifact_id}?confirmed=true",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    log_resp = await client.get(
        "/api/admin/audit-log",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert log_resp.status_code == 200
    entries = log_resp.json()
    delete_entries = [e for e in entries if e["action"] == "hard_delete_artifact"]
    assert len(delete_entries) >= 1
    entry = delete_entries[-1]
    assert entry["target_id"] == artifact_id


# --- Permission tests ---

@pytest.mark.asyncio
async def test_analyst_cannot_archive_artifact(client: AsyncClient, admin_token: str):
    """Analyst cannot archive artifacts — 403."""
    artifact = await _upload_artifact(client, admin_token)
    analyst_token = await _create_analyst(client, admin_token)

    resp = await client.post(
        f"/api/admin/captures/{artifact['id']}/archive",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_analyst_cannot_delete_artifact(client: AsyncClient, admin_token: str):
    """Analyst cannot hard-delete artifacts — 403."""
    artifact = await _upload_artifact(client, admin_token)
    analyst_token = await _create_analyst(client, admin_token)

    resp = await client.delete(
        f"/api/admin/captures/{artifact['id']}?confirmed=true",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_analyst_cannot_view_audit_log(client: AsyncClient, admin_token: str):
    """Analyst cannot view audit log — 403."""
    analyst_token = await _create_analyst(client, admin_token)

    resp = await client.get(
        "/api/admin/audit-log",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_lifecycle_rejected(client: AsyncClient, admin_token: str):
    """Unauthenticated access to lifecycle endpoints is rejected."""
    artifact = await _upload_artifact(client, admin_token)
    artifact_id = artifact["id"]

    resp = await client.post(f"/api/admin/captures/{artifact_id}/archive")
    assert resp.status_code == 401

    resp = await client.post(f"/api/admin/captures/{artifact_id}/restore")
    assert resp.status_code == 401

    resp = await client.delete(f"/api/admin/captures/{artifact_id}?confirmed=true")
    assert resp.status_code == 401

    resp = await client.get("/api/admin/audit-log")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_archive_nonexistent_artifact_returns_404(client: AsyncClient, admin_token: str):
    """Archiving a non-existent artifact returns 404."""
    resp = await client.post(
        "/api/admin/captures/99999/archive",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_hard_delete_warns_about_evidence_link_loss(client: AsyncClient, admin_token: str):
    """Hard delete response includes a warning about evidence link loss."""
    artifact = await _upload_artifact(client, admin_token)
    artifact_id = artifact["id"]

    resp = await client.delete(
        f"/api/admin/captures/{artifact_id}?confirmed=true",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "warning" in data
