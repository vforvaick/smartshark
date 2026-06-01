import datetime
import enum

from sqlalchemy import String, Integer, BigInteger, DateTime, Enum, Text, ForeignKey, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class CaptureIndex(Base):
    __tablename__ = "capture_indexes"

    id: Mapped[int] = mapped_column(primary_key=True)
    artifact_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    protocol_mix: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    top_endpoints: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    conversations_count: Mapped[int] = mapped_column(Integer, default=0)
    time_range_start: Mapped[str] = mapped_column(String(32), nullable=True)
    time_range_end: Mapped[str] = mapped_column(String(32), nullable=True)
    total_packets: Mapped[int] = mapped_column(Integer, default=0)
    total_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    timeline: Mapped[list["TimelineBucket"]] = relationship(
        "TimelineBucket",
        back_populates="capture_index",
        order_by="TimelineBucket.timestamp",
        cascade="all, delete-orphan",
    )


class TimelineBucket(Base):
    __tablename__ = "timeline_buckets"

    id: Mapped[int] = mapped_column(primary_key=True)
    capture_index_id: Mapped[int] = mapped_column(
        ForeignKey("capture_indexes.id"), nullable=False
    )
    timestamp: Mapped[str] = mapped_column(String(32), nullable=False)
    packets_per_sec: Mapped[int] = mapped_column(Integer, default=0)
    bytes_per_sec: Mapped[int] = mapped_column(BigInteger, default=0)
    tcp_retransmissions: Mapped[int] = mapped_column(Integer, default=0)
    tcp_resets: Mapped[int] = mapped_column(Integer, default=0)
    dns_queries: Mapped[int] = mapped_column(Integer, default=0)
    dns_responses: Mapped[int] = mapped_column(Integer, default=0)
    dns_timeouts: Mapped[int] = mapped_column(Integer, default=0)

    capture_index: Mapped["CaptureIndex"] = relationship(
        "CaptureIndex", back_populates="timeline"
    )
