from datetime import datetime, timedelta, timezone

from app.services.training_engine import (
    WeightedItem,
    grade_translation,
    recency_multiplier,
    update_probability,
    weighted_sample_without_replacement,
)


def test_grade_translation_exact_and_synonym():
    exact = grade_translation("hola", ["hola"], ["buenas"])
    synonym = grade_translation("buenas", ["hola"], ["buenas"])
    wrong = grade_translation("adios", ["hola"], ["buenas"])

    assert exact.is_correct is True
    assert exact.multiplier == 0.7

    assert synonym.is_correct is True
    assert synonym.is_synonym is True
    assert synonym.multiplier == 0.8

    assert wrong.is_correct is False
    assert wrong.multiplier == 1.3


def test_probability_bounds():
    assert update_probability(10, 0.1) == 20.0
    assert update_probability(100000, 10) == 100000.0


def test_recency_multiplier_increases_with_time():
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=10)
    fresh = now - timedelta(hours=1)

    assert recency_multiplier(old, now) > recency_multiplier(fresh, now)


def test_weighted_sample_without_replacement_size():
    items = [WeightedItem(item_id=i, probability=1000 + i) for i in range(1, 11)]
    chosen = weighted_sample_without_replacement(items, 5)
    assert len(chosen) == 5
    assert len(set(chosen)) == 5
