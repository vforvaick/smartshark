"""Metrics/hardening router — Issue #20."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.user import User, Role
from app.models.metrics import VantagePoint
from app.schemas.metrics import (
    CreateLimitationRequest,
    LimitationResponse,
    SetVantagePointRequest,
    VantagePointResponse,
    CheckCoverageResponse,
    ComputeMetricsRequest,
    SuccessMetricsResponse,
    FeedbackRequest,
    MetricsSummaryResponse,
)
from app.services.hardening import (
    add_limitation,
    get_check_coverage,
    get_vantage_point,
    set_vantage_point,
    compute_metrics,
    update_metrics_fields,
    submit_feedback,
    get_metrics,
    get_metrics_summary,
)
from app.services.evidence_validator import ValidationError

router = APIRouter(prefix="/api", tags=["metrics"])


# ---------------------------------------------------------------------------
# Limitations
# ---------------------------------------------------------------------------


@router.post(
    "/analysis-runs/{run_id}/limitations",
    response_model=LimitationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_limitation(
    run_id: int,
    body: CreateLimitationRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Record a limitation for an analysis run (e.g., encrypted payload)."""
    limitation = await add_limitation(db, run_id, body.category, body.detail)
    return limitation


# ---------------------------------------------------------------------------
# Check Coverage
# ---------------------------------------------------------------------------


@router.get(
    "/analysis-runs/{run_id}/check-coverage",
    response_model=CheckCoverageResponse,
)
async def get_run_check_coverage(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get check coverage including failed, skipped, and cancelled checks."""
    return await get_check_coverage(db, run_id)


# ---------------------------------------------------------------------------
# Vantage Point
# ---------------------------------------------------------------------------


@router.post(
    "/analysis-runs/{run_id}/vantage-point",
    response_model=VantagePointResponse,
)
async def set_run_vantage_point(
    run_id: int,
    body: SetVantagePointRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Set the capture vantage point for an analysis run."""
    return await set_vantage_point(db, run_id, body.vantage_point)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


@router.post(
    "/analysis-runs/{run_id}/metrics",
    response_model=SuccessMetricsResponse,
)
async def compute_run_metrics(
    run_id: int,
    body: ComputeMetricsRequest | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Compute and store success metrics for a completed analysis run."""
    # First compute base metrics
    metrics = await compute_metrics(db, run_id)

    # Update optional fields if provided
    if body:
        time_ms = body.time_to_first_evidence_ms
        saved_ms = body.report_time_saved_estimate_ms
        if time_ms is not None or saved_ms is not None:
            metrics = await update_metrics_fields(
                db, run_id,
                time_to_first_evidence_ms=time_ms,
                report_time_saved_estimate_ms=saved_ms,
            )

    return metrics


@router.get(
    "/analysis-runs/{run_id}/metrics",
    response_model=SuccessMetricsResponse,
)
async def get_run_metrics(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get metrics for a specific run."""
    metrics = await get_metrics(db, run_id)
    if metrics is None:
        raise HTTPException(status_code=404, detail="Metrics not found")
    return metrics


@router.patch(
    "/analysis-runs/{run_id}/metrics/feedback",
    response_model=SuccessMetricsResponse,
)
async def submit_run_feedback(
    run_id: int,
    body: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Submit usefulness feedback (1-5) for an analysis run."""
    try:
        return await submit_feedback(db, run_id, body.usefulness_score)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )


# ---------------------------------------------------------------------------
# Aggregate Summary (Admin)
# ---------------------------------------------------------------------------


@router.get(
    "/metrics/summary",
    response_model=MetricsSummaryResponse,
)
async def metrics_summary(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_role(Role.admin)),
):
    """Get aggregate metrics across all runs (admin only)."""
    return await get_metrics_summary(db)
