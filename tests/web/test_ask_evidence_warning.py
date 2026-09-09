"""An answer formed on a truncated prompt says so, next to the answer (OR-11c).

ADR-0478 made a MISSING answer explain itself. This is the harder half: the answer ARRIVES —
fluent, cited, confident — and the model never read all the evidence, because the prompt exceeded
the Ollama context window and Ollama drops the overflow rather than erroring. On a 32-version
workbook that is the prompt this tool routinely builds.

The tool cannot know the operator's window (it never sends `num_ctx`, and Ollama's defaults are
VRAM-tiered and moved in v0.15.5). It does not need to: `/api/generate` reports
`prompt_eval_count`, and a count below what the prompt could possibly tokenize to is proof.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from schedule_forensics.ai.backend import AIConfig
from schedule_forensics.ai.ollama import OllamaBackend
from schedule_forensics.importers import parse_mspdi
from schedule_forensics.web import app as app_module
from schedule_forensics.web.app import SessionState, create_app

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests" / "fixtures" / "golden" / "project2_5" / "Project5.mspdi.xml"
ANSWER = "The programme is behind its plan."


def _session() -> SessionState:
    st = SessionState()
    st.schedules["v1"] = parse_mspdi(GOLDEN)
    st.ai_config = AIConfig(backend="ollama", model="m", qa_mode="annotate")
    return st


def _opener(body: dict[str, object]):
    def open_(url: str, data: bytes | None, timeout: float) -> str:
        if url.endswith("/api/tags"):
            return json.dumps({"models": [{"name": "m"}]})
        return json.dumps(body)

    return open_


def _ask(monkeypatch, body: dict[str, object], *, marking: bool = False) -> dict[str, object]:
    monkeypatch.setattr(
        app_module,
        "_ollama_or_none",
        lambda cfg: OllamaBackend(model=cfg.model, opener=_opener(body)),
    )
    st = _session()
    if marking:
        # ADR-0315: a routed Ollama is WRAPPED in `_UseMarking` whenever the launcher hook
        # is set — i.e. in the deployed app. Without this the tests only ever measure the
        # bare backend, and a wrapper that swallowed the measurement would keep them green.
        st.ai_use_hook = lambda model, endpoint: None
    resp = TestClient(create_app(st)).post(
        "/api/ask", data={"question": "Is the schedule slipping?"}
    )
    assert resp.status_code == 200
    return dict(resp.json())


def test_a_truncated_prompt_is_disclosed_beside_the_answer(monkeypatch) -> None:
    """THE defect: the answer arrives and nothing says the model read part of the evidence."""
    body = _ask(monkeypatch, {"response": ANSWER, "prompt_eval_count": 12})
    assert body["answer"] is not None and ANSWER in str(body["answer"])
    warning = body["evidence_warning"]
    assert warning is not None
    assert "12" in str(warning) and "OLLAMA_CONTEXT_LENGTH" in str(warning)


def test_an_untruncated_answer_carries_no_warning(monkeypatch) -> None:
    """The negative half — a warning that also fires on a complete prompt is noise."""
    body = _ask(monkeypatch, {"response": ANSWER, "prompt_eval_count": 10_000_000})
    assert body["answer"] is not None
    assert body["evidence_warning"] is None


def test_a_server_reporting_no_count_is_not_accused(monkeypatch) -> None:
    body = _ask(monkeypatch, {"response": ANSWER})
    assert body["answer"] is not None
    assert body["evidence_warning"] is None


def test_no_model_no_warning(monkeypatch) -> None:
    """With nothing routed there is no generation to measure — and ADR-0478's `no_answer`
    already explains that case. Two disclosures for one state would contradict each other."""
    st = _session()
    st.ai_config = AIConfig(backend="null")
    body = TestClient(create_app(st)).post("/api/ask", data={"question": "x?"}).json()
    assert body["answer"] is None
    assert body["evidence_warning"] is None
    assert body["no_answer"] is not None


def test_the_panel_renders_the_warning() -> None:
    js = (ROOT / "src" / "schedule_forensics" / "web" / "static" / "ask.js").read_text("utf-8")
    assert "evidence_warning" in js


def test_the_use_marking_wrapper_does_not_swallow_the_warning(monkeypatch) -> None:
    """The DEPLOYED path. `_active_backend` wraps a routed Ollama in `_UseMarking` (ADR-0315),
    and the wrapper forwards only the protocol's own methods — so the measurement needs an
    explicit passthrough. Measured: removing it leaves every other test in this file green
    while the disclosure disappears from the real app."""
    body = _ask(monkeypatch, {"response": ANSWER, "prompt_eval_count": 12}, marking=True)
    assert body["answer"] is not None
    assert body["evidence_warning"] is not None
    assert "12" in str(body["evidence_warning"])
