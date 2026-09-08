# Handoff — 2026-09-08 (c) (OR-11a CLOSED (ADR-0479): the driving path to a focus UID is computed for EVERY loaded version — 1 of 32 → 32 of 32 on both Ask surfaces; v1.0.249)

STATUS (current) — Branch `claude/polaris-audit-r55-r20-handoff-uoa34g`, restarted on `origin/main` @ `340b025` (#655's squash, whose tree was verified byte-identical to the head its eight checks passed on). One unit, engine-untouched, proven red-first and mutation-tested **12/12**. Highest ADR **0479**. Version **1.0.249** (wheel + nine installers rebuilt AFTER the last source edit; the `SF_MPXJ_REF=42d92dc9acc98f7d87f19c82dc62be3e5d3c15ca` override is still required on this SHALLOW clone — and note a `git fetch --depth 1` of that sha makes it a NEW graft boundary, which fails `test_the_converter_pin_is_a_real_touch_not_a_shallow_graft_artifact`; `git fetch --deepen=25` past it is the remedy). QC-1/QC-2 bind every session — ADR-0393, pinned by `tests/test_standing_rules.py`.

## OR-11a — the second half of the operator's question, and it was never the model's fault

ADR-0478 made the panel say WHY it had no answer. It did not make the operator's question answerable. **Measured on the pre-fix tree** — 32 versions, the focus UID named in a driving-intent question, the real endpoint: **1** driving-path fact reached the model, citing **1** file (the newest), and `/api/driving-path` with no scope answered for that same one. Thirty-one versions were loaded, parsed and CPM-solved, then not asked. `ask_workbook` called `driving_path_facts(schedules[-1], cpms[-1], text)`; the deterministic button fell through to the same pair.

**Three measurements decided the design.** (1) The engine was never wrong: `compute_driving_slack` reproduces the operator's SSI Directional Path export for UID 152 on the real 2,126-task master IMS **exactly — 76 of 76 members**, against `golden/ssi_uid152/case.json`, so the series inherits SSI parity by construction. (2) One call costs **0.039 s** there, so 32 versions × 2 UIDs ≈ **2.5 s** on top of CPMs already paid for, and only on a driving-intent question naming a UID. (3) The full 32-version sheet is **32 facts** against `model_evidence`'s **48** cap — nothing is dropped today, but 32 MORE facts would have crossed it and started silently evicting the frame. Hence ONE pinned series line, the shape `version_facts.py` already uses.

**Shipped:** `driving_path_series` + `driving_path_series_facts` in `ai/driving_facts.py` — two pinned facts. DRIVING-PATH SERIES: every version, oldest data date first, each with ITS OWN driver count and the focus's own computed finish; a version the focus is absent from says so, a version whose slack could not be computed says *that*, separately, and neither is ever a fabricated 0. DRIVING-PATH MOVEMENT: first-to-last count, finish movement in days, and the step census — how many steps changed WHICH activities drive the focus, and how many of those left its finish on the same date. That last number is the pattern the operator is hunting and it is stated as a **count, never a motive** (the sentence says so). `version_facts._elide` promoted to the shared public `elide_series` rather than copied. **After: 32 of 32 versions on both surfaces, 0.2 s / 0.1 s.** On the REAL `Project2 → Project5` pair it catches UID 35's path collapsing **6 drivers → 0**.

## Traps this session paid for, by name

* **A green mutation is a finding about the TEST — again, and it is the same shape as last session's.** 11 RED / 1 GREEN first: the movement check asserted the sentence's WORDING (`"membership" in text`), which a census hard-wired to zero still produces. Re-aimed at the VALUES (`1 changed WHICH activities drive it`) and paired with a **zero control** — two identical-logic versions must count 0 — so a constant in either direction now fails. 12/12 after.
* **Verify the FIXTURE against the engine before trusting a test built on it.** Before any assertion was believed, the synthetic versions were run through `compute_driving_slack`: v1 `{1,2}`, v2 `{3}` (zero overlap), focus early finish **12,000 minutes in both**. A re-wire with the date held — measured, not asserted.
* **Re-pair CPMs BY IDENTITY after ordering.** `order_versions` reorders; a positional zip after it measures one version's network against another's timings. Silent, wrong, and in a testimony context the worst defect available — so it has its own mutation (N2) and its own test.
* **4 of 7 endpoint tests were green from the first run BY DESIGN** and that is not a weak test: they pin what must NOT change (a scoped request, a single-version session, no-intent questions, an unknown UID). Their mutations (N8, N10) are what prove them.

## Next — campaign queue

**OR-11b is now partly measured and should be finished next**: the 48-fact cap is NON-binding at 32 versions today (32 facts) but this unit moved it closer — re-measure on a real 32-file workbook before touching `_MODEL_MAX_FACTS`. Then **OR-11c** (`OllamaBackend.generate` sends no `num_ctx`; whether current Ollama silently truncates is UNVERIFIED — read its docs, do not assume) and **OR-11d** (`_AskRecord` exports an unanswered ask without its reason). The audit queue is unchanged: R-56 (add UID 385, seven heads, both `pc == 0`) · R-49 · R-46 · R-47 · R-52 · R-50 · R-57 / R-58 / R-59 · then R-03 / R-04 / R-09 / R-13 / R-18 / R-21 / R-22 / R-32 / R-39. Residuals still registered: the working-minute axis cannot carry a recorded instant on a day boundary or a non-working moment; the hint bubble still widens the document while OPEN. PLUS the design page owed each session — still current: `/scorecards` (`setScreen('sk')`), 21 artboards remaining (report §6).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
