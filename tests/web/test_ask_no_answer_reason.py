"""/api/ask says WHY there is no written answer — five causes, five different sentences.

THE OPERATOR-REPORTED DEFECT. A 32-version workbook, a long manipulation question, AI Settings
showing a configured local model — and the panel answered:

    "No local model is active (or strict mode discarded its answer) — these are the engine's
     cited facts that match your question."

Measured on this tree before the fix: a routed Null backend, an unreachable Ollama, an Ollama
that 404s the generation (the selected model is not installed), a generation that times out, an
empty completion, and a strict-mode discard ALL produced the same payload — ``answer: null``,
no other key — so one hard-coded sentence had to cover all of them. It named the least likely
cause first, and offered "strict mode discarded its answer" while the session ran in ANNOTATE
mode, where a discard is impossible.

The server knows which one happened in every case. These tests pin that it says so.
"""

from __future__ import annotations

import datetime as dt
import json
import shutil
import subprocess
import urllib.error
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.ai.backend import AIConfig
from schedule_forensics.ai.ollama import OllamaBackend
from schedule_forensics.ai.qa import NoAnswer
from schedule_forensics.importers import parse_mspdi
from schedule_forensics.web import app as app_module
from schedule_forensics.web.app import SessionState, _no_answer_note, create_app

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests" / "fixtures" / "golden" / "project2_5" / "Project5.mspdi.xml"
ENDPOINT = "http://127.0.0.1:12345"  # a NON-default port: the reason must name what is CONFIGURED
MODEL = "qwen2.5:7b-instruct"
QUESTION = "Do you see signs of an intentional effort to prevent UID 152 from slipping right?"


def _session(mode: str = "annotate", backend: str = "ollama") -> SessionState:
    st = SessionState()
    base = parse_mspdi(GOLDEN)
    for i in range(2):
        label = f"IPMR_v{i + 1:02d}.mpp"
        st.schedules[label] = base.model_copy(
            update={
                "name": label,
                "source_file": label,
                "status_date": dt.datetime(2026, 4, 15) + dt.timedelta(days=21 * i),
            }
        )
    st.ai_config = AIConfig(
        backend=backend, endpoint=ENDPOINT, model=MODEL, qa_mode=mode, gen_timeout=42.0
    )
    return st


def _opener(installed: tuple[str, ...], reply: str | BaseException):
    """A fake urllib opener for a REAL ``OllamaBackend`` (the repo's idiom): ``/api/tags``
    answers the install list, ``/api/generate`` returns a completion or raises."""

    def open_(url: str, data: bytes | None, timeout: float) -> str:
        if url.endswith("/api/tags"):
            if isinstance(installed, BaseException):  # pragma: no cover - defensive
                raise installed
            return json.dumps({"models": [{"name": n} for n in installed]})
        if isinstance(reply, BaseException):
            raise reply
        return json.dumps({"response": reply})

    return open_


def _dead_opener(exc: BaseException):
    def open_(url: str, data: bytes | None, timeout: float) -> str:
        raise exc

    return open_


def _ask(monkeypatch: pytest.MonkeyPatch, st: SessionState, opener: Any) -> dict[str, Any]:
    """POST the question with ``_ollama_or_none`` patched AT THE CALL SITE ``_active_backend``
    uses (``web.app``'s binding — the phase-1 monkeypatch trap, CLAUDE.md)."""
    if opener is not None:
        monkeypatch.setattr(
            app_module,
            "_ollama_or_none",
            lambda cfg: OllamaBackend(endpoint=cfg.endpoint, model=cfg.model, opener=opener),
        )
    client = TestClient(create_app(st))
    resp = client.post("/api/ask", data={"question": QUESTION})
    assert resp.status_code == 200
    return dict(resp.json())


