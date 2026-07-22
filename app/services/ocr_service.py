"""Local OCR for photographed text, backed by RapidOCR (PP-OCR ONNX models).

Engine init and inference are CPU-bound, so they run in a worker thread and a
single-slot semaphore keeps concurrent requests from thrashing the
low-resource host. Engines are cached per recognition model; the first request
for a language downloads its model (~15 MB) into the rapidocr package cache,
after which everything runs fully offline.
"""

from __future__ import annotations

import asyncio
import io
import logging
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

# App language codes -> recognition model family. English rides the newest
# PP-OCRv6 small stack; fr/es share the latin model and ru the cyrillic one
# (both PP-OCRv5 mobile — v6 only ships ch/en).
OCR_LANG_BY_CODE = {"en": "en", "es": "latin", "fr": "latin", "ru": "cyrillic"}

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
_MAX_PIXELS = 40_000_000
_MAX_DIMENSION = 1600
_MIN_LINE_SCORE = 0.5

_OCR_SEMAPHORE = asyncio.Semaphore(1)
_ENGINES: dict[str, object] = {}

logging.getLogger("RapidOCR").setLevel(logging.WARNING)


class OcrError(Exception):
    """The image could not be read or processed."""


class OcrUnavailableError(OcrError):
    """RapidOCR or the requested recognition model is not available."""


@dataclass(slots=True)
class OcrBox:
    """Axis-aligned word bounds normalized to the processed image."""

    x: float
    y: float
    width: float
    height: float


@dataclass(slots=True)
class OcrWord:
    text: str
    confidence: float
    box: OcrBox


@dataclass(slots=True)
class OcrResult:
    text: str
    lines: list[str]
    mean_confidence: float | None
    words: list[OcrWord] = field(default_factory=list)


def _get_engine(model_key: str):
    engine = _ENGINES.get(model_key)
    if engine is not None:
        return engine
    try:
        from rapidocr import LangRec, ModelType, OCRVersion, RapidOCR
    except ImportError as exc:
        raise OcrUnavailableError("RapidOCR is not installed.") from exc

    if model_key == "en":
        params = {"Rec.lang_type": LangRec.EN}
    else:
        lang = LangRec.LATIN if model_key == "latin" else LangRec.CYRILLIC
        params = {
            "Rec.lang_type": lang,
            "Rec.ocr_version": OCRVersion.PPOCRV5,
            "Rec.model_type": ModelType.MOBILE,
        }
    try:
        # RapidOCR already calculates the word geometry while recognizing a
        # line. Keep it enabled so the client can make the photo itself the
        # word-selection surface instead of repeating the text below it.
        params["Global.return_word_box"] = True
        engine = RapidOCR(params=params)
    except Exception as exc:  # model download or engine setup failed
        raise OcrUnavailableError(
            f"OCR model for '{model_key}' is unavailable: {exc}"
        ) from exc
    _ENGINES[model_key] = engine
    return engine


def _preprocess(data: bytes) -> np.ndarray:
    try:
        img = Image.open(io.BytesIO(data))
        if img.width * img.height > _MAX_PIXELS:
            raise OcrError("Image resolution too large.")
        img = ImageOps.exif_transpose(img)
        if max(img.size) > _MAX_DIMENSION:
            img.thumbnail((_MAX_DIMENSION, _MAX_DIMENSION), Image.LANCZOS)
        img = img.convert("RGB")
    except OcrError:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise OcrError("Not a readable image.") from exc
    # rapidocr follows the cv2 convention, so hand it BGR.
    return np.asarray(img)[:, :, ::-1]


def _clean_word(value: str) -> str:
    """Trim surrounding punctuation while preserving internal apostrophes."""

    start = 0
    end = len(value)
    while start < end and not value[start].isalnum():
        start += 1
    while end > start and not value[end - 1].isalnum():
        end -= 1
    return value[start:end]


def _normalized_box(box: object, image_width: int, image_height: int) -> OcrBox | None:
    try:
        points = np.asarray(box, dtype=float).reshape(-1, 2)
    except (TypeError, ValueError):
        return None
    if points.size == 0 or not np.isfinite(points).all():
        return None

    x0 = max(0.0, min(float(points[:, 0].min()), float(image_width)))
    x1 = max(0.0, min(float(points[:, 0].max()), float(image_width)))
    y0 = max(0.0, min(float(points[:, 1].min()), float(image_height)))
    y1 = max(0.0, min(float(points[:, 1].max()), float(image_height)))
    if x1 <= x0 or y1 <= y0:
        return None

    return OcrBox(
        x=round(x0 / image_width, 6),
        y=round(y0 / image_height, 6),
        width=round((x1 - x0) / image_width, 6),
        height=round((y1 - y0) / image_height, 6),
    )


def _run(engine, img: np.ndarray) -> OcrResult:
    try:
        output = engine(img)
    except Exception as exc:
        raise OcrError("OCR failed to process the image.") from exc

    lines: list[str] = []
    scores: list[float] = []
    words: list[OcrWord] = []
    word_lines = getattr(output, "word_results", None) or ()
    image_height, image_width = img.shape[:2]
    for line_index, (text, score) in enumerate(
        zip(output.txts or (), output.scores or ())
    ):
        line = text.strip()
        if not line or float(score) < _MIN_LINE_SCORE:
            continue
        lines.append(line)
        scores.append(float(score))

        line_words = word_lines[line_index] if line_index < len(word_lines) else ()
        for item in line_words:
            if not isinstance(item, (tuple, list)) or len(item) != 3:
                continue
            raw_word, word_score, word_box = item
            word = _clean_word(str(raw_word).strip())
            box = _normalized_box(word_box, image_width, image_height)
            if not word or box is None:
                continue
            words.append(
                OcrWord(
                    text=word,
                    confidence=round(float(word_score) * 100, 1),
                    box=box,
                )
            )

    # Scores are 0-1; the API contract (and frontend threshold) is 0-100.
    mean_confidence = round(sum(scores) / len(scores) * 100, 1) if scores else None
    return OcrResult(
        text="\n".join(lines),
        lines=lines,
        mean_confidence=mean_confidence,
        words=words,
    )


def _extract_sync(data: bytes, lang_code: str) -> OcrResult:
    model_key = OCR_LANG_BY_CODE.get(lang_code)
    if model_key is None:
        raise OcrError(f"Unsupported OCR language: {lang_code}")
    img = _preprocess(data)
    return _run(_get_engine(model_key), img)


async def extract_text(data: bytes, lang_code: str) -> OcrResult:
    async with _OCR_SEMAPHORE:
        return await asyncio.to_thread(_extract_sync, data, lang_code)
