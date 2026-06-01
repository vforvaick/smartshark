"""Tests for Issue #12: Implement Scoped Analysis from selected scope.

Acceptance criteria:
- Analyst can define a scoped analysis using one or more supported scope types
- Scoped Analysis checks run only inside the selected boundary
- Scope is recorded in Analysis Run provenance
- Results link back to scoped packet/flow/timeline evidence
- Invalid or empty scopes produce actionable feedback
"""

import pytest
from httpx import AsyncClient


# ── Helper ──────────────────────────────────────────────────────────────────

async def _create_artifact(client: AsyncClient, admin_token: str) -> int:
    """Upload a valid PCAP and return the artifact ID."""
    pcap_magic = bytes([0xd4, 0xc3, 0xb2, 0xa1]) + b"\x00" * 60
    response = await client.post(
        "/api/captures/upload",
        files={"file": ("test.pcap", pcap_magic, "application/octet-stream")},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    return response.json()["id"]


async def _create_run(client: AsyncClient, admin_token: str, artifact_id: int) -> int:
    """Create an analysis run and return its ID."""
    response = await client.post(
        "/api/analysis-runs",
        json={"capture_artifact_id": artifact_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    return response.json()["id"]


# ── Scope creation tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_time_window_scope(client: AsyncClient, admin_token: str):
    """Analyst can define a time_window scope."""
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    response = await client.post(
        f"/api/analysis-runs/{run_id}/scope",
        json={"scope_type": "time_window", "scope_params": {"time_start": "2026-01-01T00:00:00Z", "time_end": "2026-01-01T01:00:00Z"}},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["scope_type"] == "time_window"
    assert data["scope_params"]["time_start"] == "2026-01-01T00:00:00Z"
    assert data["scope_params"]["time_end"] == "2026-01-01T01:00:00Z"
    assert data["analysis_run_id"] == run_id


@pytest.mark.asyncio
async def test_create_endpoint_scope(client: AsyncClient, admin_token: str):
    """Analyst can define an endpoint scope."""
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    response = await client.post(
        f"/api/analysis-runs/{run_id}/scope",
        json={"scope_type": "endpoint", "scope_params": {"ip": "192.168.1.1"}},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["scope_type"] == "endpoint"
    assert data["scope_params"]["ip"] == "192.168.1.1"


@pytest.mark.asyncio
async def test_create_conversation_scope(client: AsyncClient, admin_token: str):
    """Analyst can define a conversation scope."""
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    response = await client.post(
        f"/api/analysis-runs/{run_id}/scope",
        json={"scope_type": "conversation", "scope_params": {"conversation_id": "192.168.1.1-192.168.1.2-TCP"}},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    assert response.json()["scope_type"] == "conversation"


@pytest.mark.asyncio
async def test_create_display_filter_scope(client: AsyncClient, admin_token: str):
    """Analyst can define a display_filter scope."""
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    response = await client.post(
        f"/api/analysis-runs/{run_id}/scope",
        json={"scope_type": "display_filter", "scope_params": {"filter_text": "tcp.port == 80"}},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    assert response.json()["scope_params"]["filter_text"] == "tcp.port == 80"


@pytest.mark.asyncio
async def test_create_symptom_scope(client: AsyncClient, admin_token: str):
    """Analyst can define a symptom scope."""
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    response = await client.post(
        f"/api/analysis-runs/{run_id}/scope",
        json={"scope_type": "symptom", "scope_params": {"description": "DNS timeouts on port 53"}},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    assert response.json()["scope_params"]["description"] == "DNS timeouts on port 53"


@pytest.mark.asyncio
async def test_create_playbook_scope(client: AsyncClient, admin_token: str):
    """Analyst can define a playbook scope."""
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    response = await client.post(
        f"/api/analysis-runs/{run_id}/scope",
        json={"scope_type": "playbook", "scope_params": {"playbook_name": "tcp_health"}},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    assert response.json()["scope_params"]["playbook_name"] == "tcp_health"


@pytest.mark.asyncio
async def test_get_scope_for_run(client: AsyncClient, admin_token: str):
    """Scope can be retrieved for an analysis run."""
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    await client.post(
        f"/api/analysis-runs/{run_id}/scope",
        json={"scope_type": "endpoint", "scope_params": {"ip": "10.0.0.1"}},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    response = await client.get(
        f"/api/analysis-runs/{run_id}/scope",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["scope_type"] == "endpoint"


# ── Combined scope types ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_combined_scope_types(client: AsyncClient, admin_token: str):
    """Analyst can define a scope with combined types (time_window + endpoint)."""
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    response = await client.post(
        f"/api/analysis-runs/{run_id}/scope",
        json={
            "scope_type": "combined",
            "scope_params": {
                "time_start": "2026-01-01T00:00:00Z",
                "time_end": "2026-01-01T01:00:00Z",
                "ip": "192.168.1.1",
            },
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["scope_type"] == "combined"
    assert data["scope_params"]["time_start"] == "2026-01-01T00:00:00Z"
    assert data["scope_params"]["ip"] == "192.168.1.1"


# ── Scoped analysis execution ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_scoped_analysis_runs_checks_within_boundary(client: AsyncClient, admin_token: str):
    """Scoped Analysis checks run only inside the selected boundary."""
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    # Define scope
    await client.post(
        f"/api/analysis-runs/{run_id}/scope",
        json={"scope_type": "endpoint", "scope_params": {"ip": "192.168.1.1"}},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Run scoped analysis
    response = await client.post(
        f"/api/analysis-runs/{run_id}/scoped-analysis",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("completed", "partial")


@pytest.mark.asyncio
async def test_scope_recorded_in_provenance(client: AsyncClient, admin_token: str):
    """Scope is recorded in Analysis Run provenance — check results reference scope."""
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    # Define scope
    await client.post(
        f"/api/analysis-runs/{run_id}/scope",
        json={"scope_type": "time_window", "scope_params": {"time_start": "2026-01-01T00:00:00Z", "time_end": "2026-01-01T01:00:00Z"}},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Run scoped analysis
    await client.post(
        f"/api/analysis-runs/{run_id}/scoped-analysis",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Check results link back to scoped evidence
    results_resp = await client.get(
        f"/api/analysis-runs/{run_id}/check-results",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert results_resp.status_code == 200
    results = results_resp.json()
    assert len(results) > 0
    # Evidence refs should contain scope information for non-skipped checks
    for cr in results:
        assert "evidence_refs" in cr
        # Skipped checks may have empty evidence_refs — only validate completed checks
        if cr["status"] != "skipped":
            scope_refs = [r for r in cr["evidence_refs"] if r.get("scope_boundary") is not None]
            assert len(scope_refs) > 0, f"Check '{cr['check_name']}' has no scope boundary references"


@pytest.mark.asyncio
async def test_results_link_back_to_scoped_evidence(client: AsyncClient, admin_token: str):
    """Results link back to scoped packet/flow/timeline evidence."""
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    await client.post(
        f"/api/analysis-runs/{run_id}/scope",
        json={"scope_type": "conversation", "scope_params": {"conversation_id": "conv-1"}},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await client.post(
        f"/api/analysis-runs/{run_id}/scoped-analysis",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    results_resp = await client.get(
        f"/api/analysis-runs/{run_id}/check-results",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    results = results_resp.json()
    # Each check result should have evidence_refs with scoped context
    all_refs = []
    for cr in results:
        all_refs.extend(cr["evidence_refs"])
    # At least some refs should exist (checks produced evidence within scope)
    assert len(all_refs) > 0


# ── Validation / error cases ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_invalid_scope_params_produce_actionable_feedback(client: AsyncClient, admin_token: str):
    """Invalid scope params produce actionable feedback."""
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    # time_window without required time_start/time_end but with empty params
    response = await client.post(
        f"/api/analysis-runs/{run_id}/scope",
        json={"scope_type": "time_window", "scope_params": {}},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    # Should mention what's wrong
    assert "time_start" in data["detail"] or "time_end" in data["detail"] or "empty" in data["detail"].lower() or "required" in data["detail"].lower()


@pytest.mark.asyncio
async def test_empty_scope_params_rejected(client: AsyncClient, admin_token: str):
    """Empty scope_params rejected."""
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    response = await client.post(
        f"/api/analysis-runs/{run_id}/scope",
        json={"scope_type": "endpoint", "scope_params": {}},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_scope_type_rejected(client: AsyncClient, admin_token: str):
    """Unsupported scope_type is rejected."""
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    response = await client.post(
        f"/api/analysis-runs/{run_id}/scope",
        json={"scope_type": "nonexistent_type", "scope_params": {"foo": "bar"}},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_scope_for_nonexistent_run_returns_404(client: AsyncClient, admin_token: str):
    """Non-existent run returns 404."""
    response = await client.post(
        "/api/analysis-runs/99999/scope",
        json={"scope_type": "endpoint", "scope_params": {"ip": "10.0.0.1"}},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_scope_for_nonexistent_run_returns_404(client: AsyncClient, admin_token: str):
    """Getting scope for non-existent run returns 404."""
    response = await client.get(
        "/api/analysis-runs/99999/scope",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_scoped_analysis_without_scope_rejected(client: AsyncClient, admin_token: str):
    """Running scoped analysis without defining a scope is rejected."""
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    response = await client.post(
        f"/api/analysis-runs/{run_id}/scoped-analysis",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 409 or response.status_code == 422


@pytest.mark.asyncio
async def test_scoped_analysis_for_nonexistent_run_returns_404(client: AsyncClient, admin_token: str):
    """Scoped analysis for non-existent run returns 404."""
    response = await client.post(
        "/api/analysis-runs/99999/scoped-analysis",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_scope_rejected(client: AsyncClient):
    """Unauthenticated access to scope endpoints is rejected."""
    response = await client.post(
        "/api/analysis-runs/1/scope",
        json={"scope_type": "endpoint", "scope_params": {"ip": "10.0.0.1"}},
    )
    assert response.status_code == 401

    response = await client.get("/api/analysis-runs/1/scope")
    assert response.status_code == 401

    response = await client.post("/api/analysis-runs/1/scoped-analysis")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_scope_already_defined_rejected(client: AsyncClient, admin_token: str):
    """Cannot define scope twice for the same run."""
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    # First scope
    resp1 = await client.post(
        f"/api/analysis-runs/{run_id}/scope",
        json={"scope_type": "endpoint", "scope_params": {"ip": "10.0.0.1"}},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp1.status_code == 201

    # Second scope — should be rejected (one scope per run)
    resp2 = await client.post(
        f"/api/analysis-runs/{run_id}/scope",
        json={"scope_type": "time_window", "scope_params": {"time_start": "2026-01-01T00:00:00Z", "time_end": "2026-01-01T01:00:00Z"}},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp2.status_code == 409
