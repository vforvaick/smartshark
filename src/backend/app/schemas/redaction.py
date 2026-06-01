import datetime

from pydantic import BaseModel


class RedactionPolicyResponse(BaseModel):
    id: int
    mask_payloads: bool
    mask_credentials: bool
    mask_auth_headers: bool
    mask_pan_values: bool
    anonymize_ips: bool
    anonymize_macs: bool
    mask_dns_suffix: bool
    raw_sharing_allowed: bool
    profile: str

    model_config = {"from_attributes": True}


class UpdateRedactionPolicyRequest(BaseModel):
    mask_payloads: bool | None = None
    mask_credentials: bool | None = None
    mask_auth_headers: bool | None = None
    mask_pan_values: bool | None = None
    anonymize_ips: bool | None = None
    anonymize_macs: bool | None = None
    mask_dns_suffix: bool | None = None
    raw_sharing_allowed: bool | None = None
    profile: str | None = None


class RedactRequest(BaseModel):
    content: str


class RedactResponse(BaseModel):
    redacted_content: str
    policy_applied: str


class RawContextSubmitRequest(BaseModel):
    content: str
    context_category: str = "raw-context"
    confirm_sharing: bool = False


class RawContextSubmitResponse(BaseModel):
    redacted_content: str
    exploratory: bool
    warning: str
    logged: bool
    request_log_id: int


class AIRequestLogResponse(BaseModel):
    id: int
    user_id: int
    analysis_run_id: int | None
    context_category: str
    model_used: str
    redacted: bool
    timestamp: datetime.datetime

    model_config = {"from_attributes": True}
