from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
import json
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.csrf import get_or_create_csrf_token, validate_csrf
from app.core.languages import format_direction_label
from app.core.rate_limit import limiter
from app.core.security import (
    SESSION_USER_KEY,
    attach_profile_if_missing,
    get_current_user,
    hash_password,
    require_admin_context,
    require_auth_context,
    verify_password,
)
from app.db.models import ChatMessage, ChatRole, Language, TrainingMode, User, UserProfile
from app.db.session import get_db
from app.routers.admin import _monitor_snapshot
from app.schemas.spa import (
    AdminConjugationRowPayload,
    AdminVerbRowPayload,
    AdminWordRowPayload,
    ChatStreamPayload,
    CircleFriendPayload,
    ConjugationStartPayload,
    ConjugationSubmitPayload,
    CredentialsPayload,
    CsrfPayload,
    RegisterPayload,
    SoundPreferencePayload,
    ThemePayload,
    TranslationAnswerPayload,
    TranslationStartPayload,
)
from app.services.admin_content import (
    content_summary,
    create_conjugation_row,
    create_verb_row,
    create_word_row,
    delete_conjugation_row,
    delete_verb_row,
    delete_word_row,
    list_conjugation_rows,
    list_verb_rows,
    list_word_rows,
    update_conjugation_row,
    update_verb_row,
    update_word_row,
)
from app.services.ai_usage import ai_usage_report
from app.services.chat_service import stream_chat_response
from app.services.dashboard_service import dashboard_snapshot, recent_chat_messages, summarize_progress
from app.services.gamification import (
    add_circle_friend,
    ensure_gamification_catalog,
    ensure_user_preference,
    gamification_snapshot,
    remove_circle_friend,
    set_sound_enabled,
)
from app.services.training_service import (
    ITEM_TYPE_BY_MODE,
    close_active_sessions,
    conjugation_tenses_for_level,
    get_active_session,
    get_conjugation_question,
    get_language_by_code,
    get_translation_question,
    increment_hint,
    start_conjugation_session,
    start_translation_session,
    submit_conjugation_answers,
    submit_translation_answer,
    translation_hint_for_session,
)

router = APIRouter(prefix="/api", tags=["api"])


def _iso(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    return None


def _sanitize_chat_text(raw: str) -> str:
    cleaned = "".join(char for char in raw if char.isprintable() or char in {"\n", "\t"})
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()[:1200]


def _http_400(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


async def _ensure_profile(db: AsyncSession, user: User | None) -> UserProfile | None:
    if user is None:
        return None
    existing = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = existing.scalar_one_or_none()
    if profile is not None:
        return profile
    profile = await attach_profile_if_missing(db, user)
    await db.commit()
    return profile


async def _ensure_sound_preference(db: AsyncSession, user: User | None) -> bool:
    if user is None:
        return False
    preference = await ensure_user_preference(db, user.id)
    return preference.sound_enabled


def _profile_payload(profile: UserProfile | None) -> dict[str, Any] | None:
    if profile is None:
        return None
    return {
        "xp": profile.xp,
        "level": profile.level,
        "streak_days": profile.streak_days,
        "last_active_date": profile.last_active_date.isoformat() if profile.last_active_date else None,
        "theme_preference": profile.theme_preference,
    }


def _user_payload(user: User | None, profile: UserProfile | None) -> dict[str, Any] | None:
    if user is None:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "is_admin": user.is_admin,
        "profile": _profile_payload(profile),
    }


def _preferences_payload(sound_enabled: bool | None) -> dict[str, Any]:
    return {
        "sound_enabled": bool(sound_enabled),
    }


def _bootstrap_payload(
    request: Request,
    user: User | None,
    profile: UserProfile | None,
    *,
    sound_enabled: bool | None = None,
) -> dict[str, Any]:
    theme = profile.theme_preference if profile else settings.default_theme
    return {
        "app_name": settings.app_name,
        "authenticated": user is not None,
        "csrf_token": get_or_create_csrf_token(request),
        "theme": theme,
        "user": _user_payload(user, profile),
        "preferences": _preferences_payload(sound_enabled),
        "entry_path": "/app/dashboard" if user else "/app/login",
    }


def _serialize_language(language: Language) -> dict[str, Any]:
    return {
        "code": language.code,
        "name": language.name,
        "pronoun_set": list(language.pronoun_set or []),
        "tense_definitions": dict(language.tense_definitions or {}),
        "difficulty_tiers": dict(language.difficulty_tiers or {}),
    }


def _serialize_recent_session(session) -> dict[str, Any]:
    return {
        "id": session.id,
        "mode": session.mode.value,
        "language_pair": session.language_pair,
        "score": session.score,
        "started_at": _iso(session.started_at),
        "completed_at": _iso(session.completed_at),
    }


def _serialize_chat_message(message: ChatMessage) -> dict[str, Any]:
    return {
        "id": message.id,
        "role": message.role.value,
        "content": message.content,
        "created_at": _iso(message.created_at),
    }


def _serialize_dashboard_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "overall": snapshot["overall"],
        "mode_cards": snapshot["mode_cards"],
        "completed_sessions": snapshot["completed_sessions"],
        "today_sessions": snapshot["today_sessions"],
        "recent_sessions": [_serialize_recent_session(session) for session in snapshot["recent_sessions"]],
        "active_sessions": [
            {
                **session,
                "started_at": _iso(session.get("started_at")),
            }
            for session in snapshot["active_sessions"]
        ],
        "mode_counts": snapshot["mode_counts"],
        "recent_messages": [_serialize_chat_message(message) for message in snapshot["recent_messages"]],
    }


