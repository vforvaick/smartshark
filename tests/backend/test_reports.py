"""Tests for Issue #16: Build report draft, review, and native report flow.

Covers:
- Draft report from eligible Evidence Cards
- Verified/Likely/Hypothesis/Unsupported claim routing
- False-positive and include/exclude annotation filtering
- Section editing, reordering
- Deep link preservation
- Auth guards and error handling
"""

import pytest
from httpx import AsyncClient

from app.models.evidence import ClaimStatus


# ---------------------------------------------------------------------------
# Helpers — create a full analysis pipeline to get an evidence map with claims
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
    """Create an AnalysisRun and return its ID."""
    resp = await client.post(
        "/api/analysis-runs",
        json={"capture_artifact_id": artifact_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_evidence_map(client: AsyncClient, token: str, run_id: int) -> int:
    """Create an EvidenceMap and return its ID."""
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
    """Add a claim to the evidence map, return claim ID."""
    body: dict = {
        "claim_text": claim_text,
        "status": status.value,
        "key_facts": ["test fact"],
        "evidence_refs": evidence_refs or [],
    }
    if verification_step:
        body["verification_step"] = verification_step
    if status in (ClaimStatus.verified, ClaimStatus.likely) and not evidence_refs:
        body["evidence_refs"] = [{"type": "frame_detail", "frame": 1, "link": "smartshark://frame/1"}]
    resp = await client.post(
        f"/api/evidence-maps/{map_id}/claims",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _annotate_claim(
    client: AsyncClient,
    token: str,
    claim_id: int,
    is_false_positive: bool = False,
    include_in_report: bool = True,
) -> int:
    """Create an annotation on a claim, return annotation ID."""
    resp = await client.post(
        "/api/annotations",
        json={
            "target_type": "claim",
            "target_id": claim_id,
            "annotation_text": "analyst note",
            "is_false_positive": is_false_positive,
            "include_in_report": include_in_report,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _setup_pipeline(client: AsyncClient, token: str) -> tuple[int, int, int]:
    """Create artifact → analysis run → evidence map. Returns (artifact_id, run_id, map_id)."""
    artifact_id = await _create_artifact(client, token)
    run_id = await _create_analysis_run(client, token, artifact_id)
    map_id = await _create_evidence_map(client, token, run_id)
    return artifact_id, run_id, map_id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_draft_report_from_evidence_cards(client: AsyncClient, admin_token: str):
    """AI can draft a report from eligible Evidence Cards."""
    _, _, map_id = await _setup_pipeline(client, admin_token)

    # Add one verified claim
    await _create_claim(client, admin_token, map_id, "TCP retransmission detected", ClaimStatus.verified)

    resp = await client.post(
        f"/api/evidence-maps/{map_id}/reports/draft",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["evidence_map_id"] == map_id
    assert data["status"] == "draft"
    assert len(data["sections"]) >= 1


@pytest.mark.asyncio
async def test_verified_claims_in_verified_findings(client: AsyncClient, admin_token: str):
    """Verified claims appear in Verified Findings section."""
    _, _, map_id = await _setup_pipeline(client, admin_token)

    await _create_claim(client, admin_token, map_id, "Verified finding A", ClaimStatus.verified)
    await _create_claim(client, admin_token, map_id, "Verified finding B", ClaimStatus.verified)

    resp = await client.post(
        f"/api/evidence-maps/{map_id}/reports/draft",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    sections = resp.json()["sections"]

    verified_section = next(s for s in sections if s["section_type"] == "verified_findings")
    assert "Verified finding A" in verified_section["content"]
    assert "Verified finding B" in verified_section["content"]


@pytest.mark.asyncio
async def test_likely_claims_in_likely_findings(client: AsyncClient, admin_token: str):
    """Likely claims appear in Likely Findings section."""
    _, _, map_id = await _setup_pipeline(client, admin_token)

    await _create_claim(client, admin_token, map_id, "Likely cause X", ClaimStatus.likely)

    resp = await client.post(
        f"/api/evidence-maps/{map_id}/reports/draft",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    sections = resp.json()["sections"]

    likely_section = next(s for s in sections if s["section_type"] == "likely_findings")
    assert "Likely cause X" in likely_section["content"]


@pytest.mark.asyncio
async def test_hypotheses_only_in_hypotheses_next_steps(client: AsyncClient, admin_token: str):
    """Hypotheses appear only in Hypotheses / Next Steps section."""
    _, _, map_id = await _setup_pipeline(client, admin_token)

    await _create_claim(
        client, admin_token, map_id, "Maybe DNS timeout", ClaimStatus.hypothesis,
        verification_step="Check DNS response latency",
    )

    resp = await client.post(
        f"/api/evidence-maps/{map_id}/reports/draft",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    sections = resp.json()["sections"]

    hyp_section = next(s for s in sections if s["section_type"] == "hypotheses_next_steps")
    assert "Maybe DNS timeout" in hyp_section["content"]

    # Ensure hypothesis does NOT appear in verified or likely findings
    verified = next((s for s in sections if s["section_type"] == "verified_findings"), None)
    likely = next((s for s in sections if s["section_type"] == "likely_findings"), None)
    if verified:
        assert "Maybe DNS timeout" not in verified["content"]
    if likely:
        assert "Maybe DNS timeout" not in likely["content"]


@pytest.mark.asyncio
async def test_unsupported_claims_excluded(client: AsyncClient, admin_token: str):
    """Unsupported claims are excluded from report findings."""
    _, _, map_id = await _setup_pipeline(client, admin_token)

    await _create_claim(client, admin_token, map_id, "Unsupported idea", ClaimStatus.unsupported)
    await _create_claim(client, admin_token, map_id, "Real finding", ClaimStatus.verified)

    resp = await client.post(
        f"/api/evidence-maps/{map_id}/reports/draft",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    report_text = resp.json()

    # Unsupported claim should not appear anywhere
    all_content = " ".join(s["content"] for s in report_text["sections"])
    assert "Unsupported idea" not in all_content
    assert "Real finding" in all_content


@pytest.mark.asyncio
async def test_false_positive_claims_excluded(client: AsyncClient, admin_token: str):
    """Claims marked as false positive via annotations are excluded from report."""
    _, _, map_id = await _setup_pipeline(client, admin_token)

    claim_id = await _create_claim(client, admin_token, map_id, "False alarm", ClaimStatus.verified)
    await _annotate_claim(client, admin_token, claim_id, is_false_positive=True)

    resp = await client.post(
        f"/api/evidence-maps/{map_id}/reports/draft",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    all_content = " ".join(s["content"] for s in resp.json()["sections"])
    assert "False alarm" not in all_content


@pytest.mark.asyncio
async def test_include_exclude_toggles_respected(client: AsyncClient, admin_token: str):
    """Claims with include_in_report=False annotation are excluded."""
    _, _, map_id = await _setup_pipeline(client, admin_token)

    claim_id = await _create_claim(client, admin_token, map_id, "Excluded claim", ClaimStatus.verified)
    await _annotate_claim(client, admin_token, claim_id, include_in_report=False)

    resp = await client.post(
        f"/api/evidence-maps/{map_id}/reports/draft",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    all_content = " ".join(s["content"] for s in resp.json()["sections"])
    assert "Excluded claim" not in all_content


@pytest.mark.asyncio
async def test_analyst_can_edit_section(client: AsyncClient, admin_token: str):
    """Analyst can edit report section title and content."""
    _, _, map_id = await _setup_pipeline(client, admin_token)
    await _create_claim(client, admin_token, map_id, "Finding to edit", ClaimStatus.verified)

    draft = await client.post(
        f"/api/evidence-maps/{map_id}/reports/draft",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert draft.status_code == 201
    report_id = draft.json()["id"]
    section_id = draft.json()["sections"][0]["id"]

    resp = await client.patch(
        f"/api/reports/{report_id}/sections/{section_id}",
        json={"title": "Custom Title", "content": "Revised content by analyst"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["title"] == "Custom Title"
    assert updated["content"] == "Revised content by analyst"


@pytest.mark.asyncio
async def test_analyst_can_reorder_sections(client: AsyncClient, admin_token: str):
    """Analyst can reorder report sections."""
    _, _, map_id = await _setup_pipeline(client, admin_token)
    await _create_claim(client, admin_token, map_id, "V finding", ClaimStatus.verified)
    await _create_claim(
        client, admin_token, map_id, "H idea", ClaimStatus.hypothesis,
        verification_step="check",
    )

    draft = await client.post(
        f"/api/evidence-maps/{map_id}/reports/draft",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert draft.status_code == 201
    report_id = draft.json()["id"]
    sections = draft.json()["sections"]
    assert len(sections) >= 2

    # Reverse the order
    reorder_payload = [
        {"section_id": s["id"], "order_index": len(sections) - 1 - i}
        for i, s in enumerate(sections)
    ]

    resp = await client.patch(
        f"/api/reports/{report_id}/sections-reorder",
        json=reorder_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    reordered = resp.json()
    # Verify the order changed
    ids_before = [s["id"] for s in sections]
    ids_after = [s["id"] for s in reordered]
    assert ids_before != ids_after


@pytest.mark.asyncio
async def test_native_report_preserves_deep_links(client: AsyncClient, admin_token: str):
    """Native report preserves active Smartshark Deep Links."""
    _, _, map_id = await _setup_pipeline(client, admin_token)

    deep_link = {"type": "frame_detail", "frame": 42, "link": "smartshark://capture/1/frame/42"}
    await _create_claim(
        client, admin_token, map_id, "Finding with link", ClaimStatus.verified,
        evidence_refs=[deep_link],
    )

    draft = await client.post(
        f"/api/evidence-maps/{map_id}/reports/draft",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert draft.status_code == 201
    sections = draft.json()["sections"]

    # Find the section containing this claim
    section = next(s for s in sections if "Finding with link" in s["content"])
    assert "smartshark://" in str(section.get("deep_links", ""))
    # The deep_links field should contain the reference
    assert any("frame/42" in str(link) for link in section.get("deep_links", []))


@pytest.mark.asyncio
async def test_get_report(client: AsyncClient, admin_token: str):
    """Can retrieve a report by ID with all sections."""
    _, _, map_id = await _setup_pipeline(client, admin_token)
    await _create_claim(client, admin_token, map_id, "Test finding", ClaimStatus.verified)

    draft = await client.post(
        f"/api/evidence-maps/{map_id}/reports/draft",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert draft.status_code == 201
    report_id = draft.json()["id"]

    resp = await client.get(
        f"/api/reports/{report_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == report_id
    assert len(data["sections"]) >= 1


@pytest.mark.asyncio
async def test_draft_nonexistent_map_returns_404(client: AsyncClient, admin_token: str):
    """Drafting a report for a non-existent evidence map returns 404."""
    resp = await client.post(
        "/api/evidence-maps/99999/reports/draft",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_nonexistent_report_returns_404(client: AsyncClient, admin_token: str):
    """Getting a non-existent report returns 404."""
    resp = await client.get(
        "/api/reports/99999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_draft_rejected(client: AsyncClient, admin_token: str):
    """Unauthenticated users cannot create report drafts."""
    _, _, map_id = await _setup_pipeline(client, admin_token)

    resp = await client.post(f"/api/evidence-maps/{map_id}/reports/draft")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthenticated_get_report_rejected(client: AsyncClient):
    """Unauthenticated users cannot get reports."""
    resp = await client.get("/api/reports/1")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_section_toggle_include(client: AsyncClient, admin_token: str):
    """Analyst can toggle section inclusion."""
    _, _, map_id = await _setup_pipeline(client, admin_token)
    await _create_claim(client, admin_token, map_id, "Toggle me", ClaimStatus.verified)

    draft = await client.post(
        f"/api/evidence-maps/{map_id}/reports/draft",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    report_id = draft.json()["id"]
    section_id = draft.json()["sections"][0]["id"]

    resp = await client.patch(
        f"/api/reports/{report_id}/sections/{section_id}",
        json={"is_included": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_included"] is False
