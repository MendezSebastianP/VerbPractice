from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.db.session import AsyncSessionLocal

router = APIRouter(tags=["ops"])


@router.get("/healthz")
async def healthz():
    return JSONResponse(
        {
            "status": "ok",
            "app": settings.app_name,
            "env": settings.app_env,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


@router.get("/readyz")
async def readyz():
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        return JSONResponse(
            {
                "status": "degraded",
                "app": settings.app_name,
                "env": settings.app_env,
                "detail": str(exc),
            },
            status_code=503,
        )

    return JSONResponse(
        {
            "status": "ready",
            "app": settings.app_name,
            "env": settings.app_env,
            "database": "ok",
        }
    )
