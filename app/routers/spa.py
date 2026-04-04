from __future__ import annotations

from fastapi import APIRouter, Request

from app.routers.common import render_template

router = APIRouter(tags=["spa"])


@router.get("/app")
@router.get("/app/{path:path}")
async def spa_shell(request: Request, path: str = ""):
    return render_template(
        request,
        "spa_shell.html",
        {
            "spa_path": path,
        },
    )
