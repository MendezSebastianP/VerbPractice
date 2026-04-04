from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    BadgeDefinition,
    BadgeRarity,
    FriendLink,
    ProgressItemType,
    TrainingSession,
    User,
    UserBadge,
    UserChallengeProgress,
    UserPreference,
    UserProfile,
    UserProgress,
    WeeklyChallenge,
    XPEvent,
)


@dataclass(slots=True)
class XPAwardResult:
    gained_xp: int
    old_level: int
    new_level: int
    leveled_up: bool


@dataclass(slots=True)
class RewardSummary:
    gained_xp: int = 0
    old_level: int = 1
    new_level: int = 1
    leveled_up: bool = False
    unlocked_badges: list[dict[str, Any]] = field(default_factory=list)
    challenge: dict[str, Any] | None = None
    combo: int | None = None
    best_combo: int | None = None


BADGE_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "code": "first_steps",
        "title": "First Steps",
        "description": "Complete your first training session.",
        "icon": "sprout",
        "rarity": BadgeRarity.COMMON,
        "metric_key": "completed_sessions",
        "threshold": 1,
    },
    {
        "code": "week_flame",
        "title": "Week Flame",
        "description": "Keep a 7-day streak alive.",
        "icon": "flame",
        "rarity": BadgeRarity.RARE,
        "metric_key": "streak_days",
        "threshold": 7,
    },
    {
        "code": "perfect_form",
        "title": "Perfect Form",
        "description": "Finish three sessions at 100% accuracy.",
        "icon": "star",
        "rarity": BadgeRarity.RARE,
        "metric_key": "perfect_sessions",
        "threshold": 3,
    },
    {
        "code": "lex_foundry",
        "title": "Lex Foundry",
        "description": "Master 25 word items.",
        "icon": "forge",
        "rarity": BadgeRarity.EPIC,
        "metric_key": "words_mastered",
        "threshold": 25,
    },
    {
        "code": "tense_tamer",
        "title": "Tense Tamer",
        "description": "Master 10 conjugation items.",
        "icon": "grid",
        "rarity": BadgeRarity.EPIC,
        "metric_key": "conjugations_mastered",
        "threshold": 10,
    },
)


WEEKLY_CHALLENGE_ROTATION: tuple[dict[str, Any], ...] = (
    {
        "metric_key": "completed_sessions",
        "title": "Session Sprint",
        "description": "Complete 5 training sessions this week.",
        "icon": "flag",
        "target_value": 5,
        "reward_xp": 120,
    },
    {
        "metric_key": "translation_correct",
        "title": "Precision Pulse",
        "description": "Score 30 correct translation answers this week.",
        "icon": "bolt",
        "target_value": 30,
        "reward_xp": 130,
    },
    {
        "metric_key": "conjugation_cells_correct",
        "title": "Table Sweep",
        "description": "Land 36 correct conjugation cells this week.",
        "icon": "matrix",
        "target_value": 36,
        "reward_xp": 145,
    },
    {
        "metric_key": "perfect_sessions",
        "title": "Clean Sheet",
        "description": "Finish 2 perfect sessions this week.",
        "icon": "spark",
        "target_value": 2,
        "reward_xp": 160,
    },
)


def xp_for_level(level: int) -> int:
    if level <= 1:
        return 0
    return int(50 * (level**1.8))


def level_from_xp(total_xp: int) -> int:
    level = 1
    while xp_for_level(level + 1) <= total_xp:
        level += 1
    return level


def update_streak(profile: UserProfile, today: date) -> None:
    if profile.last_active_date is None:
        profile.last_active_date = today
        profile.streak_days = 1
        return

    if profile.last_active_date == today:
        return

    if profile.last_active_date == today - timedelta(days=1):
        profile.streak_days += 1
    else:
        profile.streak_days = 1

    profile.last_active_date = today


