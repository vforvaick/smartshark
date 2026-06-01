"""Admin lifecycle router — archive, restore, hard-delete captures + audit log."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.user import Role, User
from app.models.capture import CaptureArtifact
from app.schemas.audit import AuditLogResponse, ArtifactLifecycleResponse, HardDeleteResponse
from app.services.audit import get_audit_log
from app.services.lifecycle import archive_artifact, restore_artifact, hard_delete_artifact

router = APIRouter(prefix="/api/admin", tags=["admin-lifecycle"])


@router.post(
    "/captures/{artifact_id}/archive",
    response_model=ArtifactLifecycleResponse,
)
async def archive_capture(
    artifact_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(Role.admin)),
):
    """Archive a capture artifact (admin only)."""
    try:
        artifact = await archive_artifact(db, artifact_id, admin)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return ArtifactLifecycleResponse(
        id=artifact.id,
        status=artifact.status.value,
        original_filename=artifact.original_filename,
        message="Artifact archived",
    )


@router.post(
    "/captures/{artifact_id}/restore",
    response_model=ArtifactLifecycleResponse,
)
async def restore_capture(
    artifact_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(Role.admin)),
):
    """Restore an archived capture artifact (admin only)."""
    try:
        artifact = await restore_artifact(db, artifact_id, admin)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return ArtifactLifecycleResponse(
        id=artifact.id,
        status=artifact.status.value,
        original_filename=artifact.original_filename,
        message="Artifact restored",
    )


@router.delete(
    "/captures/{artifact_id}",
    response_model=HardDeleteResponse,
)
async def hard_delete_capture(
    artifact_id: int,
    confirmed: bool = Query(False, alias="confirmed"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(Role.admin)),
):
    """Hard delete a capture artifact (admin only, requires confirmation).

    Pass ?confirmed=true to confirm. This action is irreversible and will
    mark any evidence links pointing to this artifact as unavailable.
    """
    try:
        result = await hard_delete_artifact(db, artifact_id, admin, confirmed=confirmed)
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return HardDeleteResponse(**result)


@router.get(
    "/audit-log",
    response_model=list[AuditLogResponse],
)
async def list_audit_log(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(Role.admin)),
):
    """View audit log entries (admin only)."""
    entries = await get_audit_log(db, limit=limit, offset=offset)
    return entries
