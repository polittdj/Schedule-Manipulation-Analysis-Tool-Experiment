"""The answer-length control on AI Settings, and the two disclosures on the Ask panel (ADR-0486).

The settings half mirrors ADR-0481's window control: the field exists, is bounded at the form
boundary, defaults to the MAXIMUM (operator directive 2026-09-11: "raise the limit to the max")
and reaches the deployed construction path — including through the ``_UseMarking`` wrapper,
the trap ADR-0480 paid for by name. The panel half pins the two sentences an operator actually
saw this defect through: an answer that stops mid-sentence now carries a CUT warning naming
the setting, and an empty answer from a thinking model says the budget was spent reasoning
instead of "select a different model". The gateway's 403 WITH a valid key gets its own words.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.ai.backend import AIConfig
from schedule_forensics.ai.completion import MAX_ANSWER_TOKENS, MIN_ANSWER_TOKENS
from schedule_forensics.ai.openai_compat import OpenAICompatBackend
from schedule_forensics.ai.qa import EMPTY_ANSWER, NoAnswer
from schedule_forensics.importers import parse_mspdi
from schedule_forensics.web import app as app_module
from schedule_forensics.web.app import (
    SessionState,
    _generation_failed_note,
    _no_answer_note,
    create_app,
)
from schedule_forensics.web.settings import _UseMarking

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests" / "fixtures" / "golden" / "project2_5" / "Project5.mspdi.xml"
GATEWAY = "https://proxy.fast.luna.nasa.gov"
FIELD = "Answer length limit"


@pytest.fixture
def state() -> SessionState:
    return SessionState()


@pytest.fixture
def client(state: SessionState) -> TestClient:
    return TestClient(create_app(state))


def _save(client: TestClient, **over: object) -> None:
    data: dict[str, object] = {
        "classification": "CLASSIFIED",
        "backend": "openai",
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


# --- the control -------------------------------------------------------------------------------


def test_the_settings_page_offers_the_field_bounded_and_defaulted_to_the_maximum(
    client: TestClient,
) -> None:
    page = client.get("/settings").text
    tags = [chunk.split(">", 1)[0] for chunk in page.split("<input")[1:]]
    field = [t for t in tags if "name=answer_max_tokens" in t]
    assert len(field) == 1
    assert (
        f"max={MAX_ANSWER_TOKENS}" in field[0]
        and 'value="' + str(MAX_ANSWER_TOKENS) + '"' in field[0]
    )
    assert "min=0" in field[0]
    assert FIELD in page and f"{MIN_ANSWER_TOKENS:,}" in page
    assert "default = max" in page.split("name=answer_max_tokens", 1)[1][:900]


def test_a_posted_limit_is_held_clamped_and_rendered_back(
    client: TestClient, state: SessionState
) -> None:
    _save(client, answer_max_tokens=8192)
    assert state.ai_config.answer_max_tokens == 8192
    assert 'value="8192"' in client.get("/settings").text
    _save(client, answer_max_tokens=5)
    assert state.ai_config.answer_max_tokens == MIN_ANSWER_TOKENS
    _save(client, answer_max_tokens=99_999_999)
    assert state.ai_config.answer_max_tokens == MAX_ANSWER_TOKENS
    _save(client, answer_max_tokens=0)
    assert state.ai_config.answer_max_tokens == 0


def test_omitting_the_field_leaves_the_maximum_in_force(
    client: TestClient, state: SessionState
) -> None:
    _save(client)
    assert state.ai_config.answer_max_tokens == MAX_ANSWER_TOKENS


def test_the_use_marking_wrapper_forwards_the_completion_evidence() -> None:
    """ADR-0480's trap, pre-empted: today the deployed app wraps only a routed Ollama
    (ADR-0315), so no OpenAI-compatible backend passes through here — but the day that
    wrapping is extended, a wrapper that swallows ``last_completion`` would hide the cut
    warning exactly where it matters. Pinned on the wrapper itself."""

    def opener(url: str, data: bytes | None, timeout: float, headers: dict[str, str]) -> str:
        return json.dumps({"choices": [{"finish_reason": "length", "message": {"content": "cut"}}]})

    inner = OpenAICompatBackend(model="m", opener=opener)
    wrapped = _UseMarking(inner, lambda model, endpoint: None, "m", "http://127.0.0.1:1234")
    assert wrapped.generate("Q") == "cut"
    assert wrapped.last_completion is inner.last_completion
    assert wrapped.last_completion is not None and wrapped.last_completion.finish_reason == "length"


# --- the panel ---------------------------------------------------------------------------------


def _session(qa_mode: str = "annotate", **cfg: Any) -> SessionState:
    st = SessionState()
    st.schedules["v1"] = parse_mspdi(GOLDEN)
    st.ai_config = AIConfig(backend="openai", model="m", qa_mode=qa_mode, **cfg)
    return st


def _ask(monkeypatch: pytest.MonkeyPatch, body: dict[str, Any], **cfg: Any) -> dict[str, Any]:
    def opener(url: str, data: bytes | None, timeout: float, headers: dict[str, str]) -> str:
        if url.endswith("/v1/models"):
            return json.dumps({"data": [{"id": "m"}]})
        return json.dumps(body)

    monkeypatch.setattr(
        app_module,
        "_openai_or_none",
        lambda c: OpenAICompatBackend(model=c.model, max_tokens=c.answer_max_tokens, opener=opener),
    )
    st = _session(**cfg)
    # The hook is set as in the deployed app, but ADR-0315 wraps ONLY a routed Ollama: an
    # OpenAI-compatible backend reaches the panel bare (measured — the battery's M25 turned
    # the wrapper's property off and this path stayed green). The property is pinned by its
    # own unit test above, for the day the wrapping is extended.
    st.ai_use_hook = lambda model, endpoint: None
    resp = TestClient(create_app(st)).post(
        "/api/ask", data={"question": "Is the schedule slipping?"}
    )
    assert resp.status_code == 200
    return dict(resp.json())


def test_a_cut_answer_is_disclosed_beside_it(monkeypatch: pytest.MonkeyPatch) -> None:
    body = {
        "choices": [{"finish_reason": "length", "message": {"content": "The programme is behind"}}],
        "usage": {"completion_tokens": 4096},
    }
    payload = _ask(monkeypatch, body, answer_max_tokens=4096)
    assert payload["answer"] and "behind" in payload["answer"]
    warning = payload["evidence_warning"]
    assert warning is not None and "CUT" in warning and FIELD in warning and "4,096" in warning


def test_a_complete_answer_carries_no_cut_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    body = {
        "choices": [{"finish_reason": "stop", "message": {"content": "The programme is behind"}}]
    }
    assert _ask(monkeypatch, body)["evidence_warning"] is None


def test_an_empty_answer_from_a_thinking_model_says_the_budget_was_spent_thinking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The operator's third ask: reasoning present, no answer text, a length stop."""
    body = {
        "choices": [
            {"finish_reason": "length", "message": {"content": "", "reasoning_content": "z" * 6000}}
        ]
    }
    payload = _ask(monkeypatch, body)
    assert payload["answer"] is None
    why = payload["no_answer"]
    assert why["code"] == "empty_answer"
    assert "6,000" in why["text"] and "reasoning" in why["text"] and FIELD in why["text"]
    assert "Annotate" in why["text"]  # the smaller-prompt remedy
    assert "select a different model" not in why["text"]


