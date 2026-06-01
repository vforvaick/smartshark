import datetime
import enum

from sqlalchemy import String, Enum, Integer, ForeignKey, Text, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RedactionPolicy(Base):
    """Singleton-like redaction policy controlled by admin."""
    __tablename__ = "redaction_policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    mask_payloads: Mapped[bool] = mapped_column(Boolean, default=True)
    mask_credentials: Mapped[bool] = mapped_column(Boolean, default=True)
    mask_auth_headers: Mapped[bool] = mapped_column(Boolean, default=True)
    mask_pan_values: Mapped[bool] = mapped_column(Boolean, default=True)
    anonymize_ips: Mapped[bool] = mapped_column(Boolean, default=False)
    anonymize_macs: Mapped[bool] = mapped_column(Boolean, default=False)
    mask_dns_suffix: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_sharing_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    profile: Mapped[str] = mapped_column(String(64), default="general")
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
    )


class AIRequestLog(Base):
    """Provenance record of what context was sent to which AI model."""
    __tablename__ = "ai_request_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    analysis_run_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("analysis_runs.id"), nullable=True
    )
    context_category: Mapped[str] = mapped_column(String(32), nullable=False)
    model_used: Mapped[str] = mapped_column(String(64), nullable=False, default="gpt-4o")
    redacted: Mapped[bool] = mapped_column(Boolean, default=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
