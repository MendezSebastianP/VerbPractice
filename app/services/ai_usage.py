from __future__ import annotations

from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AIUsageLog, User


# Prices are stored with each row so historical reports stay stable if rates change.
# Rates match the OpenAI API pricing page for text tokens. gpt-5.6-luna uses the
# short-context tier; these are list rates, so cache hits make the real bill lower.
# Unknown models fall back to (0.0, 0.0), so add a model here when you switch to it.
MODEL_TOKEN_PRICING_USD: dict[str, tuple[float, float]] = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-5.6-luna": (0.20, 1.20),
}
TRANSLATION_FEATURES = {"word_translate", "word_native_translate"}


def _usage_int(usage: Any, attr: str) -> int:
    value = getattr(usage, attr, 0) if usage is not None else 0
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def token_counts(usage: Any) -> tuple[int, int, int]:
    prompt_tokens = _usage_int(usage, "prompt_tokens")
    completion_tokens = _usage_int(usage, "completion_tokens")
    total_tokens = _usage_int(usage, "total_tokens") or prompt_tokens + completion_tokens
    return prompt_tokens, completion_tokens, total_tokens


def pricing_for_model(model: str) -> tuple[float, float]:
    return MODEL_TOKEN_PRICING_USD.get(model, (0.0, 0.0))


def estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> tuple[float, float, float]:
    input_rate, output_rate = pricing_for_model(model)
    cost = (prompt_tokens * input_rate / 1_000_000) + (completion_tokens * output_rate / 1_000_000)
    return input_rate, output_rate, cost


async def record_ai_usage(
    db: AsyncSession,
    *,
    user_id: int | None,
    feature: str,
    model: str,
    usage: Any,
    request_label: str | None = None,
    extra_data: dict[str, object] | None = None,
    status: str = "success",
) -> AIUsageLog:
    prompt_tokens, completion_tokens, total_tokens = token_counts(usage)
    input_rate, output_rate, cost_usd = estimate_cost_usd(model, prompt_tokens, completion_tokens)
    row = AIUsageLog(
        user_id=user_id,
        feature=feature,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        input_cost_per_million=input_rate,
        output_cost_per_million=output_rate,
        cost_usd=cost_usd,
        status=status,
        request_label=(request_label or "")[:255] or None,
        extra_data=extra_data or {},
    )
    db.add(row)
    await db.flush()
    return row


def _round_money(value: float | int | None, digits: int = 6) -> float:
    return round(float(value or 0), digits)


def _feature_label(feature: str) -> str:
    labels = {
        "word_translate": "Word translation",
        "word_native_translate": "Cached word, new target language",
        "word_expand": "More info",
        "chat_stream": "AI tutor",
    }
    return labels.get(feature, feature.replace("_", " ").title())