def _translation_defaults(mode: TrainingMode) -> dict[str, Any]:
    if mode == TrainingMode.WORD_TRANSLATION:
        direction = "es_fr"
        return {
            "slug": "words",
            "title": "Word Training",
            "direction": direction,
            "length": 10,
            "direction_label": format_direction_label(direction),
        }
    direction = "fr_es"
    return {
        "slug": "verbs",
        "title": "Verb Training",
        "direction": direction,
        "length": 10,
        "direction_label": format_direction_label(direction),
    }


def _translation_mode_from_slug(mode_slug: str) -> TrainingMode:
    if mode_slug == "words":
        return TrainingMode.WORD_TRANSLATION
    if mode_slug == "verbs":
        return TrainingMode.VERB_TRANSLATION
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unsupported training mode")


async def _translation_state(
    db: AsyncSession,
    *,
    user_id: int,
    mode: TrainingMode,
    feedback: str | None = None,
    result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    defaults = _translation_defaults(mode)
    active = await get_active_session(db, user_id=user_id, mode=mode)
    direction = defaults["direction"]
    default_length = defaults["length"]
    if active is not None:
        direction = active.language_pair
    elif result is not None:
        direction = str(result.get("direction", direction))
        default_length = int(result.get("length", default_length))
    else:
        # No active session: prefer the user's last practiced pair so focus items match their history
        pref = await ensure_user_preference(db, user_id)
        if pref.last_practice_pair:
            direction = pref.last_practice_pair
    overview = await summarize_progress(
        db,
        user_id=user_id,
        item_type=ITEM_TYPE_BY_MODE[mode],
        language_pair=direction,
        focus_limit=4,
    )

    if active is None:
        return {
            "mode": mode.value,
            "slug": defaults["slug"],
            "title": defaults["title"],
            "setup": True,
            "finished": bool(result and result.get("finished")),
            "feedback": feedback,
            "defaults": {
                "length": default_length,
                "direction": direction,
            },
            "direction_label": format_direction_label(direction),
            "overview": overview,
            "result": result,
        }

    config = active.config or {}
    question = await get_translation_question(db, active)
    if question is None:
        return {
            "mode": mode.value,
            "slug": defaults["slug"],
            "title": defaults["title"],
            "setup": True,
            "finished": True,
            "feedback": feedback or "Session complete.",
            "defaults": {
                "length": int(config.get("length", default_length)),
                "direction": direction,
            },
            "direction_label": format_direction_label(direction),
            "overview": overview,
            "result": result,
        }

    queue = list(config.get("queue", []))
    index = int(config.get("index", 0))

    return {
        "mode": mode.value,
        "slug": defaults["slug"],
        "title": defaults["title"],
        "setup": False,
        "feedback": feedback,
        "result": result,
        "direction_label": format_direction_label(direction),
        "overview": overview,
        "session": {
            "id": active.id,
            "direction": direction,
            "length": int(config.get("length", default_length)),
            "progress_current": min(index + 1, len(queue)),
            "progress_total": len(queue),
            "combo": int(config.get("combo", 0)),
            "best_combo": int(config.get("best_combo", 0)),
        },
        "question": {
            "item_id": question.item_id,
            "prompt": question.prompt,
        },
        "hint": await translation_hint_for_session(db, active),
    }


async def _conjugation_languages(db: AsyncSession) -> list[Language]:
    rows = await db.execute(select(Language).order_by(Language.code.asc()))
    return rows.scalars().all()


async def _conjugation_state(
    db: AsyncSession,
    *,
    user_id: int,
    feedback: str | None = None,
    result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    active = await get_active_session(db, user_id=user_id, mode=TrainingMode.CONJUGATION)
    languages = await _conjugation_languages(db)
    default_pair = "fr_conj"
    language_pair = active.language_pair if active is not None else str((result or {}).get("language_pair", default_pair))
    overview = await summarize_progress(
        db,
        user_id=user_id,
        item_type=ITEM_TYPE_BY_MODE[TrainingMode.CONJUGATION],
        language_pair=language_pair,
        focus_limit=4,
    )

    serialized_languages = [_serialize_language(language) for language in languages]
    if active is None:
        return {
            "mode": TrainingMode.CONJUGATION.value,
            "slug": "conjugation",
            "title": "Conjugation Training",
            "setup": True,
            "finished": bool(result and result.get("finished")),
            "feedback": feedback,
            "result": result,
            "overview": overview,
            "languages": serialized_languages,
        }

    question = await get_conjugation_question(db, active)
    if question is None:
        return {
            "mode": TrainingMode.CONJUGATION.value,
            "slug": "conjugation",
            "title": "Conjugation Training",
            "setup": True,
            "finished": True,
            "feedback": feedback or "Conjugation session complete.",
            "result": result,
            "overview": overview,
            "languages": serialized_languages,
        }

    config = active.config or {}
    queue = list(config.get("queue", []))
    index = int(config.get("index", 0))
    rows: list[dict[str, Any]] = []
    for pronoun in question.pronouns:
        cells: list[dict[str, Any]] = []
        for tense in question.selected_tenses:
            expected = question.table[tense][pronoun]
            is_prefilled = question.prefill[tense].get(pronoun, False)
            if expected == "-":
                cells.append({"tense": tense, "kind": "missing", "value": None, "prefilled": False})
            elif is_prefilled:
                cells.append({"tense": tense, "kind": "prefilled", "value": expected, "prefilled": True})
            else:
                cells.append({"tense": tense, "kind": "input", "value": "", "prefilled": False})
        rows.append({"pronoun": pronoun, "cells": cells})

    return {
        "mode": TrainingMode.CONJUGATION.value,
        "slug": "conjugation",
        "title": "Conjugation Training",
        "setup": False,
        "feedback": feedback,
        "result": result,
        "overview": overview,
        "languages": serialized_languages,
        "session": {
            "id": active.id,
            "language": str(config.get("language", "FR")),
            "level": str(config.get("level", "easy")),
            "fill_level": str(config.get("fill_level", "easy")),
            "length": int(config.get("length", 5)),
            "selected_tenses": list(config.get("selected_tenses", [])),
            "progress_current": min(index + 1, len(queue)),
            "progress_total": len(queue),
            "combo": int(config.get("combo", 0)),
            "best_combo": int(config.get("best_combo", 0)),
        },
        "question": {
            "verb_id": question.verb_id,
            "verb": question.verb,
            "selected_tenses": question.selected_tenses,
            "pronouns": question.pronouns,
            "rows": rows,
        },
    }


async def _chat_state(db: AsyncSession, *, user_id: int) -> dict[str, Any]:
    messages = await recent_chat_messages(db, user_id=user_id, limit=18)
    weak_items = await summarize_progress(db, user_id=user_id, focus_limit=5)
    suggestions = [
        "Quiz me on the words I miss most often.",
        "Give me a short French-to-Spanish verb drill.",
        "Create a conjugation challenge using my weakest tense.",
    ]
    if weak_items["focus_items"]:
        suggestions[0] = f"Quiz me on {weak_items['focus_items'][0]['label']} and similar words."
    return {
        "messages": [_serialize_chat_message(message) for message in messages],
        "focus_items": weak_items["focus_items"],
        "suggestions": suggestions,
        "api_enabled": bool(settings.openai_api_key),
    }


@router.get("/bootstrap")
async def bootstrap(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    await ensure_gamification_catalog(db)
    profile = await _ensure_profile(db, user)
    sound_enabled = await _ensure_sound_preference(db, user)
    await db.commit()
    return JSONResponse(_bootstrap_payload(request, user, profile, sound_enabled=sound_enabled))


@router.post("/auth/login")
async def login(
    request: Request,
    payload: CredentialsPayload,
    db: AsyncSession = Depends(get_db),
):
    validate_csrf(request, payload.csrf_token)
    username = payload.username.strip().lower()
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    request.session[SESSION_USER_KEY] = user.id
    await ensure_gamification_catalog(db)
    profile = await _ensure_profile(db, user)
    sound_enabled = await _ensure_sound_preference(db, user)
    await db.commit()
    return JSONResponse(_bootstrap_payload(request, user, profile, sound_enabled=sound_enabled))


@router.post("/auth/register")
async def register(
    request: Request,
    payload: RegisterPayload,
    db: AsyncSession = Depends(get_db),
):
    validate_csrf(request, payload.csrf_token)
    username = payload.username.strip().lower()

    if not username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username is required")
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")

    existing = await db.execute(select(User).where(User.username == username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    user = User(username=username, password_hash=hash_password(payload.password))
    db.add(user)
    await db.flush()
    profile = UserProfile(user_id=user.id, xp=0, level=1, streak_days=0, theme_preference="light")
    db.add(profile)
    await ensure_gamification_catalog(db)
    await ensure_user_preference(db, user.id)
    await db.commit()

    request.session[SESSION_USER_KEY] = user.id
    return JSONResponse(_bootstrap_payload(request, user, profile, sound_enabled=False))


@router.post("/auth/logout")
async def logout(request: Request, payload: CsrfPayload):
    validate_csrf(request, payload.csrf_token)
    request.session.clear()
    return JSONResponse(_bootstrap_payload(request, None, None))


@router.post("/preferences/theme")
async def update_theme(
    request: Request,
    payload: ThemePayload,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_auth_context),
):
    validate_csrf(request, payload.csrf_token)
    theme = payload.theme if payload.theme in {"light", "dark", "arcade"} else "light"
    auth.profile.theme_preference = theme
    await db.commit()
    return JSONResponse({"ok": True, "theme": theme})


@router.post("/preferences/sound")
async def update_sound_preference(
    request: Request,
    payload: SoundPreferencePayload,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_auth_context),
):
    validate_csrf(request, payload.csrf_token)
    preference = await set_sound_enabled(db, user_id=auth.user.id, sound_enabled=payload.sound_enabled)
    await db.commit()
    return JSONResponse({"ok": True, "sound_enabled": preference.sound_enabled})


@router.get("/dashboard")
async def dashboard(
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_auth_context),
):
    await ensure_gamification_catalog(db)
    await ensure_user_preference(db, auth.user.id)
    snapshot = await dashboard_snapshot(db, user_id=auth.user.id)
    gamification = await gamification_snapshot(db, user=auth.user, profile=auth.profile)
    await db.commit()
    return JSONResponse(
        {
            "user": _user_payload(auth.user, auth.profile),
            "theme": auth.profile.theme_preference,
            "preferences": _preferences_payload(gamification["sound_enabled"]),
            "gamification": gamification,
            **_serialize_dashboard_snapshot(snapshot),
        }
    )


@router.get("/training/words")
async def words_state(
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_auth_context),
):
    return JSONResponse(await _translation_state(db, user_id=auth.user.id, mode=TrainingMode.WORD_TRANSLATION))


@router.get("/training/verbs")
async def verbs_state(
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_auth_context),
):
    return JSONResponse(await _translation_state(db, user_id=auth.user.id, mode=TrainingMode.VERB_TRANSLATION))


