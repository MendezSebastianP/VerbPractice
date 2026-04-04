from __future__ import annotations

from collections.abc import AsyncIterator

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import ProgressItemType, UserProgress


async def weak_items_context(db: AsyncSession, user_id: int) -> str:
    result = await db.execute(
        select(UserProgress)
        .where(UserProgress.user_id == user_id)
        .order_by(UserProgress.probability.desc())
        .limit(6)
    )
    rows = result.scalars().all()
    if not rows:
        return "No progress data yet. Start with basics and adapt difficulty gradually."

    lines = []
    for row in rows:
        if row.item_type == ProgressItemType.CONJUGATION:
            tense_scores = (row.extra_data or {}).get("tense_scores", {})
            lines.append(
                f"Conjugation verb_id={row.item_id}, probability={row.probability:.0f}, weak_tenses={tense_scores}"
            )
        else:
            lines.append(
                f"{row.item_type.value} item_id={row.item_id}, probability={row.probability:.0f}, seen={row.times_seen}, correct={row.times_correct}"
            )
    return "\n".join(lines)


async def stream_chat_response(
    *,
    db: AsyncSession,
    user_id: int,
    user_message: str,
) -> AsyncIterator[str]:
    if not settings.openai_api_key:
        yield "OpenAI API key is not configured. Add OPENAI_API_KEY in .env."
        return

    profile_context = await weak_items_context(db, user_id)
    system_prompt = (
        "You are a multilingual tutor for VerbPractice. "
        "Generate concise, targeted feedback and include one short exercise. "
        "Use the learner context to prioritize weak areas.\n"
        f"Learner weak items:\n{profile_context}"
    )

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    stream = await client.chat.completions.create(
        model="gpt-4o-mini",
        stream=True,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )

    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
