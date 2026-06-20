"""Risks & Executive-Briefing pages render instantly; local-AI polish loads asynchronously.

Regression for the "Risks & Opportunities / Executive Briefing won't open" bug: those two pages
used to run the (possibly very slow) local model synchronously during the page render — one
generation per narrative statement / briefing section — so a big workbook on a large local model
made the page hang. They now render the deterministic content immediately and fetch the AI polish
off the page-load path via /api/ai/narrative and /api/ai/briefing (which can never hang or 500 the
page)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import schedule_forensics.web.app as appmod
from schedule_forensics.web.app import SessionState, create_app

GOLD = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"


class _CountingBackend:
    """A stand-in 'real' local backend that records every generate() call."""

    name = "ollama"
    is_local = True
    model = "stub"

    def __init__(self) -> None:
        self.calls = 0

    def is_available(self) -> bool:
        return True

    def list_models(self) -> tuple[str, ...]:
        return ("stub",)

    def pull_model(self, model: str) -> None: ...

    def generate(self, prompt: str) -> str:
        self.calls += 1
        return prompt + " (AI polished)."


@pytest.fixture
def loaded() -> tuple[TestClient, SessionState]:
    st = SessionState()
    c = TestClient(create_app(st))
    for name in ("Project2", "Project5"):
        data = (GOLD / f"{name}.mspdi.xml").read_bytes()
        c.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")})
    return c, st


def test_risks_and_briefing_never_call_the_model_on_page_load(
    loaded: tuple[TestClient, SessionState], monkeypatch: pytest.MonkeyPatch
) -> None:
    c, _ = loaded
    backend = _CountingBackend()
    monkeypatch.setattr(appmod, "_active_backend", lambda state: backend)
    for route in ("/risks", "/briefing"):
        page = c.get(route).text
        assert "data-ai-endpoint" in page  # the async polish hook is present
        assert "/static/ai_polish.js" in page
    assert backend.calls == 0  # the (slow) model is NEVER invoked during the page render


def test_ai_endpoints_degrade_without_a_model(loaded: tuple[TestClient, SessionState]) -> None:
    c, st = loaded  # default Null backend → nothing to polish
    assert c.get("/api/ai/briefing").json() == {"polished": False}
    key = next(iter(st.schedules))
    assert c.get(f"/api/ai/narrative?key={key}").json()["polished"] is False


def test_ai_briefing_endpoint_polishes_with_a_model(
    loaded: tuple[TestClient, SessionState], monkeypatch: pytest.MonkeyPatch
) -> None:
    c, _ = loaded
    backend = _CountingBackend()
    monkeypatch.setattr(appmod, "_active_backend", lambda state: backend)
    body = c.get("/api/ai/briefing").json()
    assert body["polished"] is True and "AI polished)." in body["html"]
    assert backend.calls > 0  # the endpoint (off the page-load path) does the AI work


def test_ai_narrative_unknown_key_is_safe(loaded: tuple[TestClient, SessionState]) -> None:
    c, _ = loaded
    assert c.get("/api/ai/narrative?key=does-not-exist").json() == {"polished": False}


def test_ai_polish_js_is_local(loaded: tuple[TestClient, SessionState]) -> None:
    c, _ = loaded
    js = c.get("/static/ai_polish.js")
    assert js.status_code == 200 and "data-ai-endpoint" in js.text
    externals = [
        u
        for u in re.findall(r"https?://[^\s\"'<>]+", js.text)
        if "127.0.0.1" not in u and "localhost" not in u and "www.w3.org" not in u
    ]
    assert not externals, externals
