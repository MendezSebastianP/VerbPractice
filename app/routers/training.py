from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.csrf import validate_csrf
from app.core.security import require_auth_context
from app.db.models import Language, ProgressItemType, TrainingMode, UserProfile
from app.db.session import get_db
from app.routers.common import render_template
from app.services.dashboard_service import summarize_progress
from app.services.training_service import (
    ITEM_TYPE_BY_MODE,
    build_conjugation_answers_from_form,
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

router = APIRouter(prefix="/training", tags=["training"])


def _translation_defaults(mode: TrainingMode) -> dict[str, Any]:
    if mode == TrainingMode.WORD_TRANSLATION:
        return {"title": "Word Training", "direction": "es_fr", "length": 10}
    return {"title": "Verb Training", "direction": "fr_es", "length": 10}


async def _render_translation_page(
    request: Request,
    db: AsyncSession,
    *,
    mode: TrainingMode,
    profile: UserProfile,
    feedback: str | None = None,
):
    defaults = _translation_defaults(mode)
    active = await get_active_session(db, user_id=request.state.user.id, mode=mode)
    overview = await summarize_progress(
        db,
        user_id=request.state.user.id,
        item_type=ITEM_TYPE_BY_MODE[mode],
        language_pair=defaults["direction"] if active is None else active.language_pair,
        focus_limit=0,
    )
    direction = defaults["direction"] if active is None else active.language_pair

    if active is None:
        return render_template(
            request,
            "training/translation.html",
            {
                "mode": mode.value,
                "title": defaults["title"],
                "setup": True,
                "default_length": defaults["length"],
                "default_direction": defaults["direction"],
                "feedback": feedback,
                "profile": profile,
                "overview": overview,
                "direction_label": "Spanish -> French" if defaults["direction"] == "es_fr" else "French -> Spanish",
            },
        )

    question = await get_translation_question(db, active)
    if question is None:
        return render_template(
            request,
            "training/translation.html",
            {
                "mode": mode.value,
                "title": defaults["title"],
                "setup": True,
                "finished": True,
                "default_length": defaults["length"],
                "default_direction": defaults["direction"],
                "feedback": feedback or "Session complete.",
                "profile": profile,
                "overview": overview,
                "direction_label": "Spanish -> French" if direction == "es_fr" else "French -> Spanish",
            },
        )

    config = active.config or {}
    queue = list(config.get("queue", []))
    index = int(config.get("index", 0))
    hint = await translation_hint_for_session(db, active)

    return render_template(
        request,
        "training/translation.html",
        {
            "mode": mode.value,
            "title": defaults["title"],
            "setup": False,
            "question": question,
            "session": active,
            "progress_current": min(index + 1, len(queue)),
            "progress_total": len(queue),
            "hint": hint,
            "feedback": feedback,
            "profile": profile,
            "direction": direction,
            "direction_label": "Spanish -> French" if direction == "es_fr" else "French -> Spanish",
            "overview": overview,
        },
    )


@router.get("/words")
async def words_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_auth_context),
):
    request.state.user = auth.user
    return await _render_translation_page(
        request,
        db,
        mode=TrainingMode.WORD_TRANSLATION,
        profile=auth.profile,
    )


@router.post("/words")
async def words_action(
    request: Request,
    action: str = Form(...),
    csrf_token: str = Form(...),
    length: int = Form(10),
    direction: str = Form("es_fr"),
    answer: str = Form(""),
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_auth_context),
):
    validate_csrf(request, csrf_token)
    request.state.user = auth.user

    mode = TrainingMode.WORD_TRANSLATION
    feedback = None

    if action == "start":
        await close_active_sessions(db, user_id=auth.user.id, mode=mode)
        await start_translation_session(
            db,
            user_id=auth.user.id,
            mode=mode,
            direction=direction,
            length=max(1, min(length, 50)),
        )
    else:
        session = await get_active_session(db, user_id=auth.user.id, mode=mode)
        if session:
            if action == "hint":
                await increment_hint(session)
            elif action == "answer":
                result = await submit_translation_answer(
                    db,
                    session=session,
                    profile=auth.profile,
                    answer=answer,
                    give_up=False,
                )
                feedback = result["feedback"]
            elif action == "giveup":
                result = await submit_translation_answer(
                    db,
                    session=session,
                    profile=auth.profile,
                    answer=answer,
                    give_up=True,
                )
                feedback = result["feedback"]

    await db.commit()
    return await _render_translation_page(
        request,
        db,
        mode=mode,
        profile=auth.profile,
        feedback=feedback,
    )


@router.get("/verbs")
async def verbs_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_auth_context),
):
    request.state.user = auth.user
    return await _render_translation_page(
        request,
        db,
        mode=TrainingMode.VERB_TRANSLATION,
        profile=auth.profile,
    )


