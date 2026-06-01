"""Schemas for hardening/metrics — Issue #20."""

from datetime import datetime

from pydantic import BaseModel

from app.models.metrics import LimitationCategory, VantagePoint


# ---------------------------------------------------------------------------
# Limitations
# ---------------------------------------------------------------------------

class CreateLimitationRequest(BaseModel):
    category: LimitationCategory
    detail: str


class LimitationResponse(BaseModel):
    id: int
    analysis_run_id: int
    category: LimitationCategory
    detail: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Vantage Point
# ---------------------------------------------------------------------------

class SetVantagePointRequest(BaseModel):
    vantage_point: VantagePoint


class VantagePointResponse(BaseModel):
    id: int
    analysis_run_id: int
    vantage_point: VantagePoint

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Check Coverage
# ---------------------------------------------------------------------------

class CheckCoverageItem(BaseModel):
    check_name: str
    status: str
    reason: str | None = None
    limitations: list[str] = []


class CheckCoverageResponse(BaseModel):
    checks: list[CheckCoverageItem]
    incomplete: bool
    coverage_summary: str


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

class ComputeMetricsRequest(BaseModel):
    time_to_first_evidence_ms: int | None = None
    report_time_saved_estimate_ms: int | None = None


class SuccessMetricsResponse(BaseModel):
    id: int
    analysis_run_id: int
    time_to_first_evidence_ms: int | None
    evidence_coverage_pct: float | None
    total_claims: int
    unsupported_claims: int
    unsupported_claim_rate: float
    report_time_saved_estimate_ms: int | None
    usefulness_score: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class FeedbackRequest(BaseModel):
    usefulness_score: int  # 1-5


class MetricsSummaryResponse(BaseModel):
    total_runs: int
    avg_unsupported_claim_rate: float
    avg_evidence_coverage_pct: float | None
    avg_usefulness_score: float | None
