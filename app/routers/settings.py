from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.csrf import validate_csrf
from app.core.security import AuthContext, require_auth_context
from app.db.models import Language, UserPreference
from app.db.session import get_db
from app.schemas.spa import SettingsPatchPayload
from app.services.gamification import ensure_user_preference

router = APIRouter(prefix="/api", tags=["settings"])


VALID_DISPLAY_MODES = {"mother_full", "partial", "learning_full"}
VALID_PRACTICE_MODES = {"word_translation", "verb_translation"}


def _serialize_preference(pref: UserPreference, languages: dict[int, Language]) -> dict:
    return {
        "sound_enabled": pref.sound_enabled,
        "mother_tongue": _lang_payload(languages.get(pref.mother_tongue_language_id)) if pref.mother_tongue_language_id else None,
        "learning_language": _lang_payload(languages.get(pref.learning_language_id)) if pref.learning_language_id else None,
        "translation_display_mode": pref.translation_display_mode,
        "force_unlock_added_words": pref.force_unlock_added_words,
        "last_practice_pair": pref.last_practice_pair,
        "last_practice_mode": pref.last_practice_mode,
    }


def _lang_payload(lang: Language | None) -> dict | None:
    if lang is None:
        return None
    return {"id": lang.id, "code": lang.code, "name": lang.name}


async def _all_languages_map(db: AsyncSession) -> dict[int, Language]:
    rows = await db.execute(select(Language))
    return {lang.id: lang for lang in rows.scalars().all()}


async def _resolve_language_by_code(db: AsyncSession, code: str) -> Language:
    result = await db.execute(select(Language).where(Language.code == code.upper()))
    lang = result.scalar_one_or_none()
    if lang is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown language: {code}")
    return lang


@router.get("/settings")
async def get_settings(
    auth: AuthContext = Depends(require_auth_context),
    db: AsyncSession = Depends(get_db),
):
    preference = await ensure_user_preference(db, auth.user.id)
    languages = await _all_languages_map(db)
    return _serialize_preference(preference, languages)


@router.patch("/settings")
async def patch_settings(
    request: Request,
    payload: SettingsPatchPayload,
    auth: AuthContext = Depends(require_auth_context),
    db: AsyncSession = Depends(get_db),
):
    validate_csrf(request, payload.csrf_token)
    preference = await ensure_user_preference(db, auth.user.id)

    if payload.mother_tongue_code is not None:
        lang = await _resolve_language_by_code(db, payload.mother_tongue_code)
        preference.mother_tongue_language_id = lang.id

    if payload.learning_language_code is not None:
        lang = await _resolve_language_by_code(db, payload.learning_language_code)
        preference.learning_language_id = lang.id

    if payload.translation_display_mode is not None:
        if payload.translation_display_mode not in VALID_DISPLAY_MODES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid display mode. Must be one of: {sorted(VALID_DISPLAY_MODES)}",
            )
        preference.translation_display_mode = payload.translation_display_mode

    if payload.force_unlock_added_words is not None:
        preference.force_unlock_added_words = payload.force_unlock_added_words

    if payload.last_practice_pair is not None:
        preference.last_practice_pair = payload.last_practice_pair

    if payload.last_practice_mode is not None:
        if payload.last_practice_mode not in VALID_PRACTICE_MODES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid practice mode. Must be one of: {sorted(VALID_PRACTICE_MODES)}",
            )
        preference.last_practice_mode = payload.last_practice_mode

    await db.commit()
    await db.refresh(preference)
    languages = await _all_languages_map(db)
    return _serialize_preference(preference, languages)


@router.get("/languages")
async def list_languages(
    _auth: AuthContext = Depends(require_auth_context),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(select(Language).order_by(Language.code))
    return {"languages": [_lang_payload(lang) for lang in rows.scalars().all()]}
