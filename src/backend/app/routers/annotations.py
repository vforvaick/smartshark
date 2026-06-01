from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.annotation import AnnotationTargetType
from app.models.user import User
from app.schemas.annotation import (
    AnnotationResponse,
    CreateAnnotationRequest,
    UpdateAnnotationRequest,
)
from app.services.annotation import (
    create_annotation,
    get_annotation,
    list_annotations,
    update_annotation,
    delete_annotation,
)

router = APIRouter(prefix="/api/annotations", tags=["annotations"])


@router.post("", response_model=AnnotationResponse, status_code=status.HTTP_201_CREATED)
async def create_annotation_endpoint(
    body: CreateAnnotationRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ann = await create_annotation(
        db=db,
        target_type=body.target_type,
        target_id=body.target_id,
        author_id=user.id,
        annotation_text=body.annotation_text,
        is_false_positive=body.is_false_positive,
        include_in_report=body.include_in_report,
    )
    return ann


@router.get("", response_model=list[AnnotationResponse])
async def list_annotations_endpoint(
    target_type: AnnotationTargetType | None = Query(None),
    target_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return await list_annotations(db, target_type=target_type, target_id=target_id)


@router.patch("/{annotation_id}", response_model=AnnotationResponse)
async def update_annotation_endpoint(
    annotation_id: int,
    body: UpdateAnnotationRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ann = await get_annotation(db, annotation_id)
    if ann is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Annotation not found")
    return await update_annotation(
        db,
        ann,
        annotation_text=body.annotation_text,
        is_false_positive=body.is_false_positive,
        include_in_report=body.include_in_report,
    )


@router.delete("/{annotation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_annotation_endpoint(
    annotation_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ann = await get_annotation(db, annotation_id)
    if ann is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Annotation not found")
    if ann.author_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete another user's annotation",
        )
    await delete_annotation(db, ann)
