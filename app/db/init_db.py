import asyncio

from app.db.base import Base
from app.db.session import engine

# Legacy helper for direct schema creation in disposable environments.
# Prefer Alembic migrations (`make migrate`) for normal app setup.
from app.db import models  # noqa: F401


async def init_models() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(init_models())
    print("Database schema created with create_all. Prefer Alembic migrations for normal setup.")
