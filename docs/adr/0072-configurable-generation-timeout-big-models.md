# ADR-0072 — Configurable generation timeout so a big, slow local model can finish

Date: 2026-06-18 · Status: accepted

## Context

Operator request: *"I want to use the newest and most powerful version of llama3.1 available, even
if it takes my machine longer to generate results."* The tool already lets the operator select any
installed Ollama model (ADR-0071 dropdown), but each generation was capped at the backend's default
**120 s** `timeout`. A large model (e.g. `llama3.1:70b`) running on CPU on a laptop can take several
minutes to produce a full analysis, so the answer would be **cut off** and the tool would fall back
to the deterministic facts — exactly the "takes longer" case the operator is willing to accept but
the timeout forbade. (Installing the model itself is a manual `ollama pull` on the operator's
machine — the air-gapped tool never fetches over the network; instructions were provided separately.)

## Decision

Make the **generation timeout operator-adjustable** and generous by default.

* `AIConfig.gen_timeout: float = 300.0` (up from the implicit 120 s) — the seconds a single
  `generate`/`pull` may run. Wired into every local-backend construction (`_ollama_or_none`,
  `_openai_or_none`, and the cross-check `_second_backend`) as the backend `timeout`. The short
  **availability probe** (ADR-0070/0071, 8 s) is untouched — only the actual generate work gets the
  long budget.
* `/settings` gains a **"Generation timeout (seconds)"** field; the POST clamps it to a sane
  **30 s … 3600 s (1 h)** window so a big slow model can finish while a wedged one can't hang a
  request forever.

No change to *which* model is used, to the figure/citation gates, or to locality: this only governs
how long a local generation may take.

## Scope / safety

No engine/CPM/metric change → **parity 10/10**. Air-gap unchanged (loopback-only; the longer budget
is for the local model's own compute, nothing leaves the machine — Law 1). Tests: the configured
`gen_timeout` flows to the backend's generate budget, and the settings field persists and clamps to
the 30 s..1 h window. Full gate green; ruff/format/mypy/bandit clean.
