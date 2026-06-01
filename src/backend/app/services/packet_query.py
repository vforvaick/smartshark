"""Packet Query Engine — stub implementation.

The real engine will wrap tshark/sharkd. For now, we validate based on
file magic numbers and return deterministic fixture packet data.
"""

from dataclasses import dataclass

from app.models.capture import DiagnosticCategory


# --- Validation types ---

@dataclass
class ValidationResult:
    valid: bool
    category: DiagnosticCategory | None = None
    detail: str | None = None
    suggested_next_step: str | None = None


@dataclass
class PacketSummaryData:
    frame_number: int
    timestamp: str
    source: str
    destination: str
    protocol: str
    length: int
    info: str


@dataclass
class LayerFieldData:
    name: str
    value: str


@dataclass
class FrameDetailData:
    frame_number: int
    timestamp: str
    protocols: list[str]
    layers: list[LayerFieldData]


@dataclass
class PayloadData:
    hex_dump: str
    ascii: str
    length: int


@dataclass
class FilterValidationResult:
    valid: bool
    error: str | None = None


@dataclass
class IndexData:
    protocol_mix: dict[str, int]
    top_endpoints: list[dict[str, str | int]]
    conversations_count: int
    time_range_start: str
    time_range_end: str
    total_packets: int
    total_bytes: int


@dataclass
class TimelineBucketData:
    timestamp: str
    packets_per_sec: int
    bytes_per_sec: int
    tcp_retransmissions: int = 0
    tcp_resets: int = 0
    dns_queries: int = 0
    dns_responses: int = 0
    dns_timeouts: int = 0


@dataclass
class ConversationData:
    id: int
    src_addr: str
    src_port: int
    dst_addr: str
    dst_port: int
    protocol: str
    packet_count: int
    byte_count: int


@dataclass
class StreamSegmentData:
    direction: str  # "client_to_server" or "server_to_client"
    data: str
    frame_numbers: list[int]


SUPPORTED_STREAM_TYPES = {"tcp", "udp"}


# --- Graph data types ---

@dataclass
class GraphNodeData:
    id: str  # IP address used as node ID
    ip_address: str
    label: str


@dataclass
class GraphEdgeData:
    id: int
    source_node: str
    target_node: str
    protocol: str
    packet_count: int
    byte_count: int
    error_count: int
    conversation_id: int


@dataclass
class ConversationGraphData:
    nodes: list[GraphNodeData]
    edges: list[GraphEdgeData]
    artifact_id: int | None = None


# --- Known capture format magic bytes ---

PCAP_MAGIC_LE = b"\xd4\xc3\xb2\xa1"
PCAP_MAGIC_BE = b"\xa1\xb2\xc3\xd4"
PCAPNG_MAGIC = b"\x0a\x0d\x0d\x0a"

MAX_CAPTURE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB


# --- Fixture packets (deterministic stub data) ---

_STUB_PACKETS = [
    PacketSummaryData(
        frame_number=1,
        timestamp="0.000000",
        source="192.168.1.1",
        destination="192.168.1.2",
        protocol="TCP",
        length=66,
        info="49152 → 80 [SYN] Seq=0 Win=65535 Len=0 MSS=1460",
    ),
    PacketSummaryData(
        frame_number=2,
        timestamp="0.000150",
        source="192.168.1.2",
        destination="192.168.1.1",
        protocol="TCP",
        length=66,
        info="80 → 49152 [SYN, ACK] Seq=0 Ack=1 Win=65535 Len=0 MSS=1460",
    ),
    PacketSummaryData(
        frame_number=3,
        timestamp="0.000300",
        source="192.168.1.1",
        destination="192.168.1.2",
        protocol="TCP",
        length=54,
        info="49152 → 80 [ACK] Seq=1 Ack=1 Win=65535 Len=0",
    ),
    PacketSummaryData(
        frame_number=4,
        timestamp="0.000500",
        source="192.168.1.1",
        destination="192.168.1.2",
        protocol="HTTP",
        length=400,
        info="GET /index.html HTTP/1.1",
    ),
    PacketSummaryData(
        frame_number=5,
        timestamp="0.001000",
        source="192.168.1.2",
        destination="8.8.8.8",
        protocol="DNS",
        length=72,
        info="Standard query 0x0001 A example.com",
    ),
    PacketSummaryData(
        frame_number=6,
        timestamp="0.002000",
        source="8.8.8.8",
        destination="192.168.1.2",
        protocol="DNS",
        length=88,
        info="Standard query response 0x0001 A 93.184.216.34",
    ),
]

