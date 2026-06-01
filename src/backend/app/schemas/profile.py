import datetime

from pydantic import BaseModel

from app.models.profile import AnalysisProfile


class ProfileInfo(BaseModel):
    """A profile listed in the catalog."""
    id: str
    description: str
    is_default: bool = False


class SetProfileRequest(BaseModel):
    profile: AnalysisProfile


class ProfileConfigResponse(BaseModel):
    id: int
    analysis_run_id: int
    profile: AnalysisProfile
    assumptions: list[str] = []
    limitations: list[str] = []
    check_weighting: dict[str, float] = {}
    mapping_questions: list[dict] = []
    created_at: datetime.datetime | None = None

    model_config = {"from_attributes": True}


class ProgressiveQuestionsResponse(BaseModel):
    questions: list[dict]
