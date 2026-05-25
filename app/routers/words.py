from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.csrf import validate_csrf
from app.core.security import AuthContext, require_auth_context
from app.db.models import (
    Language,
    ProgressItemType,
    TranslationReport,
    UserAddedWord,
    UserPreference,
    UserProgress,
    Word,
    WordLexicalEntry,
    WordNativeTranslation,
)
from app.db.session import get_db
from app.schemas.spa import (
    AddWordPayload,
    ExpandWordPayload,
    ReportTranslationPayload,
)
from app.services.gamification import ensure_user_preference
from app.services.word_ai_service import WordAIError, expand_word, translate_word

router = APIRouter(prefix="/api/words", tags=["words"])


def _serialize_lexical(entry: WordLexicalEntry) -> dict:
    return {
        "id": entry.id,
        "word_id": entry.word_id,
        "definition": entry.definition,
        "synonyms": entry.synonyms or [],
        "examples": entry.examples or [],
        "extended_content": entry.extended_content,
    }


def _serialize_native(entry: WordNativeTranslation, lang_code: str) -> dict:
    return {
        "id": entry.id,
        "word_id": entry.word_id,
        "native_language_code": lang_code,
        "translation": entry.translation,
        "note": entry.note,
    }


async def _require_lang_prefs(
    db: AsyncSession, preference: UserPreference
) -> tuple[Language, Language]:
    if preference.learning_language_id is None or preference.mother_tongue_language_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Set mother tongue and learning language in settings before adding words.",
        )
    rows = await db.execute(
        select(Language).where(
            Language.id.in_(
                [preference.learning_language_id, preference.mother_tongue_language_id]
            )
        )
    )
    by_id = {lang.id: lang for lang in rows.scalars().all()}
    learning = by_id.get(preference.learning_language_id)
    mother = by_id.get(preference.mother_tongue_language_id)
    if learning is None or mother is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configured languages are missing.",
        )
    if learning.id == mother.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mother tongue and learning language must differ.",
        )
    return learning, mother


@router.post("/add")
async def add_word(
    request: Request,
    payload: AddWordPayload,
    auth: AuthContext = Depends(require_auth_context),
    db: AsyncSession = Depends(get_db),
):
    validate_csrf(request, payload.csrf_token)
    preference = await ensure_user_preference(db, auth.user.id)
    learning, mother = await _require_lang_prefs(db, preference)

    if payload.learning_lang_code:
        override_lookup = await db.execute(
            select(Language).where(Language.code == payload.learning_lang_code.upper())
        )
        override = override_lookup.scalar_one_or_none()
        if override is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown learning language: {payload.learning_lang_code}",
            )
        if override.id == mother.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Learning language must differ from mother tongue",
            )
        learning = override

    try:
        result = await translate_word(
            db,
            input_text=payload.input_text,
            learning_lang=learning,
            mother_tongue=mother,
            context=payload.context,
        )
    except WordAIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    if result.status == "not_found":
        await db.rollback()
        return {
            "status": "not_found",
            "suggestions": result.suggestions or [],
            "original_input": payload.input_text,
            "learning_language_code": learning.code,
            "mother_tongue_code": mother.code,
        }

    assert result.word is not None and result.lexical is not None and result.natives is not None

    language_pair = f"{learning.code.lower()}_{mother.code.lower()}"

    existing_added = await db.execute(
        select(UserAddedWord).where(
            UserAddedWord.user_id == auth.user.id,
            UserAddedWord.word_id == result.word.id,
            UserAddedWord.language_pair == language_pair,
        )
    )
    added = existing_added.scalar_one_or_none()
    if added is None:
        added = UserAddedWord(
            user_id=auth.user.id,
            word_id=result.word.id,
            language_pair=language_pair,
            context_hint=payload.context,
        )
        db.add(added)
        await db.flush()

    force_unlocked = False
    if preference.force_unlock_added_words:
        existing_progress = await db.execute(
            select(UserProgress).where(
                UserProgress.user_id == auth.user.id,
                UserProgress.item_type == ProgressItemType.WORD,
                UserProgress.item_id == result.word.id,
                UserProgress.language_pair == language_pair,
            )
        )
        progress = existing_progress.scalar_one_or_none()
        if progress is None:
            db.add(
                UserProgress(
                    user_id=auth.user.id,
                    item_type=ProgressItemType.WORD,
                    item_id=result.word.id,
                    language_pair=language_pair,
                    probability=1000.0,
                    unlocked=True,
                    extra_data={"source": "user_added"},
                )
            )
            force_unlocked = True

    await db.commit()
    await db.refresh(result.word)
    await db.refresh(result.lexical)
    for n in result.natives:
        await db.refresh(n)

    return {
        "status": result.status,
        "original_input": result.original_input or payload.input_text,
        "detected_input_language": result.detected_input_language,
        "word_id": result.word.id,
        "text": result.word.text,
        "learning_language_code": learning.code,
        "mother_tongue_code": mother.code,
        "lexical": _serialize_lexical(result.lexical),
        "natives": [_serialize_native(n, mother.code) for n in result.natives],
        "general_note": result.general_note,
        "suggested_tags": result.suggested_tags or [],
        "priority_queue_id": added.id,
        "force_unlocked": force_unlocked,
    }


