"""Models for hardening/metrics — Issue #20."""

import datetime
import enum

from sqlalchemy import String, Enum, Integer, Float, ForeignKey, Text, DateTime, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class VantagePoint(str, enum.Enum):
    known = "known"
    unknown = "unknown"


class LimitationCategory(str, enum.Enum):
    encrypted_payload = "encrypted_payload"
    check_failed = "check_failed"
    check_skipped = "check_skipped"
    check_cancelled = "check_cancelled"
    vantage_point_unknown = "vantage_point_unknown"
    other = "other"


class RunLimitation(Base):
    __tablename__ = "run_limitations"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_run_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_runs.id"), nullable=False
    )
    category: Mapped[LimitationCategory] = mapped_column(Enum(LimitationCategory), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )


class RunVantagePoint(Base):
    __tablename__ = "run_vantage_points"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_run_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_runs.id"), unique=True, nullable=False
    )
    vantage_point: Mapped[VantagePoint] = mapped_column(
        Enum(VantagePoint), default=VantagePoint.known
    )


class SuccessMetrics(Base):
    __tablename__ = "success_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_run_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_runs.id"), unique=True, nullable=False
    )
    time_to_first_evidence_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence_coverage_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_claims: Mapped[int] = mapped_column(Integer, default=0)
    unsupported_claims: Mapped[int] = mapped_column(Integer, default=0)
    unsupported_claim_rate: Mapped[float] = mapped_column(Float, default=0.0)
    report_time_saved_estimate_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usefulness_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
