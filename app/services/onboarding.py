"""First-run onboarding state.

Drills unlock in a fixed chain — Words, then Add Word, then verb translation,
then verb tables — with one escape hatch that opens everything at once. The
whole mechanism runs off a single JSON blob on ``user_preferences``.

The chain here must stay in step with ``frontend/src/lib/components/onboarding/
onboarding.ts``; the server is the authority, the client mirrors it so it can
render locks without a round trip.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TrainingMode, TrainingSession, UserAddedWord, UserPreference

# Ordered: each entry unlocks the next.
FEATURE_CHAIN: tuple[str, ...] = ("words", "add-word", "verb-translate", "verb-tables")
FEATURE_SET = frozenset(FEATURE_CHAIN)

TOUR_IDS: frozenset[str] = frozenset({"intro", *FEATURE_CHAIN})


def empty_state() -> dict[str, Any]:
    return {"completed": [], "seenTours": [], "skipped": False}


def normalize(raw: Any) -> dict[str, Any]:
    """Coerce a stored blob into the shape the rest of the app expects."""
    if not isinstance(raw, dict):
        return empty_state()

    completed_raw = raw.get("completed")
    completed = (
        [item for item in completed_raw if item in FEATURE_SET] if isinstance(completed_raw, list) else []
    )
    # Keep chain order regardless of how it was written.
    completed = [feature for feature in FEATURE_CHAIN if feature in completed]

    seen_raw = raw.get("seenTours")
    seen = [item for item in seen_raw if item in TOUR_IDS] if isinstance(seen_raw, list) else []

    return {
        "completed": completed,
        "seenTours": seen,
        "skipped": raw.get("skipped") is True,
    }


def is_unlocked(state: dict[str, Any], feature: str) -> bool:
    if feature not in FEATURE_SET:
        return True
    if state.get("skipped") is True:
        return True
    index = FEATURE_CHAIN.index(feature)
    if index == 0:
        return True
    return FEATURE_CHAIN[index - 1] in state.get("completed", [])


def unlocked_features(state: dict[str, Any]) -> list[str]:
    return [feature for feature in FEATURE_CHAIN if is_unlocked(state, feature)]


async def _derive_completed(db: AsyncSession, *, user_id: int) -> list[str]:
    """Work out what a user has already done, for accounts older than this feature.

    Without this an established user would be sent back to square one and find
    three of their four drills locked.
    """
    mode_for = {
        "words": TrainingMode.WORD_TRANSLATION,
        "verb-translate": TrainingMode.VERB_TRANSLATION,
        "verb-tables": TrainingMode.CONJUGATION,
    }

    done: list[str] = []
    for feature, mode in mode_for.items():
        count = (
            await db.execute(
                select(func.count(TrainingSession.id)).where(
                    TrainingSession.user_id == user_id,
                    TrainingSession.mode == mode,
                    TrainingSession.completed_at.is_not(None),
                )
            )
        ).scalar_one()
        if count:
            done.append(feature)

    added = (
        await db.execute(
            select(func.count(UserAddedWord.id)).where(UserAddedWord.user_id == user_id)
        )
    ).scalar_one()
    if added:
        done.append("add-word")

    return [feature for feature in FEATURE_CHAIN if feature in done]


async def load_state(
    db: AsyncSession, *, user_id: int, preference: UserPreference | None
) -> dict[str, Any]:
    """Return the user's onboarding state, seeding it from history on first read."""
    stored = preference.onboarding if preference else None
    if isinstance(stored, dict) and stored:
        return normalize(stored)

    # Nothing stored yet: infer from what they have already done.
    state = empty_state()
    state["completed"] = await _derive_completed(db, user_id=user_id)
    if preference is not None:
        preference.onboarding = state
        await db.flush()
    return state


FEATURE_BY_TRAINING_MODE: dict[TrainingMode, str] = {
    TrainingMode.WORD_TRANSLATION: "words",
    TrainingMode.VERB_TRANSLATION: "verb-translate",
    TrainingMode.CONJUGATION: "verb-tables",
}


async def mark_feature_complete(db: AsyncSession, *, user_id: int, feature: str) -> None:
    """Record a drill as done from the server side.

    Called where the thing actually happens — a session reaching its end, a word
    being saved — so the unlock cannot be faked by a client that never sends the
    PATCH, and cannot be lost by one that crashes before it does.
    """
    if feature not in FEATURE_SET:
        return

    row = await db.execute(select(UserPreference).where(UserPreference.user_id == user_id))
    preference = row.scalar_one_or_none()
    if preference is None:
        return

    state = normalize(preference.onboarding)
    if feature in state["completed"]:
        return

    state["completed"] = [
        entry for entry in FEATURE_CHAIN if entry in {*state["completed"], feature}
    ]
    preference.onboarding = state
    await db.flush()


async def save_state(
    db: AsyncSession, *, preference: UserPreference, patch: dict[str, Any]
) -> dict[str, Any]:
    """Merge a client patch over the stored state and persist it."""
    current = normalize(preference.onboarding)

    if isinstance(patch.get("completed"), list):
        merged = set(current["completed"]) | {
            item for item in patch["completed"] if item in FEATURE_SET
        }
        current["completed"] = [feature for feature in FEATURE_CHAIN if feature in merged]

    if isinstance(patch.get("seenTours"), list):
        merged_tours = set(current["seenTours"]) | {
            item for item in patch["seenTours"] if item in TOUR_IDS
        }
        current["seenTours"] = sorted(merged_tours)

    if isinstance(patch.get("skipped"), bool):
        current["skipped"] = patch["skipped"]

    if patch.get("reset") is True:
        current = empty_state()

    preference.onboarding = current
    await db.flush()
    return current
