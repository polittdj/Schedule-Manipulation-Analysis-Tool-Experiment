# ADR-0486 — The answer length is the tool's to set, and a cut or empty answer says so: the OpenAI-compatible backends send `max_tokens` (default = the maximum), fall back honestly when a server rejects it, and read the completion as evidence — and OR-14's root cause is corrected: the operator's backend was the approved gateway all along, and the v1.0.254 mislabel is what pointed at LM Studio

- **Status:** Accepted — 2026-09-11 (operator directive, same day: *"I want you to do option 3 and I want you to raise the limit to the max."* — OR-15)
- **Version:** 1.0.256
- **Extends:** ADR-0485 (the local server's token — and the mislabel it fixed), ADR-0480 / ADR-0481 (the input-side truncation disclosure and its lever), ADR-0478 (`/api/ask` says WHY), ADR-0403 (the gateway's credential), ADR-0315 (the use-marking wrapper), ADR-0393 (QC-1 / QC-2)
- **Shipped:** `ai/completion.py` (NEW — `MIN/MAX/DEFAULT_ANSWER_TOKENS`, `clamp_answer_tokens`, `CompletionStats`, `limit_rejected`, `read_completion`, `answer_cut_warning`, `empty_answer_detail`), `ai/backend.py` (`AIConfig.answer_max_tokens`), `ai/openai_compat.py` + `ai/gateway.py` (`max_tokens=` sent; one retry without it on a 400 that names it; `last_completion`), `ai/factory.py` (threaded to primary, cross-check and gateway), `ai/config_store.py` (persisted; a missing key reads as the maximum), `ai/qa.py` (the empty answer carries its evidence), `web/settings.py` (the **Answer length limit** field; `_UseMarking.last_completion`), `web/app.py` (the POST; `_evidence_warning` reads the output side; `_no_answer_note`'s measured empty-answer sentence; `_generation_failed_note`'s gateway-403-with-a-valid-key sentence), `tests/ai/test_answer_length.py` (21, NEW — 28 cases with the clamp's parametrization), `tests/web/test_answer_length_settings.py` (10, NEW)

## Context

**Three asks in a row, in the operator's own words and screenshots.** After ADR-0485 shipped, the
operator asked the Ask panel a float-loss question three times. The first two answers were long,
well-formed forensic prose that **stopped mid-sentence** (*"…an SPI of"*; *"…A schedule genuinely 62
workdays behind"*). The third — one sentence longer, naming UID 152 — produced:

> The local model ran but returned no text, so there was nothing to show - nothing was discarded.
> Ask again, or select a different model in AI Settings.

Then the AI Settings screenshot: **Backend = Approved AI gateway (`https://proxy.fast.luna.nasa.gov`),
Model = `claude-opus-4.8-thinking-itar`, key saved, AI answer mode = Unrestricted, cross-check off.**
And the operator's PowerShell, against `http://127.0.0.1:1234`: *"Unable to connect to the remote
server"* — **nothing listens on port 1234 on that machine.**

**The correction, stated plainly.** ADR-0485 read the morning's note — *"the model server at
http://127.0.0.1:1234 was reachable, but the generation itself failed: server returned HTTP 403"* —
as LM Studio. It was not. The v1.0.254 note printed `cfg.openai_endpoint` for **every** non-Ollama
backend, the gateway included (the mislabel ADR-0485 itself found and fixed, `app.py`'s
`endpoint = cfg.endpoint if is_ollama else cfg.openai_endpoint`). The operator's 403 came from the
**approved gateway**, on the chat completion, after the catalog probe passed (so the key is valid).
ADR-0485's LM Studio token stands as a real capability gap closed for anyone who runs LM Studio — it
was not this operator's fix. Why the gateway refused that morning and later did not is **not
established**; the AI transaction log (`ai-transactions.jsonl`, which stores a SHA-256 and a byte
count per prompt, never the prompt) records every refusal with its size and is the evidence
requested from the operator (§ Residuals). QC-2's lesson is recorded in LESSONS-LEARNED: the fixed
bug was evidence against the working hypothesis, and the session did not re-read the diagnosis in
its light.

**What the tool could not see — measured on the code before the fix.** Neither OpenAI-compatible
backend sent `max_tokens`, so the server's own default output budget governed every answer; a
*thinking* model spends part of that budget reasoning before it writes. Neither read
`finish_reason`, so a `length` stop rendered as a complete answer with no caveat. Neither read the
reasoning fields (`reasoning_content` / `reasoning`), so "no answer text" could not be told apart
from "no answer at all" — and the panel's only sentence for it named the one thing it could see
("select a different model") rather than the cause. And `str(content)` turned a `null` content
into the four-letter answer **"None"**, which then passed every figure gate as prose. Two
hypotheses were refuted first: the tool's own generation timeout (it reports a timeout by name;
none was reported) and a truncated paste (twice, the same shape, then an empty third).

## Decisions

1. **A bounded answer-length setting, sent as `max_tokens` on every generation** to an
   OpenAI-compatible server or the approved gateway. `clamp_answer_tokens` bounds it to
   `[256, 131,072]` at every boundary it crosses (the form, the settings file, both constructors);
   `0` sends nothing and leaves the server's default in charge, exactly as before.
2. **The default IS the maximum** (`DEFAULT_ANSWER_TOKENS = MAX_ANSWER_TOKENS`) — the operator's
   directive. This deliberately differs from ADR-0481's window, which defaults to OFF: raising
   `num_ctx` allocates KV-cache memory and can take a machine down; a large `max_tokens` allocates
   nothing, and a value a server will not accept is rejected out loud (HTTP 400) and falls back
   with a disclosure. A settings file written before this ADR reads as the maximum too, for the
   same reason.
3. **No universal "max" exists, so the fallback is the max.** Every model and server has its own
   output ceiling (UNVERIFIED for the operator's gateway model), and a hard-coded number above it
   would turn every answer into an HTTP 400. `limit_rejected` recognises a **400 whose body names
   the parameter** (`max_tokens` or `max_completion_tokens`); the backend then sends the same
   request **once more without it** and records `limit_rejected=True`. A 403, a 500, a bodiless
   400, or a 400 about anything else propagates unchanged (a refusal is not a rejection). On the
   gateway the retry is a second transmission and is logged as one (`generate.sent` /
   `generate.done ok=false` / `generate.sent` / `generate.done ok=true`).
4. **The completion is read as evidence** (`read_completion` → `CompletionStats`): `finish_reason`,
   the answer's length, the reasoning's length when a server exposes it, `usage.completion_tokens`
   when reported, the budget sent, and whether it was rejected. A `null` or absent `content` is
   `""`, never `"None"`. Both backends keep it as `last_completion`; `_UseMarking` forwards it like
   `last_stats` (see § Verification for what the battery said about that).
5. **A cut answer is disclosed beside it**, through the OR-11c channel: `_evidence_warning` reads
   the OUTPUT side when the backend has one — *"The answer was CUT at the output limit
   (finish_reason=length, N tokens generated): this tool asked for up to 131,072 tokens and the
   server stopped there — a thinking model spends part of that budget reasoning before it writes.
   Raise the Answer length limit in AI Settings if it is below the maximum, switch AI answer mode
   to Annotate (a much smaller prompt), or ask a narrower question."* When the server rejected the
   budget the sentence says so and tells the operator to LOWER the setting; when no limit was sent
   (0) it says the server's default cut it.
6. **An empty answer says why**, when the server measured it: `qa.answer_question_detail` attaches
   `empty_answer_detail(last_completion)` and the panel reads *"The model ran but produced no answer
   text: it stopped at the output limit (finish_reason=length) after 6,000 characters of reasoning
   and no answer text. Raise the Answer length limit … switch AI answer mode to Annotate … or
   choose a non-thinking model."* With nothing measured, the old sentence stands.
7. **The gateway's 403 with a VALID key gets its own words** (`_generation_failed_note`): the
   catalog served, so "paste your key" is the wrong advice — *"accepted your key for its model
   catalog but refused this generation (server returned HTTP 403). Common causes: the selected model
   '…' is not authorized for your key, or a gateway policy refused the request — an over-large
   prompt is a frequent one (Unrestricted answer mode sends the full per-activity table; try
   Annotate). The AI transaction log at … records each refusal with the prompt's size."* Keyless,
   the ADR-0403 sentence stands.
8. **Refused, named:** a hard-coded "maximum" (decision 3); sending `max_completion_tokens` as well
   (a second undocumented parameter on every request — a residual, below); touching Ollama's
   `num_predict` (Ollama's documented default is unlimited generation — UNVERIFIED on the operator's
   build; its `done_reason` is already captured in `GenerationStats` for a future output-side
   disclosure there).

**Shipped code changed → v1.0.255 → v1.0.256**, wheel + nine installers rebuilt
(`SF_MPXJ_REF=42d92dc9acc98f7d87f19c82dc62be3e5d3c15ca`; the clone is unshallowed).

## Verification (QC-1)

*Red first:* the two new test modules ran on the pristine tree before any source edit — **2 errors
during collection**: `schedule_forensics.ai.completion` does not exist, so every test in both files
is red by construction. That red is coarse (it refutes "the module exists", not each behaviour), so
the per-behaviour refutations are the battery's job, below.

*Green:* the two new modules **38 passed**; the touched neighbourhood (17 files — both backends,
the gateway, the config store, the window control, the input-side evidence warning, the no-answer
census, the token unit, the gateway settings, the coverage pins, txlog, the allowlist and banner
guards) **306 passed**. Full suite after the bump and the rebuild: **5,275 passed / 5 skipped / 1 failed in 36:19 — the one red is `test_driving_path_whole_schedule_browser.py:104`, the #667 width race (registered, outside this diff: no driving/path/chrome/static file is touched), green on an immediate re-run alone**; `-m parity`
**96 passed**. Both ruff binaries (0.16.7 = CI's, 0.15.8 on PATH), mypy strict (164 files), bandit,
`node --check`, 5,281 collected: clean.

*Teeth:* a **30-mutant** battery on a SCRATCH copy of the package under a PYTHONPATH shadow (the
instrument never mutated), each mutant counted only when the run is red AND the named test is among
the failures — **30/30 caught by name**: `openai_limit_not_sent` · `gateway_limit_not_sent` ·
`openai_zero_still_sent` · `openai_no_retry` · `openai_retry_keeps_the_limit` ·
`openai_retry_on_any_400` · `openai_rejection_not_recorded` · `null_content_regression` ·
`reasoning_not_counted` · `finish_reason_not_read` · `cut_warning_silent` ·
`cut_warning_loses_the_setting_name` · `evidence_warning_ignores_completion` ·
`empty_detail_dropped` · `empty_note_ignores_detail` · `clamp_floor_off` · `clamp_ceiling_off` ·
`store_drops_the_key` · `store_missing_reads_zero` · `post_not_clamped` · `form_field_missing` ·
`factory_primary_drops` · `factory_gateway_drops` · `factory_second_drops` ·
`wrapper_swallows_completion` · `gateway_403_with_key_regresses` ·
`gateway_note_loses_the_prompt_size_lever` · `limit_rejected_ignores_status` · `default_not_max` ·
`gateway_retry_keeps_the_limit`.

*What the battery found in the instrument (the reason batteries are read, not counted):* on its
first run `wrapper_swallows_completion` came back **RED(other)** — the wrapper's own unit test
caught it, but the end-to-end cut test, whose docstring claimed to exercise "the deployed wrapping
(ADR-0315)", stayed GREEN with the wrapper's forwarding switched off. Measured cause: the deployed
app wraps **only a routed Ollama** (`_active_backend`: `backend.name == "ollama"`;
`_second_backend`: `cfg.second_backend == "ollama"`), so an OpenAI-compatible backend never passes
through `_UseMarking` and the e2e was measuring the bare backend. The claim was corrected in the
test and in the property's docstring; the property stays, pinned on the wrapper itself, for the day
the wrapping is extended. Second run **30/30**.

## Consequences

- The operator's next answers on the gateway carry `max_tokens: 131072`. If the gateway rejects
  that value, the answer still arrives (from the retry) and the panel says the server's default cut
  it and to LOWER the setting — the field evidence that settles the gateway model's real ceiling.
  If it accepts, cut answers should stop; if the thinking model still spends the whole budget
  reasoning, the panel now says exactly that and offers the smaller-prompt remedy (Annotate mode).
- **OR-14 is corrected in the ledger:** the operator's backend is the approved gateway; port 1234
  has no listener (measured by the operator); the LM Studio token (ADR-0485) is a real gap closed
  for LM Studio users and was not this operator's fix; the morning's 403 is the GATEWAY's and its
  cause is pending the transaction log.
- **UNVERIFIED, stated:** the true output ceiling of `claude-opus-4.8-thinking-itar` through the
  NASA gateway (the fallback is designed so the tool does not need to know it); whether that
  gateway exposes reasoning in `reasoning_content` / `reasoning` at all (if it strips reasoning
  entirely, the empty-answer sentence degrades to the `finish_reason=length` form, which is still
  measured); whether any server the tool meets demands `max_completion_tokens` instead of
  `max_tokens` (it would be a 400 naming it → the retry-without → the server's default, disclosed).
- **Residuals, not taken:** `max_completion_tokens` as a second attempt before falling back to no
  limit; an output-side disclosure for Ollama from `GenerationStats.done_reason`; the cross-check
  second model's `last_completion` is recorded but not surfaced (only the primary's evidence
  reaches the panel — as with `last_stats`).
- Review cover is still absent (Codex quota exhausted through #669); this unit's review is the
  battery and the gate.
