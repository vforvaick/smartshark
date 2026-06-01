"""Tests for Issue #7: Analysis Run lifecycle and async job progress.

Covers: create, status transitions, progress messages, cancellation,
partial results, failure categories, listing, and auth requirements.
"""

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Create analysis run
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_analysis_run(client: AsyncClient, admin_token: str):
    """Analysis Run can be created for a capture artifact."""
    response = await client.post(
        "/api/analysis-runs",
        json={"capture_artifact_id": 1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["status"] == "pending"
    assert data["capture_artifact_id"] == 1


@pytest.mark.asyncio
async def test_create_analysis_run_starts_pending(client: AsyncClient, admin_token: str):
    """Newly created run is in pending status."""
    response = await client.post(
        "/api/analysis-runs",
        json={"capture_artifact_id": 1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.json()["status"] == "pending"


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_transitions_to_running(client: AsyncClient, admin_token: str):
    """Run can be started: pending → running."""
    create_resp = await client.post(
        "/api/analysis-runs",
        json={"capture_artifact_id": 1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    run_id = create_resp.json()["id"]

    start_resp = await client.post(
        f"/api/analysis-runs/{run_id}/start",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert start_resp.status_code == 200
    assert start_resp.json()["status"] == "running"


@pytest.mark.asyncio
async def test_run_transitions_to_completed(client: AsyncClient, admin_token: str):
    """Run can complete: pending → running → completed."""
    create_resp = await client.post(
        "/api/analysis-runs",
        json={"capture_artifact_id": 1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    run_id = create_resp.json()["id"]

    await client.post(
        f"/api/analysis-runs/{run_id}/start",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    complete_resp = await client.post(
        f"/api/analysis-runs/{run_id}/complete",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_cannot_start_non_pending_run(client: AsyncClient, admin_token: str):
    """Cannot start a run that is already running."""
    create_resp = await client.post(
        "/api/analysis-runs",
        json={"capture_artifact_id": 1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    run_id = create_resp.json()["id"]

    # Start it
    await client.post(
        f"/api/analysis-runs/{run_id}/start",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # Try to start again → conflict
    second_start = await client.post(
        f"/api/analysis-runs/{run_id}/start",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert second_start.status_code == 409


# ---------------------------------------------------------------------------
# Cancellation and partial results
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cancel_pending_run(client: AsyncClient, admin_token: str):
    """Pending run can be cancelled."""
    create_resp = await client.post(
        "/api/analysis-runs",
        json={"capture_artifact_id": 1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    run_id = create_resp.json()["id"]

    cancel_resp = await client.post(
        f"/api/analysis-runs/{run_id}/cancel",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_cancel_running_run_preserves_partial_results(client: AsyncClient, admin_token: str):
    """Cancelling a running run with progress → partial status."""
    create_resp = await client.post(
        "/api/analysis-runs",
        json={"capture_artifact_id": 1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    run_id = create_resp.json()["id"]

    # Start it
    await client.post(
        f"/api/analysis-runs/{run_id}/start",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # Add some progress
    await client.post(
        f"/api/analysis-runs/{run_id}/progress",
        json={"message": "Checked TCP health"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # Cancel
    cancel_resp = await client.post(
        f"/api/analysis-runs/{run_id}/cancel",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "partial"


@pytest.mark.asyncio
async def test_cancel_running_run_without_progress_is_cancelled(client: AsyncClient, admin_token: str):
    """Cancelling a running run with no progress → cancelled status."""
    create_resp = await client.post(
        "/api/analysis-runs",
        json={"capture_artifact_id": 1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    run_id = create_resp.json()["id"]

    await client.post(
        f"/api/analysis-runs/{run_id}/start",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    cancel_resp = await client.post(
        f"/api/analysis-runs/{run_id}/cancel",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert cancel_resp.json()["status"] == "cancelled"


# ---------------------------------------------------------------------------
# Failed jobs
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fail_run_records_category_and_suggestion(client: AsyncClient, admin_token: str):
    """Failed run exposes category and suggested next step."""
    create_resp = await client.post(
        "/api/analysis-runs",
        json={"capture_artifact_id": 1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    run_id = create_resp.json()["id"]

    await client.post(
        f"/api/analysis-runs/{run_id}/start",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    fail_resp = await client.post(
        f"/api/analysis-runs/{run_id}/fail",
        json={
            "category": "tool_error",
            "suggested_next_step": "Check that tshark is installed and the capture file is valid.",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert fail_resp.status_code == 200
    data = fail_resp.json()
    assert data["status"] == "failed"
    assert data["failure_category"] == "tool_error"
    assert data["suggested_next_step"] == "Check that tshark is installed and the capture file is valid."


# ---------------------------------------------------------------------------
# Progress messages
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_progress_messages_are_recorded(client: AsyncClient, admin_token: str):
    """Progress messages are visible and concise."""
    create_resp = await client.post(
        "/api/analysis-runs",
        json={"capture_artifact_id": 1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    run_id = create_resp.json()["id"]

    await client.post(
        f"/api/analysis-runs/{run_id}/start",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # Add progress
    await client.post(
        f"/api/analysis-runs/{run_id}/progress",
        json={"message": "Running TCP health check"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await client.post(
        f"/api/analysis-runs/{run_id}/progress",
        json={"message": "Running DNS resolution check"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Get the run and check progress
    get_resp = await client.get(
        f"/api/analysis-runs/{run_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    progress = get_resp.json()["progress"]
    assert len(progress) == 2
    assert progress[0]["message"] == "Running TCP health check"
    assert progress[1]["message"] == "Running DNS resolution check"
    # Each has a timestamp
    assert progress[0]["timestamp"] is not None


# ---------------------------------------------------------------------------
# List and get
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_analysis_runs_for_artifact(client: AsyncClient, admin_token: str):
    """List analysis runs filtered by capture artifact."""
    await client.post(
        "/api/analysis-runs",
        json={"capture_artifact_id": 1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await client.post(
        "/api/analysis-runs",
        json={"capture_artifact_id": 1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # Different artifact
    await client.post(
        "/api/analysis-runs",
        json={"capture_artifact_id": 2},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    list_resp = await client.get(
        "/api/analysis-runs?capture_artifact_id=1",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 2


@pytest.mark.asyncio
async def test_get_single_analysis_run(client: AsyncClient, admin_token: str):
    """Get analysis run by ID."""
    create_resp = await client.post(
        "/api/analysis-runs",
        json={"capture_artifact_id": 1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    run_id = create_resp.json()["id"]

    get_resp = await client.get(
        f"/api/analysis-runs/{run_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == run_id


@pytest.mark.asyncio
async def test_get_nonexistent_run_returns_404(client: AsyncClient, admin_token: str):
    """Get a run that doesn't exist returns 404."""
    get_resp = await client.get(
        "/api/analysis-runs/9999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# Auth requirements
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unauthenticated_create_rejected(client: AsyncClient):
    """Unauthenticated user cannot create analysis runs."""
    response = await client.post(
        "/api/analysis-runs",
        json={"capture_artifact_id": 1},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_unauthenticated_list_rejected(client: AsyncClient):
    """Unauthenticated user cannot list analysis runs."""
    response = await client.get("/api/analysis-runs")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_analyst_can_create_run(client: AsyncClient, admin_token: str):
    """Analyst (non-admin) can create analysis runs."""
    # Create an analyst
    await client.post(
        "/api/auth/analysts",
        json={"username": "analyst1", "password": "pw"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    analyst_token = (await client.post("/api/auth/login", json={
        "username": "analyst1", "password": "pw",
    })).json()["access_token"]

    response = await client.post(
        "/api/analysis-runs",
        json={"capture_artifact_id": 1},
        headers={"Authorization": f"Bearer {analyst_token}"},
    )
    assert response.status_code == 201
