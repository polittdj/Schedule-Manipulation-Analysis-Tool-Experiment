# Handoff — 2026-09-11 (d) (OR-15 CLOSED (ADR-0486): the answer length is the tool's to set — `max_tokens` at the maximum with an honest fallback, a cut answer disclosed, an empty answer explained; OR-14 CORRECTED — the operator's backend was the approved gateway all along; v1.0.256)

STATUS (current) — `main` @ **`2ae8d06b`** (#669, ADR-0485 / v1.0.255 — tree-verified against the PR head `a97c5bee`; `main`'s own runs **CI 1843 / installer-smoke 706 both success**). **This session's third unit re-diagnosed its second.** The operator's AI Settings screenshot shows **Backend = Approved AI gateway** (`proxy.fast.luna.nasa.gov`, `claude-opus-4.8-thinking-itar`, key saved, Unrestricted mode) and their PowerShell proves **nothing listens on `127.0.0.1:1234`** — the morning's "model server at http://127.0.0.1:1234 … HTTP 403" was the v1.0.254 mislabel (the OpenAI endpoint printed for EVERY non-Ollama backend — the bug ADR-0485 fixed without re-reading its own diagnosis). **The 403 was the gateway's; ADR-0485's LM Studio token is a real gap closed for LM Studio users and was not this operator's fix; the gateway 403's cause is PENDING the operator's transaction-log tail** (no schedule content in it — a SHA-256 and a byte count per prompt). Then three asks: two answers cut mid-sentence, one empty (*"select a different model"*). **ADR-0486, v1.0.256 (OR-15 — "do option 3 and raise the limit to the max"):** `ai/completion.py`; **Answer length limit** in AI Settings, bounded 256–131,072, **default = max**, 0 = server default, sent as `max_tokens` by `openai_compat` and `gateway`; a 400 that NAMES the parameter → one retry without it, recorded; `finish_reason`, answer/reasoning lengths and `usage` read as evidence (`last_completion`); a `length` stop disclosed beside the answer through the OR-11c channel; an empty answer explained ("spent its budget thinking", with the reasoning length) and given the Annotate remedy; `null` content is empty, never "None"; a gateway 403 WITH a valid key names entitlement + prompt size + the transaction log. Red-first (both new modules fail collection on the pristine tree — the module does not exist), **30 mutants / 30 red by name** after the battery found one FALSE claim in the instrument (the e2e's "deployed wrapping" — the app wraps only Ollama, ADR-0315; corrected), new modules 38 passed, neighbourhood 306 passed, full suite **5,275 passed / 5 skipped / 1 failed in 36:19 — the one red is `test_driving_path_whole_schedule_browser.py:104`, the #667 width race (registered, outside this diff: no driving/path/chrome/static file is touched), green on an immediate re-run alone**, `-m parity` **96 passed**. Draft PR: from this branch (`claude/optimistic-ride-3qv2jc`; the SESSION-LOG follow-up records the number and the eight verdicts). Highest ADR **0486**. QC-1/QC-2 bind every session — ADR-0393.

**CARRIED FORWARD, still live and NOT this unit's:** `test_driving_path_whole_schedule_browser.py:104` is **width-racy** (registered by #667; a race with a mechanism, not a flake; its own unit, never fixed by widening a wait).

## What landed, in one paragraph

`completion.py` (`MIN/MAX/DEFAULT_ANSWER_TOKENS` 256 / 131,072 / = max · `clamp_answer_tokens` · `CompletionStats` · `limit_rejected` — a 400 whose body names `max_tokens`/`max_completion_tokens`, nothing else · `read_completion` · `answer_cut_warning` · `empty_answer_detail`) · `AIConfig.answer_max_tokens` · both OpenAI-compatible backends send it, retry once without it on rejection, keep `last_completion` · `factory` threads it to primary / cross-check / gateway · `config_store` persists it (a MISSING key reads as the maximum — unlike `num_ctx`, no memory rides on it) · the form field + POST clamp · `_UseMarking.last_completion` · `_evidence_warning` reads the output side · `_no_answer_note`'s measured empty sentence · `_generation_failed_note`'s gateway-403-with-a-valid-key sentence. Refused and named: a hard-coded "max" (no universal ceiling exists; the fallback IS the max), a second `max_completion_tokens` attempt (residual), touching Ollama's `num_predict`.

## UNVERIFIED, stated — what the operator's machine will settle

- The real output ceiling of `claude-opus-4.8-thinking-itar` through the NASA gateway — the first ask on v1.0.256 settles it: an answer plus *"the server REJECTED that setting"* means the gateway's ceiling is below 131,072 (lower the field); a clean answer means it accepted.
- Whether that gateway exposes reasoning (`reasoning_content` / `reasoning`) — if it strips it, the empty-answer sentence degrades to the `finish_reason=length` form, still measured.
- **Why the gateway 403'd this morning** — the operator's `Get-Content … ai-transactions.jsonl -Tail 40`: if the refused lines carry larger `prompt_bytes` than the answered ones, the gateway refuses oversized requests (Unrestricted mode ships the per-activity table); if equal, it was the gateway's own.

## Traps this session paid for, by name

* **A fixed bug is evidence against the hypothesis it lived under.** ADR-0485 found that the note printed the OpenAI endpoint for every non-Ollama backend, fixed it, and still shipped a diagnosis that TRUSTED that endpoint. Re-read the working hypothesis the moment a mislabel is found in the instrument that produced it.
* **A diagnostic's mislabel misdirects the next diagnostician, not just the operator** — the cost of the v1.0.254 line was a full unit built for the wrong backend. Every note names its own backend now (ADR-0485's fix) — and the ledger records the correction rather than hiding it.
* **"Raise the limit to the max" has no number** — every model has its own ceiling; the design is the bounded default plus a disclosed fallback when a server rejects it, never a constant that turns every answer into a 400.
* **The battery found a FALSE claim in the instrument, not a weak one:** the e2e said it exercised "the deployed wrapping" and stayed green with the wrapper's forwarding removed — because the app wraps only Ollama (ADR-0315). The test now says so; the wrapper's own unit test pins the forwarding.
* **A `null` in a completion is not a string** — `str(content)` shipped the word "None" as an answer for as long as the backend existed. Read a completion as evidence, never coerce it.
* `/root/.local/bin/ruff` 0.15.8 still shadows CI's 0.16.7 on PATH — run both; `git log -1 -- tools/mpxj` reads `42d92dc9` on the unshallowed clone.

