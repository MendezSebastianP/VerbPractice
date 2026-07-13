import asyncio
import re
from datetime import date
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import hash_password
from app.db.base import Base
from app.db.models import Language, User, UserProfile, Verb, VerbConjugation, VerbTranslation, Word, WordTranslation
from app.db.session import AsyncSessionLocal, engine
from app.main import app

TEST_PASSWORD = "smoke-pass-123"
TEST_USERNAME = f"smoke_{uuid4().hex[:10]}"


async def _get_or_create_language(
    db,
    *,
    code: str,
    name: str,
    pronouns: list[str],
    tense_definitions: dict[str, dict[str, str]],
    difficulty_tiers: dict[str, list[str]],
) -> Language:
    result = await db.execute(select(Language).where(Language.code == code))
    language = result.scalar_one_or_none()
    if language is not None:
        return language

    language = Language(
        code=code,
        name=name,
        pronoun_set=pronouns,
        tense_definitions=tense_definitions,
        difficulty_tiers=difficulty_tiers,
    )
    db.add(language)
    await db.flush()
    return language


async def _ensure_smoke_data() -> dict[str, str]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        fr = await _get_or_create_language(
            db,
            code="FR",
            name="French",
            pronouns=["je", "tu", "il", "nous", "vous", "ils"],
            tense_definitions={
                "Présent": {"mood": "Indicatif"},
                "Futur": {"mood": "Indicatif"},
            },
            difficulty_tiers={"easy": ["Présent"], "medium": ["Futur"], "hard": []},
        )
        es = await _get_or_create_language(
            db,
            code="ES",
            name="Spanish",
            pronouns=["yo", "tu", "el", "nosotros", "vosotros", "ellos"],
            tense_definitions={"Presente": {"mood": "Indicativo"}},
            difficulty_tiers={"easy": ["Presente"], "medium": [], "hard": []},
        )

        word_pairs = [
            ("hola", "bonjour"),
            ("tiempo", "temps"),
            ("mundo", "monde"),
            ("casa", "maison"),
            ("libro", "livre"),
            ("amigo", "ami"),
        ]
        for source, target in word_pairs:
            word = (
                await db.execute(select(Word).where(Word.text == source, Word.language_id == es.id))
            ).scalar_one_or_none()
            if word is None:
                word = Word(text=source, language_id=es.id)
                db.add(word)
                await db.flush()

            translation = (
                await db.execute(
                    select(WordTranslation).where(
                        WordTranslation.word_id == word.id,
                        WordTranslation.target_language_id == fr.id,
                        WordTranslation.translation == target,
                    )
                )
            ).scalar_one_or_none()
            if translation is None:
                db.add(
                    WordTranslation(
                        word_id=word.id,
                        target_language_id=fr.id,
                        translation=target,
                        synonyms=[],
                        verified=True,
                        source="smoke_test",
                    )
                )

        verb_pairs = [
            ("aller", "ir"),
            ("avoir", "haber"),
            ("faire", "hacer"),
            ("parler", "hablar"),
            ("venir", "venir"),
            ("voir", "ver"),
        ]
        present_rows = [
            ("je", "vais"),
            ("tu", "vas"),
            ("il", "va"),
            ("nous", "allons"),
            ("vous", "allez"),
            ("ils", "vont"),
        ]
        for index, (source, target) in enumerate(verb_pairs):
            verb = (
                await db.execute(select(Verb).where(Verb.infinitive == source, Verb.language_id == fr.id))
            ).scalar_one_or_none()
            if verb is None:
                verb = Verb(infinitive=source, language_id=fr.id)
                db.add(verb)
                await db.flush()

            translation = (
                await db.execute(
                    select(VerbTranslation).where(
                        VerbTranslation.verb_id == verb.id,
                        VerbTranslation.target_language_id == es.id,
                        VerbTranslation.translation == target,
                    )
                )
            ).scalar_one_or_none()
            if translation is None:
                db.add(
                    VerbTranslation(
                        verb_id=verb.id,
                        target_language_id=es.id,
                        translation=target,
                        synonyms=[],
                        verified=True,
                        source="smoke_test",
                    )
                )

            if index == 0:
                for pronoun, form in present_rows:
                    existing = (
                        await db.execute(
                            select(VerbConjugation).where(
                                VerbConjugation.verb_id == verb.id,
                                VerbConjugation.language_id == fr.id,
                                VerbConjugation.mood == "Indicatif",
                                VerbConjugation.tense == "Présent",
                                VerbConjugation.pronoun == pronoun,
                            )
                        )
                    ).scalar_one_or_none()
                    if existing is None:
                        db.add(
                            VerbConjugation(
                                verb_id=verb.id,
                                language_id=fr.id,
                                mood="Indicatif",
                                tense="Présent",
                                pronoun=pronoun,
                                conjugated_form=form,
                                verified=True,
                                source="smoke_test",
                            )
                        )

        user = (await db.execute(select(User).where(User.username == TEST_USERNAME))).scalar_one_or_none()
        if user is None:
            user = User(username=TEST_USERNAME, password_hash=hash_password(TEST_PASSWORD), is_admin=True)
            db.add(user)
            await db.flush()
            db.add(
                UserProfile(
                    user_id=user.id,
                    xp=0,
                    level=1,
                    streak_days=0,
                    last_active_date=date.today(),
                    theme_preference="light",
                )
            )
        elif not user.is_admin:
            user.is_admin = True

        await db.commit()

    return {"username": TEST_USERNAME, "password": TEST_PASSWORD}


