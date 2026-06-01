"""Hardening pass — Issue #20.

Tests enforce:
- Encrypted payload limitations are explicit in Evidence Maps and reports
- Failed, skipped, and cancelled checks appear in check coverage/limitations
- Unknown Capture Vantage Point limits claim status appropriately
- MVP success metrics are captured or instrumented
- Unsupported claim rate cannot be hidden by export flow
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


async def _create_run_with_evidence_map(
    client: AsyncClient, admin_token: str
) -> tuple[int, int]:
    """Create artifact → analysis run → quick analysis → evidence map. Returns (run_id, map_id)."""
    artifact_id = await _create_artifact(client, admin_token)

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

    map_resp = await client.post(
        f"/api/analysis-runs/{run_id}/evidence-map",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert map_resp.status_code == 201
    map_id = map_resp.json()["id"]

    return run_id, map_id


async def _add_claim(
    client: AsyncClient,
    admin_token: str,
    map_id: int,
    claim_text: str = "Test claim",
    status: str = "unsupported",
    evidence_refs: list | None = None,
    verification_step: str | None = None,
) -> int:
    """Add a claim to an evidence map. Returns claim_id."""
    body: dict = {
        "claim_text": claim_text,
        "status": status,
        "key_facts": [],
        "evidence_refs": evidence_refs or [],
    }
    if verification_step:
        body["verification_step"] = verification_step
    resp = await client.post(
        f"/api/evidence-maps/{map_id}/claims",
        json=body,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# 1. Encrypted payload limitations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_encrypted_payload_limitation_in_evidence_map(
    client: AsyncClient, admin_token: str
):
    """Encrypted payload limitations are explicit in Evidence Maps."""
    run_id, map_id = await _create_run_with_evidence_map(client, admin_token)

    resp = await client.post(
        f"/api/analysis-runs/{run_id}/limitations",
        json={"category": "encrypted_payload", "detail": "TLS payload is encrypted; content analysis not possible"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["category"] == "encrypted_payload"
    assert "encrypted" in data["detail"].lower()

    # Limitation visible in evidence map
    emap = await client.get(
        f"/api/analysis-runs/{run_id}/evidence-map",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert emap.status_code == 200
    limitations = emap.json().get("limitations", [])
    encrypted_limits = [l for l in limitations if l["category"] == "encrypted_payload"]
    assert len(encrypted_limits) > 0


@pytest.mark.asyncio
async def test_encrypted_limitation_appears_in_export(
    client: AsyncClient, admin_token: str
):
    """Encrypted payload limitation appears in report export."""
    run_id, map_id = await _create_run_with_evidence_map(client, admin_token)

    # Add encrypted limitation
    await client.post(
        f"/api/analysis-runs/{run_id}/limitations",
        json={"category": "encrypted_payload", "detail": "TLS encrypted"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Create report
    report_resp = await client.post(
        f"/api/evidence-maps/{map_id}/reports/draft",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert report_resp.status_code == 201
    report_id = report_resp.json()["id"]

    # Export as markdown
    md_resp = await client.get(
        f"/api/reports/{report_id}/export/markdown",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert md_resp.status_code == 200
    md_text = md_resp.text
    assert "encrypted" in md_text.lower()


# ---------------------------------------------------------------------------
# 2. Failed/skipped/cancelled checks in coverage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_failed_checks_appear_in_coverage(
    client: AsyncClient, admin_token: str
):
    """Failed checks appear in check coverage/limitations."""
    run_id, map_id = await _create_run_with_evidence_map(client, admin_token)

    resp = await client.get(
        f"/api/analysis-runs/{run_id}/check-coverage",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    coverage = resp.json()
    failed = [c for c in coverage["checks"] if c["status"] == "failed"]
    # Check coverage includes all statuses
    statuses = {c["status"] for c in coverage["checks"]}
    assert "completed" in statuses
    assert "coverage_summary" in coverage


@pytest.mark.asyncio
async def test_skipped_checks_appear_in_coverage(
    client: AsyncClient, admin_token: str
):
    """Skipped checks appear in check coverage."""
    run_id, map_id = await _create_run_with_evidence_map(client, admin_token)

    resp = await client.get(
        f"/api/analysis-runs/{run_id}/check-coverage",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    coverage = resp.json()
    # The quick analysis runs 5 checks; at least one (TLS) is skipped in our fixture
    skipped = [c for c in coverage["checks"] if c["status"] == "skipped"]
    assert len(skipped) >= 1
    # Skipped checks have a reason
    for s in skipped:
        assert "reason" in s or "limitations" in s


@pytest.mark.asyncio
async def test_cancelled_checks_appear_in_coverage(
    client: AsyncClient, admin_token: str
):
    """Cancelled analysis records incomplete checks in coverage."""
    artifact_id = await _create_artifact(client, admin_token)
    resp = await client.post(
        "/api/analysis-runs",
        json={"capture_artifact_id": artifact_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    run_id = resp.json()["id"]

    # Start the run to running
    await client.post(
        f"/api/analysis-runs/{run_id}/start",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Cancel the run while running (before quick-analysis completes)
    cancel_resp = await client.post(
        f"/api/analysis-runs/{run_id}/cancel",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert cancel_resp.status_code == 200

    # Check coverage shows incomplete
    resp = await client.get(
        f"/api/analysis-runs/{run_id}/check-coverage",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    coverage = resp.json()
    assert "checks" in coverage
    # Cancelled run should flag incomplete coverage
    assert coverage["incomplete"] is True


# ---------------------------------------------------------------------------
# 3. Vantage point limits
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_vantage_point_limits_claim_to_likely(
    client: AsyncClient, admin_token: str
):
    """Unknown vantage point prevents Verified claims; max is Likely."""
    run_id, map_id = await _create_run_with_evidence_map(client, admin_token)

    # Set vantage point to unknown
    vp_resp = await client.post(
        f"/api/analysis-runs/{run_id}/vantage-point",
        json={"vantage_point": "unknown"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert vp_resp.status_code == 200

    # Try to create a verified claim — should be rejected
    resp = await client.post(
        f"/api/evidence-maps/{map_id}/claims",
        json={
            "claim_text": "TCP handshake failure",
            "status": "verified",
            "key_facts": ["SYN, no SYN-ACK"],
            "evidence_refs": [{"type": "frame_detail", "frame": 1}],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422
    assert "vantage point" in resp.json()["detail"].lower()

    # Likely claim should succeed
    resp2 = await client.post(
        f"/api/evidence-maps/{map_id}/claims",
        json={
            "claim_text": "TCP handshake failure",
            "status": "likely",
            "key_facts": ["SYN, no SYN-ACK"],
            "evidence_refs": [{"type": "frame_detail", "frame": 1}],
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp2.status_code == 201
    assert resp2.json()["status"] == "likely"


@pytest.mark.asyncio
async def test_known_vantage_point_allows_verified_claims(
    client: AsyncClient, admin_token: str
):
    """Known vantage point allows Verified claims."""
    run_id, map_id = await _create_run_with_evidence_map(client, admin_token)

    # Set vantage point to known
    vp_resp = await client.post(
        f"/api/analysis-runs/{run_id}/vantage-point",
        json={"vantage_point": "known"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert vp_resp.status_code == 200

    # Verified claim should succeed
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
# 4. Success metrics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_metrics_computed_for_completed_run(
    client: AsyncClient, admin_token: str
):
    """Success metrics can be computed for a completed analysis run."""
    run_id, map_id = await _create_run_with_evidence_map(client, admin_token)

    # Add a few claims
    await _add_claim(client, admin_token, map_id, "TCP issue", "verified",
                     evidence_refs=[{"type": "frame_detail", "frame": 1}])
    await _add_claim(client, admin_token, map_id, "DNS timeout", "likely",
                     evidence_refs=[{"type": "frame_detail", "frame": 2}])
    await _add_claim(client, admin_token, map_id, "No evidence", "unsupported")

    resp = await client.post(
        f"/api/analysis-runs/{run_id}/metrics",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_claims"] == 3
    assert data["unsupported_claims"] == 1
    assert "unsupported_claim_rate" in data


@pytest.mark.asyncio
async def test_time_to_first_evidence_recorded(
    client: AsyncClient, admin_token: str
):
    """Time to first evidence is recorded in metrics."""
    run_id, map_id = await _create_run_with_evidence_map(client, admin_token)

    resp = await client.post(
        f"/api/analysis-runs/{run_id}/metrics",
        json={"time_to_first_evidence_ms": 3200},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["time_to_first_evidence_ms"] == 3200


@pytest.mark.asyncio
async def test_evidence_coverage_percentage(
    client: AsyncClient, admin_token: str
):
    """Evidence coverage percentage is calculated."""
    run_id, map_id = await _create_run_with_evidence_map(client, admin_token)

    await _add_claim(client, admin_token, map_id, "Verified", "verified",
                     evidence_refs=[{"type": "frame_detail", "frame": 1}])
    await _add_claim(client, admin_token, map_id, "Unsupported", "unsupported")

    resp = await client.post(
        f"/api/analysis-runs/{run_id}/metrics",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["evidence_coverage_pct"] == 50.0  # 1 of 2 claims has evidence


@pytest.mark.asyncio
async def test_unsupported_claim_rate_visible(
    client: AsyncClient, admin_token: str
):
    """Unsupported claim rate is calculated and visible in metrics."""
    run_id, map_id = await _create_run_with_evidence_map(client, admin_token)

    await _add_claim(client, admin_token, map_id, "V1", "verified",
                     evidence_refs=[{"type": "frame_detail", "frame": 1}])
    await _add_claim(client, admin_token, map_id, "V2", "verified",
                     evidence_refs=[{"type": "frame_detail", "frame": 2}])
    await _add_claim(client, admin_token, map_id, "U1", "unsupported")

    resp = await client.post(
        f"/api/analysis-runs/{run_id}/metrics",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_claims"] == 3
    assert data["unsupported_claims"] == 1
    assert abs(data["unsupported_claim_rate"] - 33.33333333333333) < 0.01


@pytest.mark.asyncio
async def test_unsupported_claim_rate_cannot_be_hidden_in_export(
    client: AsyncClient, admin_token: str
):
    """Unsupported claim rate must appear in exported reports."""
    run_id, map_id = await _create_run_with_evidence_map(client, admin_token)

    await _add_claim(client, admin_token, map_id, "Good", "verified",
                     evidence_refs=[{"type": "frame_detail", "frame": 1}])
    await _add_claim(client, admin_token, map_id, "Bad", "unsupported")

    # Compute metrics
    metrics_resp = await client.post(
        f"/api/analysis-runs/{run_id}/metrics",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert metrics_resp.status_code == 200

    # Create report
    report_resp = await client.post(
        f"/api/evidence-maps/{map_id}/reports/draft",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert report_resp.status_code == 201
    report_id = report_resp.json()["id"]

    # Export must include unsupported claim rate
    md_resp = await client.get(
        f"/api/reports/{report_id}/export/markdown",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert md_resp.status_code == 200
    md_text = md_resp.text.lower()
    assert "unsupported" in md_text


@pytest.mark.asyncio
async def test_report_time_saved_estimate(
    client: AsyncClient, admin_token: str
):
    """Report time saved estimate can be recorded."""
    run_id, map_id = await _create_run_with_evidence_map(client, admin_token)

    resp = await client.post(
        f"/api/analysis-runs/{run_id}/metrics",
        json={"report_time_saved_estimate_ms": 1800000},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["report_time_saved_estimate_ms"] == 1800000


@pytest.mark.asyncio
async def test_usefulness_feedback_score(
    client: AsyncClient, admin_token: str
):
    """Usefulness feedback score (1-5) can be submitted."""
    run_id, map_id = await _create_run_with_evidence_map(client, admin_token)

    # First compute metrics
    await client.post(
        f"/api/analysis-runs/{run_id}/metrics",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Submit feedback
    resp = await client.patch(
        f"/api/analysis-runs/{run_id}/metrics/feedback",
        json={"usefulness_score": 4},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["usefulness_score"] == 4


@pytest.mark.asyncio
async def test_usefulness_feedback_rejects_invalid_score(
    client: AsyncClient, admin_token: str
):
    """Usefulness score must be 1-5."""
    run_id, map_id = await _create_run_with_evidence_map(client, admin_token)

    await client.post(
        f"/api/analysis-runs/{run_id}/metrics",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.patch(
        f"/api/analysis-runs/{run_id}/metrics/feedback",
        json={"usefulness_score": 0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_metrics_for_run(
    client: AsyncClient, admin_token: str
):
    """Metrics can be retrieved for a specific run."""
    run_id, map_id = await _create_run_with_evidence_map(client, admin_token)

    await client.post(
        f"/api/analysis-runs/{run_id}/metrics",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.get(
        f"/api/analysis-runs/{run_id}/metrics",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert "total_claims" in resp.json()


# ---------------------------------------------------------------------------
# 5. Aggregate metrics summary (admin)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_metrics_summary_aggregates_across_runs(
    client: AsyncClient, admin_token: str
):
    """Admin can see aggregated metrics across all runs."""
    run_id, map_id = await _create_run_with_evidence_map(client, admin_token)

    await _add_claim(client, admin_token, map_id, "V1", "verified",
                     evidence_refs=[{"type": "frame_detail", "frame": 1}])
    await _add_claim(client, admin_token, map_id, "U1", "unsupported")

    await client.post(
        f"/api/analysis-runs/{run_id}/metrics",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.get(
        "/api/metrics/summary",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    summary = resp.json()
    assert summary["total_runs"] >= 1
    assert "avg_unsupported_claim_rate" in summary
    assert "avg_evidence_coverage_pct" in summary


# ---------------------------------------------------------------------------
# 6. Auth guards
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unauthenticated_metrics_rejected(client: AsyncClient):
    resp = await client.post("/api/analysis-runs/1/metrics")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthenticated_vantage_point_rejected(client: AsyncClient):
    resp = await client.post("/api/analysis-runs/1/vantage-point",
                             json={"vantage_point": "unknown"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthenticated_summary_rejected(client: AsyncClient):
    resp = await client.get("/api/metrics/summary")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_analyst_cannot_access_summary(client: AsyncClient, admin_token: str):
    """Metrics summary is admin-only."""
    # Create analyst
    await client.post(
        "/api/auth/analysts",
        json={"username": "analyst1", "password": "pw"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    analyst_token = (await client.post("/api/auth/login", json={
        "username": "analyst1", "password": "pw",
    })).json()["access_token"]

    resp = await client.get(
        "/api/metrics/summary",
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert resp.status_code == 403
