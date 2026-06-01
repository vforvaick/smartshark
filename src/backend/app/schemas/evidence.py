import datetime

from pydantic import BaseModel

from app.models.evidence import ClaimStatus


# ---------------------------------------------------------------------------
# Claim
# ---------------------------------------------------------------------------


class CreateClaimRequest(BaseModel):
    claim_text: str
    status: ClaimStatus
    key_facts: list[str] = []
    evidence_refs: list[dict] = []
    verification_step: str | None = None


class UpdateClaimStatusRequest(BaseModel):
    status: ClaimStatus
    evidence_refs: list[dict] | None = None


class UpdateReportableRequest(BaseModel):
    is_reportable: bool


class ClaimResponse(BaseModel):
    id: int
    evidence_map_id: int
    claim_text: str
    status: ClaimStatus
    key_facts: list[str] = []
    evidence_refs: list[dict] = []
    is_reportable: bool = False
    verification_step: str | None = None
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Evidence Map
# ---------------------------------------------------------------------------


class EvidenceMapResponse(BaseModel):
    id: int
    analysis_run_id: int
    created_at: datetime.datetime
    claims: list[ClaimResponse] = []
    limitations: list[dict] = []

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Evidence Card
# ---------------------------------------------------------------------------


class EvidenceAction(BaseModel):
    type: str
    label: str


class EvidenceCardResponse(BaseModel):
    claim_id: int
    claim_text: str
    status: ClaimStatus
    key_facts: list[str] = []
    evidence_refs: list[dict] = []
    is_reportable: bool = False
    actions: list[EvidenceAction] = []