@router.post("/training/words/start")
async def words_start(
    request: Request,
    payload: TranslationStartPayload,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_auth_context),
):
    validate_csrf(request, payload.csrf_token)
    await close_active_sessions(db, user_id=auth.user.id, mode=TrainingMode.WORD_TRANSLATION)
    await start_translation_session(
        db,
        user_id=auth.user.id,
        mode=TrainingMode.WORD_TRANSLATION,
        direction=payload.direction,
        length=max(1, min(payload.length, 50)),
        set_id=payload.set_id,
    )
    await db.commit()
    return JSONResponse(await _translation_state(db, user_id=auth.user.id, mode=TrainingMode.WORD_TRANSLATION))


@router.post("/training/verbs/start")
async def verbs_start(
    request: Request,
    payload: TranslationStartPayload,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_auth_context),
):
    validate_csrf(request, payload.csrf_token)
    await close_active_sessions(db, user_id=auth.user.id, mode=TrainingMode.VERB_TRANSLATION)
    await start_translation_session(
        db,
        user_id=auth.user.id,
        mode=TrainingMode.VERB_TRANSLATION,
        direction=payload.direction,
        length=max(1, min(payload.length, 50)),
        set_id=payload.set_id,
    )
    await db.commit()
    return JSONResponse(await _translation_state(db, user_id=auth.user.id, mode=TrainingMode.VERB_TRANSLATION))