async def ai_usage_report(db: AsyncSession, *, limit: int = 50) -> dict[str, Any]:
    total_row = (
        await db.execute(
            select(
                func.count(AIUsageLog.id),
                func.coalesce(func.sum(AIUsageLog.cost_usd), 0),
                func.coalesce(func.sum(AIUsageLog.prompt_tokens), 0),
                func.coalesce(func.sum(AIUsageLog.completion_tokens), 0),
                func.coalesce(func.sum(AIUsageLog.total_tokens), 0),
            )
        )
    ).one()
    translation_row = (
        await db.execute(
            select(
                func.count(AIUsageLog.id),
                func.coalesce(func.sum(AIUsageLog.cost_usd), 0),
                func.coalesce(func.sum(AIUsageLog.total_tokens), 0),
            ).where(AIUsageLog.feature.in_(TRANSLATION_FEATURES))
        )
    ).one()

    total_calls = int(total_row[0] or 0)
    translation_calls = int(translation_row[0] or 0)
    total_cost = float(total_row[1] or 0)
    translation_cost = float(translation_row[1] or 0)

    by_feature_rows = (
        await db.execute(
            select(
                AIUsageLog.feature,
                func.count(AIUsageLog.id),
                func.coalesce(func.sum(AIUsageLog.cost_usd), 0),
                func.coalesce(func.sum(AIUsageLog.prompt_tokens), 0),
                func.coalesce(func.sum(AIUsageLog.completion_tokens), 0),
                func.coalesce(func.sum(AIUsageLog.total_tokens), 0),
            )
            .group_by(AIUsageLog.feature)
            .order_by(desc(func.sum(AIUsageLog.cost_usd)))
        )
    ).all()

    by_model_rows = (
        await db.execute(
            select(
                AIUsageLog.model,
                func.count(AIUsageLog.id),
                func.coalesce(func.sum(AIUsageLog.cost_usd), 0),
                func.coalesce(func.sum(AIUsageLog.total_tokens), 0),
            )
            .group_by(AIUsageLog.model)
            .order_by(desc(func.sum(AIUsageLog.cost_usd)))
        )
    ).all()

    top_user_rows = (
        await db.execute(
            select(
                User.username,
                func.count(AIUsageLog.id),
                func.coalesce(func.sum(AIUsageLog.cost_usd), 0),
            )
            .join(User, User.id == AIUsageLog.user_id)
            .group_by(User.username)
            .order_by(desc(func.count(AIUsageLog.id)))
            .limit(8)
        )
    ).all()

    recent_rows = (
        await db.execute(
            select(AIUsageLog, User)
            .outerjoin(User, User.id == AIUsageLog.user_id)
            .order_by(AIUsageLog.created_at.desc())
            .limit(max(1, min(limit, 200)))
        )
    ).all()

    return {
        "financials": {
            "total_cost_usd": _round_money(total_cost, 4),
            "translation_cost_usd": _round_money(translation_cost, 4),
            "average_translation_cost_usd": _round_money(
                translation_cost / translation_calls if translation_calls else 0,
                6,
            ),
            "total_calls": total_calls,
            "translation_calls": translation_calls,
            "prompt_tokens": int(total_row[2] or 0),
            "completion_tokens": int(total_row[3] or 0),
            "total_tokens": int(total_row[4] or 0),
            "translation_tokens": int(translation_row[2] or 0),
        },
        "by_feature": [
            {
                "feature": feature,
                "label": _feature_label(feature),
                "calls": int(calls or 0),
                "cost_usd": _round_money(cost, 6),
                "prompt_tokens": int(prompt_tokens or 0),
                "completion_tokens": int(completion_tokens or 0),
                "total_tokens": int(total_tokens or 0),
                "average_cost_usd": _round_money((float(cost or 0) / int(calls or 1)) if calls else 0, 6),
            }
            for feature, calls, cost, prompt_tokens, completion_tokens, total_tokens in by_feature_rows
        ],
        "by_model": [
            {
                "model": model,
                "calls": int(calls or 0),
                "cost_usd": _round_money(cost, 6),
                "total_tokens": int(total_tokens or 0),
                "input_cost_per_million": pricing_for_model(model)[0],
                "output_cost_per_million": pricing_for_model(model)[1],
            }
            for model, calls, cost, total_tokens in by_model_rows
        ],
        "top_users": [
            {
                "username": username,
                "calls": int(calls or 0),
                "total_cost_usd": _round_money(cost, 6),
            }
            for username, calls, cost in top_user_rows
        ],
        "recent": [
            {
                "id": row.id,
                "user": user.username if user else None,
                "feature": row.feature,
                "label": _feature_label(row.feature),
                "model": row.model,
                "prompt_tokens": row.prompt_tokens,
                "completion_tokens": row.completion_tokens,
                "total_tokens": row.total_tokens,
                "cost_usd": _round_money(row.cost_usd, 6),
                "request_label": row.request_label,
                "status": row.status,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "extra_data": row.extra_data or {},
            }
            for row, user in recent_rows
        ],
        "pricing": [
            {
                "model": model,
                "input_cost_per_million": input_rate,
                "output_cost_per_million": output_rate,
            }
            for model, (input_rate, output_rate) in MODEL_TOKEN_PRICING_USD.items()
        ],
    }