def award_xp(profile: UserProfile, points: int) -> XPAwardResult:
    points = max(0, points)
    old_level = profile.level
    profile.xp += points
    profile.level = level_from_xp(profile.xp)
    return XPAwardResult(
        gained_xp=points,
        old_level=old_level,
        new_level=profile.level,
        leveled_up=profile.level > old_level,
    )


def merge_reward_summaries(*rewards: RewardSummary | None) -> RewardSummary:
    merged = RewardSummary()
    seen_level = False
    for reward in rewards:
        if reward is None:
            continue
        merged.gained_xp += reward.gained_xp
        if reward.gained_xp > 0 or reward.leveled_up:
            if not seen_level:
                merged.old_level = reward.old_level
                merged.new_level = reward.new_level
                seen_level = True
            else:
                merged.old_level = min(merged.old_level, reward.old_level)
                merged.new_level = max(merged.new_level, reward.new_level)
        merged.leveled_up = merged.leveled_up or reward.leveled_up
        merged.unlocked_badges.extend(reward.unlocked_badges)
        if reward.challenge is not None:
            merged.challenge = reward.challenge
        if reward.combo is not None:
            merged.combo = reward.combo
        if reward.best_combo is not None:
            merged.best_combo = reward.best_combo
    if not seen_level:
        merged.old_level = merged.new_level
    elif merged.new_level < merged.old_level:
        merged.old_level = merged.new_level
    return merged


async def ensure_user_preference(db: AsyncSession, user_id: int) -> UserPreference:
    existing = await db.execute(select(UserPreference).where(UserPreference.user_id == user_id))
    preference = existing.scalar_one_or_none()
    if preference is not None:
        return preference

    preference = UserPreference(user_id=user_id, sound_enabled=False)
    db.add(preference)
    await db.flush()
    return preference


async def ensure_badge_catalog(db: AsyncSession) -> None:
    existing_rows = await db.execute(select(BadgeDefinition.code))
    existing_codes = {row[0] for row in existing_rows.all()}
    for badge in BADGE_CATALOG:
        if badge["code"] in existing_codes:
            continue
        db.add(BadgeDefinition(**badge))
    await db.flush()


def current_week_window(today: date | None = None) -> tuple[date, date]:
    today = today or date.today()
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    return start, end


async def ensure_weekly_challenge(db: AsyncSession, today: date | None = None) -> WeeklyChallenge:
    today = today or date.today()
    start, end = current_week_window(today)
    iso_year, iso_week, _ = today.isocalendar()
    template = WEEKLY_CHALLENGE_ROTATION[(iso_week - 1) % len(WEEKLY_CHALLENGE_ROTATION)]
    slug = f"week-{iso_year}-w{iso_week:02d}-{template['metric_key']}"

    existing = await db.execute(select(WeeklyChallenge).where(WeeklyChallenge.slug == slug))
    challenge = existing.scalar_one_or_none()
    if challenge is not None:
        if not challenge.active:
            challenge.active = True
        return challenge

    active_rows = await db.execute(select(WeeklyChallenge).where(WeeklyChallenge.active.is_(True)))
    for row in active_rows.scalars().all():
        row.active = False

    challenge = WeeklyChallenge(
        slug=slug,
        title=template["title"],
        description=template["description"],
        icon=template["icon"],
        metric_key=template["metric_key"],
        target_value=template["target_value"],
        reward_xp=template["reward_xp"],
        starts_at=start,
        ends_at=end,
        active=True,
    )
    db.add(challenge)
    await db.flush()
    return challenge


async def ensure_gamification_catalog(db: AsyncSession) -> None:
    await ensure_badge_catalog(db)
    await ensure_weekly_challenge(db)


def serialize_badge(definition: BadgeDefinition, unlocked_at: datetime | None = None) -> dict[str, Any]:
    return {
        "code": definition.code,
        "title": definition.title,
        "description": definition.description,
        "icon": definition.icon,
        "rarity": definition.rarity.value if isinstance(definition.rarity, BadgeRarity) else str(definition.rarity),
        "unlocked_at": unlocked_at.isoformat() if unlocked_at else None,
    }


