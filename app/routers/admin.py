from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_admin_context
from app.db.models import ChatMessage, SessionItem, TrainingSession, User, UserProfile, UserProgress
from app.db.session import get_db
from app.routers.common import render_template, templates

router = APIRouter(prefix="/admin", tags=["admin"])


async def _monitor_snapshot(db: AsyncSession) -> dict[str, object]:
    user_rows = (await db.execute(select(User).order_by(User.created_at.desc()))).scalars().all()
    profile_rows = (
        await db.execute(select(UserProfile).order_by(UserProfile.user_id.asc()))
    ).scalars().all()
    active_sessions = (
        await db.execute(
            select(TrainingSession)
            .where(TrainingSession.completed_at.is_(None))
            .order_by(TrainingSession.started_at.desc())
            .limit(15)
        )
    ).scalars().all()
    recent_sessions = (
        await db.execute(
            select(TrainingSession)
            .where(TrainingSession.completed_at.is_not(None))
            .order_by(TrainingSession.completed_at.desc())
            .limit(15)
        )
    ).scalars().all()
    recent_items = (
        await db.execute(
            select(SessionItem).order_by(SessionItem.timestamp.desc()).limit(25)
        )
    ).scalars().all()
    hottest_progress = (
        await db.execute(
            select(UserProgress)
            .order_by(UserProgress.last_seen.desc().nullslast(), UserProgress.probability.desc())
            .limit(20)
        )
    ).scalars().all()
    recent_messages = (
        await db.execute(select(ChatMessage).order_by(ChatMessage.created_at.desc()).limit(10))
    ).scalars().all()

    totals = {
        "users": len(user_rows),
        "active_sessions": len(active_sessions),
        "completed_sessions": (
            await db.execute(select(func.count(TrainingSession.id)).where(TrainingSession.completed_at.is_not(None)))
        ).scalar_one(),
        "session_items": (await db.execute(select(func.count(SessionItem.id)))).scalar_one(),
        "progress_rows": (await db.execute(select(func.count(UserProgress.id)))).scalar_one(),
        "chat_messages": (await db.execute(select(func.count(ChatMessage.id)))).scalar_one(),
    }

    profiles_by_user = {row.user_id: row for row in profile_rows}
    users = []
    for user in user_rows:
        profile = profiles_by_user.get(user.id)
        users.append(
            {
                "id": user.id,
                "username": user.username,
                "level": profile.level if profile else 1,
                "xp": profile.xp if profile else 0,
                "streak_days": profile.streak_days if profile else 0,
                "theme": profile.theme_preference if profile else "light",
            }
        )

    return {
        "totals": totals,
        "users": users,
        "active_sessions": active_sessions,
        "recent_sessions": recent_sessions,
        "recent_items": recent_items,
        "hottest_progress": hottest_progress,
        "recent_messages": list(reversed(recent_messages)),
    }


@router.get("/monitor")
async def monitor_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_admin_context),
):
    request.state.user = auth.user
    snapshot = await _monitor_snapshot(db)
    return render_template(
        request,
        "admin/monitor.html",
        {
            "profile": auth.profile,
            **snapshot,
        },
    )


@router.get("/monitor/panel")
async def monitor_panel(
    request: Request,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_admin_context),
):
    request.state.user = auth.user
    snapshot = await _monitor_snapshot(db)
    context = {
        "request": request,
        "profile": auth.profile,
        **snapshot,
    }
    return templates.TemplateResponse(
        request,
        "admin/monitor_panel.html",
        context,
    )


@router.get("/api/live")
async def live_monitor_api(
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_admin_context),
):
    snapshot = await _monitor_snapshot(db)
    payload = {
        "totals": snapshot["totals"],
        "users": snapshot["users"],
        "active_sessions": [
            {
                "id": session.id,
                "user_id": session.user_id,
                "mode": session.mode.value,
                "language_pair": session.language_pair,
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "config": session.config,
            }
            for session in snapshot["active_sessions"]
        ],
        "recent_sessions": [
            {
                "id": session.id,
                "user_id": session.user_id,
                "mode": session.mode.value,
                "language_pair": session.language_pair,
                "score": session.score,
                "started_at": session.started_at.isoformat() if session.started_at else None,
                "completed_at": session.completed_at.isoformat() if session.completed_at else None,
            }
            for session in snapshot["recent_sessions"]
        ],
        "recent_items": [
            {
                "id": item.id,
                "session_id": item.session_id,
                "item_type": item.item_type.value,
                "item_id": item.item_id,
                "prompt": item.prompt,
                "answer": item.answer,
                "expected": item.expected,
                "correct": item.correct,
                "multiplier_applied": item.multiplier_applied,
                "timestamp": item.timestamp.isoformat() if item.timestamp else None,
            }
            for item in snapshot["recent_items"]
        ],
        "progress_rows": [
            {
                "user_id": row.user_id,
                "item_type": row.item_type.value,
                "item_id": row.item_id,
                "language_pair": row.language_pair,
                "probability": row.probability,
                "times_seen": row.times_seen,
                "times_correct": row.times_correct,
                "streak": row.streak,
                "last_seen": row.last_seen.isoformat() if row.last_seen else None,
            }
            for row in snapshot["hottest_progress"]
        ],
        "recent_messages": [
            {
                "id": message.id,
                "user_id": message.user_id,
                "role": message.role.value,
                "content": message.content,
                "created_at": message.created_at.isoformat() if message.created_at else None,
            }
            for message in snapshot["recent_messages"]
        ],
        "viewer": auth.user.username,
    }
    return JSONResponse(payload)