async def _active_translation_session_or_409(
    db: AsyncSession,
    *,
    user_id: int,
    mode: TrainingMode,
):
    session = await get_active_session(db, user_id=user_id, mode=mode)
    if session is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No active session")
    return session


@router.post("/training/words/hint")
async def words_hint(
    request: Request,
    payload: CsrfPayload,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_auth_context),
):
    validate_csrf(request, payload.csrf_token)
    session = await _active_translation_session_or_409(
        db, user_id=auth.user.id, mode=TrainingMode.WORD_TRANSLATION
    )
    await increment_hint(session)
    await db.commit()
    return JSONResponse(await _translation_state(db, user_id=auth.user.id, mode=TrainingMode.WORD_TRANSLATION))


@router.post("/training/verbs/hint")
async def verbs_hint(
    request: Request,
    payload: CsrfPayload,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_auth_context),
):
    validate_csrf(request, payload.csrf_token)
    session = await _active_translation_session_or_409(
        db, user_id=auth.user.id, mode=TrainingMode.VERB_TRANSLATION
    )
    await increment_hint(session)
    await db.commit()
    return JSONResponse(await _translation_state(db, user_id=auth.user.id, mode=TrainingMode.VERB_TRANSLATION))


@router.post("/training/words/finish")
async def words_finish(
    request: Request,
    payload: CsrfPayload,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_auth_context),
):
    validate_csrf(request, payload.csrf_token)
    session = await _active_translation_session_or_409(
        db, user_id=auth.user.id, mode=TrainingMode.WORD_TRANSLATION
    )
    config = dict(session.config or {})
    await close_active_sessions(db, user_id=auth.user.id, mode=TrainingMode.WORD_TRANSLATION)
    await db.commit()
    return JSONResponse(
        await _translation_state(
            db,
            user_id=auth.user.id,
            mode=TrainingMode.WORD_TRANSLATION,
            feedback="Session ended.",
            result={
                "finished": False,
                "direction": str(config.get("direction", "es_fr")),
                "length": int(config.get("length", 10)),
            },
        )
    )


