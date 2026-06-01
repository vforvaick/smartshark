"""Schemas for audit log and lifecycle endpoints."""

import datetime
from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: int
    user_id: int
    action: str
    target_type: str
    target_id: int
    details: dict | None
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class ArtifactLifecycleResponse(BaseModel):
    id: int
    status: str
    original_filename: str
    message: str | None = None

    model_config = {"from_attributes": True}


class HardDeleteResponse(BaseModel):
    id: int
    message: str
    warning: str
    affected_links: int
