"""A prompt the model never fully saw must not produce a silent answer (OR-11c).

`OllamaBackend.generate` sends `temperature`/`seed`/`top_p` and **no `num_ctx`**, so every
generation runs at whatever context window the server happens to be configured for. Ollama's
defaults are VRAM-tiered and moved in v0.15.5 (`< 24 GiB` → 4,096 · `24-48 GiB` → 32,768 ·
`>= 48 GiB` → 262,144 — ollama/ollama#14073), and a prompt longer than that window does not come
back as an error: the answer arrives, confident and cited, formed on a fact sheet the model only
partly read. On a 32-version workbook that is exactly the shape of prompt this tool builds.

The fix does NOT guess the window and does NOT raise it — raising it blind is a documented
footgun (the same issue has a 52 GB box going unresponsive when the new default spills to CPU).
It MEASURES: `/api/generate` returns `prompt_eval_count`, the tokens the server actually
evaluated (documented in ollama's api.md), and a count far below what the prompt's own length
can possibly tokenize to is proof the model did not see all of it.
"""

from __future__ import annotations

import json

from schedule_forensics.ai.ollama import (
    MAX_CHARS_PER_TOKEN,
    GenerationStats,
    OllamaBackend,
    truncation_warning,
)


def _opener(body: dict[str, object]):
    def open_(url: str, data: bytes | None, timeout: float) -> str:
        return json.dumps(body)

    return open_


def _backend(body: dict[str, object]) -> OllamaBackend:
    return OllamaBackend(model="m", opener=_opener(body))


# --- the detector -----------------------------------------------------------------------------


def test_a_prompt_far_longer_than_the_tokens_evaluated_warns() -> None:
    """60,000 characters cannot tokenize to 4,096 tokens on ANY tokenizer — the server
    evaluated a fraction of what was sent."""
    warning = truncation_warning(GenerationStats(prompt_chars=60_000, prompt_eval_count=4096))
    assert warning is not None
    assert "4,096" in warning and "60,000" in warning
    assert "OLLAMA_CONTEXT_LENGTH" in warning  # the remedy, named


def test_a_prompt_the_model_fully_read_does_not_warn() -> None:
    """The negative half. 12,000 characters at ~4 chars/token is ~3,000 tokens; a server that
    evaluated 3,000 read all of it. A detector that fires here is noise, and noise gets ignored."""
    assert truncation_warning(GenerationStats(prompt_chars=12_000, prompt_eval_count=3_000)) is None


def test_the_bound_is_conservative_by_construction() -> None:
    """One-sided by design: it fires only when the count is below what the prompt can POSSIBLY
    tokenize to, assuming a generous MAX_CHARS_PER_TOKEN. Right at the boundary it stays silent,
    so a false alarm needs a tokenizer more compressive than any in use."""
    chars = 60_000
    exactly_at_bound = chars // MAX_CHARS_PER_TOKEN
    assert truncation_warning(GenerationStats(chars, exactly_at_bound)) is None
    assert truncation_warning(GenerationStats(chars, exactly_at_bound - 1)) is not None


def test_a_server_that_reports_no_count_is_not_accused() -> None:
    """UNVERIFIED is not the same as truncated. An older server, or an OpenAI-compatible one,
    may not report the count at all — say nothing rather than invent a verdict."""
    assert truncation_warning(GenerationStats(prompt_chars=60_000, prompt_eval_count=None)) is None
    assert truncation_warning(GenerationStats(prompt_chars=0, prompt_eval_count=0)) is None


# --- the backend captures what the server reported ---------------------------------------------


def test_generate_records_the_servers_own_prompt_eval_count() -> None:
    backend = _backend({"response": "ok", "prompt_eval_count": 4096, "done_reason": "stop"})
    assert backend.last_stats is None  # nothing measured before the first generation
    assert backend.generate("x" * 60_000) == "ok"
    stats = backend.last_stats
    assert stats is not None
    assert stats.prompt_eval_count == 4096
    assert stats.prompt_chars == 60_000  # the prompt WE sent, not the server's word for it
    assert truncation_warning(stats) is not None


def test_generate_still_works_against_a_server_that_reports_nothing() -> None:
    """The field is documented but a stripped or proxied server may omit it; a missing count
    must never break an answer that arrived."""
    backend = _backend({"response": "ok"})
    assert backend.generate("hello") == "ok"
    assert backend.last_stats is not None
    assert backend.last_stats.prompt_eval_count is None
    assert truncation_warning(backend.last_stats) is None


def test_a_second_generation_replaces_the_first_measurement() -> None:
    """Stale stats would attach one ask's warning to the next ask's answer."""
    backend = _backend({"response": "ok", "prompt_eval_count": 4096})
    backend.generate("x" * 60_000)
    assert truncation_warning(backend.last_stats) is not None  # type: ignore[arg-type]
    backend._open = _opener({"response": "ok", "prompt_eval_count": 4096})
    backend.generate("short")
    assert truncation_warning(backend.last_stats) is None  # type: ignore[arg-type]