@router.post("/training/verbs/finish")
async def verbs_finish(
    request: Request,
    payload: CsrfPayload,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_auth_context),
):
    validate_csrf(request, payload.csrf_token)
    session = await _active_translation_session_or_409(
        db, user_id=auth.user.id, mode=TrainingMode.VERB_TRANSLATION
    )
    config = dict(session.config or {})
    await close_active_sessions(db, user_id=auth.user.id, mode=TrainingMode.VERB_TRANSLATION)
    await db.commit()
    return JSONResponse(
        await _translation_state(
            db,
            user_id=auth.user.id,
            mode=TrainingMode.VERB_TRANSLATION,
            feedback="Session ended.",
            result={
                "finished": False,
                "direction": str(config.get("direction", "fr_es")),
                "length": int(config.get("length", 10)),
            },
        )
    )


@router.post("/training/words/answer")
async def words_answer(
    request: Request,
    payload: TranslationAnswerPayload,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_auth_context),
):
    validate_csrf(request, payload.csrf_token)
    session = await _active_translation_session_or_409(
        db, user_id=auth.user.id, mode=TrainingMode.WORD_TRANSLATION
    )
    result = await submit_translation_answer(
        db,
        session=session,
        profile=auth.profile,
        answer=payload.answer,
        give_up=False,
    )
    await db.commit()
    return JSONResponse(
        await _translation_state(
            db,
            user_id=auth.user.id,
            mode=TrainingMode.WORD_TRANSLATION,
            feedback=result["feedback"],
            result=result,
        )
    )


