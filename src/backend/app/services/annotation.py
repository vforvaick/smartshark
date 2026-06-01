from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.annotation import Annotation, AnnotationTargetType


async def create_annotation(
    db: AsyncSession,
    target_type: AnnotationTargetType,
    target_id: int,
    author_id: int,
    annotation_text: str,
    is_false_positive: bool = False,
    include_in_report: bool = True,
) -> Annotation:
    ann = Annotation(
        target_type=target_type,
        target_id=target_id,
        author_id=author_id,
        annotation_text=annotation_text,
        is_false_positive=is_false_positive,
        include_in_report=include_in_report,
        provenance="analyst",
    )
    db.add(ann)
    await db.commit()
    await db.refresh(ann)
    return ann


async def list_annotations(
    db: AsyncSession,
    target_type: AnnotationTargetType | None = None,
    target_id: int | None = None,
) -> list[Annotation]:
    stmt = select(Annotation).order_by(Annotation.created_at)
    if target_type is not None:
        stmt = stmt.where(Annotation.target_type == target_type)
    if target_id is not None:
        stmt = stmt.where(Annotation.target_id == target_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_annotation(db: AsyncSession, annotation_id: int) -> Annotation | None:
    result = await db.execute(select(Annotation).where(Annotation.id == annotation_id))
    return result.scalar_one_or_none()


async def update_annotation(
    db: AsyncSession,
    annotation: Annotation,
    annotation_text: str | None = None,
    is_false_positive: bool | None = None,
    include_in_report: bool | None = None,
) -> Annotation:
    if annotation_text is not None:
        annotation.annotation_text = annotation_text
    if is_false_positive is not None:
        annotation.is_false_positive = is_false_positive
    if include_in_report is not None:
        annotation.include_in_report = include_in_report
    await db.commit()
    await db.refresh(annotation)
    return annotation


async def delete_annotation(db: AsyncSession, annotation: Annotation) -> None:
    await db.delete(annotation)
    await db.commit()
