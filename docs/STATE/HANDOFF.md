# Handoff — 2026-09-08 (d) (OR-11c CLOSED (ADR-0480): an answer the model only PARTLY read now says so — measured from the server's own prompt_eval_count, never guessed; v1.0.250)

STATUS (current) — Branch `claude/polaris-audit-r55-r20-handoff-uoa34g`, restarted on `origin/main` @ `3b2604e` (#656's squash — tree verified byte-identical to head `123ad06`, `a398b96334517824e18d505c35eb1485c2130a96` on both). One unit, engine-untouched, red-first, mutation-tested **10/10**. Highest ADR **0480**. Version **1.0.250** (wheel + nine installers rebuilt AFTER the last source edit; `SF_MPXJ_REF=42d92dc9acc98f7d87f19c82dc62be3e5d3c15ca` still required on this SHALLOW clone — and a `--depth 1` fetch of that sha makes it a NEW graft boundary that fails `test_the_converter_pin_is_a_real_touch_not_a_shallow_graft_artifact`; `git fetch --deepen=25` past it is the remedy). QC-1/QC-2 bind every session — ADR-0393.

## OR-11c — the answer ARRIVES and the model never read all of it

ADR-0478 made a MISSING answer explain itself; this is the harder half. `OllamaBackend.generate` sends `temperature`/`seed`/`top_p` and **no `num_ctx`**, so a generation runs at whatever window the operator's server has. **The UNVERIFIED was resolved against primary sources first**: `/api/generate` (`stream:false`) returns **`prompt_eval_count`** (ollama `docs/api.md`); defaults are **VRAM-tiered and moved in v0.15.5** — `<24 GiB` 4,096 · `24-48 GiB` 32,768 · `>=48 GiB` 262,144 (ollama/ollama#14073); `OLLAMA_CONTEXT_LENGTH` sets the server default. **Still NOT verbatim-confirmed: the exact truncation semantics** — so nothing is built on them.

**The design refuses to guess and refuses to auto-raise.** Raising `num_ctx` blind was rejected on evidence: KV cache scales with the window and #14073 records a 52 GB box going unresponsive on the larger default. Instead: `GenerationStats` (our prompt's char count + the server's `prompt_eval_count` + `done_reason`) captured into `OllamaBackend.last_stats`, replaced every generation; `truncation_warning` fires ONE-SIDED only when the evaluated tokens are below what the prompt could possibly tokenize to at `MAX_CHARS_PER_TOKEN = 6`. **Silence means "no evidence of truncation", never "verified complete"** — the warning may under-fire, the reassurance may not. A server reporting no count is UNKNOWN, not accused. Surfaced as `evidence_warning` on the ask payload (only beside an answer that arrived — a missing one is ADR-0478's `no_answer`) and rendered ABOVE the answer by `ask.js`. `_UseMarking` forwards `last_stats` or the wrapper swallows it in the deployed path.

## Traps this session paid for, by name

* **8 RED / 2 GREEN first, and BOTH greens were findings about the TESTS.** **C8**: the mutation making `_UseMarking` swallow the measurement walked straight through — every endpoint test patched in a BARE `OllamaBackend` and none set `ai_use_hook`, so the DEPLOYED wrapped path was never exercised; the disclosure could have been absent in production with the suite green. Remedy: a test that sets the hook. **C9**: the panel mutation walked through a SOURCE PIN (`"evidence_warning" in js`), which `if (false)` leaves satisfied — a grep cannot see behaviour. Remedy: the node harness now boots `ask.js` and asserts the warning renders AND precedes the answer. 10/10 after.
* **Verify the UNVERIFIED before designing.** The whole unit turned on `prompt_eval_count` existing; that came from ollama's own `docs/api.md`, not memory. The truncation SEMANTICS are still unconfirmed and the design deliberately does not depend on them.
* **The sandbox is not the tree.** 9 failures in the sandbox sweep were `installer/`- and `docs/`-reading tests; the sandbox only carries `src/`, `tests/`, `pyproject.toml`. All three named ones PASS on the real tree. Triage before believing a red.

## Next — campaign queue

**OR-11e (NEW)**: the tool still does not SEND `num_ctx` — an operator-set window is a separate unit and must ship with the VRAM cost stated in the form. **OR-11b**: the 48-fact cap is non-binding at 32 versions today; re-measure on a real 32-file workbook before touching `_MODEL_MAX_FACTS`. **OR-11d**: `_AskRecord` exports an unanswered ask without its reason. Then the audit queue, unchanged: R-56 (add UID 385, seven heads, both `pc == 0`) · R-49 · R-46 · R-47 · R-52 · R-50 · R-57/58/59 · then R-03 · R-04 · R-09 · R-13 · R-18 · R-21 · R-22 · R-32 · R-39. Residuals still registered: the working-minute axis cannot carry a recorded instant on a day boundary or a non-working moment; the hint bubble still widens the document while OPEN. PLUS the design page owed each session — still current: `/scorecards` (`setScreen('sk')`), 21 artboards remaining (report §6).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
