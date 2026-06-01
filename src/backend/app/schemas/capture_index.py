from datetime import datetime

from pydantic import BaseModel


class TimelineBucketResponse(BaseModel):
    timestamp: str
    packets_per_sec: int
    bytes_per_sec: int
    tcp_retransmissions: int
    tcp_resets: int
    dns_queries: int
    dns_responses: int
    dns_timeouts: int

    model_config = {"from_attributes": True}


class CaptureIndexResponse(BaseModel):
    id: int
    artifact_id: int
    protocol_mix: dict
    top_endpoints: list[dict]
    conversations_count: int
    time_range_start: str | None
    time_range_end: str | None
    total_packets: int
    total_bytes: int
    created_at: datetime

    model_config = {"from_attributes": True}


class PreScanSummary(BaseModel):
    protocol_mix: dict
    top_endpoints: list[dict]
    conversations_count: int
    time_range_start: str | None
    time_range_end: str | None
    total_packets: int
    total_bytes: int
    summary: str