_REFUSED = urllib.error.URLError(ConnectionRefusedError(111, "Connection refused"))
_TIMEOUT = urllib.error.URLError(TimeoutError("timed out"))
_NOT_FOUND = urllib.error.HTTPError(f"{ENDPOINT}/api/generate", 404, "Not Found", {}, None)  # type: ignore[arg-type]
_BOGUS = "The programme carries 987654 days of hidden float, so the date was protected."


# --- the census: distinct causes must not collapse into one sentence --------------------------


def test_five_distinct_failures_report_five_distinct_causes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """THE regression. Before the fix every one of these returned the identical payload."""
    cases = {
        "ai_off": (_session(backend="null"), None),
        "unreachable": (_session(), _dead_opener(_REFUSED)),
        "model_missing": (_session(), _opener(("llama3.1:8b",), _NOT_FOUND)),
        "empty": (_session(), _opener((MODEL,), "   \n")),
        "discarded": (_session("strict"), _opener((MODEL,), _BOGUS)),
    }
    seen: dict[str, tuple[str, str]] = {}
    for label, (st, opener) in cases.items():
        payload = _ask(monkeypatch, st, opener)
        assert payload["answer"] is None, label
        why = payload["no_answer"]
        assert why is not None, label
        seen[label] = (why["code"], why["text"])
    texts = [t for _, t in seen.values()]
    assert len(set(texts)) == len(cases), (
        f"distinct causes collapsed into {len(set(texts))} sentence(s): {seen}"
    )
    assert all(t.strip() for t in texts)
    # the code names the CLASS of failure; two of these five are both "nothing was routed" and
    # are separated by their sentence, not their code (AI switched off vs. a dead server).
    assert {c for c, _ in seen.values()} == {
        "no_model",
        "generation_failed",
        "empty_answer",
        "discarded_unsourced",
    }
    assert seen["ai_off"][0] == seen["unreachable"][0] == "no_model"
    assert seen["ai_off"][1] != seen["unreachable"][1]


def test_an_answered_question_carries_no_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """The negative half — a reason that also fires on success diagnoses nothing."""
    payload = _ask(monkeypatch, _session(), _opener((MODEL,), "The dates were held."))
    assert payload["answer"] is not None
    assert payload["no_answer"] is None


# --- each cause, by name ----------------------------------------------------------------------


def test_ai_switched_off_says_so(monkeypatch: pytest.MonkeyPatch) -> None:
    why = _ask(monkeypatch, _session(backend="null"), None)["no_answer"]
    assert why["code"] == "no_model"
    assert "off" in why["text"].lower()
    assert "AI Settings" in why["text"]


def test_an_unreachable_server_names_the_endpoint_and_the_refusal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    why = _ask(monkeypatch, _session(), _dead_opener(_REFUSED))["no_answer"]
    assert why["code"] == "no_model"
    assert ENDPOINT in why["text"]  # the CONFIGURED endpoint, not the default
    assert "refused" in why["text"].lower()


