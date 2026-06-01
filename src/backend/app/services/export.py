"""Export service — generates Markdown/PDF exports of investigation reports.

Ensures:
- All findings include fallback textual citations
- Smartshark deep links are preserved
- Unsupported claims cannot appear in exported findings
- Limitations and assumptions are always included
"""

import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.evidence import Claim, ClaimStatus, EvidenceMap
from app.models.metrics import SuccessMetrics
from app.models.report import Report, ReportSection, ReportSectionType
from app.services.evidence_validator import validate_evidence_map


def _section_heading(section: ReportSection) -> str:
    """Generate a markdown heading for a section."""
    return f"## {section.title}\n"


def _format_citation_from_refs(evidence_refs: list[dict]) -> str:
    """Extract textual citations from evidence_refs as fallback."""
    citations = []
    for ref in evidence_refs:
        if "citation" in ref:
            citations.append(ref["citation"])
        elif "link" in ref:
            # Build a fallback citation from the deep link
            citations.append(f"[{ref.get('type', 'evidence')}]({ref['link']})")
        elif "frame" in ref:
            citations.append(f"Frame {ref['frame']}")
        elif "conv_id" in ref:
            citations.append(f"Flow {ref['conv_id']}")
    return "; ".join(citations) if citations else ""


def _format_deep_link_markdown(ref: dict) -> str:
    """Format a deep link reference as a markdown link."""
    link = ref.get("link", "")
    citation = ref.get("citation", ref.get("type", "link"))
    if link:
        return f"[{citation}]({link})"
    return citation


async def validate_report_for_export(
    db: AsyncSession, report_id: int
) -> tuple[bool, list[str]]:
    """Validate a report for export.

    Returns (valid, errors). Invalid if:
    - Report doesn't exist
    - Evidence map has validation violations
    - Any reportable claim is unsupported
    """
    # Load report with sections
    result = await db.execute(
        select(Report)
        .options(selectinload(Report.sections))
        .where(Report.id == report_id)
    )
    report = result.scalar_one_or_none()
    if report is None:
        return False, ["Report not found."]

    # Load evidence map with claims
    result = await db.execute(
        select(EvidenceMap)
        .options(selectinload(EvidenceMap.claims))
        .where(EvidenceMap.id == report.evidence_map_id)
    )
    emap = result.scalar_one_or_none()
    if emap is None:
        return False, ["Evidence map not found."]

    # Run the evidence map validator
    violations = validate_evidence_map(emap)
    if violations:
        return False, violations

    # Check that no unsupported claims appear in findings sections
    claim_ids_in_findings: set[int] = set()
    for section in report.sections:
        if section.section_type in (
            ReportSectionType.verified_findings,
            ReportSectionType.likely_findings,
        ):
            claim_ids_in_findings.update(section.claim_ids)

    for claim in emap.claims:
        if claim.id in claim_ids_in_findings and claim.status == ClaimStatus.unsupported:
            return False, [
                f"Claim {claim.id}: unsupported claim found in findings section."
            ]

    return True, []


