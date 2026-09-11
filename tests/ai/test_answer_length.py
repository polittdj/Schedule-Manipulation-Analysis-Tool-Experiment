"""The answer length is the tool's to set, and a cut or empty answer says so (ADR-0486).

THE OPERATOR-REPORTED DEFECT, three asks in a row on the approved gateway (a *thinking* model,
``claude-opus-4.8-thinking-itar``): two answers stopped mid-sentence ("an SPI of", "A schedule
genuinely 62 workdays behind"), then a slightly longer question produced *"The local model ran
but returned no text … select a different model in AI Settings."* Measured on this tree before
the fix: neither OpenAI-compatible backend sends ``max_tokens`` (the server's own default output
budget governs — a thinking model spends it reasoning), neither reads ``finish_reason`` (a
``length`` stop renders as a complete answer), neither reads the reasoning fields (so "no
answer text" cannot be told apart from "no answer at all"), and a ``null`` ``content`` became
the literal word ``None``.

Pinned here: the limit is sent (default = the maximum the form allows — operator directive,
2026-09-11: *"raise the limit to the max"*), ``0`` sends none, a server that REJECTS the value
(HTTP 400 naming it) gets the request once more without it and the rejection is recorded, a
``length`` stop is recorded and worded, reasoning is counted, ``null`` content is empty, and the
value reaches every construction path (primary, cross-check, gateway) and survives the settings
file.

UNVERIFIED, stated: the true output ceiling of the operator's gateway model. No universal
maximum exists — each model/server has its own — which is exactly why the rejection fallback
exists instead of a hard-coded "max".
"""

from __future__ import annotations

import io
import json
import urllib.error
from pathlib import Path
from typing import Any

import pytest

import schedule_forensics.ai.factory as factory
from schedule_forensics.ai import config_store
from schedule_forensics.ai.backend import AIConfig
from schedule_forensics.ai.completion import (
    DEFAULT_ANSWER_TOKENS,
    MAX_ANSWER_TOKENS,
    MIN_ANSWER_TOKENS,
    CompletionStats,
    answer_cut_warning,
    clamp_answer_tokens,
    empty_answer_detail,
    limit_rejected,
    read_completion,
)
from schedule_forensics.ai.gateway import GatewayBackend
from schedule_forensics.ai.openai_compat import OpenAICompatBackend

GATEWAY = "https://proxy.fast.luna.nasa.gov"
FIELD = "Answer length limit"


def _http_error(code: int, body: str, url: str = "http://127.0.0.1:1234/v1/chat/completions"):
    return urllib.error.HTTPError(url, code, "Bad Request", {}, io.BytesIO(body.encode("utf-8")))  # type: ignore[arg-type]


# --- the bound and its clamp ------------------------------------------------------------------


def test_the_default_is_the_maximum_and_the_bound_is_sane() -> None:
    """Operator directive: the default IS the maximum — a long forensic answer must never be
    cut by a server default the operator never chose."""
    assert DEFAULT_ANSWER_TOKENS == MAX_ANSWER_TOKENS
    assert AIConfig().answer_max_tokens == MAX_ANSWER_TOKENS
    assert 0 < MIN_ANSWER_TOKENS < MAX_ANSWER_TOKENS
    assert MAX_ANSWER_TOKENS == 131_072


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (0, 0),
        (-5, 0),
        (1, MIN_ANSWER_TOKENS),
        (MIN_ANSWER_TOKENS, MIN_ANSWER_TOKENS),
        (4_096, 4_096),
        (MAX_ANSWER_TOKENS, MAX_ANSWER_TOKENS),
        (MAX_ANSWER_TOKENS + 1, MAX_ANSWER_TOKENS),
        (10_000_000, MAX_ANSWER_TOKENS),
    ],
)
def test_the_clamp_bounds_every_value_and_keeps_zero_meaning_off(raw: int, expected: int) -> None:
    assert clamp_answer_tokens(raw) == expected


# --- the completion reader ---------------------------------------------------------------------


def test_a_null_or_absent_content_is_empty_never_the_word_none() -> None:
    """The regression the old ``str(content)`` shipped: ``null`` became the four-letter
    answer "None", which then passed every figure gate as prose."""
    text, _ = read_completion({"choices": [{"message": {"content": None}}]})
    assert text == ""
    text, _ = read_completion({"choices": [{"message": {"role": "assistant"}}]})
    assert text == ""
    text, _ = read_completion({"choices": []})
    assert text == ""
    text, _ = read_completion({"error": {"message": "nope"}})
    assert text == ""
    text, _ = read_completion({"choices": [{"message": {"content": "  real  "}}]})
    assert text == "  real  "  # the reader does not strip; the QA layer decides that


