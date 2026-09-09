"""An operator-set context window is SENT, bounded, and disclosed (OR-11e, ADR-0481).

ADR-0480 made a partly-read prompt say so; it deliberately stopped short of doing anything
about it, because the only lever — Ollama's `num_ctx` — is the one that can take a machine
down. `ollama/ollama#14073` records a 52 GB box going unresponsive when v0.15.5's larger
VRAM-tiered default spilled the KV cache to CPU, so raising the window automatically was
refused. What was left is the gap this unit closes: the tool never sent `num_ctx` AT ALL,
so an operator who read the truncation disclosure had no remedy inside the tool.

The design is therefore: **off by default, operator-set, bounded, and reported.**

* `num_ctx = 0` sends NOTHING — byte-for-byte today's request. The server's own default
  (`OLLAMA_CONTEXT_LENGTH`, or the VRAM tier) still governs, and the tool makes no claim
  about it.
* A non-zero value is clamped into `[MIN_NUM_CTX, MAX_NUM_CTX]`. The ceiling is not
  invented: 262,144 is Ollama's OWN default for the `>= 48 GiB` tier (#14073), so the tool
  will never let an operator request more than Ollama itself would hand the largest machine.
* What we SENT is recorded on the generation stats, so the truncation disclosure can name
  the window already requested instead of telling an operator to raise what they raised.

**Not verified here and deliberately not claimed anywhere:** what the server DOES on
receipt. There is no Ollama in this container, and ADR-0480 already recorded the truncation
semantics as not verbatim-confirmed. These checks prove what leaves the tool — the payload —
which is the whole of what the tool controls.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from schedule_forensics.ai.backend import AIConfig
from schedule_forensics.ai.config_store import load_ai_config, save_ai_config
from schedule_forensics.ai.ollama import (
    MAX_NUM_CTX,
    MIN_NUM_CTX,
    GenerationStats,
    OllamaBackend,
    clamp_num_ctx,
    truncation_warning,
)


def _capturing() -> tuple[list[dict[str, Any]], Any]:
    """An opener that records every POST body and answers like a real /api/generate."""
    seen: list[dict[str, Any]] = []

    def open_(url: str, data: bytes | None, timeout: float) -> str:
        if data is not None:
            seen.append(json.loads(data.decode("utf-8")))
        return json.dumps({"response": "ok", "prompt_eval_count": 10})

    return seen, open_


# --- what actually goes on the wire -----------------------------------------------------------


def test_no_window_configured_sends_no_num_ctx() -> None:
    """The default is the CURRENT behaviour, unchanged: the tool must not start dictating a
    window to every operator's server as a side effect of gaining the ability to."""
    seen, open_ = _capturing()
    OllamaBackend(model="m", opener=open_).generate("hello")
    assert seen and "num_ctx" not in seen[0]["options"]


def test_a_configured_window_is_sent_verbatim_in_options() -> None:
    """The value the operator set is the value on the wire — not a rounded, defaulted or
    re-derived one. `options.num_ctx` is Ollama's documented per-request window."""
    seen, open_ = _capturing()
    OllamaBackend(model="m", opener=open_, num_ctx=32_768).generate("hello")
    assert seen[0]["options"]["num_ctx"] == 32_768


def test_sending_a_window_disturbs_nothing_else_about_the_request() -> None:
    """Determinism (temperature/seed/top_p) and the residency bound are load-bearing for
    other reasons; a new option must not displace them."""
    seen, open_ = _capturing()
    OllamaBackend(model="m", opener=open_, num_ctx=8_192).generate("hello")
    opts = seen[0]["options"]
    assert opts["temperature"] == 0.0 and opts["seed"] == 0 and opts["top_p"] == 1.0
    assert seen[0]["keep_alive"] and seen[0]["stream"] is False


def test_an_out_of_range_window_reaching_the_backend_is_still_bounded() -> None:
    """Defence in depth: the form clamps, the store clamps — and so does the backend, so no
    caller can put an unbounded allocation request on the wire by constructing directly."""
    seen, open_ = _capturing()
    OllamaBackend(model="m", opener=open_, num_ctx=10_000_000).generate("hello")
    assert seen[0]["options"]["num_ctx"] == MAX_NUM_CTX


