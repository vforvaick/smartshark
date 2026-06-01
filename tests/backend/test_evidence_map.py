"""Evidence Map, Claim Status validator, and Evidence Cards — Issue #9.

Tests enforce the critical anti-hallucination rules:
- Verified/Likely claims require evidence_refs
- Hypotheses require a verification_step
- Unsupported claims cannot be marked reportable
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


async def _create_and_run_analysis(
    client: AsyncClient, admin_token: str, artifact_id: int
) -> int:
    """Create an analysis run, run quick analysis, return run id."""
    resp = await client.post(
        "/api/analysis-runs",
        json={"capture_artifact_id": artifact_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    run_id = resp.json()["id"]

    qa = await client.post(
        f"/api/analysis-runs/{run_id}/quick-analysis",
        json={"issue_brief": "Test issue"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert qa.status_code == 200
    return run_id


# ---------------------------------------------------------------------------
# 1. Create Evidence Map from Analysis Run
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_evidence_map_from_analysis_run(
    client: AsyncClient, admin_token: str
):
    """Analysis Run creates a base Evidence Map."""
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_and_run_analysis(client, admin_token, artifact_id)

    resp = await client.post(
        f"/api/analysis-runs/{run_id}/evidence-map",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["analysis_run_id"] == run_id
    assert "id" in data
    assert data["claims"] == []


@pytest.mark.asyncio
async def test_evidence_map_for_nonexistent_run_rejected(
    client: AsyncClient, admin_token: str
):
    resp = await client.post(
        "/api/analysis-runs/9999/evidence-map",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_duplicate_evidence_map_rejected(
    client: AsyncClient, admin_token: str
):
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_and_run_analysis(client, admin_token, artifact_id)

    resp1 = await client.post(
        f"/api/analysis-runs/{run_id}/evidence-map",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp1.status_code == 201

    resp2 = await client.post(
        f"/api/analysis-runs/{run_id}/evidence-map",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp2.status_code == 409


# ---------------------------------------------------------------------------
# 2. Get Evidence Map
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_evidence_map_returns_claims(
    client: AsyncClient, admin_token: str
):
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_and_run_analysis(client, admin_token, artifact_id)

    await client.post(
        f"/api/analysis-runs/{run_id}/evidence-map",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.get(
        f"/api/analysis-runs/{run_id}/evidence-map",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["analysis_run_id"] == run_id


# ---------------------------------------------------------------------------
# 3. Claim Status Validation — Verified
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verified_claim_requires_evidence_refs(
    client: AsyncClient, admin_token: str
):
    """Verified claims are rejected unless they have at least one evidence_ref."""
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_and_run_analysis(client, admin_token, artifact_id)
    map_resp = await client.post(
        f"/api/analysis-runs/{run_id}/evidence-map",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    map_id = map_resp.json()["id"]

    resp = await client.post(
        f"/api/evidence-maps/{map_id}/claims",
        json={
            "claim_text": "TCP retransmission detected",
            "status": "verified",
            "key_facts": ["Retransmission rate: 5%"],
            "evidence_refs": [],  # empty — should be rejected
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422
    assert "evidence" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_verified_claim_with_evidence_refs_accepted(
    client: AsyncClient, admin_token: str
):
    """Verified claim with evidence_refs is accepted."""
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_and_run_analysis(client, admin_token, artifact_id)
    map_resp = await client.post(
        f"/api/analysis-runs/{run_id}/evidence-map",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    map_id = map_resp.json()["id"]

    resp = await client.post(
        f"/api/evidence-maps/{map_id}/claims",
        json={
            "claim_text": "TCP retransmission detected",
            "status": "verified",
            "key_facts": ["Retransmission rate: 5%"],
            "evidence_refs": [{"type": "frame_detail", "frame": 42}],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "verified"


# ---------------------------------------------------------------------------
# 4. Claim Status Validation — Likely
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_likely_claim_requires_evidence_refs(
    client: AsyncClient, admin_token: str
):
    """Likely claims are rejected unless they have at least one evidence_ref."""
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_and_run_analysis(client, admin_token, artifact_id)
    map_resp = await client.post(
        f"/api/analysis-runs/{run_id}/evidence-map",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    map_id = map_resp.json()["id"]

    resp = await client.post(
        f"/api/evidence-maps/{map_id}/claims",
        json={
            "claim_text": "DNS timeout likely causing app slowness",
            "status": "likely",
            "key_facts": ["3 DNS timeouts observed"],
            "evidence_refs": [],  # empty — should be rejected
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422
    assert "evidence" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_likely_claim_with_evidence_refs_accepted(
    client: AsyncClient, admin_token: str
):
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_and_run_analysis(client, admin_token, artifact_id)
    map_resp = await client.post(
        f"/api/analysis-runs/{run_id}/evidence-map",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    map_id = map_resp.json()["id"]

    resp = await client.post(
        f"/api/evidence-maps/{map_id}/claims",
        json={
            "claim_text": "DNS timeout likely causing app slowness",
            "status": "likely",
            "key_facts": ["3 DNS timeouts"],
            "evidence_refs": [{"type": "packet_subset", "filter": "dns"}],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "likely"


# ---------------------------------------------------------------------------
# 5. Claim Status Validation — Hypothesis
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hypothesis_requires_verification_step(
    client: AsyncClient, admin_token: str
):
    """Hypotheses require a verification_step."""
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_and_run_analysis(client, admin_token, artifact_id)
    map_resp = await client.post(
        f"/api/analysis-runs/{run_id}/evidence-map",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    map_id = map_resp.json()["id"]

    resp = await client.post(
        f"/api/evidence-maps/{map_id}/claims",
        json={
            "claim_text": "Firewall may be dropping packets",
            "status": "hypothesis",
            "key_facts": ["Asymmetric traffic observed"],
            "evidence_refs": [],
            # no verification_step — should be rejected
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422
    assert "verification" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_hypothesis_with_verification_step_accepted(
    client: AsyncClient, admin_token: str
):
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_and_run_analysis(client, admin_token, artifact_id)
    map_resp = await client.post(
        f"/api/analysis-runs/{run_id}/evidence-map",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    map_id = map_resp.json()["id"]

    resp = await client.post(
        f"/api/evidence-maps/{map_id}/claims",
        json={
            "claim_text": "Firewall may be dropping packets",
            "status": "hypothesis",
            "key_facts": ["Asymmetric traffic"],
            "evidence_refs": [],
            "verification_step": "Compare capture from both sides of the firewall",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "hypothesis"
    assert resp.json()["verification_step"] == "Compare capture from both sides of the firewall"


# ---------------------------------------------------------------------------
# 6. Claim Status Validation — Unsupported
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unsupported_claim_can_be_created(
    client: AsyncClient, admin_token: str
):
    """Unsupported claims can exist (to capture rejected AI output)."""
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_and_run_analysis(client, admin_token, artifact_id)
    map_resp = await client.post(
        f"/api/analysis-runs/{run_id}/evidence-map",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    map_id = map_resp.json()["id"]

    resp = await client.post(
        f"/api/evidence-maps/{map_id}/claims",
        json={
            "claim_text": "Network is slow because of aliens",
            "status": "unsupported",
            "key_facts": ["No supporting evidence"],
            "evidence_refs": [],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "unsupported"


@pytest.mark.asyncio
async def test_unsupported_claim_cannot_be_marked_reportable(
    client: AsyncClient, admin_token: str
):
    """Unsupported claims cannot be marked reportable."""
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_and_run_analysis(client, admin_token, artifact_id)
    map_resp = await client.post(
        f"/api/analysis-runs/{run_id}/evidence-map",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    map_id = map_resp.json()["id"]

    claim_resp = await client.post(
        f"/api/evidence-maps/{map_id}/claims",
        json={
            "claim_text": "No evidence for this",
            "status": "unsupported",
            "key_facts": [],
            "evidence_refs": [],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    claim_id = claim_resp.json()["id"]

    resp = await client.patch(
        f"/api/claims/{claim_id}/reportable",
        json={"is_reportable": True},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422
    assert "reportable" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 7. Reportable — Positive Cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verified_claim_can_be_marked_reportable(
    client: AsyncClient, admin_token: str
):
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_and_run_analysis(client, admin_token, artifact_id)
    map_resp = await client.post(
        f"/api/analysis-runs/{run_id}/evidence-map",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    map_id = map_resp.json()["id"]

    claim_resp = await client.post(
        f"/api/evidence-maps/{map_id}/claims",
        json={
            "claim_text": "TCP handshake failure",
            "status": "verified",
            "key_facts": ["SYN, no SYN-ACK"],
            "evidence_refs": [{"type": "frame_detail", "frame": 1}],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    claim_id = claim_resp.json()["id"]

    resp = await client.patch(
        f"/api/claims/{claim_id}/reportable",
        json={"is_reportable": True},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_reportable"] is True


@pytest.mark.asyncio
async def test_likely_claim_can_be_marked_reportable(
    client: AsyncClient, admin_token: str
):
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_and_run_analysis(client, admin_token, artifact_id)
    map_resp = await client.post(
        f"/api/analysis-runs/{run_id}/evidence-map",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    map_id = map_resp.json()["id"]

    claim_resp = await client.post(
        f"/api/evidence-maps/{map_id}/claims",
        json={
            "claim_text": "Likely DNS issue",
            "status": "likely",
            "key_facts": ["DNS timeout observed"],
            "evidence_refs": [{"type": "packet_subset", "filter": "dns.time"}],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    claim_id = claim_resp.json()["id"]

    resp = await client.patch(
        f"/api/claims/{claim_id}/reportable",
        json={"is_reportable": True},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_reportable"] is True


@pytest.mark.asyncio
async def test_hypothesis_cannot_be_marked_reportable(
    client: AsyncClient, admin_token: str
):
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_and_run_analysis(client, admin_token, artifact_id)
    map_resp = await client.post(
        f"/api/analysis-runs/{run_id}/evidence-map",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    map_id = map_resp.json()["id"]

    claim_resp = await client.post(
        f"/api/evidence-maps/{map_id}/claims",
        json={
            "claim_text": "Maybe firewall",
            "status": "hypothesis",
            "key_facts": [],
            "evidence_refs": [],
            "verification_step": "Capture from both sides",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    claim_id = claim_resp.json()["id"]

    resp = await client.patch(
        f"/api/claims/{claim_id}/reportable",
        json={"is_reportable": True},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 8. Update Claim Status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_claim_status_can_be_updated_with_validation(
    client: AsyncClient, admin_token: str
):
    """Update status from hypothesis → verified (providing evidence_refs)."""
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_and_run_analysis(client, admin_token, artifact_id)
    map_resp = await client.post(
        f"/api/analysis-runs/{run_id}/evidence-map",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    map_id = map_resp.json()["id"]

    claim_resp = await client.post(
        f"/api/evidence-maps/{map_id}/claims",
        json={
            "claim_text": "Suspect TCP issue",
            "status": "hypothesis",
            "key_facts": ["TCP retransmissions"],
            "evidence_refs": [],
            "verification_step": "Check retransmission stats",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    claim_id = claim_resp.json()["id"]

    # Promote to verified — must provide evidence_refs at update time
    resp = await client.patch(
        f"/api/claims/{claim_id}/status",
        json={
            "status": "verified",
            "evidence_refs": [{"type": "frame_detail", "frame": 5}],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "verified"


@pytest.mark.asyncio
async def test_claim_status_update_rejected_if_new_status_invalid(
    client: AsyncClient, admin_token: str
):
    """Promoting to verified without evidence_refs fails."""
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_and_run_analysis(client, admin_token, artifact_id)
    map_resp = await client.post(
        f"/api/analysis-runs/{run_id}/evidence-map",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    map_id = map_resp.json()["id"]

    claim_resp = await client.post(
        f"/api/evidence-maps/{map_id}/claims",
        json={
            "claim_text": "Something",
            "status": "hypothesis",
            "key_facts": [],
            "evidence_refs": [],
            "verification_step": "Check X",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    claim_id = claim_resp.json()["id"]

    resp = await client.patch(
        f"/api/claims/{claim_id}/status",
        json={"status": "verified"},  # no evidence_refs — rejected
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 9. Evidence Cards
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evidence_cards_show_status_facts_links_actions(
    client: AsyncClient, admin_token: str
):
    """Evidence Cards render claim status, key facts, links, and actions."""
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_and_run_analysis(client, admin_token, artifact_id)
    map_resp = await client.post(
        f"/api/analysis-runs/{run_id}/evidence-map",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    map_id = map_resp.json()["id"]

    await client.post(
        f"/api/evidence-maps/{map_id}/claims",
        json={
            "claim_text": "TCP retransmission detected on stream 7",
            "status": "verified",
            "key_facts": ["Retransmission rate: 5%", "Affected stream: TCP stream 7"],
            "evidence_refs": [
                {"type": "frame_detail", "frame": 42},
                {"type": "follow_stream", "stream_id": 7},
            ],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.get(
        f"/api/evidence-maps/{map_id}/cards",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    cards = resp.json()
    assert len(cards) == 1
    card = cards[0]
    assert card["status"] == "verified"
    assert card["claim_text"] == "TCP retransmission detected on stream 7"
    assert len(card["key_facts"]) == 2
    assert len(card["evidence_refs"]) == 2
    assert "actions" in card
    # Default actions should include at least annotate and add_to_report
    action_types = [a["type"] for a in card["actions"]]
    assert "annotate" in action_types
    assert "add_to_report" in action_types


# ---------------------------------------------------------------------------
# 10. Auth Guards
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unauthenticated_evidence_map_rejected(client: AsyncClient):
    resp = await client.post("/api/analysis-runs/1/evidence-map")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthenticated_claims_rejected(client: AsyncClient):
    resp = await client.post("/api/evidence-maps/1/claims", json={
        "claim_text": "x", "status": "unsupported", "key_facts": [], "evidence_refs": [],
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthenticated_cards_rejected(client: AsyncClient):
    resp = await client.get("/api/evidence-maps/1/cards")
    assert resp.status_code == 401
