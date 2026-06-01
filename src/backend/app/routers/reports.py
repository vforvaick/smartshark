from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.report import (
    ReportResponse,
    ReportSectionResponse,
    UpdateSectionRequest,
    ReorderItem,
)
from app.services.report import (
    draft_report,
    get_report,
    update_section,
    reorder_sections,
)

router = APIRouter(prefix="/api", tags=["reports"])


@router.post(
    "/evidence-maps/{map_id}/reports/draft",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_draft(
    map_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a report draft from eligible evidence cards."""
    report = await draft_report(db, map_id, user.id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence map not found",
        )
    return report


@router.get(
    "/reports/{report_id}",
    response_model=ReportResponse,
)
async def get_report_endpoint(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get a report with all sections."""
    report = await get_report(db, report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )
    return report


@router.patch(
    "/reports/{report_id}/sections/{section_id}",
    response_model=ReportSectionResponse,
)
async def update_section_endpoint(
    report_id: int,
    section_id: int,
    body: UpdateSectionRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Edit a report section (title, content, inclusion)."""
    section = await update_section(
        db,
        section_id,
        title=body.title,
        content=body.content,
        is_included=body.is_included,
    )
    if section is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Section not found",
        )
    return section


@router.patch(
    "/reports/{report_id}/sections-reorder",
    response_model=list[ReportSectionResponse],
)
async def reorder_sections_endpoint(
    report_id: int,
    body: list[ReorderItem],
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Reorder report sections."""
    sections = await reorder_sections(
        db,
        report_id,
        [{"section_id": item.section_id, "order_index": item.order_index} for item in body],
    )
    if sections is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )
    return sections
