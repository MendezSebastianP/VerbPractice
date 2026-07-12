from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Request

from app.routers.common import render_template

router = APIRouter(tags=["spa"])

SPA_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "static" / "spa"
MANIFEST_PATH = SPA_DIR / ".vite" / "manifest.json"

# Vite emits content-hashed filenames (app-<hash>.js) so deploys are never
# served stale from a cache; the manifest tells us the current names. Cached
# per manifest mtime so dev rebuilds are picked up without a server restart.
_manifest_cache: tuple[float, str, str | None] | None = None


def _spa_assets() -> tuple[str, str | None]:
    global _manifest_cache
    try:
        mtime = MANIFEST_PATH.stat().st_mtime
    except OSError:
        return "app.js", "app.css"  # pre-manifest build layout

    if _manifest_cache and _manifest_cache[0] == mtime:
        return _manifest_cache[1], _manifest_cache[2]

    try:
        manifest = json.loads(MANIFEST_PATH.read_text())
        entry = next(item for item in manifest.values() if item.get("isEntry"))
        js = entry["file"]
        css = (entry.get("css") or [None])[0]
    except (OSError, ValueError, StopIteration, KeyError):
        return "app.js", "app.css"

    _manifest_cache = (mtime, js, css)
    return js, css


@router.get("/app")
@router.get("/app/{path:path}")
async def spa_shell(request: Request, path: str = ""):
    spa_js, spa_css = _spa_assets()
    response = render_template(
        request,
        "spa_shell.html",
        {
            "spa_path": path,
            "spa_js": spa_js,
            "spa_css": spa_css,
        },
    )
    # The shell must always be revalidated — it is what points browsers at the
    # current hashed bundle after a deploy.
    response.headers["Cache-Control"] = "no-cache"
    return response
