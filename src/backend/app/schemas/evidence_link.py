import datetime
from typing import Any

from pydantic import BaseModel

from app.models.evidence_link import TargetType


class CreateEvidenceLinkRequest(BaseModel):
    target_type: TargetType
    artifact_id: int | None = None
    target_params: dict[str, Any] = {}


class EvidenceLinkResponse(BaseModel):
    id: int
    target_type: TargetType
    artifact_id: int | None
    target_params: dict[str, Any]
    citation_text: str | None
    is_available: bool
    unavailability_reason: str | None
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class EvidenceLinkResolution(BaseModel):
    link: EvidenceLinkResponse
    deep_link: str
    resolved: bool
    resolution_data: dict[str, Any] | None = None


class BatchResolveRequest(BaseModel):
    link_ids: list[int]


class BatchResolveResponse(BaseModel):
    resolutions: list[EvidenceLinkResolution]
