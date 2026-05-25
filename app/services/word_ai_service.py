from __future__ import annotations

import json
from dataclasses import dataclass

from openai import AsyncOpenAI
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.languages import language_display_name
from app.core.tags import TAG_BY_SLUG, WORD_ITEM, tag_prompt_list, tag_slugs_for_item_type
from app.db.models import (
    Language,
    Word,
    WordLexicalEntry,
    WordNativeTranslation,
)

WORD_AI_MODEL = "gpt-4o"
WORD_AI_SOURCE = "openai_gpt4o"


class WordAIError(RuntimeError):
    pass


@dataclass(slots=True)
class TranslatedWord:
    status: str  # "exact" | "corrected" | "ambiguous" | "not_found"
    word: Word | None = None
    lexical: WordLexicalEntry | None = None
    natives: list[WordNativeTranslation] | None = None
    general_note: str | None = None
    suggested_tags: list[str] | None = None
    detected_input_language: str | None = None
    original_input: str | None = None
    suggestions: list[str] | None = None
    fresh_lexical: bool = False
    fresh_natives: bool = False


def _system_prompt(learning_lang: Language, mother_tongue: Language) -> str:
    target = language_display_name(learning_lang.code)
    native = language_display_name(mother_tongue.code)
    tag_list = tag_prompt_list(WORD_ITEM)
    return (
        f"You are a careful bilingual lexicographer. The user's target language is {target} "
        f"and their mother tongue is {native}.\n"
        "\n"
        "When given a word or short phrase, return ONE strict JSON object describing what you "
        "found. The 'status' field controls the rest of the payload:\n"
        "\n"
        '  - status="exact": the input is a clean word in the target language. Fill all fields.\n'
        '  - status="corrected": the input has a small typo; you recognized the intended word. '
        "Fill all fields with the corrected form. Include 'original_input' verbatim.\n"
        '  - status="ambiguous": the input could mean multiple distinct things. Fill all fields '
        "for the most likely meaning and use native_translations to capture each sense.\n"
        '  - status="not_found": the input does not match any real word in the target language '
        "after considering close-by spellings. Return ONLY {status, suggestions} and stop.\n"
        "\n"
        "JSON shape for exact / corrected / ambiguous:\n"
        f'  - status (str): one of "exact" | "corrected" | "ambiguous"\n'
        "  - original_input (str): the raw text the user typed. Required for corrected.\n"
        f'  - detected_input_language (str): ISO code in upper case of the language the input '
        f'appears to be in (e.g. "{learning_lang.code}", "{mother_tongue.code}"). The user may '
        "have typed in their mother tongue intending a translation request — report what you "
        "detect, do not silently assume target language.\n"
        f"  - canonical_text (str): the canonical {target} form: lowercase, no surrounding "
        "articles or punctuation, with diacritics restored.\n"
        f"  - definition (str): 1-2 sentences entirely in {target}, learner-friendly.\n"
        "  - synonyms (array): 0 to 5 entries, each {text, gloss}. text is a real "
        f"{target} synonym a native speaker would actually use; gloss is a short {native} "
        "gloss. **Return ONLY synonyms that genuinely exist.** If there is one good synonym, "
        "return one. If there are none, return an empty array. Do NOT invent or pad.\n"
        f"  - examples (array of str): 1 to 3 natural {target} sentences. Do NOT pad to three. "
        "If the user's context contained grammatical errors, silently use the correct form in "
        "your examples — do not mirror their mistakes.\n"
        f"  - native_translations (array): 1 to 3 entries, each {{translation, note}}. "
        f"translation is in {native}; note is an optional short {native} caveat (figurative "
        "vs. literal sense, register, regional). If there is only one good translation, "
        "return one. Multiple entries should reflect genuinely distinct senses.\n"
        f"  - general_note (str): optional top-level note in {native} (gender, irregular "
        "plural, false friend with a similar word in the mother tongue, etc.). Empty if none.\n"
        f"  - suggested_tags (array of str): 0 to 5 tags from this controlled list ONLY: "
        f"[{tag_list}]. Prefer one thematic tag plus one grammatical tag when obvious. "
        "For verbs, include verb_action or verb_state and, if useful, one verb_semantic tag. "
        "Skip if uncertain - do not invent tags outside this list.\n"
        "\n"
        "JSON shape for not_found:\n"
        '  - status: "not_found"\n'
        f"  - suggestions (array of str): 0 to 3 plausible {target} words the user may have "
        "meant. Empty array if no good guesses. Words only, no explanation.\n"
        "\n"
        "Always emit valid JSON. No prose outside the JSON object."
    )


