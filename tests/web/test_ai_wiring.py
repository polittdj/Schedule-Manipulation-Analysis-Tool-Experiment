"""Per-request AI backend wiring — the settings-selected backend drives the narrative
and briefing prose, behind the citation + figure gates (never a 500, never a fabrication)."""

from __future__ import annotations

from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

import schedule_forensics.web.app as app_module
from schedule_forensics.web.app import SessionState, create_app


class _PolishBackend:
    """A fake local model that prefixes prose (figures preserved) and counts calls."""

    name = "ollama"  # routes exactly like a live Ollama
    is_local = True

    def __init__(self) -> None:
        self.calls = 0

    def is_available(self) -> bool:
        return True

    def list_models(self) -> tuple[str, ...]:
        return ("fake",)

    def pull_model(self, model: str) -> None: ...

    def generate(self, prompt: str) -> str:
        self.calls += 1
        return "POLISHED " + prompt


class _FabricatorBackend(_PolishBackend):
    """A fake model that invents figures — the reattach gate must discard every rephrase."""

    def generate(self, prompt: str) -> str:
        self.calls += 1
        return "FABRICATED: only 12345 minor issues remain."


class _BoomBackend(_PolishBackend):
    """A fake model that dies mid-generation — pages must degrade, never 500."""

    def generate(self, prompt: str) -> str:
        raise RuntimeError("model server went away")


@pytest.fixture
def state() -> SessionState:
    return SessionState()


@pytest.fixture
def client(state: SessionState) -> TestClient:
    return TestClient(create_app(state))


def _wire(monkeypatch: pytest.MonkeyPatch, backend: _PolishBackend) -> None:
    # the session default config already selects "ollama"; substitute the transport
    monkeypatch.setattr(app_module, "_ollama_or_none", lambda config: backend)


def _load_example(client: TestClient, state: SessionState) -> str:
    assert client.post("/example").status_code == 200
    return next(iter(state.schedules))


def test_selected_backend_polishes_the_report_narrative_and_caches(
    monkeypatch: pytest.MonkeyPatch, state: SessionState, client: TestClient
) -> None:
    fake = _PolishBackend()
    _wire(monkeypatch, fake)
    key = _load_example(client, state)
    page = client.get(f"/analysis/{quote(key)}").text
    assert "POLISHED" in page  # the selected backend's rephrase reached the page
    calls = fake.calls
    assert calls > 0
    again = client.get(f"/analysis/{quote(key)}").text
    assert "POLISHED" in again
    assert fake.calls == calls  # polished once per (schedule, backend, model) — then cached


def test_settings_change_switches_the_narrative_backend_immediately(
    monkeypatch: pytest.MonkeyPatch, state: SessionState, client: TestClient
) -> None:
    _wire(monkeypatch, _PolishBackend())
    key = _load_example(client, state)
    assert "POLISHED" in client.get(f"/analysis/{quote(key)}").text
    # switching to the Null backend must bypass the probe TTL and take effect now
    client.post("/settings", data={"classification": "CLASSIFIED", "backend": "null", "model": "x"})
    page = client.get(f"/analysis/{quote(key)}").text
    assert "POLISHED" not in page and "AI narrative" in page


def test_figure_fabricating_generation_never_reaches_the_page(
    monkeypatch: pytest.MonkeyPatch, state: SessionState, client: TestClient
) -> None:
    fake = _FabricatorBackend()
    _wire(monkeypatch, fake)
    key = _load_example(client, state)
    page = client.get(f"/analysis/{quote(key)}").text
    assert fake.calls > 0  # generation ran…
    assert "FABRICATED" not in page and "12345" not in page  # …and was discarded wholesale
    assert "AI narrative" in page  # the deterministic narrative serves instead


def test_generation_failure_degrades_to_the_deterministic_narrative(
    monkeypatch: pytest.MonkeyPatch, state: SessionState, client: TestClient
) -> None:
    _wire(monkeypatch, _BoomBackend())
    key = _load_example(client, state)
    resp = client.get(f"/analysis/{quote(key)}")
    assert resp.status_code == 200  # never a 500 because a model died
    assert "AI narrative" in resp.text


def test_briefing_uses_the_selected_backend_and_degrades_on_failure(
    monkeypatch: pytest.MonkeyPatch, state: SessionState, client: TestClient
) -> None:
    _wire(monkeypatch, _PolishBackend())
    _load_example(client, state)
    assert "POLISHED" in client.get("/briefing").text
    _wire(monkeypatch, _BoomBackend())
    client.post(  # reset the routed-backend cache so the dying backend is picked up
        "/settings", data={"classification": "CLASSIFIED", "backend": "ollama", "model": "x"}
    )
    page = client.get("/briefing")
    assert page.status_code == 200
    assert "Diagnostic Executive Briefing" in page.text and "POLISHED" not in page.text


def test_wipe_clears_polished_narratives(
    monkeypatch: pytest.MonkeyPatch, state: SessionState, client: TestClient
) -> None:
    _wire(monkeypatch, _PolishBackend())
    key = _load_example(client, state)
    client.get(f"/analysis/{quote(key)}")
    assert state.polished
    client.post("/session/wipe")
    assert not state.polished


def test_settings_show_ollama_endpoint_field_and_offline_diagnostic(client: TestClient) -> None:
    """Operator AI fix: the Ollama endpoint is editable, and when no local server is reachable
    the page explains WHY the AI is off (actionable), instead of a silent 'Active backend: null'."""
    page = client.get("/settings").text
    assert "name=endpoint" in page and "127.0.0.1:11434" in page  # editable Ollama endpoint
    # no Ollama in the test container -> a concrete, actionable diagnostic
    assert "Local AI is OFF" in page and "could not reach Ollama" in page


def test_settings_persist_loopback_ollama_endpoint_and_refuse_remote(client: TestClient) -> None:
    client.post(
        "/settings",
        data={"backend": "ollama", "model": "llama3.1:8b", "endpoint": "http://127.0.0.1:11500"},
    )
    assert "127.0.0.1:11500" in client.get("/settings").text  # custom loopback port persisted
    # a remote endpoint is refused (Law 1), falling back to the loopback default
    client.post(
        "/settings",
        data={"backend": "ollama", "model": "x", "endpoint": "http://evil.example.com:11434"},
    )
    page = client.get("/settings").text
    assert "evil.example.com" not in page and "127.0.0.1:11434" in page
