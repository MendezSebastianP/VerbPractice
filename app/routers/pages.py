from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.csrf import validate_csrf
from app.core.security import get_current_user
from app.db.models import User, UserProfile
from app.db.session import get_db
from app.routers.common import render_template
from app.services.dashboard_service import dashboard_snapshot

router = APIRouter(tags=["pages"])


@router.get("/")
async def home_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    if user is None:
        return RedirectResponse(url="/app/login", status_code=303)
    return RedirectResponse(url="/app/dashboard", status_code=303)


@router.get("/legacy")
async def legacy_home_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=303)
    request.state.user = user

    profile_result = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = profile_result.scalar_one_or_none()
    snapshot = await dashboard_snapshot(db, user_id=user.id)

    return render_template(
        request,
        "home.html",
        {
            "user": user,
            "profile": profile,
            "total_items": snapshot["overall"]["total"],
            "mastered_items": snapshot["overall"]["mastered"],
            "completed_sessions": snapshot["completed_sessions"],
            "today_sessions": snapshot["today_sessions"],
            "recent_sessions": snapshot["recent_sessions"],
            "mode_counts": snapshot["mode_counts"],
            "mode_cards": snapshot["mode_cards"],
            "weak_items": snapshot["overall"]["focus_items"],
            "active_sessions": snapshot["active_sessions"],
            "recent_messages": snapshot["recent_messages"],
            "theme": profile.theme_preference if profile else "light",
        },
    )


@router.post("/preferences/theme")
async def update_theme(
    request: Request,
    theme: str = Form(...),
    csrf_token: str = Form(...),
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    validate_csrf(request, csrf_token)
    if user is None:
        return JSONResponse({"ok": False, "error": "Authentication required"}, status_code=401)

    theme = theme if theme in {"light", "dark", "arcade"} else "light"
    profile_result = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = profile_result.scalar_one_or_none()
    if profile is None:
        profile = UserProfile(user_id=user.id, theme_preference=theme, xp=0, level=1, streak_days=0)
        db.add(profile)
    else:
        profile.theme_preference = theme

    await db.commit()
    return JSONResponse({"ok": True, "theme": theme})
