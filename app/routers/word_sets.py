from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.csrf import validate_csrf
from app.core.security import AuthContext, require_auth_context
from app.db.models import Tag, Word, WordSet, WordSetMember, WordTag
from app.db.session import get_db
from app.schemas.spa import CsrfPayload

router = APIRouter(prefix="/api/word-sets", tags=["word-sets"])


class WordSetCreatePayload(CsrfPayload):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=1024)
    icon: str | None = Field(default=None, max_length=32)
    kind: str = Field(default="manual", pattern=r"^(manual|smart)$")
    filter_tag_slugs: list[str] = Field(default_factory=list)


class WordSetUpdatePayload(CsrfPayload):
    name: str | None = Field(default=None, max_length=128)
    description: str | None = Field(default=None, max_length=1024)
    icon: str | None = Field(default=None, max_length=32)
    filter_tag_slugs: list[str] | None = None


class WordSetMemberPayload(CsrfPayload):
    word_id: int


async def _resolve_filter_tag_ids(db: AsyncSession, slugs: list[str]) -> list[int]:
    if not slugs:
        return []
    rows = await db.execute(select(Tag).where(Tag.slug.in_(slugs)))
    return [t.id for t in rows.scalars().all()]


async def _slugs_for_tag_ids(db: AsyncSession, tag_ids: list[int]) -> list[str]:
    if not tag_ids:
        return []
    rows = await db.execute(select(Tag).where(Tag.id.in_(tag_ids)))
    return [t.slug for t in rows.scalars().all()]


async def _smart_set_word_ids(db: AsyncSession, tag_ids: list[int]) -> list[int]:
    """Return word IDs that have ALL the given tag IDs attached."""
    if not tag_ids:
        return []
    # words with WordTag rows covering every tag in the filter
    rows = await db.execute(
        select(WordTag.word_id, func.count(WordTag.tag_id))
        .where(WordTag.tag_id.in_(tag_ids))
        .group_by(WordTag.word_id)
        .having(func.count(WordTag.tag_id) == len(tag_ids))
    )
    return [r[0] for r in rows.all()]


async def _summary(db: AsyncSession, ws: WordSet) -> dict:
    slugs = await _slugs_for_tag_ids(db, list(ws.filter_tag_ids or []))
    if ws.kind == "manual":
        count = (
            await db.execute(
                select(func.count(WordSetMember.word_id)).where(WordSetMember.set_id == ws.id)
            )
        ).scalar_one()
    else:
        count = len(await _smart_set_word_ids(db, list(ws.filter_tag_ids or [])))
    return {
        "id": ws.id,
        "name": ws.name,
        "description": ws.description,
        "icon": ws.icon,
        "kind": ws.kind,
        "owner_user_id": ws.owner_user_id,
        "filter_tag_slugs": slugs,
        "word_count": count,
    }


async def _owned_or_public(auth: AuthContext, ws: WordSet) -> bool:
    return ws.owner_user_id is None or ws.owner_user_id == auth.user.id


@router.get("")
async def list_sets(
    auth: AuthContext = Depends(require_auth_context),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(
        select(WordSet).where(
            or_(WordSet.owner_user_id == auth.user.id, WordSet.owner_user_id.is_(None))
        ).order_by(WordSet.created_at.desc())
    )
    sets = []
    for ws in rows.scalars().all():
        sets.append(await _summary(db, ws))
    return {"sets": sets}


@router.post("")
async def create_set(
    request: Request,
    payload: WordSetCreatePayload,
    auth: AuthContext = Depends(require_auth_context),
    db: AsyncSession = Depends(get_db),
):
    validate_csrf(request, payload.csrf_token)
    tag_ids = await _resolve_filter_tag_ids(db, payload.filter_tag_slugs)
    if payload.kind == "smart" and not tag_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Smart sets require at least one filter tag.",
        )
    ws = WordSet(
        owner_user_id=auth.user.id,
        name=payload.name,
        description=payload.description,
        icon=payload.icon,
        kind=payload.kind,
        filter_tag_ids=tag_ids,
    )
    db.add(ws)
    await db.commit()
    await db.refresh(ws)
    return await _summary(db, ws)


