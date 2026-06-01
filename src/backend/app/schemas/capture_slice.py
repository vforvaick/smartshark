from datetime import datetime

from pydantic import BaseModel

from app.models.capture_slice import SliceCriteria


class CreateSliceRequest(BaseModel):
    criteria_type: SliceCriteria
    criteria_params: dict


class CaptureSliceResponse(BaseModel):
    id: int
    source_artifact_id: int
    criteria_type: SliceCriteria
    criteria_params: dict
    exported_artifact_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ExportedSliceResponse(BaseModel):
    slice: CaptureSliceResponse
    artifact_id: int
    content_hash: str
    is_new: bool
