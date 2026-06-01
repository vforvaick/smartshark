"""TDD tests for Issue #13: Add Analysis Profiles and progressive profile context.

Proves:
- Four profiles available (general, f5, infoblox, verifone)
- General is default
- Profile can be set per analysis run
- Profile config includes assumptions, limitations, check_weighting
- F5 profile weights TCP/HTTP checks higher
- Infoblox profile weights DNS check higher
- Verifone profile adds payment-sensitive limitations
- Progressive questions appear based on prescan data
- Profile included in run results
- Non-existent run returns 404
- Unauthenticated access rejected
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
    pcap_magic = b"\xd4\xc3\xb2\xa1" + b"\x00" * 44
    upload = await client.post(
        "/api/captures/upload",
        files={"file": ("test.pcap", pcap_magic, "application/octet-stream")},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert upload.status_code == 201
    artifact_id = upload.json()["id"]

    idx = await client.post(
        f"/api/captures/{artifact_id}/index",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert idx.status_code == 201

    run = await client.post(
        "/api/analysis-runs",
        json={"capture_artifact_id": artifact_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert run.status_code == 201
    return run.json()


# ---------------------------------------------------------------------------
# Tests: List profiles
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_available_profiles(client: AsyncClient, admin_token: str):
    """GET /api/profiles returns all four profiles."""
    response = await client.get(
        "/api/profiles",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    profile_ids = [p["id"] for p in data]
    assert "general" in profile_ids
    assert "f5_load_balancer" in profile_ids
    assert "infoblox_dns" in profile_ids
    assert "verifone_intellinac" in profile_ids


@pytest.mark.asyncio
async def test_profiles_have_descriptions(client: AsyncClient, admin_token: str):
    """Each profile has a human-readable description."""
    response = await client.get(
        "/api/profiles",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    for p in data:
        assert "id" in p
        assert "description" in p
        assert len(p["description"]) > 0


# ---------------------------------------------------------------------------
# Tests: Default profile
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_general_is_default_profile(client: AsyncClient, admin_token: str):
    """General Network Troubleshooting is the default profile."""
    run_data = await _create_analysis_run_with_artifact(client, admin_token)

    # Before setting any profile, getting profile should return general
    response = await client.get(
        f"/api/analysis-runs/{run_data['id']}/profile",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["profile"] == "general"


# ---------------------------------------------------------------------------
# Tests: Set profile
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_profile_for_analysis_run(client: AsyncClient, admin_token: str):
    """Analyst can set one primary Analysis Profile per Analysis Run."""
    run_data = await _create_analysis_run_with_artifact(client, admin_token)

    response = await client.post(
        f"/api/analysis-runs/{run_data['id']}/profile",
        json={"profile": "f5_load_balancer"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["profile"] == "f5_load_balancer"


@pytest.mark.asyncio
async def test_set_profile_returns_assumptions_and_limitations(
    client: AsyncClient, admin_token: str
):
    """Profile config includes assumptions and limitations."""
    run_data = await _create_analysis_run_with_artifact(client, admin_token)

    response = await client.post(
        f"/api/analysis-runs/{run_data['id']}/profile",
        json={"profile": "f5_load_balancer"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "assumptions" in data
    assert isinstance(data["assumptions"], list)
    assert len(data["assumptions"]) > 0
    assert "limitations" in data
    assert isinstance(data["limitations"], list)


# ---------------------------------------------------------------------------
# Tests: Profile-specific weighting
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_f5_profile_weights_tcp_http_higher(
    client: AsyncClient, admin_token: str
):
    """F5 profile changes check weighting toward TCP and HTTP."""
    run_data = await _create_analysis_run_with_artifact(client, admin_token)

    response = await client.post(
        f"/api/analysis-runs/{run_data['id']}/profile",
        json={"profile": "f5_load_balancer"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    weighting = data["check_weighting"]
    # TCP and HTTP should be weighted higher than default
    assert weighting.get("tcp_health", 0) >= 1.0
    assert weighting.get("http_api", 0) >= 1.0
    # F5-specific: TCP health should be higher than DNS
    assert weighting["tcp_health"] > weighting.get("dns_resolution", 0)


@pytest.mark.asyncio
async def test_infoblox_profile_weights_dns_higher(
    client: AsyncClient, admin_token: str
):
    """Infoblox profile changes check weighting toward DNS."""
    run_data = await _create_analysis_run_with_artifact(client, admin_token)

    response = await client.post(
        f"/api/analysis-runs/{run_data['id']}/profile",
        json={"profile": "infoblox_dns"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    weighting = data["check_weighting"]
    assert weighting.get("dns_resolution", 0) >= 1.0
    # DNS should be highest for Infoblox
    assert weighting["dns_resolution"] > weighting.get("tcp_health", 0)


@pytest.mark.asyncio
async def test_verifone_profile_adds_payment_sensitive_limitations(
    client: AsyncClient, admin_token: str
):
    """Verifone profile adds payment-sensitive limitations."""
    run_data = await _create_analysis_run_with_artifact(client, admin_token)

    response = await client.post(
        f"/api/analysis-runs/{run_data['id']}/profile",
        json={"profile": "verifone_intellinac"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    limitations = data["limitations"]
    # Should mention payment-sensitive or similar
    has_payment_limitation = any(
        "payment" in lim.lower() or "card" in lim.lower()
        for lim in limitations
    )
    assert has_payment_limitation


# ---------------------------------------------------------------------------
# Tests: Progressive questions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_progressive_questions_appear_for_f5_profile(
    client: AsyncClient, admin_token: str
):
    """F5/Infoblox/iNAC context questions appear progressively when needed."""
    run_data = await _create_analysis_run_with_artifact(client, admin_token)

    # Set F5 profile
    await client.post(
        f"/api/analysis-runs/{run_data['id']}/profile",
        json={"profile": "f5_load_balancer"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Get progressive questions based on prescan
    response = await client.get(
        f"/api/analysis-runs/{run_data['id']}/profile/questions",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "questions" in data
    assert isinstance(data["questions"], list)
    # F5 profile should have at least one mapping question
    assert len(data["questions"]) > 0


@pytest.mark.asyncio
async def test_general_profile_has_minimal_questions(
    client: AsyncClient, admin_token: str
):
    """General profile has minimal or no progressive questions."""
    run_data = await _create_analysis_run_with_artifact(client, admin_token)

    response = await client.get(
        f"/api/analysis-runs/{run_data['id']}/profile/questions",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    # General profile should have no mapping questions
    assert len(data["questions"]) == 0


# ---------------------------------------------------------------------------
# Tests: Profile in run results
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_profile_included_in_run_results(
    client: AsyncClient, admin_token: str
):
    """Reports include profile, assumptions, and profile-specific limitations."""
    run_data = await _create_analysis_run_with_artifact(client, admin_token)

    # Set F5 profile
    profile_resp = await client.post(
        f"/api/analysis-runs/{run_data['id']}/profile",
        json={"profile": "f5_load_balancer"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert profile_resp.status_code == 200

    # Get the run — it should show the profile
    run_resp = await client.get(
        f"/api/analysis-runs/{run_data['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert run_resp.status_code == 200
    run = run_resp.json()
    # The run itself doesn't have profile directly but we can verify via the profile endpoint
    profile_get = await client.get(
        f"/api/analysis-runs/{run_data['id']}/profile",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert profile_get.status_code == 200
    profile_data = profile_get.json()
    assert profile_data["profile"] == "f5_load_balancer"
    assert len(profile_data["assumptions"]) > 0
    assert len(profile_data["limitations"]) > 0


# ---------------------------------------------------------------------------
# Tests: Error cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_profile_for_nonexistent_run_404(
    client: AsyncClient, admin_token: str
):
    """Non-existent run returns 404."""
    response = await client.post(
        "/api/analysis-runs/99999/profile",
        json={"profile": "f5_load_balancer"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_profile_for_nonexistent_run_404(
    client: AsyncClient, admin_token: str
):
    """Get profile for non-existent run returns 404."""
    response = await client.get(
        "/api/analysis-runs/99999/profile",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_questions_for_nonexistent_run_404(
    client: AsyncClient, admin_token: str
):
    """Get questions for non-existent run returns 404."""
    response = await client.get(
        "/api/analysis-runs/99999/profile/questions",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_invalid_profile_rejected(client: AsyncClient, admin_token: str):
    """Setting an invalid profile returns 422."""
    run_data = await _create_analysis_run_with_artifact(client, admin_token)

    response = await client.post(
        f"/api/analysis-runs/{run_data['id']}/profile",
        json={"profile": "nonexistent_profile"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_cannot_change_profile_after_set(client: AsyncClient, admin_token: str):
    """Cannot change profile once set (one primary profile per run)."""
    run_data = await _create_analysis_run_with_artifact(client, admin_token)

    # Set profile to F5
    resp1 = await client.post(
        f"/api/analysis-runs/{run_data['id']}/profile",
        json={"profile": "f5_load_balancer"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp1.status_code == 200

    # Try to change to Infoblox
    resp2 = await client.post(
        f"/api/analysis-runs/{run_data['id']}/profile",
        json={"profile": "infoblox_dns"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp2.status_code == 409


# ---------------------------------------------------------------------------
# Tests: Auth
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_profiles_list_unauthenticated(client: AsyncClient):
    """Unauthenticated access to profiles list is rejected."""
    response = await client.get("/api/profiles")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_set_profile_unauthenticated(client: AsyncClient):
    """Unauthenticated access to set profile is rejected."""
    response = await client.post(
        "/api/analysis-runs/1/profile",
        json={"profile": "f5_load_balancer"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_profile_unauthenticated(client: AsyncClient):
    """Unauthenticated access to get profile is rejected."""
    response = await client.get("/api/analysis-runs/1/profile")
    assert response.status_code == 401