def _native_only_prompt(learning_lang: Language, mother_tongue: Language) -> str:
    target = language_display_name(learning_lang.code)
    native = language_display_name(mother_tongue.code)
    return (
        f"You are a careful bilingual lexicographer. The user's target language is {target} "
        f"and their mother tongue is {native}. The {target}-side lexical entry already exists "
        "in our database — only generate the mother-tongue side.\n"
        "\n"
        "Return strict JSON:\n"
        f"  - native_translations (array): 1 to 3 entries, each {{translation, note}}. "
        f"translation is in {native}; note is a short {native} caveat (figurative vs. literal, "
        "register, regional). Return only genuinely distinct senses; do not pad.\n"
        f"  - general_note (str): optional top-level {native} note (gender, false friend, "
        "etc.). Empty if none.\n"
        "\n"
        "No prose outside the JSON object."
    )


def _expand_prompt(learning_lang: Language) -> str:
    return (
        f"You are an expert in {language_display_name(learning_lang.code)}. Given a word and its "
        "existing definition, append additional learning content in the target language: "
        "etymology (if interesting), register (formal/informal/slang), regional variants, "
        "common collocations, and 1-2 advanced example sentences. Plain text, no JSON, "
        "no headings, max 250 words."
    )


async def _call_openai_json(client: AsyncOpenAI, system: str, user: str) -> dict:
    response = await client.chat.completions.create(
        model=WORD_AI_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    if not response.choices:
        raise WordAIError("AI returned no choices")
    content = response.choices[0].message.content or "{}"
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise WordAIError(f"AI returned invalid JSON: {exc}") from exc


async def _call_openai_text(client: AsyncOpenAI, system: str, user: str) -> str:
    response = await client.chat.completions.create(
        model=WORD_AI_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    if not response.choices:
        raise WordAIError("AI returned no choices")
    return response.choices[0].message.content or ""


def _user_message(input_text: str, context: str | None) -> str:
    if context:
        return f"Word/phrase: {input_text}\nContext: {context}"
    return f"Word/phrase: {input_text}"


def _normalise_native_entries(raw: object) -> list[dict]:
    if not isinstance(raw, list):
        return []
    cleaned: list[dict] = []
    for item in raw[:3]:
        if isinstance(item, dict):
            translation = str(item.get("translation") or "").strip()
            if not translation:
                continue
            note = str(item.get("note") or "").strip() or None
            cleaned.append({"translation": translation, "note": note})
        elif isinstance(item, str):
            text = item.strip()
            if text:
                cleaned.append({"translation": text, "note": None})
    return cleaned


def _normalise_tags(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    allowed = set(tag_slugs_for_item_type(WORD_ITEM))
    return [t for t in raw if isinstance(t, str) and t in allowed][:5]


async def translate_word(
    db: AsyncSession,
    *,
    input_text: str,
    learning_lang: Language,
    mother_tongue: Language,
    context: str | None = None,
    force: bool = False,
) -> TranslatedWord:
    if not settings.openai_api_key:
        raise WordAIError("OPENAI_API_KEY is not configured")

    cleaned_input = input_text.strip()
    if not cleaned_input:
        raise WordAIError("Empty input")

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    word_row = None
    lexical = None
    if not force:
        word_lookup = await db.execute(
            select(Word).where(
                Word.text == cleaned_input.lower(),
                Word.language_id == learning_lang.id,
            )
        )
        word_row = word_lookup.scalar_one_or_none()
        if word_row is not None:
            lex_lookup = await db.execute(
                select(WordLexicalEntry).where(WordLexicalEntry.word_id == word_row.id)
            )
            lexical = lex_lookup.scalar_one_or_none()

    # Path 1: full miss (or force) — call full-add prompt
    if lexical is None or force:
        payload = await _call_openai_json(
            client,
            _system_prompt(learning_lang, mother_tongue),
            _user_message(cleaned_input, context),
        )
        status = str(payload.get("status") or "exact").lower()

        if status == "not_found":
            suggestions_raw = payload.get("suggestions") or []
            suggestions = [
                str(s).strip() for s in suggestions_raw if isinstance(s, str) and s.strip()
            ][:3]
            return TranslatedWord(status="not_found", suggestions=suggestions)

        if status not in ("exact", "corrected", "ambiguous"):
            status = "exact"  # be forgiving with model deviations

        canonical = str(payload.get("canonical_text") or cleaned_input).strip().lower()
        definition = str(payload.get("definition") or "").strip()
        synonyms = payload.get("synonyms") or []
        examples = payload.get("examples") or []
        general_note = str(payload.get("general_note") or "").strip() or None
        natives_raw = _normalise_native_entries(payload.get("native_translations"))
        detected_lang = str(payload.get("detected_input_language") or "").strip().upper() or None
        original_input = str(payload.get("original_input") or "").strip() or None
        suggested_tags = _normalise_tags(payload.get("suggested_tags"))

        if not definition or not natives_raw:
            raise WordAIError("AI response missing required fields (definition, native_translations)")

        # If a Word with the canonical_text already exists for this lang, reuse it.
        if word_row is None or (word_row.text != canonical and not force):
            existing_lookup = await db.execute(
                select(Word).where(
                    Word.text == canonical,
                    Word.language_id == learning_lang.id,
                )
            )
            existing_word = existing_lookup.scalar_one_or_none()
            if existing_word is not None:
                word_row = existing_word
                lex_lookup = await db.execute(
                    select(WordLexicalEntry).where(WordLexicalEntry.word_id == word_row.id)
                )
                lexical = lex_lookup.scalar_one_or_none()
            elif word_row is None:
                word_row = Word(text=canonical, language_id=learning_lang.id)
                db.add(word_row)
                await db.flush()

        fresh_lexical = False
        if lexical is None:
            lexical = WordLexicalEntry(
                word_id=word_row.id,
                definition=definition,
                synonyms=synonyms if isinstance(synonyms, list) else [],
                examples=examples if isinstance(examples, list) else [],
                source=WORD_AI_SOURCE,
            )
            db.add(lexical)
            fresh_lexical = True
        else:
            lexical.definition = definition
            lexical.synonyms = synonyms if isinstance(synonyms, list) else []
            lexical.examples = examples if isinstance(examples, list) else []
            lexical.source = WORD_AI_SOURCE

        # Replace native translations for this (word, mother_tongue) when fresh/forced.
        if force or not await _has_natives(db, word_row.id, mother_tongue.id):
            if force:
                await db.execute(
                    delete(WordNativeTranslation).where(
                        WordNativeTranslation.word_id == word_row.id,
                        WordNativeTranslation.native_language_id == mother_tongue.id,
                    )
                )
            natives = await _insert_natives(
                db,
                word_id=word_row.id,
                native_lang_id=mother_tongue.id,
                entries=natives_raw,
            )
            fresh_natives = True
        else:
            natives = await _load_natives(db, word_row.id, mother_tongue.id)
            fresh_natives = False

        await db.flush()
        await _attach_word_tags(db, word_id=word_row.id, tag_slugs=suggested_tags)
        return TranslatedWord(
            status=status,
            word=word_row,
            lexical=lexical,
            natives=natives,
            general_note=general_note,
            suggested_tags=suggested_tags,
            detected_input_language=detected_lang,
            original_input=original_input,
            fresh_lexical=fresh_lexical,
            fresh_natives=fresh_natives,
        )

    # Path 2: lexical cache hit; check native rows
    existing_natives = await _load_natives(db, word_row.id, mother_tongue.id)
    if existing_natives:
        return TranslatedWord(
            status="exact",
            word=word_row,
            lexical=lexical,
            natives=existing_natives,
            fresh_lexical=False,
            fresh_natives=False,
        )

    native_payload = await _call_openai_json(
        client,
        _native_only_prompt(learning_lang, mother_tongue),
        _user_message(cleaned_input, context),
    )
    natives_raw = _normalise_native_entries(native_payload.get("native_translations"))
    general_note = str(native_payload.get("general_note") or "").strip() or None
    if not natives_raw:
        raise WordAIError("AI native translations missing")
    natives = await _insert_natives(
        db,
        word_id=word_row.id,
        native_lang_id=mother_tongue.id,
        entries=natives_raw,
    )
    await db.flush()
    return TranslatedWord(
        status="exact",
        word=word_row,
        lexical=lexical,
        natives=natives,
        general_note=general_note,
        fresh_lexical=False,
        fresh_natives=True,
    )


async def _has_natives(db: AsyncSession, word_id: int, native_lang_id: int) -> bool:
    result = await db.execute(
        select(WordNativeTranslation.id).where(
            WordNativeTranslation.word_id == word_id,
            WordNativeTranslation.native_language_id == native_lang_id,
        ).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def _load_natives(
    db: AsyncSession, word_id: int, native_lang_id: int
) -> list[WordNativeTranslation]:
    result = await db.execute(
        select(WordNativeTranslation)
        .where(
            WordNativeTranslation.word_id == word_id,
            WordNativeTranslation.native_language_id == native_lang_id,
        )
        .order_by(WordNativeTranslation.priority.asc(), WordNativeTranslation.id.asc())
    )
    return list(result.scalars().all())


async def _insert_natives(
    db: AsyncSession,
    *,
    word_id: int,
    native_lang_id: int,
    entries: list[dict],
) -> list[WordNativeTranslation]:
    rows: list[WordNativeTranslation] = []
    for idx, entry in enumerate(entries):
        row = WordNativeTranslation(
            word_id=word_id,
            native_language_id=native_lang_id,
            translation=entry["translation"],
            note=entry.get("note"),
            source=WORD_AI_SOURCE,
            priority=idx,
        )
        db.add(row)
        rows.append(row)
    await db.flush()
    return rows


async def _attach_word_tags(
    db: AsyncSession, *, word_id: int, tag_slugs: list[str]
) -> None:
    """Idempotent tag attachment. Imported lazily to avoid circular models."""
    from app.db.models import Tag, WordTag

    if not tag_slugs:
        return
    tag_lookup = await db.execute(select(Tag).where(Tag.slug.in_(tag_slugs)))
    by_slug = {t.slug: t for t in tag_lookup.scalars().all()}
    for slug in tag_slugs:
        if slug in by_slug or slug not in TAG_BY_SLUG:
            continue
        tag_def = TAG_BY_SLUG[slug]
        tag = Tag(
            slug=tag_def.slug,
            display_name=tag_def.display_name,
            kind=tag_def.kind,
            applies_to=list(tag_def.applies_to),
        )
        db.add(tag)
        await db.flush()
        by_slug[slug] = tag
    existing_lookup = await db.execute(
        select(WordTag.tag_id).where(WordTag.word_id == word_id)
    )
    existing_tag_ids = {row[0] for row in existing_lookup.all()}
    for slug in tag_slugs:
        tag = by_slug.get(slug)
        if tag is None or tag.id in existing_tag_ids:
            continue
        db.add(WordTag(word_id=word_id, tag_id=tag.id, source="ai_suggested"))
    await db.flush()


async def expand_word(
    db: AsyncSession,
    *,
    word: Word,
    learning_lang: Language,
) -> WordLexicalEntry:
    if not settings.openai_api_key:
        raise WordAIError("OPENAI_API_KEY is not configured")
    lex_lookup = await db.execute(
        select(WordLexicalEntry).where(WordLexicalEntry.word_id == word.id)
    )
    lexical = lex_lookup.scalar_one_or_none()
    if lexical is None:
        raise WordAIError("Lexical entry not found")

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    addition = await _call_openai_text(
        client,
        _expand_prompt(learning_lang),
        f"Word: {word.text}\nExisting definition: {lexical.definition}",
    )
    addition = addition.strip()
    if not addition:
        return lexical
    if lexical.extended_content:
        lexical.extended_content = f"{lexical.extended_content}\n\n{addition}"
    else:
        lexical.extended_content = addition
    return lexical
