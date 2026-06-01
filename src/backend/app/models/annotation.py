import datetime
import enum

from sqlalchemy import String, Enum, Integer, ForeignKey, Text, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AnnotationTargetType(str, enum.Enum):
    claim = "claim"
    evidence_card = "evidence_card"
    evidence_link = "evidence_link"
    report_section = "report_section"


class Annotation(Base):
    __tablename__ = "annotations"

    id: Mapped[int] = mapped_column(primary_key=True)
    target_type: Mapped[AnnotationTargetType] = mapped_column(
        Enum(AnnotationTargetType), nullable=False
    )
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    author_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    annotation_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_false_positive: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    include_in_report: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    provenance: Mapped[str] = mapped_column(
        String(32), nullable=False, default="analyst"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
