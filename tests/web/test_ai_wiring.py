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
        text = prompt.split("STATEMENT: ", 1)[1].rsplit("\nREWRITE:", 1)[0]
        return "POLISHED " + text


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
    # the report page renders the deterministic narrative and defers polish (it must never block the
    # render on a slow local model — the .mpp "won't load" / spinning-tab regression)
    page = client.get(f"/analysis/{quote(key)}").text
    assert "POLISHED" not in page and "data-ai-endpoint" in page
    assert fake.calls == 0  # the model is NOT run during the page render
    # the async endpoint does the polish and caches it per (schedule, backend, model)
    html = client.get(f"/api/ai/narrative?key={quote(key)}").json()["html"]
    assert "POLISHED" in html
    calls = fake.calls
    assert calls > 0
    again = client.get(f"/api/ai/narrative?key={quote(key)}").json()["html"]
    assert "POLISHED" in again
    assert fake.calls == calls  # polished once per (schedule, backend, model) — then cached


def test_settings_change_switches_the_narrative_backend_immediately(
    monkeypatch: pytest.MonkeyPatch, state: SessionState, client: TestClient
) -> None:
    _wire(monkeypatch, _PolishBackend())
    key = _load_example(client, state)
    assert "POLISHED" in client.get(f"/api/ai/narrative?key={quote(key)}").json()["html"]
    # switching to the Null backend must bypass the probe TTL and take effect now
    client.post("/settings", data={"classification": "CLASSIFIED", "backend": "null", "model": "x"})
    assert client.get(f"/api/ai/narrative?key={quote(key)}").json()["polished"] is False
    page = client.get(f"/analysis/{quote(key)}").text
    assert "POLISHED" not in page and "AI narrative" in page


def test_figure_fabricating_generation_never_reaches_the_page(
    monkeypatch: pytest.MonkeyPatch, state: SessionState, client: TestClient
) -> None:
    fake = _FabricatorBackend()
    _wire(monkeypatch, fake)
    key = _load_example(client, state)
    # the fabricating model runs at the async endpoint; the reattach figure-gate strips every
    # invented number, so no fabricated figure can ever reach the client
    html = client.get(f"/api/ai/narrative?key={quote(key)}").json()["html"]
    assert fake.calls > 0  # generation ran…
    assert "FABRICATED" not in html and "12345" not in html  # …invented figure discarded
    page = client.get(f"/analysis/{quote(key)}").text
    assert "FABRICATED" not in page and "12345" not in page
    assert "AI narrative" in page  # the deterministic narrative serves instead


def test_generation_failure_degrades_to_the_deterministic_narrative(
    monkeypatch: pytest.MonkeyPatch, state: SessionState, client: TestClient
) -> None:
    _wire(monkeypatch, _BoomBackend())
    key = _load_example(client, state)
    resp = client.get(f"/analysis/{quote(key)}")
    assert resp.status_code == 200  # never a 500 because a model died
    assert "AI narrative" in resp.text


def test_briefing_polish_is_async_off_the_page_load_and_degrades_on_failure(
    monkeypatch: pytest.MonkeyPatch, state: SessionState, client: TestClient
) -> None:
    """The briefing page renders the deterministic briefing immediately (never blocks on the
    model); the local-AI polish is fetched off the page-load path via /api/ai/briefing, which
    degrades to {polished:false} on a dying model instead of 500-ing or hanging the page."""
    _wire(monkeypatch, _PolishBackend())
    _load_example(client, state)
    page = client.get("/briefing").text
    assert "1. The Bottom Line" in page  # deterministic briefing present on load…
    assert "data-ai-endpoint" in page and "POLISHED" not in page  # …polish is deferred, not inline
    assert "POLISHED" in client.get("/api/ai/briefing").json()["html"]  # the endpoint does it
    # a dying model degrades the endpoint to {polished:false} (never a 500), page stays usable
    _wire(monkeypatch, _BoomBackend())
    client.post(  # reset the routed-backend cache so the dying backend is picked up
        "/settings", data={"classification": "CLASSIFIED", "backend": "ollama", "model": "x"}
    )
    resp = client.get("/api/ai/briefing")
    assert resp.status_code == 200 and resp.json() == {"polished": False}


class _FakeOllamaManager:
    """Records ensure_running()/shutdown() so the lazy start AND stop wiring can be asserted
    off-thread (both run on a background thread so the redirect never waits on Ollama)."""

    def __init__(self) -> None:
        import threading

        self.started = threading.Event()
        self.stopped = threading.Event()

    def ensure_running(self) -> str:
        self.started.set()
        return "started"

    def shutdown(self) -> None:
        self.stopped.set()


def test_enabling_ollama_in_settings_starts_it_lazily() -> None:
    """The tool starts Ollama only when the operator turns the Ollama backend on in AI Settings
    (ADR-0122) — not at launch. A non-Ollama backend must not start it."""
    mgr = _FakeOllamaManager()
    client = TestClient(create_app(SessionState(), ollama=mgr))
    # selecting a non-Ollama backend never spins Ollama up
    client.post("/settings", data={"classification": "CLASSIFIED", "backend": "null", "model": "x"})
    assert not mgr.started.wait(0.3)
    # turning the Ollama backend on starts it (off-thread, so wait briefly)
    client.post(
        "/settings", data={"classification": "CLASSIFIED", "backend": "ollama", "model": "x"}
    )
    assert mgr.started.wait(2.0)  # ensure_running() ran on the background thread


