# ADR-0478 — Ask-the-AI names WHY there is no answer

Status: accepted (2026-09-08)

## Context

An operator asked the Ask-the-AI panel on `/integrity`, against a 32-version workbook, for a
manipulation analysis of UID 152 plus a per-version driving path. The panel answered:

> No local model is active (or strict mode discarded its answer) — these are the engine's cited
> facts that match your question. For a full written analysis, enable a local Ollama model in AI
> Settings.

Their AI Settings showed a model configured. The sentence is `static/ask.js`'s only `else` branch:
it renders whenever `/api/ask` returns a falsy `answer`, and it names two causes.

## The measurement

`/api/ask` was driven end-to-end against a real loopback fake-Ollama (a `ThreadingHTTPServer` on
127.0.0.1) with 32 synthetic versions of golden Project5 and the operator's verbatim question:

| the world | HTTP | `answer` | any other key naming the cause | what the panel printed |
| --- | ---: | --- | --- | --- |
| healthy server, annotate | 200 | prose | — | the answer |
| server up, model **not installed** (`/api/generate` → 404) | 200 | `null` | **none** | "No local model is active …" |
| server **down** (connection refused) | 200 | `null` | **none** | "No local model is active …" |
| generation **timed out** | 200 | `null` | **none** | "No local model is active …" |
| **empty** completion | 200 | `null` | **none** | "No local model is active …" |
| **strict** discarded the answer | 200 | `null` | **none** | "No local model is active …" |

Five materially different failures, one byte-identical payload: `{"answer": null, "mode": …,
"second_answer": null, "second_model": null, "agreement": null, "facts": [...]}`. The response
carried no field that distinguished them, so one hard-coded sentence had to cover all five.

Two things follow, and the second is the sharper defect:

1. **The sentence leads with the least likely cause.** An operator looking at a configured model
   in AI Settings reads "no local model is active" as false and stops there — the actual cause
   (their Ollama is down, or the selected model was never pulled, or the generation timed out) is
   never named, and none of them is fixed on the page the link points at without knowing which.
2. **In annotate mode the alternative it offers cannot happen.** `qa.answer_question` discards
   only under `mode == "strict"`; `annotate` always returns the text (flagged), and
   `interpretive` / `unrestricted` are ungated by design. `annotate` is the DEFAULT. So the
   panel's second explanation was, for most sessions, a statement the code cannot produce.

The information existed at every one of those returns and was thrown away at the boundary. Worse,
the diagnosis was already **written** — `settings._ai_status_note` reports "could not reach Ollama
at …: connection refused" and "Ollama is reachable but the selected model … isn't installed" — on
a page the operator has to go looking for, and never at the point of failure.

## Decision

**A no-answer carries its reason, composed on the server, rendered by the panel.**

* `ai/qa.py` gains `NoAnswer(code, detail)` and `answer_question_detail(...)` returning
  `(answer, shown, NoAnswer | None)`. Four stable codes — `no_model`, `generation_failed`,
  `empty_answer`, `discarded_unsourced` — the four things the qa layer can actually observe: the
  routed backend's name, the transport exception, an empty completion, the gate's verdict.
  `answer_question` stays exactly as it was, a two-tuple wrapper, so its dozen call sites and
  their tests are untouched.
* `detail` is local diagnostic text, never new schedule content: `probe_error_text(exc)` — the
  same classifier `settings` reports a dead server with, so both pages speak one vocabulary — or,
  for a discard, the figures that tripped the gate (which the panel is already showing beside it
  in the cited facts).
* `web/app.py` gains `_no_answer_note(cfg, why)`, which turns a code plus the OPERATOR'S
  CONFIGURATION into one sentence with the next action in it. That half cannot live in the qa
  layer (it has no config) or in the client (it has neither), which is why the note is composed
  server-side and shipped as `no_answer: {code, text}`.
* A `generation_failed` carrying HTTP 404 on Ollama re-probes `/api/tags` and, when the selected
  model is genuinely absent, names it, lists what IS installed, and prints the `ollama pull`
  command. The availability probe cannot see this — `is_available()` asks `/api/tags`, never
  whether the configured model exists — which is exactly how a reachable server produced "no
  local model is active".
* `static/ask.js` renders `no_answer.text` and degrades to a usable line if the key is absent.
  The retired sentence is gone from the file and pinned gone.

## Consequences

* The panel's answer to the operator's screenshot is now one of: *AI answering is switched OFF…*
  / *could not reach Ollama at http://127.0.0.1:11434: connection refused…* / *the selected model
  'qwen2.5:7b-instruct' is not installed there (installed: …) — run: ollama pull …* / *the model
  TIMED OUT — it did not finish within the 3600s generation timeout…* / *STRICT answer mode
  discarded the model's answer: it contained 1 figure the engine never computed (987654) — set AI
  answer mode to "annotate"…*. Each names what to do; each is the tool's own measurement.
* **The primary answer's call site moved**, from `answer_question` to `answer_question_detail`.
  Two existing tests monkeypatch `app.answer_question` to intercept that call
  (`test_unrestricted_ask_feeds_the_newest_versions_activity_table` captures the unrestricted
  data block; `test_ask_response_skips_agreement_when_an_answer_is_empty` forces an empty answer).
  Both are re-aimed PER CALL SITE, not per name — ADR-0390's rule: the cross-check second model
  still calls `answer_question`, so the second test patches BOTH.
* Law 1 is untouched: no new transport, no new destination, nothing added to a payload that
  leaves the machine (nothing does). The one new outbound call is a `/api/tags` GET to the same
  loopback endpoint the ask already used, on the failure path only.
* Deliberately NOT done: `_AskRecord` (and therefore the Q&A Excel/Word export) still records
  only `answer=None`, so an exported unanswered ask does not carry the reason. Registered.

## What this does not fix

It does not make a model appear. If the cause is "Ollama is not running" the tool still cannot
answer — it now says so in the operator's own configuration terms instead of guessing. And the
diagnosis is only as good as the failure's own signal: an Ollama returning HTTP 404 for a reason
other than a missing model falls through to the generic "the generation itself failed: <reason>",
which is honest rather than confident.

## Evidence

* Red first: `tests/web/test_ask_no_answer_reason.py` (13 tests) and
  `tests/ai/test_qa_no_answer_reason.py` (7) were written against the pristine tree and observed
  to fail — the web file on the absent `no_answer` key, the qa file on the absent API.
* Teeth: a nine-mutation battery on fresh scratch copies (collapse every cause to the no-model
  note; drop the not-installed hint; report a refused generation as no model; restore the blanket
  sentence in `ask.js`; drop the payload key; empty the discard detail; leak "strict" into a
  non-strict note; report a failure on a successful answer; report an empty completion as no
  model) went **RED by name, 9 of 9** — after the first run returned one GREEN. That green was a
  finding about the TEST: the "never blames strict mode" check only ever walked the `ollama`
  branch, so a "strict" leaked into the AI-switched-off sentence passed it. The remedy is
  `test_only_a_strict_discard_ever_mentions_strict_mode`, a census over every cause × every
  backend selection straight at the composer.
* Execution, not inspection, for the panel: `tests/web/js/ask_no_answer_harness.mjs` boots
  `ask.js` against a DOM stub and a stubbed `fetch`, drives the click handler, and asserts the
  SERVER's sentence lands on screen, the retired one does not, and a payload without a reason
  still renders a non-empty line.
