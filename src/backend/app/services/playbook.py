"""Playbook Engine — runs default generic playbook fan-out for Quick Analysis.

The default triage fan-out runs these checks:
1. TCP Health — retransmissions, resets, zero-window
2. DNS Resolution — response codes, timeouts
3. HTTP/API — error rates, latency
4. TLS Handshake — failures, version issues
5. Path / Visibility — one-sided flows, missing data

Each check uses Capture Index and Timeline data from Issue #5.
"""

from dataclasses import dataclass

from app.models.check_result import CheckResult, CheckStatus
from app.services.packet_query import (
    IndexData,
    TimelineBucketData,
    ConversationData,
    build_capture_index,
    compute_timeline,
    list_conversations,
)


@dataclass
class CheckOutput:
    check_name: str
    status: CheckStatus
    summary: str
    evidence_refs: list[dict]
    limitations: list[str]


def _run_tcp_health_check(
    index_data: IndexData,
    timeline_data: list[TimelineBucketData],
    conversations: list[ConversationData],
) -> CheckOutput:
    """Check TCP Health: retransmissions, resets, zero-window."""
    total_retransmissions = sum(b.tcp_retransmissions for b in timeline_data)
    total_resets = sum(b.tcp_resets for b in timeline_data)
    tcp_packets = index_data.protocol_mix.get("TCP", 0)

    parts = []
    evidence_refs = []
    limitations = []

    if tcp_packets > 0:
        evidence_refs.append({"type": "protocol_mix", "protocol": "TCP", "count": tcp_packets})
        parts.append(f"Found {tcp_packets} TCP packets.")

        if total_retransmissions > 0:
            evidence_refs.append({"type": "timeline_metric", "metric": "tcp_retransmissions", "total": total_retransmissions})
            parts.append(f"Detected {total_retransmissions} TCP retransmission(s).")
        else:
            parts.append("No TCP retransmissions detected.")

        if total_resets > 0:
            evidence_refs.append({"type": "timeline_metric", "metric": "tcp_resets", "total": total_resets})
            parts.append(f"Detected {total_resets} TCP reset(s).")
        else:
            parts.append("No TCP resets detected.")

        # Limitation: no zero-window analysis available from stub data
        limitations.append("Zero-window analysis not available from current index data.")
    else:
        limitations.append("No TCP traffic found in capture. TCP health check may be incomplete.")

    summary = " ".join(parts) if parts else "No TCP traffic to analyze."

    return CheckOutput(
        check_name="tcp_health",
        status=CheckStatus.completed,
        summary=summary,
        evidence_refs=evidence_refs,
        limitations=limitations,
    )


def _run_dns_resolution_check(
    index_data: IndexData,
    timeline_data: list[TimelineBucketData],
    conversations: list[ConversationData],
) -> CheckOutput:
    """Check DNS Resolution: response codes, timeouts."""
    dns_queries = sum(b.dns_queries for b in timeline_data)
    dns_responses = sum(b.dns_responses for b in timeline_data)
    dns_timeouts = sum(b.dns_timeouts for b in timeline_data)
    dns_packets = index_data.protocol_mix.get("DNS", 0)

    parts = []
    evidence_refs = []
    limitations = []

    if dns_packets > 0 or dns_queries > 0:
        evidence_refs.append({"type": "protocol_mix", "protocol": "DNS", "count": dns_packets})
        parts.append(f"Found {dns_packets} DNS packets: {dns_queries} queries, {dns_responses} responses, {dns_timeouts} timeouts.")

        if dns_timeouts > 0:
            limitations.append(f"{dns_timeouts} DNS timeout(s) detected — some queries received no response.")
        if dns_queries > 0 and dns_responses == 0:
            limitations.append("DNS queries found but no responses — possible DNS resolution failure.")
    else:
        limitations.append("No DNS traffic found in capture. DNS resolution check cannot be performed.")

    summary = " ".join(parts) if parts else "No DNS traffic to analyze."

    return CheckOutput(
        check_name="dns_resolution",
        status=CheckStatus.completed,
        summary=summary,
        evidence_refs=evidence_refs,
        limitations=limitations,
    )


