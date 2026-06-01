"""Capture Slice service — handles slice views and export-as-artifact flow."""

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.capture import CaptureArtifact, ArtifactStatus
from app.models.capture_slice import CaptureSlice, SliceCriteria
from app.models.evidence_link import EvidenceLink, TargetType
from pathlib import Path


def _compute_slice_hash(source_hash: str, criteria_type: str, criteria_params: dict) -> str:
    """Compute a deterministic content identity for a slice."""
    raw = f"{source_hash}:{criteria_type}:{json.dumps(criteria_params, sort_keys=True)}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def create_slice(
    db: AsyncSession,
    source_artifact_id: int,
    criteria_type: SliceCriteria,
    criteria_params: dict,
) -> CaptureSlice:
    """Create a slice view over a capture artifact."""
    # Validate source artifact exists
    result = await db.execute(
        select(CaptureArtifact).where(CaptureArtifact.id == source_artifact_id)
    )
    artifact = result.scalar_one_or_none()
    if artifact is None:
        return None

    # Validate criteria_params has required fields
    _validate_params(criteria_type, criteria_params)

    slice_obj = CaptureSlice(
        source_artifact_id=source_artifact_id,
        criteria_type=criteria_type,
        criteria_params=criteria_params,
    )
    db.add(slice_obj)
    await db.commit()
    await db.refresh(slice_obj)
    return slice_obj


def _validate_params(criteria_type: SliceCriteria, params: dict) -> None:
    """Validate that criteria_params has required fields for the given type."""
    if criteria_type == SliceCriteria.time_range:
        if "time_start" not in params or "time_end" not in params:
            raise ValueError("time_range requires time_start and time_end")
    elif criteria_type == SliceCriteria.display_filter:
        if "filter_text" not in params:
            raise ValueError("display_filter requires filter_text")
    elif criteria_type == SliceCriteria.endpoint_pair:
        if "src_ip" not in params or "dst_ip" not in params:
            raise ValueError("endpoint_pair requires src_ip and dst_ip")
    elif criteria_type == SliceCriteria.conversation:
        if "conversation_id" not in params:
            raise ValueError("conversation requires conversation_id")


async def list_slices(db: AsyncSession, artifact_id: int) -> list[CaptureSlice]:
    result = await db.execute(
        select(CaptureSlice)
        .where(CaptureSlice.source_artifact_id == artifact_id)
        .order_by(CaptureSlice.created_at.desc())
    )
    return list(result.scalars().all())


async def get_slice(db: AsyncSession, slice_id: int) -> CaptureSlice | None:
    result = await db.execute(
        select(CaptureSlice).where(CaptureSlice.id == slice_id)
    )
    return result.scalar_one_or_none()


async def export_slice(db: AsyncSession, slice_id: int) -> dict:
    """Export a slice as a new Capture Artifact.

    Returns dict with:
      - slice: the updated CaptureSlice
      - artifact: the new (or existing) CaptureArtifact
      - is_new: whether a new artifact was created
    """
    result = await db.execute(
        select(CaptureSlice).where(CaptureSlice.id == slice_id)
    )
    slice_obj = result.scalar_one_or_none()
    if slice_obj is None:
        return None

    # Get source artifact for hash derivation
    src_result = await db.execute(
        select(CaptureArtifact).where(CaptureArtifact.id == slice_obj.source_artifact_id)
    )
    source_artifact = src_result.scalar_one_or_none()
    if source_artifact is None:
        return None

    # Already exported?
    if slice_obj.exported_artifact_id is not None:
        exp_result = await db.execute(
            select(CaptureArtifact).where(CaptureArtifact.id == slice_obj.exported_artifact_id)
        )
        existing = exp_result.scalar_one_or_none()
        return {"slice": slice_obj, "artifact": existing, "is_new": False}

    # Compute deterministic content hash for the slice
    slice_hash = _compute_slice_hash(
        source_artifact.content_hash,
        slice_obj.criteria_type.value,
        slice_obj.criteria_params,
    )

    # Check if this slice content already exists as an artifact
    existing_result = await db.execute(
        select(CaptureArtifact).where(CaptureArtifact.content_hash == slice_hash)
    )
    existing_artifact = existing_result.scalar_one_or_none()

    if existing_artifact is not None:
        # Link to existing artifact
        slice_obj.exported_artifact_id = existing_artifact.id
        await db.commit()
        await db.refresh(slice_obj)
        return {"slice": slice_obj, "artifact": existing_artifact, "is_new": False}

    # Create new artifact from slice
    # In stub mode, we create a minimal artifact record pointing to a derived path
    settings = get_settings()
    storage_path = settings.capture_storage_path
    storage_path.mkdir(parents=True, exist_ok=True)
    file_path = storage_path / f"slice-{slice_hash[:16]}"

    # Write a stub slice file (real impl would use tshark to export)
    file_path.write_text(f"slice-of:{source_artifact.content_hash}")

    # Estimate slice size (stub: use a fraction based on criteria)
    estimated_size = source_artifact.size_bytes // 4

    new_artifact = CaptureArtifact(
        content_hash=slice_hash,
        original_filename=f"slice-{slice_obj.criteria_type.value}-{source_artifact.original_filename}",
        size_bytes=estimated_size,
        file_path=str(file_path),
        status=ArtifactStatus.ready,
    )
    db.add(new_artifact)
    await db.commit()
    await db.refresh(new_artifact)

    # Link slice to exported artifact
    slice_obj.exported_artifact_id = new_artifact.id
    await db.commit()
    await db.refresh(slice_obj)

    return {"slice": slice_obj, "artifact": new_artifact, "is_new": True}