def test_a_model_that_is_not_installed_is_named_with_the_pull_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The cause the old sentence was WORST at: Ollama is up (so "no local model is active" is
    false), the generation 404s because the selected model was never pulled."""
    why = _ask(monkeypatch, _session(), _opener(("llama3.1:8b",), _NOT_FOUND))["no_answer"]
    assert why["code"] == "generation_failed"
    assert MODEL in why["text"]
    assert f"ollama pull {MODEL}" in why["text"]
    assert "llama3.1:8b" in why["text"]  # what IS installed, so the fix is one click away


def test_a_timeout_is_named_a_timeout_and_points_at_the_timeout_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    why = _ask(monkeypatch, _session(), _opener((MODEL,), _TIMEOUT))["no_answer"]
    assert why["code"] == "generation_failed"
    assert "timed out" in why["text"].lower()
    assert "42" in why["text"]  # the configured generation timeout, so the operator can raise it


def test_an_empty_completion_is_not_reported_as_a_missing_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    why = _ask(monkeypatch, _session(), _opener((MODEL,), "   \n"))["no_answer"]
    assert why["code"] == "empty_answer"
    assert "no local model is active" not in why["text"].lower()


def test_a_strict_discard_names_the_figure_and_the_way_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    why = _ask(monkeypatch, _session("strict"), _opener((MODEL,), _BOGUS))["no_answer"]
    assert why["code"] == "discarded_unsourced"
    assert "987654" in why["text"]
    assert "annotate" in why["text"].lower()  # the setting that would have kept the answer


@pytest.mark.parametrize("mode", ["annotate", "interpretive", "unrestricted"])
def test_a_non_strict_mode_never_blames_strict_mode(
    monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    """A discard is IMPOSSIBLE outside strict mode — offering it as the explanation is a
    statement the code cannot produce, which is what sent the operator to the wrong page."""
    for opener in (_dead_opener(_REFUSED), _opener((MODEL,), _NOT_FOUND), _opener((MODEL,), "")):
        why = _ask(monkeypatch, _session(mode), opener)["no_answer"]
        assert "strict" not in why["text"].lower(), (mode, why)
    off = _ask(monkeypatch, _session(mode, backend="null"), None)["no_answer"]
    assert "strict" not in off["text"].lower(), (mode, off)


class _DeadProbe:
    """A constructed-but-silent local backend, so the note census does no real I/O."""

    name = "ollama"
    is_local = True

    def is_available(self) -> bool:
        return False

    def unavailable_reason(self) -> str:
        return "connection refused - the model server isn't listening on this address"

    def list_models(self) -> tuple[str, ...]:
        return ()

    def pull_model(self, model: str) -> None: ...

    def generate(self, prompt: str) -> str:  # pragma: no cover - never generated from
        return ""


def test_only_a_strict_discard_ever_mentions_strict_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """A census over EVERY cause x EVERY backend selection, straight at the composer.

    The endpoint-level test above only ever walks the ``ollama`` branch, so a "strict" leaking
    into (say) the AI-switched-off sentence walked past it — measured, as mutation M7 of this
    change's battery. "strict" belongs to exactly one note: the discard.
    """
    monkeypatch.setattr(app_module, "_ollama_or_none", lambda cfg: _DeadProbe())
    monkeypatch.setattr(app_module, "_openai_or_none", lambda cfg: _DeadProbe())
    codes = ("no_model", "generation_failed", "empty_answer", "discarded_unsourced")
    for backend in ("null", "ollama", "openai", "gateway", "cloud"):
        cfg = AIConfig(backend=backend, endpoint=ENDPOINT, model=MODEL)
        for code in codes:
            text = _no_answer_note(cfg, NoAnswer(code, "1 figure the engine never computed (7)"))
            assert text.strip(), (backend, code)
            assert ("strict" in text.lower()) == (code == "discarded_unsourced"), (backend, code)


# --- the panel actually renders it ------------------------------------------------------------


def test_the_panel_no_longer_ships_the_blanket_sentence() -> None:
    js = (ROOT / "src" / "schedule_forensics" / "web" / "static" / "ask.js").read_text("utf-8")
    assert "No local model is active (or strict mode discarded its answer)" not in js


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH (local-gate tool)")
def test_the_panel_renders_the_servers_reason_under_node() -> None:
    """A source pin proves the sentence is gone; only execution proves the SERVER'S reason is
    what lands on screen (and that a payload without one still degrades to a usable line)."""
    node = shutil.which("node")
    assert node is not None
    harness = Path(__file__).parent / "js" / "ask_no_answer_harness.mjs"
    proc = subprocess.run(  # fixed argv, repo-local harness
        [node, str(harness)], cwd=ROOT, capture_output=True, text=True, timeout=120
    )
    assert proc.returncode == 0, f"harness failed:\n{proc.stdout}\n{proc.stderr}"
    assert proc.stdout.rstrip().endswith("OK ask no-answer"), proc.stdout
