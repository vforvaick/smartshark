"""Symptom Interview service — extracts fields from issue briefs and manages interview questions.

Field extraction uses keyword matching for the MVP. When AI is integrated,
this can be replaced with LLM-based extraction while keeping the same interface.
"""

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deep_analysis import IssueBrief, InterviewQuestion
from app.services.packet_query import IndexData, build_capture_index


# --- Field extraction ---

# Symptom keyword mapping
_SYMPTOM_PATTERNS: list[tuple[str, list[str]]] = [
    ("timeout", ["timeout", "time out", "timed out", "no response", "hangs", "hanging"]),
    ("reset", ["reset", "rst", "rset", "connection refused", "refused"]),
    ("slow", ["slow", "latency", "high latency", "delay", "delayed", "sluggish"]),
    ("failure", ["fail", "failing", "failed", "cannot", "can't", "unable", "broken", "not working"]),
    ("packet_loss", ["packet loss", "dropped", "drop", "missing packets", "loss"]),
    ("retransmission", ["retransmit", "retransmission", "re-transmit", "duplicate ack"]),
]

# Protocol keywords
_PROTOCOL_PATTERNS: list[tuple[str, list[str]]] = [
    ("TCP", ["tcp"]),
    ("UDP", ["udp"]),
    ("DNS", ["dns", "domain name"]),
    ("HTTP", ["http", "web"]),
    ("HTTPS", ["https", "tls", "ssl"]),
    ("ICMP", ["icmp", "ping"]),
]

# Timing keywords
_TIMING_PATTERN = re.compile(
    r"((?:every|each|at|during|between)\s+"
    r"[\w\s]+?(?:am|pm|morning|afternoon|evening|night|hour|minute|second|day|week|month|monday|tuesday|wednesday|thursday|friday|saturday|sunday))",
    re.IGNORECASE,
)

