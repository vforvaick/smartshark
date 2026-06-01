"""Redaction Pipeline — masks sensitive packet context before AI requests.

This module implements the Redaction Pipeline deep module:
- Applies admin-configured masking rules to text content
- Supports Verifone intelliNAC stricter payment masking
- Logs all AI requests for provenance
"""

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.redaction import RedactionPolicy, AIRequestLog


# ---------------------------------------------------------------------------
# Policy management
# ---------------------------------------------------------------------------


async def get_redaction_policy(db: AsyncSession) -> RedactionPolicy:
    """Get the current redaction policy. Creates default if none exists."""
    result = await db.execute(select(RedactionPolicy).limit(1))
    policy = result.scalar_one_or_none()
    if policy is None:
        policy = RedactionPolicy()
        db.add(policy)
        await db.commit()
        await db.refresh(policy)
    return policy


async def update_redaction_policy(
    db: AsyncSession, policy: RedactionPolicy, updates: dict
) -> RedactionPolicy:
    """Update policy fields from a dict of changes."""
    for key, value in updates.items():
        if value is not None and hasattr(policy, key):
            setattr(policy, key, value)
    await db.commit()
    await db.refresh(policy)
    return policy


# ---------------------------------------------------------------------------
# Redaction logic
# ---------------------------------------------------------------------------

# Patterns for sensitive content
_IP_PATTERN = re.compile(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b')
_MAC_PATTERN = re.compile(r'\b([0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2})\b')
_PAN_PATTERN = re.compile(r'\b(\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4})\b')
_AUTH_HEADER_PATTERN = re.compile(r'(Authorization:\s*).*', re.IGNORECASE)
_TOKEN_PATTERN = re.compile(r'(\btoken[=:]\s*)\S+', re.IGNORECASE)
_API_KEY_PATTERN = re.compile(r'(\bapi_?key[=:]\s*)\S+', re.IGNORECASE)
_COOKIE_PATTERN = re.compile(r'(Cookie:\s*)\S+', re.IGNORECASE)
_BODY_JSON_PATTERN = re.compile(r'(\{[^{}]*["\'](?:password|secret|token|key|credential)["\'][^{}]*\})', re.IGNORECASE)
# Verifone-specific: terminal IDs (8 digits) and auth codes (6 alphanum)
_TERMINAL_ID_PATTERN = re.compile(r'(Terminal\s*ID:\s*)\d{8}', re.IGNORECASE)
_AUTH_CODE_PATTERN = re.compile(r'(Auth\s*Code:\s*)[A-Za-z0-9]{4,8}', re.IGNORECASE)


def redact_content(content: str, policy: RedactionPolicy) -> str:
    """Apply redaction rules to text content based on policy settings."""
    result = content

    # Always apply in order: most specific patterns first

    if policy.mask_auth_headers:
        result = _AUTH_HEADER_PATTERN.sub(r'\1[REDACTED AUTH]', result)

    if policy.mask_credentials:
        result = _TOKEN_PATTERN.sub(r'\1[REDACTED CREDENTIAL]', result)
        result = _API_KEY_PATTERN.sub(r'\1[REDACTED CREDENTIAL]', result)
        result = _COOKIE_PATTERN.sub(r'\1[REDACTED CREDENTIAL]', result)

    if policy.mask_pan_values:
        result = _PAN_PATTERN.sub('[REDACTED PAN]', result)

    if policy.mask_payloads:
        result = _BODY_JSON_PATTERN.sub('[REDACTED PAYLOAD]', result)

    # Verifone intelliNAC stricter masking
    if policy.profile == "verifone-intellinac":
        result = _TERMINAL_ID_PATTERN.sub(r'\1[REDACTED TERMINAL]', result)
        result = _AUTH_CODE_PATTERN.sub(r'\1[REDACTED AUTH-CODE]', result)

    if policy.anonymize_ips:
        ip_map: dict[str, str] = {}
        counter = [0]

        def _replace_ip(match: re.Match) -> str:
            ip = match.group(1)
            if ip not in ip_map:
                counter[0] += 1
                ip_map[ip] = f"[IP-{chr(64 + counter[0])}]"
            return ip_map[ip]

        result = _IP_PATTERN.sub(_replace_ip, result)

    if policy.anonymize_macs:
        mac_map: dict[str, str] = {}
        counter = [0]

        def _replace_mac(match: re.Match) -> str:
            mac = match.group(1)
            if mac not in mac_map:
                counter[0] += 1
                mac_map[mac] = f"[MAC-{counter[0]}]"
            return mac_map[mac]

        result = _MAC_PATTERN.sub(_replace_mac, result)

    return result


# ---------------------------------------------------------------------------
# AI Request logging
# ---------------------------------------------------------------------------


async def log_ai_request(
    db: AsyncSession,
    user_id: int,
    context_category: str,
    model_used: str,
    redacted: bool,
    analysis_run_id: int | None = None,
) -> AIRequestLog:
    """Record an AI request for provenance."""
    entry = AIRequestLog(
        user_id=user_id,
        analysis_run_id=analysis_run_id,
        context_category=context_category,
        model_used=model_used,
        redacted=redacted,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry
