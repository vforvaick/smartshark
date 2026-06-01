"""Schemas for Deep Analysis: Issue Brief, Interview Questions."""

import datetime

from pydantic import BaseModel


class IssueBriefResponse(BaseModel):
    id: int
    analysis_run_id: int
    raw_text: str
    extracted_fields: dict
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class CreateIssueBriefRequest(BaseModel):
    raw_text: str


class InterviewQuestionResponse(BaseModel):
    id: int
    question_text: str
    field_name: str
    answer: str | None = None
    is_answered: bool

    model_config = {"from_attributes": True}


class InterviewResponse(BaseModel):
    questions: list[InterviewQuestionResponse]
    is_complete: bool


class AnswerQuestionRequest(BaseModel):
    answer: str