def _run_http_api_check(
    index_data: IndexData,
    timeline_data: list[TimelineBucketData],
    conversations: list[ConversationData],
) -> CheckOutput:
    """Check HTTP/API: error rates, latency."""
    http_packets = index_data.protocol_mix.get("HTTP", 0)
    tcp_conversations = [c for c in conversations if c.protocol == "TCP" and c.dst_port == 80]

    parts = []
    evidence_refs = []
    limitations = []

    if http_packets > 0:
        evidence_refs.append({"type": "protocol_mix", "protocol": "HTTP", "count": http_packets})
        parts.append(f"Found {http_packets} HTTP packet(s) across {len(tcp_conversations)} TCP conversation(s) on port 80.")

        # Stub doesn't provide HTTP status codes, so note limitation
        limitations.append("HTTP status code analysis not available from current index data. Full payload inspection required for error rate assessment.")
    else:
        limitations.append("No HTTP traffic found in capture. HTTP/API check cannot be performed.")

    summary = " ".join(parts) if parts else "No HTTP traffic to analyze."

    return CheckOutput(
        check_name="http_api",
        status=CheckStatus.completed,
        summary=summary,
        evidence_refs=evidence_refs,
        limitations=limitations,
    )


def _run_tls_handshake_check(
    index_data: IndexData,
    timeline_data: list[TimelineBucketData],
    conversations: list[ConversationData],
) -> CheckOutput:
    """Check TLS Handshake: failures, version issues."""
    # Check protocol mix for TLS/SSL
    tls_packets = index_data.protocol_mix.get("TLS", 0) + index_data.protocol_mix.get("SSL", 0)

    limitations = []

    if tls_packets == 0:
        return CheckOutput(
            check_name="tls_handshake",
            status=CheckStatus.skipped,
            summary="No TLS/SSL traffic found in capture. TLS handshake check skipped.",
            evidence_refs=[],
            limitations=["No TLS traffic present — cannot assess handshake health."],
        )

    return CheckOutput(
        check_name="tls_handshake",
        status=CheckStatus.completed,
        summary=f"Found {tls_packets} TLS packet(s).",
        evidence_refs=[{"type": "protocol_mix", "protocol": "TLS", "count": tls_packets}],
        limitations=["TLS version and cipher analysis requires deeper packet inspection."],
    )


def _run_path_visibility_check(
    index_data: IndexData,
    timeline_data: list[TimelineBucketData],
    conversations: list[ConversationData],
) -> CheckOutput:
    """Check Path / Visibility: one-sided flows, missing data."""
    parts = []
    evidence_refs = []
    limitations = []

    total_conversations = len(conversations)
    total_endpoints = len(index_data.top_endpoints)

    evidence_refs.append({
        "type": "conversation_count",
        "total": total_conversations,
    })
    evidence_refs.append({
        "type": "endpoint_count",
        "total": total_endpoints,
    })

    parts.append(f"Found {total_conversations} conversation(s) across {total_endpoints} endpoint(s).")

    # Check for potential one-sided flows
    # A very rough heuristic: if we only see one direction of a TCP conversation
    for conv in conversations:
        if conv.protocol == "TCP":
            # In the stub data, TCP conversations are bidirectional
            pass

    # Limitation: vantage point not known
    limitations.append("Capture vantage point is unknown — path visibility assessment may be incomplete.")
    limitations.append("One-sided flow detection requires bidirectional traffic analysis which is limited in index data.")

    summary = " ".join(parts)

    return CheckOutput(
        check_name="path_visibility",
        status=CheckStatus.completed,
        summary=summary,
        evidence_refs=evidence_refs,
        limitations=limitations,
    )


# Ordered list of default checks
DEFAULT_CHECKS = [
    _run_tcp_health_check,
    _run_dns_resolution_check,
    _run_http_api_check,
    _run_tls_handshake_check,
    _run_path_visibility_check,
]


def run_quick_analysis_checks(
    capture_path: str,
) -> list[CheckOutput]:
    """Run all default playbook checks against capture data.

    Uses the Packet Query Engine stubs for deterministic results.
    Returns a list of CheckOutput, one per check.
    """
    index_data = build_capture_index(capture_path)
    timeline_data = compute_timeline(capture_path)
    conversations = list_conversations(capture_path)

    results = []
    for check_fn in DEFAULT_CHECKS:
        result = check_fn(index_data, timeline_data, conversations)
        results.append(result)

    return results
