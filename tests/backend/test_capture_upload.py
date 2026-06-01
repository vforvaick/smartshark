"""Tests for Issue #2: Upload a Capture Artifact and show Import Diagnostic.

Covers: valid upload, dedup by hash, invalid/corrupt/unsupported/too-large files,
import diagnostics, workspace listing, immutability, and permission checks.
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
    """Minimal valid-ish PCAP content with the global header magic number.

    PCAP global header: d4 c3 b2 a1 (little-endian magic) + 20 more bytes.
    """
    header = b"\xd4\xc3\xb2\xa1"  # PCAP magic number (little-endian)
    header += b"\x02\x00"  # version major
    header += b"\x04\x00"  # version minor
    header += b"\x00\x00\x00\x00"  # thiszone
    header += b"\x00\x00\x00\x00"  # sigfigs
    header += b"\xff\xff\x00\x00"  # snaplen
    header += b"\x01\x00\x00\x00"  # network (ETHERNET)
    # One empty packet record header
    header += b"\x00\x00\x00\x00"  # ts_sec
    header += b"\x00\x00\x00\x00"  # ts_usec
    header += b"\x04\x00\x00\x00"  # incl_len
    header += b"\x04\x00\x00\x00"  # orig_len
    header += b"\x00\x00\x00\x00"  # 4 bytes of packet data
    return header


# --- Valid upload tests ---

@pytest.mark.asyncio
async def test_upload_valid_pcap_creates_artifact(client: AsyncClient, admin_token: str):
    """Analyst can upload a PCAP and see a Capture Artifact record."""
    token = await _create_analyst(client, admin_token)
    files = {"file": ("test.pcap", _pcap_bytes(), "application/octet-stream")}
    resp = await client.post("/api/captures/upload", files=files, headers={
        "Authorization": f"Bearer {token}",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] is not None
    assert data["content_hash"] is not None
    assert data["original_filename"] == "test.pcap"
    assert data["status"] == "ready"
    assert data["size_bytes"] > 0


@pytest.mark.asyncio
async def test_upload_same_content_returns_existing_artifact(client: AsyncClient, admin_token: str):
    """Duplicate content hash returns the existing artifact instead of duplicating."""
    token = await _create_analyst(client, admin_token)
    pcap = _pcap_bytes()
    headers = {"Authorization": f"Bearer {token}"}

    resp1 = await client.post("/api/captures/upload",
        files={"file": ("first.pcap", pcap, "application/octet-stream")},
        headers=headers)
    assert resp1.status_code == 201

    resp2 = await client.post("/api/captures/upload",
        files={"file": ("second.pcap", pcap, "application/octet-stream")},
        headers=headers)
    # Same content → return existing artifact (200, not 201)
    assert resp2.status_code == 200
    assert resp2.json()["id"] == resp1.json()["id"]
    assert resp2.json()["content_hash"] == resp1.json()["content_hash"]


# --- Import diagnostic tests ---

@pytest.mark.asyncio
async def test_upload_invalid_file_creates_import_diagnostic(client: AsyncClient, admin_token: str):
    """Non-capture file produces an Import Diagnostic with category and suggestion."""
    token = await _create_analyst(client, admin_token)
    files = {"file": ("bad.txt", b"this is not a pcap", "text/plain")}
    resp = await client.post("/api/captures/upload", files=files, headers={
        "Authorization": f"Bearer {token}",
    })
    assert resp.status_code == 422
    data = resp.json()["detail"]
    assert data["category"] is not None
    assert data["suggested_next_step"] is not None
    assert data["original_filename"] == "bad.txt"


@pytest.mark.asyncio
async def test_upload_corrupt_pcap_creates_import_diagnostic(client: AsyncClient, admin_token: str):
    """Corrupt PCAP (valid magic but truncated) produces a diagnostic."""
    token = await _create_analyst(client, admin_token)
    # Valid PCAP magic but truncated (only 8 bytes, needs at least 24 for header)
    files = {"file": ("corrupt.pcap", b"\xd4\xc3\xb2\xa1" + b"\x00" * 4, "application/octet-stream")}
    resp = await client.post("/api/captures/upload", files=files, headers={
        "Authorization": f"Bearer {token}",
    })
    assert resp.status_code == 422
    data = resp.json()["detail"]
    assert data["category"] == "corrupt_capture"


@pytest.mark.asyncio
async def test_upload_unsupported_format_creates_import_diagnostic(client: AsyncClient, admin_token: str):
    """Unsupported capture format produces a diagnostic."""
    token = await _create_analyst(client, admin_token)
    files = {"file": ("image.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "image/png")}
    resp = await client.post("/api/captures/upload", files=files, headers={
        "Authorization": f"Bearer {token}",
    })
    assert resp.status_code == 422
    data = resp.json()["detail"]
    assert data["category"] == "unsupported_format"


# --- Workspace listing ---

@pytest.mark.asyncio
async def test_list_artifacts(client: AsyncClient, admin_token: str):
    """Imported captures are visible in the workspace."""
    token = await _create_analyst(client, admin_token)
    headers = {"Authorization": f"Bearer {token}"}

    # Initially empty
    resp = await client.get("/api/captures", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []

    # Upload one
    await client.post("/api/captures/upload",
        files={"file": ("test.pcap", _pcap_bytes(), "application/octet-stream")},
        headers=headers)

    # Now has one
    resp = await client.get("/api/captures", headers=headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["original_filename"] == "test.pcap"


@pytest.mark.asyncio
async def test_get_artifact_by_id(client: AsyncClient, admin_token: str):
    """Can retrieve a single artifact by ID."""
    token = await _create_analyst(client, admin_token)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/api/captures/upload",
        files={"file": ("single.pcap", _pcap_bytes(), "application/octet-stream")},
        headers=headers)
    artifact_id = resp.json()["id"]

    resp = await client.get(f"/api/captures/{artifact_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == artifact_id
    assert resp.json()["original_filename"] == "single.pcap"


@pytest.mark.asyncio
async def test_get_nonexistent_artifact_returns_404(client: AsyncClient, admin_token: str):
    """Requesting a missing artifact returns 404."""
    token = await _create_analyst(client, admin_token)
    resp = await client.get("/api/captures/99999", headers={
        "Authorization": f"Bearer {token}",
    })
    assert resp.status_code == 404


# --- Immutability ---

@pytest.mark.asyncio
async def test_artifact_has_no_update_endpoint(client: AsyncClient, admin_token: str):
    """No PUT/PATCH endpoint exists for artifacts — they are immutable."""
    token = await _create_analyst(client, admin_token)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/api/captures/upload",
        files={"file": ("immutable.pcap", _pcap_bytes(), "application/octet-stream")},
        headers=headers)
    artifact_id = resp.json()["id"]

    # PUT should return 405 (Method Not Allowed)
    resp = await client.put(f"/api/captures/{artifact_id}", json={"status": "modified"}, headers=headers)
    assert resp.status_code == 405

    # PATCH should also return 405
    resp = await client.patch(f"/api/captures/{artifact_id}", json={"status": "modified"}, headers=headers)
    assert resp.status_code == 405


# --- Permission checks ---

@pytest.mark.asyncio
async def test_upload_requires_auth(client: AsyncClient):
    """Unauthenticated users cannot upload."""
    files = {"file": ("test.pcap", _pcap_bytes(), "application/octet-stream")}
    resp = await client.post("/api/captures/upload", files=files)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_can_also_upload(client: AsyncClient, admin_token: str):
    """Admin can upload captures too."""
    files = {"file": ("admin.pcap", _pcap_bytes(), "application/octet-stream")}
    resp = await client.post("/api/captures/upload", files=files, headers={
        "Authorization": f"Bearer {admin_token}",
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_list_requires_auth(client: AsyncClient):
    """Unauthenticated users cannot list captures."""
    resp = await client.get("/api/captures")
    assert resp.status_code == 401
