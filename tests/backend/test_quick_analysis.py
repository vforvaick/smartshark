"""TDD tests for Issue #8: Quick Analysis with default triage fan-out.

Proves:
- Quick Analysis runs with and without Issue Brief
- Default generic playbook fan-out runs all 5 checks
- Each check produces a CheckResult (completed/skipped/failed)
- Progress messages are recorded during analysis
- Limitations are recorded when evidence is insufficient
- Check results are retrievable
- Unauthenticated access is rejected
"""

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helper — creates a capture artifact + index + analysis run for testing
# ---------------------------------------------------------------------------

async def _create_analysis_run_with_artifact(
    client: AsyncClient, admin_token: str
) -> dict:
    """Upload a valid PCAP, build its index, create an analysis run, return run data."""
    # Upload a minimal valid PCAP (pcap magic + enough bytes for header)
    pcap_magic = b"\xd4\xc3\xb2\xa1" + b"\x00" * 44  # 48 bytes: valid pcap header
    upload = await client.post(
        "/api/captures/upload",
        files={"file": ("test.pcap", pcap_magic, "application/octet-stream")},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert upload.status_code == 201
    artifact_id = upload.json()["id"]

    # Build capture index
    idx = await client.post(
        f"/api/captures/{artifact_id}/index",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert idx.status_code == 201

    # Create analysis run
    run = await client.post(
        "/api/analysis-runs",
        json={"capture_artifact_id": artifact_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert run.status_code == 201
    return run.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_quick_analysis_without_issue_brief(
    client: AsyncClient, admin_token: str
):
    """Analyst can start Quick Analysis without an Issue Brief."""
    run = await _create_analysis_run_with_artifact(client, admin_token)

    # Start quick analysis
    response = await client.post(
        f"/api/analysis-runs/{run['id']}/quick-analysis",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("completed", "partial")


@pytest.mark.asyncio
async def test_start_quick_analysis_with_issue_brief(
    client: AsyncClient, admin_token: str
):
    """Analyst can start Quick Analysis with an Issue Brief."""
    run = await _create_analysis_run_with_artifact(client, admin_token)

    response = await client.post(
        f"/api/analysis-runs/{run['id']}/quick-analysis",
        json={"issue_brief": "Users report slow HTTP responses from web server"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("completed", "partial")


@pytest.mark.asyncio
async def test_quick_analysis_runs_all_five_checks(
    client: AsyncClient, admin_token: str
):
    """Quick Analysis runs all 5 default playbook checks."""
    run = await _create_analysis_run_with_artifact(client, admin_token)

    await client.post(
        f"/api/analysis-runs/{run['id']}/quick-analysis",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    results = await client.get(
        f"/api/analysis-runs/{run['id']}/check-results",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert results.status_code == 200
    check_names = {r["check_name"] for r in results.json()}
    expected = {"tcp_health", "dns_resolution", "http_api", "tls_handshake", "path_visibility"}
    assert expected == check_names


@pytest.mark.asyncio
async def test_each_check_creates_check_result(
    client: AsyncClient, admin_token: str
):
    """Each check creates a CheckResult with a status."""
    run = await _create_analysis_run_with_artifact(client, admin_token)

    await client.post(
        f"/api/analysis-runs/{run['id']}/quick-analysis",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    results = await client.get(
        f"/api/analysis-runs/{run['id']}/check-results",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    for check in results.json():
        assert check["status"] in ("completed", "skipped", "failed")
        assert "summary" in check
        assert isinstance(check["summary"], str)


@pytest.mark.asyncio
async def test_quick_analysis_records_progress(
    client: AsyncClient, admin_token: str
):
    """Analysis records progress messages during execution."""
    run = await _create_analysis_run_with_artifact(client, admin_token)

    response = await client.post(
        f"/api/analysis-runs/{run['id']}/quick-analysis",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    data = response.json()
    # Progress should have been recorded
    assert len(data["progress"]) >= 1
    messages = [p["message"] for p in data["progress"]]
    # At least one progress message about starting analysis
    assert any("analysis" in m.lower() or "check" in m.lower() for m in messages)


@pytest.mark.asyncio
async def test_tcp_health_check_completed(
    client: AsyncClient, admin_token: str
):
    """TCP Health check produces a result with evidence from timeline."""
    run = await _create_analysis_run_with_artifact(client, admin_token)

    await client.post(
        f"/api/analysis-runs/{run['id']}/quick-analysis",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    results = await client.get(
        f"/api/analysis-runs/{run['id']}/check-results",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    tcp = next(r for r in results.json() if r["check_name"] == "tcp_health")
    assert tcp["status"] == "completed"
    # The stub timeline has 1 retransmission and 1 reset — summary should mention them
    assert "retransmission" in tcp["summary"].lower() or "reset" in tcp["summary"].lower() or "tcp" in tcp["summary"].lower()


@pytest.mark.asyncio
async def test_dns_resolution_check_completed(
    client: AsyncClient, admin_token: str
):
    """DNS Resolution check produces a result from timeline data."""
    run = await _create_analysis_run_with_artifact(client, admin_token)

    await client.post(
        f"/api/analysis-runs/{run['id']}/quick-analysis",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    results = await client.get(
        f"/api/analysis-runs/{run['id']}/check-results",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    dns = next(r for r in results.json() if r["check_name"] == "dns_resolution")
    assert dns["status"] == "completed"
    # Stub has DNS queries and responses
    assert "dns" in dns["summary"].lower()


@pytest.mark.asyncio
async def test_tls_handshake_check_skipped_when_no_tls(
    client: AsyncClient, admin_token: str
):
    """TLS Handshake check is skipped when no TLS traffic present."""
    run = await _create_analysis_run_with_artifact(client, admin_token)

    await client.post(
        f"/api/analysis-runs/{run['id']}/quick-analysis",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    results = await client.get(
        f"/api/analysis-runs/{run['id']}/check-results",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    tls = next(r for r in results.json() if r["check_name"] == "tls_handshake")
    # Stub data has no TLS traffic — should be skipped
    assert tls["status"] == "skipped"


@pytest.mark.asyncio
async def test_limitations_recorded_when_evidence_insufficient(
    client: AsyncClient, admin_token: str
):
    """Limitations are recorded when evidence is insufficient."""
    run = await _create_analysis_run_with_artifact(client, admin_token)

    await client.post(
        f"/api/analysis-runs/{run['id']}/quick-analysis",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    results = await client.get(
        f"/api/analysis-runs/{run['id']}/check-results",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # At least one check should have limitations (TLS skipped, or path visibility partial)
    all_limitations = []
    for check in results.json():
        if check.get("limitations"):
            all_limitations.extend(check["limitations"])
    assert len(all_limitations) >= 1


@pytest.mark.asyncio
async def test_check_results_retrievable(
    client: AsyncClient, admin_token: str
):
    """Check results can be retrieved independently after analysis."""
    run = await _create_analysis_run_with_artifact(client, admin_token)

    # Run analysis
    await client.post(
        f"/api/analysis-runs/{run['id']}/quick-analysis",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Retrieve results separately
    results = await client.get(
        f"/api/analysis-runs/{run['id']}/check-results",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert results.status_code == 200
    data = results.json()
    assert len(data) == 5
    for check in data:
        assert "id" in check
        assert "check_name" in check
        assert "status" in check
        assert "summary" in check
        assert "evidence_refs" in check
        assert "limitations" in check


@pytest.mark.asyncio
async def test_quick_analysis_rejected_for_nonexistent_run(
    client: AsyncClient, admin_token: str
):
    """Quick analysis returns 404 for nonexistent run."""
    response = await client.post(
        "/api/analysis-runs/99999/quick-analysis",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_quick_analysis_rejected_for_non_pending_run(
    client: AsyncClient, admin_token: str
):
    """Quick analysis rejects a run that is already completed."""
    run = await _create_analysis_run_with_artifact(client, admin_token)

    # Run quick analysis once
    await client.post(
        f"/api/analysis-runs/{run['id']}/quick-analysis",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Try again — should be rejected (run is no longer pending)
    response = await client.post(
        f"/api/analysis-runs/{run['id']}/quick-analysis",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_check_results_return_404_for_nonexistent_run(
    client: AsyncClient, admin_token: str
):
    """Check results endpoint returns 404 for nonexistent run."""
    results = await client.get(
        "/api/analysis-runs/99999/check-results",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert results.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_quick_analysis_rejected(client: AsyncClient):
    """Unauthenticated access to quick analysis is rejected."""
    response = await client.post("/api/analysis-runs/1/quick-analysis")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_unauthenticated_check_results_rejected(client: AsyncClient):
    """Unauthenticated access to check results is rejected."""
    response = await client.get("/api/analysis-runs/1/check-results")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_evidence_refs_recorded_for_completed_checks(
    client: AsyncClient, admin_token: str
):
    """Completed checks record evidence references."""
    run = await _create_analysis_run_with_artifact(client, admin_token)

    await client.post(
        f"/api/analysis-runs/{run['id']}/quick-analysis",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    results = await client.get(
        f"/api/analysis-runs/{run['id']}/check-results",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    completed = [r for r in results.json() if r["status"] == "completed"]
    # At least some completed checks should have evidence refs
    has_refs = any(r["evidence_refs"] for r in completed)
    assert has_refs, "At least one completed check should have evidence references"
