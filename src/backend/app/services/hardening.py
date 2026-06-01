"""Hardening service — Issue #20.

Provides:
- Encrypted payload limitation recording
- Check coverage computation
- Vantage point claim status limits
- Success metrics computation
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.analysis import AnalysisRun
from app.models.check_result import CheckResult, CheckStatus
from app.models.evidence import Claim, ClaimStatus, EvidenceMap
from app.models.metrics import (
    RunLimitation,
    RunVantagePoint,
    SuccessMetrics,
    VantagePoint,
)
from app.services.evidence_validator import ValidationError


async def add_limitation(
    db: AsyncSession, run_id: int, category: str, detail: str
) -> RunLimitation:
    """Record a limitation for an analysis run."""
    limitation = RunLimitation(
        analysis_run_id=run_id,
        category=category,
        detail=detail,
    )
    db.add(limitation)
    await db.commit()
    await db.refresh(limitation)
    return limitation


async def get_limitations(db: AsyncSession, run_id: int) -> list[RunLimitation]:
    """Get all limitations for an analysis run."""
    result = await db.execute(
        select(RunLimitation).where(RunLimitation.analysis_run_id == run_id)
    )
    return list(result.scalars().all())


async def get_check_coverage(db: AsyncSession, run_id: int) -> dict:
    """Compute check coverage for an analysis run, including failed/skipped checks."""
    # Load run with check results
    result = await db.execute(
        select(CheckResult).where(CheckResult.analysis_run_id == run_id)
    )
    checks = list(result.scalars().all())

    # Get run status for cancelled/incomplete detection
    run_result = await db.execute(
        select(AnalysisRun).where(AnalysisRun.id == run_id)
    )
    run = run_result.scalar_one_or_none()
    incomplete = run is not None and run.status in ("cancelled", "partial", "failed")

    items = []
    for c in checks:
        item = {
            "check_name": c.check_name,
            "status": c.status.value if hasattr(c.status, "value") else str(c.status),
        }
        if c.status in (CheckStatus.skipped, CheckStatus.failed):
            item["reason"] = c.summary or f"Check {c.status.value}"
        if c.limitations:
            item["limitations"] = c.limitations
        items.append(item)

    completed = sum(1 for i in items if i["status"] == "completed")
    total = len(items)
    summary = f"{completed}/{total} checks completed"

    return {
        "checks": items,
        "incomplete": incomplete,
        "coverage_summary": summary,
    }


async def get_vantage_point(db: AsyncSession, run_id: int) -> VantagePoint:
    """Get the vantage point setting for a run. Default is 'known'."""
    result = await db.execute(
        select(RunVantagePoint).where(RunVantagePoint.analysis_run_id == run_id)
    )
    vp = result.scalar_one_or_none()
    if vp is None:
        return VantagePoint.known
    return vp.vantage_point


async def set_vantage_point(
    db: AsyncSession, run_id: int, vantage_point: VantagePoint
) -> RunVantagePoint:
    """Set the vantage point for an analysis run."""
    result = await db.execute(
        select(RunVantagePoint).where(RunVantagePoint.analysis_run_id == run_id)
    )
    vp = result.scalar_one_or_none()
    if vp is None:
        vp = RunVantagePoint(analysis_run_id=run_id, vantage_point=vantage_point)
        db.add(vp)
    else:
        vp.vantage_point = vantage_point

    # If unknown, add a limitation
    if vantage_point == VantagePoint.unknown:
        # Check if limitation already exists
        existing = await db.execute(
            select(RunLimitation).where(
                RunLimitation.analysis_run_id == run_id,
                RunLimitation.category == "vantage_point_unknown",
            )
        )
        if existing.scalar_one_or_none() is None:
            limitation = RunLimitation(
                analysis_run_id=run_id,
                category="vantage_point_unknown",
                detail="Capture vantage point is unknown; claim statuses limited to Likely maximum",
            )
            db.add(limitation)

    await db.commit()
    await db.refresh(vp)
    return vp


def validate_claim_for_vantage_point(
    vantage_point: VantagePoint, claim_status: ClaimStatus
) -> None:
    """Validate that a claim status is allowed given the vantage point."""
    if vantage_point == VantagePoint.unknown and claim_status == ClaimStatus.verified:
        raise ValidationError(
            "Verified claims are not allowed when capture vantage point is unknown. "
            "Maximum allowed status is Likely."
        )


async def compute_metrics(db: AsyncSession, run_id: int) -> SuccessMetrics:
    """Compute success metrics for a completed analysis run."""
    # Load evidence map with claims
    result = await db.execute(
        select(EvidenceMap)
        .options(selectinload(EvidenceMap.claims))
        .where(EvidenceMap.analysis_run_id == run_id)
    )
    emap = result.scalar_one_or_none()

    total_claims = len(emap.claims) if emap else 0
    unsupported_claims = 0
    claims_with_evidence = 0

    if emap:
        for claim in emap.claims:
            if claim.status == ClaimStatus.unsupported:
                unsupported_claims += 1
            if claim.evidence_refs:
                claims_with_evidence += 1

    unsupported_rate = (unsupported_claims / total_claims * 100) if total_claims > 0 else 0.0
    coverage_pct = (claims_with_evidence / total_claims * 100) if total_claims > 0 else 0.0

    # Upsert metrics
    existing = await db.execute(
        select(SuccessMetrics).where(SuccessMetrics.analysis_run_id == run_id)
    )
    metrics = existing.scalar_one_or_none()

    if metrics is None:
        metrics = SuccessMetrics(
            analysis_run_id=run_id,
            total_claims=total_claims,
            unsupported_claims=unsupported_claims,
            unsupported_claim_rate=round(unsupported_rate, 4),
            evidence_coverage_pct=round(coverage_pct, 1),
        )
        db.add(metrics)
    else:
        metrics.total_claims = total_claims
        metrics.unsupported_claims = unsupported_claims
        metrics.unsupported_claim_rate = round(unsupported_rate, 4)
        metrics.evidence_coverage_pct = round(coverage_pct, 1)

    await db.commit()
    await db.refresh(metrics)
    return metrics


async def update_metrics_fields(
    db: AsyncSession,
    run_id: int,
    time_to_first_evidence_ms: int | None = None,
    report_time_saved_estimate_ms: int | None = None,
) -> SuccessMetrics:
    """Update optional metrics fields. Creates metrics record if needed."""
    existing = await db.execute(
        select(SuccessMetrics).where(SuccessMetrics.analysis_run_id == run_id)
    )
    metrics = existing.scalar_one_or_none()

    if metrics is None:
        # Compute base metrics first
        metrics = await compute_metrics(db, run_id)

    if time_to_first_evidence_ms is not None:
        metrics.time_to_first_evidence_ms = time_to_first_evidence_ms
    if report_time_saved_estimate_ms is not None:
        metrics.report_time_saved_estimate_ms = report_time_saved_estimate_ms

    await db.commit()
    await db.refresh(metrics)
    return metrics


async def submit_feedback(
    db: AsyncSession, run_id: int, usefulness_score: int
) -> SuccessMetrics:
    """Submit usefulness feedback (1-5) for a run's metrics."""
    if usefulness_score < 1 or usefulness_score > 5:
        raise ValueError("Usefulness score must be between 1 and 5")

    existing = await db.execute(
        select(SuccessMetrics).where(SuccessMetrics.analysis_run_id == run_id)
    )
    metrics = existing.scalar_one_or_none()

    if metrics is None:
        metrics = await compute_metrics(db, run_id)

    metrics.usefulness_score = usefulness_score
    await db.commit()
    await db.refresh(metrics)
    return metrics


