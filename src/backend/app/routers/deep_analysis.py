"""Deep Analysis router: Issue Brief, Symptom Interview, and Deep Analysis endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models.analysis import AnalysisRun, AnalysisRunStatus, ProgressMessage
from app.models.capture import CaptureArtifact
from app.models.check_result import CheckResult, CheckStatus
from app.models.deep_analysis import IssueBrief
from app.models.user import User
from app.schemas.deep_analysis import (
    CreateIssueBriefRequest,
    IssueBriefResponse,
    InterviewResponse,
    InterviewQuestionResponse,
    AnswerQuestionRequest,
)
from app.schemas.analysis import AnalysisRunResponse
from app.services.symptom_interview import (
    create_issue_brief,
    get_issue_brief_by_run,
    get_interview_questions,
    answer_question,
    is_interview_complete,
)
from app.services.playbook import run_quick_analysis_checks

router = APIRouter(prefix="/api/analysis-runs", tags=["deep-analysis"])


async def _load_run(db: AsyncSession, run_id: int) -> AnalysisRun | None:
    """Load a run with eager-loaded relationships."""
    result = await db.execute(
        select(AnalysisRun)
        .options(
            selectinload(AnalysisRun.progress),
            selectinload(AnalysisRun.check_results),
        )
        .where(AnalysisRun.id == run_id)
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Issue Brief endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{run_id}/issue-brief",
    response_model=IssueBriefResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_issue_brief(
    run_id: int,
    body: CreateIssueBriefRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Submit an Issue Brief for a Deep Analysis run."""
    run = await _load_run(db, run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis run not found",
        )

    # Check for duplicate brief
    existing = await get_issue_brief_by_run(db, run_id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Issue brief already exists for this analysis run",
        )

    # Get capture path for prescan
    capture_path = None
    artifact_result = await db.execute(
        select(CaptureArtifact).where(CaptureArtifact.id == run.capture_artifact_id)
    )
    artifact = artifact_result.scalar_one_or_none()
    if artifact is not None:
        capture_path = artifact.file_path

    brief = await create_issue_brief(db, run_id, body.raw_text, capture_path)
    return brief


@router.get(
    "/{run_id}/issue-brief",
    response_model=IssueBriefResponse,
)
async def get_issue_brief(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get the Issue Brief for an analysis run."""
    brief = await get_issue_brief_by_run(db, run_id)
    if brief is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue brief not found",
        )
    return brief


# ---------------------------------------------------------------------------
# Interview endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/{run_id}/interview",
    response_model=InterviewResponse,
)
async def get_interview(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get interview questions and completion status."""
    brief = await get_issue_brief_by_run(db, run_id)
    if brief is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue brief not found — submit a brief first",
        )

    questions = await get_interview_questions(db, run_id)
    return InterviewResponse(
        questions=questions,
        is_complete=is_interview_complete(questions),
    )


@router.post(
    "/{run_id}/interview/{question_id}",
    response_model=InterviewQuestionResponse,
)
async def submit_answer(
    run_id: int,
    question_id: int,
    body: AnswerQuestionRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Answer an interview question."""
    # Verify the question belongs to this run's brief
    brief = await get_issue_brief_by_run(db, run_id)
    if brief is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue brief not found",
        )

    question = await answer_question(db, question_id, body.answer)
    if question is None or question.issue_brief_id != brief.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview question not found",
        )
    return question


# ---------------------------------------------------------------------------
# Deep Analysis endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/{run_id}/deep-analysis",
    response_model=AnalysisRunResponse,
)
async def run_deep_analysis(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Start Deep Analysis using Issue Brief and Interview context.

    Works with complete or partial interview data.
    """
    run = await _load_run(db, run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis run not found",
        )

    if run.status != AnalysisRunStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot run analysis on run in {run.status.value} status",
        )

    # Require an issue brief
    brief = await get_issue_brief_by_run(db, run_id)
    if brief is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Issue brief required before starting deep analysis",
        )

    # Transition to running
    run.status = AnalysisRunStatus.running
    brief_ctx = brief.extracted_fields or {}
    symptom = brief_ctx.get("symptom", "unknown")
    endpoint = brief_ctx.get("endpoint", "unknown")
    db.add(ProgressMessage(
        analysis_run_id=run_id,
        message=f"Starting Deep Analysis. Symptom: {symptom}, Endpoint: {endpoint}.",
    ))
    await db.commit()

    # Get capture artifact path
    artifact_result = await db.execute(
        select(CaptureArtifact).where(CaptureArtifact.id == run.capture_artifact_id)
    )
    artifact = artifact_result.scalar_one_or_none()
    if artifact is None:
        run.status = AnalysisRunStatus.failed
        run.failure_category = "missing_artifact"
        run.suggested_next_step = "The capture artifact for this analysis run was not found."
        db.add(ProgressMessage(analysis_run_id=run_id, message="Analysis failed: capture artifact not found."))
        await db.commit()
        return await _load_run(db, run_id)

    capture_path = artifact.file_path

    # Record progress
    db.add(ProgressMessage(
        analysis_run_id=run_id,
        message="Running directed analysis with issue brief context.",
    ))
    await db.commit()

    # Run playbook checks (same as quick analysis, but brief context is available
    # for future weighting/prioritization)
    check_outputs = run_quick_analysis_checks(capture_path)

    for output in check_outputs:
        check_result = CheckResult(
            analysis_run_id=run_id,
            check_name=output.check_name,
            status=output.status,
            summary=output.summary,
            evidence_refs=output.evidence_refs,
            limitations=output.limitations,
        )
        db.add(check_result)
        db.add(ProgressMessage(
            analysis_run_id=run_id,
            message=f"Check {output.check_name}: {output.status.value}.",
        ))

    run.status = AnalysisRunStatus.completed
    db.add(ProgressMessage(
        analysis_run_id=run_id,
        message="Deep Analysis complete.",
    ))
    await db.commit()
    db.expire_all()

    return await _load_run(db, run_id)
