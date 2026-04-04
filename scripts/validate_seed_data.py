from __future__ import annotations

import asyncio

from sqlalchemy import func, select

from app.db.models import Language, VerbConjugation
from app.db.session import AsyncSessionLocal


async def main() -> None:
    async with AsyncSessionLocal() as session:
        total_words = await session.execute(select(func.count(VerbConjugation.id)))
        print(f"Total conjugation rows: {total_words.scalar_one()}")

        languages = await session.execute(select(Language))
        for lang in languages.scalars().all():
            rows = await session.execute(
                select(func.count(VerbConjugation.id)).where(VerbConjugation.language_id == lang.id)
            )
            print(f"{lang.code}: {rows.scalar_one()} conjugation rows")


if __name__ == "__main__":
    asyncio.run(main())