async def get_metrics(db: AsyncSession, run_id: int) -> SuccessMetrics | None:
    """Get metrics for a run."""
    result = await db.execute(
        select(SuccessMetrics).where(SuccessMetrics.analysis_run_id == run_id)
    )
    return result.scalar_one_or_none()


async def get_metrics_summary(db: AsyncSession) -> dict:
    """Get aggregate metrics across all runs (admin)."""
    result = await db.execute(select(SuccessMetrics))
    all_metrics = list(result.scalars().all())

    total_runs = len(all_metrics)
    if total_runs == 0:
        return {
            "total_runs": 0,
            "avg_unsupported_claim_rate": 0.0,
            "avg_evidence_coverage_pct": None,
            "avg_usefulness_score": None,
        }

    avg_rate = sum(m.unsupported_claim_rate for m in all_metrics) / total_runs

    coverage_metrics = [m for m in all_metrics if m.evidence_coverage_pct is not None]
    avg_coverage = (
        sum(m.evidence_coverage_pct for m in coverage_metrics) / len(coverage_metrics)
        if coverage_metrics
        else None
    )

    feedback_metrics = [m for m in all_metrics if m.usefulness_score is not None]
    avg_score = (
        sum(m.usefulness_score for m in feedback_metrics) / len(feedback_metrics)
        if feedback_metrics
        else None
    )

    return {
        "total_runs": total_runs,
        "avg_unsupported_claim_rate": round(avg_rate, 4),
        "avg_evidence_coverage_pct": round(avg_coverage, 1) if avg_coverage is not None else None,
        "avg_usefulness_score": round(avg_score, 1) if avg_score is not None else None,
    }
