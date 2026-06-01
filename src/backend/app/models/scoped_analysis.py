"""Models for scoped analysis (Issue #12)."""

import datetime
import enum

from sqlalchemy import String, Enum, Integer, ForeignKey, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ScopeType(str, enum.Enum):
    time_window = "time_window"
    endpoint = "endpoint"
    conversation = "conversation"
    display_filter = "display_filter"
    symptom = "symptom"
    playbook = "playbook"
    combined = "combined"


class AnalysisScope(Base):
    __tablename__ = "analysis_scopes"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_run_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_runs.id"), unique=True, nullable=False
    )
    scope_type: Mapped[ScopeType] = mapped_column(Enum(ScopeType), nullable=False)
    scope_params: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    analysis_run: Mapped["AnalysisRun"] = relationship(
        "AnalysisRun", back_populates="scope"
    )
