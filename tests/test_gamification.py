from datetime import date, timedelta

from app.db.models import UserProfile
from app.services.gamification import award_xp, update_streak


def test_award_xp_levels_up():
    profile = UserProfile(user_id=1, xp=0, level=1, streak_days=0)
    result = award_xp(profile, 300)
    assert result.gained_xp == 300
    assert profile.level >= 2


def test_streak_resets_after_gap():
    today = date.today()
    profile = UserProfile(user_id=1, xp=0, level=1, streak_days=4, last_active_date=today - timedelta(days=3))
    update_streak(profile, today)
    assert profile.streak_days == 1
