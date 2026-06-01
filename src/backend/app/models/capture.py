import enum
from datetime import datetime, timezone

from sqlalchemy import String, Integer, BigInteger, DateTime, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ArtifactStatus(str, enum.Enum):
    importing = "importing"
    ready = "ready"
    archived = "archived"


class DiagnosticCategory(str, enum.Enum):
    invalid_format = "invalid_format"
    unsupported_format = "unsupported_format"
    corrupt_capture = "corrupt_capture"
    too_large = "too_large"
    tool_failure = "tool_failure"


class CaptureArtifact(Base):
    __tablename__ = "capture_artifacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    original_filename: Mapped[str] = mapped_column(String(256))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    file_path: Mapped[str] = mapped_column(String(512))
    status: Mapped[ArtifactStatus] = mapped_column(
        Enum(ArtifactStatus), default=ArtifactStatus.importing
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow
    )


class ImportDiagnostic(Base):
    __tablename__ = "import_diagnostics"

    id: Mapped[int] = mapped_column(primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(256))
    file_size_bytes: Mapped[int] = mapped_column(BigInteger)
    category: Mapped[DiagnosticCategory] = mapped_column(Enum(DiagnosticCategory))
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_next_step: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow
    )
