import datetime

from pydantic import BaseModel

from app.models.analysis import AnalysisRunStatus


class CreateAnalysisRunRequest(BaseModel):
    capture_artifact_id: int


class ProgressMessageResponse(BaseModel):
    id: int
    message: str
    timestamp: datetime.datetime

    model_config = {"from_attributes": True}


class CheckResultResponse(BaseModel):
    id: int
    analysis_run_id: int
    check_name: str
    status: str
    summary: str
    evidence_refs: list[dict] = []
    limitations: list[str] = []
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class AnalysisRunResponse(BaseModel):
    id: int
    capture_artifact_id: int
    status: AnalysisRunStatus
    failure_category: str | None = None
    suggested_next_step: str | None = None
    created_at: datetime.datetime
    progress: list[ProgressMessageResponse] = []
    check_results: list[CheckResultResponse] = []

    model_config = {"from_attributes": True}


class FailRunRequest(BaseModel):
    category: str
    suggested_next_step: str


class AddProgressRequest(BaseModel):
    message: str


class QuickAnalysisRequest(BaseModel):
    issue_brief: str | None = None