def serialize_challenge(challenge: WeeklyChallenge, progress: UserChallengeProgress | None) -> dict[str, Any]:
    progress_value = progress.progress if progress else 0
    return {
        "slug": challenge.slug,
        "title": challenge.title,
        "description": challenge.description,
        "icon": challenge.icon,
        "metric_key": challenge.metric_key,
        "target_value": challenge.target_value,
        "reward_xp": challenge.reward_xp,
        "starts_at": challenge.starts_at.isoformat(),
        "ends_at": challenge.ends_at.isoformat(),
        "progress": min(progress_value, challenge.target_value),
        "completed": bool(progress and progress.completed_at),
        "completed_at": progress.completed_at.isoformat() if progress and progress.completed_at else None,
    }


def reward_summary_payload(reward: RewardSummary) -> dict[str, Any]:
    return {
        "gained_xp": reward.gained_xp,
        "old_level": reward.old_level,
        "new_level": reward.new_level,
        "leveled_up": reward.leveled_up,
        "unlocked_badges": reward.unlocked_badges,
        "challenge": reward.challenge,
        "combo": reward.combo,
        "best_combo": reward.best_combo,
    }


async def grant_xp(
    db: AsyncSession,
    *,
    profile: UserProfile,
    points: int,
    reason: str,
    meta: dict[str, Any] | None = None,
) -> RewardSummary:
    result = award_xp(profile, points)
    db.add(
        XPEvent(
            user_id=profile.user_id,
            amount=result.gained_xp,
            reason=reason,
            meta=meta or {},
        )
    )
    await db.flush()
    return RewardSummary(
        gained_xp=result.gained_xp,
        old_level=result.old_level,
        new_level=result.new_level,
        leveled_up=result.leveled_up,
    )


async def _metric_snapshot(db: AsyncSession, *, user_id: int, profile: UserProfile) -> dict[str, int]:
    completed_sessions = (
        await db.execute(
            select(func.count(TrainingSession.id)).where(
                TrainingSession.user_id == user_id,
                TrainingSession.completed_at.is_not(None),
            )
        )
    ).scalar_one()
    perfect_sessions = (
        await db.execute(
            select(func.count(TrainingSession.id)).where(
                TrainingSession.user_id == user_id,
                TrainingSession.completed_at.is_not(None),
                TrainingSession.score >= 100,
            )
        )
    ).scalar_one()
    words_mastered = (
        await db.execute(
            select(func.count(UserProgress.id)).where(
                UserProgress.user_id == user_id,
                UserProgress.item_type == ProgressItemType.WORD,
                UserProgress.probability <= 200,
            )
        )
    ).scalar_one()
    conjugations_mastered = (
        await db.execute(
            select(func.count(UserProgress.id)).where(
                UserProgress.user_id == user_id,
                UserProgress.item_type == ProgressItemType.CONJUGATION,
                UserProgress.probability <= 250,
            )
        )
    ).scalar_one()
    start_of_week = datetime.combine(current_week_window()[0], time.min, tzinfo=timezone.utc)
    weekly_xp = (
        await db.execute(
            select(func.coalesce(func.sum(XPEvent.amount), 0)).where(
                XPEvent.user_id == user_id,
                XPEvent.created_at >= start_of_week,
            )
        )
    ).scalar_one()

    return {
        "completed_sessions": int(completed_sessions),
        "perfect_sessions": int(perfect_sessions),
        "words_mastered": int(words_mastered),
        "conjugations_mastered": int(conjugations_mastered),
        "streak_days": int(profile.streak_days),
        "weekly_xp": int(weekly_xp or 0),
    }


