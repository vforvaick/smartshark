from pydantic import BaseModel


class ConversationSummary(BaseModel):
    id: int
    src_addr: str
    src_port: int
    dst_addr: str
    dst_port: int
    protocol: str
    packet_count: int
    byte_count: int


class StreamSegment(BaseModel):
    direction: str  # "client_to_server" or "server_to_client"
    data: str
    frame_numbers: list[int]


class FollowStreamRequest(BaseModel):
    stream_index: int
    stream_type: str  # "tcp", "udp"


class FollowStreamResponse(BaseModel):
    stream_type: str
    stream_index: int
    segments: list[StreamSegment]