def test_a_null_content_is_an_empty_answer_not_the_word_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = {"choices": [{"finish_reason": "stop", "message": {"content": None}}]}
    payload = _ask(monkeypatch, body)
    assert payload["answer"] is None and payload["no_answer"]["code"] == "empty_answer"


def test_the_plain_empty_sentence_survives_when_nothing_is_known() -> None:
    text = _no_answer_note(AIConfig(backend="openai"), NoAnswer(EMPTY_ANSWER))
    assert "returned no text" in text and FIELD not in text


# --- the gateway's 403 with a valid key -------------------------------------------------------


def test_a_gateway_403_with_a_saved_key_names_entitlement_and_prompt_size() -> None:
    """The operator's ACTUAL morning: the catalog served (the key is valid), the generation
    403'd. 'Paste your key' is the wrong advice for a key that already works."""
    cfg = AIConfig(
        backend="gateway",
        gateway_endpoint=GATEWAY,
        gateway_approved=True,
        gateway_api_key="sk-valid",
        model="claude-opus-4.8-thinking-itar",
    )
    note = _generation_failed_note(cfg, "server returned HTTP 403")
    assert GATEWAY in note and "HTTP 403" in note
    assert "accepted your key" in note and "claude-opus-4.8-thinking-itar" in note
    assert "Unrestricted" in note and "Annotate" in note  # the prompt-size lever
    assert "transaction log" in note and "sk-valid" not in note
    keyless = _generation_failed_note(
        AIConfig(backend="gateway", gateway_endpoint=GATEWAY, gateway_approved=True),
        "server returned HTTP 401",
    )
    assert "Gateway API key" in keyless and "accepted your key" not in keyless
