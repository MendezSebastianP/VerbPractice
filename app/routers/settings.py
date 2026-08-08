from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.csrf import validate_csrf
from app.core.security import AuthContext, require_auth_context
from app.db.models import Language, TrainingMode, UserPreference
from app.db.session import get_db
from app.schemas.spa import OnboardingPatchPayload, SettingsPatchPayload
from app.services import onboarding as onboarding_service
from app.services.gamification import ensure_user_preference
from app.services.training_service import close_active_sessions
from app.services.tutorial import ensure_tutorial_words, tutorial_script

router = APIRouter(prefix="/api", tags=["settings"])


VALID_DISPLAY_MODES = {"mother_full", "partial", "learning_full"}
VALID_PRACTICE_MODES = {"word_translation", "verb_translation", "conjugation"}


def _serialize_preference(pref: UserPreference, languages: dict[int, Language]) -> dict:
    return {
        "sound_enabled": pref.sound_enabled,
        "show_shortcuts": pref.show_shortcuts,
        "mother_tongue": _lang_payload(languages.get(pref.mother_tongue_language_id)) if pref.mother_tongue_language_id else None,
        "learning_language": _lang_payload(languages.get(pref.learning_language_id)) if pref.learning_language_id else None,
        "translation_display_mode": pref.translation_display_mode,
        "force_unlock_added_words": pref.force_unlock_added_words,
        "last_practice_pair": pref.last_practice_pair,
        "last_practice_mode": pref.last_practice_mode,
        "trainer_setups": pref.trainer_setups or {},
        "onboarding": onboarding_service.normalize(pref.onboarding),
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

    if payload.show_shortcuts is not None:
        preference.show_shortcuts = payload.show_shortcuts

    if payload.last_practice_pair is not None:
        preference.last_practice_pair = payload.last_practice_pair

    if payload.last_practice_mode is not None:
        if payload.last_practice_mode not in VALID_PRACTICE_MODES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid practice mode. Must be one of: {sorted(VALID_PRACTICE_MODES)}",
            )
        preference.last_practice_mode = payload.last_practice_mode

    if payload.trainer_setup is not None:
        if payload.trainer_setup.mode not in VALID_PRACTICE_MODES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid trainer mode. Must be one of: {sorted(VALID_PRACTICE_MODES)}",
            )
        # Reassign (not mutate) so SQLAlchemy detects the JSON column change.
        setups = dict(preference.trainer_setups or {})
        setups[payload.trainer_setup.mode] = payload.trainer_setup.setup
        preference.trainer_setups = setups

    await db.commit()
    await db.refresh(preference)
    languages = await _all_languages_map(db)
    return _serialize_preference(preference, languages)


@router.patch("/onboarding")
async def patch_onboarding(
    request: Request,
    payload: OnboardingPatchPayload,
    auth: AuthContext = Depends(require_auth_context),
    db: AsyncSession = Depends(get_db),
):
    """Persist first-run progress.

    Kept off /settings because the client writes here on every tour step and
    drill completion, and the merge semantics differ — lists union rather than
    overwrite, so two tabs cannot undo each other's progress.
    """
    validate_csrf(request, payload.csrf_token)
    preference = await ensure_user_preference(db, auth.user.id)

    patch: dict = {}
    if payload.completed is not None:
        patch["completed"] = payload.completed
    if payload.seen_tours is not None:
        patch["seenTours"] = payload.seen_tours
    if payload.skipped is not None:
        patch["skipped"] = payload.skipped
    if payload.reset is not None:
        patch["reset"] = payload.reset

    if payload.reset:
        # Restarting drops the learner back on Words, which shows a live session
        # if one is open — and the setup tour's anchors only exist on the menu.
        # Close whatever is running so they land where the tutorial expects.
        for mode in TrainingMode:
            await close_active_sessions(db, user_id=auth.user.id, mode=mode)

    state = await onboarding_service.save_state(db, preference=preference, patch=patch)
    await db.commit()
    return state


@router.get("/tutorial/translation")
async def get_tutorial_script(
    direction: str,
    auth: AuthContext = Depends(require_auth_context),
    db: AsyncSession = Depends(get_db),
):
    """Prompt/answer pairs for the scripted first round.

    The client needs the expected answers up front — it has to say "write día"
    before the learner types anything — and grading stays server-side regardless.
    """
    if not re.fullmatch(r"[a-z]{2}_[a-z]{2}", direction or ""):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid direction"
        )
    # Idempotent, and the only guarantee that the Add Word step resolves from
    # the inventory rather than the model for an account that reached it by an
    # unusual route.
    await ensure_tutorial_words(db)
    await db.commit()
    return await tutorial_script(db, direction=direction)


@router.get("/languages")
async def list_languages(
    _auth: AuthContext = Depends(require_auth_context),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(select(Language).order_by(Language.code))
    return {"languages": [_lang_payload(lang) for lang in rows.scalars().all()]}
