import asyncio
import io
import shutil

import pytest
from PIL import Image, ImageDraw, ImageFont, ImageStat

from app.services.ocr_service import (
    TESSERACT_LANG_BY_CODE,
    OcrError,
    _preprocess,
    extract_subtitle_text,
)

TESSERACT_MISSING = shutil.which("tesseract") is None


def _to_bytes(img: Image.Image, fmt: str = "JPEG") -> bytes:
    buffer = io.BytesIO()
    img.save(buffer, fmt, quality=90)
    return buffer.getvalue()


def _subtitle_image(text: str) -> bytes:
    """A synthetic TV frame: dark background, white subtitle with black stroke."""
    img = Image.new("RGB", (1280, 720), (25, 22, 30))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42
        )
    except OSError:
        font = ImageFont.load_default(size=42)
    draw.text((160, 600), text, font=font, fill="white", stroke_width=3, stroke_fill="black")
    return _to_bytes(img)


def test_language_mapping_covers_app_languages():
    assert TESSERACT_LANG_BY_CODE == {"en": "eng", "es": "spa", "fr": "fra", "ru": "rus"}


def test_preprocess_downscales_and_grayscales():
    big = Image.new("RGB", (4000, 2200), (120, 130, 140))
    processed = _preprocess(_to_bytes(big))
    assert processed.mode == "L"
    assert max(processed.size) <= 1600


def test_preprocess_inverts_dark_images():
    dark = Image.new("RGB", (400, 300), (10, 10, 10))
    draw = ImageDraw.Draw(dark)
    draw.rectangle((0, 0, 60, 300), fill=(240, 240, 240))
    processed = _preprocess(_to_bytes(dark))
    assert ImageStat.Stat(processed).mean[0] > 128


def test_preprocess_rejects_garbage_bytes():
    with pytest.raises(OcrError):
        _preprocess(b"definitely not an image")


def test_preprocess_rejects_huge_resolution():
    huge = Image.new("L", (9000, 7000), 128)
    with pytest.raises(OcrError):
        _preprocess(_to_bytes(huge, fmt="PNG"))


@pytest.mark.skipif(TESSERACT_MISSING, reason="tesseract binary not installed")
def test_extract_reads_subtitle_image():
    data = _subtitle_image("the quick brown fox jumps")
    result = asyncio.run(extract_subtitle_text(data, "eng"))
    found = result.text.lower()
    for word in ("quick", "brown", "fox"):
        assert word in found
    assert result.lines
    assert result.mean_confidence is not None and result.mean_confidence > 40


@pytest.mark.skipif(TESSERACT_MISSING, reason="tesseract binary not installed")
def test_extract_garbage_raises_ocr_error():
    with pytest.raises(OcrError):
        asyncio.run(extract_subtitle_text(b"not an image", "eng"))
