"""GatewayBackend + the AI transaction log (ADR-0402): recorded, deterministic, fail-closed.

The properties pinned here, layer by layer:

* **Nothing leaves unrecorded.** The ``*.sent`` record hits disk BEFORE the transport is
  invoked; a log that cannot be written aborts the transmission with the opener never
  called (fail closed). The record carries what-left/when/where/under-which-classification
  as a content hash + byte count — never the prompt text (the log must not become CUI).
* **Consent gates routing at every layer.** ``factory.gateway_or_none`` returns ``None``
  without the acknowledgment; ``route_backend`` refuses an already-constructed gateway
  object without it; the gateway is never a fallback for any other backend selection.
* **The banner never softens by accident.** The APPROVED-GATEWAY wording requires the
  backend to MEASURE ``is_approved_gateway`` and the config to carry both arming fields;
  anything less falls through to the harsher generic non-local warning.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from schedule_forensics.ai import factory, txlog
from schedule_forensics.ai.backend import (
    AIConfig,
    Classification,
    banner_for,
    banner_for_backend,
    route_backend,
)
from schedule_forensics.ai.gateway import GatewayBackend
from schedule_forensics.ai.null import NullBackend

ENDPOINT = "https://proxy.fast.luna.nasa.gov"


class _Recorder:
    """An injectable opener that records calls and serves canned OpenAI-shape responses."""

    def __init__(self, fail: bool = False) -> None:
        self.calls: list[tuple[str, bytes | None, float]] = []
        self.fail = fail
        self.log_lines_at_call: list[int] = []
        self.log_path: Path | None = None

    def __call__(self, url: str, data: bytes | None, timeout: float) -> str:
        if self.log_path is not None:  # measure ORDER: how many records existed pre-transmit
            text = self.log_path.read_text() if self.log_path.exists() else ""
            self.log_lines_at_call.append(len([ln for ln in text.splitlines() if ln]))
        self.calls.append((url, data, timeout))
        if self.fail:
            raise OSError("connection refused")
        if url.endswith("/v1/models"):
            return json.dumps({"data": [{"id": "claude-opus-4.8-thinking-itar"}, {"id": "m2"}]})
        return json.dumps({"choices": [{"message": {"content": "ANSWER"}}]})


def _gateway(tmp_path: Path, opener: _Recorder | None = None, **kw: object) -> GatewayBackend:
    op = opener or _Recorder()
    log = tmp_path / "tx.jsonl"
    op.log_path = log
    return GatewayBackend(
        ENDPOINT,
        model="claude-opus-4.8-thinking-itar",
        classification="CLASSIFIED",
        opener=op,
        log_path=log,
        **kw,  # type: ignore[arg-type]
    )


def _lines(tmp_path: Path) -> list[dict[str, object]]:
    text = (tmp_path / "tx.jsonl").read_text()
    return [json.loads(ln) for ln in text.splitlines() if ln]


# --- the transaction log ------------------------------------------------------------------


def test_generate_records_sent_before_transmitting_and_done_after(tmp_path: Path) -> None:
    op = _Recorder()
    be = _gateway(tmp_path, op)
    assert be.generate("PROMPT with schedule content") == "ANSWER"
    lines = _lines(tmp_path)
    assert [ln["kind"] for ln in lines] == ["generate.sent", "generate.done"]
    # ORDER measured, not assumed: at transmit time exactly the sent record existed
    assert op.log_lines_at_call == [1]
    sent, done = lines
    raw = b"PROMPT with schedule content"
    assert sent["endpoint"] == ENDPOINT and sent["classification"] == "CLASSIFIED"
    assert sent["model"] == "claude-opus-4.8-thinking-itar"
    # the content itself never reaches the file — hash + byte count only
    assert sent["prompt_sha256"] == hashlib.sha256(raw).hexdigest()
    assert sent["prompt_bytes"] == len(raw)
    assert "PROMPT" not in (tmp_path / "tx.jsonl").read_text()
    assert done["ok"] is True and isinstance(done["response_bytes"], int)


def test_an_unwritable_log_aborts_the_transmission_with_nothing_sent(tmp_path: Path) -> None:
    """Fail closed: no record, no egress — the opener must never be reached."""
    op = _Recorder()
    log = tmp_path / "not-a-dir"
    log.write_text("a file where the log DIRECTORY must be created")
    be = GatewayBackend(
        ENDPOINT, model="m", opener=op, log_path=log / "tx.jsonl", classification="CLASSIFIED"
    )
    with pytest.raises(OSError):  # mkdir over a file: the record write fails, so nothing sends
        be.generate("schedule content")
    assert op.calls == []  # nothing was transmitted
    # and the same failure makes the availability probe read DOWN, so routing falls to Null
    assert be.is_available() is False
    cfg = AIConfig(backend="gateway", gateway_endpoint=ENDPOINT, gateway_approved=True)
    routed, _banner = route_backend(cfg, null_backend=NullBackend(), gateway_backend=be)
    assert routed.name == "null"


def test_probe_and_model_list_are_recorded_too(tmp_path: Path) -> None:
    be = _gateway(tmp_path)
    assert be.is_available() is True
    assert be.list_models() == ("claude-opus-4.8-thinking-itar", "m2")
    kinds = [ln["kind"] for ln in _lines(tmp_path)]
    assert kinds == ["probe.sent", "probe.done", "models.sent", "models.done"]


def test_a_failed_transmission_records_a_sanitized_failure(tmp_path: Path) -> None:
    op = _Recorder(fail=True)
    be = _gateway(tmp_path, op)
    with pytest.raises(OSError):
        be.generate("p")
    sent, done = _lines(tmp_path)
    assert sent["kind"] == "generate.sent" and done["kind"] == "generate.done"
    assert done["ok"] is False
    assert "refused" in str(done["error"])  # the short probe reason, not a raw dump


def test_default_log_path_honors_the_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SF_AI_LOG_DIR", "/somewhere/audit")
    assert txlog.default_log_path() == Path("/somewhere/audit") / "ai-transactions.jsonl"
    monkeypatch.delenv("SF_AI_LOG_DIR")
    assert txlog.default_log_path().name == "ai-transactions.jsonl"
    # never inside the clear-on-quit cache dir
    assert ".cache" not in str(txlog.default_log_path())


# --- the wire format ----------------------------------------------------------------------


def test_generate_sends_the_deterministic_openai_payload(tmp_path: Path) -> None:
    op = _Recorder()
    be = _gateway(tmp_path, op)
    be.generate("Q")
    url, data, _timeout = op.calls[0]
    assert url == f"{ENDPOINT}/v1/chat/completions"
    assert data is not None
    payload = json.loads(data)
    assert payload["model"] == "claude-opus-4.8-thinking-itar"
    assert payload["messages"] == [{"role": "user", "content": "Q"}]
    assert payload["temperature"] == 0.0 and payload["seed"] == 0
    assert payload["stream"] is False


def test_pull_model_is_refused_with_a_catalog_hint(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="catalog"):
        _gateway(tmp_path).pull_model("anything")


# --- routing consent + banner truth -------------------------------------------------------


def test_factory_requires_selection_and_acknowledgment_and_allowlist() -> None:
    armed = AIConfig(backend="gateway", gateway_endpoint=ENDPOINT, gateway_approved=True)
    assert factory.gateway_or_none(armed) is not None
    for cfg in (
        AIConfig(backend="gateway", gateway_endpoint=ENDPOINT),  # no acknowledgment
        AIConfig(backend="ollama", gateway_endpoint=ENDPOINT, gateway_approved=True),  # not chosen
        AIConfig(backend="gateway", gateway_approved=True),  # no endpoint
        AIConfig(  # endpoint off the allowlist
            backend="gateway", gateway_endpoint="https://evil.com", gateway_approved=True
        ),
    ):
        assert factory.gateway_or_none(cfg) is None


def test_route_refuses_a_supplied_gateway_without_the_acknowledgment(tmp_path: Path) -> None:
    be = _gateway(tmp_path)
    cfg = AIConfig(backend="gateway", gateway_endpoint=ENDPOINT)  # gateway_approved=False
    routed, banner = route_backend(cfg, null_backend=NullBackend(), gateway_backend=be)
    assert routed.name == "null"
    assert banner.cloud_active is True  # the standing intent still warns (§0.2)
    assert "Local-only" not in banner.text


def test_route_serves_the_gateway_only_when_fully_armed_and_reachable(tmp_path: Path) -> None:
    be = _gateway(tmp_path)
    cfg = AIConfig(backend="gateway", gateway_endpoint=ENDPOINT, gateway_approved=True)
    routed, banner = route_backend(cfg, null_backend=NullBackend(), gateway_backend=be)
    assert routed is be
    assert banner.cloud_active is True and ENDPOINT in banner.text
    assert "APPROVED GATEWAY" in banner.text and "Local-only" not in banner.text


def test_the_gateway_is_never_a_fallback_for_other_selections(tmp_path: Path) -> None:
    be = _gateway(tmp_path)
    for cfg in (AIConfig(backend="ollama"), AIConfig(backend="null"), AIConfig(backend="openai")):
        routed, banner = route_backend(cfg, null_backend=NullBackend(), gateway_backend=be)
        assert routed.name == "null" and banner.cloud_active is False


def test_gateway_config_warns_under_both_classifications_even_while_unarmed() -> None:
    for cls in (Classification.CLASSIFIED, Classification.UNCLASSIFIED):
        cfg = AIConfig(classification=cls, backend="gateway")
        shown = banner_for(cfg)
        _routed, routed_banner = route_backend(cfg, null_backend=NullBackend())
        assert shown.cloud_active is True and routed_banner.cloud_active is True
        assert shown.text == routed_banner.text  # the two derivations may never disagree


def test_the_approved_wording_requires_measurement_and_both_arming_fields(
    tmp_path: Path,
) -> None:
    """Fail-closed WORDING: anything short of (measured gateway) + (chosen) + (acknowledged)
    gets the harsher generic non-local warning, never the approved-gateway sentence."""
    be = _gateway(tmp_path)
    armed = AIConfig(backend="gateway", gateway_endpoint=ENDPOINT, gateway_approved=True)
    assert "APPROVED GATEWAY" in banner_for_backend(be, armed).text

    class _Impostor:  # declares the name but cannot MEASURE approval
        name = "gateway"
        is_local = False
        endpoint = ENDPOINT

        def is_available(self) -> bool:
            return True

        def list_models(self) -> tuple[str, ...]:
            return ()

        def pull_model(self, model: str) -> None: ...

        def generate(self, prompt: str) -> str:
            return prompt

    assert "APPROVED GATEWAY" not in banner_for_backend(_Impostor(), armed).text
    unacknowledged = AIConfig(backend="gateway", gateway_endpoint=ENDPOINT)
    assert "APPROVED GATEWAY" not in banner_for_backend(be, unacknowledged).text
    not_chosen = AIConfig(backend="ollama", gateway_approved=True)
    assert "APPROVED GATEWAY" not in banner_for_backend(be, not_chosen).text
    for text in (
        banner_for_backend(_Impostor(), armed).text,
        banner_for_backend(be, unacknowledged).text,
        banner_for_backend(be, not_chosen).text,
    ):
        assert "Local-only" not in text  # never soften all the way to the assurance


def test_second_backend_can_never_be_the_gateway() -> None:
    """The cross-check second model receives every prompt too — it stays local-only by
    design (the factory refuses anything but the two local kinds)."""
    cfg = AIConfig(
        backend="null",
        second_backend="gateway",
        gateway_endpoint=ENDPOINT,
        gateway_approved=True,
    )
    assert factory.second_or_none(cfg) is None