## Next — campaign queue

**Read `git log origin/main` before trusting any sha written here.**

**First: the operator's evidence** — the transaction-log tail decides whether the gateway 403 is a prompt-size policy (then Unrestricted mode needs a size guard, its own unit) or the gateway's own. Then **R-56** (add UID 385, seven heads, both `pc == 0`) · R-49 · R-46 · R-47 · R-52 · R-50 · R-57/58/59 · then R-03 · R-04 · R-09 · R-13 · R-18 · R-21 · R-22 · R-32 · R-39. Other residuals: ADR-0486's own (`max_completion_tokens` as a second attempt; an output-side disclosure for Ollama from `done_reason`; the cross-check's `last_completion` recorded but not surfaced) · ADR-0485's (`_gateway_status_note` still detects a refusal by substring; the model dropdown probes with the SAVED token) · ADR-0483's (a live-peer response is cut at 5 s) · `/settings` horizontal overflow · OR-11b (the 48-fact cap — the model could not name the one activity that went critical) · OR-11d · the working-minute axis · the hint bubble · ADR-0484's in-grid rows. **The design page: 10 done, 20 artboards remain; `/margin` (`setScreen('mg')`) next by cost.**

**Review cover is still absent** — Codex quota EXHAUSTED through #669; the mutation battery and the full gate are all this repo gets.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
