"""Export schemas — validation response for report export."""

from pydantic import BaseModel


class ExportValidationResponse(BaseModel):
    valid: bool
    errors: list[str] = []
