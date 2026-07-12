from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.csrf import validate_csrf
from app.core.rate_limit import limiter
from app.core.security import AuthContext, require_auth_context
from app.db.models import (
    Language,
    ProgressItemType,
    Tag,
    TranslationReport,
    UserAddedWord,
    UserPreference,
    UserProgress,
    Word,
    WordLexicalEntry,
    WordNativeTranslation,
    WordTag,
)
from app.db.session import get_db
from app.schemas.spa import (
    AddWordOfflinePayload,
    AddWordPayload,
    DeleteUserWordPayload,
    ExpandWordPayload,
    OcrExtractResponse,
    ReportTranslationPayload,
)
from app.services.gamification import ensure_user_preference
from app.services.ocr_service import (
    MAX_UPLOAD_BYTES,
    TESSERACT_LANG_BY_CODE,
    OcrError,
    OcrUnavailableError,
    extract_subtitle_text,
)
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


async def _lang_by_code(db: AsyncSession, code: str) -> Language:
    lookup = await db.execute(select(Language).where(Language.code == code.upper()))
    lang = lookup.scalar_one_or_none()
    if lang is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown language: {code}",
        )
    return lang


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
        learning = await _lang_by_code(db, payload.learning_lang_code)
    if payload.mother_lang_code:
        mother = await _lang_by_code(db, payload.mother_lang_code)
    if learning.id == mother.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source and target languages must differ",
        )

    try:
        result = await translate_word(
            db,
            input_text=payload.input_text,
            learning_lang=learning,
            mother_tongue=mother,
            context=payload.context,
            user_id=auth.user.id,
        )
    except WordAIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    if result.status == "not_found":
        await db.commit()
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


@router.post("/ocr", response_model=OcrExtractResponse)
@limiter.limit("10/minute")
async def ocr_extract(
    request: Request,
    image: UploadFile = File(...),
    csrf_token: str = Form(...),
    lang_code: str = Form(...),
    auth: AuthContext = Depends(require_auth_context),
):
    validate_csrf(request, csrf_token)

    tesseract_lang = TESSERACT_LANG_BY_CODE.get(lang_code.lower())
    if tesseract_lang is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OCR language: {lang_code}",
        )
    if not (image.content_type or "").startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload must be an image.",
        )
    data = await image.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image too large (max 8 MB).",
        )

    try:
        result = await extract_subtitle_text(data, tesseract_lang)
    except OcrUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except OcrError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    return OcrExtractResponse(
        text=result.text,
        lines=result.lines,
        mean_confidence=result.mean_confidence,
        ocr_lang=tesseract_lang,
    )


@router.get("/history")
async def word_history(
    limit: int = 20,
    auth: AuthContext = Depends(require_auth_context),
    db: AsyncSession = Depends(get_db),
):
    limit = max(1, min(limit, 100))
    added_rows = await db.execute(
        select(UserAddedWord)
        .where(UserAddedWord.user_id == auth.user.id)
        .order_by(UserAddedWord.added_at.desc())
        .limit(limit)
    )
    added_list = list(added_rows.scalars().all())
    if not added_list:
        return {"entries": []}

    word_ids = [a.word_id for a in added_list]
    words_lookup = await db.execute(select(Word).where(Word.id.in_(word_ids)))
    words_by_id = {w.id: w for w in words_lookup.scalars().all()}

    lang_ids = {w.language_id for w in words_by_id.values()}
    lang_lookup = await db.execute(select(Language).where(Language.id.in_(lang_ids)))
    lang_by_id = {l.id: l for l in lang_lookup.scalars().all()}

    lex_lookup = await db.execute(
        select(WordLexicalEntry).where(WordLexicalEntry.word_id.in_(word_ids))
    )
    lex_by_word: dict[int, WordLexicalEntry] = {
        l.word_id: l for l in lex_lookup.scalars().all()
    }

    native_lookup = await db.execute(
        select(WordNativeTranslation)
        .where(WordNativeTranslation.word_id.in_(word_ids))
        .order_by(WordNativeTranslation.priority.asc(), WordNativeTranslation.id.asc())
    )
    natives_by_pair: dict[tuple[int, int], list[WordNativeTranslation]] = {}
    for n in native_lookup.scalars().all():
        natives_by_pair.setdefault((n.word_id, n.native_language_id), []).append(n)

    tag_lookup = await db.execute(
        select(WordTag.word_id, Tag.slug)
        .join(Tag, Tag.id == WordTag.tag_id)
        .where(WordTag.word_id.in_(word_ids))
    )
    tags_by_word: dict[int, list[str]] = {}
    for word_id, slug in tag_lookup.all():
        tags_by_word.setdefault(word_id, []).append(slug)

    entries = []
    for added in added_list:
        word = words_by_id.get(added.word_id)
        if word is None:
            continue
        lex = lex_by_word.get(word.id)
        if lex is None:
            continue
        learning_code, _, mother_code = added.language_pair.partition("_")
        mother_lang = next(
            (l for l in lang_by_id.values() if l.code.lower() == mother_code.lower()),
            None,
        )
        natives = (
            natives_by_pair.get((word.id, mother_lang.id), []) if mother_lang else []
        )
        entries.append(
            {
                "added_id": added.id,
                "word_id": word.id,
                "text": word.text,
                "language_pair": added.language_pair,
                "learning_language_code": learning_code.upper(),
                "mother_tongue_code": mother_code.upper(),
                "added_at": added.added_at.isoformat() if added.added_at else None,
                "lexical": _serialize_lexical(lex),
                "natives": [
                    _serialize_native(n, mother_code.upper()) for n in natives
                ],
                "tags": tags_by_word.get(word.id, []),
            }
        )
    return {"entries": entries}


