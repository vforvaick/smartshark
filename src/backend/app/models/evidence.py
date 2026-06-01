import datetime
import enum

from sqlalchemy import String, Enum, Integer, ForeignKey, Text, DateTime, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ClaimStatus(str, enum.Enum):
    verified = "verified"
    likely = "likely"
    hypothesis = "hypothesis"
    unsupported = "unsupported"


class EvidenceMap(Base):
    __tablename__ = "evidence_maps"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("analysis_runs.id"), unique=True, nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    claims: Mapped[list["Claim"]] = relationship(
        "Claim",
        back_populates="evidence_map",
        order_by="Claim.id",
        cascade="all, delete-orphan",
    )


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(primary_key=True)
    evidence_map_id: Mapped[int] = mapped_column(
        ForeignKey("evidence_maps.id"), nullable=False
    )
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ClaimStatus] = mapped_column(
        Enum(ClaimStatus), nullable=False
    )
    key_facts: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    evidence_refs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    is_reportable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verification_step: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    evidence_map: Mapped["EvidenceMap"] = relationship(
        "EvidenceMap", back_populates="claims"
    )
