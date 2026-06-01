"""Schemas for scoped analysis (Issue #12)."""

import datetime
from typing import Literal

from pydantic import BaseModel

from app.models.scoped_analysis import ScopeType


ScopeTypeLiteral = Literal[
    "time_window", "endpoint", "conversation",
    "display_filter", "symptom", "playbook", "combined",
]


class CreateScopeRequest(BaseModel):
    scope_type: ScopeTypeLiteral
    scope_params: dict


class AnalysisScopeResponse(BaseModel):
    id: int
    analysis_run_id: int
    scope_type: ScopeType
    scope_params: dict
    created_at: datetime.datetime

    model_config = {"from_attributes": True}