async def _resolve_language_pair(
    db: AsyncSession, language_pair: str
) -> tuple[Language, Language]:
    learning_code, _, mother_code = language_pair.lower().partition("_")
    if not learning_code or not mother_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid language_pair (expected e.g. 'en_es')",
        )
    rows = await db.execute(
        select(Language).where(Language.code.in_([learning_code.upper(), mother_code.upper()]))
    )
    by_code = {l.code.upper(): l for l in rows.scalars().all()}
    learning = by_code.get(learning_code.upper())
    mother = by_code.get(mother_code.upper())
    if learning is None or mother is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown language in pair: {language_pair}",
        )
    if learning.id == mother.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Learning and mother tongue must differ",
        )
    return learning, mother


@router.get("/manage")
async def list_user_words(
    language_pair: str,
    auth: AuthContext = Depends(require_auth_context),
    db: AsyncSession = Depends(get_db),
):
    learning, mother = await _resolve_language_pair(db, language_pair)
    pair_key = f"{learning.code.lower()}_{mother.code.lower()}"

    added_rows = await db.execute(
        select(UserAddedWord)
        .where(
            UserAddedWord.user_id == auth.user.id,
            UserAddedWord.language_pair == pair_key,
        )
        .order_by(UserAddedWord.added_at.desc())
    )
    added_list = list(added_rows.scalars().all())

    progress_rows = await db.execute(
        select(UserProgress).where(
            UserProgress.user_id == auth.user.id,
            UserProgress.item_type == ProgressItemType.WORD,
            UserProgress.language_pair == pair_key,
        )
    )
    progress_by_word: dict[int, UserProgress] = {
        p.item_id: p for p in progress_rows.scalars().all()
    }

    word_ids = sorted({a.word_id for a in added_list} | set(progress_by_word.keys()))
    if not word_ids:
        return {"entries": []}

    words_lookup = await db.execute(
        select(Word).where(Word.id.in_(word_ids), Word.language_id == learning.id)
    )
    words_by_id = {w.id: w for w in words_lookup.scalars().all()}

    native_lookup = await db.execute(
        select(WordNativeTranslation)
        .where(
            WordNativeTranslation.word_id.in_(word_ids),
            WordNativeTranslation.native_language_id == mother.id,
        )
        .order_by(WordNativeTranslation.priority.asc(), WordNativeTranslation.id.asc())
    )
    natives_by_word: dict[int, list[WordNativeTranslation]] = {}
    for n in native_lookup.scalars().all():
        natives_by_word.setdefault(n.word_id, []).append(n)

    added_by_word = {a.word_id: a for a in added_list}

    entries = []
    for word_id in word_ids:
        word = words_by_id.get(word_id)
        if word is None:
            continue
        added = added_by_word.get(word_id)
        progress = progress_by_word.get(word_id)
        natives = natives_by_word.get(word_id, [])
        entries.append(
            {
                "word_id": word.id,
                "text": word.text,
                "translation": natives[0].translation if natives else None,
                "in_progress": progress is not None,
                "unlocked": bool(progress.unlocked) if progress else False,
                "probability": float(progress.probability) if progress else None,
                "added_at": added.added_at.isoformat() if added and added.added_at else None,
            }
        )
    entries.sort(key=lambda e: (not e["in_progress"], e["text"]))
    return {"entries": entries}


