import datetime
import enum

from sqlalchemy import String, Enum, Integer, ForeignKey, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CheckStatus(str, enum.Enum):
    completed = "completed"
    skipped = "skipped"
    failed = "failed"


class CheckResult(Base):
    __tablename__ = "check_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_run_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_runs.id"), nullable=False
    )
    check_name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[CheckStatus] = mapped_column(
        Enum(CheckStatus), default=CheckStatus.completed
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    evidence_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    limitations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    analysis_run: Mapped["AnalysisRun"] = relationship(
        "AnalysisRun", back_populates="check_results"
    )