@router.post("/training/verbs/answer")
async def verbs_answer(
    request: Request,
    payload: TranslationAnswerPayload,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_auth_context),
):
    validate_csrf(request, payload.csrf_token)
    session = await _active_translation_session_or_409(
        db, user_id=auth.user.id, mode=TrainingMode.VERB_TRANSLATION
    )
    result = await submit_translation_answer(
        db,
        session=session,
        profile=auth.profile,
        answer=payload.answer,
        give_up=False,
    )
    await db.commit()
    return JSONResponse(
        await _translation_state(
            db,
            user_id=auth.user.id,
            mode=TrainingMode.VERB_TRANSLATION,
            feedback=result["feedback"],
            result=result,
        )
    )


@router.post("/training/words/reveal")
async def words_reveal(
    request: Request,
    payload: TranslationAnswerPayload,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_auth_context),
):
    validate_csrf(request, payload.csrf_token)
    session = await _active_translation_session_or_409(
        db, user_id=auth.user.id, mode=TrainingMode.WORD_TRANSLATION
    )
    result = await submit_translation_answer(
        db,
        session=session,
        profile=auth.profile,
        answer=payload.answer,
        give_up=True,
    )
    await db.commit()
    return JSONResponse(
        await _translation_state(
            db,
            user_id=auth.user.id,
            mode=TrainingMode.WORD_TRANSLATION,
            feedback=result["feedback"],
            result=result,
        )
    )


@router.post("/training/verbs/reveal")
async def verbs_reveal(
    request: Request,
    payload: TranslationAnswerPayload,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_auth_context),
):
    validate_csrf(request, payload.csrf_token)
    session = await _active_translation_session_or_409(
        db, user_id=auth.user.id, mode=TrainingMode.VERB_TRANSLATION
    )
    result = await submit_translation_answer(
        db,
        session=session,
        profile=auth.profile,
        answer=payload.answer,
        give_up=True,
    )
    await db.commit()
    return JSONResponse(
        await _translation_state(
            db,
            user_id=auth.user.id,
            mode=TrainingMode.VERB_TRANSLATION,
            feedback=result["feedback"],
            result=result,
        )
    )


@router.get("/training/conjugation")
async def conjugation_state(
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_auth_context),
):
    return JSONResponse(await _conjugation_state(db, user_id=auth.user.id))


@router.post("/training/conjugation/start")
async def conjugation_start(
    request: Request,
    payload: ConjugationStartPayload,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_auth_context),
):
    validate_csrf(request, payload.csrf_token)
    await close_active_sessions(db, user_id=auth.user.id, mode=TrainingMode.CONJUGATION)
    language = await get_language_by_code(db, payload.language)
    selected_tenses = conjugation_tenses_for_level(language, payload.level, payload.selected_tenses)
    await start_conjugation_session(
        db,
        user_id=auth.user.id,
        language_code=payload.language,
        level=payload.level,
        selected_tenses=selected_tenses,
        fill_level=payload.fill_level,
        length=max(1, min(payload.length, 20)),
    )
    await db.commit()
    return JSONResponse(await _conjugation_state(db, user_id=auth.user.id))


@router.post("/training/conjugation/submit")
async def conjugation_submit(
    request: Request,
    payload: ConjugationSubmitPayload,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_auth_context),
):
    validate_csrf(request, payload.csrf_token)
    session = await get_active_session(db, user_id=auth.user.id, mode=TrainingMode.CONJUGATION)
    if session is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No active session")

    result = await submit_conjugation_answers(
        db,
        session=session,
        profile=auth.profile,
        answers=payload.answers,
    )
    await db.commit()
    feedback = f"Score: {result.get('correct', 0)}/{result.get('total', 0)} · {result.get('accuracy', 0)}%"
    return JSONResponse(
        await _conjugation_state(
            db,
            user_id=auth.user.id,
            feedback=feedback,
            result=result,
        )
    )


@router.post("/training/conjugation/finish")
async def conjugation_finish(
    request: Request,
    payload: CsrfPayload,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_auth_context),
):
    validate_csrf(request, payload.csrf_token)
    session = await get_active_session(db, user_id=auth.user.id, mode=TrainingMode.CONJUGATION)
    if session is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No active session")

    language_pair = session.language_pair
    await close_active_sessions(db, user_id=auth.user.id, mode=TrainingMode.CONJUGATION)
    await db.commit()
    return JSONResponse(
        await _conjugation_state(
            db,
            user_id=auth.user.id,
            feedback="Session ended.",
            result={"finished": False, "language_pair": language_pair},
        )
    )


