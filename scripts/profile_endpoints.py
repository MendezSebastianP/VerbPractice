from __future__ import annotations

import argparse
import asyncio
import statistics
from dataclasses import dataclass
from time import perf_counter

import httpx
from sqlalchemy import select

from app.core.security import hash_password
from app.db.models import User, UserProfile
from app.db.session import AsyncSessionLocal
from app.main import app

PROFILE_USERNAME = "qa_profile"
PROFILE_PASSWORD = "profile12345"


@dataclass(slots=True)
class ProfileResult:
    name: str
    method: str
    path: str
    samples_ms: list[float]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Profile the main app endpoints.")
    parser.add_argument("--iterations", type=int, default=12, help="How many timing samples to collect per endpoint.")
    parser.add_argument(
        "--base-url",
        default="",
        help="Optional live server base URL. Defaults to in-process ASGI profiling if omitted.",
    )
    parser.add_argument(
        "--skip-auth",
        action="store_true",
        help="Only profile public endpoints.",
    )
    return parser.parse_args()


async def ensure_profile_user() -> None:
    async with AsyncSessionLocal() as session:
        user = (await session.execute(select(User).where(User.username == PROFILE_USERNAME))).scalar_one_or_none()
        if user is None:
            user = User(username=PROFILE_USERNAME, password_hash=hash_password(PROFILE_PASSWORD), is_admin=True)
            session.add(user)
            await session.flush()
            session.add(
                UserProfile(
                    user_id=user.id,
                    xp=0,
                    level=1,
                    streak_days=0,
                    theme_preference="light",
                )
            )
        elif not user.is_admin:
            user.is_admin = True
        await session.commit()


def summarize(samples_ms: list[float]) -> tuple[float, float, float]:
    ordered = sorted(samples_ms)
    avg = statistics.fmean(ordered)
    p50 = ordered[len(ordered) // 2]
    p95_index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * 0.95)))
    p95 = ordered[p95_index]
    return avg, p50, p95


async def timed_request(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    *,
    json: dict | None = None,
) -> float:
    started = perf_counter()
    response = await client.request(method, path, json=json)
    response.raise_for_status()
    return (perf_counter() - started) * 1000


async def build_client(base_url: str) -> httpx.AsyncClient:
    if base_url:
        return httpx.AsyncClient(base_url=base_url, timeout=20.0)
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver", timeout=20.0)


async def collect_public_samples(client: httpx.AsyncClient, iterations: int) -> list[ProfileResult]:
    endpoints = [
        ("Health", "GET", "/healthz", None),
        ("Readiness", "GET", "/readyz", None),
        ("Bootstrap", "GET", "/api/bootstrap", None),
        ("Login Page", "GET", "/app/login", None),
    ]
    results: list[ProfileResult] = []
    for name, method, path, payload in endpoints:
        samples = [await timed_request(client, method, path, json=payload) for _ in range(iterations)]
        results.append(ProfileResult(name=name, method=method, path=path, samples_ms=samples))
    return results


async def collect_auth_samples(client: httpx.AsyncClient, iterations: int) -> list[ProfileResult]:
    await ensure_profile_user()
    bootstrap = await client.get("/api/bootstrap")
    bootstrap.raise_for_status()
    csrf_token = bootstrap.json()["csrf_token"]

    login_response = await client.post(
        "/api/auth/login",
        json={
            "username": PROFILE_USERNAME,
            "password": PROFILE_PASSWORD,
            "csrf_token": csrf_token,
        },
    )
    login_response.raise_for_status()

    endpoints = [
        ("Dashboard API", "GET", "/api/dashboard", None),
        ("Community API", "GET", "/api/community", None),
        ("Admin Summary API", "GET", "/api/admin/content/summary", None),
        ("Dashboard SPA", "GET", "/app/dashboard", None),
        ("Verb Lab SPA", "GET", "/app/training/verbs", None),
    ]

    results: list[ProfileResult] = []
    for name, method, path, payload in endpoints:
        samples = [await timed_request(client, method, path, json=payload) for _ in range(iterations)]
        results.append(ProfileResult(name=name, method=method, path=path, samples_ms=samples))
    return results


def print_report(results: list[ProfileResult]) -> None:
    print("Endpoint performance snapshot")
    print()
    print(f"{'Name':24} {'Method':6} {'Path':32} {'Avg (ms)':>9} {'P50':>9} {'P95':>9}")
    print("-" * 95)
    for result in results:
        avg, p50, p95 = summarize(result.samples_ms)
        print(f"{result.name:24} {result.method:6} {result.path:32} {avg:9.1f} {p50:9.1f} {p95:9.1f}")


async def main() -> None:
    args = parse_args()
    async with await build_client(args.base_url) as client:
        results = await collect_public_samples(client, args.iterations)
        if not args.skip_auth:
            results.extend(await collect_auth_samples(client, args.iterations))
    print_report(results)


if __name__ == "__main__":
    asyncio.run(main())
