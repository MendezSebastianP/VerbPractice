import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.services.ocr_service import MAX_UPLOAD_BYTES, OcrResult, OcrUnavailableError


def _login(client: TestClient, smoke_user: dict) -> str:
    bootstrap = client.get("/api/bootstrap")
    bootstrap.raise_for_status()
    csrf_token = bootstrap.json()["csrf_token"]
    response = client.post(
        "/api/auth/login",
        json={
            "username": smoke_user["username"],
            "password": smoke_user["password"],
            "csrf_token": csrf_token,
        },
    )
    response.raise_for_status()
    return response.json()["csrf_token"]


def _jpeg_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (64, 64), (30, 30, 30)).save(buffer, "JPEG")
    return buffer.getvalue()


async def _fake_extract(data: bytes, lang: str) -> OcrResult:
    return OcrResult(text="hola mundo", lines=["hola mundo"], mean_confidence=91.5)


def test_ocr_endpoint_returns_extracted_text(client, smoke_user, monkeypatch):
    monkeypatch.setattr("app.routers.words.extract_text", _fake_extract)
    csrf_token = _login(client, smoke_user)
    response = client.post(
        "/api/words/ocr",
        files={"image": ("subtitle.jpg", _jpeg_bytes(), "image/jpeg")},
        data={"csrf_token": csrf_token, "lang_code": "es"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["text"] == "hola mundo"
    assert payload["lines"] == ["hola mundo"]
    assert payload["mean_confidence"] == 91.5
    assert payload["ocr_lang"] == "es"


def test_ocr_endpoint_rejects_bad_csrf(client, smoke_user):
    _login(client, smoke_user)
    response = client.post(
        "/api/words/ocr",
        files={"image": ("subtitle.jpg", _jpeg_bytes(), "image/jpeg")},
        data={"csrf_token": "wrong-token", "lang_code": "es"},
    )
    assert response.status_code == 400


def test_ocr_endpoint_rejects_unknown_language(client, smoke_user):
    csrf_token = _login(client, smoke_user)
    response = client.post(
        "/api/words/ocr",
        files={"image": ("subtitle.jpg", _jpeg_bytes(), "image/jpeg")},
        data={"csrf_token": csrf_token, "lang_code": "de"},
    )
    assert response.status_code == 400
    assert "Unsupported OCR language" in response.json()["detail"]


def test_ocr_endpoint_rejects_non_image_upload(client, smoke_user):
    csrf_token = _login(client, smoke_user)
    response = client.post(
        "/api/words/ocr",
        files={"image": ("notes.txt", b"plain text", "text/plain")},
        data={"csrf_token": csrf_token, "lang_code": "es"},
    )
    assert response.status_code == 400


def test_ocr_endpoint_rejects_oversized_upload(client, smoke_user):
    csrf_token = _login(client, smoke_user)
    oversized = b"\xff" * (MAX_UPLOAD_BYTES + 1)
    response = client.post(
        "/api/words/ocr",
        files={"image": ("subtitle.jpg", oversized, "image/jpeg")},
        data={"csrf_token": csrf_token, "lang_code": "es"},
    )
    assert response.status_code == 413


def test_ocr_endpoint_maps_missing_engine_to_503(client, smoke_user, monkeypatch):
    async def _unavailable(data: bytes, lang: str) -> OcrResult:
        raise OcrUnavailableError("RapidOCR is not installed.")

    monkeypatch.setattr("app.routers.words.extract_text", _unavailable)
    csrf_token = _login(client, smoke_user)
    response = client.post(
        "/api/words/ocr",
        files={"image": ("subtitle.jpg", _jpeg_bytes(), "image/jpeg")},
        data={"csrf_token": csrf_token, "lang_code": "es"},
    )
    assert response.status_code == 503


def test_ocr_endpoint_requires_auth(client, smoke_user):
    response = client.post(
        "/api/words/ocr",
        files={"image": ("subtitle.jpg", _jpeg_bytes(), "image/jpeg")},
        data={"csrf_token": "anything", "lang_code": "es"},
        follow_redirects=False,
    )
    assert response.status_code == 303
