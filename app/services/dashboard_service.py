from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ChatMessage,
    ProgressItemType,
    TrainingMode,
    TrainingSession,
    UserProgress,
    Verb,
    Word,
)


def _progress_filters(
    *,
    user_id: int,
    item_type: ProgressItemType | None = None,
    language_pair: str | None = None,
) -> list[Any]:
    filters: list[Any] = [UserProgress.user_id == user_id]
    if item_type is not None:
        filters.append(UserProgress.item_type == item_type)
    if language_pair is not None:
        filters.append(UserProgress.language_pair == language_pair)
    return filters


async def _label_maps(db: AsyncSession, rows: list[UserProgress]) -> tuple[dict[int, str], dict[int, str]]:
    word_ids = [row.item_id for row in rows if row.item_type == ProgressItemType.WORD]
    verb_ids = [
        row.item_id
        for row in rows
        if row.item_type in {ProgressItemType.VERB, ProgressItemType.CONJUGATION}
    ]

    word_map: dict[int, str] = {}
    verb_map: dict[int, str] = {}

    if word_ids:
        word_rows = await db.execute(select(Word).where(Word.id.in_(word_ids)))
        word_map = {item.id: item.text for item in word_rows.scalars().all()}

    if verb_ids:
        verb_rows = await db.execute(select(Verb).where(Verb.id.in_(verb_ids)))
        verb_map = {item.id: item.infinitive for item in verb_rows.scalars().all()}

    return word_map, verb_map


async def build_focus_items(
    db: AsyncSession,
    rows: list[UserProgress],
) -> list[dict[str, Any]]:
    word_map, verb_map = await _label_maps(db, rows)

    items: list[dict[str, Any]] = []
    for row in rows:
        if row.item_type == ProgressItemType.WORD:
            label = word_map.get(row.item_id, f"Word #{row.item_id}")
        else:
            label = verb_map.get(row.item_id, f"Verb #{row.item_id}")

        accuracy = round((row.times_correct / row.times_seen) * 100, 1) if row.times_seen else None
        items.append(
            {
                "label": label,
                "item_type": row.item_type.value,
                "language_pair": row.language_pair,
                "probability": round(row.probability),
                "times_seen": row.times_seen,
                "times_correct": row.times_correct,
                "accuracy": accuracy,
                "streak": row.streak,
            }
        )
    return items


async def summarize_progress(
    db: AsyncSession,
    *,
    user_id: int,
    item_type: ProgressItemType | None = None,
    language_pair: str | None = None,
    focus_limit: int = 4,
) -> dict[str, Any]:
    filters = _progress_filters(user_id=user_id, item_type=item_type, language_pair=language_pair)

    summary_row = (
        await db.execute(
            select(
                func.count(UserProgress.id).label("total"),
                func.count(UserProgress.id)
                .filter(UserProgress.unlocked.is_(True))
                .label("unlocked"),
                func.count(UserProgress.id)
                .filter(UserProgress.probability <= 200)
                .label("mastered"),
                func.count(UserProgress.id)
                .filter(UserProgress.times_seen > 0)
                .label("practiced"),
                func.avg(UserProgress.probability).label("avg_probability"),
            ).where(*filters)
        )
    ).one()

    focus_rows: list[UserProgress] = []
    if focus_limit > 0:
        focus_rows = (
            await db.execute(
                select(UserProgress)
                .where(*filters, UserProgress.unlocked.is_(True))
                .order_by(UserProgress.probability.desc(), UserProgress.times_seen.asc(), UserProgress.item_id.asc())
                .limit(focus_limit)
            )
        ).scalars().all()

    return {
        "total": summary_row.total,
        "unlocked": summary_row.unlocked,
        "mastered": summary_row.mastered,
        "practiced": summary_row.practiced,
        "avg_probability": round(float(summary_row.avg_probability or 0)),
        "focus_items": await build_focus_items(db, focus_rows),
    }


def mode_route(mode: TrainingMode) -> str:
    if mode == TrainingMode.WORD_TRANSLATION:
        return "/training/words"
    if mode == TrainingMode.VERB_TRANSLATION:
        return "/training/verbs"
    return "/training/verbs/conjugation"


