from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.languages import tenses_for_level
from app.db.models import (
    Language,
    ProgressItemType,
    SessionItem,
    TrainingMode,
    TrainingSession,
    UserAddedWord,
    UserProfile,
    UserProgress,
    Verb,
    VerbConjugation,
    VerbTranslation,
    Word,
    WordTranslation,
)
from app.services.conjugation_engine import PronounCheck, conjugation_answer_is_correct, update_tense_score
from app.services.gamification import (
    RewardSummary,
    grant_xp,
    merge_reward_summaries,
    reward_summary_payload,
    track_weekly_metric,
    unlock_badges,
    update_streak,
)
from app.services.training_engine import (
    GradeResult,
    WeightedItem,
    grade_translation,
    hint_text,
    update_probability,
    weighted_sample_without_replacement,
)


ITEM_TYPE_BY_MODE: dict[TrainingMode, ProgressItemType] = {
    TrainingMode.WORD_TRANSLATION: ProgressItemType.WORD,
    TrainingMode.VERB_TRANSLATION: ProgressItemType.VERB,
    TrainingMode.CONJUGATION: ProgressItemType.CONJUGATION,
}


@dataclass(slots=True)
class TranslationQuestion:
    item_id: int
    prompt: str
    accepted_answers: list[str]
    synonym_answers: list[str]
    expected_primary: str


@dataclass(slots=True)
class ConjugationQuestion:
    verb_id: int
    verb: str
    selected_tenses: list[str]
    table: dict[str, dict[str, str]]
    prefill: dict[str, dict[str, bool]]
    pronouns: list[str]


async def _resolve_inventory_language(
    db: AsyncSession, mode: TrainingMode, direction: str
) -> Language:
    """Return the Language whose Word/Verb rows back this (mode, direction).

    Direction is "{source}_{target}" lowercase. Whichever side has inventory rows
    wins; if neither does, returns the source side (caller will see an empty set).
    """
    source_code, target_code = direction.upper().split("_")
    model = await _model_for_mode(mode)
    source_lang = await get_language_by_code(db, source_code)
    target_lang = await get_language_by_code(db, target_code)

    source_count = await db.scalar(
        select(func.count()).select_from(model).where(model.language_id == source_lang.id)
    )
    if source_count and source_count > 0:
        return source_lang
    target_count = await db.scalar(
        select(func.count()).select_from(model).where(model.language_id == target_lang.id)
    )
    if target_count and target_count > 0:
        return target_lang
    return source_lang


async def get_language_by_code(db: AsyncSession, code: str) -> Language:
    result = await db.execute(select(Language).where(Language.code == code))
    language = result.scalar_one_or_none()
    if language is None:
        raise ValueError(f"Language not found: {code}")
    return language


async def _model_for_mode(mode: TrainingMode):
    if mode == TrainingMode.WORD_TRANSLATION:
        return Word
    if mode == TrainingMode.VERB_TRANSLATION:
        return Verb
    raise ValueError(f"Unsupported translation mode: {mode}")


async def _translation_model_for_mode(mode: TrainingMode):
    if mode == TrainingMode.WORD_TRANSLATION:
        return WordTranslation
    if mode == TrainingMode.VERB_TRANSLATION:
        return VerbTranslation
    raise ValueError(f"Unsupported translation mode: {mode}")


async def eligible_translation_item_ids(
    db: AsyncSession,
    *,
    mode: TrainingMode,
    direction: str,
) -> list[int]:
    """Return inventory items that have a translation for this exact pair."""
    base_language = await _resolve_inventory_language(db, mode, direction)
    source_code, target_code = direction.upper().split("_")
    other_code = target_code if base_language.code == source_code else source_code
    other_language = await get_language_by_code(db, other_code)
    model = await _model_for_mode(mode)
    translation_model = await _translation_model_for_mode(mode)
    fk_column = translation_model.word_id if mode == TrainingMode.WORD_TRANSLATION else translation_model.verb_id

    rows = await db.execute(
        select(model.id)
        .join(translation_model, fk_column == model.id)
        .where(
            model.language_id == base_language.id,
            translation_model.target_language_id == other_language.id,
        )
        .distinct()
        .order_by(model.id.asc())
    )
    return [item_id for (item_id,) in rows.all()]


async def ensure_initial_translation_unlocks(
    db: AsyncSession,
    *,
    user_id: int,
    mode: TrainingMode,
    language_pair: str,
    initial_count: int = 10,
) -> None:
    item_type = ITEM_TYPE_BY_MODE[mode]
    existing_rows = await db.execute(
        select(UserProgress).where(
            UserProgress.user_id == user_id,
            UserProgress.item_type == item_type,
            UserProgress.language_pair == language_pair,
        )
    )
    existing_by_id = {row.item_id: row for row in existing_rows.scalars().all()}
    existing_ids = set(existing_by_id)
    unlocked_ids = {item_id for item_id, row in existing_by_id.items() if row.unlocked}
    eligible_ids = await eligible_translation_item_ids(
        db,
        mode=mode,
        direction=language_pair,
    )

    # Always drain user-added priority words for word_translation, even if
    # progress rows already exist (so a freshly added word appears next session).
    if mode == TrainingMode.WORD_TRANSLATION:
        priority_rows = await db.execute(
            select(UserAddedWord)
            .where(
                UserAddedWord.user_id == user_id,
                UserAddedWord.language_pair == language_pair,
            )
            .order_by(UserAddedWord.added_at.asc())
        )
        for added in priority_rows.scalars().all():
            if added.word_id in existing_ids:
                continue
            db.add(
                UserProgress(
                    user_id=user_id,
                    item_type=item_type,
                    item_id=added.word_id,
                    language_pair=language_pair,
                    probability=1000.0,
                    unlocked=True,
                    extra_data={"source": "user_added"},
                )
            )
            existing_ids.add(added.word_id)
            unlocked_ids.add(added.word_id)

    eligible_existing = unlocked_ids.intersection(eligible_ids)
    remaining = initial_count - len(eligible_existing)
    if remaining <= 0:
        return

    created = 0
    for item_id in eligible_ids:
        if item_id in unlocked_ids:
            continue
        existing = existing_by_id.get(item_id)
        if existing is not None:
            existing.unlocked = True
        else:
            row = UserProgress(
                user_id=user_id,
                item_type=item_type,
                item_id=item_id,
                language_pair=language_pair,
                probability=1000.0,
                unlocked=True,
                extra_data={},
            )
            db.add(row)
            existing_by_id[item_id] = row
        existing_ids.add(item_id)
        unlocked_ids.add(item_id)
        created += 1
        if created >= remaining:
            break


