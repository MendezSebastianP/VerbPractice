from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthContext, require_auth_context
from app.db.models import Tag
from app.db.session import get_db

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("")
async def list_tags(
    _auth: AuthContext = Depends(require_auth_context),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(select(Tag).order_by(Tag.kind.asc(), Tag.display_name.asc()))
    return {
        "tags": [
            {
                "id": t.id,
                "slug": t.slug,
                "display_name": t.display_name,
                "kind": t.kind,
                "applies_to": t.applies_to or [],
            }
            for t in rows.scalars().all()
        ]
    }