@router.get("/chat")
async def chat_state(
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_auth_context),
):
    return JSONResponse(await _chat_state(db, user_id=auth.user.id))


@router.post("/chat/stream")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def chat_stream(
    request: Request,
    payload: ChatStreamPayload,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_auth_context),
):
    validate_csrf(request, payload.csrf_token)
    content = _sanitize_chat_text(payload.message)
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message is required")

    db.add(ChatMessage(user_id=auth.user.id, role=ChatRole.USER, content=content))
    await db.flush()

    async def event_stream() -> AsyncIterator[str]:
        chunks: list[str] = []
        try:
            async for chunk in stream_chat_response(db=db, user_id=auth.user.id, user_message=content):
                chunks.append(chunk)
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        except Exception:
            fallback = "The tutor stream failed. Please try again."
            chunks.append(fallback)
            yield f"data: {json.dumps({'chunk': fallback})}\n\n"

        full_response = "".join(chunks)
        db.add(ChatMessage(user_id=auth.user.id, role=ChatRole.ASSISTANT, content=full_response))
        await db.commit()
        yield "event: done\ndata: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/community")
async def community_state(
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_auth_context),
):
    await ensure_gamification_catalog(db)
    await ensure_user_preference(db, auth.user.id)
    snapshot = await gamification_snapshot(db, user=auth.user, profile=auth.profile)
    await db.commit()
    return JSONResponse(snapshot)


@router.post("/community/friends")
async def add_circle_friend_route(
    request: Request,
    payload: CircleFriendPayload,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_auth_context),
):
    validate_csrf(request, payload.csrf_token)
    try:
        friend = await add_circle_friend(db, user_id=auth.user.id, username=payload.username)
    except ValueError as exc:
        raise _http_400(str(exc)) from exc
    await db.commit()
    return JSONResponse({"ok": True, "friend": {"user_id": friend.id, "username": friend.username}})


@router.delete("/community/friends/{friend_user_id}")
async def remove_circle_friend_route(
    friend_user_id: int,
    request: Request,
    payload: CsrfPayload,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_auth_context),
):
    validate_csrf(request, payload.csrf_token)
    await remove_circle_friend(db, user_id=auth.user.id, friend_user_id=friend_user_id)
    await db.commit()
    return JSONResponse({"ok": True})


@router.get("/admin/content/summary")
async def admin_content_summary(
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_admin_context),
):
    return JSONResponse({"viewer": auth.user.username, "summary": await content_summary(db)})


@router.get("/admin/ai/usage")
async def admin_ai_usage(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_admin_context),
):
    return JSONResponse(
        {
            "viewer": auth.user.username,
            **await ai_usage_report(db, limit=max(1, min(limit, 200))),
        }
    )


@router.get("/admin/content/words")
async def admin_content_words(
    search: str = "",
    verified: str | None = None,
    limit: int = 60,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_admin_context),
):
    rows = await list_word_rows(db, search=search, verified=verified, limit=max(1, min(limit, 200)))
    return JSONResponse({"rows": rows})


@router.post("/admin/content/words")
async def admin_content_words_create(
    request: Request,
    payload: AdminWordRowPayload,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_admin_context),
):
    validate_csrf(request, payload.csrf_token)
    try:
        row = await create_word_row(db, payload.model_dump(exclude={"csrf_token"}, exclude_none=True))
    except ValueError as exc:
        raise _http_400(str(exc)) from exc
    await db.commit()
    return JSONResponse({"row": row})


@router.patch("/admin/content/words/{translation_id}")
async def admin_content_words_update(
    translation_id: int,
    request: Request,
    payload: AdminWordRowPayload,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_admin_context),
):
    validate_csrf(request, payload.csrf_token)
    try:
        row = await update_word_row(db, translation_id, payload.model_dump(exclude={"csrf_token"}, exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await db.commit()
    return JSONResponse({"row": row})


@router.delete("/admin/content/words/{translation_id}")
async def admin_content_words_delete(
    translation_id: int,
    request: Request,
    payload: CsrfPayload,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_admin_context),
):
    validate_csrf(request, payload.csrf_token)
    await delete_word_row(db, translation_id)
    await db.commit()
    return JSONResponse({"ok": True})


@router.get("/admin/content/verbs")
async def admin_content_verbs(
    search: str = "",
    verified: str | None = None,
    limit: int = 60,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_admin_context),
):
    rows = await list_verb_rows(db, search=search, verified=verified, limit=max(1, min(limit, 200)))
    return JSONResponse({"rows": rows})