async def _select_weighted_items(
    db: AsyncSession,
    *,
    user_id: int,
    item_type: ProgressItemType,
    language_pair: str,
    length: int,
    scoped_item_ids: set[int] | None = None,
    eligible_item_ids: set[int] | None = None,
) -> list[int]:
    query = select(UserProgress).where(
        UserProgress.user_id == user_id,
        UserProgress.item_type == item_type,
        UserProgress.language_pair == language_pair,
        UserProgress.unlocked.is_(True),
    )
    if scoped_item_ids is not None:
        if not scoped_item_ids:
            return []
        query = query.where(UserProgress.item_id.in_(scoped_item_ids))
    if eligible_item_ids is not None:
        if not eligible_item_ids:
            return []
        query = query.where(UserProgress.item_id.in_(eligible_item_ids))
    rows = await db.execute(query.order_by(UserProgress.item_id.asc()))
    weighted_rows = [
        WeightedItem(item_id=row.item_id, probability=row.probability, last_seen=row.last_seen)
        for row in rows.scalars().all()
    ]
    return weighted_sample_without_replacement(weighted_rows, length)


async def _resolve_set_item_ids(
    db: AsyncSession, set_id: int, mode: TrainingMode
) -> set[int] | None:
    """Return item IDs contained in a set, or None if the set doesn't exist."""
    from app.db.models import VerbTag, WordSet, WordSetMember, WordTag

    ws = (await db.execute(select(WordSet).where(WordSet.id == set_id))).scalar_one_or_none()
    if ws is None:
        return None
    if ws.kind == "manual":
        if mode != TrainingMode.WORD_TRANSLATION:
            return set()
        rows = await db.execute(
            select(WordSetMember.word_id).where(WordSetMember.set_id == set_id)
        )
        return {r[0] for r in rows.all()}
    # smart
    tag_ids = list(ws.filter_tag_ids or [])
    if not tag_ids:
        return set()
    if mode == TrainingMode.WORD_TRANSLATION:
        item_id_column = WordTag.word_id
        tag_id_column = WordTag.tag_id
    elif mode == TrainingMode.VERB_TRANSLATION:
        item_id_column = VerbTag.verb_id
        tag_id_column = VerbTag.tag_id
    else:
        return set()
    rows = await db.execute(
        select(item_id_column, func.count(tag_id_column))
        .where(tag_id_column.in_(tag_ids))
        .group_by(item_id_column)
        .having(func.count(tag_id_column) == len(tag_ids))
    )
    return {r[0] for r in rows.all()}


