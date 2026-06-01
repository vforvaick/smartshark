from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models.analysis import AnalysisRun, AnalysisRunStatus, ProgressMessage
from app.models.capture import CaptureArtifact
from app.models.check_result import CheckResult, CheckStatus
from app.models.user import User
from app.schemas.analysis import (
    CreateAnalysisRunRequest,
    AnalysisRunResponse,
    FailRunRequest,
    AddProgressRequest,
    QuickAnalysisRequest,
    CheckResultResponse,
)
from app.services.playbook import run_quick_analysis_checks

router = APIRouter(prefix="/api/analysis-runs", tags=["analysis-runs"])


def _terminal_statuses() -> set[AnalysisRunStatus]:
    return {
        AnalysisRunStatus.completed,
        AnalysisRunStatus.failed,
        AnalysisRunStatus.cancelled,
        AnalysisRunStatus.partial,
    }


async def _load_run(db: AsyncSession, run_id: int) -> AnalysisRun | None:
    """Load a run with progress and check_results eagerly loaded."""
    result = await db.execute(
        select(AnalysisRun)
        .options(selectinload(AnalysisRun.progress), selectinload(AnalysisRun.check_results))
        .where(AnalysisRun.id == run_id)
    )
    return result.scalar_one_or_none()


@router.post("", response_model=AnalysisRunResponse, status_code=status.HTTP_201_CREATED)
async def create_analysis_run(
    body: CreateAnalysisRunRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    run = AnalysisRun(capture_artifact_id=body.capture_artifact_id)
    db.add(run)
    await db.commit()
    run = await _load_run(db, run.id)
    return run


@router.get("", response_model=list[AnalysisRunResponse])
async def list_analysis_runs(
    capture_artifact_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    stmt = select(AnalysisRun).options(
        selectinload(AnalysisRun.progress), selectinload(AnalysisRun.check_results)
    )
    if capture_artifact_id is not None:
        stmt = stmt.where(AnalysisRun.capture_artifact_id == capture_artifact_id)
    result = await db.execute(stmt.order_by(AnalysisRun.id))
    return result.scalars().all()


@router.get("/{run_id}", response_model=AnalysisRunResponse)
async def get_analysis_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    run = await _load_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found")
    return run


@router.post("/{run_id}/start", response_model=AnalysisRunResponse)
async def start_analysis_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    run = await _load_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found")
    if run.status != AnalysisRunStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot start run in {run.status.value} status",
        )
    run.status = AnalysisRunStatus.running
    await db.commit()
    return await _load_run(db, run_id)


@router.post("/{run_id}/complete", response_model=AnalysisRunResponse)
async def complete_analysis_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    run = await _load_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found")
    if run.status != AnalysisRunStatus.running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot complete run in {run.status.value} status",
        )
    run.status = AnalysisRunStatus.completed
    await db.commit()
    return await _load_run(db, run_id)


@router.post("/{run_id}/fail", response_model=AnalysisRunResponse)
async def fail_analysis_run(
    run_id: int,
    body: FailRunRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    run = await _load_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found")
    if run.status != AnalysisRunStatus.running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot fail run in {run.status.value} status",
        )
    run.status = AnalysisRunStatus.failed
    run.failure_category = body.category
    run.suggested_next_step = body.suggested_next_step
    await db.commit()
    return await _load_run(db, run_id)


@router.post("/{run_id}/cancel", response_model=AnalysisRunResponse)
async def cancel_analysis_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    run = await _load_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found")
    if run.status in _terminal_statuses():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel run in {run.status.value} status",
        )
    # Preserve partial results if run had progress
    if run.status == AnalysisRunStatus.running and len(run.progress) > 0:
        run.status = AnalysisRunStatus.partial
    else:
        run.status = AnalysisRunStatus.cancelled
    await db.commit()
    return await _load_run(db, run_id)


@router.post("/{run_id}/progress", response_model=AnalysisRunResponse)
async def add_progress(
    run_id: int,
    body: AddProgressRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    run = await _load_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found")
    if run.status != AnalysisRunStatus.running:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot add progress to run in {run.status.value} status",
        )
    msg = ProgressMessage(analysis_run_id=run_id, message=body.message)
    db.add(msg)
    await db.commit()
    return await _load_run(db, run_id)


# ---------------------------------------------------------------------------
# Quick Analysis endpoints (Issue #8)
# ---------------------------------------------------------------------------


@router.post("/{run_id}/quick-analysis", response_model=AnalysisRunResponse)
async def run_quick_analysis(
    run_id: int,
    body: QuickAnalysisRequest | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Run Quick Analysis: default generic playbook fan-out."""
    run = await _load_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found")
    if run.status != AnalysisRunStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot run analysis on run in {run.status.value} status",
        )

    # Transition to running
    run.status = AnalysisRunStatus.running
    issue_brief_text = body.issue_brief if body else None
    brief_msg = f"Starting Quick Analysis{' with issue brief' if issue_brief_text else ''}."
    db.add(ProgressMessage(analysis_run_id=run_id, message=brief_msg))
    await db.commit()

    # Get the capture artifact's file path
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

    # Record progress: running playbook checks
    db.add(ProgressMessage(
        analysis_run_id=run_id,
        message="Running default triage fan-out: TCP Health, DNS Resolution, HTTP/API, TLS Handshake, Path/Visibility.",
    ))
    await db.commit()

    # Run all checks via playbook engine
    check_outputs = run_quick_analysis_checks(capture_path)

    # Store check results and progress
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

    # Transition to completed
    run.status = AnalysisRunStatus.completed
    db.add(ProgressMessage(analysis_run_id=run_id, message="Quick Analysis complete."))
    await db.commit()
    # Expire all cached objects so the final load gets fresh data
    db.expire_all()

    return await _load_run(db, run_id)


@router.get("/{run_id}/check-results", response_model=list[CheckResultResponse])
async def get_check_results(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get check results for an analysis run."""
    run = await _load_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found")

    result = await db.execute(
        select(CheckResult)
        .where(CheckResult.analysis_run_id == run_id)
        .order_by(CheckResult.id)
    )
    return result.scalars().all()