@pytest.fixture(scope="session")
def smoke_user():
    try:
        return asyncio.run(_ensure_smoke_data())
    except Exception as exc:  # pragma: no cover - skip path only used when DB is unavailable
        pytest.skip(f"Smoke routes need a reachable PostgreSQL database: {exc}")


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def _csrf_token(client: TestClient, path: str) -> str:
    response = client.get(path)
    response.raise_for_status()
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    assert match is not None
    return match.group(1)


def _api_bootstrap(client: TestClient) -> dict:
    response = client.get("/api/bootstrap")
    response.raise_for_status()
    return response.json()


def _login(client: TestClient, smoke_user: dict[str, str]) -> None:
    token = _csrf_token(client, "/auth/login")
    response = client.post(
        "/auth/login",
        data={
            "username": smoke_user["username"],
            "password": smoke_user["password"],
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_public_routes_render(client: TestClient):
    assert client.get("/app/login").status_code == 200
    assert client.get("/app/register").status_code == 200
    assert client.get("/training/words", follow_redirects=False).status_code == 303
    assert client.get("/", follow_redirects=False).headers["location"] == "/app/login"


def test_authenticated_pages_render(client: TestClient, smoke_user: dict[str, str]):
    _login(client, smoke_user)

    redirect = client.get("/", follow_redirects=False)
    assert redirect.status_code == 303
    assert redirect.headers["location"] == "/app/dashboard"

    for path in ["/app/dashboard", "/app/training/words", "/app/training/verbs", "/app/training/conjugation", "/app/chat", "/app/monitor"]:
        response = client.get(path)
        assert response.status_code == 200


def test_admin_live_feed_renders_json(client: TestClient, smoke_user: dict[str, str]):
    _login(client, smoke_user)

    response = client.get("/admin/api/live")
    assert response.status_code == 200
    payload = response.json()
    assert "totals" in payload
    assert "users" in payload
    assert payload["viewer"] == smoke_user["username"]


def test_spa_bootstrap_and_api_routes(client: TestClient, smoke_user: dict[str, str]):
    bootstrap = _api_bootstrap(client)
    assert bootstrap["authenticated"] is False
    assert bootstrap["csrf_token"]

    login_response = client.post(
        "/api/auth/login",
        json={
            "username": smoke_user["username"],
            "password": smoke_user["password"],
            "csrf_token": bootstrap["csrf_token"],
        },
    )
    assert login_response.status_code == 200
    login_payload = login_response.json()
    assert login_payload["authenticated"] is True
    csrf_token = login_payload["csrf_token"]

    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["user"]["username"] == smoke_user["username"]

    words_setup = client.get("/api/training/words")
    assert words_setup.status_code == 200
    assert words_setup.json()["setup"] is True

    words_start = client.post(
        "/api/training/words/start",
        json={"length": 5, "direction": "es_fr", "csrf_token": csrf_token},
    )
    assert words_start.status_code == 200
    assert words_start.json()["setup"] is False

    chat_state = client.get("/api/chat")
    assert chat_state.status_code == 200
    assert "suggestions" in chat_state.json()


def test_training_finish_endpoints(client: TestClient, smoke_user: dict[str, str]):
    bootstrap = _api_bootstrap(client)
    login_response = client.post(
        "/api/auth/login",
        json={
            "username": smoke_user["username"],
            "password": smoke_user["password"],
            "csrf_token": bootstrap["csrf_token"],
        },
    )
    assert login_response.status_code == 200
    csrf_token = login_response.json()["csrf_token"]

    words_start = client.post(
        "/api/training/words/start",
        json={"length": 5, "direction": "es_fr", "csrf_token": csrf_token},
    )
    assert words_start.status_code == 200
    words_finish = client.post("/api/training/words/finish", json={"csrf_token": csrf_token})
    assert words_finish.status_code == 200
    assert words_finish.json()["setup"] is True
    assert words_finish.json()["feedback"] == "Session ended."

    verbs_start = client.post(
        "/api/training/verbs/start",
        json={"length": 5, "direction": "fr_es", "csrf_token": csrf_token},
    )
    assert verbs_start.status_code == 200
    verbs_finish = client.post("/api/training/verbs/finish", json={"csrf_token": csrf_token})
    assert verbs_finish.status_code == 200
    assert verbs_finish.json()["setup"] is True
    assert verbs_finish.json()["feedback"] == "Session ended."

    conjugation_start = client.post(
        "/api/training/conjugation/start",
        json={
            "language": "FR",
            "level": "easy",
            "fill_level": "hard",
            "selected_tenses": ["Présent"],
            "length": 3,
            "csrf_token": csrf_token,
        },
    )
    assert conjugation_start.status_code == 200
    start_question = conjugation_start.json()["question"]
    editable_cells = [
        cell
        for row in start_question["rows"]
        for cell in row["cells"]
        if cell["tense"] == "Présent" and cell["kind"] == "input"
    ]
    assert editable_cells
    assert all(cell["accepted_answers"] for cell in editable_cells)
    expected_answers = sum(
        cell["kind"] == "input"
        for row in start_question["rows"]
        for cell in row["cells"]
        if cell["tense"] == "Présent"
    )
    conjugation_review = client.post(
        "/api/training/conjugation/check-tense",
        json={
            "tense": "Présent",
            "answers": {
                "je": "vais",
                "tu": "wrong",
                "il": "va",
                "nous": "allons",
                "vous": "allez",
                "ils": "vont",
            },
            "csrf_token": csrf_token,
        },
    )
    assert conjugation_review.status_code == 200
    review_payload = conjugation_review.json()
    assert review_payload["tense"] == "Présent"
    assert review_payload["total"] == expected_answers
    assert len(review_payload["cells"]) == len(start_question["pronouns"])
    assert sum(cell["kind"] == "answer" for cell in review_payload["cells"]) == expected_answers
    assert all(cell["expected"] for cell in review_payload["cells"])
    conjugation_finish = client.post("/api/training/conjugation/finish", json={"csrf_token": csrf_token})
    assert conjugation_finish.status_code == 200
    assert conjugation_finish.json()["setup"] is True
    assert conjugation_finish.json()["feedback"] == "Session ended."

    conjugation_state = client.get("/api/training/conjugation")
    assert conjugation_state.status_code == 200
    languages = conjugation_state.json()["languages"]
    assert {language["code"] for language in languages} == {"EN", "ES", "FR", "RU"}
    assert all("available_tenses" in language and "verb_count" in language for language in languages)

    empty_custom = client.post(
        "/api/training/conjugation/start",
        json={
            "language": "FR",
            "level": "custom",
            "fill_level": "hard",
            "selected_tenses": [],
            "length": 3,
            "csrf_token": csrf_token,
        },
    )
    assert empty_custom.status_code == 422
    assert "Choose at least one tense" in empty_custom.json()["detail"]

    conjugation_preference = client.patch(
        "/api/settings",
        json={
            "last_practice_mode": "conjugation",
            "show_shortcuts": False,
            "csrf_token": csrf_token,
        },
    )
    assert conjugation_preference.status_code == 200
    assert conjugation_preference.json()["last_practice_mode"] == "conjugation"
    assert conjugation_preference.json()["show_shortcuts"] is False

    shortcuts_on = client.patch(
        "/api/settings",
        json={"show_shortcuts": True, "csrf_token": csrf_token},
    )
    assert shortcuts_on.status_code == 200
    assert shortcuts_on.json()["show_shortcuts"] is True


def test_training_and_chat_flows(client: TestClient, smoke_user: dict[str, str]):
    _login(client, smoke_user)

    words_response = client.post(
        "/training/words",
        data={
            "csrf_token": _csrf_token(client, "/training/words"),
            "action": "start",
            "length": "5",
            "direction": "es_fr",
        },
    )
    assert words_response.status_code == 200
    assert "Session progress" in words_response.text

    verbs_response = client.post(
        "/training/verbs",
        data={
            "csrf_token": _csrf_token(client, "/training/verbs"),
            "action": "start",
            "length": "5",
            "direction": "fr_es",
        },
    )
    assert verbs_response.status_code == 200
    assert "Session progress" in verbs_response.text

    conjugation_response = client.post(
        "/training/conjugation",
        data={
            "csrf_token": _csrf_token(client, "/training/conjugation"),
            "action": "start",
            "language": "FR",
            "level": "easy",
            "fill_level": "hard",
            "selected_tenses": ["Présent"],
        },
    )
    assert conjugation_response.status_code == 200
    assert "Current verb" in conjugation_response.text

    conjugation_submit = client.post(
        "/training/conjugation",
        data={
            "csrf_token": _csrf_token(client, "/training/conjugation"),
            "action": "submit",
            "ans__Présent__je": "vais",
            "ans__Présent__tu": "vas",
            "ans__Présent__il": "va",
            "ans__Présent__nous": "allons",
            "ans__Présent__vous": "allez",
            "ans__Présent__ils": "vont",
        },
    )
    assert conjugation_submit.status_code == 200
    assert "Score:" in conjugation_submit.text

    chat_response = client.post(
        "/chat/stream",
        data={
            "csrf_token": _csrf_token(client, "/chat"),
            "message": "Give me one short drill.",
        },
    )
    assert chat_response.status_code == 200
    assert "data:" in chat_response.text
