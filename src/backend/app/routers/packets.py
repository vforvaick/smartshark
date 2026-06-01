from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.user import Role, User
from app.schemas.packet import (
    PacketSummary,
    FrameDetail,
    PayloadPreview,
)
from app.services.capture import get_artifact
from app.services.packet_query import list_packets, get_frame_detail, get_payload_preview

router = APIRouter(prefix="/api/captures/{artifact_id}", tags=["packets"])


async def _resolve_artifact(
    artifact_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role(Role.admin, Role.analyst)),
) -> str:
    """Resolve artifact_id to its file_path, or 404."""
    artifact = await get_artifact(db, artifact_id)
    if artifact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Capture artifact not found",
        )
    return artifact.file_path


@router.get("/packets", response_model=list[PacketSummary])
async def list_capture_packets(
    artifact_id: int,
    filter: str | None = Query(None, alias="filter"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    file_path: str = Depends(_resolve_artifact),
):
    """List packets for a capture artifact with optional display filter."""
    packets, filter_error = list_packets(file_path, display_filter=filter, limit=limit, offset=offset)
    if filter_error is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=filter_error.error,
        )
    return packets


@router.get("/frames/{frame_number}", response_model=FrameDetail)
async def get_frame(
    artifact_id: int,
    frame_number: int,
    file_path: str = Depends(_resolve_artifact),
):
    """Get frame detail / dissector fields for a specific frame."""
    detail = get_frame_detail(file_path, frame_number)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Frame {frame_number} not found",
        )
    return detail


@router.get("/frames/{frame_number}/payload", response_model=PayloadPreview)
async def get_payload(
    artifact_id: int,
    frame_number: int,
    file_path: str = Depends(_resolve_artifact),
):
    """Get payload/bytes preview for a specific frame."""
    payload = get_payload_preview(file_path, frame_number)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Frame {frame_number} not found",
        )
    return payload
