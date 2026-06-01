import datetime
import enum

from sqlalchemy import String, Enum, Integer, ForeignKey, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AnalysisRunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
    partial = "partial"


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    capture_artifact_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[AnalysisRunStatus] = mapped_column(
        Enum(AnalysisRunStatus), default=AnalysisRunStatus.pending
    )
    failure_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    suggested_next_step: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    progress: Mapped[list["ProgressMessage"]] = relationship(
        "ProgressMessage",
        back_populates="analysis_run",
        order_by="ProgressMessage.id",
        cascade="all, delete-orphan",
    )

    check_results: Mapped[list["CheckResult"]] = relationship(
        "CheckResult",
        back_populates="analysis_run",
        order_by="CheckResult.id",
        cascade="all, delete-orphan",
    )

    scope: Mapped["AnalysisScope | None"] = relationship(
        "AnalysisScope",
        back_populates="analysis_run",
        uselist=False,
    )

    profile_config: Mapped["ProfileConfig | None"] = relationship(
        "ProfileConfig",
        back_populates="analysis_run",
        uselist=False,
    )


class ProgressMessage(Base):
    __tablename__ = "progress_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_run_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_runs.id"), nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    analysis_run: Mapped["AnalysisRun"] = relationship(
        "AnalysisRun", back_populates="progress"
    )