_STUB_FRAME_DETAILS = {
    1: FrameDetailData(
        frame_number=1,
        timestamp="0.000000",
        protocols=["eth", "ip", "tcp"],
        layers=[
            LayerFieldData(name="eth.src", value="00:11:22:33:44:55"),
            LayerFieldData(name="eth.dst", value="66:77:88:99:aa:bb"),
            LayerFieldData(name="ip.src", value="192.168.1.1"),
            LayerFieldData(name="ip.dst", value="192.168.1.2"),
            LayerFieldData(name="tcp.srcport", value="49152"),
            LayerFieldData(name="tcp.dstport", value="80"),
            LayerFieldData(name="tcp.flags", value="0x0002 [SYN]"),
        ],
    ),
    2: FrameDetailData(
        frame_number=2,
        timestamp="0.000150",
        protocols=["eth", "ip", "tcp"],
        layers=[
            LayerFieldData(name="eth.src", value="66:77:88:99:aa:bb"),
            LayerFieldData(name="eth.dst", value="00:11:22:33:44:55"),
            LayerFieldData(name="ip.src", value="192.168.1.2"),
            LayerFieldData(name="ip.dst", value="192.168.1.1"),
            LayerFieldData(name="tcp.srcport", value="80"),
            LayerFieldData(name="tcp.dstport", value="49152"),
            LayerFieldData(name="tcp.flags", value="0x0012 [SYN, ACK]"),
        ],
    ),
    3: FrameDetailData(
        frame_number=3,
        timestamp="0.000300",
        protocols=["eth", "ip", "tcp"],
        layers=[
            LayerFieldData(name="eth.src", value="00:11:22:33:44:55"),
            LayerFieldData(name="eth.dst", value="66:77:88:99:aa:bb"),
            LayerFieldData(name="ip.src", value="192.168.1.1"),
            LayerFieldData(name="ip.dst", value="192.168.1.2"),
            LayerFieldData(name="tcp.srcport", value="49152"),
            LayerFieldData(name="tcp.dstport", value="80"),
            LayerFieldData(name="tcp.flags", value="0x0010 [ACK]"),
        ],
    ),
    4: FrameDetailData(
        frame_number=4,
        timestamp="0.000500",
        protocols=["eth", "ip", "tcp", "http"],
        layers=[
            LayerFieldData(name="eth.src", value="00:11:22:33:44:55"),
            LayerFieldData(name="eth.dst", value="66:77:88:99:aa:bb"),
            LayerFieldData(name="ip.src", value="192.168.1.1"),
            LayerFieldData(name="ip.dst", value="192.168.1.2"),
            LayerFieldData(name="tcp.srcport", value="49152"),
            LayerFieldData(name="tcp.dstport", value="80"),
            LayerFieldData(name="http.request.method", value="GET"),
            LayerFieldData(name="http.request.uri", value="/index.html"),
            LayerFieldData(name="http.host", value="192.168.1.2"),
        ],
    ),
    5: FrameDetailData(
        frame_number=5,
        timestamp="0.001000",
        protocols=["eth", "ip", "udp", "dns"],
        layers=[
            LayerFieldData(name="eth.src", value="66:77:88:99:aa:bb"),
            LayerFieldData(name="eth.dst", value="cc:dd:ee:ff:00:11"),
            LayerFieldData(name="ip.src", value="192.168.1.2"),
            LayerFieldData(name="ip.dst", value="8.8.8.8"),
            LayerFieldData(name="dns.qry.name", value="example.com"),
            LayerFieldData(name="dns.qry.type", value="A"),
        ],
    ),
    6: FrameDetailData(
        frame_number=6,
        timestamp="0.002000",
        protocols=["eth", "ip", "udp", "dns"],
        layers=[
            LayerFieldData(name="eth.src", value="cc:dd:ee:ff:00:11"),
            LayerFieldData(name="eth.dst", value="66:77:88:99:aa:bb"),
            LayerFieldData(name="ip.src", value="8.8.8.8"),
            LayerFieldData(name="ip.dst", value="192.168.1.2"),
            LayerFieldData(name="dns.qry.name", value="example.com"),
            LayerFieldData(name="dns.a", value="93.184.216.34"),
        ],
    ),
}

