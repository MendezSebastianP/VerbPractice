from __future__ import annotations

import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import Language, Verb, VerbTranslation, Word, WordTranslation
from app.db.session import AsyncSessionLocal

TEST_PASSWORD = "smoke-pass-123"


def _api_login(client: TestClient, username: str, password: str) -> dict:
    bootstrap = client.get("/api/bootstrap")
    bootstrap.raise_for_status()
    csrf_token = bootstrap.json()["csrf_token"]
    response = client.post(
        "/api/auth/login",
        json={
            "username": username,
            "password": password,
            "csrf_token": csrf_token,
        },
    )
    response.raise_for_status()
    return response.json()


async def _lookup_word_translation(prompt: str, target_code: str = "FR") -> str:
    async with AsyncSessionLocal() as session:
        row = (
            await session.execute(
                select(WordTranslation.translation)
                .join(Word, Word.id == WordTranslation.word_id)
                .join(Language, Language.id == WordTranslation.target_language_id)
                .where(Word.text == prompt, Language.code == target_code)
                .order_by(WordTranslation.verified.desc(), WordTranslation.id.asc())
            )
        ).first()
    assert row is not None
    return row[0]


async def _lookup_verb_translation(prompt: str, target_code: str = "ES") -> str:
    async with AsyncSessionLocal() as session:
        row = (
            await session.execute(
                select(VerbTranslation.translation)
                .join(Verb, Verb.id == VerbTranslation.verb_id)
                .join(Language, Language.id == VerbTranslation.target_language_id)
                .where(Verb.infinitive == prompt, Language.code == target_code)
                .order_by(VerbTranslation.verified.desc(), VerbTranslation.id.asc())
            )
        ).first()
    assert row is not None
    return row[0]


def test_health_endpoints_emit_request_ids(client: TestClient, smoke_user: dict[str, str]):
    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.headers["X-Request-ID"]
    assert health.json()["status"] == "ok"

    ready = client.get("/readyz")
    assert ready.status_code == 200
    assert ready.headers["X-Request-ID"]
    assert ready.json()["status"] == "ready"


def test_preferences_community_and_training_rewards(
    client: TestClient,
    smoke_user: dict[str, str],
    circle_user: dict[str, str],
):
    login = _api_login(client, smoke_user["username"], smoke_user["password"])
    csrf_token = login["csrf_token"]

    sound = client.post(
        "/api/preferences/sound",
        json={
            "sound_enabled": True,
            "csrf_token": csrf_token,
        },
    )
    assert sound.status_code == 200
    assert sound.json()["sound_enabled"] is True

    add_friend = client.post(
        "/api/community/friends",
        json={"username": circle_user["username"], "csrf_token": csrf_token},
    )
    assert add_friend.status_code == 200
    assert add_friend.json()["friend"]["username"] == circle_user["username"]
    friend_user_id = add_friend.json()["friend"]["user_id"]

    community = client.get("/api/community")
    assert community.status_code == 200
    assert any(friend["username"] == circle_user["username"] for friend in community.json()["circle"]["friends"])

    words_start = client.post(
        "/api/training/words/start",
        json={"length": 5, "direction": "es_fr", "csrf_token": csrf_token},
    )
    assert words_start.status_code == 200
    prompt = words_start.json()["question"]["prompt"]
    word_answer = asyncio.run(_lookup_word_translation(prompt))

    words_answer = client.post(
        "/api/training/words/answer",
        json={"answer": word_answer, "csrf_token": csrf_token},
    )
    assert words_answer.status_code == 200
    reward = words_answer.json()["result"]["gamification"]
    assert words_answer.json()["result"]["is_correct"] is True
    assert reward["gained_xp"] > 0
    assert reward["combo"] >= 1

    verbs_start = client.post(
        "/api/training/verbs/start",
        json={"length": 5, "direction": "fr_es", "csrf_token": csrf_token},
    )
    assert verbs_start.status_code == 200
    verb_prompt = verbs_start.json()["question"]["prompt"]
    verb_answer = asyncio.run(_lookup_verb_translation(verb_prompt))

    verbs_answer = client.post(
        "/api/training/verbs/answer",
        json={"answer": verb_answer, "csrf_token": csrf_token},
    )
    assert verbs_answer.status_code == 200
    assert verbs_answer.json()["result"]["is_correct"] is True

    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    payload = dashboard.json()
    assert payload["preferences"]["sound_enabled"] is True
    assert payload["preferences"]["show_shortcuts"] is True
    assert payload["gamification"]["recent_xp"]
    assert any(friend["username"] == circle_user["username"] for friend in payload["gamification"]["circle"]["friends"])

    remove_friend = client.request(
        "DELETE",
        f"/api/community/friends/{friend_user_id}",
        json={"csrf_token": csrf_token},
    )
    assert remove_friend.status_code == 200
    assert remove_friend.json()["ok"] is True


