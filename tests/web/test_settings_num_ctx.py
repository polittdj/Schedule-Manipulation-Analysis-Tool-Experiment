"""The operator can set the Ollama context window, and is told what it costs (OR-11e, ADR-0481).

ADR-0480 shipped a disclosure with a remedy the tool could not perform: raise the window on
the Ollama SERVER. This pins the control that closes it, and the two things that make the
control safe rather than a footgun with a text box in front of it:

1. **The cost is stated where the value is typed.** Raising the window raises the KV-cache
   allocation; `ollama/ollama#14073` records a 52 GB machine going unresponsive when
   v0.15.5's larger tier default spilled to CPU. A field that silently accepts 262,144 with
   no warning is the tool handing an operator that outcome. So the form states the mechanism,
   the multiplier (`OLLAMA_NUM_PARALLEL`), and Ollama's own VRAM tiers as the calibration.
2. **It reaches the DEPLOYED path, not just a bare constructor.** The routed backend is
   wrapped (`_UseMarking`) and the cross-check model is built separately — the trap ADR-0480
   paid for by name. Both are exercised here through the session's real construction path.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import schedule_forensics.ai.factory as factory
from schedule_forensics.ai.backend import AIConfig
from schedule_forensics.ai.ollama import MAX_NUM_CTX, MIN_NUM_CTX, OllamaBackend
from schedule_forensics.web.app import SessionState, create_app
from schedule_forensics.web.settings import _num_ctx_cost_note, _second_backend


@pytest.fixture
def state() -> SessionState:
    return SessionState()


@pytest.fixture
def client(state: SessionState) -> TestClient:
    return TestClient(create_app(state))


def _save(client: TestClient, **over: object) -> None:
    data: dict[str, object] = {
        "classification": "CLASSIFIED",
        "backend": "ollama",
        "model": "m",
        "qa_mode": "annotate",
        "endpoint": "http://127.0.0.1:11434",
        "openai_endpoint": "http://127.0.0.1:1234",
        "second_backend": "none",
        "second_model": "",
        "gen_timeout": 3600.0,
    }
    data.update(over)
    assert client.post("/settings", data=data, follow_redirects=False).status_code == 303


# --- the control exists, and says what it costs -----------------------------------------------


def test_the_settings_page_offers_the_window_field(client: TestClient) -> None:
    body = client.get("/settings").text
    assert "name=num_ctx" in body


def test_the_cost_note_states_the_mechanism_the_multiplier_and_the_incident() -> None:
    """The refusal in ADR-0480 was evidence-based; shipping the lever without carrying that
    evidence to the operator would discard the reason the refusal existed.

    Asserted against the NOTE'S OWN OUTPUT, never the whole page. The first version of this
    check searched the page body and a mutation deleting the note entirely walked straight
    through: `/settings` already carries `OLLAMA_NUM_PARALLEL` (the ADR-0315 env-var report)
    and `262,144` (the input's own `max=`), so every token it looked for was satisfied by
    text the mutation had not touched. A check that cannot fail is not evidence.
    """
    note = _num_ctx_cost_note(AIConfig())
    assert "memory" in note.lower()
    assert "OLLAMA_NUM_PARALLEL" in note  # the multiplier, named
    assert "262,144" in note  # Ollama's own largest-tier default, as the calibration
    assert "14073" in note and "52" in note  # the reported incident, attributed


def test_the_page_actually_carries_that_note(client: TestClient) -> None:
    """The other half: a note that says everything and is never rendered says nothing. Together
    with the test above this is what M14 (delete the call) and M15 (gut the text) each go red on.
    """
    assert _num_ctx_cost_note(AIConfig()) in client.get("/settings").text


def test_the_note_reports_what_is_actually_in_force() -> None:
    """A claim derived from configuration describes intent (QC-2). With no window set the note
    must say the tool sends NOTHING — an operator who reads "in force: 8,192" while the tool
    sends nothing has been told the opposite of the truth."""
    off = _num_ctx_cost_note(AIConfig())
    assert "sends no window" in off and "8,192" not in off
    on = _num_ctx_cost_note(AIConfig(num_ctx=8_192))
    assert "8,192" in on and "sends no window" not in on


def test_the_field_says_that_leaving_it_off_changes_nothing(client: TestClient) -> None:
    """A blank/0 field must READ as "the server decides", or an operator will type a number
    to make the warning go away and take the allocation with it."""
    assert "0 = leave it to the server" in client.get("/settings").text


# --- the posted value survives, bounded --------------------------------------------------------


def test_a_posted_window_is_held_in_the_session_config(
    client: TestClient, state: SessionState
) -> None:
    _save(client, num_ctx=32_768)
    assert state.ai_config.num_ctx == 32_768


def test_a_posted_window_is_clamped_at_the_form_boundary(
    client: TestClient, state: SessionState
) -> None:
    _save(client, num_ctx=10_000_000)
    assert state.ai_config.num_ctx == MAX_NUM_CTX
    _save(client, num_ctx=7)
    assert state.ai_config.num_ctx == MIN_NUM_CTX


def test_omitting_the_field_leaves_the_window_off(client: TestClient, state: SessionState) -> None:
    """Every form POST in the existing suite omits this field; none of them may switch a
    window on as a side effect."""
    _save(client)
    assert state.ai_config.num_ctx == 0


def test_the_saved_window_is_rendered_back_into_the_field(client: TestClient) -> None:
    """A clamp the operator cannot SEE is a silent disagreement between intent and behaviour
    (QC-2). The 303 re-render must show what actually resolved."""
    _save(client, num_ctx=10_000_000)
    assert f'value="{MAX_NUM_CTX}"' in client.get("/settings").text


# --- it reaches the backends the session really uses -------------------------------------------


def test_the_primary_ollama_backend_is_built_with_the_configured_window() -> None:
    built = factory.ollama_or_none(AIConfig(backend="ollama", num_ctx=16_384))
    assert isinstance(built, OllamaBackend) and built.num_ctx == 16_384


def test_the_cross_check_ollama_backend_is_built_with_the_same_window(
    state: SessionState, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The deployed cross-check path, not the bare constructor: `_second_backend` probes,
    caches and (with a use hook set) WRAPS. ADR-0480's C8 was exactly this — a measurement
    that existed on the bare object and was absent in production."""
    state.ai_config = AIConfig(backend="ollama", second_backend="ollama", num_ctx=16_384)
    state.ai_use_hook = lambda model, endpoint: None
    monkeypatch.setattr(OllamaBackend, "is_available", lambda self: True)
    wrapped = _second_backend(state)
    assert wrapped is not None
    inner = getattr(wrapped, "_inner", wrapped)
    assert isinstance(inner, OllamaBackend) and inner.num_ctx == 16_384


def test_the_window_off_builds_a_backend_that_sends_nothing() -> None:
    built = factory.ollama_or_none(AIConfig(backend="ollama"))
    assert isinstance(built, OllamaBackend) and built.num_ctx == 0
