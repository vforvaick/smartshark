"""Capture Indexer service — builds and retrieves capture indexes and timeline data."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capture_index import CaptureIndex, TimelineBucket
from app.models.capture import CaptureArtifact
from app.schemas.capture_index import PreScanSummary
from app.services.packet_query import build_capture_index, compute_timeline


async def create_index(db: AsyncSession, artifact_id: int) -> CaptureIndex | None:
    """Build a Capture Index for an artifact. Returns None if artifact not found."""
    # Check artifact exists
    result = await db.execute(
        select(CaptureArtifact).where(CaptureArtifact.id == artifact_id)
    )
    artifact = result.scalar_one_or_none()
    if artifact is None:
        return None

    # Check if index already exists
    existing = await db.execute(
        select(CaptureIndex).where(CaptureIndex.artifact_id == artifact_id)
    )
    if existing.scalar_one_or_none() is not None:
        # Return existing index (idempotent)
        result = await db.execute(
            select(CaptureIndex).where(CaptureIndex.artifact_id == artifact_id)
        )
        return result.scalar_one()

    # Build index from packet query engine
    index_data = build_capture_index(artifact.file_path)

    capture_index = CaptureIndex(
        artifact_id=artifact_id,
        protocol_mix=index_data.protocol_mix,
        top_endpoints=index_data.top_endpoints,
        conversations_count=index_data.conversations_count,
        time_range_start=index_data.time_range_start,
        time_range_end=index_data.time_range_end,
        total_packets=index_data.total_packets,
        total_bytes=index_data.total_bytes,
    )
    db.add(capture_index)
    await db.flush()

    # Build timeline
    timeline_data = compute_timeline(artifact.file_path)
    for bucket in timeline_data:
        tb = TimelineBucket(
            capture_index_id=capture_index.id,
            timestamp=bucket.timestamp,
            packets_per_sec=bucket.packets_per_sec,
            bytes_per_sec=bucket.bytes_per_sec,
            tcp_retransmissions=bucket.tcp_retransmissions,
            tcp_resets=bucket.tcp_resets,
            dns_queries=bucket.dns_queries,
            dns_responses=bucket.dns_responses,
            dns_timeouts=bucket.dns_timeouts,
        )
        db.add(tb)

    await db.commit()
    await db.refresh(capture_index)
    return capture_index


async def get_index(db: AsyncSession, artifact_id: int) -> CaptureIndex | None:
    """Retrieve an existing Capture Index. Returns None if not found."""
    result = await db.execute(
        select(CaptureIndex).where(CaptureIndex.artifact_id == artifact_id)
    )
    return result.scalar_one_or_none()


async def get_timeline(db: AsyncSession, artifact_id: int) -> list[TimelineBucket] | None:
    """Retrieve timeline buckets for an artifact. Returns None if no index exists."""
    index = await get_index(db, artifact_id)
    if index is None:
        return None
    result = await db.execute(
        select(TimelineBucket)
        .where(TimelineBucket.capture_index_id == index.id)
        .order_by(TimelineBucket.timestamp)
    )
    return list(result.scalars().all())


async def get_prescan(db: AsyncSession, artifact_id: int) -> PreScanSummary | None:
    """Return Pre-Scan summary for an artifact. Returns None if no index exists."""
    index = await get_index(db, artifact_id)
    if index is None:
        return None

    # Build human-readable summary
    top_protocols = ", ".join(
        f"{proto} ({count})" for proto, count in
        sorted(index.protocol_mix.items(), key=lambda x: -x[1])
    )
    top_ips = [e["address"] for e in index.top_endpoints[:3]]

    summary = (
        f"{index.total_packets} packets, {index.total_bytes} bytes. "
        f"Protocols: {top_protocols}. "
        f"Top endpoints: {', '.join(top_ips)}. "
        f"{index.conversations_count} conversations. "
        f"Time range: {index.time_range_start} - {index.time_range_end}."
    )

    return PreScanSummary(
        protocol_mix=index.protocol_mix,
        top_endpoints=index.top_endpoints,
        conversations_count=index.conversations_count,
        time_range_start=index.time_range_start,
        time_range_end=index.time_range_end,
        total_packets=index.total_packets,
        total_bytes=index.total_bytes,
        summary=summary,
    )