_STUB_PAYLOADS = {
    1: PayloadData(hex_dump="0000  00 11 22 33 44 55 66 77  88 99 aa bb 08 00 45 00", ascii='.."3DUfw....E.', length=16),
    2: PayloadData(hex_dump="0000  66 77 88 99 aa bb 00 11  22 33 44 55 08 00 45 00", ascii='fw....."3DU..E.', length=16),
    3: PayloadData(hex_dump="0000  00 11 22 33 44 55 66 77  88 99 aa bb 08 00 45 00", ascii='.."3DUfw....E.', length=16),
    4: PayloadData(
        hex_dump="0000  47 45 54 20 2f 69 6e 64  65 78 2e 68 74 6d 6c 20  GET /index.html \n0010  48 54 54 50 2f 31 2e 31  0d 0a 48 6f 73 74 3a 20  HTTP/1.1..Host: ",
        ascii="GET /index.html HTTP/1.1\r\nHost: ",
        length=32,
    ),
    5: PayloadData(hex_dump="0000  cc:dd:ee:ff:00:11 66:77  88:99:aa:bb", ascii="......fw....", length=12),
    6: PayloadData(hex_dump="0000  66:77:88:99:aa:bb cc:dd  ee:ff:00:11", ascii="fw..........", length=12),
}

# Known invalid filter patterns (stubs a tshark-style syntax check)
_INVALID_FILTER_PATTERNS = ["((((invalid", "))))", "((())", "((((((((("]

# --- Fixture conversations (deterministic stub data) ---

_STUB_CONVERSATIONS = [
    ConversationData(
        id=0,
        src_addr="192.168.1.1",
        src_port=49152,
        dst_addr="192.168.1.2",
        dst_port=80,
        protocol="TCP",
        packet_count=4,
        byte_count=586,
    ),
    ConversationData(
        id=1,
        src_addr="192.168.1.2",
        src_port=0,
        dst_addr="8.8.8.8",
        dst_port=0,
        protocol="UDP",
        packet_count=2,
        byte_count=160,
    ),
]

# Conversation 0 (TCP: 192.168.1.1:49152 <-> 192.168.1.2:80) uses frames 1-4
# Conversation 1 (UDP: 192.168.1.2 <-> 8.8.8.8) uses frames 5-6
_CONVERSATION_PACKETS = {
    0: [1, 2, 3, 4],
    1: [5, 6],
}

_STUB_STREAMS = {
    ("tcp", 0): [
        StreamSegmentData(
            direction="client_to_server",
            data="GET /index.html HTTP/1.1\r\nHost: 192.168.1.2\r\n\r\n",
            frame_numbers=[1, 3, 4],
        ),
        StreamSegmentData(
            direction="server_to_client",
            data="HTTP/1.1 200 OK\r\nContent-Length: 1270\r\n\r\n<html>",
            frame_numbers=[2],
        ),
    ],
    ("udp", 0): [
        StreamSegmentData(
            direction="client_to_server",
            data="\x00\x00Standard query A example.com",
            frame_numbers=[5],
        ),
        StreamSegmentData(
            direction="server_to_client",
            data="\x00\x00Standard query response A 93.184.216.34",
            frame_numbers=[6],
        ),
    ],
}


# --- Validation (existing, unchanged) ---

