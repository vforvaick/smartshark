"""Export router — Markdown/PDF report export endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.export import ExportValidationResponse
from app.services.export import (
    validate_report_for_export,
    export_markdown,
    export_pdf,
)

router = APIRouter(prefix="/api", tags=["export"])


@router.get(
    "/reports/{report_id}/export/markdown",
)
async def export_markdown_endpoint(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Export report as Markdown."""
    try:
        md = await export_markdown(db, report_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if md is None:
        raise HTTPException(status_code=404, detail="Report not found.")

    return Response(
        content=md,
        media_type="text/markdown; charset=utf-8",
    )


@router.get(
    "/reports/{report_id}/export/pdf",
)
async def export_pdf_endpoint(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Export report as PDF."""
    try:
        pdf_bytes = await export_pdf(db, report_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if pdf_bytes is None:
        raise HTTPException(status_code=404, detail="Report not found.")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=report-{report_id}.pdf"},
    )


@router.post(
    "/reports/{report_id}/export/validate",
    response_model=ExportValidationResponse,
)
async def validate_export_endpoint(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Validate a report for export readiness."""
    valid, errors = await validate_report_for_export(db, report_id)
    if not errors and not valid:
        # If not valid but no explicit errors, report doesn't exist
        raise HTTPException(status_code=404, detail="Report not found.")
    return ExportValidationResponse(valid=valid, errors=errors)
