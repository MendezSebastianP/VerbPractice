"""Local OCR for photos of TV subtitles, backed by the tesseract binary.

The whole decode -> preprocess -> OCR pipeline is CPU-bound, so it runs in a
worker thread and a single-slot semaphore keeps concurrent requests from
thrashing the low-resource host.
"""

from __future__ import annotations

import asyncio
import io
from dataclasses import dataclass

import pytesseract
from PIL import Image, ImageOps, ImageStat, UnidentifiedImageError
from pytesseract import Output

# App language codes -> tesseract traineddata names (apt: tesseract-ocr-<name>).
TESSERACT_LANG_BY_CODE = {"en": "eng", "es": "spa", "fr": "fra", "ru": "rus"}

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
_MAX_PIXELS = 40_000_000
_MAX_DIMENSION = 1600
_MIN_LINE_CONFIDENCE = 40.0

_OCR_SEMAPHORE = asyncio.Semaphore(1)


class OcrError(Exception):
    """The image could not be read or processed."""


class OcrUnavailableError(OcrError):
    """Tesseract or the requested language pack is not installed."""


@dataclass(slots=True)
class OcrResult:
    text: str
    lines: list[str]
    mean_confidence: float | None


def _preprocess(data: bytes) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(data))
        if img.width * img.height > _MAX_PIXELS:
            raise OcrError("Image resolution too large.")
        img = ImageOps.exif_transpose(img)
        if max(img.size) > _MAX_DIMENSION:
            img.thumbnail((_MAX_DIMENSION, _MAX_DIMENSION), Image.LANCZOS)
        img = img.convert("L")
    except OcrError:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise OcrError("Not a readable image.") from exc
    img = ImageOps.autocontrast(img, cutoff=1)
    # Subtitles are typically white-on-dark; tesseract prefers dark-on-light.
    if ImageStat.Stat(img).mean[0] < 128:
        img = ImageOps.invert(img)
    return img


def _run_tesseract(img: Image.Image, lang: str) -> OcrResult:
    try:
        # PSM 6: one uniform text block — fits 1-3 subtitle lines better than
        # full page segmentation on a busy TV frame.
        data = pytesseract.image_to_data(
            img, lang=lang, config="--psm 6", output_type=Output.DICT
        )
    except pytesseract.TesseractNotFoundError as exc:
        raise OcrUnavailableError("The tesseract binary is not installed.") from exc
    except pytesseract.TesseractError as exc:
        message = str(exc)
        if "Failed loading language" in message or "tessdata" in message:
            raise OcrUnavailableError(
                f"Tesseract language pack for '{lang}' is not installed."
            ) from exc
        raise OcrError("OCR failed to process the image.") from exc

    grouped: dict[tuple[int, int, int], list[tuple[str, float]]] = {}
    for i, raw_word in enumerate(data["text"]):
        word = raw_word.strip()
        conf = float(data["conf"][i])
        if not word or conf < 0:  # conf == -1 marks non-word boxes
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        grouped.setdefault(key, []).append((word, conf))

    lines: list[str] = []
    confidences: list[float] = []
    for key in sorted(grouped):
        words = grouped[key]
        line_confs = [conf for _, conf in words]
        if sum(line_confs) / len(line_confs) < _MIN_LINE_CONFIDENCE:
            continue
        lines.append(" ".join(word for word, _ in words))
        confidences.extend(line_confs)

    mean_confidence = sum(confidences) / len(confidences) if confidences else None
    return OcrResult(text="\n".join(lines), lines=lines, mean_confidence=mean_confidence)


def _extract_sync(data: bytes, lang: str) -> OcrResult:
    return _run_tesseract(_preprocess(data), lang)


async def extract_subtitle_text(data: bytes, lang: str) -> OcrResult:
    async with _OCR_SEMAPHORE:
        return await asyncio.to_thread(_extract_sync, data, lang)