def test_settings_lazy_start_is_a_no_op_without_a_manager(client: TestClient) -> None:
    """In a plain (non-desktop) app there is no Ollama manager; enabling Ollama must not error."""
    resp = client.post(
        "/settings", data={"classification": "CLASSIFIED", "backend": "ollama", "model": "x"}
    )
    assert resp.status_code in (200, 303)  # redirect, no crash when app.state.ollama is None


def test_switching_the_backend_off_ollama_stops_the_local_model() -> None:
    """Turning the AI off Ollama (to Null/OpenAI/Cloud) stops the local model the tool started so it
    is never left consuming RAM/CPU once it is no longer the chosen backend (operator report)."""
    mgr = _FakeOllamaManager()
    client = TestClient(create_app(SessionState(), ollama=mgr))
    client.post(
        "/settings", data={"classification": "CLASSIFIED", "backend": "ollama", "model": "x"}
    )
    assert mgr.started.wait(2.0)
    client.post("/settings", data={"classification": "CLASSIFIED", "backend": "null", "model": "x"})
    assert mgr.stopped.wait(2.0)  # switching the AI off Ollama stopped the local server


def test_ai_off_button_routes_to_null_and_stops_the_model() -> None:
    """The explicit 'Turn AI off' control routes back to the deterministic Null backend AND stops
    the local model (operator order: an off switch once the AI is on, without quitting the tool)."""
    from schedule_forensics.ai.backend import AIConfig

    mgr = _FakeOllamaManager()
    st = SessionState()
    st.ai_config = AIConfig(backend="ollama")
    client = TestClient(create_app(st, ollama=mgr))
    resp = client.post("/settings/ai-off")
    assert resp.status_code in (200, 303)
    assert st.ai_config.backend == "null"  # routed back to the offline deterministic backend
    assert mgr.stopped.wait(2.0)  # and the local model was stopped


def test_wipe_turns_ai_off_and_stops_the_model() -> None:
    """A session wipe is a full reset: it turns the AI back off and stops any local model, so a
    wiped session never leaves Ollama running (operator report: Ollama survived a Wipe -> Quit)."""
    from schedule_forensics.ai.backend import AIConfig

    mgr = _FakeOllamaManager()
    st = SessionState()
    st.ai_config = AIConfig(backend="ollama")
    client = TestClient(create_app(st, ollama=mgr))
    client.post("/session/wipe")
    assert st.ai_config.backend == "null"
    assert mgr.stopped.wait(2.0)