# IP address pattern
_IP_PATTERN = re.compile(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b")

# Port pattern
_PORT_PATTERN = re.compile(r"\bport\s+(\d{1,5})\b", re.IGNORECASE)

# Expected behavior pattern
_EXPECTED_PATTERN = re.compile(
    r"(?:expected|expect|should|supposed to|normally)\s+(.+?)(?:\.|,|$)",
    re.IGNORECASE,
)

# Goal pattern
_GOAL_PATTERNS = ["goal", "objective", "trying to", "want to", "need to", "looking for", "find"]


def extract_fields(raw_text: str) -> dict[str, str | None]:
    """Extract known fields from raw issue brief text.

    Returns a dict with keys: symptom, timing, endpoint, protocol,
    vantage_point, expected_behavior, goal.
    Missing fields have None values.
    """
    text_lower = raw_text.lower()
    fields: dict[str, str | None] = {
        "symptom": None,
        "timing": None,
        "endpoint": None,
        "protocol": None,
        "vantage_point": None,
        "expected_behavior": None,
        "goal": None,
    }

    # Extract symptom
    for symptom, keywords in _SYMPTOM_PATTERNS:
        if any(kw in text_lower for kw in keywords):
            fields["symptom"] = symptom
            break

    # Extract timing
    timing_match = _TIMING_PATTERN.search(raw_text)
    if timing_match:
        fields["timing"] = timing_match.group(1).strip()

    # Extract endpoint (IP address)
    ip_match = _IP_PATTERN.search(raw_text)
    if ip_match:
        fields["endpoint"] = ip_match.group(1)

    # Extract protocol
    for protocol, keywords in _PROTOCOL_PATTERNS:
        if any(kw in text_lower for kw in keywords):
            fields["protocol"] = protocol
            break

    # Extract expected behavior
    expected_match = _EXPECTED_PATTERN.search(raw_text)
    if expected_match:
        fields["expected_behavior"] = expected_match.group(1).strip()

    # Extract goal
    for goal_kw in _GOAL_PATTERNS:
        if goal_kw in text_lower:
            # Find the sentence containing the goal keyword
            sentences = raw_text.split(".")
            for sentence in sentences:
                if goal_kw in sentence.lower():
                    fields["goal"] = sentence.strip()
                    break
            break

    return fields


# --- Interview question generation ---

# High-value fields that should have questions
_HIGH_VALUE_FIELDS = [
    ("symptom", "What is the primary symptom you are observing? (e.g., timeouts, resets, slow response)"),
    ("endpoint", "Which endpoint(s) or IP address(es) are affected?"),
    ("timing", "When does the issue occur? (e.g., specific time, intermittent, constant)"),
    ("protocol", "Which protocol(s) are involved? (e.g., TCP, UDP, DNS, HTTP)"),
    ("expected_behavior", "What is the expected behavior? What should happen normally?"),
    ("goal", "What is your investigation goal? What are you trying to determine?"),
]

# Pre-scan influenced questions keyed by protocol presence
_PROTOCOL_SPECIFIC_QUESTIONS = {
    "DNS": ("dns_context", "The capture shows DNS traffic. Are the DNS queries for internal or external hosts? Any specific domains?"),
    "TCP": ("tcp_symptom", "The capture shows significant TCP traffic. Are you seeing retransmissions, connection failures, or slow throughput?"),
    "HTTP": ("http_context", "The capture contains HTTP traffic. Are there specific URLs, error codes, or slow page loads?"),
    "TLS": ("tls_context", "The capture contains TLS traffic. Are there handshake failures or certificate issues?"),
}


def generate_interview_questions(
    extracted_fields: dict[str, str | None],
    prescan_data: IndexData | None = None,
) -> list[tuple[str, str]]:
    """Generate interview questions for missing high-value fields.

    Returns a list of (field_name, question_text) tuples.
    Only asks about fields that are missing from the extracted_fields.
    Pre-scan data adds protocol-specific questions if those protocols are present.
    """
    questions = []

    # Ask about missing high-value fields
    for field_name, question_text in _HIGH_VALUE_FIELDS:
        if not extracted_fields.get(field_name):
            questions.append((field_name, question_text))

    # Add pre-scan influenced questions
    if prescan_data is not None:
        protocol_mix = prescan_data.protocol_mix
        for protocol, (field_name, question_text) in _PROTOCOL_SPECIFIC_QUESTIONS.items():
            if protocol in protocol_mix and not extracted_fields.get(field_name):
                # Only add if we don't already have a question for this field
                existing_fields = [q[0] for q in questions]
                if field_name not in existing_fields:
                    questions.append((field_name, question_text))

    return questions


# --- Service functions ---

async def create_issue_brief(
    db: AsyncSession,
    run_id: int,
    raw_text: str,
    capture_path: str | None = None,
) -> IssueBrief:
    """Create an IssueBrief, extract fields, and generate interview questions."""
    fields = extract_fields(raw_text)

    # Get prescan data if capture path is available
    prescan_data = None
    if capture_path:
        prescan_data = build_capture_index(capture_path)

    # Generate questions for missing fields
    question_defs = generate_interview_questions(fields, prescan_data)

    brief = IssueBrief(
        analysis_run_id=run_id,
        raw_text=raw_text,
        extracted_fields=fields,
    )
    db.add(brief)
    await db.flush()

    for field_name, question_text in question_defs:
        q = InterviewQuestion(
            issue_brief_id=brief.id,
            question_text=question_text,
            field_name=field_name,
        )
        db.add(q)

    await db.commit()
    await db.refresh(brief)
    return brief


async def get_issue_brief_by_run(
    db: AsyncSession, run_id: int
) -> IssueBrief | None:
    """Get IssueBrief for an analysis run. Returns None if not found."""
    result = await db.execute(
        select(IssueBrief)
        .where(IssueBrief.analysis_run_id == run_id)
    )
    return result.scalar_one_or_none()


async def get_interview_questions(
    db: AsyncSession, run_id: int
) -> list[InterviewQuestion]:
    """Get interview questions for a run."""
    brief = await get_issue_brief_by_run(db, run_id)
    if brief is None:
        return []
    result = await db.execute(
        select(InterviewQuestion)
        .where(InterviewQuestion.issue_brief_id == brief.id)
        .order_by(InterviewQuestion.id)
    )
    return list(result.scalars().all())


async def answer_question(
    db: AsyncSession, question_id: int, answer_text: str
) -> InterviewQuestion | None:
    """Record an answer to an interview question and update extracted_fields."""
    result = await db.execute(
        select(InterviewQuestion).where(InterviewQuestion.id == question_id)
    )
    question = result.scalar_one_or_none()
    if question is None:
        return None

    question.answer = answer_text
    question.is_answered = True

    # Update the brief's extracted_fields with the answer
    brief_result = await db.execute(
        select(IssueBrief).where(IssueBrief.id == question.issue_brief_id)
    )
    brief = brief_result.scalar_one_or_none()
    if brief is not None:
        fields = dict(brief.extracted_fields) if brief.extracted_fields else {}
        fields[question.field_name] = answer_text
        brief.extracted_fields = fields

    await db.commit()
    await db.refresh(question)
    return question


def is_interview_complete(questions: list[InterviewQuestion]) -> bool:
    """Check if all high-value questions have been answered."""
    if not questions:
        return True  # No questions means nothing to answer
    return all(q.is_answered for q in questions)