def validate_capture(content: bytes, filename: str) -> ValidationResult:
    """Validate capture file content. Returns a ValidationResult."""
    if len(content) > MAX_CAPTURE_SIZE_BYTES:
        return ValidationResult(
            valid=False,
            category=DiagnosticCategory.too_large,
            detail=f"File is {len(content)} bytes, maximum is {MAX_CAPTURE_SIZE_BYTES} bytes",
            suggested_next_step="Use a smaller capture or filter the capture before importing.",
        )

    if len(content) < 4:
        return ValidationResult(
            valid=False,
            category=DiagnosticCategory.invalid_format,
            detail="File is too small to be a valid capture.",
            suggested_next_step="Verify the file is a PCAP or PCAPNG capture.",
        )

    magic = content[:4]

    if magic == PCAPNG_MAGIC:
        return _validate_pcapng(content, filename)

    if magic in (PCAP_MAGIC_LE, PCAP_MAGIC_BE):
        return _validate_pcap(content, filename)

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in ("pcap", "pcapng", "cap"):
        return ValidationResult(
            valid=False,
            category=DiagnosticCategory.corrupt_capture,
            detail="File extension suggests a capture format but the file header is invalid.",
            suggested_next_step="Re-export or re-capture the file in PCAP or PCAPNG format.",
        )

    return ValidationResult(
        valid=False,
        category=DiagnosticCategory.unsupported_format,
        detail="File format not recognized as a capture file.",
        suggested_next_step="Upload a PCAP or PCAPNG file.",
    )


def _validate_pcap(content: bytes, filename: str) -> ValidationResult:
    if len(content) < 24:
        return ValidationResult(
            valid=False,
            category=DiagnosticCategory.corrupt_capture,
            detail="PCAP global header is incomplete.",
            suggested_next_step="The file may be truncated. Re-capture or re-export it.",
        )
    return ValidationResult(valid=True)


def _validate_pcapng(content: bytes, filename: str) -> ValidationResult:
    if len(content) < 12:
        return ValidationResult(
            valid=False,
            category=DiagnosticCategory.corrupt_capture,
            detail="PCAPNG section header block is incomplete.",
            suggested_next_step="The file may be truncated. Re-capture or re-export it.",
        )
    return ValidationResult(valid=True)


# --- Packet query methods (stub) ---

def list_packets(
    capture_path: str,
    display_filter: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[PacketSummaryData], FilterValidationResult | None]:
    """List packets from a capture. Returns (packets, filter_error).

    For the stub, returns deterministic fixture data. Supports simple
    protocol-based filtering (case-insensitive substring match).
    """
    if display_filter:
        filter_result = validate_display_filter(display_filter)
        if not filter_result.valid:
            return [], filter_result
        # Simple stub: filter by protocol substring match
        filtered = [
            p for p in _STUB_PACKETS
            if display_filter.lower() in p.protocol.lower()
        ]
        return filtered[offset:offset + limit], None

    return _STUB_PACKETS[offset:offset + limit], None


def get_frame_detail(capture_path: str, frame_number: int) -> FrameDetailData | None:
    """Get frame detail for a specific frame number. Returns None if not found."""
    return _STUB_FRAME_DETAILS.get(frame_number)


def get_payload_preview(capture_path: str, frame_number: int) -> PayloadData | None:
    """Get payload preview (hex + ASCII) for a frame. Returns None if not found."""
    return _STUB_PAYLOADS.get(frame_number)


def validate_display_filter(filter_text: str) -> FilterValidationResult:
    """Validate a display filter string. Returns validation result with error detail."""
    if not filter_text or not filter_text.strip():
        return FilterValidationResult(valid=True)

    # Check for obviously malformed filters (unbalanced parens)
    depth = 0
    for ch in filter_text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if depth < 0:
            return FilterValidationResult(
                valid=False,
                error=f"Unbalanced display filter: unexpected ')' in \"{filter_text}\"",
            )
    if depth != 0:
        return FilterValidationResult(
            valid=False,
            error=f"Unbalanced display filter: missing ')' in \"{filter_text}\"",
        )

    return FilterValidationResult(valid=True)


# --- Conversation / stream query methods (stub) ---

def list_conversations(capture_path: str) -> list[ConversationData]:
    """List conversations (flows) for a capture. Returns deterministic fixture data."""
    return list(_STUB_CONVERSATIONS)


def get_conversation_packets(
    capture_path: str, conversation_id: int
) -> list[PacketSummaryData] | None:
    """Get packet subset for a conversation. Returns None if conversation not found."""
    frame_numbers = _CONVERSATION_PACKETS.get(conversation_id)
    if frame_numbers is None:
        return None
    return [p for p in _STUB_PACKETS if p.frame_number in frame_numbers]


