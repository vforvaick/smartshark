from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.evidence_link import EvidenceLink
from app.models.user import User
from app.schemas.evidence_link import (
    CreateEvidenceLinkRequest,
    EvidenceLinkResponse,
    EvidenceLinkResolution,
    BatchResolveRequest,
    BatchResolveResponse,
)
from app.services.deep_link import generate_citation, resolve_evidence_link

router = APIRouter(prefix="/api/evidence-links", tags=["evidence-links"])


@router.post("", response_model=EvidenceLinkResponse, status_code=status.HTTP_201_CREATED)
async def create_evidence_link(
    body: CreateEvidenceLinkRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Create a new Evidence Link."""
    link = EvidenceLink(
        target_type=body.target_type,
        artifact_id=body.artifact_id,
        target_params=body.target_params,
        citation_text=None,  # generated below
    )
    link.citation_text = generate_citation(link)
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link


@router.get("/{link_id}", response_model=EvidenceLinkResolution)
async def resolve_link(
    link_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Resolve an Evidence Link — returns target data or unavailability state."""
    result = await db.execute(
        select(EvidenceLink).where(EvidenceLink.id == link_id)
    )
    link = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence link not found")

    resolution_data = await resolve_evidence_link(db, link)
    await db.commit()

    deep_link = f"smartshark://{link.artifact_id or '_'}/{link.target_type.value}/"

    return EvidenceLinkResolution(
        link=link,
        deep_link=deep_link,
        resolved=link.is_available,
        resolution_data=resolution_data,
    )


@router.get("/{link_id}/citation")
async def get_citation(
    link_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get the portable textual citation for an Evidence Link."""
    result = await db.execute(
        select(EvidenceLink).where(EvidenceLink.id == link_id)
    )
    link = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence link not found")

    return {"citation": link.citation_text or generate_citation(link)}


@router.post("/batch-resolve", response_model=BatchResolveResponse)
async def batch_resolve(
    body: BatchResolveRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Resolve multiple Evidence Links at once."""
    resolutions: list[EvidenceLinkResolution] = []

    for link_id in body.link_ids:
        result = await db.execute(
            select(EvidenceLink).where(EvidenceLink.id == link_id)
        )
        link = result.scalar_one_or_none()
        if link is None:
            continue

        resolution_data = await resolve_evidence_link(db, link)
        deep_link = f"smartshark://{link.artifact_id or '_'}/{link.target_type.value}/"

        resolutions.append(EvidenceLinkResolution(
            link=link,
            deep_link=deep_link,
            resolved=link.is_available,
            resolution_data=resolution_data,
        ))

    await db.commit()
    return BatchResolveResponse(resolutions=resolutions)
