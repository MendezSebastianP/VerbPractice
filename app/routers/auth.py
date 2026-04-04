from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.csrf import validate_csrf
from app.core.security import SESSION_USER_KEY, hash_password, verify_password
from app.db.models import User, UserProfile
from app.db.session import get_db
from app.routers.common import render_template

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/register")
async def register_page(request: Request):
    return render_template(request, "auth/register.html", {"error": None})


@router.post("/register")
async def register_action(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    csrf_token: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    username = username.strip().lower()

    if not username:
        return render_template(request, "auth/register.html", {"error": "Username is required."})

    if password != confirm_password:
        return render_template(request, "auth/register.html", {"error": "Passwords do not match."})

    existing = await db.execute(select(User).where(User.username == username))
    if existing.scalar_one_or_none():
        return render_template(request, "auth/register.html", {"error": "Username already exists."})

    user = User(username=username, password_hash=hash_password(password))
    db.add(user)
    await db.flush()

    profile = UserProfile(user_id=user.id, xp=0, level=1, streak_days=0, theme_preference="light")
    db.add(profile)
    await db.commit()

    request.session[SESSION_USER_KEY] = user.id
    return RedirectResponse(url="/", status_code=303)


@router.get("/login")
async def login_page(request: Request):
    return render_template(request, "auth/login.html", {"error": None})


@router.post("/login")
async def login_action(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    username = username.strip().lower()

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.password_hash):
        return render_template(request, "auth/login.html", {"error": "Invalid credentials."})

    request.session[SESSION_USER_KEY] = user.id
    return RedirectResponse(url="/", status_code=303)


@router.post("/logout")
async def logout_action(
    request: Request,
    csrf_token: str = Form(...),
):
    validate_csrf(request, csrf_token)
    request.session.clear()
    return RedirectResponse(url="/auth/login", status_code=303)
