from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from fastapi import Depends, HTTPException, Request, status
from passlib.context import CryptContext
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, UserProfile
from app.db.session import get_db

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
SESSION_USER_KEY = "user_id"


def hash_password(raw_password: str) -> str:
    return pwd_context.hash(raw_password)


def verify_password(raw_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(raw_password, hashed_password)


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User | None:
    user_id = request.session.get(SESSION_USER_KEY)
    if not user_id:
        return None

    result = await db.execute(
        select(User).options(selectinload(User.profile)).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def require_user(user: User | None = Depends(get_current_user)) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/auth/login"})
    return user


async def attach_profile_if_missing(db: AsyncSession, user: User) -> UserProfile:
    profile_result = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = profile_result.scalar_one_or_none()
    if profile is not None:
        return profile

    profile = UserProfile(
        user_id=user.id,
        xp=0,
        level=1,
        streak_days=0,
        last_active_date=date.today(),
        theme_preference="light",
    )
    db.add(profile)
    await db.flush()
    return profile


@dataclass(slots=True)
class AuthContext:
    user: User
    profile: UserProfile


async def require_auth_context(
    user: User = Depends(require_user), db: AsyncSession = Depends(get_db)
) -> AuthContext:
    profile = await attach_profile_if_missing(db, user)
    return AuthContext(user=user, profile=profile)


async def require_admin_context(auth: AuthContext = Depends(require_auth_context)) -> AuthContext:
    if not auth.user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return auth
