from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.user import Role, User
from app.schemas.capture_index import (
    CaptureIndexResponse,
    TimelineBucketResponse,
    PreScanSummary,
)
from app.services.capture_indexer import create_index, get_index, get_timeline, get_prescan

router = APIRouter(prefix="/api/captures", tags=["capture-index"])


@router.post("/{artifact_id}/index", response_model=CaptureIndexResponse, status_code=status.HTTP_201_CREATED)
async def build_index(
    artifact_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role(Role.admin, Role.analyst)),
):
    result = await create_index(db, artifact_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capture artifact not found")
    return result


@router.get("/{artifact_id}/index", response_model=CaptureIndexResponse)
async def get_capture_index(
    artifact_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role(Role.admin, Role.analyst)),
):
    result = await get_index(db, artifact_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capture index not found")
    return result


@router.get("/{artifact_id}/timeline", response_model=list[TimelineBucketResponse])
async def get_capture_timeline(
    artifact_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role(Role.admin, Role.analyst)),
):
    result = await get_timeline(db, artifact_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capture index not found. Build the index first.")
    return result


@router.get("/{artifact_id}/prescan", response_model=PreScanSummary)
async def get_capture_prescan(
    artifact_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role(Role.admin, Role.analyst)),
):
    result = await get_prescan(db, artifact_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capture index not found. Build the index first.")
    return result
