from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_admin_context
from app.db.models import (
    ChatMessage,
    Language,
    ProgressItemType,
    SessionItem,
    TrainingMode,
    TrainingSession,
    TranslationReport,
    User,
    UserAddedWord,
    UserPreference,
    UserProfile,
    UserProgress,
    Verb,
    Word,
    WordLexicalEntry,
    WordNativeTranslation,
)
from app.db.session import get_db
from app.routers.common import render_template, templates
from app.services.word_ai_service import WordAIError, translate_word

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("")
@router.get("/")
async def admin_root():
    return RedirectResponse(url="/admin/users", status_code=status.HTTP_303_SEE_OTHER)


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


@router.get("/users")
async def users_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_rows = (await db.execute(select(User).order_by(User.username.asc()))).scalars().all()
    progress_counts: dict[int, int] = {}
    counts_query = await db.execute(
        select(UserProgress.user_id, func.count(UserProgress.id))
        .where(UserProgress.unlocked.is_(True))
        .group_by(UserProgress.user_id)
    )
    for user_id, count in counts_query.all():
        progress_counts[user_id] = count

    pref_rows = (await db.execute(select(UserPreference))).scalars().all()
    prefs_by_user = {p.user_id: p for p in pref_rows}
    lang_rows = (await db.execute(select(Language))).scalars().all()
    lang_by_id = {lang.id: lang for lang in lang_rows}

    users = []
    for user in user_rows:
        pref = prefs_by_user.get(user.id)
        users.append(
            {
                "id": user.id,
                "username": user.username,
                "is_admin": user.is_admin,
                "mother_tongue": lang_by_id[pref.mother_tongue_language_id].code if pref and pref.mother_tongue_language_id else "—",
                "learning_language": lang_by_id[pref.learning_language_id].code if pref and pref.learning_language_id else "—",
                "unlocked_count": progress_counts.get(user.id, 0),
            }
        )
    return render_template(
        request,
        "admin/users_list.html",
        {"profile": None, "users": users},
    )


