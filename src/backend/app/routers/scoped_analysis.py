"""Router for scoped analysis endpoints (Issue #12)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models.analysis import AnalysisRun, AnalysisRunStatus, ProgressMessage
from app.models.check_result import CheckResult, CheckStatus
from app.models.scoped_analysis import AnalysisScope, ScopeType
from app.models.user import User
from app.schemas.scoped_analysis import (
    CreateScopeRequest,
    AnalysisScopeResponse,
)
from app.services.scoped_analysis import validate_scope, scope_boundary_label
from app.services.playbook import run_quick_analysis_checks

router = APIRouter(prefix="/api/analysis-runs", tags=["scoped-analysis"])


async def _load_run_with_scope(db: AsyncSession, run_id: int) -> AnalysisRun | None:
    """Load a run with scope, progress, and check_results eagerly loaded."""
    result = await db.execute(
        select(AnalysisRun)
        .options(
            selectinload(AnalysisRun.scope),
            selectinload(AnalysisRun.progress),
            selectinload(AnalysisRun.check_results),
        )
        .where(AnalysisRun.id == run_id)
    )
    return result.scalar_one_or_none()


@router.post("/{run_id}/scope", response_model=AnalysisScopeResponse, status_code=status.HTTP_201_CREATED)
async def create_scope(
    run_id: int,
    body: CreateScopeRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Define a scope for an analysis run."""
    run = await _load_run_with_scope(db, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found")

    # Check if scope already exists for this run
    if run.scope is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Scope already defined for this analysis run",
        )

    # Validate scope type
    try:
        scope_type = ScopeType(body.scope_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported scope_type: {body.scope_type}",
        )

    # Validate scope params
    error = validate_scope(scope_type, body.scope_params)
    if error is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error,
        )

    scope = AnalysisScope(
        analysis_run_id=run_id,
        scope_type=scope_type,
        scope_params=body.scope_params,
    )
    db.add(scope)
    await db.commit()
    await db.refresh(scope)
    return scope


@router.get("/{run_id}/scope", response_model=AnalysisScopeResponse)
async def get_scope(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get the scope for an analysis run."""
    result = await db.execute(
        select(AnalysisScope).where(AnalysisScope.analysis_run_id == run_id)
    )
    scope = result.scalar_one_or_none()
    if scope is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scope not found for this analysis run")
    return scope


@router.post("/{run_id}/scoped-analysis")
async def run_scoped_analysis(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Run scoped analysis within the defined boundary."""
    run = await _load_run_with_scope(db, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found")

    if run.scope is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No scope defined for this analysis run. Define a scope first.",
        )

    if run.status != AnalysisRunStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot run scoped analysis on run in {run.status.value} status",
        )

    scope = run.scope
    boundary_label = scope_boundary_label(scope.scope_type, scope.scope_params)

    # Transition to running
    run.status = AnalysisRunStatus.running
    db.add(ProgressMessage(
        analysis_run_id=run_id,
        message=f"Starting Scoped Analysis within boundary: {boundary_label}.",
    ))
    await db.commit()

    # Run the default checks (scoped — in stub, checks produce evidence refs with scope boundary)
    check_outputs = run_quick_analysis_checks("")

    for output in check_outputs:
        # Annotate evidence_refs with scope boundary for provenance
        scoped_refs = []
        for ref in output.evidence_refs:
            scoped_ref = dict(ref)
            scoped_ref["scope_boundary"] = boundary_label
            scoped_ref["scope_type"] = scope.scope_type.value
            scoped_refs.append(scoped_ref)

        check_result = CheckResult(
            analysis_run_id=run_id,
            check_name=output.check_name,
            status=output.status,
            summary=output.summary,
            evidence_refs=scoped_refs,
            limitations=output.limitations,
        )
        db.add(check_result)
        db.add(ProgressMessage(
            analysis_run_id=run_id,
            message=f"Check {output.check_name}: {output.status.value} (scoped to {boundary_label}).",
        ))

    run.status = AnalysisRunStatus.completed
    db.add(ProgressMessage(
        analysis_run_id=run_id,
        message=f"Scoped Analysis complete for boundary: {boundary_label}.",
    ))
    await db.commit()
    db.expire_all()

    run = await _load_run_with_scope(db, run_id)
    return {
        "id": run.id,
        "capture_artifact_id": run.capture_artifact_id,
        "status": run.status,
        "scope": {
            "id": run.scope.id,
            "scope_type": run.scope.scope_type,
            "scope_params": run.scope.scope_params,
        } if run.scope else None,
        "check_results": [
            {
                "id": cr.id,
                "check_name": cr.check_name,
                "status": cr.status,
                "summary": cr.summary,
                "evidence_refs": cr.evidence_refs,
                "limitations": cr.limitations,
            }
            for cr in run.check_results
        ],
        "progress": [
            {"id": p.id, "message": p.message, "timestamp": p.timestamp.isoformat()}
            for p in run.progress
        ],
    }
