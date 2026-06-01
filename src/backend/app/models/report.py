import datetime
import enum

from sqlalchemy import String, Enum, Integer, ForeignKey, Text, DateTime, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ReportSectionType(str, enum.Enum):
    verified_findings = "verified_findings"
    likely_findings = "likely_findings"
    hypotheses_next_steps = "hypotheses_next_steps"
    limitations_assumptions = "limitations_assumptions"


class ReportStatus(str, enum.Enum):
    draft = "draft"
    review = "review"
    final = "final"


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    evidence_map_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("evidence_maps.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False, default="Investigation Report")
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus), default=ReportStatus.draft
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    sections: Mapped[list["ReportSection"]] = relationship(
        "ReportSection",
        back_populates="report",
        order_by="ReportSection.order_index",
        cascade="all, delete-orphan",
    )


class ReportSection(Base):
    __tablename__ = "report_sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("reports.id"), nullable=False
    )
    section_type: Mapped[ReportSectionType] = mapped_column(
        Enum(ReportSectionType), nullable=False
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    claim_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    is_included: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deep_links: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    report: Mapped["Report"] = relationship(
        "Report", back_populates="sections"
    )
