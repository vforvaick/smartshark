import datetime
import enum

from sqlalchemy import String, Enum, Integer, ForeignKey, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SliceCriteria(str, enum.Enum):
    time_range = "time_range"
    display_filter = "display_filter"
    endpoint_pair = "endpoint_pair"
    conversation = "conversation"


class CaptureSlice(Base):
    __tablename__ = "capture_slices"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_artifact_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("capture_artifacts.id"), nullable=False
    )
    criteria_type: Mapped[SliceCriteria] = mapped_column(
        Enum(SliceCriteria), nullable=False
    )
    criteria_params: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    exported_artifact_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("capture_artifacts.id"), nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    source_artifact: Mapped["app.models.capture.CaptureArtifact"] = relationship(
        "CaptureArtifact", foreign_keys=[source_artifact_id]
    )
    exported_artifact: Mapped["app.models.capture.CaptureArtifact | None"] = relationship(
        "CaptureArtifact", foreign_keys=[exported_artifact_id]
    )
