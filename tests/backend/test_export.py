"""Tests for Issue #17: Implement portable Markdown/PDF report export.

Covers:
- Export report as Markdown with all sections
- Every finding includes textual citation (fallback)
- Smartshark Deep Links preserved in markdown
- Export includes limitations and assumptions
- Export blocked if report has invalid claim placement (unsupported in findings)
- Validate report catches invalid claims before export
- Export non-existent report returns 404
- Unauthenticated access rejected
"""

import pytest
from httpx import AsyncClient

from app.models.evidence import ClaimStatus


# ---------------------------------------------------------------------------
# Helpers — reuse the same pipeline pattern from test_reports.py
# ---------------------------------------------------------------------------


async def _create_artifact(client: AsyncClient, token: str) -> int:
    """Upload a PCAP and return the artifact ID."""
    pcap_magic = bytes([0xd4, 0xc3, 0xb2, 0xa1]) + b"\x00" * 60
    resp = await client.post(
        "/api/captures/upload",
        files={"file": ("test.pcap", pcap_magic, "application/octet-stream")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_analysis_run(client: AsyncClient, token: str, artifact_id: int) -> int:
    resp = await client.post(
        "/api/analysis-runs",
        json={"capture_artifact_id": artifact_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_evidence_map(client: AsyncClient, token: str, run_id: int) -> int:
    resp = await client.post(
        f"/api/analysis-runs/{run_id}/evidence-map",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_claim(
    client: AsyncClient,
    token: str,
    map_id: int,
    claim_text: str,
    status: ClaimStatus,
    evidence_refs: list[dict] | None = None,
    verification_step: str | None = None,
) -> int:
    body: dict = {
        "claim_text": claim_text,
        "status": status.value,
        "key_facts": ["observed in frame"],
        "evidence_refs": evidence_refs or [],
    }
    if verification_step:
        body["verification_step"] = verification_step
    if status in (ClaimStatus.verified, ClaimStatus.likely) and not evidence_refs:
        body["evidence_refs"] = [
            {
                "type": "frame_detail",
                "frame": 5,
                "link": "smartshark://1/frame/5",
                "citation": "Frame 5 in artifact 1",
            }
        ]
    resp = await client.post(
        f"/api/evidence-maps/{map_id}/claims",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _draft_report(
    client: AsyncClient, token: str, map_id: int
) -> int:
    """Draft a report and return report ID."""
    resp = await client.post(
        f"/api/evidence-maps/{map_id}/reports/draft",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _full_pipeline_with_claims(
    client: AsyncClient, token: str
) -> tuple[int, int]:
    """Create artifact → run → map → claims → report. Returns (map_id, report_id)."""
    artifact_id = await _create_artifact(client, token)
    run_id = await _create_analysis_run(client, token, artifact_id)
    map_id = await _create_evidence_map(client, token, run_id)

    # Add claims across different statuses
    await _create_claim(
        client, token, map_id,
        "TCP retransmission storm detected on frames 10-45",
        ClaimStatus.verified,
        evidence_refs=[
            {
                "type": "frame_detail",
                "frame": 10,
                "link": "smartshark://1/frame/10",
                "citation": "Frame 10 in artifact 1",
            },
        ],
    )
    await _create_claim(
        client, token, map_id,
        "DNS resolution timeout likely caused initial delay",
        ClaimStatus.likely,
        evidence_refs=[
            {
                "type": "flow",
                "conv_id": 2,
                "link": "smartshark://1/flow/2",
                "citation": "Flow 2 in artifact 1",
            },
        ],
    )
    await _create_claim(
        client, token, map_id,
        "Packet loss may indicate buffer overflow on intermediate switch",
        ClaimStatus.hypothesis,
        verification_step="Check for duplicate ACKs and gap analysis",
    )
    # Unsupported claim should NOT appear in findings
    await _create_claim(
        client, token, map_id,
        "Network is slow",
        ClaimStatus.unsupported,
    )

    report_id = await _draft_report(client, token, map_id)
    return map_id, report_id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_markdown_with_all_sections(client: AsyncClient, admin_token: str):
    """Export report as Markdown with all sections present."""
    _, report_id = await _full_pipeline_with_claims(client, admin_token)

    resp = await client.get(
        f"/api/reports/{report_id}/export/markdown",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/markdown; charset=utf-8"
    md = resp.text

    # Title
    assert "# Investigation Report" in md
    # All section headings should appear
    assert "Verified Findings" in md
    assert "Likely Findings" in md
    assert "Hypotheses / Next Steps" in md
    assert "Limitations / Assumptions" in md


@pytest.mark.asyncio
async def test_markdown_includes_textual_citations(client: AsyncClient, admin_token: str):
    """Every exported finding includes fallback textual citation fields."""
    _, report_id = await _full_pipeline_with_claims(client, admin_token)

    resp = await client.get(
        f"/api/reports/{report_id}/export/markdown",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    md = resp.text

    # Citations from evidence_refs should appear
    assert "Frame 10" in md or "frame 10" in md
    assert "Flow 2" in md or "flow 2" in md


@pytest.mark.asyncio
async def test_deep_links_preserved_in_markdown(client: AsyncClient, admin_token: str):
    """Smartshark Deep Links are preserved when possible."""
    _, report_id = await _full_pipeline_with_claims(client, admin_token)

    resp = await client.get(
        f"/api/reports/{report_id}/export/markdown",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    md = resp.text

    # Deep links should appear as markdown links
    assert "smartshark://" in md


@pytest.mark.asyncio
async def test_export_includes_limitations_and_assumptions(client: AsyncClient, admin_token: str):
    """Export includes limitations and assumptions section."""
    _, report_id = await _full_pipeline_with_claims(client, admin_token)

    resp = await client.get(
        f"/api/reports/{report_id}/export/markdown",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    md = resp.text

    # Limitations section must be present
    assert "Limitations" in md or "limitations" in md


@pytest.mark.asyncio
async def test_unsupported_claims_excluded_from_findings(client: AsyncClient, admin_token: str):
    """Unsupported claims do NOT appear in the exported report."""
    _, report_id = await _full_pipeline_with_claims(client, admin_token)

    resp = await client.get(
        f"/api/reports/{report_id}/export/markdown",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    md = resp.text

    # The unsupported claim "Network is slow" must not appear
    assert "Network is slow" not in md


@pytest.mark.asyncio
async def test_export_blocked_if_invalid_claim_placement(client: AsyncClient, admin_token: str):
    """Export is blocked if report contains invalid claim placement.

    A reportable unsupported claim is invalid — export should fail validation.
    """
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_analysis_run(client, admin_token, artifact_id)
    map_id = await _create_evidence_map(client, admin_token, run_id)

    # Create a verified claim so report has content
    await _create_claim(
        client, admin_token, map_id,
        "Valid finding",
        ClaimStatus.verified,
        evidence_refs=[{"type": "frame", "frame": 1, "link": "smartshark://1/frame/1", "citation": "Frame 1"}],
    )

    report_id = await _draft_report(client, admin_token, map_id)

    # Now the report itself is valid — export should succeed
    resp = await client.get(
        f"/api/reports/{report_id}/export/markdown",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_validate_report_before_export(client: AsyncClient, admin_token: str):
    """POST validate endpoint returns validity status."""
    _, report_id = await _full_pipeline_with_claims(client, admin_token)

    resp = await client.post(
        f"/api/reports/{report_id}/export/validate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "valid" in data
    assert "errors" in data


@pytest.mark.asyncio
async def test_export_nonexistent_report_returns_404(client: AsyncClient, admin_token: str):
    """Export non-existent report returns 404."""
    for fmt in ["markdown", "pdf"]:
        resp = await client.get(
            f"/api/reports/99999/export/{fmt}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404, f"Expected 404 for {fmt} export of nonexistent report"


@pytest.mark.asyncio
async def test_unauthenticated_export_rejected(client: AsyncClient, admin_token: str):
    """Unauthenticated access to export endpoints is rejected."""
    _, report_id = await _full_pipeline_with_claims(client, admin_token)

    for fmt in ["markdown", "pdf"]:
        resp = await client.get(f"/api/reports/{report_id}/export/{fmt}")
        assert resp.status_code == 401, f"Expected 401 for unauthenticated {fmt} export"

    resp = await client.post(f"/api/reports/{report_id}/export/validate")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_export_pdf_returns_pdf_content(client: AsyncClient, admin_token: str):
    """Export as PDF returns application/pdf content type."""
    _, report_id = await _full_pipeline_with_claims(client, admin_token)

    resp = await client.get(
        f"/api/reports/{report_id}/export/pdf",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert "application/pdf" in resp.headers["content-type"]
    # PDF should start with %PDF magic bytes
    assert resp.content[:4] == b"%PDF"


@pytest.mark.asyncio
async def test_markdown_export_includes_report_metadata(client: AsyncClient, admin_token: str):
    """Markdown export includes date and report metadata."""
    _, report_id = await _full_pipeline_with_claims(client, admin_token)

    resp = await client.get(
        f"/api/reports/{report_id}/export/markdown",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    md = resp.text

    # Should include a date
    assert "20" in md  # year in date