@router.post("/admin/content/verbs")
async def admin_content_verbs_create(
    request: Request,
    payload: AdminVerbRowPayload,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_admin_context),
):
    validate_csrf(request, payload.csrf_token)
    try:
        row = await create_verb_row(db, payload.model_dump(exclude={"csrf_token"}, exclude_none=True))
    except ValueError as exc:
        raise _http_400(str(exc)) from exc
    await db.commit()
    return JSONResponse({"row": row})


@router.patch("/admin/content/verbs/{translation_id}")
async def admin_content_verbs_update(
    translation_id: int,
    request: Request,
    payload: AdminVerbRowPayload,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_admin_context),
):
    validate_csrf(request, payload.csrf_token)
    try:
        row = await update_verb_row(db, translation_id, payload.model_dump(exclude={"csrf_token"}, exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await db.commit()
    return JSONResponse({"row": row})


@router.delete("/admin/content/verbs/{translation_id}")
async def admin_content_verbs_delete(
    translation_id: int,
    request: Request,
    payload: CsrfPayload,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_admin_context),
):
    validate_csrf(request, payload.csrf_token)
    await delete_verb_row(db, translation_id)
    await db.commit()
    return JSONResponse({"ok": True})


@router.get("/admin/content/conjugations")
async def admin_content_conjugations(
    search: str = "",
    verified: str | None = None,
    language_code: str | None = None,
    limit: int = 80,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_admin_context),
):
    rows = await list_conjugation_rows(
        db,
        search=search,
        verified=verified,
        language_code=language_code,
        limit=max(1, min(limit, 250)),
    )
    return JSONResponse({"rows": rows})


@router.post("/admin/content/conjugations")
async def admin_content_conjugations_create(
    request: Request,
    payload: AdminConjugationRowPayload,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_admin_context),
):
    validate_csrf(request, payload.csrf_token)
    try:
        row = await create_conjugation_row(db, payload.model_dump(exclude={"csrf_token"}, exclude_none=True))
    except ValueError as exc:
        raise _http_400(str(exc)) from exc
    await db.commit()
    return JSONResponse({"row": row})


@router.patch("/admin/content/conjugations/{conjugation_id}")
async def admin_content_conjugations_update(
    conjugation_id: int,
    request: Request,
    payload: AdminConjugationRowPayload,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_admin_context),
):
    validate_csrf(request, payload.csrf_token)
    try:
        row = await update_conjugation_row(
            db,
            conjugation_id,
            payload.model_dump(exclude={"csrf_token"}, exclude_none=True),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await db.commit()
    return JSONResponse({"row": row})


@router.delete("/admin/content/conjugations/{conjugation_id}")
async def admin_content_conjugations_delete(
    conjugation_id: int,
    request: Request,
    payload: CsrfPayload,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_admin_context),
):
    validate_csrf(request, payload.csrf_token)
    await delete_conjugation_row(db, conjugation_id)
    await db.commit()
    return JSONResponse({"ok": True})


@router.get("/admin/monitor")
async def admin_monitor(
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_admin_context),
):
    snapshot = await _monitor_snapshot(db)
    return JSONResponse(
        {
            "viewer": auth.user.username,
            "totals": snapshot["totals"],
            "users": snapshot["users"],
            "active_sessions": [
                {
                    "id": session.id,
                    "user_id": session.user_id,
                    "mode": session.mode.value,
                    "language_pair": session.language_pair,
                    "started_at": _iso(session.started_at),
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
                    "started_at": _iso(session.started_at),
                    "completed_at": _iso(session.completed_at),
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
                    "timestamp": _iso(item.timestamp),
                    "meta": item.meta,
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
                    "last_seen": _iso(row.last_seen),
                }
                for row in snapshot["hottest_progress"]
            ],
            "recent_messages": [_serialize_chat_message(message) for message in snapshot["recent_messages"]],
        }
    )