async def get_active_session(
    db: AsyncSession,
    *,
    user_id: int,
    mode: TrainingMode,
) -> TrainingSession | None:
    result = await db.execute(
        select(TrainingSession)
        .where(
            TrainingSession.user_id == user_id,
            TrainingSession.mode == mode,
            TrainingSession.completed_at.is_(None),
        )
        .order_by(TrainingSession.started_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def close_active_sessions(
    db: AsyncSession,
    *,
    user_id: int,
    mode: TrainingMode,
) -> None:
    rows = await db.execute(
        select(TrainingSession).where(
            TrainingSession.user_id == user_id,
            TrainingSession.mode == mode,
            TrainingSession.completed_at.is_(None),
        )
    )
    now = datetime.now(timezone.utc)
    for session in rows.scalars().all():
        session.completed_at = now
        session.score = session.score or 0.0


async def start_translation_session(
    db: AsyncSession,
    *,
    user_id: int,
    mode: TrainingMode,
    direction: str,
    length: int,
    set_id: int | None = None,
) -> TrainingSession:
    language_pair = direction
    scoped_item_ids: set[int] | None = None
    if set_id is not None:
        scoped_item_ids = await _resolve_set_item_ids(db, set_id, mode)
        if scoped_item_ids is None:
            scoped_item_ids = set()

    await ensure_initial_translation_unlocks(
        db,
        user_id=user_id,
        mode=mode,
        language_pair=language_pair,
        initial_count=10,
    )

    eligible_item_ids = set(
        await eligible_translation_item_ids(
            db,
            mode=mode,
            direction=language_pair,
        )
    )
    if not eligible_item_ids:
        raise ValueError("No translations are available for that language pair.")

    item_ids = await _select_weighted_items(
        db,
        user_id=user_id,
        item_type=ITEM_TYPE_BY_MODE[mode],
        language_pair=language_pair,
        length=length,
        scoped_item_ids=scoped_item_ids,
        eligible_item_ids=eligible_item_ids,
    )
    if not item_ids:
        if set_id is not None:
            raise ValueError("This set has no items available for that language pair.")
        raise ValueError("No unlocked translations are available for that language pair.")

    session = TrainingSession(
        user_id=user_id,
        mode=mode,
        language_pair=language_pair,
        config={
            "queue": item_ids,
            "index": 0,
            "hint": 0,
            "length": length,
            "direction": direction,
            "combo": 0,
            "best_combo": 0,
            "scored_word_items": [],
        },
    )
    db.add(session)
    await db.flush()
    return session


async def _resolve_translation_question(
    db: AsyncSession,
    *,
    mode: TrainingMode,
    item_id: int,
    direction: str,
) -> TranslationQuestion:
    base_language = await _resolve_inventory_language(db, mode, direction)
    source_code, target_code = direction.upper().split("_")
    other_code = target_code if base_language.code == source_code else source_code
    target_language = await get_language_by_code(db, other_code)

    base_direction = f"{base_language.code.lower()}_{other_code.lower()}"
    model = await _model_for_mode(mode)
    translation_model = await _translation_model_for_mode(mode)

    item_result = await db.execute(select(model).where(model.id == item_id))
    item = item_result.scalar_one_or_none()
    if item is None:
        raise ValueError(f"Item not found: {item_id}")

    text_field = "text" if mode == TrainingMode.WORD_TRANSLATION else "infinitive"
    base_text = getattr(item, text_field)

    fk_column = translation_model.word_id if mode == TrainingMode.WORD_TRANSLATION else translation_model.verb_id
    target_rows = await db.execute(
        select(translation_model).where(
            fk_column == item.id,
            translation_model.target_language_id == target_language.id,
        )
    )
    translations = target_rows.scalars().all()
    if not translations:
        raise ValueError("No translation rows found")

    if item.language_id != base_language.id:
        # Fallback path for non-base items: treat as direct prompt and return source text as answer.
        return TranslationQuestion(
            item_id=item.id,
            prompt=base_text,
            accepted_answers=[base_text],
            synonym_answers=[],
            expected_primary=base_text,
        )

    if direction == base_direction:
        accepted = [row.translation for row in translations]
        synonyms = [syn for row in translations for syn in (row.synonyms or [])]
        prompt = base_text
    else:
        prompt = translations[0].translation
        accepted = [base_text]
        synonyms = []

    return TranslationQuestion(
        item_id=item.id,
        prompt=prompt,
        accepted_answers=accepted,
        synonym_answers=synonyms,
        expected_primary=accepted[0] if accepted else "",
    )


def _session_queue_state(session: TrainingSession) -> tuple[list[int], int, int, str]:
    config = session.config or {}
    queue = list(config.get("queue", []))
    index = int(config.get("index", 0))
    hint = int(config.get("hint", 0))
    direction = str(config.get("direction", "es_fr"))
    return queue, index, hint, direction


async def get_translation_question(
    db: AsyncSession,
    session: TrainingSession,
) -> TranslationQuestion | None:
    queue, index, _, direction = _session_queue_state(session)
    if index >= len(queue):
        return None
    item_id = queue[index]
    return await _resolve_translation_question(db, mode=session.mode, item_id=item_id, direction=direction)


async def increment_hint(session: TrainingSession) -> None:
    config = dict(session.config or {})
    config["hint"] = int(config.get("hint", 0)) + 1
    session.config = config


async def _get_or_create_progress(
    db: AsyncSession,
    *,
    user_id: int,
    item_type: ProgressItemType,
    item_id: int,
    language_pair: str,
    unlocked: bool = True,
) -> UserProgress:
    result = await db.execute(
        select(UserProgress).where(
            UserProgress.user_id == user_id,
            UserProgress.item_type == item_type,
            UserProgress.item_id == item_id,
            UserProgress.language_pair == language_pair,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        if unlocked and not row.unlocked:
            row.unlocked = True
        return row

    row = UserProgress(
        user_id=user_id,
        item_type=item_type,
        item_id=item_id,
        language_pair=language_pair,
        unlocked=unlocked,
        probability=1000.0,
        extra_data={},
    )
    db.add(row)
    await db.flush()
    return row


async def _unlock_next_items(
    db: AsyncSession,
    *,
    user_id: int,
    mode: TrainingMode,
    language_pair: str,
    count: int,
) -> int:
    item_type = ITEM_TYPE_BY_MODE[mode]

    created = 0
    remaining = count

    if mode == TrainingMode.WORD_TRANSLATION:
        priority_rows = await db.execute(
            select(UserAddedWord)
            .where(
                UserAddedWord.user_id == user_id,
                UserAddedWord.language_pair == language_pair,
            )
            .order_by(UserAddedWord.added_at.asc())
        )
        for added in priority_rows.scalars().all():
            if remaining <= 0:
                break
            existing = await db.execute(
                select(UserProgress.id).where(
                    UserProgress.user_id == user_id,
                    UserProgress.item_type == ProgressItemType.WORD,
                    UserProgress.item_id == added.word_id,
                    UserProgress.language_pair == language_pair,
                )
            )
            if existing.scalar_one_or_none() is not None:
                continue
            await _get_or_create_progress(
                db,
                user_id=user_id,
                item_type=item_type,
                item_id=added.word_id,
                language_pair=language_pair,
                unlocked=True,
            )
            created += 1
            remaining -= 1

    if remaining <= 0:
        return created

    current_rows = await db.execute(
        select(UserProgress)
        .where(
            UserProgress.user_id == user_id,
            UserProgress.item_type == item_type,
            UserProgress.language_pair == language_pair,
        )
    )
    unlocked_ids = {row.item_id for row in current_rows.scalars().all() if row.unlocked}
    eligible_ids = await eligible_translation_item_ids(
        db,
        mode=mode,
        direction=language_pair,
    )
    for item_id in (candidate for candidate in eligible_ids if candidate not in unlocked_ids):
        if remaining <= 0:
            break
        await _get_or_create_progress(
            db,
            user_id=user_id,
            item_type=item_type,
            item_id=item_id,
            language_pair=language_pair,
            unlocked=True,
        )
        created += 1
        remaining -= 1
    return created


async def maybe_unlock_translation_items(
    db: AsyncSession,
    *,
    user_id: int,
    mode: TrainingMode,
    language_pair: str,
) -> int:
    item_type = ITEM_TYPE_BY_MODE[mode]
    rows = await db.execute(
        select(UserProgress)
        .where(
            UserProgress.user_id == user_id,
            UserProgress.item_type == item_type,
            UserProgress.language_pair == language_pair,
            UserProgress.unlocked.is_(True),
        )
        .order_by(UserProgress.probability.asc())
        .limit(5)
    )
    best = rows.scalars().all()
    if not best:
        return 0
    avg = sum(row.probability for row in best) / len(best)
    if avg >= 750:
        return 0
    return await _unlock_next_items(db, user_id=user_id, mode=mode, language_pair=language_pair, count=3)


async def _count_session_accuracy(db: AsyncSession, session_id: int) -> float:
    rows = await db.execute(select(SessionItem).where(SessionItem.session_id == session_id))
    attempts = rows.scalars().all()
    if not attempts:
        return 0.0
    correct = sum(1 for item in attempts if item.correct)
    return (correct / len(attempts)) * 100


def _update_combo(config: dict[str, Any], *, succeeded: bool) -> RewardSummary:
    combo = int(config.get("combo", 0))
    best_combo = int(config.get("best_combo", 0))
    combo = combo + 1 if succeeded else 0
    best_combo = max(best_combo, combo)
    config["combo"] = combo
    config["best_combo"] = best_combo
    return RewardSummary(combo=combo, best_combo=best_combo)


def _int_set_from_config(config: dict[str, Any], key: str) -> set[int]:
    return {int(value) for value in config.get(key, [])}


def _str_set_from_config(config: dict[str, Any], key: str) -> set[str]:
    return {str(value) for value in config.get(key, [])}


def _store_config_int_set(config: dict[str, Any], key: str, values: set[int]) -> None:
    config[key] = sorted(values)


def _store_config_str_set(config: dict[str, Any], key: str, values: set[str]) -> None:
    config[key] = sorted(values)


def _conjugation_slot_key(*, verb_id: int, tense: str, pronoun: str) -> str:
    return f"{verb_id}|{tense}|{pronoun}"


async def submit_translation_answer(
    db: AsyncSession,
    *,
    session: TrainingSession,
    profile: UserProfile,
    answer: str,
    give_up: bool,
) -> dict[str, Any]:
    question = await get_translation_question(db, session)
    if question is None:
        return {"finished": True, "feedback": "Session complete."}

    queue, index, hint, direction = _session_queue_state(session)
    item_type = ITEM_TYPE_BY_MODE[session.mode]
    config = dict(session.config or {})
    scored_word_items = _int_set_from_config(config, "scored_word_items")

    if give_up:
        grade = GradeResult(False, False, 1.3, question.expected_primary)
    else:
        synonyms = question.synonym_answers if session.mode == TrainingMode.WORD_TRANSLATION else []
        grade = grade_translation(answer, question.accepted_answers, synonyms)

    score_applied = True
    effective_multiplier = grade.multiplier
    if session.mode == TrainingMode.WORD_TRANSLATION:
        score_applied = question.item_id not in scored_word_items
        effective_multiplier = grade.multiplier if score_applied else 1.0
        if score_applied:
            scored_word_items.add(question.item_id)
            _store_config_int_set(config, "scored_word_items", scored_word_items)

    progress = await _get_or_create_progress(
        db,
        user_id=session.user_id,
        item_type=item_type,
        item_id=question.item_id,
        language_pair=session.language_pair,
        unlocked=True,
    )

    progress.times_seen += 1
    if grade.is_correct:
        progress.times_correct += 1
        progress.streak += 1
    else:
        progress.streak = 0
    progress.probability = update_probability(progress.probability, effective_multiplier)
    progress.last_seen = datetime.now(timezone.utc)

    db.add(
        SessionItem(
            session_id=session.id,
            item_type=item_type,
            item_id=question.item_id,
            prompt=question.prompt,
            answer=answer,
            expected=grade.expected_primary,
            correct=grade.is_correct,
            multiplier_applied=effective_multiplier,
            meta={"direction": direction, "synonym": grade.is_synonym, "score_applied": score_applied},
        )
    )

    reward = _update_combo(config, succeeded=grade.is_correct and not give_up)
    update_streak(profile, date.today())
    if grade.is_correct and grade.is_synonym:
        reward = merge_reward_summaries(
            reward,
            await grant_xp(
                db,
                profile=profile,
                points=7,
                reason="translation_synonym",
                meta={"mode": session.mode.value, "item_id": question.item_id},
            ),
            await track_weekly_metric(
                db,
                user_id=session.user_id,
                metric_key="translation_correct",
                delta=1,
                profile=profile,
            ),
        )
    elif grade.is_correct:
        reward = merge_reward_summaries(
            reward,
            await grant_xp(
                db,
                profile=profile,
                points=10,
                reason="translation_correct",
                meta={"mode": session.mode.value, "item_id": question.item_id},
            ),
            await track_weekly_metric(
                db,
                user_id=session.user_id,
                metric_key="translation_correct",
                delta=1,
                profile=profile,
            ),
        )

    feedback: str
    if give_up:
        feedback = f"{question.prompt} → {grade.expected_primary}"
    elif grade.is_correct:
        feedback = "Correct!"
    else:
        feedback = f"Wrong. Correct answer: {grade.expected_primary}"

    if grade.is_correct or give_up:
        config["index"] = index + 1
        config["hint"] = 0
    else:
        config["hint"] = hint
    session.config = config

    finished = config.get("index", 0) >= len(queue)
    if finished:
        session.completed_at = datetime.now(timezone.utc)
        session.score = await _count_session_accuracy(db, session.id)
        reward = merge_reward_summaries(
            reward,
            await grant_xp(
                db,
                profile=profile,
                points=25,
                reason="session_complete",
                meta={"mode": session.mode.value},
            ),
            await track_weekly_metric(
                db,
                user_id=session.user_id,
                metric_key="completed_sessions",
                delta=1,
                profile=profile,
            ),
        )
        if session.score >= 100:
            reward = merge_reward_summaries(
                reward,
                await track_weekly_metric(
                    db,
                    user_id=session.user_id,
                    metric_key="perfect_sessions",
                    delta=1,
                    profile=profile,
                ),
            )
        await maybe_unlock_translation_items(
            db,
            user_id=session.user_id,
            mode=session.mode,
            language_pair=session.language_pair,
        )

    reward.unlocked_badges.extend(await unlock_badges(db, user_id=session.user_id, profile=profile))
    return {
        "finished": finished,
        "feedback": feedback,
        "is_correct": grade.is_correct,
        "is_synonym": grade.is_synonym,
        "direction": direction,
        "length": int(config.get("length", len(queue) or 10)),
        "gamification": reward_summary_payload(reward),
    }


async def translation_hint_for_session(db: AsyncSession, session: TrainingSession) -> str:
    question = await get_translation_question(db, session)
    if question is None:
        return ""
    config = session.config or {}
    hint_level = int(config.get("hint", 0))
    return hint_text(question.expected_primary, hint_level)


async def eligible_conjugation_verb_ids(
    db: AsyncSession,
    *,
    language: Language,
    selected_tenses: list[str],
) -> list[int]:
    """Return verbs with a complete row for every requested table slot."""
    pronouns = list(language.pronoun_set or [])
    if not selected_tenses or not pronouns:
        return []

    tense_definitions = language.tense_definitions or {}
    slot_filters = []
    for tense in selected_tenses:
        definition = tense_definitions.get(tense)
        if not definition:
            return []
        slot_filters.append(
            and_(
                VerbConjugation.tense == tense,
                VerbConjugation.mood == str(definition.get("mood", "Indicatif")),
            )
        )

    required_slots = len(selected_tenses) * len(pronouns)
    rows = await db.execute(
        select(VerbConjugation.verb_id)
        .where(
            VerbConjugation.language_id == language.id,
            VerbConjugation.pronoun.in_(pronouns),
            or_(*slot_filters),
        )
        .group_by(VerbConjugation.verb_id)
        .having(func.count(VerbConjugation.id) == required_slots)
        .order_by(VerbConjugation.verb_id.asc())
    )
    return [verb_id for (verb_id,) in rows.all()]


async def ensure_initial_conjugation_unlocks(
    db: AsyncSession,
    *,
    user_id: int,
    language_code: str,
    language_pair: str,
    selected_tenses: list[str],
    initial_count: int = 10,
) -> int:
    language = await get_language_by_code(db, language_code)
    eligible_ids = await eligible_conjugation_verb_ids(
        db,
        language=language,
        selected_tenses=selected_tenses,
    )
    if not eligible_ids:
        return 0

    existing_rows = await db.execute(
        select(UserProgress).where(
            UserProgress.user_id == user_id,
            UserProgress.item_type == ProgressItemType.CONJUGATION,
            UserProgress.language_pair == language_pair,
        )
    )
    existing_progress = existing_rows.scalars().all()
    existing_by_id = {row.item_id: row for row in existing_progress}
    unlocked_ids = {row.item_id for row in existing_progress if row.unlocked}
    eligible_existing = unlocked_ids.intersection(eligible_ids)
    needed = max(0, initial_count - len(eligible_existing))
    created = 0
    for verb_id in (item_id for item_id in eligible_ids if item_id not in unlocked_ids):
        if created >= needed:
            break
        existing = existing_by_id.get(verb_id)
        if existing is not None:
            existing.unlocked = True
        else:
            row = UserProgress(
                user_id=user_id,
                item_type=ProgressItemType.CONJUGATION,
                item_id=verb_id,
                language_pair=language_pair,
                probability=1000.0,
                unlocked=True,
                extra_data={"tense_scores": {}},
            )
            db.add(row)
            existing_by_id[verb_id] = row
        unlocked_ids.add(verb_id)
        created += 1
    return created


async def start_conjugation_session(
    db: AsyncSession,
    *,
    user_id: int,
    language_code: str,
    level: str,
    selected_tenses: list[str],
    fill_level: str,
    length: int = 5,
) -> TrainingSession:
    language_pair = f"{language_code.lower()}_conj"
    language = await get_language_by_code(db, language_code)
    eligible_ids = await eligible_conjugation_verb_ids(
        db,
        language=language,
        selected_tenses=selected_tenses,
    )
    if not eligible_ids:
        raise ValueError("No complete conjugation tables are available for those tenses.")

    await ensure_initial_conjugation_unlocks(
        db,
        user_id=user_id,
        language_code=language_code,
        language_pair=language_pair,
        selected_tenses=selected_tenses,
        initial_count=10,
    )

    unlocked_rows = await db.execute(
        select(UserProgress)
        .where(
            UserProgress.user_id == user_id,
            UserProgress.item_type == ProgressItemType.CONJUGATION,
            UserProgress.language_pair == language_pair,
            UserProgress.unlocked.is_(True),
            UserProgress.item_id.in_(eligible_ids),
        )
        .order_by(UserProgress.item_id.asc())
    )

    weighted: list[WeightedItem] = []
    for row in unlocked_rows.scalars().all():
        tense_scores = (row.extra_data or {}).get("tense_scores", {})
        if selected_tenses:
            values = [float(tense_scores.get(tense, 1000.0)) for tense in selected_tenses]
            probability = sum(values) / len(values)
        else:
            probability = row.probability
        weighted.append(WeightedItem(item_id=row.item_id, probability=probability, last_seen=row.last_seen))

    queue = weighted_sample_without_replacement(weighted, length)
    if not queue:
        raise ValueError("No unlocked conjugation tables are available for those tenses.")

    session = TrainingSession(
        user_id=user_id,
        mode=TrainingMode.CONJUGATION,
        language_pair=language_pair,
        config={
            "queue": queue,
            "index": 0,
            "length": length,
            "level": level,
            "selected_tenses": selected_tenses,
            "fill_level": fill_level,
            "language": language_code,
            "combo": 0,
            "best_combo": 0,
            "scored_conjugation_slots": [],
            "checked_conjugation_tenses": [],
            "pending_conjugation_answers": {},
            "conjugation_tense_reviews": {},
        },
    )
    db.add(session)
    await db.flush()
    return session


async def _conjugation_table_for_verb(
    db: AsyncSession,
    *,
    verb_id: int,
    language: Language,
    selected_tenses: list[str],
) -> dict[str, dict[str, str]]:
    table: dict[str, dict[str, str]] = {}
    for tense in selected_tenses:
        mood = (language.tense_definitions or {}).get(tense, {}).get("mood", "Indicatif")
        rows = await db.execute(
            select(VerbConjugation)
            .where(
                VerbConjugation.verb_id == verb_id,
                VerbConjugation.language_id == language.id,
                VerbConjugation.tense == tense,
                VerbConjugation.mood == mood,
            )
            .order_by(VerbConjugation.pronoun.asc())
        )
        by_pronoun = {entry.pronoun: entry.conjugated_form for entry in rows.scalars().all()}
        table[tense] = {
            pronoun: by_pronoun.get(pronoun, "-")
            for pronoun in (language.pronoun_set or [])
        }
    return table


async def get_conjugation_question(
    db: AsyncSession,
    session: TrainingSession,
) -> ConjugationQuestion | None:
    config = session.config or {}
    queue = list(config.get("queue", []))
    index = int(config.get("index", 0))
    if index >= len(queue):
        return None

    language_code = str(config.get("language", "FR"))
    language = await get_language_by_code(db, language_code)
    selected_tenses = list(config.get("selected_tenses", []))

    verb_id = queue[index]
    verb_result = await db.execute(select(Verb).where(Verb.id == verb_id))
    verb = verb_result.scalar_one()

    table = await _conjugation_table_for_verb(
        db,
        verb_id=verb_id,
        language=language,
        selected_tenses=selected_tenses,
    )

    fill_level = str(config.get("fill_level", "easy"))
    prefill: dict[str, dict[str, bool]] = {}
    for tense in selected_tenses:
        pronouns = list(language.pronoun_set or [])
        valid_pronouns = [pronoun for pronoun in pronouns if table[tense].get(pronoun, "-") != "-"]
        unique_forms = {
            table[tense][pronoun].strip().casefold()
            for pronoun in valid_pronouns
        }
        giveaway_tense = len(valid_pronouns) <= 1 or len(unique_forms) <= 1

        guide_count = 0
        if not giveaway_tense and fill_level == "medium":
            guide_count = 1
        elif not giveaway_tense and fill_level == "easy":
            guide_count = min(len(valid_pronouns) - 1, int(len(valid_pronouns) * 0.7))

        indexed_pronouns = {pronoun: index for index, pronoun in enumerate(pronouns)}
        guide_order = sorted(
            valid_pronouns,
            key=lambda pronoun: (
                verb_id * 31
                + len(tense) * 13
                + indexed_pronouns[pronoun] * 17
            )
            % 101,
        )
        guides = set(guide_order[:guide_count])
        prefill[tense] = {
            pronoun: pronoun in guides
            for pronoun in pronouns
        }

    return ConjugationQuestion(
        verb_id=verb_id,
        verb=verb.infinitive,
        selected_tenses=selected_tenses,
        table=table,
        prefill=prefill,
        pronouns=list(language.pronoun_set or []),
    )


async def _unlock_next_conjugation_verbs(
    db: AsyncSession,
    *,
    user_id: int,
    language_pair: str,
    language_code: str,
    selected_tenses: list[str],
    count: int = 3,
) -> int:
    current_rows = await db.execute(
        select(UserProgress)
        .where(
            UserProgress.user_id == user_id,
            UserProgress.item_type == ProgressItemType.CONJUGATION,
            UserProgress.language_pair == language_pair,
        )
    )
    unlocked_ids = {row.item_id for row in current_rows.scalars().all() if row.unlocked}

    language = await get_language_by_code(db, language_code)
    eligible_ids = await eligible_conjugation_verb_ids(
        db,
        language=language,
        selected_tenses=selected_tenses,
    )

    created = 0
    for verb_id in (item_id for item_id in eligible_ids if item_id not in unlocked_ids):
        if created >= count:
            break
        await _get_or_create_progress(
            db,
            user_id=user_id,
            item_type=ProgressItemType.CONJUGATION,
            item_id=verb_id,
            language_pair=language_pair,
            unlocked=True,
        )
        created += 1
    return created


async def maybe_unlock_conjugation_verbs(
    db: AsyncSession,
    *,
    user_id: int,
    language_pair: str,
    language_code: str,
    selected_tenses: list[str],
) -> int:
    rows = await db.execute(
        select(UserProgress)
        .where(
            UserProgress.user_id == user_id,
            UserProgress.item_type == ProgressItemType.CONJUGATION,
            UserProgress.language_pair == language_pair,
            UserProgress.times_seen > 0,
        )
        .order_by(UserProgress.probability.desc())
        .limit(5)
    )
    weakest = rows.scalars().all()
    if len(weakest) < 5:
        return 0

    avg = sum(row.probability for row in weakest) / len(weakest)
    if avg >= 700:
        return 0

    return await _unlock_next_conjugation_verbs(
        db,
        user_id=user_id,
        language_pair=language_pair,
        language_code=language_code,
        selected_tenses=selected_tenses,
    )


def _conjugation_tense_review(
    *,
    question: ConjugationQuestion,
    language_code: str,
    tense: str,
    answers: dict[str, str],
) -> dict[str, Any]:
    cells: list[dict[str, Any]] = []
    correct_count = 0
    answer_count = 0

    for pronoun in question.pronouns:
        user_answer = (answers.get(pronoun) or "").strip()
        correct_answer = question.table[tense].get(pronoun, "-")
        if correct_answer == "-":
            cells.append(
                {
                    "pronoun": pronoun,
                    "kind": "missing",
                    "answer": "",
                    "expected": "-",
                    "correct": None,
                }
            )
            continue
        if question.prefill[tense].get(pronoun, False):
            cells.append(
                {
                    "pronoun": pronoun,
                    "kind": "prefilled",
                    "answer": correct_answer,
                    "expected": correct_answer,
                    "correct": True,
                }
            )
            continue

        is_correct = conjugation_answer_is_correct(user_answer, correct_answer, language_code)
        answer_count += 1
        correct_count += int(is_correct)
        cells.append(
            {
                "pronoun": pronoun,
                "kind": "answer",
                "answer": user_answer,
                "expected": correct_answer,
                "correct": is_correct,
            }
        )

    accuracy = (correct_count / answer_count * 100.0) if answer_count else 0.0
    return {
        "verb_id": question.verb_id,
        "verb": question.verb,
        "tense": tense,
        "correct": correct_count,
        "total": answer_count,
        "accuracy": round(accuracy, 1),
        "cells": cells,
    }


async def check_conjugation_tense(
    db: AsyncSession,
    *,
    session: TrainingSession,
    tense: str,
    answers: dict[str, str],
) -> dict[str, Any]:
    question = await get_conjugation_question(db, session)
    if question is None:
        raise ValueError("Conjugation session is complete.")
    if tense not in question.selected_tenses:
        raise ValueError(f"Tense is not part of this table: {tense}")

    config = dict(session.config or {})
    stored_reviews = dict(config.get("conjugation_tense_reviews", {}))
    existing_review = stored_reviews.get(tense)
    if isinstance(existing_review, dict):
        return dict(existing_review)

    checked_tenses = [
        item
        for item in config.get("checked_conjugation_tenses", [])
        if item in question.selected_tenses
    ]
    next_tense = next(
        (item for item in question.selected_tenses if item not in checked_tenses),
        None,
    )
    if next_tense != tense:
        raise ValueError("Complete the conjugation tenses in order.")

    language_code = str(config.get("language", "FR"))
    frozen_answers = {
        pronoun: (answers.get(pronoun) or "").strip()
        for pronoun in question.pronouns
    }
    review = _conjugation_tense_review(
        question=question,
        language_code=language_code,
        tense=tense,
        answers=frozen_answers,
    )

    pending_answers = dict(config.get("pending_conjugation_answers", {}))
    pending_answers[tense] = frozen_answers
    checked_tenses.append(tense)
    stored_reviews[tense] = review
    config["pending_conjugation_answers"] = pending_answers
    config["checked_conjugation_tenses"] = checked_tenses
    config["conjugation_tense_reviews"] = stored_reviews
    session.config = config
    return review


async def submit_conjugation_answers(
    db: AsyncSession,
    *,
    session: TrainingSession,
    profile: UserProfile,
    answers: dict[str, dict[str, str]],
) -> dict[str, Any]:
    question = await get_conjugation_question(db, session)
    if question is None:
        return {"finished": True, "feedback": "Session complete."}

    config = dict(session.config or {})
    language_code = str(config.get("language", "FR"))
    language_pair = session.language_pair
    scored_conjugation_slots = _str_set_from_config(config, "scored_conjugation_slots")
    effective_answers = {
        tense: dict(tense_answers)
        for tense, tense_answers in answers.items()
        if isinstance(tense_answers, dict)
    }
    for tense, tense_answers in dict(config.get("pending_conjugation_answers", {})).items():
        if isinstance(tense_answers, dict):
            effective_answers[str(tense)] = {
                str(pronoun): str(answer)
                for pronoun, answer in tense_answers.items()
            }
    answers = effective_answers

    progress = await _get_or_create_progress(
        db,
        user_id=session.user_id,
        item_type=ProgressItemType.CONJUGATION,
        item_id=question.verb_id,
        language_pair=language_pair,
        unlocked=True,
    )

    extra_data = dict(progress.extra_data or {})
    tense_scores = dict(extra_data.get("tense_scores", {}))

    total_correct = 0
    total_answered = 0
    review_by_slot: dict[tuple[str, str], dict[str, Any]] = {}

    for tense in question.selected_tenses:
        tense_answers = answers.get(tense, {})
        checks: list[PronounCheck] = []
        scored_checks: list[PronounCheck] = []
        applied_slot_keys: set[str] = set()

        for pronoun in question.pronouns:
            user_answer = (tense_answers.get(pronoun) or "").strip()
            correct_answer = question.table[tense].get(pronoun, "-")
            if correct_answer == "-":
                review_by_slot[(tense, pronoun)] = {
                    "kind": "missing",
                    "answer": "",
                    "expected": "-",
                    "correct": None,
                }
                continue
            if question.prefill[tense].get(pronoun, False):
                review_by_slot[(tense, pronoun)] = {
                    "kind": "prefilled",
                    "answer": correct_answer,
                    "expected": correct_answer,
                    "correct": True,
                }
                continue

            is_correct = conjugation_answer_is_correct(user_answer, correct_answer, language_code)
            review_by_slot[(tense, pronoun)] = {
                "kind": "answer",
                "answer": user_answer,
                "expected": correct_answer,
                "correct": is_correct,
            }
            checks.append(
                PronounCheck(
                    pronoun=pronoun,
                    user_answer=user_answer,
                    correct_answer=correct_answer,
                    is_correct=is_correct,
                )
            )
            slot_key = _conjugation_slot_key(verb_id=question.verb_id, tense=tense, pronoun=pronoun)
            if slot_key not in scored_conjugation_slots:
                scored_checks.append(checks[-1])
                applied_slot_keys.add(slot_key)

        if not checks:
            continue

        current_tense_score = float(tense_scores.get(tense, 1000.0))
        multiplier_applied = 1.0
        if scored_checks:
            result = update_tense_score(current_tense_score, scored_checks)
            tense_scores[tense] = result.new_tense_score
            multiplier_applied = result.multiplier
            scored_conjugation_slots.update(applied_slot_keys)

        correct_count = sum(1 for check in checks if check.is_correct)
        total_correct += correct_count
        total_answered += len(checks)

        db.add(
            SessionItem(
                session_id=session.id,
                item_type=ProgressItemType.CONJUGATION,
                item_id=question.verb_id,
                prompt=f"{question.verb} - {tense}",
                answer=str({check.pronoun: check.user_answer for check in checks}),
                expected=str({check.pronoun: check.correct_answer for check in checks}),
                correct=correct_count == len(checks),
                multiplier_applied=multiplier_applied,
                meta={
                    "tense": tense,
                    "score_applied": bool(applied_slot_keys),
                    "checks": [
                        {
                            **asdict(check),
                            "slot_key": _conjugation_slot_key(
                                verb_id=question.verb_id,
                                tense=tense,
                                pronoun=check.pronoun,
                            ),
                            "score_applied": _conjugation_slot_key(
                                verb_id=question.verb_id,
                                tense=tense,
                                pronoun=check.pronoun,
                            )
                            in applied_slot_keys,
                        }
                        for check in checks
                    ],
                },
            )
        )

    progress.times_seen += max(1, total_answered)
    progress.times_correct += total_correct
    progress.last_seen = datetime.now(timezone.utc)
    extra_data["tense_scores"] = tense_scores
    progress.extra_data = extra_data

    if tense_scores:
        progress.probability = sum(float(score) for score in tense_scores.values()) / len(tense_scores)

    reward = _update_combo(config, succeeded=total_answered > 0 and total_correct == total_answered)
    update_streak(profile, date.today())
    if total_correct > 0:
        reward = merge_reward_summaries(
            reward,
            await grant_xp(
                db,
                profile=profile,
                points=total_correct * 5,
                reason="conjugation_correct_cells",
                meta={"verb_id": question.verb_id, "correct": total_correct},
            ),
            await track_weekly_metric(
                db,
                user_id=session.user_id,
                metric_key="conjugation_cells_correct",
                delta=total_correct,
                profile=profile,
            ),
        )
    if total_answered > 0 and total_correct == total_answered:
        reward = merge_reward_summaries(
            reward,
            await grant_xp(
                db,
                profile=profile,
                points=50,
                reason="conjugation_perfect_table",
                meta={"verb_id": question.verb_id},
            ),
        )

    _store_config_str_set(config, "scored_conjugation_slots", scored_conjugation_slots)
    config.pop("checked_conjugation_tenses", None)
    config.pop("pending_conjugation_answers", None)
    config.pop("conjugation_tense_reviews", None)
    config["index"] = int(config.get("index", 0)) + 1
    session.config = config

    queue = list(config.get("queue", []))
    finished = int(config.get("index", 0)) >= len(queue)
    if finished:
        session.completed_at = datetime.now(timezone.utc)
        session.score = await _count_session_accuracy(db, session.id)
        reward = merge_reward_summaries(
            reward,
            await grant_xp(
                db,
                profile=profile,
                points=25,
                reason="session_complete",
                meta={"mode": session.mode.value},
            ),
            await track_weekly_metric(
                db,
                user_id=session.user_id,
                metric_key="completed_sessions",
                delta=1,
                profile=profile,
            ),
        )
        if session.score >= 100:
            reward = merge_reward_summaries(
                reward,
                await track_weekly_metric(
                    db,
                    user_id=session.user_id,
                    metric_key="perfect_sessions",
                    delta=1,
                    profile=profile,
                ),
            )
        await maybe_unlock_conjugation_verbs(
            db,
            user_id=session.user_id,
            language_pair=language_pair,
            language_code=language_code,
            selected_tenses=question.selected_tenses,
        )

    accuracy = (total_correct / total_answered * 100.0) if total_answered else 0.0
    review_rows = [
        {
            "pronoun": pronoun,
            "cells": [
                {
                    "tense": tense,
                    **review_by_slot.get(
                        (tense, pronoun),
                        {"kind": "missing", "answer": "", "expected": "-", "correct": None},
                    ),
                }
                for tense in question.selected_tenses
            ],
        }
        for pronoun in question.pronouns
    ]
    reward.unlocked_badges.extend(await unlock_badges(db, user_id=session.user_id, profile=profile))
    return {
        "finished": finished,
        "accuracy": round(accuracy, 1),
        "correct": total_correct,
        "total": total_answered,
        "session_score": round(float(session.score), 1) if finished and session.score is not None else None,
        "session_length": len(queue),
        "best_combo": int(config.get("best_combo", 0)),
        "language_pair": language_pair,
        "review": {
            "verb_id": question.verb_id,
            "verb": question.verb,
            "selected_tenses": question.selected_tenses,
            "rows": review_rows,
        },
        "gamification": reward_summary_payload(reward),
    }


def build_conjugation_answers_from_form(form_data: dict[str, str]) -> dict[str, dict[str, str]]:
    answers: dict[str, dict[str, str]] = {}
    for key, value in form_data.items():
        if not key.startswith("ans__"):
            continue
        _, tense, pronoun = key.split("__", 2)
        answers.setdefault(tense, {})[pronoun] = value
    return answers


def conjugation_tenses_for_level(language: Language, level: str, selected_tenses: list[str] | None) -> list[str]:
    available = list((language.tense_definitions or {}).keys())
    if level == "custom":
        requested = list(dict.fromkeys(selected_tenses or []))
        invalid = [tense for tense in requested if tense not in available]
        if invalid:
            raise ValueError(f"Unsupported tense for {language.name}: {invalid[0]}")
        chosen = [tense for tense in available if tense in requested]
        if not chosen:
            raise ValueError("Choose at least one tense for a custom session.")
        return chosen

    if level not in {"easy", "medium", "hard"}:
        raise ValueError(f"Unsupported conjugation level: {level}")
    chosen = [tense for tense in tenses_for_level(language.__dict__, level) if tense in available]
    if not chosen:
        raise ValueError(f"No tenses are configured for {language.name} at this level.")
    return chosen
