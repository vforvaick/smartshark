import datetime
import enum

from sqlalchemy import String, Enum, Integer, ForeignKey, Text, DateTime, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TargetType(str, enum.Enum):
    packets = "packets"
    frame = "frame"
    flow = "flow"
    stream = "stream"
    timeline = "timeline"
    graph_edge = "graph_edge"
    claim = "claim"
    report_section = "report_section"


class EvidenceLink(Base):
    __tablename__ = "evidence_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    target_type: Mapped[TargetType] = mapped_column(Enum(TargetType), nullable=False)
    artifact_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("capture_artifacts.id"), nullable=True
    )
    target_params: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    citation_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    unavailability_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