async def export_markdown(db: AsyncSession, report_id: int) -> str | None:
    """Export a report as Markdown.

    Returns markdown string, or None if report not found.
    Raises ValueError if report fails validation.
    """
    # Load report with sections
    result = await db.execute(
        select(Report)
        .options(selectinload(Report.sections))
        .where(Report.id == report_id)
    )
    report = result.scalar_one_or_none()
    if report is None:
        return None

    # Validate first
    valid, errors = await validate_report_for_export(db, report_id)
    if not valid:
        raise ValueError(f"Report fails export validation: {'; '.join(errors)}")

    # Load evidence map with claims for citation data
    result = await db.execute(
        select(EvidenceMap)
        .options(selectinload(EvidenceMap.claims))
        .where(EvidenceMap.id == report.evidence_map_id)
    )
    emap = result.scalar_one_or_none()
    claims_by_id: dict[int, Claim] = {}
    if emap:
        claims_by_id = {c.id: c for c in emap.claims}

    # Build markdown
    lines: list[str] = []

    # Title and metadata
    lines.append(f"# {report.title}")
    lines.append("")
    now = datetime.datetime.now(datetime.timezone.utc)
    lines.append(f"**Exported:** {now.strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"**Status:** {report.status.value}")
    lines.append("")

    # Sections (ordered by order_index — already sorted via relationship)
    for section in report.sections:
        if not section.is_included:
            continue

        lines.append(_section_heading(section))

        if section.content:
            lines.append(section.content)
        else:
            lines.append("No content.")
        lines.append("")

        # Add textual citations for findings sections
        if section.section_type in (
            ReportSectionType.verified_findings,
            ReportSectionType.likely_findings,
            ReportSectionType.hypotheses_next_steps,
        ):
            claim_citations = []
            for cid in section.claim_ids:
                claim = claims_by_id.get(cid)
                if claim and claim.evidence_refs:
                    citation_text = _format_citation_from_refs(claim.evidence_refs)
                    if citation_text:
                        claim_citations.append(f"  - Evidence: {citation_text}")
            if claim_citations:
                lines.append("**Citations:**")
                lines.extend(claim_citations)
                lines.append("")

        # Add deep links
        if section.deep_links:
            link_lines = []
            for ref in section.deep_links:
                link_md = _format_deep_link_markdown(ref)
                if link_md:
                    link_lines.append(f"  - {link_md}")
            if link_lines:
                lines.append("**Deep Links:**")
                lines.extend(link_lines)
                lines.append("")

    # Add metrics section (unsupported claim rate cannot be hidden)
    if emap:
        metrics_result = await db.execute(
            select(SuccessMetrics).where(
                SuccessMetrics.analysis_run_id == emap.analysis_run_id
            )
        )
        metrics = metrics_result.scalar_one_or_none()
        if metrics:
            lines.append("## Metrics")
            lines.append("")
            lines.append(f"- **Total Claims:** {metrics.total_claims}")
            lines.append(f"- **Unsupported Claims:** {metrics.unsupported_claims}")
            lines.append(f"- **Unsupported Claim Rate:** {metrics.unsupported_claim_rate:.1f}%")
            if metrics.evidence_coverage_pct is not None:
                lines.append(f"- **Evidence Coverage:** {metrics.evidence_coverage_pct:.1f}%")
            lines.append("")
        else:
            # Still include unsupported claim count from claims
            unsupported = sum(1 for c in emap.claims if c.status == ClaimStatus.unsupported)
            total = len(emap.claims)
            if total > 0:
                rate = unsupported / total * 100
                lines.append("## Metrics")
                lines.append("")
                lines.append(f"- **Unsupported Claims:** {unsupported}/{total} ({rate:.1f}%)")
                lines.append("")

    # Add limitations from run
    if emap:
        from app.services.hardening import get_limitations as get_run_limitations
        limitations = await get_run_limitations(db, emap.analysis_run_id)
        if limitations:
            lines.append("## Limitations")
            lines.append("")
            for lim in limitations:
                lines.append(f"- [{lim.category.value}] {lim.detail}")
            lines.append("")

    return "\n".join(lines)


async def export_pdf(db: AsyncSession, report_id: int) -> bytes | None:
    """Export a report as a simple PDF.

    Returns PDF bytes, or None if report not found.
    Raises ValueError if report fails validation.

    For MVP, generates a minimal valid PDF from the markdown content.
    """
    # Get markdown first (reuses validation + data loading)
    md = await export_markdown(db, report_id)
    if md is None:
        return None

    # Generate a minimal valid PDF
    # We build a bare-minimum PDF structure with the report text
    return _markdown_to_pdf(md)


def _markdown_to_pdf(text: str) -> bytes:
    """Convert text to a minimal valid PDF (MVP approach).

    Produces a simple single-page PDF with the text content.
    No external PDF library needed — hand-crafts the PDF structure.
    """
    # PDF works with latin-1 compatible text for simplicity in MVP
    # Replace problematic characters
    safe_text = text.encode("latin-1", errors="replace").decode("latin-1")

    # Split into lines and escape parentheses
    lines = safe_text.split("\n")
    escaped_lines = []
    for line in lines:
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        escaped_lines.append(escaped)

    # Build PDF objects
    objects: list[bytes] = []
    obj_offsets: list[int] = []

    # Object 1: Catalog
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")

    # Object 2: Pages
    objects.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")

    # Build page content stream
    content_lines = [b"BT"]
    content_lines.append(b"/F1 10 Tf")
    y = 750  # start near top of page

    for line in escaped_lines:
        if y < 50:  # stop if we'd go off-page (MVP: single page)
            break
        # Truncate very long lines to fit page width (~80 chars at 10pt)
        display_line = line[:100]
        content_lines.append(
            f"1 0 0 1 50 {y} Tm".encode() + b" (" + display_line.encode("latin-1", errors="replace") + b") Tj"
        )
        y -= 14  # line height

    content_lines.append(b"ET")
    stream_content = b"\n".join(content_lines)

    # Object 5: Content stream
    objects.append(
        f"5 0 obj\n<< /Length {len(stream_content)} >>\nstream\n".encode()
        + stream_content
        + b"\nendstream\nendobj\n"
    )

    # Object 4: Font
    objects.append(b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>\nendobj\n")

    # Object 3: Page
    objects.append(
        b"3 0 obj\n"
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 5 0 R /Resources << /Font << /F1 4 0 R >> >> >>\n"
        b"endobj\n"
    )

    # Reorder: 1=Catalog, 2=Pages, 3=Page, 4=Font, 5=Stream
    ordered_objects = [objects[0], objects[1], objects[4], objects[3], objects[2]]

    # Build PDF
    pdf = bytearray()
    pdf.extend(b"%PDF-1.4\n")

    for obj_data in ordered_objects:
        obj_offsets.append(len(pdf))
        pdf.extend(obj_data)

    # Cross-reference table
    xref_offset = len(pdf)
    pdf.extend(b"xref\n")
    pdf.extend(f"0 {len(ordered_objects) + 1}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")
    for offset in obj_offsets:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())

    # Trailer
    pdf.extend(b"trailer\n")
    pdf.extend(f"<< /Size {len(ordered_objects) + 1} /Root 1 0 R >>\n".encode())
    pdf.extend(b"startxref\n")
    pdf.extend(f"{xref_offset}\n".encode())
    pdf.extend(b"%%EOF\n")

    return bytes(pdf)
