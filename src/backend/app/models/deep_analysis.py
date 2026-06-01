"""Deep Analysis models: IssueBrief and InterviewQuestion."""

import datetime
import enum
import json

from sqlalchemy import String, Integer, ForeignKey, Text, DateTime, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class InterviewStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"


class IssueBrief(Base):
    __tablename__ = "issue_briefs"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("analysis_runs.id"), unique=True, nullable=False
    )
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_fields: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    questions: Mapped[list["InterviewQuestion"]] = relationship(
        "InterviewQuestion",
        back_populates="issue_brief",
        order_by="InterviewQuestion.id",
        cascade="all, delete-orphan",
    )


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    issue_brief_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("issue_briefs.id"), nullable=False
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    field_name: Mapped[str] = mapped_column(String(64), nullable=False)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_answered: Mapped[bool] = mapped_column(Boolean, default=False)

    issue_brief: Mapped["IssueBrief"] = relationship(
        "IssueBrief", back_populates="questions"
    )
