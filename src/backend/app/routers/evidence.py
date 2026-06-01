from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_current_user
from app.models.analysis import AnalysisRun, AnalysisRunStatus
from app.models.evidence import EvidenceMap, Claim, ClaimStatus
from app.models.user import User
from app.schemas.evidence import (
    CreateClaimRequest,
    UpdateClaimStatusRequest,
    UpdateReportableRequest,
    ClaimResponse,
    EvidenceMapResponse,
    EvidenceCardResponse,
    EvidenceAction,
)
from app.services.evidence_validator import (
    ValidationError,
    validate_claim_for_create,
    validate_claim_status_update,
    validate_reportable,
)
from app.services.hardening import get_vantage_point, validate_claim_for_vantage_point, get_limitations as get_run_limitations

router = APIRouter(prefix="/api", tags=["evidence"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _load_evidence_map(db: AsyncSession, map_id: int) -> EvidenceMap | None:
    result = await db.execute(
        select(EvidenceMap)
        .options(selectinload(EvidenceMap.claims))
        .where(EvidenceMap.id == map_id)
    )
    return result.scalar_one_or_none()


async def _load_claim(db: AsyncSession, claim_id: int) -> Claim | None:
    result = await db.execute(
        select(Claim).where(Claim.id == claim_id)
    )
    return result.scalar_one_or_none()


def _build_card_actions(claim: Claim) -> list[EvidenceAction]:
    """Build available actions for an Evidence Card based on claim state."""
    actions: list[EvidenceAction] = [
        EvidenceAction(type="annotate", label="Add annotation"),
    ]

    if claim.status in (ClaimStatus.verified, ClaimStatus.likely):
        actions.append(EvidenceAction(type="add_to_report", label="Add to report"))

    # Allow status promotion/demotion
    if claim.status == ClaimStatus.hypothesis:
        actions.append(EvidenceAction(type="promote", label="Promote to likely/verified"))
    elif claim.status in (ClaimStatus.verified, ClaimStatus.likely):
        actions.append(EvidenceAction(type="demote", label="Demote to hypothesis"))

    # Evidence link navigation
    for ref in claim.evidence_refs:
        ref_type = ref.get("type", "")
        if ref_type == "frame_detail":
            actions.append(EvidenceAction(type="open_frame", label=f"Open frame {ref.get('frame', '?')}"))
        elif ref_type == "packet_subset":
            actions.append(EvidenceAction(type="open_packets", label="Open packet subset"))
        elif ref_type == "follow_stream":
            actions.append(EvidenceAction(type="follow_stream", label=f"Follow stream {ref.get('stream_id', '?')}"))

    actions.append(EvidenceAction(type="mark_false_positive", label="Mark false positive"))
    return actions


# ---------------------------------------------------------------------------
# Evidence Map endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/analysis-runs/{run_id}/evidence-map",
    response_model=EvidenceMapResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_evidence_map(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Create an Evidence Map for an Analysis Run."""
    run_result = await db.execute(
        select(AnalysisRun).where(AnalysisRun.id == run_id)
    )
    run = run_result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found")

    existing = await db.execute(
        select(EvidenceMap).where(EvidenceMap.analysis_run_id == run_id)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Evidence map already exists for this analysis run",
        )

    emap = EvidenceMap(analysis_run_id=run_id)
    db.add(emap)
    await db.commit()
    return await _load_evidence_map(db, emap.id)


@router.get(
    "/analysis-runs/{run_id}/evidence-map",
    response_model=EvidenceMapResponse,
)
async def get_evidence_map(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get the Evidence Map for an Analysis Run."""
    result = await db.execute(
        select(EvidenceMap)
        .options(selectinload(EvidenceMap.claims))
        .where(EvidenceMap.analysis_run_id == run_id)
    )
    emap = result.scalar_one_or_none()
    if emap is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence map not found")

    # Attach limitations
    limitations = await get_run_limitations(db, emap.analysis_run_id)
    resp = EvidenceMapResponse.model_validate(emap)
    resp.limitations = [
        {"id": l.id, "category": l.category.value, "detail": l.detail}
        for l in limitations
    ]
    return resp


# ---------------------------------------------------------------------------
# Claims
# ---------------------------------------------------------------------------


@router.post(
    "/evidence-maps/{map_id}/claims",
    response_model=ClaimResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_claim(
    map_id: int,
    body: CreateClaimRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Add a claim to an Evidence Map with validation."""
    emap = await _load_evidence_map(db, map_id)
    if emap is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence map not found")

    # Validate claim before creation
    try:
        validate_claim_for_create(
            status=body.status,
            evidence_refs=body.evidence_refs,
            verification_step=body.verification_step,
        )
        # Enforce vantage point limits
        vp = await get_vantage_point(db, run_id=emap.analysis_run_id)
        validate_claim_for_vantage_point(vp, body.status)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=e.message,
        )

    claim = Claim(
        evidence_map_id=map_id,
        claim_text=body.claim_text,
        status=body.status,
        key_facts=body.key_facts,
        evidence_refs=body.evidence_refs,
        verification_step=body.verification_step,
    )
    db.add(claim)
    await db.commit()
    await db.refresh(claim)
    return claim


@router.patch(
    "/claims/{claim_id}/status",
    response_model=ClaimResponse,
)
async def update_claim_status(
    claim_id: int,
    body: UpdateClaimStatusRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Update claim status with validation."""
    claim = await _load_claim(db, claim_id)
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    try:
        validate_claim_status_update(
            claim=claim,
            new_status=body.status,
            evidence_refs=body.evidence_refs,
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=e.message,
        )

    claim.status = body.status
    if body.evidence_refs is not None:
        claim.evidence_refs = body.evidence_refs

    # Demote from verified/likely → anything else: clear reportable
    if body.status not in (ClaimStatus.verified, ClaimStatus.likely) and claim.is_reportable:
        claim.is_reportable = False

    await db.commit()
    await db.refresh(claim)
    return claim


@router.patch(
    "/claims/{claim_id}/reportable",
    response_model=ClaimResponse,
)
async def update_claim_reportable(
    claim_id: int,
    body: UpdateReportableRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Mark or unmark a claim as reportable with validation."""
    claim = await _load_claim(db, claim_id)
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    try:
        validate_reportable(claim, body.is_reportable)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=e.message,
        )

    claim.is_reportable = body.is_reportable
    await db.commit()
    await db.refresh(claim)
    return claim


# ---------------------------------------------------------------------------
# Evidence Cards
# ---------------------------------------------------------------------------


@router.get(
    "/evidence-maps/{map_id}/cards",
    response_model=list[EvidenceCardResponse],
)
async def get_evidence_cards(
    map_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get Evidence Cards for all claims in an Evidence Map."""
    emap = await _load_evidence_map(db, map_id)
    if emap is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence map not found")

    cards = []
    for claim in emap.claims:
        actions = _build_card_actions(claim)
        cards.append(EvidenceCardResponse(
            claim_id=claim.id,
            claim_text=claim.claim_text,
            status=claim.status,
            key_facts=claim.key_facts,
            evidence_refs=claim.evidence_refs,
            is_reportable=claim.is_reportable,
            actions=actions,
        ))
    return cards