@router.post("/manage/{word_id}/delete")
async def delete_user_word(
    word_id: int,
    request: Request,
    payload: DeleteUserWordPayload,
    auth: AuthContext = Depends(require_auth_context),
    db: AsyncSession = Depends(get_db),
):
    validate_csrf(request, payload.csrf_token)
    pair_key = payload.language_pair.lower()

    await db.execute(
        delete(UserAddedWord).where(
            UserAddedWord.user_id == auth.user.id,
            UserAddedWord.word_id == word_id,
            UserAddedWord.language_pair == pair_key,
        )
    )
    await db.execute(
        delete(UserProgress).where(
            UserProgress.user_id == auth.user.id,
            UserProgress.item_type == ProgressItemType.WORD,
            UserProgress.item_id == word_id,
            UserProgress.language_pair == pair_key,
        )
    )
    await db.commit()
    return {"ok": True}


@router.post("/add-offline")
async def add_word_offline(
    request: Request,
    payload: AddWordOfflinePayload,
    auth: AuthContext = Depends(require_auth_context),
    db: AsyncSession = Depends(get_db),
):
    validate_csrf(request, payload.csrf_token)
    pair_key = f"{payload.learning_lang_code.lower()}_{payload.mother_lang_code.lower()}"
    learning, mother = await _resolve_language_pair(db, pair_key)

    learning_text = payload.learning_text.strip().lower()
    native_text = payload.native_text.strip()
    if not learning_text or not native_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both words are required",
        )

    word_lookup = await db.execute(
        select(Word).where(Word.text == learning_text, Word.language_id == learning.id)
    )
    word = word_lookup.scalar_one_or_none()
    if word is None:
        word = Word(text=learning_text, language_id=learning.id)
        db.add(word)
        await db.flush()

    lex_lookup = await db.execute(
        select(WordLexicalEntry).where(WordLexicalEntry.word_id == word.id)
    )
    lex = lex_lookup.scalar_one_or_none()
    if lex is None:
        lex = WordLexicalEntry(
            word_id=word.id,
            definition=native_text,
            synonyms=[],
            examples=[],
            source="manual",
        )
        db.add(lex)
        await db.flush()

    native_lookup = await db.execute(
        select(WordNativeTranslation).where(
            WordNativeTranslation.word_id == word.id,
            WordNativeTranslation.native_language_id == mother.id,
            WordNativeTranslation.translation == native_text,
        )
    )
    if native_lookup.scalar_one_or_none() is None:
        db.add(
            WordNativeTranslation(
                word_id=word.id,
                native_language_id=mother.id,
                translation=native_text,
                note=payload.note,
                source="manual",
                priority=0,
            )
        )
        await db.flush()

    existing_added = await db.execute(
        select(UserAddedWord).where(
            UserAddedWord.user_id == auth.user.id,
            UserAddedWord.word_id == word.id,
            UserAddedWord.language_pair == pair_key,
        )
    )
    added = existing_added.scalar_one_or_none()
    if added is None:
        added = UserAddedWord(
            user_id=auth.user.id,
            word_id=word.id,
            language_pair=pair_key,
            context_hint=payload.note,
        )
        db.add(added)
        await db.flush()

    preference = await ensure_user_preference(db, auth.user.id)
    force_unlocked = False
    if preference.force_unlock_added_words:
        existing_progress = await db.execute(
            select(UserProgress).where(
                UserProgress.user_id == auth.user.id,
                UserProgress.item_type == ProgressItemType.WORD,
                UserProgress.item_id == word.id,
                UserProgress.language_pair == pair_key,
            )
        )
        if existing_progress.scalar_one_or_none() is None:
            db.add(
                UserProgress(
                    user_id=auth.user.id,
                    item_type=ProgressItemType.WORD,
                    item_id=word.id,
                    language_pair=pair_key,
                    probability=1000.0,
                    unlocked=True,
                    extra_data={"source": "user_added_manual"},
                )
            )
            force_unlocked = True

    await db.commit()
    return {
        "ok": True,
        "word_id": word.id,
        "text": word.text,
        "translation": native_text,
        "language_pair": pair_key,
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
    existing_lex = await db.execute(
        select(WordLexicalEntry).where(WordLexicalEntry.word_id == word.id)
    )
    existing = existing_lex.scalar_one_or_none()
    if existing is not None and existing.extended_content:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Extended content already exists for this word.",
        )
    try:
        lexical = await expand_word(db, word=word, learning_lang=learning, user_id=auth.user.id)
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
