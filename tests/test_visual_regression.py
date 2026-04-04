from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import httpx
import pytest
pytest.importorskip("PIL")
pytest.importorskip("playwright.sync_api")
from PIL import Image, ImageChops

from playwright.sync_api import sync_playwright

pytestmark = pytest.mark.visual

ROOT = Path(__file__).resolve().parents[1]
BASELINES = ROOT / "tests" / "visual_baselines"
ARTIFACTS = ROOT / "tests" / "visual_artifacts"
QA_DB = ROOT / ".qa" / "visual.db"
VISUAL_PORT = 8765
VISUAL_URL = f"http://127.0.0.1:{VISUAL_PORT}"


def qa_env() -> dict[str, str]:
    env = os.environ.copy()
    env["APP_ENV"] = "test"
    env["APP_BASE_URL"] = VISUAL_URL
    env["SECRET_KEY"] = "visual-secret"
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///{QA_DB}"
    env["DATABASE_USE_NULL_POOL"] = "true"
    return env


def wait_for_server(url: str, timeout_seconds: int = 30) -> None:
    started = time.time()
    while time.time() - started < timeout_seconds:
        try:
            response = httpx.get(f"{url}/healthz", timeout=2.0)
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            time.sleep(0.4)
    raise AssertionError("Timed out waiting for the visual regression server")


def diff_ratio(baseline_path: Path, actual_path: Path) -> float:
    with Image.open(baseline_path) as baseline, Image.open(actual_path) as actual:
        if baseline.size != actual.size:
            return 1.0
        diff = ImageChops.difference(baseline.convert("RGB"), actual.convert("RGB")).convert("L")
        histogram = diff.histogram()
        changed = sum(histogram[15:])
        return changed / max(1, diff.size[0] * diff.size[1])


def assert_visual_match(page, name: str) -> None:
    BASELINES.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    actual_path = ARTIFACTS / name
    baseline_path = BASELINES / name
    page.screenshot(path=str(actual_path), full_page=True)

    if os.getenv("UPDATE_VISUAL_BASELINES") == "1":
        shutil.copyfile(actual_path, baseline_path)
        return

    assert baseline_path.exists(), f"Missing baseline {baseline_path.name}. Run with UPDATE_VISUAL_BASELINES=1."
    ratio = diff_ratio(baseline_path, actual_path)
    assert ratio <= 0.01, f"{name} drifted by {ratio:.2%}"


@pytest.fixture(scope="module")
def visual_server():
    if os.getenv("RUN_VISUAL_TESTS") != "1":
        pytest.skip("Visual checks are opt-in. Run with RUN_VISUAL_TESTS=1.")

    if not (ROOT / "frontend" / "static" / "spa").exists():
        pytest.skip("Build the SPA bundle first with `make spa-build`.")

    QA_DB.parent.mkdir(parents=True, exist_ok=True)
    if QA_DB.exists():
        QA_DB.unlink()

    env = qa_env()
    subprocess.run(
        [str(ROOT / ".venv" / "bin" / "python"), "scripts/bootstrap_qa_db.py"],
        cwd=ROOT,
        env=env,
        check=True,
    )
    server = subprocess.Popen(
        [
            str(ROOT / ".venv" / "bin" / "uvicorn"),
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(VISUAL_PORT),
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        wait_for_server(VISUAL_URL)
        yield VISUAL_URL
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()


def login(page, base_url: str) -> None:
    page.goto(f"{base_url}/app/login", wait_until="networkidle")
    page.get_by_label("Username").fill("demo")
    page.get_by_label("Password").fill("demo12345")
    page.get_by_role("button", name="Enter LexArena").click()
    page.wait_for_url(f"{base_url}/app/dashboard")


def test_spa_visual_regression(visual_server):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100}, color_scheme="light")

        page.goto(f"{visual_server}/app/login", wait_until="networkidle")
        assert_visual_match(page, "login.png")

        login(page, visual_server)

        page.goto(f"{visual_server}/app/training/words", wait_until="networkidle")
        assert_visual_match(page, "words.png")

        page.goto(f"{visual_server}/app/training/verbs", wait_until="networkidle")
        assert_visual_match(page, "verb_lab.png")

        page.goto(f"{visual_server}/app/monitor", wait_until="networkidle")
        page.get_by_role("tab", name="Words").click()
        page.wait_for_timeout(350)
        assert_visual_match(page, "monitor_words.png")

        browser.close()
