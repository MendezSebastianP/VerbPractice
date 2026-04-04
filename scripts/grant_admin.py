from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.db.models import User


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Grant admin access to an existing user.")
    parser.add_argument("username", help="Username to promote.")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    username = args.username.strip().lower()

    async with AsyncSessionLocal() as session:
        user = (await session.execute(select(User).where(User.username == username))).scalar_one_or_none()
        if user is None:
            raise SystemExit(f"User not found: {username}")
        user.is_admin = True
        await session.commit()

    print(f"Granted admin access to {username}.")


if __name__ == "__main__":
    asyncio.run(main())