def test_admin_content_crud_flow(client: TestClient, smoke_user: dict[str, str]):
    login = _api_login(client, smoke_user["username"], TEST_PASSWORD)
    csrf_token = login["csrf_token"]
    suffix = uuid4().hex[:8]

    word_create = client.post(
        "/api/admin/content/words",
        json={
            "text": f"qa_word_{suffix}",
            "language_code": "ES",
            "translation": f"mot_{suffix}",
            "target_language_code": "FR",
            "synonyms": "mot_alt",
            "verified": False,
            "source": "e2e_admin",
            "csrf_token": csrf_token,
        },
    )
    assert word_create.status_code == 200
    word_id = word_create.json()["row"]["id"]

    word_list = client.get("/api/admin/content/words", params={"search": f"qa_word_{suffix}"})
    assert word_list.status_code == 200
    assert any(row["id"] == word_id for row in word_list.json()["rows"])

    word_update = client.patch(
        f"/api/admin/content/words/{word_id}",
        json={
            "text": f"qa_word_{suffix}",
            "language_code": "ES",
            "translation": f"mot_{suffix}",
            "target_language_code": "FR",
            "synonyms": "mot_alt, mot_alt_2",
            "verified": True,
            "source": "e2e_reviewed",
            "csrf_token": csrf_token,
        },
    )
    assert word_update.status_code == 200
    assert word_update.json()["row"]["verified"] is True

    verb_infinitive = f"qa_verb_{suffix}"
    verb_create = client.post(
        "/api/admin/content/verbs",
        json={
            "infinitive": verb_infinitive,
            "language_code": "FR",
            "translation": f"accion_{suffix}",
            "target_language_code": "ES",
            "synonyms": "accion_alt",
            "verified": False,
            "source": "e2e_admin",
            "csrf_token": csrf_token,
        },
    )
    assert verb_create.status_code == 200
    verb_id = verb_create.json()["row"]["id"]

    conjugation_create = client.post(
        "/api/admin/content/conjugations",
        json={
            "infinitive": verb_infinitive,
            "language_code": "FR",
            "mood": "Indicatif",
            "tense": "Présent",
            "pronoun": "je",
            "conjugated_form": f"{verb_infinitive}e",
            "verified": False,
            "source": "e2e_admin",
            "csrf_token": csrf_token,
        },
    )
    assert conjugation_create.status_code == 200
    conjugation_id = conjugation_create.json()["row"]["id"]

    conjugation_update = client.patch(
        f"/api/admin/content/conjugations/{conjugation_id}",
        json={
            "infinitive": verb_infinitive,
            "language_code": "FR",
            "mood": "Indicatif",
            "tense": "Présent",
            "pronoun": "je",
            "conjugated_form": f"{verb_infinitive}ons",
            "verified": True,
            "source": "e2e_reviewed",
            "csrf_token": csrf_token,
        },
    )
    assert conjugation_update.status_code == 200
    assert conjugation_update.json()["row"]["conjugated_form"] == f"{verb_infinitive}ons"

    summary = client.get("/api/admin/content/summary")
    assert summary.status_code == 200
    assert "summary" in summary.json()
    assert summary.json()["summary"]["curated"]["batches_total"] >= 1

    assert client.request(
        "DELETE",
        f"/api/admin/content/conjugations/{conjugation_id}",
        json={"csrf_token": csrf_token},
    ).status_code == 200
    assert client.request(
        "DELETE",
        f"/api/admin/content/verbs/{verb_id}",
        json={"csrf_token": csrf_token},
    ).status_code == 200
    assert client.request(
        "DELETE",
        f"/api/admin/content/words/{word_id}",
        json={"csrf_token": csrf_token},
    ).status_code == 200


def test_non_admin_users_cannot_access_admin_api_but_legacy_admin_is_open(
    client: TestClient,
    circle_user: dict[str, str],
):
    login = _api_login(client, circle_user["username"], circle_user["password"])
    assert login["user"]["is_admin"] is False

    response = client.get("/api/admin/content/summary")
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"

    legacy_response = client.get("/admin/monitor")
    assert legacy_response.status_code == 200
