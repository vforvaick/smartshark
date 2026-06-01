"""Capture artifact lifecycle service — archive, restore, hard-delete."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capture import CaptureArtifact, ArtifactStatus
from app.models.evidence_link import EvidenceLink
from app.models.user import User
from app.services.audit import log_action


async def get_artifact_or_raise(db: AsyncSession, artifact_id: int) -> CaptureArtifact:
    """Get an artifact or raise ValueError if not found."""
    result = await db.execute(
        select(CaptureArtifact).where(CaptureArtifact.id == artifact_id)
    )
    artifact = result.scalar_one_or_none()
    if artifact is None:
        raise ValueError(f"Capture artifact {artifact_id} not found")
    return artifact


async def archive_artifact(
    db: AsyncSession,
    artifact_id: int,
    admin_user: User,
) -> CaptureArtifact:
    """Archive a capture artifact (admin only)."""
    artifact = await get_artifact_or_raise(db, artifact_id)
    artifact.status = ArtifactStatus.archived
    await db.commit()
    await db.refresh(artifact)

    await log_action(
        db,
        user_id=admin_user.id,
        action="archive_artifact",
        target_type="capture_artifact",
        target_id=artifact_id,
        details={"original_filename": artifact.original_filename},
    )
    return artifact


async def restore_artifact(
    db: AsyncSession,
    artifact_id: int,
    admin_user: User,
) -> CaptureArtifact:
    """Restore an archived capture artifact (admin only)."""
    artifact = await get_artifact_or_raise(db, artifact_id)
    artifact.status = ArtifactStatus.ready
    await db.commit()
    await db.refresh(artifact)

    await log_action(
        db,
        user_id=admin_user.id,
        action="restore_artifact",
        target_type="capture_artifact",
        target_id=artifact_id,
        details={"original_filename": artifact.original_filename},
    )
    return artifact


async def hard_delete_artifact(
    db: AsyncSession,
    artifact_id: int,
    admin_user: User,
    confirmed: bool = False,
) -> dict:
    """Hard delete a capture artifact (admin only, requires confirmation).

    Returns a dict with the deletion result and warning about evidence links.
    """
    artifact = await get_artifact_or_raise(db, artifact_id)

    if not confirmed:
        raise ValueError("Hard delete requires confirmed=true")

    # Count evidence links that will be affected
    link_result = await db.execute(
        select(EvidenceLink).where(EvidenceLink.artifact_id == artifact_id)
    )
    affected_links = list(link_result.scalars().all())

    # Mark evidence links as unavailable
    await db.execute(
        update(EvidenceLink)
        .where(EvidenceLink.artifact_id == artifact_id)
        .values(
            is_available=False,
            unavailability_reason="Artifact hard-deleted by admin",
        )
    )

    # Log audit before deletion (so we still have the artifact_id)
    await log_action(
        db,
        user_id=admin_user.id,
        action="hard_delete_artifact",
        target_type="capture_artifact",
        target_id=artifact_id,
        details={
            "original_filename": artifact.original_filename,
            "content_hash": artifact.content_hash,
            "affected_evidence_links": len(affected_links),
        },
    )

    # Delete the artifact
    await db.delete(artifact)
    await db.commit()

    return {
        "id": artifact_id,
        "message": "Artifact hard-deleted",
        "warning": f"{len(affected_links)} evidence link(s) marked as unavailable",
        "affected_links": len(affected_links),
    }