def test_settings_shows_the_ai_off_button_only_when_a_model_is_active(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    """The one-click 'Turn AI off' control is shown only while a real local model is active (there
    is nothing to turn off otherwise)."""

    class _Reachable:
        name = "ollama"
        is_local = True

        def is_available(self) -> bool:
            return True

        def unavailable_reason(self) -> None:
            return None

        def list_models(self) -> tuple[str, ...]:
            return ("m",)

        def pull_model(self, model: str) -> None: ...

        def generate(self, prompt: str) -> str:
            return ""

    monkeypatch.setattr(app_module, "_ollama_or_none", lambda cfg: _Reachable())
    page = client.get("/settings").text
    assert "/settings/ai-off" in page and "Turn the AI off" in page
    monkeypatch.setattr(app_module, "_ollama_or_none", lambda cfg: None)  # no model reachable
    assert "/settings/ai-off" not in client.get("/settings").text


def test_wipe_clears_polished_narratives(
    monkeypatch: pytest.MonkeyPatch, state: SessionState, client: TestClient
) -> None:
    _wire(monkeypatch, _PolishBackend())
    key = _load_example(client, state)
    client.get(f"/api/ai/narrative?key={quote(key)}")  # the async polish caches into state.polished
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


def test_settings_model_field_is_a_dropdown_of_installed_models(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    """When Ollama is reachable, the Model field becomes a dropdown of installed models so the
    operator picks one (e.g. a purpose-built model) instead of matching a free-text string; the
    configured-but-missing model is kept as a selected option, marked not installed."""

    class _Reachable:
        name = "ollama"
        is_local = True

        def is_available(self) -> bool:
            return True

        def unavailable_reason(self) -> None:
            return None

        def list_models(self) -> tuple[str, ...]:
            return ("llama3.2:latest", "schedule-analyst:latest", "qwen2.5:7b-instruct")

        def pull_model(self, model: str) -> None: ...

        def generate(self, prompt: str) -> str:
            return ""

    monkeypatch.setattr(app_module, "_ollama_or_none", lambda cfg: _Reachable())
    page = client.get("/settings").text
    assert "<select name=model id=primaryModel>" in page
    assert "schedule-analyst:latest" in page and "qwen2.5:7b-instruct" in page
    # the default configured model isn't installed -> kept as an option, flagged, with a fix hint
    assert "llama3.1:8b" in page and "not installed" in page
    assert "pick an installed model from the Model dropdown" in page


def test_generation_timeout_is_configurable_and_wires_into_the_backend() -> None:
    """A big, slow local model (e.g. llama3.1:70b) must be allowed to finish — the configured
    generation timeout flows through to the backend's generate budget."""
    from schedule_forensics.ai.backend import AIConfig

    backend = app_module._ollama_or_none(AIConfig(backend="ollama", gen_timeout=900.0))
    assert backend is not None and backend._timeout == 900.0


def test_settings_persist_and_clamp_the_generation_timeout(client: TestClient) -> None:
    client.post("/settings", data={"backend": "ollama", "model": "x", "gen_timeout": "1200"})
    page = client.get("/settings").text
    assert "name=gen_timeout" in page and 'value="1200"' in page
    # absurd values clamp into the 30s..3600s window (a wedged model can't hang forever)
    client.post("/settings", data={"backend": "ollama", "model": "x", "gen_timeout": "999999"})
    assert 'value="3600"' in client.get("/settings").text
    client.post("/settings", data={"backend": "ollama", "model": "x", "gen_timeout": "1"})
    assert 'value="30"' in client.get("/settings").text


def test_generation_timeout_defaults_to_the_form_maximum() -> None:
    """Operator order 2026-07-08 ("make the default the max"): the out-of-the-box generation
    timeout is the form maximum 3600s (1 h) so a big, slow local model finishes a full answer by
    default. Both the config default and the /settings form share it."""
    from schedule_forensics.ai.backend import AIConfig

    assert AIConfig().gen_timeout == 3600.0


def test_fresh_settings_page_shows_the_max_default(client: TestClient) -> None:
    assert "name=gen_timeout" in client.get("/settings").text
    assert 'value="3600"' in client.get("/settings").text


def test_settings_page_wires_cross_check_model_autopopulate(client: TestClient) -> None:
    """Selecting a cross-check second backend should auto-fill the model id (operator order).
    The page must carry the field hooks and the local script that does it."""
    page = client.get("/settings").text
    assert "id=primaryModel" in page
    assert "id=secondBackend" in page and "id=secondModel" in page
    assert "/static/settings.js" in page


def test_settings_page_carries_the_local_model_setup_guide(client: TestClient) -> None:
    page = client.get("/settings").text
    assert "ollama pull llama3.1:8b" in page
    assert "How to download" in page


def test_ai_models_endpoint_refuses_a_remote_endpoint(client: TestClient) -> None:
    """The live model probe is loopback-only and fail-closed (Law 1): a remote endpoint is refused
    and never reached, returning reachable=false rather than dialing out."""
    j = client.get("/api/ai/models", params={"kind": "openai", "endpoint": "http://10.1.2.3:1234"})
    assert j.status_code == 200
    body = j.json()
    assert body["reachable"] is False and body["models"] == []
    assert "loopback" in body["reason"].lower()


def test_ai_models_endpoint_is_graceful_when_unreachable(client: TestClient) -> None:
    """A loopback endpoint with no server answering returns reachable=false (never a 500)."""
    j = client.get("/api/ai/models", params={"kind": "ollama"})
    assert j.status_code == 200
    body = j.json()
    assert body["reachable"] is False and body["models"] == []


def test_ai_models_endpoint_lists_served_models(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the local server answers, the probe returns the model ids it serves — these feed the
    live Model dropdowns in settings."""

    class _Server:
        def __init__(self, *a: object, **k: object) -> None: ...
        def unavailable_reason(self) -> None:
            return None

        def list_models(self) -> tuple[str, ...]:
            return ("phi3:mini", "qwen2.5:7b")

    monkeypatch.setattr(app_module, "OllamaBackend", _Server)
    body = client.get("/api/ai/models", params={"kind": "ollama"}).json()
    assert body["reachable"] is True
    assert body["models"] == ["phi3:mini", "qwen2.5:7b"]


def test_cross_check_second_model_is_a_dropdown(client: TestClient) -> None:
    """Operator: pick the cross-check second model from a dropdown (not a free-text box)."""
    page = client.get("/settings").text
    assert "<select name=second_model id=secondModel>" in page
    # the live model probe + refresh affordance are wired
    assert "id=refreshModels" in page
    assert "/api/ai/models" in client.get("/static/settings.js").text


def test_settings_explains_each_backend_and_its_cui_posture(client: TestClient) -> None:
    """Operator: explain in detail what each model/backend does and how it handles CUI (local vs
    leaving the machine)."""
    page = client.get("/settings").text
    assert "how it handles your data (CUI)" in page
    # each option is covered, with its data-locality verdict
    assert "Ollama (local)</b>" in page and "Stays on the machine" in page
    assert "OpenAI-compatible (local)</b>" in page
    assert "Null (offline, deterministic)</b>" in page
    assert "Cloud</b>" in page and "Data LEAVES this machine" in page
    assert "Cross-check second model</b>" in page