def mode_label(mode: TrainingMode) -> str:
    if mode == TrainingMode.WORD_TRANSLATION:
        return "Word Training"
    if mode == TrainingMode.VERB_TRANSLATION:
        return "Verb Training"
    return "Conjugation"


async def dashboard_snapshot(db: AsyncSession, *, user_id: int) -> dict[str, Any]:
    overall = await summarize_progress(db, user_id=user_id, focus_limit=6)

    mode_specs = [
        (
            TrainingMode.WORD_TRANSLATION,
            ProgressItemType.WORD,
            "Word loops for high-frequency vocabulary and synonym tolerance.",
            "Spanish <> French",
        ),
        (
            TrainingMode.VERB_TRANSLATION,
            ProgressItemType.VERB,
            "Infinitive drills weighted toward the verbs that still slip.",
            "French <> Spanish",
        ),
        (
            TrainingMode.CONJUGATION,
            ProgressItemType.CONJUGATION,
            "Table practice with tense-aware scoring and verb unlocks.",
            "Per language",
        ),
    ]

    mode_cards: list[dict[str, Any]] = []
    for mode, item_type, description, pair_label in mode_specs:
        summary = await summarize_progress(db, user_id=user_id, item_type=item_type, focus_limit=3)
        mode_cards.append(
            {
                "mode": mode.value,
                "title": mode_label(mode),
                "href": mode_route(mode),
                "description": description,
                "pair_label": pair_label,
                **summary,
            }
        )

    completed_sessions = (
        await db.execute(
            select(func.count(TrainingSession.id)).where(
                TrainingSession.user_id == user_id,
                TrainingSession.completed_at.is_not(None),
            )
        )
    ).scalar_one()

    start_of_day = datetime.combine(date.today(), time.min, tzinfo=timezone.utc)
    today_sessions = (
        await db.execute(
            select(func.count(TrainingSession.id)).where(
                TrainingSession.user_id == user_id,
                TrainingSession.completed_at.is_not(None),
                TrainingSession.completed_at >= start_of_day,
            )
        )
    ).scalar_one()

    recent_sessions = (
        await db.execute(
            select(TrainingSession)
            .where(TrainingSession.user_id == user_id, TrainingSession.completed_at.is_not(None))
            .order_by(TrainingSession.completed_at.desc())
            .limit(8)
        )
    ).scalars().all()

    active_sessions_raw = (
        await db.execute(
            select(TrainingSession)
            .where(TrainingSession.user_id == user_id, TrainingSession.completed_at.is_(None))
            .order_by(TrainingSession.started_at.desc())
        )
    ).scalars().all()
    active_sessions: list[dict[str, Any]] = []
    for session in active_sessions_raw:
        config = session.config or {}
        queue = list(config.get("queue", []))
        index = int(config.get("index", 0))
        active_sessions.append(
            {
                "title": mode_label(session.mode),
                "href": mode_route(session.mode),
                "progress_current": min(index + 1, len(queue)) if queue else 0,
                "progress_total": len(queue),
                "started_at": session.started_at,
                "language_pair": session.language_pair,
            }
        )

    recent_messages = (
        await db.execute(
            select(ChatMessage)
            .where(ChatMessage.user_id == user_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(6)
        )
    ).scalars().all()

    mode_counts = {
        TrainingMode.WORD_TRANSLATION.value: 0,
        TrainingMode.VERB_TRANSLATION.value: 0,
        TrainingMode.CONJUGATION.value: 0,
    }
    for session in recent_sessions:
        mode_counts[session.mode.value] = mode_counts.get(session.mode.value, 0) + 1

    return {
        "overall": overall,
        "mode_cards": mode_cards,
        "completed_sessions": completed_sessions,
        "today_sessions": today_sessions,
        "recent_sessions": recent_sessions,
        "active_sessions": active_sessions,
        "mode_counts": mode_counts,
        "recent_messages": list(reversed(recent_messages)),
    }


async def recent_chat_messages(db: AsyncSession, *, user_id: int, limit: int = 20) -> list[ChatMessage]:
    rows = (
        await db.execute(
            select(ChatMessage)
            .where(ChatMessage.user_id == user_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return list(reversed(rows))
