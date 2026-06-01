import datetime

from pydantic import BaseModel

from app.models.annotation import AnnotationTargetType


class CreateAnnotationRequest(BaseModel):
    target_type: AnnotationTargetType
    target_id: int
    annotation_text: str
    is_false_positive: bool = False
    include_in_report: bool = True


class UpdateAnnotationRequest(BaseModel):
    annotation_text: str | None = None
    is_false_positive: bool | None = None
    include_in_report: bool | None = None


class AnnotationResponse(BaseModel):
    id: int
    target_type: AnnotationTargetType
    target_id: int
    author_id: int
    annotation_text: str
    is_false_positive: bool
    include_in_report: bool
    provenance: str
    created_at: datetime.datetime

    model_config = {"from_attributes": True}
