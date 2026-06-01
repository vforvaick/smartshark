import datetime

from pydantic import BaseModel

from app.models.report import ReportSectionType, ReportStatus


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


class ReportSectionResponse(BaseModel):
    id: int
    report_id: int
    section_type: ReportSectionType
    order_index: int
    title: str
    content: str
    claim_ids: list[int] = []
    is_included: bool = True
    deep_links: list[dict] = []

    model_config = {"from_attributes": True}


class ReportResponse(BaseModel):
    id: int
    evidence_map_id: int
    title: str
    created_by: int
    status: ReportStatus
    created_at: datetime.datetime
    updated_at: datetime.datetime
    sections: list[ReportSectionResponse] = []

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class UpdateSectionRequest(BaseModel):
    title: str | None = None
    content: str | None = None
    is_included: bool | None = None


class ReorderItem(BaseModel):
    section_id: int
    order_index: int