async def unlock_badges(db: AsyncSession, *, user_id: int, profile: UserProfile) -> list[dict[str, Any]]:
    await ensure_badge_catalog(db)

    unlocked_codes = {
        row[0]
        for row in (
            await db.execute(select(UserBadge.badge_code).where(UserBadge.user_id == user_id))
        ).all()
    }
    metrics = await _metric_snapshot(db, user_id=user_id, profile=profile)
    definitions = (
        await db.execute(select(BadgeDefinition).where(BadgeDefinition.active.is_(True)).order_by(BadgeDefinition.code.asc()))
    ).scalars().all()

    new_badges: list[dict[str, Any]] = []
    for definition in definitions:
        if definition.code in unlocked_codes:
            continue
        if metrics.get(definition.metric_key, 0) < definition.threshold:
            continue
        badge = UserBadge(user_id=user_id, badge_code=definition.code)
        db.add(badge)
        await db.flush()
        new_badges.append(serialize_badge(definition, badge.unlocked_at))
    return new_badges


async def track_weekly_metric(
    db: AsyncSession,
    *,
    user_id: int,
    metric_key: str,
    delta: int,
    profile: UserProfile,
) -> RewardSummary | None:
    if delta <= 0:
        return None

    challenge = await ensure_weekly_challenge(db)
    if challenge.metric_key != metric_key:
        existing = (
            await db.execute(
                select(UserChallengeProgress).where(
                    UserChallengeProgress.user_id == user_id,
                    UserChallengeProgress.challenge_id == challenge.id,
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            return RewardSummary(challenge=serialize_challenge(challenge, None))
        return RewardSummary(challenge=serialize_challenge(challenge, existing))

    progress = (
        await db.execute(
            select(UserChallengeProgress).where(
                UserChallengeProgress.user_id == user_id,
                UserChallengeProgress.challenge_id == challenge.id,
            )
        )
    ).scalar_one_or_none()
    if progress is None:
        progress = UserChallengeProgress(user_id=user_id, challenge_id=challenge.id, progress=0)
        db.add(progress)
        await db.flush()

    progress.progress = min(challenge.target_value, progress.progress + delta)
    reward = RewardSummary(challenge=serialize_challenge(challenge, progress))
    if progress.progress >= challenge.target_value and progress.completed_at is None:
        progress.completed_at = datetime.now(timezone.utc)
        if not progress.reward_claimed:
            progress.reward_claimed = True
            reward = merge_reward_summaries(
                reward,
                await grant_xp(
                    db,
                    profile=profile,
                    points=challenge.reward_xp,
                    reason="weekly_challenge",
                    meta={"challenge": challenge.slug},
                ),
            )
        reward.challenge = serialize_challenge(challenge, progress)
    return reward


async def build_combo_reward(
    db: AsyncSession,
    *,
    user_id: int,
    combo: int,
    best_combo: int,
    profile: UserProfile,
) -> RewardSummary:
    reward = RewardSummary(combo=combo, best_combo=best_combo)
    if combo >= 5:
        challenge_reward = await track_weekly_metric(
            db,
            user_id=user_id,
            metric_key="combo_peak",
            delta=combo,
            profile=profile,
        )
        reward = merge_reward_summaries(reward, challenge_reward)
    return reward


async def gamification_snapshot(db: AsyncSession, *, user: User, profile: UserProfile) -> dict[str, Any]:
    await ensure_gamification_catalog(db)
    preference = await ensure_user_preference(db, user.id)
    challenge = await ensure_weekly_challenge(db)
    challenge_progress = (
        await db.execute(
            select(UserChallengeProgress).where(
                UserChallengeProgress.user_id == user.id,
                UserChallengeProgress.challenge_id == challenge.id,
            )
        )
    ).scalar_one_or_none()

    badge_rows = (
        await db.execute(
            select(UserBadge, BadgeDefinition)
            .join(BadgeDefinition, BadgeDefinition.code == UserBadge.badge_code)
            .where(UserBadge.user_id == user.id)
            .order_by(UserBadge.unlocked_at.desc())
        )
    ).all()
    badges = [serialize_badge(definition, badge.unlocked_at) for badge, definition in badge_rows]

    global_rows = (
        await db.execute(
            select(User, UserProfile)
            .join(UserProfile, UserProfile.user_id == User.id)
            .order_by(UserProfile.xp.desc(), User.username.asc())
            .limit(10)
        )
    ).all()
    global_leaderboard = [
        {
            "username": entry_user.username,
            "level": entry_profile.level,
            "xp": entry_profile.xp,
            "streak_days": entry_profile.streak_days,
        }
        for entry_user, entry_profile in global_rows
    ]

    weekly_start = datetime.combine(current_week_window()[0], time.min, tzinfo=timezone.utc)
    weekly_rows = (
        await db.execute(
            select(User.username, func.coalesce(func.sum(XPEvent.amount), 0).label("weekly_xp"))
            .join(User, User.id == XPEvent.user_id)
            .where(XPEvent.created_at >= weekly_start)
            .group_by(User.id, User.username)
            .order_by(func.coalesce(func.sum(XPEvent.amount), 0).desc(), User.username.asc())
            .limit(10)
        )
    ).all()
    weekly_leaderboard = [
        {"username": username, "weekly_xp": int(weekly_xp or 0)}
        for username, weekly_xp in weekly_rows
    ]

    friend_rows = (
        await db.execute(
            select(User.id, User.username)
            .join(FriendLink, FriendLink.friend_user_id == User.id)
            .where(FriendLink.user_id == user.id)
            .order_by(User.username.asc())
        )
    ).all()
    friend_ids = [row[0] for row in friend_rows]
    circle_ids = [user.id, *friend_ids]
    circle_rows = (
        await db.execute(
            select(User, UserProfile)
            .join(UserProfile, UserProfile.user_id == User.id)
            .where(User.id.in_(circle_ids))
            .order_by(UserProfile.xp.desc(), User.username.asc())
        )
    ).all()
    circle_leaderboard = [
        {
            "user_id": entry_user.id,
            "username": entry_user.username,
            "level": entry_profile.level,
            "xp": entry_profile.xp,
        }
        for entry_user, entry_profile in circle_rows
    ]

    recent_xp_rows = (
        await db.execute(
            select(XPEvent)
            .where(XPEvent.user_id == user.id)
            .order_by(XPEvent.created_at.desc())
            .limit(8)
        )
    ).scalars().all()

    return {
        "sound_enabled": preference.sound_enabled,
        "badges": badges,
        "weekly_challenge": serialize_challenge(challenge, challenge_progress),
        "global_leaderboard": global_leaderboard,
        "weekly_leaderboard": weekly_leaderboard,
        "circle": {
            "friends": [{"user_id": friend_id, "username": username} for friend_id, username in friend_rows],
            "leaderboard": circle_leaderboard,
        },
        "recent_xp": [
            {
                "amount": row.amount,
                "reason": row.reason,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in recent_xp_rows
        ],
    }


async def set_sound_enabled(db: AsyncSession, *, user_id: int, sound_enabled: bool) -> UserPreference:
    preference = await ensure_user_preference(db, user_id)
    preference.sound_enabled = sound_enabled
    await db.flush()
    return preference


async def add_circle_friend(db: AsyncSession, *, user_id: int, username: str) -> User:
    normalized = username.strip().lower()
    if not normalized:
        raise ValueError("Username is required")

    friend = (await db.execute(select(User).where(User.username == normalized))).scalar_one_or_none()
    if friend is None:
        raise ValueError("User not found")
    if friend.id == user_id:
        raise ValueError("You cannot add yourself")

    existing = (
        await db.execute(
            select(FriendLink).where(
                FriendLink.user_id == user_id,
                FriendLink.friend_user_id == friend.id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return friend

    db.add(FriendLink(user_id=user_id, friend_user_id=friend.id))
    await db.flush()
    return friend


async def remove_circle_friend(db: AsyncSession, *, user_id: int, friend_user_id: int) -> None:
    row = (
        await db.execute(
            select(FriendLink).where(
                FriendLink.user_id == user_id,
                FriendLink.friend_user_id == friend_user_id,
            )
        )
    ).scalar_one_or_none()
    if row is not None:
        await db.delete(row)