@router.get("/priority-queue")
async def priority_queue(
    auth: AuthContext = Depends(require_auth_context),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(
        select(UserAddedWord, Word)
        .join(Word, Word.id == UserAddedWord.word_id)
        .where(UserAddedWord.user_id == auth.user.id)
        .order_by(UserAddedWord.added_at.asc())
    )
    pending = []
    for added, word in rows.all():
        progress_lookup = await db.execute(
            select(UserProgress.id).where(
                UserProgress.user_id == auth.user.id,
                UserProgress.item_type == ProgressItemType.WORD,
                UserProgress.item_id == word.id,
                UserProgress.language_pair == added.language_pair,
            )
        )
        if progress_lookup.scalar_one_or_none() is not None:
            continue
        pending.append(
            {
                "id": added.id,
                "word_id": word.id,
                "word_text": word.text,
                "language_pair": added.language_pair,
                "context_hint": added.context_hint,
                "added_at": added.added_at.isoformat() if added.added_at else None,
            }
        )
    return {"entries": pending}


@router.post("/{word_id}/expand")
async def expand_word_endpoint(
    word_id: int,
    request: Request,
    payload: ExpandWordPayload,
    auth: AuthContext = Depends(require_auth_context),
    db: AsyncSession = Depends(get_db),
):
    validate_csrf(request, payload.csrf_token)
    word_lookup = await db.execute(select(Word).where(Word.id == word_id))
    word = word_lookup.scalar_one_or_none()
    if word is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Word not found")
    lang_lookup = await db.execute(select(Language).where(Language.id == word.language_id))
    learning = lang_lookup.scalar_one_or_none()
    if learning is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Word language unknown")
    try:
        lexical = await expand_word(db, word=word, learning_lang=learning)
    except WordAIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(lexical)
    return {"extended_content": lexical.extended_content or ""}


@router.post("/{word_id}/report")
async def report_translation(
    word_id: int,
    request: Request,
    payload: ReportTranslationPayload,
    auth: AuthContext = Depends(require_auth_context),
    db: AsyncSession = Depends(get_db),
):
    validate_csrf(request, payload.csrf_token)

    if payload.entry_type == "lexical":
        target_lookup = await db.execute(
            select(WordLexicalEntry).where(WordLexicalEntry.id == payload.entry_id)
        )
        target = target_lookup.scalar_one_or_none()
    else:
        target_lookup = await db.execute(
            select(WordNativeTranslation).where(WordNativeTranslation.id == payload.entry_id)
        )
        target = target_lookup.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Translation entry not found")

    target.flag_count = (target.flag_count or 0) + 1
    report = TranslationReport(
        user_id=auth.user.id,
        entry_type=payload.entry_type,
        entry_id=payload.entry_id,
        reason=payload.reason,
        status="pending",
    )
    db.add(report)
    await db.commit()
    return {"ok": True, "report_id": report.id}
