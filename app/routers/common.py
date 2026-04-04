from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.core.csrf import get_or_create_csrf_token

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def render_template(request: Request, name: str, context: dict[str, Any]):
    theme = context.get("theme")
    profile = context.get("profile")
    current_user = context.get("user") or getattr(request.state, "user", None)
    if theme is None and profile is not None and hasattr(profile, "theme_preference"):
        theme = getattr(profile, "theme_preference")

    base_context = {
        "request": request,
        "csrf_token": get_or_create_csrf_token(request),
        "active_path": request.url.path,
        "theme": theme or settings.default_theme,
        "current_user": current_user,
    }
    return templates.TemplateResponse(request, name, {**base_context, **context})