def test_finish_reason_reasoning_and_usage_are_read_as_evidence() -> None:
    _, stats = read_completion(
        {
            "choices": [
                {
                    "finish_reason": "length",
                    "message": {"content": "", "reasoning_content": "x" * 1234},
                }
            ],
            "usage": {"completion_tokens": 4096},
        }
    )
    assert stats.finish_reason == "length"
    assert stats.content_chars == 0 and stats.reasoning_chars == 1234
    assert stats.completion_tokens == 4096
    # the alternative field name some servers use, and a clean stop
    _, stats2 = read_completion(
        {"choices": [{"finish_reason": "stop", "message": {"content": "ok", "reasoning": "yy"}}]}
    )
    assert stats2.finish_reason == "stop" and stats2.reasoning_chars == 2
    assert stats2.content_chars == 2 and stats2.completion_tokens is None


# --- the rejection detector --------------------------------------------------------------------


def test_only_a_400_that_names_the_parameter_reads_as_a_rejected_limit() -> None:
    assert limit_rejected(_http_error(400, '{"error":{"message":"max_tokens is too large"}}'))
    assert limit_rejected(_http_error(400, "Unsupported parameter: max_completion_tokens"))
    assert not limit_rejected(_http_error(400, '{"error":"model not found"}'))
    assert not limit_rejected(_http_error(403, "max_tokens"))  # a refusal is not a rejection
    assert not limit_rejected(_http_error(500, "max_tokens"))
    assert not limit_rejected(urllib.error.HTTPError("http://x", 400, "Bad Request", {}, None))  # type: ignore[arg-type]
    assert not limit_rejected(OSError("connection refused"))


# --- the backends send it, and fall back honestly ----------------------------------------------


def _openai_opener(script: list[Any], seen: list[dict[str, Any]]):
    """Each call pops the next scripted reply (a dict body or an exception to raise) and
    records the JSON it was sent."""

    def opener(url: str, data: bytes | None, timeout: float, headers: dict[str, str]) -> str:
        if url.endswith("/v1/models"):
            return json.dumps({"data": [{"id": "m"}]})
        seen.append(json.loads(data or b"{}"))
        reply = script.pop(0)
        if isinstance(reply, BaseException):
            raise reply
        return json.dumps(reply)

    return opener


_OK = {"choices": [{"finish_reason": "stop", "message": {"content": "ANSWER"}}]}


def test_openai_compat_sends_the_limit_by_default_and_nothing_when_zero() -> None:
    seen: list[dict[str, Any]] = []
    OpenAICompatBackend(model="m", opener=_openai_opener([_OK], seen)).generate("Q")
    assert seen[0]["max_tokens"] == MAX_ANSWER_TOKENS
    seen.clear()
    OpenAICompatBackend(model="m", max_tokens=4096, opener=_openai_opener([_OK], seen)).generate(
        "Q"
    )
    assert seen[0]["max_tokens"] == 4096
    seen.clear()
    OpenAICompatBackend(model="m", max_tokens=0, opener=_openai_opener([_OK], seen)).generate("Q")
    assert "max_tokens" not in seen[0]


def test_openai_compat_clamps_the_constructor_value_too() -> None:
    seen: list[dict[str, Any]] = []
    be = OpenAICompatBackend(model="m", max_tokens=10_000_000, opener=_openai_opener([_OK], seen))
    be.generate("Q")
    assert seen[0]["max_tokens"] == MAX_ANSWER_TOKENS


def test_a_rejected_limit_is_retried_once_without_it_and_recorded() -> None:
    seen: list[dict[str, Any]] = []
    script = [
        _http_error(400, '{"error":{"message":"max_tokens: 131072 exceeds the model limit"}}'),
        _OK,
    ]
    be = OpenAICompatBackend(model="m", opener=_openai_opener(script, seen))
    assert be.generate("Q") == "ANSWER"
    assert len(seen) == 2
    assert seen[0]["max_tokens"] == MAX_ANSWER_TOKENS and "max_tokens" not in seen[1]
    assert seen[1]["messages"] == seen[0]["messages"]  # the same question, only the limit dropped
    assert be.last_completion is not None
    assert be.last_completion.limit_rejected is True
    assert be.last_completion.max_tokens_sent == MAX_ANSWER_TOKENS


