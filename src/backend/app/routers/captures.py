from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.user import Role, User
from app.schemas.capture import CaptureArtifactResponse
from app.services.capture import import_capture, list_artifacts, get_artifact

router = APIRouter(prefix="/api/captures", tags=["captures"])


@router.post("/upload", response_model=CaptureArtifactResponse)
async def upload_capture(
    response: Response,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role(Role.admin, Role.analyst)),
):
    content = await file.read()
    result = await import_capture(db, content, file.filename or "unknown")

    if result.diagnostic is not None:
        raise HTTPException(
            status_code=422,
            detail={
                "original_filename": result.diagnostic.original_filename,
                "file_size_bytes": result.diagnostic.file_size_bytes,
                "category": result.diagnostic.category.value,
                "detail": result.diagnostic.detail,
                "suggested_next_step": result.diagnostic.suggested_next_step,
            },
        )

    if result.is_duplicate:
        response.status_code = status.HTTP_200_OK
    else:
        response.status_code = status.HTTP_201_CREATED

    return result.artifact


@router.get("", response_model=list[CaptureArtifactResponse])
async def list_captures(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role(Role.admin, Role.analyst)),
):
    return await list_artifacts(db)


@router.get("/{artifact_id}", response_model=CaptureArtifactResponse)
async def get_capture(
    artifact_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role(Role.admin, Role.analyst)),
):
    artifact = await get_artifact(db, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capture artifact not found")
    return artifact