@router.post("/verbs")
async def verbs_action(
    request: Request,
    action: str = Form(...),
    csrf_token: str = Form(...),
    length: int = Form(10),
    direction: str = Form("fr_es"),
    answer: str = Form(""),
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_auth_context),
):
    validate_csrf(request, csrf_token)
    request.state.user = auth.user

    mode = TrainingMode.VERB_TRANSLATION
    feedback = None

    if action == "start":
        await close_active_sessions(db, user_id=auth.user.id, mode=mode)
        await start_translation_session(
            db,
            user_id=auth.user.id,
            mode=mode,
            direction=direction,
            length=max(1, min(length, 50)),
        )
    else:
        session = await get_active_session(db, user_id=auth.user.id, mode=mode)
        if session:
            if action == "hint":
                await increment_hint(session)
            elif action == "answer":
                result = await submit_translation_answer(
                    db,
                    session=session,
                    profile=auth.profile,
                    answer=answer,
                    give_up=False,
                )
                feedback = result["feedback"]
            elif action == "giveup":
                result = await submit_translation_answer(
                    db,
                    session=session,
                    profile=auth.profile,
                    answer=answer,
                    give_up=True,
                )
                feedback = result["feedback"]

    await db.commit()
    return await _render_translation_page(
        request,
        db,
        mode=mode,
        profile=auth.profile,
        feedback=feedback,
    )


async def _render_conjugation_page(
    request: Request,
    db: AsyncSession,
    *,
    profile: UserProfile,
    feedback: str | None = None,
):
    active = await get_active_session(db, user_id=request.state.user.id, mode=TrainingMode.CONJUGATION)
    overview = await summarize_progress(
        db,
        user_id=request.state.user.id,
        item_type=ProgressItemType.CONJUGATION,
        language_pair=active.language_pair if active is not None else None,
        focus_limit=0,
    )

    languages_result = await db.execute(select(Language).order_by(Language.code.asc()))
    languages = languages_result.scalars().all()
    languages_payload = [
        {
            "code": lang.code,
            "name": lang.name,
            "difficulty_tiers": lang.difficulty_tiers or {},
        }
        for lang in languages
    ]

    if active is None:
        return render_template(
            request,
            "training/conjugation.html",
            {
                "setup": True,
                "languages": languages,
                "languages_payload": languages_payload,
                "feedback": feedback,
                "profile": profile,
                "overview": overview,
            },
        )

    question = await get_conjugation_question(db, active)
    if question is None:
        return render_template(
            request,
            "training/conjugation.html",
            {
                "setup": True,
                "languages": languages,
                "languages_payload": languages_payload,
                "finished": True,
                "feedback": feedback or "Session complete.",
                "profile": profile,
                "overview": overview,
            },
        )

    config = active.config or {}
    queue = list(config.get("queue", []))
    index = int(config.get("index", 0))

    return render_template(
        request,
        "training/conjugation.html",
        {
            "setup": False,
            "languages": languages,
            "languages_payload": languages_payload,
            "question": question,
            "session": active,
            "config": config,
            "progress_current": min(index + 1, len(queue)),
            "progress_total": len(queue),
            "feedback": feedback,
            "profile": profile,
            "overview": overview,
        },
    )


@router.get("/conjugation")
async def conjugation_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_auth_context),
):
    request.state.user = auth.user
    return await _render_conjugation_page(request, db, profile=auth.profile)


@router.post("/conjugation")
async def conjugation_action(
    request: Request,
    action: str = Form(...),
    csrf_token: str = Form(...),
    language: str = Form("FR"),
    level: str = Form("easy"),
    fill_level: str = Form("easy"),
    selected_tenses: list[str] = Form(default=[]),
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_auth_context),
):
    validate_csrf(request, csrf_token)
    request.state.user = auth.user

    feedback = None

    if action == "start":
        await close_active_sessions(db, user_id=auth.user.id, mode=TrainingMode.CONJUGATION)
        language_obj = await get_language_by_code(db, language)
        tenses = conjugation_tenses_for_level(language_obj, level, selected_tenses)
        await start_conjugation_session(
            db,
            user_id=auth.user.id,
            language_code=language,
            level=level,
            selected_tenses=tenses,
            fill_level=fill_level,
            length=5,
        )
    elif action == "submit":
        session = await get_active_session(db, user_id=auth.user.id, mode=TrainingMode.CONJUGATION)
        if session:
            form_data = await request.form()
            answers = build_conjugation_answers_from_form(dict(form_data))
            result = await submit_conjugation_answers(
                db,
                session=session,
                profile=auth.profile,
                answers=answers,
            )
            feedback = f"Score: {result['correct']}/{result['total']} ({result['accuracy']}%)"

    await db.commit()
    return await _render_conjugation_page(request, db, profile=auth.profile, feedback=feedback)
