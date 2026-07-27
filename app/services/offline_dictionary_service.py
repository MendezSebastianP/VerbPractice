from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from threading import Lock

import numpy as np
import onnxruntime as ort
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.models import Word, WordSense, WordSenseTranslation


LOGGER = logging.getLogger(__name__)
MODEL_NAME = "intfloat/multilingual-e5-small"
MODEL_FILE = "model_qint8_avx512_vnni.onnx"
_WORD_RE = re.compile(r"[^\W\d_]+", flags=re.UNICODE)


@dataclass(slots=True)
class RankedSense:
    sense: WordSense
    translations: list[WordSenseTranslation]
    method: str
    score: float | None = None
    margin: float | None = None
    alternatives: list[WordSense] | None = None


class LocalSenseRanker:
    """Lazy, CPU-only multilingual E5 inference with a lexical fallback."""

    def __init__(self, model_dir: str | Path) -> None:
        self.model_dir = Path(model_dir)
        self._session: ort.InferenceSession | None = None
        self._tokenizer = None
        self._load_attempted = False
        self._lock = Lock()

    @property
    def available(self) -> bool:
        return self._ensure_loaded()

    @property
    def configured(self) -> bool:
        return (
            settings.offline_sense_model_enabled
            and (self.model_dir / "tokenizer.json").is_file()
            and self._resolve_model_path().is_file()
        )

    def _resolve_model_path(self) -> Path:
        nested = self.model_dir / "onnx" / MODEL_FILE
        return nested if nested.exists() else self.model_dir / MODEL_FILE

    def _ensure_loaded(self) -> bool:
        if self._session is not None and self._tokenizer is not None:
            return True
        if not settings.offline_sense_model_enabled:
            return False
        with self._lock:
            if self._session is not None and self._tokenizer is not None:
                return True
            if self._load_attempted:
                return False
            self._load_attempted = True
            tokenizer_path = self.model_dir / "tokenizer.json"
            model_path = self._resolve_model_path()
            if not tokenizer_path.exists() or not model_path.exists():
                LOGGER.info(
                    "Offline sense model is not installed at %s; using lexical ranking",
                    self.model_dir,
                )
                return False
            try:
                from tokenizers import Tokenizer

                tokenizer = Tokenizer.from_file(str(tokenizer_path))
                tokenizer.enable_truncation(max_length=128)
                options = ort.SessionOptions()
                options.intra_op_num_threads = min(6, max(1, os.cpu_count() or 1))
                options.inter_op_num_threads = 1
                options.enable_cpu_mem_arena = False
                options.enable_mem_pattern = False
                session = ort.InferenceSession(
                    str(model_path),
                    sess_options=options,
                    providers=["CPUExecutionProvider"],
                )
            except Exception:
                LOGGER.exception("Unable to load offline sense model from %s", self.model_dir)
                return False
            self._tokenizer = tokenizer
            self._session = session
            return True

    def would_truncate(self, texts: list[str], *, kind: str) -> bool:
        if not texts or not self._ensure_loaded():
            return False
        assert self._tokenizer is not None
        prefix = "query: " if kind == "query" else "passage: "
        encodings = self._tokenizer.encode_batch([f"{prefix}{text}" for text in texts])
        return any(encoding.overflowing for encoding in encodings)

    def encode(self, texts: list[str], *, kind: str) -> np.ndarray | None:
        if not texts or not self._ensure_loaded():
            return None
        assert self._tokenizer is not None and self._session is not None
        prefix = "query: " if kind == "query" else "passage: "
        encodings = self._tokenizer.encode_batch([f"{prefix}{text}" for text in texts])
        max_length = max(len(encoding.ids) for encoding in encodings)

        def padded(values: list[int], fill: int = 0) -> list[int]:
            return values + [fill] * (max_length - len(values))

        input_ids = np.asarray([padded(e.ids) for e in encodings], dtype=np.int64)
        attention_mask = np.asarray(
            [padded(e.attention_mask) for e in encodings], dtype=np.int64
        )
        token_type_ids = np.asarray(
            [padded(e.type_ids) for e in encodings], dtype=np.int64
        )
        available = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "token_type_ids": token_type_ids,
        }
        feeds = {
            input_meta.name: available[input_meta.name]
            for input_meta in self._session.get_inputs()
        }
        hidden = self._session.run(None, feeds)[0]
        mask = attention_mask.astype(np.float32)[..., None]
        pooled = (hidden * mask).sum(axis=1) / np.maximum(mask.sum(axis=1), 1e-9)
        return pooled / np.maximum(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-9)

    def rank(
        self,
        *,
        context: str,
        senses: list[WordSense],
        translations_by_sense: dict[int, list[WordSenseTranslation]],
    ) -> tuple[list[int], list[float], str]:
        candidate_texts = [
            _sense_text(sense, translations_by_sense.get(sense.id, []))
            for sense in senses
        ]
        candidate_vectors = self.encode(candidate_texts, kind="passage")
        query_vector = self.encode([context], kind="query")
        if candidate_vectors is not None and query_vector is not None:
            scores = (candidate_vectors @ query_vector[0]).tolist()
            order = sorted(range(len(senses)), key=scores.__getitem__, reverse=True)
            return order, [float(score) for score in scores], MODEL_NAME

        scores = [_lexical_score(context, text) for text in candidate_texts]
        order = sorted(
            range(len(senses)),
            key=lambda index: (scores[index], senses[index].is_primary, -senses[index].id),
            reverse=True,
        )
        return order, scores, "lexical_overlap"


