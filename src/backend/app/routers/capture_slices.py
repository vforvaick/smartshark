from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.user import Role, User
from app.schemas.capture_slice import (
    CreateSliceRequest,
    CaptureSliceResponse,
    ExportedSliceResponse,
)
from app.services import capture_slice as slice_service

router = APIRouter(prefix="/api/captures", tags=["capture-slices"])


def _validate_artifact_id(artifact_id: int, slice_source_id: int):
    """Ensure the slice belongs to the given artifact."""
    if artifact_id != slice_source_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Slice does not belong to this artifact",
        )


@router.post(
    "/{artifact_id}/slices",
    response_model=CaptureSliceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_slice(
    artifact_id: int,
    body: CreateSliceRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role(Role.admin, Role.analyst)),
):
    try:
        result = await slice_service.create_slice(
            db, artifact_id, body.criteria_type, body.criteria_params
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Capture artifact not found",
        )
    return result


@router.get(
    "/{artifact_id}/slices",
    response_model=list[CaptureSliceResponse],
)
async def list_slices(
    artifact_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role(Role.admin, Role.analyst)),
):
    return await slice_service.list_slices(db, artifact_id)


@router.get(
    "/{artifact_id}/slices/{slice_id}",
    response_model=CaptureSliceResponse,
)
async def get_slice(
    artifact_id: int,
    slice_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role(Role.admin, Role.analyst)),
):
    result = await slice_service.get_slice(db, slice_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slice not found",
        )
    _validate_artifact_id(artifact_id, result.source_artifact_id)
    return result


@router.post(
    "/{artifact_id}/slices/{slice_id}/export",
    response_model=ExportedSliceResponse,
)
async def export_slice(
    artifact_id: int,
    slice_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role(Role.admin, Role.analyst)),
):
    # Validate slice belongs to artifact
    existing = await slice_service.get_slice(db, slice_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slice not found",
        )
    _validate_artifact_id(artifact_id, existing.source_artifact_id)

    result = await slice_service.export_slice(db, slice_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slice or source artifact not found",
        )

    return ExportedSliceResponse(
        slice=result["slice"],
        artifact_id=result["artifact"].id,
        content_hash=result["artifact"].content_hash,
        is_new=result["is_new"],
    )
