from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.user import User, Role
from app.models.redaction import AIRequestLog
from app.schemas.redaction import (
    RedactionPolicyResponse,
    UpdateRedactionPolicyRequest,
    RedactRequest,
    RedactResponse,
    RawContextSubmitRequest,
    RawContextSubmitResponse,
    AIRequestLogResponse,
)
from app.services.redaction import (
    get_redaction_policy,
    update_redaction_policy,
    redact_content,
    log_ai_request,
)

router = APIRouter(tags=["redaction"])


# ---------------------------------------------------------------------------
# Admin: Redaction Policy CRUD
# ---------------------------------------------------------------------------


@router.get(
    "/api/admin/redaction-policy",
    response_model=RedactionPolicyResponse,
)
async def get_policy(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_role(Role.admin)),
):
    policy = await get_redaction_policy(db)
    return policy


@router.put(
    "/api/admin/redaction-policy",
    response_model=RedactionPolicyResponse,
)
async def update_policy(
    body: UpdateRedactionPolicyRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_role(Role.admin)),
):
    policy = await get_redaction_policy(db)
    updates = body.model_dump(exclude_none=True)
    return await update_redaction_policy(db, policy, updates)


# ---------------------------------------------------------------------------
# Redaction endpoint (preview what gets masked)
# ---------------------------------------------------------------------------


@router.post(
    "/api/raw-context/redact",
    response_model=RedactResponse,
)
async def redact(
    body: RedactRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    policy = await get_redaction_policy(db)
    redacted = redact_content(body.content, policy)
    return RedactResponse(
        redacted_content=redacted,
        policy_applied=policy.profile,
    )


# ---------------------------------------------------------------------------
# Raw-context submission (requires admin-enabled sharing + analyst confirmation)
# ---------------------------------------------------------------------------


@router.post(
    "/api/raw-context/submit",
    response_model=RawContextSubmitResponse,
)
async def submit_raw_context(
    body: RawContextSubmitRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    policy = await get_redaction_policy(db)

    # Check if raw sharing is allowed
    if not policy.raw_sharing_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Raw-context sharing is not allowed by admin policy",
        )

    # Require analyst confirmation
    if not body.confirm_sharing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Analyst confirmation is required to share raw context with AI",
        )

    # Apply redaction
    redacted = redact_content(body.content, policy)

    # Log the AI request
    log_entry = await log_ai_request(
        db=db,
        user_id=user.id,
        context_category=body.context_category,
        model_used="gpt-4o",
        redacted=True,
    )

    return RawContextSubmitResponse(
        redacted_content=redacted,
        exploratory=True,
        warning="Raw-context output is exploratory. Claims must be verified by tool-grounded evidence before becoming Verified or Likely.",
        logged=True,
        request_log_id=log_entry.id,
    )


# ---------------------------------------------------------------------------
# Admin: AI Request Log
# ---------------------------------------------------------------------------


@router.get(
    "/api/admin/ai-request-log",
    response_model=list[AIRequestLogResponse],
)
async def get_ai_request_log(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_role(Role.admin)),
):
    result = await db.execute(
        select(AIRequestLog).order_by(AIRequestLog.id.desc())
    )
    entries = result.scalars().all()
    return entries
