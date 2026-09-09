# ADR-0480 — An answer the model only partly read says so (OR-11c)

Status: accepted (2026-09-08)

## Context

ADR-0478 made a **missing** answer explain itself. This is the harder half: the answer **arrives**
— fluent, cited, confident — and the model never read all of the evidence, because the prompt
exceeded the Ollama context window and Ollama drops the overflow instead of erroring.

`OllamaBackend.generate` sends `temperature` / `seed` / `top_p` and **no `num_ctx`**, so every
generation runs at whatever window the operator's server happens to be configured for. Recorded as
**OR-11c**, explicitly **UNVERIFIED**. Resolved against primary sources before any design:

* `POST /api/generate` with `stream:false` returns **`prompt_eval_count`** — the prompt tokens the
  server actually evaluated (ollama `docs/api.md`).
* Ollama's default context length is **VRAM-tiered and moved in v0.15.5**: `< 24 GiB` → 4,096;
  `24–48 GiB` → 32,768; `>= 48 GiB` → 262,144 (ollama/ollama#14073).
* `OLLAMA_CONTEXT_LENGTH` sets the server default; `num_ctx` sets it per request. The settings
  page already REPORTS the env var (ADR-0315) and has never applied one.
* **Still not verbatim-confirmed:** the exact truncation semantics (which end is dropped, whether
  anything is logged). So nothing here is built on them.

On a 32-version workbook this tool routinely builds a prompt of tens of thousands of characters.
Under a 4,096-token window that is a partial fact sheet, and every downstream gate stays green:
the citation gate checks that figures came from the facts, not that the model SAW all the facts.

## Decision

**Measure it; never guess the window, and never raise it silently.**

Raising `num_ctx` automatically was rejected on the evidence: KV-cache cost scales with the
window, and ollama/ollama#14073 records a 52 GB machine going unresponsive — spilling to CPU — on
the new larger default. A forensic tool must not trade the operator's machine for a longer prompt
without them asking.

* `ai/ollama.py` gains `GenerationStats` (the prompt's own character count, the server's
  `prompt_eval_count`, `done_reason`) captured by `generate` into `OllamaBackend.last_stats`,
  replaced on every generation so a stale measurement can never ride a later answer.
* `truncation_warning(stats)` is a **one-sided** test: it fires only when the tokens the server
  says it evaluated are fewer than the prompt could possibly tokenize to at
  `MAX_CHARS_PER_TOKEN = 6` — deliberately generous, since real tokenizers average ~4 characters
  per token and our fact sheets (dates, UIDs, decimals) tokenize harder than prose. **Silence
  means "no evidence of truncation", never "verified complete"**: the warning direction may
  under-fire, the reassurance may not — the same asymmetry the locality banner uses.
* A server that reports no count is **UNKNOWN, not accused**.
* `web/app.py` adds `evidence_warning` to the ask payload (only alongside an answer that
  arrived — a missing answer is already explained by ADR-0478's `no_answer`, and two
  disclosures for one state would contradict each other). `ask.js` renders it **above** the
  answer: a caveat printed under a confident paragraph is a caveat nobody reads.
* `web/settings.py::_UseMarking` forwards `last_stats`. Without that passthrough the wrapper —
  which wraps every routed Ollama in the deployed app — swallows the measurement.

## Consequences

* An answer built on a truncated prompt now carries, next to itself, the two numbers that prove
  it (tokens evaluated vs prompt characters) and the remedy (`OLLAMA_CONTEXT_LENGTH`, whose
  current value AI Settings already shows).
* No new request field, no new endpoint, no behaviour change to any generation: the same bytes
  are sent as before. Law 1 untouched.
* **Not done:** the tool still does not SEND `num_ctx`. Adding an operator-set window is a
  separate unit and a separate risk (the VRAM footgun above); it should ship with the memory
  cost stated in the form. Registered as OR-11e.

## Evidence

* **Red first.** 13 new tests (7 unit + 6 endpoint) written against the pristine tree and observed
  to fail — the unit file on the absent API, every endpoint test on the absent payload key.
* **Teeth: 10 of 10 mutations RED by name** — the detector never firing / always firing; a missing
  count treated as truncation; `generate` not recording the count; stats never replaced (stale);
  `prompt_chars` taken from the server instead of our own prompt; the payload dropping the field;
  the `_UseMarking` wrapper swallowing it; the panel not rendering it; the bound loosened until it
  cannot fire.
* **The first battery returned 8 RED / 2 GREEN, and both greens were findings about the TESTS.**
  **C8** — the wrapper mutation walked straight through, because every endpoint test patched in a
  BARE `OllamaBackend` and no test set `ai_use_hook`, so the deployed wrapped path was never
  exercised: the disclosure could have been absent in production with the suite green. Remedy:
  `test_the_use_marking_wrapper_does_not_swallow_the_warning`, which sets the hook. **C9** — the
  panel mutation walked through a **source pin** (`"evidence_warning" in js`), which `if (false)`
  leaves satisfied. Remedy: the node harness now boots `ask.js` and asserts the warning renders
  AND precedes the answer. 10/10 after.