# --- the bound --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("given", "want"),
    [
        (0, 0),  # off stays off — the one value that sends nothing
        (-1, 0),  # nonsense is off, never a window
        (MIN_NUM_CTX, MIN_NUM_CTX),
        (MIN_NUM_CTX - 1, MIN_NUM_CTX),  # a window too small to hold a fact sheet is raised
        (1, MIN_NUM_CTX),
        (32_768, 32_768),  # Ollama's own 24-48 GiB tier default passes through untouched
        (MAX_NUM_CTX, MAX_NUM_CTX),
        (MAX_NUM_CTX + 1, MAX_NUM_CTX),
        (10**9, MAX_NUM_CTX),
    ],
)
def test_the_window_is_clamped_to_a_sourced_range(given: int, want: int) -> None:
    assert clamp_num_ctx(given) == want


def test_the_ceiling_is_ollamas_own_largest_tier_default() -> None:
    """Not an invented number. 262,144 is what Ollama itself defaults to on a `>= 48 GiB`
    machine (ollama/ollama#14073) — so the tool can never request more than the reference
    implementation would hand the largest tier it recognises."""
    assert MAX_NUM_CTX == 262_144
    assert MIN_NUM_CTX == 2_048


# --- the disclosure stays true after this ships -----------------------------------------------


def test_the_generation_records_the_window_we_asked_for() -> None:
    _, open_ = _capturing()
    backend = OllamaBackend(model="m", opener=open_, num_ctx=16_384)
    backend.generate("hello")
    assert backend.last_stats is not None
    assert backend.last_stats.num_ctx_sent == 16_384


def test_no_window_records_none_not_zero() -> None:
    """`None` means "we asked for nothing", which is a different statement from "we asked for
    0" — the disclosure phrases itself off this distinction."""
    _, open_ = _capturing()
    backend = OllamaBackend(model="m", opener=open_)
    backend.generate("hello")
    assert backend.last_stats is not None and backend.last_stats.num_ctx_sent is None


def test_the_truncation_warning_names_the_window_already_requested() -> None:
    """ADR-0480's remedy sentence sends the operator to raise the window. Once the tool
    itself can set one, telling an operator who already set 8,192 to "raise the window"
    without saying what is in force is the disclosure going stale against its own product."""
    warning = truncation_warning(
        GenerationStats(prompt_chars=60_000, prompt_eval_count=4_096, num_ctx_sent=8_192)
    )
    assert warning is not None
    assert "8,192" in warning


def test_the_truncation_warning_still_names_the_server_side_remedy() -> None:
    """The env var remains the remedy when the tool sent no window of its own — ADR-0480's
    behaviour must survive this change unaltered in the unconfigured case."""
    warning = truncation_warning(GenerationStats(prompt_chars=60_000, prompt_eval_count=4_096))
    assert warning is not None and "OLLAMA_CONTEXT_LENGTH" in warning


# --- the setting survives the quit ------------------------------------------------------------


def test_the_window_round_trips_through_the_settings_file(tmp_path: Any) -> None:
    path = tmp_path / "ai-settings.json"
    save_ai_config(AIConfig(num_ctx=32_768), path)
    assert load_ai_config(path).num_ctx == 32_768


def test_a_hand_edited_settings_file_cannot_smuggle_an_unbounded_window(tmp_path: Any) -> None:
    """Loading is a trust boundary (ADR-0404): the file is operator-editable, so the same
    bound the form applies is re-applied on load — a hand-typed 10,000,000 must not become a
    ten-million-token allocation request at the next launch."""
    path = tmp_path / "ai-settings.json"
    path.write_text(json.dumps({"schema": 1, "num_ctx": 10_000_000}), encoding="utf-8")
    assert load_ai_config(path).num_ctx == MAX_NUM_CTX


def test_a_settings_file_without_the_field_loads_as_off(tmp_path: Any) -> None:
    """Every file written before this unit lacks the key; it must read as OFF, not as a
    window, so an upgrade never silently starts dictating an allocation."""
    path = tmp_path / "ai-settings.json"
    path.write_text(json.dumps({"schema": 1, "model": "m"}), encoding="utf-8")
    assert load_ai_config(path).num_ctx == 0


def test_a_non_integer_in_the_settings_file_loads_as_off(tmp_path: Any) -> None:
    path = tmp_path / "ai-settings.json"
    path.write_text(json.dumps({"schema": 1, "num_ctx": "big"}), encoding="utf-8")
    assert load_ai_config(path).num_ctx == 0
