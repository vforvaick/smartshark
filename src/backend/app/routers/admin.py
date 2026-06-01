from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_role
from app.models.user import Role, User

router = APIRouter(prefix="/api/admin", tags=["admin"])


class AIProviderSettings(BaseModel):
    provider: str = "openai"
    model: str = "gpt-4o"
    api_key_set: bool = False
    base_url: str | None = None


class UpdateAIProviderRequest(BaseModel):
    provider: str
    model: str
    api_key: str
    base_url: str | None = None


# In-memory placeholder — will move to DB in later issues
_ai_settings = AIProviderSettings()


@router.get("/ai-provider", response_model=AIProviderSettings)
async def get_ai_provider(_admin: User = Depends(require_role(Role.admin))):
    return _ai_settings


@router.put("/ai-provider", response_model=AIProviderSettings)
async def update_ai_provider(
    body: UpdateAIProviderRequest,
    _admin: User = Depends(require_role(Role.admin)),
):
    global _ai_settings
    _ai_settings = AIProviderSettings(
        provider=body.provider,
        model=body.model,
        api_key_set=bool(body.api_key),
        base_url=body.base_url,
    )
    return _ai_settings
