"""Report Builder service — drafts reports from Evidence Cards."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.annotation import Annotation, AnnotationTargetType
from app.models.evidence import Claim, ClaimStatus, EvidenceMap
from app.models.report import Report, ReportSection, ReportSectionType, ReportStatus


# Section titles by type
_SECTION_TITLES: dict[ReportSectionType, str] = {
    ReportSectionType.verified_findings: "Verified Findings",
    ReportSectionType.likely_findings: "Likely Findings",
    ReportSectionType.hypotheses_next_steps: "Hypotheses / Next Steps",
    ReportSectionType.limitations_assumptions: "Limitations / Assumptions",
}


def _claim_to_section_type(status: ClaimStatus) -> ReportSectionType | None:
    """Map claim status to the report section type it belongs in."""
    mapping = {
        ClaimStatus.verified: ReportSectionType.verified_findings,
        ClaimStatus.likely: ReportSectionType.likely_findings,
        ClaimStatus.hypothesis: ReportSectionType.hypotheses_next_steps,
    }
    return mapping.get(status)  # unsupported → None (excluded)


async def _get_claim_annotations(
    db: AsyncSession, claim_id: int
) -> list[Annotation]:
    """Get all annotations for a claim."""
    result = await db.execute(
        select(Annotation).where(
            Annotation.target_type == AnnotationTargetType.claim,
            Annotation.target_id == claim_id,
        )
    )
    return list(result.scalars().all())


def _is_claim_excluded(annotations: list[Annotation]) -> bool:
    """Check if a claim should be excluded based on annotations."""
    for ann in annotations:
        if ann.is_false_positive:
            return True
        if not ann.include_in_report:
            return True
    return False


async def draft_report(
    db: AsyncSession,
    evidence_map_id: int,
    author_id: int,
) -> Report:
    """Generate a report draft from eligible evidence cards.

    - Routes claims to sections by status
    - Excludes unsupported claims entirely
    - Excludes claims marked as false positive or include_in_report=False
    - Preserves deep links from evidence_refs
    """
    # Load evidence map with claims
    result = await db.execute(
        select(EvidenceMap)
        .options(selectinload(EvidenceMap.claims))
        .where(EvidenceMap.id == evidence_map_id)
    )
    emap = result.scalar_one_or_none()
    if emap is None:
        return None  # caller handles 404

    # Group claims by section type, filtering excluded ones
    section_claims: dict[ReportSectionType, list[Claim]] = {
        ReportSectionType.verified_findings: [],
        ReportSectionType.likely_findings: [],
        ReportSectionType.hypotheses_next_steps: [],
    }
    section_deep_links: dict[ReportSectionType, list[dict]] = {
        ReportSectionType.verified_findings: [],
        ReportSectionType.likely_findings: [],
        ReportSectionType.hypotheses_next_steps: [],
    }

    for claim in emap.claims:
        # Skip unsupported claims
        if claim.status == ClaimStatus.unsupported:
            continue

        section_type = _claim_to_section_type(claim.status)
        if section_type is None:
            continue

        # Check annotations for exclusion
        annotations = await _get_claim_annotations(db, claim.id)
        if _is_claim_excluded(annotations):
            continue

        section_claims[section_type].append(claim)
        # Collect deep links from evidence_refs
        for ref in claim.evidence_refs:
            if "link" in ref:
                section_deep_links[section_type].append(ref)

    # Build report
    report = Report(
        evidence_map_id=evidence_map_id,
        title="Investigation Report",
        created_by=author_id,
        status=ReportStatus.draft,
    )
    db.add(report)
    await db.flush()  # get report.id

    order = 0
    for section_type in [
        ReportSectionType.verified_findings,
        ReportSectionType.likely_findings,
        ReportSectionType.hypotheses_next_steps,
        ReportSectionType.limitations_assumptions,
    ]:
        claims = section_claims.get(section_type, [])
        deep_links = section_deep_links.get(section_type, [])

        if section_type == ReportSectionType.limitations_assumptions:
            # Always create a limitations section placeholder
            content = "No limitations recorded."
            claim_ids = []
        else:
            if not claims:
                continue  # skip empty sections
            content_lines = []
            claim_ids = []
            for claim in claims:
                content_lines.append(f"• {claim.claim_text}")
                if claim.key_facts:
                    for fact in claim.key_facts:
                        content_lines.append(f"  - {fact}")
                claim_ids.append(claim.id)
            content = "\n".join(content_lines)

        section = ReportSection(
            report_id=report.id,
            section_type=section_type,
            order_index=order,
            title=_SECTION_TITLES[section_type],
            content=content,
            claim_ids=claim_ids,
            is_included=True,
            deep_links=deep_links,
        )
        db.add(section)
        order += 1

    await db.commit()

    # Reload with sections
    result = await db.execute(
        select(Report)
        .options(selectinload(Report.sections))
        .where(Report.id == report.id)
    )
    return result.scalar_one()


async def get_report(db: AsyncSession, report_id: int) -> Report | None:
    """Get a report by ID with all sections."""
    result = await db.execute(
        select(Report)
        .options(selectinload(Report.sections))
        .where(Report.id == report_id)
    )
    return result.scalar_one_or_none()


async def update_section(
    db: AsyncSession,
    section_id: int,
    title: str | None = None,
    content: str | None = None,
    is_included: bool | None = None,
) -> ReportSection | None:
    """Update a report section's title, content, or inclusion."""
    result = await db.execute(
        select(ReportSection).where(ReportSection.id == section_id)
    )
    section = result.scalar_one_or_none()
    if section is None:
        return None

    if title is not None:
        section.title = title
    if content is not None:
        section.content = content
    if is_included is not None:
        section.is_included = is_included

    await db.commit()
    await db.refresh(section)
    return section


async def reorder_sections(
    db: AsyncSession,
    report_id: int,
    items: list[dict],
) -> list[ReportSection] | None:
    """Reorder report sections. items: [{section_id, order_index}]."""
    # Verify report exists
    report = await get_report(db, report_id)
    if report is None:
        return None

    for item in items:
        result = await db.execute(
            select(ReportSection).where(
                ReportSection.id == item["section_id"],
                ReportSection.report_id == report_id,
            )
        )
        section = result.scalar_one_or_none()
        if section is not None:
            section.order_index = item["order_index"]

    await db.commit()

    # Expire cached data and reload with updated sections
    db.expire_all()
    report = await get_report(db, report_id)
    return report.sections
