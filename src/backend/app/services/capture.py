"""Capture Artifact service — handles upload, storage, hashing, and diagnostics."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.capture import CaptureArtifact, ImportDiagnostic, ArtifactStatus, DiagnosticCategory
from app.services.packet_query import validate_capture


@dataclass
class ImportResult:
    artifact: CaptureArtifact | None = None
    diagnostic: ImportDiagnostic | None = None
    is_duplicate: bool = False


def _compute_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


async def import_capture(
    db: AsyncSession,
    content: bytes,
    filename: str,
) -> ImportResult:
    """Import a capture file. Returns ImportResult with artifact or diagnostic."""
    # Validate capture format
    result = validate_capture(content, filename)
    if not result.valid:
        diagnostic = ImportDiagnostic(
            original_filename=filename,
            file_size_bytes=len(content),
            category=result.category,
            detail=result.detail,
            suggested_next_step=result.suggested_next_step,
        )
        db.add(diagnostic)
        await db.commit()
        await db.refresh(diagnostic)
        return ImportResult(diagnostic=diagnostic)

    # Compute content hash
    content_hash = _compute_hash(content)

    # Check for duplicate
    existing = await db.execute(
        select(CaptureArtifact).where(CaptureArtifact.content_hash == content_hash)
    )
    existing_artifact = existing.scalar_one_or_none()
    if existing_artifact is not None:
        return ImportResult(artifact=existing_artifact, is_duplicate=True)

    # Store file
    settings = get_settings()
    storage_path = settings.capture_storage_path
    storage_path.mkdir(parents=True, exist_ok=True)
    file_path = storage_path / content_hash
    file_path.write_bytes(content)

    # Create artifact record
    artifact = CaptureArtifact(
        content_hash=content_hash,
        original_filename=filename,
        size_bytes=len(content),
        file_path=str(file_path),
        status=ArtifactStatus.ready,
    )
    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)
    return ImportResult(artifact=artifact)


async def list_artifacts(db: AsyncSession) -> list[CaptureArtifact]:
    result = await db.execute(
        select(CaptureArtifact)
        .where(CaptureArtifact.status != ArtifactStatus.archived)
        .order_by(CaptureArtifact.created_at.desc())
    )
    return list(result.scalars().all())


async def get_artifact(db: AsyncSession, artifact_id: int) -> CaptureArtifact | None:
    result = await db.execute(
        select(CaptureArtifact).where(CaptureArtifact.id == artifact_id)
    )
    return result.scalar_one_or_none()