def test_a_400_that_does_not_name_the_limit_is_not_retried() -> None:
    seen: list[dict[str, Any]] = []
    script = [_http_error(400, '{"error":"model not found"}'), _OK]
    be = OpenAICompatBackend(model="m", opener=_openai_opener(script, seen))
    with pytest.raises(urllib.error.HTTPError):
        be.generate("Q")
    assert len(seen) == 1


def test_a_second_rejection_propagates_no_infinite_retry() -> None:
    seen: list[dict[str, Any]] = []
    script = [_http_error(400, "max_tokens too large"), _http_error(400, "max_tokens too large")]
    be = OpenAICompatBackend(model="m", opener=_openai_opener(script, seen))
    with pytest.raises(urllib.error.HTTPError):
        be.generate("Q")
    assert len(seen) == 2


def test_the_backend_records_the_completion_evidence() -> None:
    seen: list[dict[str, Any]] = []
    cut = {
        "choices": [
            {
                "finish_reason": "length",
                "message": {"content": "partial", "reasoning_content": "hmm"},
            }
        ],
        "usage": {"completion_tokens": 77},
    }
    be = OpenAICompatBackend(model="m", max_tokens=2048, opener=_openai_opener([cut], seen))
    assert be.generate("Q") == "partial"
    stats = be.last_completion
    assert stats is not None and stats.finish_reason == "length"
    assert stats.reasoning_chars == 3 and stats.completion_tokens == 77
    assert stats.max_tokens_sent == 2048 and stats.limit_rejected is False


def test_a_null_content_from_the_backend_is_empty() -> None:
    seen: list[dict[str, Any]] = []
    body = {
        "choices": [
            {"finish_reason": "length", "message": {"content": None, "reasoning": "r" * 50}}
        ]
    }
    be = OpenAICompatBackend(model="m", opener=_openai_opener([body], seen))
    assert be.generate("Q") == ""
    assert be.last_completion is not None and be.last_completion.reasoning_chars == 50


class _GatewayOpener:
    def __init__(self, script: list[Any]) -> None:
        self.script = script
        self.seen: list[dict[str, Any]] = []

    def __call__(
        self, url: str, data: bytes | None, timeout: float, headers: dict[str, str]
    ) -> str:
        if url.endswith("/v1/models"):
            return json.dumps({"data": [{"id": "claude-opus-4.8-thinking-itar"}]})
        self.seen.append(json.loads(data or b"{}"))
        reply = self.script.pop(0)
        if isinstance(reply, BaseException):
            raise reply
        return json.dumps(reply)


def _gateway(tmp_path: Path, script: list[Any], **kw: Any) -> tuple[GatewayBackend, _GatewayOpener]:
    op = _GatewayOpener(script)
    be = GatewayBackend(
        GATEWAY,
        model="claude-opus-4.8-thinking-itar",
        classification="CLASSIFIED",
        opener=op,
        log_path=tmp_path / "tx.jsonl",
        **kw,
    )
    return be, op


def test_the_gateway_sends_the_limit_and_falls_back_the_same_way(tmp_path: Path) -> None:
    be, op = _gateway(tmp_path, [_OK])
    assert be.generate("Q") == "ANSWER"
    assert op.seen[0]["max_tokens"] == MAX_ANSWER_TOKENS
    rejected = _http_error(
        400,
        '{"error":{"message":"max_tokens exceeds model maximum"}}',
        f"{GATEWAY}/v1/chat/completions",
    )
    be2, op2 = _gateway(tmp_path, [rejected, _OK], max_tokens=65_536)
    assert be2.generate("Q") == "ANSWER"
    assert op2.seen[0]["max_tokens"] == 65_536 and "max_tokens" not in op2.seen[1]
    assert be2.last_completion is not None and be2.last_completion.limit_rejected is True
    be3, op3 = _gateway(tmp_path, [_OK], max_tokens=0)
    be3.generate("Q")
    assert "max_tokens" not in op3.seen[0]


def test_the_gateway_logs_both_attempts_and_never_the_answer_budget_as_content(
    tmp_path: Path,
) -> None:
    """Law 1 bookkeeping: the retry is a second transmission and is recorded as one."""
    rejected = _http_error(400, "max_tokens too large", f"{GATEWAY}/v1/chat/completions")
    be, _ = _gateway(tmp_path, [rejected, _OK])
    be.generate("Q")
    lines = [json.loads(ln) for ln in (tmp_path / "tx.jsonl").read_text().splitlines() if ln]
    kinds = [(ln["kind"], ln.get("ok")) for ln in lines if ln["kind"].startswith("generate")]
    assert kinds == [
        ("generate.sent", None),
        ("generate.done", False),
        ("generate.sent", None),
        ("generate.done", True),
    ]


