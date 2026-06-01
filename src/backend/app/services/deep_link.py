"""Deep-link resolver — creates, resolves, and cites Evidence Links."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capture import CaptureArtifact, ArtifactStatus
from app.models.evidence_link import EvidenceLink, TargetType
from app.models.evidence import Claim
from app.models.capture_index import CaptureIndex


def _build_deep_link(link: EvidenceLink) -> str:
    """Build a smartshark:// deep-link URL from an EvidenceLink."""
    artifact_part = str(link.artifact_id) if link.artifact_id else "_"
    target_id = link.target_params.get("frame_number") or link.target_params.get("conv_id") or link.target_params.get("stream_index") or link.target_params.get("claim_id") or link.target_params.get("section_id") or ""
    return f"smartshark://{artifact_part}/{link.target_type.value}/{target_id}"


def generate_citation(link: EvidenceLink) -> str:
    """Generate a portable textual citation for an Evidence Link."""
    params = link.target_params
    artifact = f"artifact {link.artifact_id}" if link.artifact_id else "unknown artifact"

    if link.target_type == TargetType.packets:
        filt = params.get("filter", "no filter")
        return f"Packet subset ({filt}) in {artifact}"
    elif link.target_type == TargetType.frame:
        frame = params.get("frame_number", "?")
        return f"Frame {frame} in {artifact}"
    elif link.target_type == TargetType.flow:
        conv_id = params.get("conv_id", "?")
        return f"Flow {conv_id} in {artifact}"
    elif link.target_type == TargetType.stream:
        stream_idx = params.get("stream_index", "?")
        proto = params.get("protocol", "TCP")
        return f"{proto} stream {stream_idx} in {artifact}"
    elif link.target_type == TargetType.timeline:
        start = params.get("time_start", "?")
        end = params.get("time_end", "?")
        return f"Timeline window {start}–{end} in {artifact}"
    elif link.target_type == TargetType.graph_edge:
        edge_id = params.get("edge_id", "?")
        return f"Graph edge {edge_id} in {artifact}"
    elif link.target_type == TargetType.claim:
        claim_id = params.get("claim_id", "?")
        return f"Claim {claim_id}"
    elif link.target_type == TargetType.report_section:
        section = params.get("section_id", "?")
        return f"Report section {section}"
    return f"Evidence link for {artifact}"


async def check_availability(db: AsyncSession, link: EvidenceLink) -> tuple[bool, str | None]:
    """Check whether the link target is still reachable."""
    if link.artifact_id is not None:
        result = await db.execute(
            select(CaptureArtifact).where(CaptureArtifact.id == link.artifact_id)
        )
        artifact = result.scalar_one_or_none()
        if artifact is None:
            return False, "deleted"
        if artifact.status == ArtifactStatus.archived:
            return False, "archived"

    # For claims, check the claim exists
    if link.target_type == TargetType.claim:
        claim_id = link.target_params.get("claim_id")
        if claim_id is not None:
            result = await db.execute(select(Claim).where(Claim.id == claim_id))
            if result.scalar_one_or_none() is None:
                return False, "deleted"

    # For timeline/graph targets, check capture index exists
    if link.target_type in (TargetType.timeline, TargetType.graph_edge):
        if link.artifact_id is not None:
            result = await db.execute(
                select(CaptureIndex).where(CaptureIndex.artifact_id == link.artifact_id)
            )
            if result.scalar_one_or_none() is None:
                return False, "missing_index"

    return True, None


async def resolve_evidence_link(db: AsyncSession, link: EvidenceLink) -> dict:
    """Resolve an evidence link — return resolution data or unavailability."""
    available, reason = await check_availability(db, link)

    # Update the link's availability fields
    link.is_available = available
    link.unavailability_reason = reason

    resolution_data: dict = {"target_type": link.target_type.value}

    if not available:
        resolution_data["unavailability_reason"] = reason
        return resolution_data

    # Add target-specific resolution data
    if link.target_type == TargetType.packets:
        resolution_data["filter"] = link.target_params.get("filter", "")
    elif link.target_type == TargetType.frame:
        resolution_data["frame_number"] = link.target_params.get("frame_number")
    elif link.target_type == TargetType.flow:
        resolution_data["conv_id"] = link.target_params.get("conv_id")
    elif link.target_type == TargetType.stream:
        resolution_data["stream_index"] = link.target_params.get("stream_index")
        resolution_data["protocol"] = link.target_params.get("protocol", "TCP")
    elif link.target_type == TargetType.timeline:
        resolution_data["time_start"] = link.target_params.get("time_start")
        resolution_data["time_end"] = link.target_params.get("time_end")
    elif link.target_type == TargetType.graph_edge:
        resolution_data["edge_id"] = link.target_params.get("edge_id")
    elif link.target_type == TargetType.claim:
        resolution_data["claim_id"] = link.target_params.get("claim_id")
    elif link.target_type == TargetType.report_section:
        resolution_data["section_id"] = link.target_params.get("section_id")

    return resolution_data
