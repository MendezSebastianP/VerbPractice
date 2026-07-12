"""Persistence and reporting for OpenAI token usage (AIUsageLog)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AIUsageLog, User

# USD per million tokens. Update when models/prices change.
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
}
_DEFAULT_PRICING = (0.0, 0.0)

FEATURE_LABELS: dict[str, str] = {
    "word_translate": "Word translations",
    "word_native_translate": "Native translations",
    "word_expand": "Word deep dives",
    "chat_stream": "AI tutor chat",
}

# Features counted as "translation" spend in the financial summary.
_TRANSLATION_FEATURES = {"word_translate", "word_native_translate", "word_expand"}


def _cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> tuple[float, float, float]:
    input_ppm, output_ppm = MODEL_PRICING.get(model, _DEFAULT_PRICING)
    cost = (prompt_tokens * input_ppm + completion_tokens * output_ppm) / 1_000_000
    return input_ppm, output_ppm, cost


async def record_ai_usage(
    db: AsyncSession,
    *,
    user_id: int | None,
    feature: str,
    model: str,
    usage,
    request_label: str | None = None,
    extra_data: dict[str, object] | None = None,
    status: str = "success",
) -> AIUsageLog:
    prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
    total_tokens = int(getattr(usage, "total_tokens", 0) or (prompt_tokens + completion_tokens))
    input_ppm, output_ppm, cost = _cost_usd(model, prompt_tokens, completion_tokens)

    entry = AIUsageLog(
        user_id=user_id,
        feature=feature,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        input_cost_per_million=input_ppm,
        output_cost_per_million=output_ppm,
        cost_usd=cost,
        status=status,
        request_label=(request_label or None) and request_label[:255],
        extra_data=extra_data or {},
    )
    db.add(entry)
    await db.flush()
    return entry


async def ai_usage_report(db: AsyncSession, *, limit: int = 50) -> dict:
    rows = (await db.execute(select(AIUsageLog))).scalars().all()

    total_cost = sum(r.cost_usd for r in rows)
    translation_rows = [r for r in rows if r.feature in _TRANSLATION_FEATURES]
    translation_cost = sum(r.cost_usd for r in translation_rows)

    by_feature: dict[str, dict] = {}
    for r in rows:
        bucket = by_feature.setdefault(
            r.feature,
            {
                "feature": r.feature,
                "label": FEATURE_LABELS.get(r.feature, r.feature),
                "calls": 0,
                "cost_usd": 0.0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
        )
        bucket["calls"] += 1
        bucket["cost_usd"] += r.cost_usd
        bucket["prompt_tokens"] += r.prompt_tokens
        bucket["completion_tokens"] += r.completion_tokens
        bucket["total_tokens"] += r.total_tokens
    for bucket in by_feature.values():
        bucket["average_cost_usd"] = bucket["cost_usd"] / bucket["calls"] if bucket["calls"] else 0.0

    by_model: dict[str, dict] = {}
    for r in rows:
        bucket = by_model.setdefault(
            r.model,
            {
                "model": r.model,
                "calls": 0,
                "cost_usd": 0.0,
                "total_tokens": 0,
                "input_cost_per_million": r.input_cost_per_million,
                "output_cost_per_million": r.output_cost_per_million,
            },
        )
        bucket["calls"] += 1
        bucket["cost_usd"] += r.cost_usd
        bucket["total_tokens"] += r.total_tokens

    user_totals = await db.execute(
        select(User.username, func.count(AIUsageLog.id), func.sum(AIUsageLog.cost_usd))
        .join(User, User.id == AIUsageLog.user_id)
        .group_by(User.username)
        .order_by(func.sum(AIUsageLog.cost_usd).desc())
        .limit(10)
    )
    top_users = [
        {"username": username, "calls": calls, "total_cost_usd": float(cost or 0.0)}
        for username, calls, cost in user_totals.all()
    ]

    recent_rows = (
        await db.execute(
            select(AIUsageLog, User.username)
            .outerjoin(User, User.id == AIUsageLog.user_id)
            .order_by(AIUsageLog.created_at.desc(), AIUsageLog.id.desc())
            .limit(limit)
        )
    ).all()
    recent = [
        {
            "id": r.id,
            "user": username,
            "feature": r.feature,
            "label": FEATURE_LABELS.get(r.feature, r.feature),
            "model": r.model,
            "prompt_tokens": r.prompt_tokens,
            "completion_tokens": r.completion_tokens,
            "total_tokens": r.total_tokens,
            "cost_usd": r.cost_usd,
            "request_label": r.request_label,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "extra_data": r.extra_data or {},
        }
        for r, username in recent_rows
    ]

    return {
        "financials": {
            "total_cost_usd": total_cost,
            "translation_cost_usd": translation_cost,
            "average_translation_cost_usd": (
                translation_cost / len(translation_rows) if translation_rows else 0.0
            ),
            "total_calls": len(rows),
            "translation_calls": len(translation_rows),
            "prompt_tokens": sum(r.prompt_tokens for r in rows),
            "completion_tokens": sum(r.completion_tokens for r in rows),
            "total_tokens": sum(r.total_tokens for r in rows),
            "translation_tokens": sum(r.total_tokens for r in translation_rows),
        },
        "by_feature": sorted(by_feature.values(), key=lambda b: b["cost_usd"], reverse=True),
        "by_model": sorted(by_model.values(), key=lambda b: b["cost_usd"], reverse=True),
        "top_users": top_users,
        "recent": recent,
        "pricing": [
            {
                "model": model,
                "input_cost_per_million": input_ppm,
                "output_cost_per_million": output_ppm,
            }
            for model, (input_ppm, output_ppm) in MODEL_PRICING.items()
        ],
    }
