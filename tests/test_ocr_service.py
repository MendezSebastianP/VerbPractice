import asyncio
import importlib.util
import io
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from app.services.ocr_service import (
    OCR_LANG_BY_CODE,
    OcrError,
    OcrUnavailableError,
    _preprocess,
    _run,
    extract_text,
)

RAPIDOCR_MISSING = importlib.util.find_spec("rapidocr") is None


def _to_bytes(img: Image.Image, fmt: str = "JPEG") -> bytes:
    buffer = io.BytesIO()
    img.save(buffer, fmt, quality=90)
    return buffer.getvalue()


def _text_image(text: str) -> bytes:
    """A synthetic photo: dark background, white text with black stroke."""
    img = Image.new("RGB", (1280, 720), (25, 22, 30))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42
        )
    except OSError:
        font = ImageFont.load_default(size=42)
    draw.text((160, 340), text, font=font, fill="white", stroke_width=3, stroke_fill="black")
    return _to_bytes(img)


class _FakeEngine:
    def __init__(self, txts, scores):
        self._output = SimpleNamespace(txts=txts, scores=scores)

    def __call__(self, img):
        return self._output


def test_language_mapping_covers_app_languages():
    assert OCR_LANG_BY_CODE == {"en": "en", "es": "latin", "fr": "latin", "ru": "cyrillic"}


def test_preprocess_downscales_and_returns_bgr_array():
    big = Image.new("RGB", (4000, 2200), (120, 130, 140))
    processed = _preprocess(_to_bytes(big))
    assert isinstance(processed, np.ndarray)
    assert processed.ndim == 3 and processed.shape[2] == 3
    assert max(processed.shape[:2]) <= 1600


def test_preprocess_rejects_garbage_bytes():
    with pytest.raises(OcrError):
        _preprocess(b"definitely not an image")


def test_preprocess_rejects_huge_resolution():
    huge = Image.new("L", (9000, 7000), 128)
    with pytest.raises(OcrError):
        _preprocess(_to_bytes(huge, fmt="PNG"))


def test_run_filters_low_score_lines_and_scales_confidence():
    engine = _FakeEngine(["good line", "  ", "noise"], [0.96, 0.9, 0.2])
    result = _run(engine, np.zeros((10, 10, 3), dtype=np.uint8))
    assert result.lines == ["good line"]
    assert result.text == "good line"
    assert result.mean_confidence == 96.0


def test_run_handles_empty_output():
    engine = _FakeEngine(None, None)
    result = _run(engine, np.zeros((10, 10, 3), dtype=np.uint8))
    assert result.text == ""
    assert result.lines == []
    assert result.mean_confidence is None


def test_extract_unknown_language_raises():
    with pytest.raises(OcrError):
        asyncio.run(extract_text(_text_image("hello"), "de"))


@pytest.mark.skipif(RAPIDOCR_MISSING, reason="rapidocr not installed")
def test_extract_reads_text_image():
    data = _text_image("the quick brown fox jumps")
    try:
        result = asyncio.run(extract_text(data, "en"))
    except OcrUnavailableError as exc:
        pytest.skip(f"OCR models unavailable: {exc}")
    found = result.text.lower()
    for word in ("quick", "brown", "fox"):
        assert word in found
    assert result.lines
    assert result.mean_confidence is not None and result.mean_confidence > 50


@pytest.mark.skipif(RAPIDOCR_MISSING, reason="rapidocr not installed")
def test_extract_garbage_raises_ocr_error():
    with pytest.raises(OcrError):
        asyncio.run(extract_text(b"not an image", "en"))