def _sense_text(
    sense: WordSense, translations: list[WordSenseTranslation]
) -> str:
    pieces = [sense.definition]
    pieces.extend(sense.examples or [])
    for synonym in sense.synonyms or []:
        if isinstance(synonym, str):
            pieces.append(synonym)
        elif isinstance(synonym, dict):
            pieces.extend(
                str(value)
                for key, value in synonym.items()
                if key in {"text", "gloss"} and value
            )
    pieces.extend(item.translation for item in translations)
    return ". ".join(piece.strip() for piece in pieces if piece and piece.strip())


def _lexical_score(left: str, right: str) -> float:
    left_words = set(_WORD_RE.findall(left.casefold()))
    right_words = set(_WORD_RE.findall(right.casefold()))
    union = left_words | right_words
    return len(left_words & right_words) / len(union) if union else 0.0


@lru_cache(maxsize=1)
def get_local_sense_ranker() -> LocalSenseRanker:
    return LocalSenseRanker(settings.offline_sense_model_dir)


async def find_ranked_sense(
    db: AsyncSession,
    *,
    word: Word,
    target_language_id: int,
    context: str | None,
) -> RankedSense | None:
    result = await db.execute(
        select(WordSense)
        .options(selectinload(WordSense.translations))
        .where(WordSense.word_id == word.id)
        .order_by(WordSense.is_primary.desc(), WordSense.id.asc())
    )
    all_senses = list(result.scalars().unique().all())
    translations_by_sense = {
        sense.id: sorted(
            [
                item
                for item in sense.translations
                if item.target_language_id == target_language_id
            ],
            key=lambda item: (item.priority, item.id),
        )
        for sense in all_senses
    }
    translated_senses = [
        sense for sense in all_senses if translations_by_sense[sense.id]
    ]
    trusted_senses = [sense for sense in translated_senses if sense.is_trusted]
    cleaned_context = (context or "").strip()
    senses = trusted_senses
    if not senses:
        return None

    if not cleaned_context or len(senses) == 1:
        selected = senses[0]
        return RankedSense(
            sense=selected,
            translations=translations_by_sense[selected.id],
            method="primary" if len(senses) > 1 else "single_sense",
            alternatives=senses[1:],
        )

    ranker = get_local_sense_ranker()
    order, scores, method = await asyncio.to_thread(
        ranker.rank,
        context=cleaned_context,
        senses=senses,
        translations_by_sense=translations_by_sense,
    )
    selected_index = order[0]
    runner_score = scores[order[1]] if len(order) > 1 else None
    selected = senses[selected_index]
    return RankedSense(
        sense=selected,
        translations=translations_by_sense[selected.id],
        method=method,
        score=scores[selected_index],
        margin=(
            scores[selected_index] - runner_score
            if runner_score is not None
            else None
        ),
        alternatives=[senses[index] for index in order[1:]],
    )


async def select_dictionary_sense(
    db: AsyncSession,
    *,
    word: Word,
    target_language_id: int,
    sense_id: int,
) -> RankedSense | None:
    """Return a user-selected sense, provided it belongs to this word/pair."""

    result = await db.execute(
        select(WordSense)
        .options(selectinload(WordSense.translations))
        .where(WordSense.word_id == word.id)
        .order_by(WordSense.is_primary.desc(), WordSense.id.asc())
    )
    all_senses = list(result.scalars().unique().all())
    translations_by_sense = {
        sense.id: sorted(
            [
                item
                for item in sense.translations
                if item.target_language_id == target_language_id
            ],
            key=lambda item: (item.priority, item.id),
        )
        for sense in all_senses
    }
    eligible = [
        sense
        for sense in all_senses
        if sense.is_trusted and translations_by_sense[sense.id]
    ]
    selected = next((sense for sense in eligible if sense.id == sense_id), None)
    if selected is None:
        return None
    return RankedSense(
        sense=selected,
        translations=translations_by_sense[selected.id],
        method="user_selected",
        alternatives=[sense for sense in eligible if sense.id != selected.id],
    )
