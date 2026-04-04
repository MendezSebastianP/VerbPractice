from __future__ import annotations

from collections.abc import AsyncIterator
import json
import re

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.csrf import validate_csrf
from app.core.rate_limit import limiter
from app.core.security import require_auth_context
from app.db.models import ChatMessage, ChatRole
from app.db.session import get_db
from app.routers.common import render_template
from app.services.dashboard_service import recent_chat_messages, summarize_progress
from app.services.chat_service import stream_chat_response

router = APIRouter(prefix="/chat", tags=["chat"])


def _sanitize_chat_text(raw: str) -> str:
    cleaned = "".join(char for char in raw if char.isprintable() or char in {"\n", "\t"})
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()[:1200]


@router.get("")
async def chat_page(request: Request, db: AsyncSession = Depends(get_db), auth=Depends(require_auth_context)):
    request.state.user = auth.user
    messages = await recent_chat_messages(db, user_id=auth.user.id, limit=18)
    weak_items = await summarize_progress(db, user_id=auth.user.id, focus_limit=5)
    suggestions = [
        "Quiz me on the words I miss most often.",
        "Give me a short French-to-Spanish verb drill.",
        "Create a conjugation challenge using my weakest tense.",
    ]
    if weak_items["focus_items"]:
        suggestions[0] = f"Quiz me on {weak_items['focus_items'][0]['label']} and similar words."
    return render_template(
        request,
        "chat/chat.html",
        {
            "profile": auth.profile,
            "messages": messages,
            "focus_items": weak_items["focus_items"],
            "suggestions": suggestions,
            "api_enabled": bool(settings.openai_api_key),
        },
    )


@router.post("/stream")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def stream_chat(
    request: Request,
    message: str = Form(...),
    csrf_token: str = Form(...),
    db: AsyncSession = Depends(get_db),
    auth=Depends(require_auth_context),
):
    validate_csrf(request, csrf_token)
    request.state.user = auth.user

    content = _sanitize_chat_text(message)
    if not content:
        return RedirectResponse(url="/chat", status_code=303)

    user_message = ChatMessage(user_id=auth.user.id, role=ChatRole.USER, content=content)
    db.add(user_message)
    await db.flush()

    async def event_stream() -> AsyncIterator[str]:
        chunks: list[str] = []
        try:
            async for chunk in stream_chat_response(db=db, user_id=auth.user.id, user_message=content):
                chunks.append(chunk)
                payload = json.dumps({"chunk": chunk})
                yield f"data: {payload}\n\n"
        except Exception:
            fallback = "The tutor stream failed. Please try again."
            chunks.append(fallback)
            yield f"data: {json.dumps({'chunk': fallback})}\n\n"

        full_response = "".join(chunks)
        db.add(ChatMessage(user_id=auth.user.id, role=ChatRole.ASSISTANT, content=full_response))
        await db.commit()
        yield "event: done\ndata: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
