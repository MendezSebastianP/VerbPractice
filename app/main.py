from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.core.languages import LANGUAGE_DEFINITIONS
from app.core.observability import RequestLogMiddleware, configure_logging
from app.core.rate_limit import limiter
from app.db.models import Language
from app.db.session import AsyncSessionLocal
from sqlalchemy import select
from app.routers import (
    admin,
    api,
    auth,
    chat,
    ops,
    pages,
    settings as settings_router,
    spa,
    tags,
    training,
    word_sets,
    words,
)

BASE_DIR = Path(__file__).resolve().parent
SPA_STATIC_DIR = BASE_DIR.parent / "frontend" / "static" / "spa"

configure_logging()

app = FastAPI(title=settings.app_name)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(_: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": str(exc.detail)})


app.add_middleware(SessionMiddleware, secret_key=settings.secret_key, same_site="lax")
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(RequestLogMiddleware)

if SPA_STATIC_DIR.exists():
    app.mount("/static/spa", StaticFiles(directory=str(SPA_STATIC_DIR)), name="spa-static")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.include_router(ops.router)
app.include_router(auth.router)
app.include_router(api.router)
app.include_router(pages.router)
app.include_router(training.router)
app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(settings_router.router)
app.include_router(words.router)
app.include_router(tags.router)
app.include_router(word_sets.router)
app.include_router(spa.router)


@app.on_event("startup")
async def _ensure_language_rows() -> None:
    async with AsyncSessionLocal() as db:
        existing = {row[0] for row in (await db.execute(select(Language.code))).all()}
        added = False
        for code, payload in LANGUAGE_DEFINITIONS.items():
            if code in existing:
                continue
            db.add(
                Language(
                    code=code,
                    name=str(payload["name"]),
                    pronoun_set=list(payload["pronoun_set"]),
                    tense_definitions=dict(payload["tense_definitions"]),
                    difficulty_tiers=dict(payload["difficulty_tiers"]),
                )
            )
            added = True
        if added:
            await db.commit()
