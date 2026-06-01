from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.user import User, Role
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    UserResponse,
    CreateAnalystRequest,
)
from app.services.auth import verify_password, create_access_token, hash_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    token = create_access_token({"sub": user.username, "role": user.role.value})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/analysts", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_analyst(
    body: CreateAnalystRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_role(Role.admin)),
):
    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    analyst = User(
        username=body.username,
        hashed_password=hash_password(body.password),
        role=Role.analyst,
    )
    db.add(analyst)
    await db.commit()
    await db.refresh(analyst)
    return analyst