@router.get("/users/{user_id}/inspect")
async def user_inspect(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_lookup = await db.execute(select(User).where(User.id == user_id))
    user = user_lookup.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    pref = (
        await db.execute(select(UserPreference).where(UserPreference.user_id == user_id))
    ).scalar_one_or_none()
    profile_row = (
        await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    ).scalar_one_or_none()
    lang_rows = (await db.execute(select(Language))).scalars().all()
    lang_by_id = {lang.id: lang for lang in lang_rows}

    progress_rows = (
        await db.execute(
            select(UserProgress)
            .where(UserProgress.user_id == user_id, UserProgress.unlocked.is_(True))
            .order_by(UserProgress.probability.desc())
        )
    ).scalars().all()

    word_ids = [p.item_id for p in progress_rows if p.item_type == ProgressItemType.WORD]
    verb_ids = [p.item_id for p in progress_rows if p.item_type == ProgressItemType.VERB]
    words_by_id = {}
    if word_ids:
        word_lookup = await db.execute(select(Word).where(Word.id.in_(word_ids)))
        words_by_id = {w.id: w for w in word_lookup.scalars().all()}
    verbs_by_id = {}
    if verb_ids:
        verb_lookup = await db.execute(select(Verb).where(Verb.id.in_(verb_ids)))
        verbs_by_id = {v.id: v for v in verb_lookup.scalars().all()}

    def _fmt(dt: datetime | None) -> str | None:
        if dt is None:
            return None
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    # Mean probability per language pair
    from collections import defaultdict
    pair_probs: dict[str, list[float]] = defaultdict(list)
    for p in progress_rows:
        pair_probs[p.language_pair].append(p.probability)
    pair_means = {pair: round(sum(v) / len(v), 1) for pair, v in sorted(pair_probs.items())}

    # Next 3 unlocked items per language pair (regular sequence, not priority queue)
    next_up: dict[str, list[dict]] = {}
    for pair, probs in pair_probs.items():
        parts = pair.split("_")
        if len(parts) != 2 or parts[1] == "conj":
            continue
        src_code = parts[0].upper()
        src_lang = next((lang for lang in lang_rows if lang.code == src_code), None)
        if src_lang is None:
            continue
        # Max unlocked item_id for word-type items in this pair
        unlocked_word_ids = [
            p.item_id for p in progress_rows
            if p.language_pair == pair and p.item_type == ProgressItemType.WORD
        ]
        max_word_id = max(unlocked_word_ids) if unlocked_word_ids else 0
        next_words = (
            await db.execute(
                select(Word)
                .where(Word.language_id == src_lang.id, Word.id > max_word_id)
                .order_by(Word.id.asc())
                .limit(3)
            )
        ).scalars().all()
        next_up[pair] = [{"label": w.text, "item_id": w.id} for w in next_words]

    progress_view = []
    for p in progress_rows:
        if p.item_type == ProgressItemType.WORD:
            label = words_by_id.get(p.item_id).text if p.item_id in words_by_id else f"#{p.item_id}"
        elif p.item_type == ProgressItemType.VERB:
            label = verbs_by_id.get(p.item_id).infinitive if p.item_id in verbs_by_id else f"#{p.item_id}"
        else:
            label = f"conj #{p.item_id}"
        progress_view.append(
            {
                "item_type": p.item_type.value,
                "item_id": p.item_id,
                "label": label,
                "language_pair": p.language_pair,
                "probability": round(p.probability, 1),
                "times_seen": p.times_seen,
                "times_correct": p.times_correct,
                "streak": p.streak,
                "last_seen": _fmt(p.last_seen),
            }
        )

    queue_rows = (
        await db.execute(
            select(UserAddedWord, Word)
            .join(Word, Word.id == UserAddedWord.word_id)
            .where(UserAddedWord.user_id == user_id)
            .order_by(UserAddedWord.added_at.asc())
        )
    ).all()
    priority_view = []
    for added, word in queue_rows:
        already = await db.execute(
            select(UserProgress.id).where(
                UserProgress.user_id == user_id,
                UserProgress.item_type == ProgressItemType.WORD,
                UserProgress.item_id == word.id,
                UserProgress.language_pair == added.language_pair,
            )
        )
        if already.scalar_one_or_none() is not None:
            continue
        priority_view.append(
            {
                "word_text": word.text,
                "language_pair": added.language_pair,
                "context_hint": added.context_hint,
                "added_at": _fmt(added.added_at),
            }
        )

    reports_rows = (
        await db.execute(
            select(TranslationReport)
            .where(TranslationReport.user_id == user_id)
            .order_by(TranslationReport.created_at.desc())
            .limit(50)
        )
    ).scalars().all()
    reports_view = []
    for r in reports_rows:
        target_text = ""
        if r.entry_type == "lexical":
            target_row = (
                await db.execute(select(WordLexicalEntry).where(WordLexicalEntry.id == r.entry_id))
            ).scalar_one_or_none()
            if target_row is not None:
                w = (await db.execute(select(Word).where(Word.id == target_row.word_id))).scalar_one_or_none()
                target_text = w.text if w else f"word #{target_row.word_id}"
        else:
            target_row = (
                await db.execute(select(WordNativeTranslation).where(WordNativeTranslation.id == r.entry_id))
            ).scalar_one_or_none()
            if target_row is not None:
                w = (await db.execute(select(Word).where(Word.id == target_row.word_id))).scalar_one_or_none()
                target_text = f"{w.text if w else '?'} → {target_row.translation}"
        reports_view.append(
            {
                "id": r.id,
                "entry_type": r.entry_type,
                "entry_id": r.entry_id,
                "target_text": target_text,
                "reason": r.reason,
                "status": r.status,
                "created_at": _fmt(r.created_at),
            }
        )

    context = {
        "profile": None,
        "target_user": {
            "id": user.id,
            "username": user.username,
            "is_admin": user.is_admin,
            "mother_tongue": lang_by_id[pref.mother_tongue_language_id].code if pref and pref.mother_tongue_language_id else "—",
            "learning_language": lang_by_id[pref.learning_language_id].code if pref and pref.learning_language_id else "—",
            "display_mode": pref.translation_display_mode if pref else "—",
            "force_unlock": pref.force_unlock_added_words if pref else False,
            "last_practice_pair": pref.last_practice_pair if pref else None,
            "xp": profile_row.xp if profile_row else 0,
            "level": profile_row.level if profile_row else 1,
        },
        "progress": progress_view,
        "pair_means": pair_means,
        "next_up": next_up,
        "priority": priority_view,
        "reports": reports_view,
    }
    return render_template(request, "admin/user_inspect.html", context)


@router.get("/reports")
async def reports_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    status_filter = request.query_params.get("status", "pending")
    query = select(TranslationReport).order_by(TranslationReport.created_at.desc())
    if status_filter and status_filter != "all":
        query = query.where(TranslationReport.status == status_filter)
    rows = (await db.execute(query.limit(200))).scalars().all()

    user_ids = {r.user_id for r in rows}
    users_by_id: dict[int, User] = {}
    if user_ids:
        user_lookup = await db.execute(select(User).where(User.id.in_(user_ids)))
        users_by_id = {u.id: u for u in user_lookup.scalars().all()}

    reports_view = []
    for r in rows:
        target_text = ""
        if r.entry_type == "lexical":
            target_row = (
                await db.execute(select(WordLexicalEntry).where(WordLexicalEntry.id == r.entry_id))
            ).scalar_one_or_none()
            if target_row is not None:
                w = (
                    await db.execute(select(Word).where(Word.id == target_row.word_id))
                ).scalar_one_or_none()
                target_text = w.text if w else f"word #{target_row.word_id}"
        else:
            target_row = (
                await db.execute(select(WordNativeTranslation).where(WordNativeTranslation.id == r.entry_id))
            ).scalar_one_or_none()
            if target_row is not None:
                w = (
                    await db.execute(select(Word).where(Word.id == target_row.word_id))
                ).scalar_one_or_none()
                target_text = f"{w.text if w else '?'} → {target_row.translation}"
        reporter = users_by_id.get(r.user_id)
        reports_view.append(
            {
                "id": r.id,
                "reporter_id": r.user_id,
                "reporter_username": reporter.username if reporter else f"#{r.user_id}",
                "entry_type": r.entry_type,
                "entry_id": r.entry_id,
                "target_text": target_text or "(deleted)",
                "reason": r.reason,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
            }
        )

    counts_rows = await db.execute(
        select(TranslationReport.status, func.count(TranslationReport.id)).group_by(
            TranslationReport.status
        )
    )
    counts = {row[0]: row[1] for row in counts_rows.all()}

    return render_template(
        request,
        "admin/reports_list.html",
        {
            "profile": None,
            "reports": reports_view,
            "current_filter": status_filter,
            "counts": counts,
        },
    )


@router.post("/reports/{report_id}/resolve")
async def resolve_report(
    report_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    action = str(form.get("action", ""))

    report = (
        await db.execute(select(TranslationReport).where(TranslationReport.id == report_id))
    ).scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    if action == "dismiss":
        report.status = "dismissed"
        report.resolved_at = datetime.now(timezone.utc)
        report.resolver_id = None
    elif action == "delete_translation":
        if report.entry_type == "lexical":
            entry = (
                await db.execute(select(WordLexicalEntry).where(WordLexicalEntry.id == report.entry_id))
            ).scalar_one_or_none()
        else:
            entry = (
                await db.execute(select(WordNativeTranslation).where(WordNativeTranslation.id == report.entry_id))
            ).scalar_one_or_none()
        if entry is not None:
            await db.delete(entry)
        report.status = "resolved"
        report.resolved_at = datetime.now(timezone.utc)
        report.resolver_id = None
    elif action == "regenerate":
        if report.entry_type == "lexical":
            entry = (
                await db.execute(select(WordLexicalEntry).where(WordLexicalEntry.id == report.entry_id))
            ).scalar_one_or_none()
            word_id = entry.word_id if entry else None
        else:
            entry = (
                await db.execute(select(WordNativeTranslation).where(WordNativeTranslation.id == report.entry_id))
            ).scalar_one_or_none()
            word_id = entry.word_id if entry else None
        if word_id is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Translation target missing")
        word = (await db.execute(select(Word).where(Word.id == word_id))).scalar_one()
        learning = (
            await db.execute(select(Language).where(Language.id == word.language_id))
        ).scalar_one()
        reporter_pref = (
            await db.execute(select(UserPreference).where(UserPreference.user_id == report.user_id))
        ).scalar_one_or_none()
        mother_id = reporter_pref.mother_tongue_language_id if reporter_pref else None
        if mother_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reporter has no mother tongue set; can't regenerate.",
            )
        mother = (
            await db.execute(select(Language).where(Language.id == mother_id))
        ).scalar_one()
        try:
            await translate_word(
                db,
                input_text=word.text,
                learning_lang=learning,
                mother_tongue=mother,
                force=True,
            )
        except WordAIError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        report.status = "resolved"
        report.resolved_at = datetime.now(timezone.utc)
        report.resolver_id = None
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown action")

    await db.commit()
    return_to = str(form.get("return_to") or f"/admin/users/{report.user_id}/inspect")
    return RedirectResponse(url=return_to, status_code=status.HTTP_303_SEE_OTHER)
