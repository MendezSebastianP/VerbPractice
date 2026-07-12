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
from dataclasses import dataclass

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
class OcrResult:
    text: str
    lines: list[str]
    mean_confidence: float | None


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


def _run(engine, img: np.ndarray) -> OcrResult:
    try:
        output = engine(img)
    except Exception as exc:
        raise OcrError("OCR failed to process the image.") from exc

    lines: list[str] = []
    scores: list[float] = []
    for text, score in zip(output.txts or (), output.scores or ()):
        line = text.strip()
        if not line or float(score) < _MIN_LINE_SCORE:
            continue
        lines.append(line)
        scores.append(float(score))

    # Scores are 0-1; the API contract (and frontend threshold) is 0-100.
    mean_confidence = round(sum(scores) / len(scores) * 100, 1) if scores else None
    return OcrResult(text="\n".join(lines), lines=lines, mean_confidence=mean_confidence)


def _extract_sync(data: bytes, lang_code: str) -> OcrResult:
    model_key = OCR_LANG_BY_CODE.get(lang_code)
    if model_key is None:
        raise OcrError(f"Unsupported OCR language: {lang_code}")
    img = _preprocess(data)
    return _run(_get_engine(model_key), img)


async def extract_text(data: bytes, lang_code: str) -> OcrResult:
    async with _OCR_SEMAPHORE:
        return await asyncio.to_thread(_extract_sync, data, lang_code)