@router.get("/{set_id}")
async def get_set(
    set_id: int,
    auth: AuthContext = Depends(require_auth_context),
    db: AsyncSession = Depends(get_db),
):
    ws = (await db.execute(select(WordSet).where(WordSet.id == set_id))).scalar_one_or_none()
    if ws is None or not await _owned_or_public(auth, ws):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Set not found")

    if ws.kind == "manual":
        rows = await db.execute(
            select(Word)
            .join(WordSetMember, WordSetMember.word_id == Word.id)
            .where(WordSetMember.set_id == ws.id)
            .order_by(Word.text.asc())
        )
        words = rows.scalars().all()
    else:
        word_ids = await _smart_set_word_ids(db, list(ws.filter_tag_ids or []))
        if word_ids:
            words = (
                await db.execute(
                    select(Word).where(Word.id.in_(word_ids)).order_by(Word.text.asc())
                )
            ).scalars().all()
        else:
            words = []

    lang_rows = (
        await db.execute(
            select(Word.language_id)
            .where(Word.id.in_([w.id for w in words]))
        )
        if words
        else None
    )

    from app.db.models import Language
    lang_lookup = await db.execute(select(Language))
    lang_by_id = {l.id: l.code for l in lang_lookup.scalars().all()}

    summary = await _summary(db, ws)
    return {
        **summary,
        "words": [
            {
                "word_id": w.id,
                "text": w.text,
                "language_code": lang_by_id.get(w.language_id, "?"),
            }
            for w in words
        ],
    }


@router.patch("/{set_id}")
async def update_set(
    set_id: int,
    request: Request,
    payload: WordSetUpdatePayload,
    auth: AuthContext = Depends(require_auth_context),
    db: AsyncSession = Depends(get_db),
):
    validate_csrf(request, payload.csrf_token)
    ws = (await db.execute(select(WordSet).where(WordSet.id == set_id))).scalar_one_or_none()
    if ws is None or ws.owner_user_id != auth.user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Set not found")

    if payload.name is not None:
        ws.name = payload.name
    if payload.description is not None:
        ws.description = payload.description
    if payload.icon is not None:
        ws.icon = payload.icon
    if payload.filter_tag_slugs is not None:
        ws.filter_tag_ids = await _resolve_filter_tag_ids(db, payload.filter_tag_slugs)

    await db.commit()
    await db.refresh(ws)
    return await _summary(db, ws)


@router.delete("/{set_id}")
async def delete_set(
    set_id: int,
    request: Request,
    payload: CsrfPayload,
    auth: AuthContext = Depends(require_auth_context),
    db: AsyncSession = Depends(get_db),
):
    validate_csrf(request, payload.csrf_token)
    ws = (await db.execute(select(WordSet).where(WordSet.id == set_id))).scalar_one_or_none()
    if ws is None or ws.owner_user_id != auth.user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Set not found")
    await db.delete(ws)
    await db.commit()
    return {"ok": True}


@router.post("/{set_id}/words")
async def add_word_to_set(
    set_id: int,
    request: Request,
    payload: WordSetMemberPayload,
    auth: AuthContext = Depends(require_auth_context),
    db: AsyncSession = Depends(get_db),
):
    validate_csrf(request, payload.csrf_token)
    ws = (await db.execute(select(WordSet).where(WordSet.id == set_id))).scalar_one_or_none()
    if ws is None or ws.owner_user_id != auth.user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Set not found")
    if ws.kind != "manual":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot manually add words to a smart set",
        )

    word = (await db.execute(select(Word).where(Word.id == payload.word_id))).scalar_one_or_none()
    if word is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Word not found")

    existing = (
        await db.execute(
            select(WordSetMember).where(
                WordSetMember.set_id == set_id, WordSetMember.word_id == word.id
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(WordSetMember(set_id=set_id, word_id=word.id))
        await db.commit()
    return {"ok": True}


@router.delete("/{set_id}/words/{word_id}")
async def remove_word_from_set(
    set_id: int,
    word_id: int,
    request: Request,
    payload: CsrfPayload,
    auth: AuthContext = Depends(require_auth_context),
    db: AsyncSession = Depends(get_db),
):
    validate_csrf(request, payload.csrf_token)
    ws = (await db.execute(select(WordSet).where(WordSet.id == set_id))).scalar_one_or_none()
    if ws is None or ws.owner_user_id != auth.user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Set not found")
    await db.execute(
        delete(WordSetMember).where(
            and_(WordSetMember.set_id == set_id, WordSetMember.word_id == word_id)
        )
    )
    await db.commit()
    return {"ok": True}