# --- the disclosures -----------------------------------------------------------------------------


def test_a_length_stop_is_worded_with_the_setting_and_the_requested_budget() -> None:
    stats = CompletionStats(
        finish_reason="length", content_chars=900, completion_tokens=4096, max_tokens_sent=4096
    )
    text = answer_cut_warning(stats)
    assert text is not None
    assert "CUT" in text and FIELD in text and "4,096" in text and "finish_reason=length" in text
    assert "thinking" in text.lower()  # the mechanism a thinking model adds


def test_a_rejected_limit_is_worded_as_the_servers_default_having_cut_it() -> None:
    stats = CompletionStats(finish_reason="length", max_tokens_sent=131_072, limit_rejected=True)
    text = answer_cut_warning(stats)
    assert text is not None
    assert "REJECTED" in text and "131,072" in text and FIELD in text and "lower" in text.lower()


def test_no_limit_sent_is_worded_as_the_servers_default() -> None:
    stats = CompletionStats(finish_reason="length", max_tokens_sent=None)
    text = answer_cut_warning(stats)
    assert text is not None and "0" in text and FIELD in text


def test_a_clean_stop_or_no_evidence_is_silent() -> None:
    assert answer_cut_warning(CompletionStats(finish_reason="stop")) is None
    assert answer_cut_warning(CompletionStats(finish_reason="")) is None
    assert answer_cut_warning(None) is None


def test_the_empty_answer_detail_names_the_budget_spent_thinking() -> None:
    both = empty_answer_detail(CompletionStats(finish_reason="length", reasoning_chars=8_000))
    assert "8,000" in both and "reasoning" in both and "finish_reason=length" in both
    only_reasoning = empty_answer_detail(CompletionStats(finish_reason="stop", reasoning_chars=12))
    assert "12" in only_reasoning and "reasoning" in only_reasoning
    only_length = empty_answer_detail(CompletionStats(finish_reason="length"))
    assert "finish_reason=length" in only_length
    assert empty_answer_detail(CompletionStats(finish_reason="stop")) == ""
    assert empty_answer_detail(None) == ""


# --- the value reaches every construction, and survives the settings file ----------------------


def test_the_factory_threads_the_limit_to_primary_second_and_gateway() -> None:
    cfg = AIConfig(
        backend="openai", answer_max_tokens=8_192, second_backend="openai", second_model="m2"
    )
    primary = factory.openai_or_none(cfg)
    second = factory.second_or_none(cfg)
    assert primary is not None and primary._max_tokens == 8_192
    assert second is not None and getattr(second, "_max_tokens", None) == 8_192
    armed = AIConfig(
        backend="gateway", gateway_endpoint=GATEWAY, gateway_approved=True, answer_max_tokens=8_192
    )
    gw = factory.gateway_or_none(armed)
    assert gw is not None and gw._max_tokens == 8_192
    assert factory.openai_or_none(AIConfig(backend="openai"))._max_tokens == MAX_ANSWER_TOKENS  # type: ignore[union-attr]


def test_the_settings_file_round_trips_clamps_and_defaults_to_the_maximum(tmp_path: Path) -> None:
    path = tmp_path / "ai-settings.json"
    config_store.save_ai_config(AIConfig(backend="openai", answer_max_tokens=8_192), path)
    assert config_store.load_ai_config(path).answer_max_tokens == 8_192
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["answer_max_tokens"] = 99_999_999  # a hand-typed absurdity is bounded at the load boundary
    path.write_text(json.dumps(doc), encoding="utf-8")
    assert config_store.load_ai_config(path).answer_max_tokens == MAX_ANSWER_TOKENS
    doc["answer_max_tokens"] = "lots"  # a non-integer reads as the default, never a crash
    path.write_text(json.dumps(doc), encoding="utf-8")
    assert config_store.load_ai_config(path).answer_max_tokens == MAX_ANSWER_TOKENS
    del doc["answer_max_tokens"]  # every file written before ADR-0486: the maximum, per directive
    path.write_text(json.dumps(doc), encoding="utf-8")
    assert config_store.load_ai_config(path).answer_max_tokens == MAX_ANSWER_TOKENS
    doc["answer_max_tokens"] = 0  # an explicit OFF survives
    path.write_text(json.dumps(doc), encoding="utf-8")
    assert config_store.load_ai_config(path).answer_max_tokens == 0
