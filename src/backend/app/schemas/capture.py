from datetime import datetime

from pydantic import BaseModel

from app.models.capture import ArtifactStatus, DiagnosticCategory


class CaptureArtifactResponse(BaseModel):
    id: int
    content_hash: str
    original_filename: str
    size_bytes: int
    status: ArtifactStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class ImportDiagnosticResponse(BaseModel):
    id: int
    original_filename: str
    file_size_bytes: int
    category: DiagnosticCategory
    detail: str | None
    suggested_next_step: str
    created_at: datetime

    model_config = {"from_attributes": True}