def follow_stream(
    capture_path: str, stream_index: int, stream_type: str
) -> tuple[list[StreamSegmentData] | None, str | None]:
    """Follow a stream. Returns (segments, error_message).

    Returns (None, error) if stream type is unsupported or stream not found.
    Returns (segments, None) on success.
    """
    if stream_type not in SUPPORTED_STREAM_TYPES:
        return None, f"Unsupported stream type: {stream_type}. Supported types: {', '.join(sorted(SUPPORTED_STREAM_TYPES))}"

    segments = _STUB_STREAMS.get((stream_type, stream_index))
    if segments is None:
        return None, f"Stream {stream_index} of type {stream_type} not found"

    return segments, None


# --- Capture Index / Timeline stubs ---

def build_capture_index(capture_path: str) -> IndexData:
    """Build a Capture Index from a capture file.

    Stub returns deterministic data derived from the fixture packets.
    """
    protocol_counts: dict[str, int] = {}
    endpoint_counts: dict[str, int] = {}
    total_bytes = 0

    for pkt in _STUB_PACKETS:
        protocol_counts[pkt.protocol] = protocol_counts.get(pkt.protocol, 0) + 1
        endpoint_counts[pkt.source] = endpoint_counts.get(pkt.source, 0) + 1
        endpoint_counts[pkt.destination] = endpoint_counts.get(pkt.destination, 0) + 1
        total_bytes += pkt.length

    # Build top endpoints sorted by count
    top_endpoints = [
        {"address": addr, "packet_count": count}
        for addr, count in sorted(endpoint_counts.items(), key=lambda x: -x[1])
    ]

    # Conversations: unique src-dst pairs
    conversations = set()
    for pkt in _STUB_PACKETS:
        conversations.add((pkt.source, pkt.destination))

    return IndexData(
        protocol_mix=protocol_counts,
        top_endpoints=top_endpoints,
        conversations_count=len(conversations),
        time_range_start=_STUB_PACKETS[0].timestamp,
        time_range_end=_STUB_PACKETS[-1].timestamp,
        total_packets=len(_STUB_PACKETS),
        total_bytes=total_bytes,
    )


def compute_timeline(capture_path: str, bucket_seconds: int = 1) -> list[TimelineBucketData]:
    """Compute timeline metrics from a capture file.

    Stub returns deterministic timeline data with TCP retransmissions,
    TCP resets, and DNS activity.
    """
    # All stub packets fit in one bucket (timestamps 0.0 - 0.002)
    total_bytes = sum(p.length for p in _STUB_PACKETS)
    return [
        TimelineBucketData(
            timestamp="0.000000",
            packets_per_sec=len(_STUB_PACKETS),
            bytes_per_sec=total_bytes,
            tcp_retransmissions=1,
            tcp_resets=1,
            dns_queries=1,
            dns_responses=1,
            dns_timeouts=0,
        ),
    ]


# --- Conversation Graph stub ---

def build_conversation_graph(capture_path: str) -> ConversationGraphData:
    """Build a Conversation Graph from a capture file.

    Nodes are unique endpoints; edges are conversations with
    packet/byte/error volume as weight.
    Stub returns deterministic data derived from fixture conversations.
    """
    # Collect unique endpoints from conversations
    endpoint_set: set[str] = set()
    for conv in _STUB_CONVERSATIONS:
        endpoint_set.add(conv.src_addr)
        endpoint_set.add(conv.dst_addr)

    nodes = [
        GraphNodeData(id=addr, ip_address=addr, label=addr)
        for addr in sorted(endpoint_set)
    ]

    edges = []
    for conv in _STUB_CONVERSATIONS:
        # TCP conversations may have retransmission errors
        error_count = 1 if conv.protocol == "TCP" else 0
        edges.append(
            GraphEdgeData(
                id=conv.id,
                source_node=conv.src_addr,
                target_node=conv.dst_addr,
                protocol=conv.protocol,
                packet_count=conv.packet_count,
                byte_count=conv.byte_count,
                error_count=error_count,
                conversation_id=conv.id,
            )
        )

    return ConversationGraphData(nodes=nodes, edges=edges)
