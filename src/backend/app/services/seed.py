from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, Role
from app.services.auth import hash_password


async def ensure_admin_exists(db: AsyncSession, default_password: str) -> None:
    """Seed an admin account on first run if none exists."""
    result = await db.execute(select(User).where(User.role == Role.admin))
    admin = result.scalar_one_or_none()
    if admin is None:
        admin = User(
            username="admin",
            hashed_password=hash_password(default_password),
            role=Role.admin,
        )
        db.add(admin)
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            # Another concurrent session may have inserted the admin
            result = await db.execute(select(User).where(User.role == Role.admin))
            admin = result.scalar_one_or_none()
            if admin is None:
                raise
