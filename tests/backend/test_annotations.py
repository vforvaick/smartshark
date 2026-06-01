"""Tests for Issue #15: Analyst Annotations and Evidence Map revision layer.

Proves: annotations on claims/links/cards, author provenance, false-positive
marking, include/exclude from report, immutability of base evidence map,
and delete-own-only semantics.
"""

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers — create the prerequisite chain: artifact → run → evidence map → claim
# ---------------------------------------------------------------------------


async def _create_evidence_map_with_claim(
    client: AsyncClient, admin_token: str
) -> dict:
    """Upload artifact, create run, create evidence map, add a verified claim."""
    # Upload artifact (valid PCAP magic bytes)
    pcap_magic = b"\xd4\xc3\xb2\xa1" + b"\x00" * 60
    upload = await client.post(
        "/api/captures/upload",
        files={"file": ("test.pcap", pcap_magic, "application/octet-stream")},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    artifact_id = upload.json()["id"]

    # Create analysis run
    run_resp = await client.post(
        "/api/analysis-runs",
        json={"capture_artifact_id": artifact_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    run_id = run_resp.json()["id"]

    # Create evidence map
    map_resp = await client.post(
        f"/api/analysis-runs/{run_id}/evidence-map",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    map_id = map_resp.json()["id"]

    # Create a verified claim with evidence refs
    claim_resp = await client.post(
        f"/api/evidence-maps/{map_id}/claims",
        json={
            "claim_text": "TCP retransmission detected",
            "status": "verified",
            "key_facts": ["3 retransmissions in 5s window"],
            "evidence_refs": [{"type": "frame_detail", "frame": 42}],
            "verification_step": None,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    claim_id = claim_resp.json()["id"]

    return {"artifact_id": artifact_id, "run_id": run_id, "map_id": map_id, "claim_id": claim_id}


async def _create_analyst(client: AsyncClient, admin_token: str, username: str = "analyst1") -> str:
    """Create an analyst and return their token."""
    await client.post(
        "/api/auth/analysts",
        json={"username": username, "password": "pw"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    resp = await client.post("/api/auth/login", json={"username": username, "password": "pw"})
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_annotation_on_claim(client: AsyncClient, admin_token: str):
    """Analyst can add an annotation to a claim."""
    ctx = await _create_evidence_map_with_claim(client, admin_token)

    resp = await client.post(
        "/api/annotations",
        json={
            "target_type": "claim",
            "target_id": ctx["claim_id"],
            "annotation_text": "This looks like a network artifact, not a real retransmission",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["target_type"] == "claim"
    assert data["target_id"] == ctx["claim_id"]
    assert data["annotation_text"] == "This looks like a network artifact, not a real retransmission"
    assert data["author_id"] is not None
    assert data["provenance"] == "analyst"


@pytest.mark.asyncio
async def test_create_annotation_on_evidence_link(client: AsyncClient, admin_token: str):
    """Analyst can add an annotation to an evidence link."""
    ctx = await _create_evidence_map_with_claim(client, admin_token)

    # Create an evidence link first
    link_resp = await client.post(
        "/api/evidence-links",
        json={
            "target_type": "frame",
            "artifact_id": ctx["artifact_id"],
            "target_params": {"frame_number": 42},
            "citation_text": "Frame 42",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    link_id = link_resp.json()["id"]

    resp = await client.post(
        "/api/annotations",
        json={
            "target_type": "evidence_link",
            "target_id": link_id,
            "annotation_text": "This link points to a relevant frame",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["target_type"] == "evidence_link"
    assert resp.json()["target_id"] == link_id


@pytest.mark.asyncio
async def test_annotation_records_author_and_provenance(client: AsyncClient, admin_token: str):
    """Annotations record author and provenance."""
    ctx = await _create_evidence_map_with_claim(client, admin_token)
    analyst_token = await _create_analyst(client, admin_token, "provenance_user")

    resp = await client.post(
        "/api/annotations",
        json={
            "target_type": "claim",
            "target_id": ctx["claim_id"],
            "annotation_text": "I reviewed this",
        },
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["provenance"] == "analyst"
    # author_id should be the analyst's user id (not the admin's)
    me_resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {analyst_token}"})
    assert data["author_id"] == me_resp.json()["id"]


@pytest.mark.asyncio
async def test_mark_annotation_as_false_positive(client: AsyncClient, admin_token: str):
    """Analyst can mark an annotation as false positive."""
    ctx = await _create_evidence_map_with_claim(client, admin_token)

    resp = await client.post(
        "/api/annotations",
        json={
            "target_type": "claim",
            "target_id": ctx["claim_id"],
            "annotation_text": "Not a real issue",
            "is_false_positive": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["is_false_positive"] is True


@pytest.mark.asyncio
async def test_include_exclude_from_report(client: AsyncClient, admin_token: str):
    """Analyst can include/exclude evidence card from report via annotation."""
    ctx = await _create_evidence_map_with_claim(client, admin_token)

    # Create annotation with include_in_report=False
    resp = await client.post(
        "/api/annotations",
        json={
            "target_type": "claim",
            "target_id": ctx["claim_id"],
            "annotation_text": "Exclude from report",
            "include_in_report": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["include_in_report"] is False

    # Update it to include
    ann_id = resp.json()["id"]
    patch = await client.patch(
        f"/api/annotations/{ann_id}",
        json={"include_in_report": True},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert patch.status_code == 200
    assert patch.json()["include_in_report"] is True


@pytest.mark.asyncio
async def test_list_annotations_filtered_by_target(client: AsyncClient, admin_token: str):
    """List annotations filtered by target type and target id."""
    ctx = await _create_evidence_map_with_claim(client, admin_token)

    # Create two annotations on the same claim
    await client.post(
        "/api/annotations",
        json={
            "target_type": "claim",
            "target_id": ctx["claim_id"],
            "annotation_text": "First note",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await client.post(
        "/api/annotations",
        json={
            "target_type": "claim",
            "target_id": ctx["claim_id"],
            "annotation_text": "Second note",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # List filtered
    resp = await client.get(
        "/api/annotations",
        params={"target_type": "claim", "target_id": ctx["claim_id"]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    texts = [a["annotation_text"] for a in data]
    assert "First note" in texts
    assert "Second note" in texts


@pytest.mark.asyncio
async def test_list_annotations_all(client: AsyncClient, admin_token: str):
    """List all annotations (no filter)."""
    ctx = await _create_evidence_map_with_claim(client, admin_token)

    await client.post(
        "/api/annotations",
        json={
            "target_type": "claim",
            "target_id": ctx["claim_id"],
            "annotation_text": "Note A",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.get(
        "/api/annotations",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_update_annotation_text(client: AsyncClient, admin_token: str):
    """Analyst can update annotation text."""
    ctx = await _create_evidence_map_with_claim(client, admin_token)

    create_resp = await client.post(
        "/api/annotations",
        json={
            "target_type": "claim",
            "target_id": ctx["claim_id"],
            "annotation_text": "Original text",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    ann_id = create_resp.json()["id"]

    patch = await client.patch(
        f"/api/annotations/{ann_id}",
        json={"annotation_text": "Updated text"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert patch.status_code == 200
    assert patch.json()["annotation_text"] == "Updated text"


@pytest.mark.asyncio
async def test_delete_own_annotation(client: AsyncClient, admin_token: str):
    """Analyst can delete their own annotation."""
    ctx = await _create_evidence_map_with_claim(client, admin_token)
    analyst_token = await _create_analyst(client, admin_token, "deleter")

    create_resp = await client.post(
        "/api/annotations",
        json={
            "target_type": "claim",
            "target_id": ctx["claim_id"],
            "annotation_text": "My note",
        },
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    ann_id = create_resp.json()["id"]

    delete_resp = await client.delete(
        f"/api/annotations/{ann_id}",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert delete_resp.status_code == 204

    # Verify it's gone
    list_resp = await client.get(
        "/api/annotations",
        params={"target_type": "claim", "target_id": ctx["claim_id"]},
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert all(a["id"] != ann_id for a in list_resp.json())


@pytest.mark.asyncio
async def test_cannot_delete_another_users_annotation(client: AsyncClient, admin_token: str):
    """Analyst cannot delete another user's annotation."""
    ctx = await _create_evidence_map_with_claim(client, admin_token)
    analyst_a = await _create_analyst(client, admin_token, "user_a")
    analyst_b = await _create_analyst(client, admin_token, "user_b")

    create_resp = await client.post(
        "/api/annotations",
        json={
            "target_type": "claim",
            "target_id": ctx["claim_id"],
            "annotation_text": "A's note",
        },
        headers={"Authorization": f"Bearer {analyst_a}"},
    )
    ann_id = create_resp.json()["id"]

    # B tries to delete A's annotation
    delete_resp = await client.delete(
        f"/api/annotations/{ann_id}",
        headers={"Authorization": f"Bearer {analyst_b}"},
    )
    assert delete_resp.status_code == 403


@pytest.mark.asyncio
async def test_base_evidence_map_remains_immutable(client: AsyncClient, admin_token: str):
    """Annotations don't modify the base Evidence Map or claims."""
    ctx = await _create_evidence_map_with_claim(client, admin_token)

    # Record original claim state
    claim_resp = await client.get(
        f"/api/evidence-maps/{ctx['map_id']}/claims",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # Get claim via cards endpoint — there should be exactly 1 claim
    cards_resp = await client.get(
        f"/api/evidence-maps/{ctx['map_id']}/cards",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    original_card = cards_resp.json()[0]

    # Add multiple annotations including false-positive and exclude-from-report
    await client.post(
        "/api/annotations",
        json={
            "target_type": "claim",
            "target_id": ctx["claim_id"],
            "annotation_text": "This is wrong",
            "is_false_positive": True,
            "include_in_report": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Verify the claim itself is unchanged
    cards_after = await client.get(
        f"/api/evidence-maps/{ctx['map_id']}/cards",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    card_after = cards_after.json()[0]
    assert card_after["claim_text"] == original_card["claim_text"]
    assert card_after["status"] == original_card["status"]
    assert card_after["key_facts"] == original_card["key_facts"]
    assert card_after["evidence_refs"] == original_card["evidence_refs"]
    assert card_after["is_reportable"] == original_card["is_reportable"]


@pytest.mark.asyncio
async def test_unauthenticated_access_rejected(client: AsyncClient, admin_token: str):
    """Unauthenticated requests to annotations are rejected."""
    ctx = await _create_evidence_map_with_claim(client, admin_token)

    # Create without auth
    resp = await client.post(
        "/api/annotations",
        json={
            "target_type": "claim",
            "target_id": ctx["claim_id"],
            "annotation_text": "No auth",
        },
    )
    assert resp.status_code == 401

    # List without auth
    resp = await client.get("/api/annotations")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_annotation_on_report_section(client: AsyncClient, admin_token: str):
    """Analyst can annotate a report section target."""
    resp = await client.post(
        "/api/annotations",
        json={
            "target_type": "report_section",
            "target_id": 1,
            "annotation_text": "Section needs revision",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["target_type"] == "report_section"
    assert resp.json()["target_id"] == 1


@pytest.mark.asyncio
async def test_create_annotation_on_evidence_card(client: AsyncClient, admin_token: str):
    """Analyst can annotate an evidence card (by claim id)."""
    ctx = await _create_evidence_map_with_claim(client, admin_token)

    resp = await client.post(
        "/api/annotations",
        json={
            "target_type": "evidence_card",
            "target_id": ctx["claim_id"],
            "annotation_text": "Card annotation",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["target_type"] == "evidence_card"


@pytest.mark.asyncio
async def test_update_nonexistent_annotation_returns_404(client: AsyncClient, admin_token: str):
    """Updating a non-existent annotation returns 404."""
    resp = await client.patch(
        "/api/annotations/99999",
        json={"annotation_text": "Ghost"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_annotation_returns_404(client: AsyncClient, admin_token: str):
    """Deleting a non-existent annotation returns 404."""
    resp = await client.delete(
        "/api/annotations/99999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404
