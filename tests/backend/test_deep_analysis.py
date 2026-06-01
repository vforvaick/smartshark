"""Tests for Issue #11: Deep Analysis Issue Brief and Symptom Interview.

Acceptance criteria:
- Deep Analysis starts with an Issue Brief prompt
- System extracts known symptom, timing, endpoint, protocol, vantage point,
  expected behavior, and goal fields from the brief
- Symptom Interview asks only missing high-value questions
- Pre-Scan information influences the questions asked
- Analysis can pause for interleaved clarification and resume
"""

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_artifact(client: AsyncClient, admin_token: str) -> int:
    """Upload a valid PCAP and return the artifact ID."""
    pcap_magic = b"\xd4\xc3\xb2\xa1" + b"\x00" * 24 + b"\x01\x00\x00\x00" + b"\x00" * 8
    resp = await client.post(
        "/api/captures/upload",
        files={"file": ("test.pcap", pcap_magic, "application/octet-stream")},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_run(client: AsyncClient, admin_token: str, artifact_id: int) -> int:
    resp = await client.post(
        "/api/analysis-runs",
        json={"capture_artifact_id": artifact_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# Test: Submit issue brief creates IssueBrief record
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_submit_issue_brief_creates_record(
    client: AsyncClient, admin_token: str
):
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    resp = await client.post(
        f"/api/analysis-runs/{run_id}/issue-brief",
        json={"raw_text": "Users report slow HTTP connections to 192.168.1.2"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["analysis_run_id"] == run_id
    assert data["raw_text"] == "Users report slow HTTP connections to 192.168.1.2"
    assert "extracted_fields" in data


# ---------------------------------------------------------------------------
# Test: System extracts known fields from raw text
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extracts_symptom_keywords(client: AsyncClient, admin_token: str):
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    resp = await client.post(
        f"/api/analysis-runs/{run_id}/issue-brief",
        json={"raw_text": "Connection timeouts to 10.0.0.5 on port 443"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    fields = resp.json()["extracted_fields"]
    assert fields["symptom"] == "timeout"
    assert fields["endpoint"] == "10.0.0.5"


@pytest.mark.asyncio
async def test_extracts_timing_from_text(client: AsyncClient, admin_token: str):
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    resp = await client.post(
        f"/api/analysis-runs/{run_id}/issue-brief",
        json={"raw_text": "Every morning at 9am the DNS lookups fail for internal hosts"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    fields = resp.json()["extracted_fields"]
    assert fields["timing"].lower() == "every morning at 9am"
    assert fields["symptom"] == "failure"


@pytest.mark.asyncio
async def test_extracts_protocol_from_text(client: AsyncClient, admin_token: str):
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    resp = await client.post(
        f"/api/analysis-runs/{run_id}/issue-brief",
        json={"raw_text": "TCP resets observed between client and server 172.16.0.1"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    fields = resp.json()["extracted_fields"]
    assert fields["protocol"] == "TCP"
    assert fields["symptom"] == "reset"
    assert fields["endpoint"] == "172.16.0.1"


# ---------------------------------------------------------------------------
# Test: Missing fields generate interview questions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_missing_fields_generate_questions(
    client: AsyncClient, admin_token: str
):
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    # Brief with only symptom — missing endpoint, timing, protocol, etc.
    await client.post(
        f"/api/analysis-runs/{run_id}/issue-brief",
        json={"raw_text": "Everything is slow"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.get(
        f"/api/analysis-runs/{run_id}/interview",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    questions = resp.json()["questions"]
    assert len(questions) > 0
    # Should ask about missing endpoint at minimum
    field_names = [q["field_name"] for q in questions]
    assert "endpoint" in field_names


@pytest.mark.asyncio
async def test_complete_brief_generates_fewer_questions(
    client: AsyncClient, admin_token: str
):
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    # Brief with most fields filled
    await client.post(
        f"/api/analysis-runs/{run_id}/issue-brief",
        json={"raw_text": "TCP connection timeouts to 10.0.0.5 port 443 every morning at 9am, expected to connect in under 1s, goal is to find the root cause"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.get(
        f"/api/analysis-runs/{run_id}/interview",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    questions = resp.json()["questions"]
    # Should have few high-value questions since most fields are extracted.
    # Pre-scan may add protocol-specific questions (DNS, TCP, HTTP from stub data)
    # so we check that core high-value fields are NOT asked about.
    field_names = [q["field_name"] for q in questions]
    # These fields were extracted, so they should NOT appear as questions
    assert "symptom" not in field_names
    assert "endpoint" not in field_names
    assert "protocol" not in field_names
    assert "timing" not in field_names
    assert "goal" not in field_names
    # Only prescan-influenced or vantage_point/expected_behavior may appear
    assert len(questions) <= 5


# ---------------------------------------------------------------------------
# Test: Pre-Scan data influences questions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_prescan_influences_questions(client: AsyncClient, admin_token: str):
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    # Create a capture index (prescan) for this artifact
    # The stub has DNS traffic, so prescan should influence DNS-related questions
    await client.post(
        f"/api/captures/{artifact_id}/index",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Brief with only a symptom — prescan should add protocol-specific questions
    await client.post(
        f"/api/analysis-runs/{run_id}/issue-brief",
        json={"raw_text": "Network is slow"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.get(
        f"/api/analysis-runs/{run_id}/interview",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    questions = resp.json()["questions"]
    # The prescan shows DNS traffic, so there should be DNS-specific questions
    question_texts = " ".join(q["question_text"].lower() for q in questions)
    assert "dns" in question_texts


# ---------------------------------------------------------------------------
# Test: Answer question updates the brief
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_answer_question_updates_brief(
    client: AsyncClient, admin_token: str
):
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    await client.post(
        f"/api/analysis-runs/{run_id}/issue-brief",
        json={"raw_text": "Everything is slow"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Get the questions
    interview = await client.get(
        f"/api/analysis-runs/{run_id}/interview",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    questions = interview.json()["questions"]

    # Answer the endpoint question
    endpoint_q = next(q for q in questions if q["field_name"] == "endpoint")
    resp = await client.post(
        f"/api/analysis-runs/{run_id}/interview/{endpoint_q['id']}",
        json={"answer": "10.0.0.5"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["is_answered"] is True
    assert resp.json()["answer"] == "10.0.0.5"

    # Verify brief was updated
    brief = await client.get(
        f"/api/analysis-runs/{run_id}/issue-brief",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    fields = brief.json()["extracted_fields"]
    assert fields["endpoint"] == "10.0.0.5"


# ---------------------------------------------------------------------------
# Test: Interview can be checked for completion
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_interview_completion_status(client: AsyncClient, admin_token: str):
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    await client.post(
        f"/api/analysis-runs/{run_id}/issue-brief",
        json={"raw_text": "Everything is slow"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Initially not complete
    interview = await client.get(
        f"/api/analysis-runs/{run_id}/interview",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert interview.json()["is_complete"] is False

    # Answer all questions
    for q in interview.json()["questions"]:
        await client.post(
            f"/api/analysis-runs/{run_id}/interview/{q['id']}",
            json={"answer": "test answer"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    # Now should be complete
    interview2 = await client.get(
        f"/api/analysis-runs/{run_id}/interview",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert interview2.json()["is_complete"] is True


# ---------------------------------------------------------------------------
# Test: Deep analysis can start after interview
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_start_deep_analysis_after_interview(
    client: AsyncClient, admin_token: str
):
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    # Submit brief
    await client.post(
        f"/api/analysis-runs/{run_id}/issue-brief",
        json={"raw_text": "TCP connection resets to 10.0.0.5"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Complete the interview
    interview = await client.get(
        f"/api/analysis-runs/{run_id}/interview",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    for q in interview.json()["questions"]:
        await client.post(
            f"/api/analysis-runs/{run_id}/interview/{q['id']}",
            json={"answer": "test answer"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    # Start deep analysis
    resp = await client.post(
        f"/api/analysis-runs/{run_id}/deep-analysis",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert len(data["check_results"]) > 0


# ---------------------------------------------------------------------------
# Test: Deep analysis produces check results with brief context
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_deep_analysis_includes_brief_context(
    client: AsyncClient, admin_token: str
):
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    await client.post(
        f"/api/analysis-runs/{run_id}/issue-brief",
        json={"raw_text": "DNS lookup failures for internal hosts"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Complete interview
    interview = await client.get(
        f"/api/analysis-runs/{run_id}/interview",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    for q in interview.json()["questions"]:
        await client.post(
            f"/api/analysis-runs/{run_id}/interview/{q['id']}",
            json={"answer": "some answer"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    # Run deep analysis
    resp = await client.post(
        f"/api/analysis-runs/{run_id}/deep-analysis",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    run_data = resp.json()

    # Check results should reference the brief's symptom context
    check_names = [cr["check_name"] for cr in run_data["check_results"]]
    assert "dns_resolution" in check_names

    # DNS check summary should mention the issue
    dns_check = next(cr for cr in run_data["check_results"] if cr["check_name"] == "dns_resolution")
    assert "DNS" in dns_check["summary"]


# ---------------------------------------------------------------------------
# Test: Analysis can pause for interleaved clarification
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_deep_analysis_can_be_started_without_complete_interview(
    client: AsyncClient, admin_token: str
):
    """Deep analysis should work even with partial interview — it uses whatever
    context is available. This enables interleaved clarification: analyst can
    start analysis, see partial results, answer more questions, then re-run."""
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    # Submit a rich brief — no interview answers needed for rich briefs
    await client.post(
        f"/api/analysis-runs/{run_id}/issue-brief",
        json={"raw_text": "TCP connection timeouts to 10.0.0.5 port 443, expected to connect in under 1s"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Don't complete the interview — start analysis anyway
    resp = await client.post(
        f"/api/analysis-runs/{run_id}/deep-analysis",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # Should succeed with partial data
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


# ---------------------------------------------------------------------------
# Test: Issue brief for non-existent run returns 404
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_issue_brief_for_nonexistent_run_returns_404(
    client: AsyncClient, admin_token: str
):
    resp = await client.post(
        "/api/analysis-runs/99999/issue-brief",
        json={"raw_text": "Something is wrong"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Test: Duplicate issue brief rejected
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_duplicate_issue_brief_rejected(
    client: AsyncClient, admin_token: str
):
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    await client.post(
        f"/api/analysis-runs/{run_id}/issue-brief",
        json={"raw_text": "First brief"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.post(
        f"/api/analysis-runs/{run_id}/issue-brief",
        json={"raw_text": "Second brief"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Test: Unauthenticated access rejected
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unauthenticated_issue_brief_rejected(client: AsyncClient):
    resp = await client.post(
        "/api/analysis-runs/1/issue-brief",
        json={"raw_text": "Something is wrong"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthenticated_interview_rejected(client: AsyncClient):
    resp = await client.get("/api/analysis-runs/1/interview")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthenticated_deep_analysis_rejected(client: AsyncClient):
    resp = await client.post("/api/analysis-runs/1/deep-analysis")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Test: Get issue brief returns stored data
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_issue_brief_returns_stored_data(
    client: AsyncClient, admin_token: str
):
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    await client.post(
        f"/api/analysis-runs/{run_id}/issue-brief",
        json={"raw_text": "Slow HTTP to 192.168.1.2"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    resp = await client.get(
        f"/api/analysis-runs/{run_id}/issue-brief",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["raw_text"] == "Slow HTTP to 192.168.1.2"
    assert data["extracted_fields"]["symptom"] == "slow"
    assert data["extracted_fields"]["endpoint"] == "192.168.1.2"


# ---------------------------------------------------------------------------
# Test: Deep analysis on non-pending run rejected
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_deep_analysis_rejected_for_completed_run(
    client: AsyncClient, admin_token: str
):
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    # Submit brief and run deep analysis
    await client.post(
        f"/api/analysis-runs/{run_id}/issue-brief",
        json={"raw_text": "TCP resets to 10.0.0.5"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await client.post(
        f"/api/analysis-runs/{run_id}/deep-analysis",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Try again — should be rejected
    resp = await client.post(
        f"/api/analysis-runs/{run_id}/deep-analysis",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Test: Deep analysis without issue brief rejected
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_deep_analysis_without_brief_rejected(
    client: AsyncClient, admin_token: str
):
    artifact_id = await _create_artifact(client, admin_token)
    run_id = await _create_run(client, admin_token, artifact_id)

    resp = await client.post(
        f"/api/analysis-runs/{run_id}/deep-analysis",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400
