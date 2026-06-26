# Handoff — 2026-06-26 (Derived metrics Layer A, ADR-0133; highest ADR 0133)

> ## STATUS (current) — Derived metrics Layer A shipped (ADR-0133); Layer B scoped/deferred
>
> **READ FIRST:** `docs/PLAN/AI-DERIVED-METRICS-SCOPE.md` (the signed-off two-layer design). The
> operator chose **Layer A first** (A: % of population + B: DCMA checks passed n/14). This branch
> `claude/ai-derived-metrics-layer-a` implements it:
> - `engine/metrics/derived.py` — `population_share(count, population)` + `dcma_pass_rate(passed,
>   failed)`, pure 1-dp functions of the primary metrics (verification-contract rounding).
> - `ai/qa.build_fact_sheet` appends two **cited derived facts** (DCMA 14-point pass rate; finish-driving
>   share) — engine-computed, so usable in every Q&A mode incl. strict (no `[AI-derived]` flag).
> - `web/help.py` documents both (formula + source); dictionary regenerated. Golden test pins
>   `derived == hand-computed`; **no parity number moved.**
>
> **REMAINING — Layer B (deferred, operator to evaluate-then-go):** the Q&A *verified-derivation gate*
> (recompute the model's ad-hoc derivations over a closed operation whitelist; relabel verified vs
> unverified) — scoped in `AI-DERIVED-METRICS-SCOPE.md` §5. Artifact-gated audit items remain in
> `audit/PARK-LIST.md`. **Workflow:** `git fetch origin` before branching/rebasing. **Highest ADR =
> 0133.** Run the full gate + `pytest -m parity` before each commit.

> ## STATUS (prev) — Audit cluster CLOSED in-env — batch 2, ADR-0132; highest ADR 0132

> ## STATUS (current) — Audit cluster fully remediated in-env (ADR-0131 + ADR-0132); only artifact-gated items remain
>
> **READ FIRST:** `audit/VERIFICATION-REPORT.md` + `audit/PARK-LIST.md`. The re-audit's full finding set
> from BOTH prior trails — plus the re-audit's own NEW-1 — is now closed in-environment across two batches.
> ADR-0131 (batch 1, #272) closed C1 (CRITICAL) + H1/H3/H4/M2-M8/L2/L7 + NEW-1. **ADR-0132 (batch 2, this
> branch `claude/audit-cluster-remediation-batch2`) closes the rest:**
> - **H2** — the narrative gate now rejects a rephrase that *introduces* an accusatory/intent term the
>   engine never asserted (`ai.citations.introduces_loaded_terms`); legitimate derivation/polish is intact.
> - **M5** — client & server round per-task remaining-days at the same precision (`_REMAIN_DAYS_DP=6`), so
>   the days↔% derive matches for sub-day tasks.
> - **M7** — `pathFilter` debounced (~140 ms) + `freezeColumns` skips redundant style writes (no grid jank).
> - **L3** — `web/offload` registers pool teardown with `atexit` (worker reaped on any exit).
>
> **AI direction (operator):** use the engine's computed metrics fully and derive further metrics from them
> when helpful — but only by industry-standard methods, verified for accuracy. H2 enforces that bar (no
> unverified accusation), without restricting legitimate derivation.
>
> **REMAINING — artifact-gated ONLY** (need operator files; see `audit/PARK-LIST.md`): the Acumen Fuse
> §A/§B/§C/§E export of the current P2/P5 pair, the `NASA_Metrics_Complete_*.aft` Bible, the native `.mpp`
> data, and SSI's focus UID for `Large_Test_File.mpp`. **F-11** (interpretive-mode role re-labeling) stays an
> accepted, documented design choice. **Workflow:** always `git fetch origin` before branching/rebasing
> (CLAUDE.md). **Highest ADR = 0132.** Run the full gate + `pytest -m parity` before each commit.

> ## STATUS (prev) — Orphaned internal-audit cluster + NEW-1 remediated (ADR-0131); batch-2/artifact-gated items remain
>
> **READ FIRST:** `audit/VERIFICATION-REPORT.md` (the unified ledger of BOTH prior audit trails,
> re-derived by re-executing code/tests) + `audit/PARK-LIST.md`. The re-audit (PR #271, merged) found the
> two trails were never merged: ADR-0130 closed the F-set, ADR-0128/0129 closed M1/C2, but the internal
> audit's own Wave plan — **C1 (CRITICAL), H1, H3, H4, M2–M8, L2/L3/L5/L7** — was orphaned and left OPEN,
> and the prior "only artifact-gated items remain" status was false. It also found **NEW-1** (a Float-Ratio
> day-axis mismatch) that neither trail had.
>
> **DONE this batch (ADR-0131, branch `claude/audit-cluster-remediation-batch1`, full gate + parity green,
> no parity number moved):**
> - **C1 (CRITICAL)** — `to_json_text` now round-trips EVERY model field (stored float/critical, is_active,
>   custom_fields, calendar working_days/day_segments, …); `test_save_json_round_trips_every_fidelity_field`
>   diffs the full set so any future schema add that isn't wired into JSON I/O fails loudly.
> - **H1** SSI load non-list `affected` guarded (no 500 / no half-mutation); **H3/H4** one malformed XER id
>   is dropped-and-counted, not fatal; **M3** friendly JSON raises on missing `project_start`; **M4** UID-0
>   baseline-finish leak closed; **M2** pre-commit + `.gitignore` block `.aft`/`.docx` (+ a blocklist test);
>   **M6** sign-aware figure gate; **NEW-1** Float Ratio single-axis; **L2/L7/M8** non-finite `_to_float`
>   guard, tolerant cosmetic OutlineLevel, MEI >1.0 help note (dictionary regenerated).
>
> **REMAINING — batch 2 (in-env, flagged in ADR-0131):** M5 (days↔% client/server rounding — JS+server),
> M7 (path-filter debounce — JS perf), L3 (offload atexit hook), H2 (prose-tamper denylist — operator
> design decision). F-11 stays an accepted documented choice. **Artifact-gated** items (Fuse/SSI/.aft/.mpp)
> are consolidated in `audit/PARK-LIST.md`. **Workflow:** always `git fetch origin` before branching/
> rebasing (CLAUDE.md). **Highest ADR = 0131.** Run the full gate + `pytest -m parity` before each commit.

> ## STATUS (prev, SUPERSEDED) — Audit in-env remediation batch DONE (ADR-0130); only artifact-gated items remain (the F-set batch WAS done, but the internal-audit cluster above was still open)
>
> **READ FIRST:** `audit/AUDIT-REPORT.md` + `audit/PATH-FORWARD.md` (on `main`, #268). The operator asked to
> "execute everything that doesn't require me to submit anything"; this batch did exactly the in-environment
> PATH-FORWARD items. Full gate + parity green (no parity number moved).
>
> **DONE this batch (ADR-0130):**
> - **F-03/F-07/F-01 docs** — `PARITY-REPORT.md` refreshed to authoritative `case.json` (P5 Critical 4, High
>   Float 44/44, BSC 41/25, Net Impact −148, SSI focus 145); §E float/critical subset **labeled
>   engine-pinned / NOT Fuse-validated**; new `tests/test_parity_report_sync.py` pins report↔case.json;
>   risks.md R-02 + ADR-0045 errata.
> - **F-02 finish gap** — new **"As-scheduled (stored dates)"** forecast method surfaces the source-tool
>   finish next to the pure-logic CPM finish (TP4 v5: 07-17 vs 06-26); `test_data_date_finish_gap.py` guards
>   it; TEST-PROJECTS.md overclaim fixed. (No engine reschedule — ADR-0108.)
> - **F-05 detectors** — new `MANIP_CONSTRAINT_ADDED` (clamping hard constraint, ≤0 float) + `MANIP_CALENDAR_LOOSENED`;
>   the constraint one correctly surfaces the real UID-131 ASAP→MSO clamp in `Project5_TAMPERED`.
> - **F-06 XSS** — surgical `_e(title)` at the layout boundary + `test_title_escaping.py`.
> - **F-04 / F-08 / F-12** — float-view "critical" labeled (not unified); `pyproject fail_under` 99.9→70.0;
>   qa.py module docstring → three-mode/annotate-default.
>
> **REMAINING — genuinely artifact-gated (need the operator to supply files; see PATH-FORWARD.md §D):** true
> Fuse numeric re-validation of §E (needs a fresh Acumen Fuse §E export of the current P5-vs-P2 pair), the
> literal `.aft` formula match (needs the `NASA_Metrics_Complete_*.aft` Bible), the native `.mpp` **data**
> (`Project2`/`Project5`/`Large_Test_File.mpp` — git-ignored CUI), the Large-File absolute SSI values (needs
> SSI's recorded focus UID). **Two items the audit had listed here were corrected on 2026-06-26 (re-sweep
> after "do you already have these files?"):** (a) **cost-EVM parity is NOT artifact-gated** — `golden/evm/
> EVM1|EVM2.mspdi.xml` are committed cost-loaded **Acumen-Fuse** references and `test_evm_acumen_reference.py`
> (6 pass) already validates BCWS/BCWP/DCMA/BEI against them; only the SPI(t)/finish/NFI residuals are open,
> and those are the ADR-0108 data-date gap (engine work), not a missing export; (b) the **`.mpp`→MSPDI
> toolchain is present** — Java 17 + vendored MPXJ (`tools/mpxj/`) are installed and runnable here, so the
> `.mpp` round-trip is blocked only on the absent `.mpp` data, not the toolchain. The audit/PATH-FORWARD
> errata blocks record both. **Highest ADR = 0130.** Keep running the full gate + `pytest -m parity` before
> each commit.

> ## STATUS (prev) — Fix session: M1 (inactive-task exclusion) + C2 (operator AI figure mode) DONE; rest of the plan remains
>
> **READ FIRST:** `docs/STATE/AUDIT-2026-06-25.md` (on `main`) — the audit + the 3-wave plan of action.
> This session executed the two operator-decision items from that plan; the remaining findings are still open.
>
> **DONE this session (one PR, full gate + parity green; +5 tests → 1664 passed):**
> - **M1 — exclude inactive tasks (ADR-0128).** Operator chose to match MS Project / Acumen. `is_active=False`
>   tasks are now dropped at the two chokepoints `metrics/_common.non_summary` and `cpm._scheduled_tasks`
>   (plus `driving_path`, `driving_slack.date_basis`, `vertical_integration`, the DCMA12 target filter), so
>   they leave the CPM network and every metric denominator; links to them drop with them. The
>   **diff/manipulation layer is intentionally left reading `schedule.tasks`** so a *deactivation* between
>   versions is still a detectable manipulation. No golden number moves (goldens have 0 inactive tasks → parity
>   green); pinned by new `tests/engine/test_inactive_tasks.py`.
> - **C2 — operator-selectable Ask-the-AI figure mode (ADR-0129).** `qa_mode` is now `annotate` (default) /
>   `strict` / `interpretive`, chosen in AI Settings. **annotate** keeps the rich answer but flags any figure
>   the engine didn't compute in an `[AI-derived …]` footer (`qa._annotate_unsourced`); **strict** discards
>   such answers; **interpretive** is verbatim/ungated (explicit opt-in). The CLAUDE.md guarantee is
>   **re-scoped** to be honest per mode. Tests updated to the new default + a 3-mode route test + an annotate
>   unit test.
>
> **REMAINING from the plan (next):** Wave 1 — **C1** (`to_json_text` Save→reopen field loss), **H1**
> (`_apply_ssi_setup` 500 + partial mutation on non-list `affected`), **H3/H4** (XER one-bad-id sinks the file),
> **M3** (friendly JSON fabricated `project_start`), **M4** (MSPDI root baseline leak), **M5** (days↔% rounding).
> Wave 2 — **H2** (reattach guards digits not prose), **M6** (sign-blind figure regex), **M2** (pre-commit guard
> omits `.aft`/`.docx`). Wave 3 — **M7, M8, L1–L12**. Full table + evidence in `AUDIT-2026-06-25.md`.
> **Highest ADR = 0129.** Keep running the full gate + `pytest -m parity` before each commit; add/patch a golden
> rather than loosen an assertion for any importer/engine change.

> ## STATUS (prev) — Full-repository QC audit MERGED (#265); the next session executes the plan of action
>
> **READ FIRST:** `docs/STATE/AUDIT-2026-06-25.md` (now on `main`) — the full audit report, a sequenced
> 3-wave plan of action, and a verification appendix (every finding re-confirmed by executing the real code
> paths; every "solid" claim survived falsification). The audit landed via **PR #265 (merged)**; that branch
> was consumed by the squash-merge, so **branch fresh from `main`** for the fix work.
> The audit itself was **read-only** — no code was changed (gate stayed green). The next session's job is to
> **fix** the findings, wave by wave.
>
> **Baseline is GREEN** (verified this session): ruff/format/mypy/bandit/node clean; `pytest -q`
> **1659 passed, 7 skipped, 2 xfailed**; `pytest -m parity` green. Both non-negotiable laws hold; no air-gap
> leak, no forbidden HTTP client, no committed CUI, no model-id leak. The findings are gaps the goldens/tests
> **don't exercise**, not regressions in the gate.
>
> **Findings: 2 Critical, 4 High, 8 Medium, 12 Low/Nit.** Headlines:
> - **C1 (Critical)** `to_json_text` Save→reopen (.json) **silently drops** the Acumen-parity
>   `stored_total_float_minutes` / `stored_is_critical` + 9 other fields (`is_active`, `custom_fields`,
>   calendar `working_days`/`day_segments`…) → silent Law-2 fidelity break. `importers/json_schedule.py:75,95,180`.
> - **C2 (Critical, ASK FIRST)** the **default** interpretive Ask-the-AI mode passes model-invented numbers
>   to the operator (the figure-gate is skipped) — contradicts the "no unsourced number" guarantee; a test
>   pins it (`31415`). `ai/qa.py:393`, `ai/backend.py:53`.
> - **H1** `_apply_ssi_setup` 500s **and half-mutates the session** on a hand-edited non-list `affected`
>   (`web/app.py:6126`). **H2** the reattach gate guards digits not prose (`ai/citations.py`). **H3/H4** one
>   malformed XER id sinks the whole file (`importers/xer.py:168,415`).
> - Medium incl. **M1** inactive tasks never excluded from CPM/metrics (no engine consumer of `is_active`;
>   goldens can't catch it — **ASK FIRST** on semantics + add a golden), **M2** pre-commit guard omits
>   `.aft`/`.docx`, **M5** days↔% client/server rounding mismatch. Full table + per-finding evidence + the
>   sequenced plan are in `AUDIT-2026-06-25.md`.
>
> **Plan of action (in the audit doc):** Wave 1 = fidelity/crash safety (C1, H1, H3/H4, M3, M4, M5; M1 ASK
> FIRST). Wave 2 = AI honesty + Law-1 spec (C2 ASK FIRST, H2, M6, M2). Wave 3 = robustness/perf/docs/test
> depth (M7, M8, all Low). Run the full gate + `pytest -m parity` before every commit; add/patch a **golden**
> rather than loosen an assertion for any importer/engine behavior change; if a fix warrants a decision, mint
> **ADR-0128** and refresh HANDOFF + SESSION-LOG in the same commit. **Highest ADR remains 0127.**
>
> **Next session:** branch **fresh off `main`** (the audit branch is merged/consumed), start Wave 1, ASK
> FIRST on C2 + M1, open a draft PR. The audit doc is the single source of truth for what to fix and in what
> order. **Two decisions gate coding:** C2 (default Ask-the-AI mode) and M1 (inactive-task semantics) — raise
> both via AskUserQuestion before implementing them.

> ## STATUS (prev) — Unified SRA risk register (enter once; ADR-0127); #258–#261 merged; branch `claude/eager-rubin-xianw9`
>
> **Five PRs this session.** Reset to `origin/main` after each merge, next stacked fresh.
> - **MERGED:** **#258** Gantt view fixes + globe-throttle SRA-freeze fix → **#259** SRA Monte-Carlo process-offload (ADR-0126) → **#260** more User Tips (7 pages) → **#261** responsive small-screen layout (hamburger nav, touch controls, table scroll — CUI-safe, pure CSS).
> - **THIS PR — Unified SRA risk register (full clean migration, ADR-0127).** Operator: enter a risk ONCE; it feeds BOTH SRA models. New `UnifiedRisk` (web/SessionState) carries one event's additive `impact_days` (SSI) AND multiplicative `impact_pct` (legacy) + per-model lock flags; `SessionState.sra_risks` is now `list[UnifiedRisk]` (the SSI list/seq removed). ONE form + ONE route `POST /sra/risk-register` (the two old routes `/sra/risk-event` + `/sra/ssi-risk` REMOVED). `_risk_events`/`_schedule_risks` derive the frozen `RiskEvent`/`ScheduleRisk` at the boundary — **engine + byte-frozen parity tests untouched** (`SCHEMA_VERSION` 2.4.0 unchanged). Days↔% auto-derive from the affected tasks' **avg remaining duration** (client `static/sra_risk.js` fed a uid→remaining-days map; server mirrors it via `_reconcile_magnitudes` for JS-off/load); typing a field locks it. Save/Load (`_ssi_setup_dict`/`_apply_ssi_setup`) persist the unified risks (both magnitudes + locks) and still load older SSI-only setups. ~5 web test files rewritten to the unified route + new derive/lock tests. Full gate green (**1654 passed**). **Highest ADR = 0127.**
> - **Operator decisions (AskUserQuestion):** SRA freeze → harden server side (#259); **iPhone access → out of scope for CUI** (no LAN bind); risk register → **full clean migration** (this PR).
> - **REMAINING queue:** #2 SRA JSON save/load of the whole setup — the unified Save/Load already landed in THIS PR (`_ssi_setup_dict` persists both magnitudes + locks); any further setup-version polish rides on top. (The responsive *view* #4 shipped in #261; tips #3 in #260.) Effectively the operator queue is complete pending review.

> ## STATUS (prev) — Gantt-view fixes + SRA Ask-the-AI freeze: #258 merged; SRA Monte-Carlo process-offload (ADR-0126) in flight; branch `claude/eager-rubin-xianw9`
>
> **Active branch is `claude/eager-rubin-xianw9`** (the seed's `claude/compassionate-ptolemy-wip898` is retired). Reset to `origin/main` after #258 merged, then this PR stacked on top.
> - **#258 MERGED to `main`** (`ba2dc69`): the path-analysis **Gantt view fixes** from the operator screenshot + the first SRA Ask-the-AI freeze fix.
>   - **Frozen data columns on every table Gantt** — shared `SFGantt.freezeColumns(table)` pins every column but the scalable timeline (`position:sticky` + measured per-column left offset, opaque canvas bg, freeze line); the activity/path/driving/SRA grids all call it, a column resize re-pins, print un-pins.
>   - **Path timeline fits the selected path** — the axis spans `axisRows()` (the chosen tier, else every activity) and auto-scales (`fitFill`) to the page width minus the measured columns, so bars fill the page next to the columns instead of squished at the far right; the zoom slider switches to a fixed px (scroll). `render()`/`reflow()` split so a tier/zoom change re-fits without tearing down dropdowns. **"View entire project"** widens to every activity (`scopeAll`). Asymmetric padding keeps the gold data-date line off the right border.
>   - **SRA Ask-the-AI freeze (client side)** — the header globe is the AI-status light; asking turned on `.ai-thinking`, restarting `globe.js`'s stroke-heavy canvas for the whole generation and pegging a CPU core on the heavy SRA page. Throttled the spin to ~15 fps (each frame schedules the next on a timer).
> - **THIS PR — SRA Monte-Carlo process-offload (ADR-0126)** — the operator chose "also harden the server side". `compute_sra` / `compute_sra_ssi` / `compute_oat_sensitivity` are CPU-bound pure Python that held the GIL in a `def` route and starved a concurrent Ask-the-AI call. New `web/offload.py` `run_offloaded` / `run_maybe_offloaded` dispatch the **heavy** runs (gated on `len(tasks) >= 300`) to a lazily-created single worker process, **byte-identical** to in-process (same seeded RNG), with an **in-process fallback** on any pool failure and the function's own exceptions propagating unchanged. Five SRA routes wired; `shutdown_offload()` on Quit; `launcher.py` adds `freeze_support()`. **No model change** (`SCHEMA_VERSION` 2.4.0 untouched), still std-lib only, air-gap intact. Tests: `tests/web/test_offload.py`. **Highest ADR = 0126.**
> - **Operator decisions this session (AskUserQuestion):** SRA freeze → "also harden the server side" (this PR). **iPhone access → "out of scope for CUI"** — queue item #5 is CLOSED; do **not** add any LAN/off-loopback bind. The responsive mobile *view* (#4) remains optional/separate (not requested again).
> - **REMAINING operator queue:** #1 unified SRA risk register, #2 SRA JSON save/load of the whole setup, #3 more User Tips, #4 responsive mobile view (optional). See the block below for the settled designs.

> ## STATUS (prev) — verified clean baseline; remaining operator queue is 5 items (1 needs an operator decision)
>
> **Verified state (assume nothing — checked on this branch):**
> - **Branch `claude/compassionate-ptolemy-wip898` is LEVEL with `origin/main`** (`git diff --quiet origin/main HEAD` → clean). No un-pushed work, no open PR for this branch (PR #256 merged).
> - **`main` tip = `29f7aaa` (#256).** Merged this sweep: **#248** self-describing SRA visuals → **#249** drop operator-facing Acumen/SSI branding → **#250** SRA finish-spread calendar-days + OAT float basis → **#251** metric-header call-outs + full-width briefing + light default + drag-drop fix → **#252** call-outs on Float/Trend/SRA tables → **#253** larger SRA visuals + full MS-Project Gantt parity + shared SRA inputs + globe freeze fix → **#254** AI Settings live model pickers + CUI explainer → **#255** EVM section + Correlation explainer → **#256** Resources section (schema 2.4.0, ADR-0125).
> - **`SCHEMA_VERSION = "2.4.0"`**; **highest ADR = 0125**; nav carries `/evm` and `/resources`.
> - **Full gate GREEN** (verified): `ruff check` ✓, `ruff format --check` ✓, `mypy src/` (strict, 84 files) ✓, `bandit -r src` exit 0 (only nosec/comment warnings) ✓, `node --check` all static JS ✓, `pytest` **1628 passed, 7 skipped (env-gated CUI intake / Java), 2 xfail (stale ssi_uid143 golden, ADR-0112)**.
>
> **What landed in this sweep (highlights):** SRA finish-date charts enlarged + tornado tightened (rowH 18→13); one MS-Project Gantt look across EVERY Gantt (sticky headers/timescale, resizable columns, Find-a-UID, outline-level picker, dates-on-bars, distinct summary bars); SRA **top-of-page file selector** for all models + **shared factor/BC-WC durations** feeding BOTH the SSI and legacy Monte-Carlo; SRA-model + JCL + **Correlation** explainers; the header-globe **perpetual-rAF freeze fix** (page froze while typing in Ask-the-AI); AI Settings **live model dropdowns** (fixes OpenAI-compatible in one flow) + cross-check-model dropdown + per-backend **CUI/data-locality** explainer; the **EVM** section (`/evm`, schedule-based always, cost indices adaptive N/A); the **Resources** section (`/resources`, ADR-0125 schema migration → assignment work/units → monthly load-vs-capacity histogram + over-allocation).
>
> **REMAINING operator queue (verified NOT done; design already settled where noted):**
> 1. **Unified SRA risk register** — still TWO separate forms: `/sra/risk-event` (legacy multiplicative %, `sra_risks`/`RiskEvent`) and `/sra/ssi-risk` (SSI additive days, `sra_ssi_risks`/`ScheduleRisk`). Operator wants to **enter a risk once**. **Decided design (operator's answer):** one register/form carrying BOTH a days magnitude (SSI) and a %/multiplicative magnitude (legacy); when the user types ONE, the tool **auto-calculates the other** from the affected tasks' remaining duration; the user may **override either**, and once overridden it is **locked** and used verbatim for that model. Keep `compute_sra`/`RiskEvent` byte-frozen — derive both `ScheduleRisk` and `RiskEvent` from the unified record at the web boundary (a parity test pins legacy byte-identity). Auto-derive is client-side JS (embed a uid→remaining-days map in the page) with per-field lock flags in SessionState.
> 2. **SRA JSON save/load of the WHOLE setup** — `_ssi_setup_dict` (`setup_version`) currently persists only the SSI inputs; extend it to the unified risks (both magnitudes + lock flags) + the legacy fields so a load applies to every model. Bump `setup_version`.
> 3. **More User Tips** — the `_user_tip()` component + `.user-tip` CSS exist (used ~5× on /sra, /evm, /resources). Add tips to the other major pages (analysis grid, path, evolution, trend, groups, forecast, settings).
> 4. **Responsive mobile view** — CUI-SAFE (pure CSS/layout). A `viewport` meta + a couple of reflow `@media` rules already exist; build a real small-screen layout (collapsible nav, touch-sized controls, stacked panels, the wide Gantt/tables scroll). No network change.
> 5. **iPhone access — NEEDS AN OPERATOR DECISION (do not build blind).** Reaching the tool *from a separate iPhone* requires binding off-loopback (LAN), which **conflicts with Law 1** (loopback-only; CUI never leaves the machine). Present options and get the call BEFORE any network-binding change: (a) responsive view only, used when the tool itself runs on the portable device; (b) explicit, opt-in LAN bind gated to **UNCLASSIFIED** only, with a loud CUI warning + the egress banner; (c) document phone access as out-of-scope for CUI. The mobile *view* (#4) is safe to build regardless.
>
> **Workflow note for the next session:** the operator merges each draft PR quickly and prefers **one focused PR per piece** (merge, then `git merge origin/main`, then next). Squash-merges diverge the rolling branch, so after a merge run `git merge origin/main` (content reconciles to a no-op) before new work. Commit author `noreply@anthropic.com`; never put the model id in commits/PRs/code. Each model-field change is change-controlled: bump `SCHEMA_VERSION` + update `tests/model/test_schema_freeze.py` + add an ADR + refresh BOTH `HANDOFF.md` and `SESSION-LOG.md` (the drift guard fails otherwise).


> ## STATUS (current) — Gantt visual-consistency: one MS-Project look + interaction on EVERY Gantt; branch `claude/compassionate-ptolemy-wip898`
>
> **Operator ask:** "make the gantt chart views in the critical path evolution and path analysis and
> driving path look like those with the white background ... a consistent visual ... a drop down such as
> that in MS Project [for filters] ... the same kind of drop down to add columns or remove columns ...
> the (view entire project) option available on all gantt charts that auto scales the timeline."
> Confirmed (AskUserQuestion): do all four pieces, with **per-column filters like MS Project**.
> - **White canvas on every Gantt.** The light-scope CSS selector now also covers `.evo-gantt` (the
>   Critical-Path Evolution SVG), so evolution/path/driving/SRA/main grids all share the white MS-Project
>   surface. (driving-path already rode `.gantt-grid`.)
> - **"View entire project" on every Gantt.** A `forcedPx` fit (auto-scale the timeline to the whole span,
>   cleared when the zoom control is nudged) is wired into `path.js` (`pathFit`), `sra_grid.js`
>   (`ssiGridFit`), `driving_path.js` (`dpFit`); the evolution view's axis-reset is relabelled
>   "View entire project" (it already snaps lo/hi back to the full padded axis).
> - **Shared columns dropdown.** The activity grid (`app.js`) and path grid (`path.js`) now add/remove
>   columns through the **same** `SFChecklist.filter` "Columns ▾" dropdown (was a loose checkbox row).
> - **Per-column MS-Project filters on the path grid.** A `.filter-row` under the headers mounts an
>   `SFChecklist.filter` per column (distinct values, `colFilters` Set), scoping visible rows;
>   `render()`/`paintRows()` split so toggling a filter repaints only the body.
> - Tests: `tests/web/test_gantt_consistency.py` (fit buttons, fit logic per script, evolution relabel,
>   shared columns dropdown, per-column filter row) + the `.evo-gantt` white-canvas assertions in
>   `test_visuals.py`. Full gate clean; **1599 passed**. No engine numbers move; no new ADR.
> - **NEXT / deferred:** the paused driving-path feature — pick up to 2 versions side-by-side, animate the
>   source→target corridor earliest→latest, call out what enters/leaves the path and why, and a
>   hide-completed filter. Engine already returns `source_uid`/`target_uid`/`entered`.

# Handoff — 2026-06-25 (SRA reporting/UX overhaul — operator batch; #23-#28 + the comprehensive Word report (ADR-0124) DONE; only the legacy-chart shrink sweep remains)

> ## STATUS (current) — SRA reporting/UX overhaul — the **comprehensive MS Word SRA report with vendor-free vector charts** + a downloadable risk registry landed (ADR-0124); branch `claude/compassionate-ptolemy-wip898`
>
> **The headline report is done.** `reports/docx.py` gained a `Chart` block that draws **native
> DrawingML vector shapes** (wpg/wps shape group: `a:custGeom` polylines for the S-curve/axis/tornado,
> `a:prstGeom rect` bars, ellipse dots) — **no image part, no rasterizer, no new ZIP part, byte-
> deterministic** — and a shaded `w:tbl` for the 5x5 matrices. `web/app.py` `_sra_report_blocks` composes
> the full report (Executive summary -> Focus-finish + S-curve + distribution -> Duration sensitivity +
> tornado + OAT -> Per-task durations -> Risk register -> the two 5x5 matrices -> Methodology &
> assumptions). `GET /export/docx/sra` now returns the narrative report; `/export/xlsx/sra` stays tabular;
> `GET /export/{fmt}/sra-registry` is the downloadable risk registry. Approach was de-risked by a recon
> **workflow** (mapped the writer + SSI data + proved the vector-docx technique builds a valid file in an
> isolated worktree) before any code. Tests: `Chart` rendering + report/registry routes; full gate clean.
> - **Operator batch status:** #23 consequence days->months (DONE, #243) - #24 NASA 5x5 matrices (DONE,
>   #243) - #25 grid resize + paste-from-Excel (DONE, #243/#244) - #26 **risk registry + Word report
>   (DONE, this push, ADR-0124)** - #27 SSI S-curve (DONE, #245) **but the legacy-chart shrink sweep +
>   the on-screen tornado restyle still REMAIN** - #28 11px text (DONE, #244).
> - **NEXT (the only operator item left):** the #27 tail — shrink/redraw the **legacy** `sra.js` charts
>   (S-curve / tornado / histogram) smaller + denser, "same for all other graphs."
>
> ## STATUS (prev) — SRA reporting/UX overhaul (operator batch, ADR-0123 family) — CHUNK 1 IN: consequence auto-calc (Schedule days->months) + the exact NASA 5x5 Risk/Opportunity matrices; branch `claude/compassionate-ptolemy-wip898`
>
> **Operator dropped a large SRA overhaul spec (screenshots + the SSI reference Excel exports).** Working
> it in sequenced chunks on one branch. **Chunk 1 (this push):**
> - **Consequence rating (1-5) auto-calc** — `engine/sra.py` `_consequence_rating` now follows the NASA
>   **Schedule** guideline, converting the entered impact **days -> calendar months** (30.44 d/mo):
>   `<1wk=1, 1wk-<1mo=2, 1-<3mo=3, 3-<=6mo=4, >6mo=5`. Tooltip on the risk-register Consequence field.
> - **5x5 matrices framed exactly like the NASA reference image** (`web/static/sra_ssi.js` + `app.css`
>   `.nasa-matrix`/`.nm-*`): Likelihood rows (5 Near Certainty..1 Remote) x Consequence/Benefit cols
>   (1..5), the fixed NASA priority ranks 1..25, tri-band zones (Risk green/yellow/red; Opportunity
>   light/medium/dark blue), axis labels, a High/Medium/Low legend, and a count badge where risks land.
> - Tests updated (engine consequence bands; web consequence guideline + NASA matrix wiring). Full suite
>   **1558 passed**, coverage held; gate clean. Still ADR-0123 (no new ADR).
> - **QUEUED (operator batch, tasks #25-#28):** (#25) SSI grid resizable columns + in-grid Factor input +
>   **paste-from-Excel** bulk fill; (#26) downloadable risk **registry** + a comprehensive **MS Word SRA
>   report** (PM high-level then details, graphics/images/assumptions); (#27) smoother high-granularity
>   **S-curve** + smaller/denser tornado + histogram + all charts (report-quality images); (#28) global
>   tool text size = 11px (the Gantt size). These are the bulk of the remaining work.
>
> ## STATUS (prev) — SRA SSI remodel (ADR-0123) feature-COMPLETE: the inline-editable schedule grid, JSON Save/Load, and Excel/Word export landed on top of the merged engine + control surface; branch `claude/compassionate-ptolemy-wip898`
>
> **The SSI remodel is done.** PR #241 (merged) shipped the engine + the SSI control panel + 5×5 matrices
> + deterministic OAT. This follow-up PR adds the three deferred pieces, all on the routes #241 landed:
> - **Editable schedule grid** (`web/static/sra_grid.js`, vendored, reuses `SFGantt`): the whole plan as
>   an SSI-style grid — type a **Risk Ranking Factor (1–5)** or edit **Best/Worst Case days** inline, pick
>   the **focus** event with a radio. A factor auto-fills Best/Worst from the table; an explicit BC/WC entry
>   is a manual override (mirrors `_ssi_three_point` precedence). Edits queue per-UID (one delegated
>   listener, no per-cell handlers) and batch-save to `POST /sra/grid`; the row feed is `GET /api/sra/grid`
>   (built on the existing `_activity_rows`). MS-Project Year/Quarter/Month timeline + a translucent
>   Best/Worst finish envelope per bar. Summary rows bold + non-editable.
> - **JSON Save/Load** (`GET /sra/ssi/save` download, `POST /sra/ssi/load` upload): a versioned
>   (`setup_version=1`) object — focus, factor table, factors, BC/WC minutes, risks, run options. Load
>   validates UIDs against the active schedule (unknown/summary dropped, factors clamped). Std-lib `json`.
> - **Excel/Word export** (`GET /export/{fmt}/sra`): a six-table hand-out (run setup, per-task durations,
>   risk register, focus-finish results, OAT sensitivity, the two 5×5 matrices) via the existing
>   `TableSet`/`render_xlsx`/`render_docx` (CUI banner stamped, byte-deterministic). Runs the MC + OAT on
>   demand, off the page-load path.
> - No model/schema change (all SSI inputs on `SessionState`); offline/std-lib/air-gap/CUI intact; new JS
>   vendored + same-origin (`node --check` clean). Still **ADR-0123** (no new ADR — this is its deferred tail).
> - Tests: `tests/web/test_sra_grid.py` (11) + the merged `test_sra_ssi*.py` (21) green; full suite **1553
>   passed**, coverage gates held. Engine parity unchanged (BC/WC + OAT exact; ADR-0005 stochastic caveat).
> - **Two operator Gantt-presentation asks added to the same PR (no new ADR):**
>   1. **Gantts always render in LIGHT mode** (the MS-Project look) regardless of the page theme — the
>      dark grid behind white bars was jarring. `app.css` scopes the light palette onto
>      `.gantt-grid/.path-view/.gantt-scroll/.sra-grid-host` (cascade flips every descendant) with a
>      white grid background; **summary-task names forced dark + bold**. Only the charts change.
>   2. **Any .mpp field selectable as a column** (standard or custom). The model/importer already map
>      extended attributes (`Task.custom_fields`, `Schedule.custom_field_labels`); this surfaces them —
>      `_activity_rows` now emits each task's `custom` map and `_analysis_data` advertises
>      `custom_field_labels`; `app.js` appends each as an optional toggleable column and reads it via a
>      `valueOf()` accessor (sort/filter/drill all work on custom columns). Activity grid (the column
>      chooser); the trace/SSI grids keep their fixed columns. Full suite **1556 passed**.
>
> ## STATUS (prev) — Gantt density pass (3x more tasks/page, bold summaries, gridlines), a "Fit project" button, and Dur/Start/Finish/Driving-slack columns on the trace; branch `claude/compassionate-ptolemy-wip898`
>
> **PR 4 (#238) is in CI; this PR 5 is HELD locally until #238 merges (don't push onto an open PR).**
> Operator wanted the Gantts much denser + a fit button + richer trace columns:
> - **Density (app.css, scoped to the schedule grids — not the report tables):** `.gantt-grid` /
>   `.gantt-row` / `.path-grid` → 11px font, ~1px row padding, line-height 1.2, **bold summary rows**
>   (`tr.sum td` 700), and **gridlines between every row AND column** (`border-right`/`border-bottom`).
>   Track 16→13px, bars 10→9px. ~2–3x more tasks per page; matches the trace font the operator liked.
> - **Fit-to-screen (app.js):** a new `#fitBtn` "Fit project" button next to Scale; `fitToWidth()`
>   computes px/day = (grid width − data cols) / project-span-days and sets `forcedPx` (overrides the
>   slider; any slider move clears it). Whole project on one screen.
> - **Driving-path trace columns (app.js renderGantt):** Dur / Start / Finish / Driving-slack columns
>   per row (data already on each row — `duration_days`/`start`/`finish`/`driving_slack_days`; no API
>   change), aligned via a fixed-width `.gantt-cols` block so the bars still line up under the scale.
> - **Gate:** ruff/format/mypy/bandit/`node --check` clean; full suite running. No new ADR. Visual —
>   eyeball it.
> - **STILL OPEN — the big one:** the SRA SSI remodel (task #19), designed + parity-anchored, not built.
>
> ## STATUS (prev) — AI "working" indicator + 3D rotating-Earth header insignia; DCMA-14 re-verified against the operator's SRA Project5; branch `claude/compassionate-ptolemy-wip898`
>
> **PR 1 (#236) + PR 2 (#237) merged.** This PR ships two operator asks + a fidelity re-check:
> - **Metrics re-validated (no code change).** Operator questioned DCMA-01 Logic (5/99 fail). Confirmed
>   correct: the 5 offenders are incomplete tasks missing a successor (UID 106, 113, 129, 136, 145);
>   DCMA-01 scores only the 99 incomplete activities, so the operator's other missing-logic tasks are
>   100% complete (correctly excluded). 5/99 = 5.05% → marginal fail (UID 145/136 are end milestones the
>   by-the-book metric still counts). Lags=1 verified against the RAW MSPDI (only 2 lag links exist;
>   28→30 is on a complete task). Float matches MS Project stored Total Slack exactly; BEI 0.59, Missed
>   37/46, High Float 39/99 all reproduce. **The engine is calculating correctly.**
> - **AI status light (operator: a 72B q8 model used 100 GB RAM and "nothing generated" — was it stuck?).**
>   It was thinking, not stuck (100 GB ≈ q8 72B + KV cache; CPU 72B is just slow). `ask.js` now shows a
>   live "the local AI is working… (Ns)" counter + a >20s "large models take minutes, not stuck" hint,
>   and toggles `.ai-thinking` on the header insignia so **every page** shows the AI is working (red
>   flash on failure/timeout).
> - **3D Earth insignia (replaces the meatball).** New vendored `static/globe.js` — a transparent
>   `<canvas>` wireframe Earth (graticule + coarse continent coastlines, far side faded so it's
>   see-through) rotating around a **stationary "NASA" wordmark**, **3× the old size** (132px). Pure
>   canvas, no images/CDN (air-gap), honours prefers-reduced-motion, and spins up + glows cyan while the
>   AI generates. `nasa-meatball.svg` removed. **Visual — eyeball it in the running app** (no headless
>   browser here).
> - **Gate:** ruff/format/mypy/bandit/`node --check` clean; full suite running. No new ADR.
> - **STILL OPEN — the big one:** the SRA SSI remodel (task #19) is designed + parity-anchored but NOT
>   yet built (engine layer was about to start when the operator pivoted to these asks). Plan:
>   `/root/.claude/plans/virtual-wobbling-donut.md` (note: ephemeral) — see the prior STATUS blocks.
>
> ## STATUS (prev) — PR 2 of 3 (UI): visible nav labels + de-bunched spacing, MS-Project Gantt plotting area, offline UI translation 7%→~58%; branch `claude/compassionate-ptolemy-wip898`
>
> **PR 1 (`.mpp`/Ollama) merged as #236.** This PR ships the UI cluster from the operator's batch:
> - **Nav legibility + spacing.** The function labels (OVERVIEW/ASSESSMENT/CONTROL/RISKS…) were 10px
>   at 0.6 opacity → now 12px, full-opacity, accent-coloured; nav links brightened to `--ink`. The
>   ~25–30% spacing condensation from #224 is reverted (main 16/22→24/28, panel 13/16→18/20 + margin
>   12→18, h2 9→12, th/td 5/9→7/10, header 10/20→14/24) so the UI is no longer "bunched up".
> - **MS-Project Gantt canvas (dark mode kept).** New theme-independent `--gantt-*` tokens (white
>   canvas, light/medium/dark gridlines, pale header band, dark milestone/%-complete overlay); the
>   Gantt classes (`.g-track`/`.g-grid*`/`.g-band`/`.gantt-track`/`.path-track`) point at them, so the
>   plotting area mirrors MS Project in BOTH themes while the rest of the page stays dark. Critically
>   fixes the milestone diamond (`--ink`, invisible on white) and the %-complete overlay (was white-on-
>   white in dark mode).
> - **Translation (operator chose "both: offline dict + AI", "translate everything").** Verified the
>   switch mechanism already works (reload + non-destructive client translate; switched es→fr→de→en→pt
>   fine). The gap was COVERAGE: the offline catalog was 117 terms (~7% of visible UI). Expanded
>   `i18n._TERMS` to **191 terms** (+UI chrome, DCMA/EVM metric names, severities, banners) → ~58% of
>   short UI strings now translate **offline**; the AI fallback covers the long-tail prose when a model
>   is on. Schedule DATA (task names) intentionally left untranslated.
> - **Gate:** ruff/format/mypy/bandit/`node --check` clean; full suite running. No new ADR.
> - **Next — PR 3:** the big SRA SSI remodel (editable Gantt grid + Risk Ranking Factors + risk
>   register + 5×5 matrices + correlation + Save/Load + Excel). Plan: the SRA design is written and
>   parity-anchored (BC/WC formula, deterministic focus finish 2027-12-03, OAT sensitivity all verified
>   against the operator's SSI exports).
>
> ## STATUS (prev) — operator bug batch, PR 1 of 3: the analysis report never blocks on the AI, and Ollama is fully controllable/stoppable; branch `claude/compassionate-ptolemy-wip898`
>
> **Operator report (this session): a batch of issues.** This PR ships the two urgent ones; UI fixes
> (nav legibility/spacing, MS-Project Gantt background, full i18n) and the big SRA SSI remodel follow
> as PR 2 and PR 3 (SRA plan written; correlation included).
> - **`.mpp` "won't load" — the tab spinner never finished. ROOT CAUSE: the `/analysis` report
>   polished its narrative through the local model *synchronously during the page render* (one
>   `backend.generate()` per statement). With the operator's 72B Ollama active, the report — the page
>   a single uploaded schedule lands on — blocked for minutes, so a big `.mpp` looked exactly like
>   "won't load."** Fix: `/analysis` now renders the **deterministic** narrative instantly and defers
>   polish to the async `/api/ai/narrative` via `ai_polish.js` (the pattern #177 already gave
>   Risks/Briefing; `/analysis` had been missed). Also hardened the MPXJ subprocess for the windowless
>   desktop (`stdin=DEVNULL` + Windows `CREATE_NO_WINDOW`) so a `pythonw` launch can't flash a console
>   / hang on an inherited stdin handle.
> - **Ollama survived Wipe → Quit and kept eating RAM. ROOT CAUSE: `_default_stop_server` killed only
>   `ollama.exe`; the Windows tray app (`ollama app.exe`) *respawns* it.** Fix: stop the tray
>   supervisor first, then the server. The AI is now fully controllable: switching the backend off
>   Ollama (to Null/etc.) **stops** the local model, a new **"Turn the AI off"** button on AI Settings
>   routes back to Null and stops the model in one click, and **Wipe Session** turns the AI off + stops
>   Ollama. Start stays lazy (only on AI-enable, ADR-0122).
> - **Gate:** ruff/format/mypy/bandit/`node --check` clean; web/ai/importers suites green; full suite
>   running. No new ADR (extends ADR-0122, still the highest on disk).
>
> ## STATUS (prev) — lazy Ollama lifecycle: start on AI-enable, free the model RAM + stop our serve on close (ADR-0122); branch `claude/compassionate-ptolemy-wip898`
>
> **What shipped this session (branch `claude/compassionate-ptolemy-wip898`, fresh on `main`):**
> - **Operator bug:** after quitting the tool, Ollama (a resident 72B model, ~40% RAM) kept running.
>   Causes: (1) the launcher started `ollama serve` at **every** launch even without AI; (2) shutdown
>   only stopped an Ollama the tool itself started, so a Windows-tray-started one was never freed.
> - **Fix — ADR-0122 (lazy + self-cleaning), gated on `OllamaLauncher._engaged`:**
>   - **Lazy start:** launcher no longer starts Ollama at launch; it hands the manager to
>     `create_app(ollama=…)`, and the `/settings` POST starts it (off-thread) **only when the
>     operator selects the Ollama backend**.
>   - **Tidy on close (operator chose "fully stop"):** `shutdown()` is a **no-op if AI was never
>     enabled**; otherwise it **unloads every in-memory model** (`/api/ps` + `keep_alive:0`, std-lib
>     `urllib`, loopback only) — freeing RAM even when the tool only *adopted* a running server —
>     gracefully terminates the serve it started, then **stops any Ollama server still running**
>     (`taskkill /F /T /IM ollama.exe` / `pkill -x ollama`, incl. a tray-started one it adopted).
>   - **Can't fully own:** the Ollama **Windows desktop app** (`ollama app.exe`) relaunches a server at
>     **next login**; the tool stops the server on close but not the tray app. The AI Settings page +
>     `docs/CONNECT-A-BIGGER-AI-MODEL.md` explain how to disable that auto-start.
> - **Gate green:** ollama/launcher/ai-wiring suites pass; full gate run before commit. Highest ADR = **0122**.
>
> ## STATUS (prev) — Executive Briefing rebuilt as a numbered, plain-English forensic summary (+ Word/Excel hand-out); ADR-0121; branch `claude/compassionate-ptolemy-wip898`
>
> **What shipped this session (branch `claude/compassionate-ptolemy-wip898`, fresh on `main`):**
> - **Executive Briefing redesign (ADR-0121).** `ai/briefing.py` is rebuilt to model an operator-
>   supplied forensic Executive Summary: a metadata header + a status-tinted verdict banner
>   (ON TRACK / WATCH / AT RISK), then numbered sections — **1. The Bottom Line** (verdict + plain
>   story + the duration-based SPI), **2. How the Project Has Performed**, **3. The Critical Path —
>   Then and Now** (real entered/left from `path_evolution` with ≥2 versions; an honest single-
>   version note otherwise), **4. Schedule Health Dashboard**, **5. Risks and Opportunities**
>   (`recommend` findings), **6. Recommended Actions** (+ if-nothing-done / if-implemented),
>   **7. How to Verify Every Number** (+ methodology + limitations). Every figure is engine-computed
>   and every statement/table row is cited (§6); the model only rephrases prose.
> - **Word + Excel hand-out.** New `/export/{fmt}/briefing` route + `briefing_blocks()`; the
>   `/briefing` page renders one continuous `brief-doc` and links the .docx/.xlsx exports.
> - **No model change:** `SCHEMA_VERSION` untouched; `ai/qa.py` reuses the new statements (signature
>   preserved). Many briefing-dependent tests updated to the new structure.
> - **Gate green:** ruff/format/mypy/bandit/`node --check` clean; full suite green. Highest ADR = **0121**.
> - **Also delivered this session (chat-only):** a 13-year-old-friendly guide to install
>   `llama3.1:8b`, `qwen2.5:7b-instruct`, and (for the operator's new 128 GB box) `qwen2.5:72b-instruct`
>   as the most powerful local brain, grounded in `docs/CONNECT-A-BIGGER-AI-MODEL.md`.
>
> ## STATUS (prev) — auto-shutdown idle grace raised to 10 minutes (ADR-0120); branch `claude/compassionate-ptolemy-wip898`
>
> **What shipped this session (branch `claude/compassionate-ptolemy-wip898`, fresh on `main` after #232 merged):**
> - **Auto-shutdown idle grace 10s → 600s (10 min) — ADR-0120.** `create_app`'s `idle_grace`
>   default is now 600.0. The page beats every 3s, but browsers throttle timers in a
>   backgrounded/minimized tab, so the old 10s grace shut a **still-open** tool down when it was
>   merely in the background (ADR-0032 had only fixed the server-busy false positive, not the
>   quiet-but-open one). 10 min also tolerates a brief navigation away / laptop sleep. The in-page
>   **Quit** control + `POST /api/shutdown` still stop it instantly; watchdog / heartbeat /
>   in-flight-hold / `_is_idle` all unchanged. Test `test_default_idle_grace_is_ten_minutes` pins it.
> - **Gate green:** full suite passed; ruff/format/mypy/bandit/`node --check` clean. Highest ADR = **0120**.
>
> ## STATUS (prev) — UI overhaul: MS-Project Gantt parity on all pages + DCMA-14 stoplight dashboard; ADR-0119 (merged #231/#232); branch `claude/compassionate-ptolemy-wip898`
>
> **What shipped this session (branch `claude/compassionate-ptolemy-wip898`):**
> - **Part A — DCMA-14 dashboard panel (merged, PR #231).** The dashboard shows spaced labels
>   (`DCMA 01`, not `DCMA01`) + the metric name, a simple measure, and a red/orange/green
>   **stoplight** (the red bar is gone). Hover a row for a tooltip calling out what the metric is,
>   why it matters, the pass/fail **threshold**, and a worked **pass** and **fail** example
>   (`help.py` gained `threshold`/`example_ok`/`example_fail`; `_dcma_card` feeds the JSON).
> - **Part B — Gantt mirrors Microsoft Project on every page (ADR-0119, this branch).**
>   - New `Task.outline_level` (MSPDI `<OutlineLevel>`, any depth) → `SCHEMA_VERSION` **2.2.0 → 2.3.0**;
>     MSPDI importer reads it; the activity grid indents the Name column by it and renders rows in
>     **file/outline order** (not UID) so parents sit above children.
>   - New vendored **`static/gantt.js` (`window.SFGantt`)** — one implementation of the stacked
>     **Year/Quarter/Month** header (`buildTierScale`) + month/quarter/year **gridlines**
>     (`gridLines`/`paintGrid`), on a tiny axis contract `{t0,t1,width,x}`. Loaded once in the shell.
>   - **Adopted everywhere a bar Gantt exists:** `app.js` (activity grid + driving-path trace),
>     `path.js`, `driving_path.js` drop their local month-tick loops and call `SFGantt`; the SVG
>     `path_evolution.js` gains the same quarter/year bands + graduated gridlines. Zoom, column
>     add/remove, and the checklist filters are preserved. `phases.js`/`cei.js` are categorical bar
>     charts (not date-axis Gantts) — left unchanged by design.
> - **Gate green:** full suite **1502 passed / 7 env-skipped / 2 xfail**; ruff/format/mypy/bandit/
>   `node --check` (all static JS) clean; coverage ≥70 overall / ≥85 engine.
> - **Highest ADR = 0119** (drift guard: referenced here and in SESSION-LOG).
> - **Next:** optional WBS collapse/expand of summary rows; consider giving the bow-wave/phase bar
>   charts the same stacked month axis if the operator wants time-scale parity there too.
>
> ## STATUS (prev) — shipped engine matches SSI on ALL 783 activities (focus UID 152); ADR-0116/0117/0118; branch `claude/compassionate-ptolemy-wip898`
>
> **What shipped this session (branch `claude/compassionate-ptolemy-wip898`, draft PR — pushed atop the merged #229):**
> - **`compute_driving_slack(target_uid=152)` reproduces the SSI Directional Path export for ALL
>   783 activities** (to the working day; driving path **61/61 set-equal**, zero full-day residuals)
>   on the operator's leveled Large Test File. Got there in three verified steps:
>   - **ADR-0116** — removed the whole-day **span-snap** (it collapsed parity to 325/783). Raw spans.
>   - **ADR-0117** — the slack pass honors the calendar's real **intraday hours** (the 12:00-13:00
>     lunch), so afternoon raggedness is no longer over-counted: 696 → **776/783**. New optional
>     `Calendar.day_segments`, populated by the MSPDI importer; global CPM untouched.
>   - **ADR-0118** — **per-task calendars + worked-exception days**: SSI counts each driving link's
>     free float on the **successor's own calendar**, and honors `DayWorking=1` days (a worked
>     Sunday). 776 → **783/783**. New `Calendar.uid`/`working_days`, `Task.calendar_uid`,
>     populated `Schedule.calendars`; `compute_driving_slack` rewritten as
>     `slack(i) = min over successor links of (link free float + successor slack)` — algebraically
>     identical to the old backward pass for single-calendar schedules (curated goldens unchanged).
> - **Root-cause story corrected:** the residuals were never "cosmetic." They were (1) the lunch
>   over-count and (2) per-task calendars (cal-68 "ZIN" holidays differ from the project cal) +
>   the skipped worked-Sunday — all consequences of ADR-0028 simplifications, now relaxed for the
>   driving-slack path only. Per-task *span* over-corrects (747) — the calendar belongs to the
>   free float, not the duration.
> - **No CUI / no Large-Test-File golden committed** (the `.mpp` is uncommittable). Regression guard:
>   `test_free_float_counted_on_successor_calendar` (synthetic — successor-cal holiday −1 day, worked
>   Saturday +1) + the committed `ssi_uid145` golden, which **stays exact**.
> - **Gate green:** full suite **1499 passed / 7 env-skipped / 2 xfail**; ruff/format/mypy/bandit/
>   `node --check` clean; engine coverage ≥85, driving_slack.py + calendar.py 100%.
> - **Highest ADR = 0118** (drift guard: referenced here and in SESSION-LOG).
>
> ## STATUS (prev) — span-snap removed; shipped engine matches SSI on the leveled Large Test File (focus UID 152, ADR-0116); branch `claude/compassionate-ptolemy-wip898`
>
> **What shipped (ADR-0116, merged as #229):**
> - **The driving-slack span-snap (ADR-0045) is REMOVED — ADR-0116.** The operator uploaded the
>   **leveled-and-saved** Large Test File ("USA OTB Master IMS", 1723 activities) + the matching SSI
>   Directional Path export for focus **UID 152** ("all dependents", **783** ancestors), plus un-leveled
>   variants. Operator-confirmed **non-CUI**; read locally, `.mpp`/`.xlsx` **not committed** (the
>   pre-commit guard blocks those binaries regardless).
> - **Verified, in order:** (step 2) MPXJ-read stored `Start`/`Finish` **= SSI dates 783/783 to the
>   minute**; (step 3) the **shipped** `compute_driving_slack(schedule, target_uid=152)` with the snap ON
>   matched only **325/783** and got the driving path wrong — with the snap **OFF** (raw working-minute
>   span) it reproduces SSI's **driving path 61/61, set-equal** (`driving_path()` returns the identical
>   UID set) and slack **within one working day for 782/783** (one full-day residual, uid 6123).
> - **Root-cause correction:** SSI does **not** snap to whole days (if it did, the raw span couldn't
>   reproduce its path exactly). ADR-0045's "afternoon-shift span raggedness" was a **misdiagnosis** of the
>   resource-leveling date discrepancy. The engine's calendar already applies the project calendar
>   ("Dynetics Standard", 480 min/day, 111 holidays **incl. 2026**) uniformly, so the seed's "cal-68 lacks
>   2026 holidays" residual hypothesis does not apply — the ~20 sub-day residuals are time-of-day boundary
>   effects below day granularity and don't change path membership.
> - **Change:** `engine/driving_slack.py` span line → raw span; the synthetic **TP1 battery test** updated
>   (snap's sub-day minutes 60/60/120 → true 210/210/120; tiers 13/1/2/2, DRIVING/floor-0, and band edges
>   all **unchanged**). **No Large-Test-File golden committed** (the `.mpp` can't be committed, so a
>   derived golden is unreproducible; it's a 1723-activity real IMS). Regression guard = updated TP1 test +
>   the committed **`ssi_uid145`** golden (ADR-0115), which **stays green** (snap was a no-op on whole-day
>   spans).
> - **Workflow answer (step 5):** the tool matches SSI **whenever the `.mpp` is saved in the same leveling
>   state SSI was run on** (leveled↔leveled and un-leveled↔un-leveled both matched). Guidance: **level →
>   save → analyze**. No tool change needed to ingest SSI's dates.
> - **Gate green:** full suite **1493 passed / 7 env-skipped / 2 xfail**; coverage overall 99.17% (≥70),
>   engine 99.84% (≥85), `driving_slack.py` 100%; ruff/format/mypy/bandit/`node --check` clean.
> - **Highest ADR = 0116** (drift guard: referenced in this HANDOFF and SESSION-LOG).
>
> ## STATUS (prev) — SSI driving-slack re-pinned (focus UID 145, ADR-0115); branch `claude/clever-volta-wbnx0i`
>
> **What shipped this session (branch `claude/clever-volta-wbnx0i`, draft PR):**
> - **SSI driving-slack parity is LIVE again on the authoritative Project5** — ADR-0115. The operator
>   provided the SSI **Directional Path Tool** export for focus **UID 145** ("Issue final request for
>   payment") on `Project5_TAMPERED.mpp` (uploaded this session, read locally, **never committed** —
>   Law 1). The engine reproduced the *Get all dependencies* export **bit-for-bit on the first run**:
>   **108/108 UniqueIDs**, every whole-day driving-slack value exact, driving path = {144, 145}, focus
>   at 0 d, tiers DRIVING=2 / SECONDARY=3 / TERTIARY=8 / BEYOND=95 (default 10/20-day bands).
> - **New golden** `tests/fixtures/golden/ssi_uid145/case.json` (108 UIDs; non-CUI Project5 sample,
>   ADR-0003/0005) + **two parity tests**: `test_ssi_driving_slack_uid145_exact` (parity gate) and
>   `test_golden_ssi_driving_slack_uid145_parity` (engine). No engine code changed — this certifies
>   existing behaviour and closes the SSI gap ADR-0112 opened.
> - **The two `ssi_uid143` `xfail`s stay documented-stale** (`test_parity_gate.py`,
>   `test_driving_slack.py`): this export is focus **145**, and a directional analysis is anchored at
>   its focus, so it does **not** yield the focus-143 map. Lifting them needs an SSI **focus-143**
>   export on the authoritative file — not fabricated (Law 2). The UID-145 match does prove the
>   *engine* is correct on the authoritative file, so `ssi_uid143` staleness is purely file-version.
> - **Highest ADR = 0115** (drift guard: referenced in this HANDOFF and SESSION-LOG).
>
> ### Environment note (important for the next session)
> This is a **cloud/web** session: the git-ignored CUI intake (`00_REFERENCE_INTAKE/`) is **empty on a
> fresh container** — it is **not** cloned. The prior #224/#225 handoff block below claims the SSI
> UID_145 export was "present in the intake"; that was true on the operator's local machine, not here.
> The operator **uploaded** the `.mpp`/`.xlsx` into this session; they were read locally and the
> derived non-CUI golden committed. Per `00_REFERENCE_INTAKE/DEPOSIT-HERE.md`, **do not deposit CUI in
> a cloud session** — for CUI-dependent work run locally, or have the operator upload (non-CUI samples
> only) as happened here.
>
> ### Open threads (still need the operator's input/files)
> 1. **Confirm Max Float 275 d vs Acumen** — engine reports Max Float 275.0 d / Avg 71.0 / Critical 4
>    on golden Project5 via `effective_total_float` (ADR-0010/0080). Needs the operator's **Acumen
>    stored value** to certify parity. ASK if not provided.
> 2. **Executive Briefing → full Acumen format** — `ai/briefing.py` opens with a "Key Assessment"
>    verdict (first pass). Matching Acumen's full briefing (sections / ordering / scoring) needs the
>    operator's **reference briefing document**. ASK.
> 3. **SSI focus-143 re-pin** — would lift the two `ssi_uid143` xfails; needs an SSI focus-143 export
>    on the authoritative file (trivial golden re-pin once it lands — same pattern as ADR-0115).
> 4. **Step 5 (value-based / per-activity SPI(t))** — BLOCKED: needs EVM3 "Detailed Metric Report.xlsx".
> 5. **Metric-formula audits** — BLOCKED: need the NASA Acumen metric-library `.aft` ("the Bible").
>
> ## STATUS (prev) — #224 merged; **full from-scratch audit done**; no work in flight
>
> **Verified this session (assumed nothing, re-checked from the repo, 2026-06-23):**
> - **`origin/main` HEAD = `99f3fea` (#224).** Every PR #213–#224 is squash-merged onto `main`; the
>   operator's entire "do them all" list shipped: S-curve fixes (#213), Max Float→stored slack (#214),
>   SRA indicator/Beta-PERT (#215), AI driving-path skill (#216, ADR-0114), i18n rewrite + Portuguese
>   (#217), Evolution path-tier selector (#218), Driving-Path 3-col tier panel (#219), slack-degradation
>   trend (#220), Finishes hide-completed (#221), curves tier-axis (#222), Exec-Briefing Key Assessment
>   (#223), optional polish — condensed spacing + tier-axis DRY (#224).
> - **Gate is green.** Parity gate re-run clean (`pytest -m parity` → 9 passed, 1 xfailed by design);
>   prior full-suite run was 1491 passed / 7 skipped / 2 xfailed. **No open PRs.** Highest ADR = **0114**.
> - **Max Float = 275.0 d** (Avg 71.0, Critical 4) on the authoritative golden Project5 via
>   `effective_total_float` (ADR-0010/0080). Engine-verified — *confirm against Acumen's stored value*.
> - **This branch (`claude/clever-hawking-06zdpz`) sits at `main` HEAD** and carries only this
>   doc-only handoff/log refresh.
>
> ### Reference-intake audit (the important correction to the prior seed prompt)
> - **SSI UID_145 directional-path export IS PRESENT — UNBLOCKED.**
>   `00_REFERENCE_INTAKE/audit/ssi_uid145/` holds the SSI run
>   `SSI Analysis UID_145_Directional_Path_Analysis_2026-6-22-…` — **7 `.xlsx` + 2 `.mpp` + 1 `.docx`**.
>   So the SSI driving-slack re-pin is **actionable now**, not awaiting a file. (CUI — git-ignored;
>   stays local; never commit it.)
> - **EVM3 detailed-metric report ABSENT** → build-order **Step 5 (value-based / per-activity SPI(t))
>   stays input-blocked.** Do not fabricate (Law 2).
> - **NASA Acumen metric-library `.aft` ("the Bible") ABSENT** → metric formula audits wait on the
>   operator's upload.
>
> ### Open threads (verified status)
> 1. **SSI driving-slack parity — TOP, UNBLOCKED.** Build a `tests/fixtures/golden/ssi_uid145/`
>    golden from the intake export and add a parity test for
>    `compute_driving_slack(schedule, target_uid=145)` on the current `Project5_TAMPERED.mpp`. The two
>    existing `xfail`s pin **UID 143** on the *prior* Project5 (stale per ADR-0112) — a UID-145 test is
>    fresh coverage and does **not** auto-lift them; first open the `.xlsx` to see whether it also
>    carries UID-143 path data that could re-pin/lift the `ssi_uid143` xfail, else leave it
>    documented-stale.
> 2. **Step 5 value-based ES — BLOCKED** (EVM3 absent; re-attach to resume).
> 3. **Executive Briefing → full Acumen format** — "Key Assessment" first pass is on `main`; matching
>    the full Acumen briefing (sections / ordering / scoring) needs the operator's reference document.
> 4. **Confirm Max Float 275 d vs Acumen** — engine value verified; needs the operator's Acumen number.
> 5. **Condensed spacing (#224)** — CSS-only, reversible; a visual eyeball is still recommended
>    (no headless browser here).
>
> ## STATUS (prev) — #213–#223 merged; optional polish (spacing + tier-axis DRY) in flight
>
> **`main` is green (#210–#223 merged):** the operator's entire "do them all" list is done (S-curve,
> Max Float, SRA, AI driving-path, i18n+PT, Evolution/Driving-Path tiers, trend, hide-completed,
> tier-axis on curves, Exec-Briefing Key Assessment).
>
> **OPEN draft PR (branch `claude/clever-hawking-06zdpz`, fresh on `main`): optional polish (both in
> one PR).** (1) **Condensed spacing** — moderate (~25–30%) reductions to the dominant whitespace
> in `base.css`/`app.css`: `main` 24/28→16/22, `.panel` 18/20→13/16 (margin 18→12), `h2` 12→9,
> `th/td` 7/10→5/9, header 14/22→10/20, `.banner`, `.viz-controls` 14→9. (2) **Tier-axis DRY** —
> `scurve.js` now draws its stacked Year/Quarter/Month header via the shared `SFTimeAxis`
> (`timeaxis.js`) instead of its own copy (~50 lines removed; behaviour identical — same minW/edges/
> first-letter logic). `timeaxis.js` loaded before `scurve.js` on the S-curve + Mission pages.
> Tests in `tests/web/test_chart_callouts.py`. No ADR. **Spacing wants a visual eyeball** (no browser
> here; CSS-only, fully reversible).
>
> ### Remaining — needs the operator's input/files
> Exec Briefing full Acumen format (reference); Step 5 (EVM3 absent); SSI #6 (UID_145); confirm
> Max Float 275d vs Acumen.
>
> **`main` is green (#210–#222 merged):** all chart-framework items done — incl. tier-axis on the
> curves charts (#222, shared `timeaxis.js`), Evolution/Driving-Path tiers, hide-completed, etc.
>
> **OPEN draft PR (branch `claude/clever-hawking-06zdpz`, fresh on `main`): Exec Briefing first pass.**
> The big remaining operator item is an Acumen-style Executive Briefing. As a verifiable FIRST PASS
> (no Acumen reference yet), `ai/briefing.py` now opens with a **"Key Assessment"** section for the
> latest version: an overall **verdict** (ON TRACK / NEEDS ATTENTION / AT RISK — a transparent
> heuristic from finish-slip + DCMA-14 fail count) plus the headline numbers a sponsor reads first
> (forecast completion vs baseline, critical exposure, DCMA fails, activity count), all engine-cited.
> `_assessment_section` reuses the existing finish/baseline/audit helpers; prepended in
> `build_briefing`. Existing structure tests updated (kinds now incl. "assessment"). Tests in
> `tests/ai/test_briefing.py`. No ADR. **Needs the operator's Acumen briefing to match the full
> format** (sections/ordering/scoring) — flagged in the PR.

> ## STATUS (prev) — #213–#221 merged; stacked time-tier axis on the curves charts in flight
>
> **`main` is green (#210–#221 merged):** … + Driving-Path 3-col tier (#219) + slack-degradation
> trend (#220) + Finishes hide-completed toggle (#221).
>
> **OPEN draft PR (branch `claude/clever-hawking-06zdpz`, fresh on `main`): tier-axis on the curves
> charts.** Extracted the S-curve's stacked Year/Quarter/Month tier logic into a shared module
> `static/timeaxis.js` (`window.SFTimeAxis` — `parseMonth`/`tiersFor`/`draw`) and wired it into
> `curves.js` `lineChart` (Finishes/Data-date/Slippage): a stacked tier header at the top (padT grows
> with the tier count), the old rotated bottom month labels removed, plus a `#curvesGran` granularity
> selector (Months/Quarters/Years) that re-renders without a re-fetch. The S-curve keeps its own copy
> (stable; node math re-verified for the curves: padT 64/48/32, healthy plot heights). Tests in
> `tests/web/test_curves_view.py`. No ADR. **Visual eyeball recommended** (no headless browser here).
> Next: tier-axis could later be consolidated (migrate scurve.js onto the shared module).

> ## STATUS (prev) — #213–#220 merged; Finishes hide-completed toggle in flight
>
> **`main` is green (#210–#220 merged):** S-curve/MaxFloat/SRA/AI-driving/i18n+PT + Evolution
> path-tier (#218) + Driving-Path 3-col tier panel (#219) + slack-degradation trend (#220).
>
> **OPEN draft PR (branch `claude/clever-hawking-06zdpz`, fresh on `main`): Finishes hide-completed.**
> Operator wanted show/hide completed on the Finishes views. `/api/curves?hide_complete=1` drops
> 100%-complete activities (filter on the "% Complete" field) and recomputes the curves; a
> `#curvesHideDone` checkbox on `/curves` re-fetches all three charts (Finishes/Data-date/Slippage).
> curves.js refactored to `load()`/`render()`. (Per-series multi-select already exists via the
> legend; field-level "select multiples" is available via the session-wide /groups filter.) Tests in
> `tests/web/test_curves_view.py`. No ADR.
>
> ### Parked threads (operator: "we are going to do them all") — still TODO
> Tier-axis propagation to the curves charts (stacked Y/Q/M like the S-curve); Acumen-style Executive
> Briefing (the big one — needs the Acumen format reference); condensed spacing; Step 5 (EVM3 absent);
> SSI #6 (UID_145).

> ## STATUS (prev) — #213–#219 merged; Driving-Path slack-degradation TREND in flight
>
> **`main` is green (#210–#219 merged):** S-curve fixes (#213) + Max Float→stored slack (#214;
> **confirm 275d vs Acumen**) + SRA indicator/Beta-PERT (#215) + AI driving-path "skill" (#216,
> ADR-0114) + i18n rewrite + Portuguese (#217) + Evolution path-tier selector (#218) + Driving-Path
> 3-column tier panel (#219).
>
> **OPEN draft PR (branch `claude/clever-hawking-06zdpz`, fresh on `main`): Driving-slack degradation
> trend.** On `/driving-path?target=`, below the 3-column tier panel, a per-version table
> (`_driving_tier_trend`, ≥2 versions) shows the count of activities at each driving-slack tier
> (driving 0d / secondary / tertiary) oldest→newest, with a Δ-driving movement column (▲+n red =
> slack eroding into the path, ▼ green = recovering). Reuses `compute_driving_slack`. Tests in
> `tests/web/test_driving_path_view.py`. No ADR (extends ADR-0011).
>
> ### Parked threads (operator: "we are going to do them all") — still TODO
> Driving-Path corridor ANIMATION already exists (corridor Gantt); remaining: tier-axis propagation
> to the curves charts; multi-select + show/hide-completed on the Finishes views; Acumen Exec
> Briefing; condensed spacing; Step 5 (EVM3 absent); SSI #6 (UID_145).
>
> **OPEN draft PR (branch `claude/clever-hawking-06zdpz`, fresh on `61906b6`):** chart-framework
> continuation — **per-point hover call-outs on the curves line charts** (`curves.js` `lineChart`:
> Finishes / Data-date finishes / Slippage). Same transparent per-month hit-strip pattern; each
> `<title>` lists every series' value at the hovered month. Tests in `tests/web/test_chart_callouts.py`.
> No ADR (additive chart slice).
>
> ### Chart-framework remaining (after operator eyeballs `/scurve` — no headless browser here)
> - **Per-point call-outs** still to add: evolution, SRA histogram already done; remaining line/area
>   charts (trend, cei, margin, drift, phases) as needed.
> - **Tier axis** (Year/Quarter/Month + a **day** tier) to propagate to curves/evolution — HOLD until
>   the operator confirms the S-curve tier layout looks right. Then: **totals/counts** toggle; improve zoom.
>
> ### Other open threads (each a fresh branch from `main`)
> - **Step 5 (value-ES):** still blocked — re-attach `EVM3- Detailed Metric Report.xlsx`.
> - **SSI parity (#6):** the new **UID_145** export is git-ignored on disk; needs its own validation
>   pass (UID 145 vs the golden's UID 143; does not auto-lift the `ssi_uid143` xfail).
> - Multi-select on Finishes/Data-date finishes; show-completed + hide-completed; Driving-Path
>   three-column (critical/secondary/tertiary) + animation + driving-slack-degradation trend;
>   Acumen-style Executive Briefing; condensed spacing.

> ## STATUS (prev) — Step 5 BLOCKED (EVM3 absent); shipped CUI export marking + AI-settings UX (ADR-0113)
>
> **OPEN draft PR (branch `claude/clever-hawking-06zdpz`, at `main` HEAD `cf480ed` incl. #209).**
> Build-order **Step 5 (value-based / per-activity SPI(t)) could not start: its required reference,
> `00_REFERENCE_INTAKE/audit/.../EVM3- Detailed Metric Report.xlsx`, is NOT on disk.** Per the operator's
> own gate ("if absent, STOP … do not fabricate") Step 5 is **paused, input-blocked** — to resume,
> re-attach EVM3 into the git-ignored intake. Reproducing the per-activity duration-ratio SPI(t) without
> it would mean inventing reference numbers (Law 2 violation in a testimony context).
>
> ### What shipped this session (parity-isolated; no engine/metric number touched) — ADR-0113
> - **CUI marking on every Excel + Word export (Law 1).** `reports/xlsx.py` stamps a CUI print
>   header+footer on every worksheet (after `<sheetData>`, grid untouched); `reports/docx.py` adds
>   `word/header1.xml`+`footer1.xml` referenced from `<w:sectPr>` so every page of every `.docx` —
>   incl. the narrative Diagnostic Brief (same `render_document` chokepoint) — is CUI-marked top+bottom.
>   Both stay byte-deterministic. New tests in `tests/reports/test_exports.py`.
> - **AI-settings UX:** generation-timeout **default 300→900 s** (`AIConfig` + `/settings`; 30–3600 clamp
>   unchanged); **cross-check second-model id auto-populates** on enable via vendored loopback-only
>   `static/settings.js` (never clobbers typed input; fields gained ids `primaryModel`/`secondBackend`/
>   `secondModel`); an in-app `<details>` **local-model setup guide** (`ollama pull llama3.1:8b` + tiers)
>   on the settings page; `docs/CONNECT-A-BIGGER-AI-MODEL.md` deepened (cross-check + timeout note).
> - Tests added in `tests/web/test_ai_wiring.py`; two existing assertions updated for the new
>   `id=primaryModel` markup (`test_ai_wiring.py`, `test_coverage_app_extra.py`).
> - **SRA file selection (operator order):** `/sra` now lets the operator choose which loaded file
>   the Monte-Carlo runs against (a `name=file` selector → `GET /sra?file=<key>`, persisted as
>   `SessionState.sra_file`). One resolver `_sra_selected(st)` (operator pick → else latest-solvable)
>   is shared by the page, the override POST, and `/api/sra`, so all three target the same schedule;
>   single-file sessions show no selector. Tests: `tests/web/test_sra_file_select.py` (4). No ADR.
> - **Critical-Path Evolution pan arrows (bug fix):** the ◀/▶ pan arrows were silent no-ops at the
>   default (fully zoomed-out) view because `clampView` reset any pan to the full axis. `pan()` now,
>   when fully zoomed out, jumps to the half of the axis the arrow points at (then subsequent clicks
>   slide). JS-only (`path_evolution.js`), `node --check` clean.
> - **Whole-page rescale (operator order):** a header `#uiScale` selector (90–175%) drives
>   `document.documentElement.style.zoom` via `theme.js` (applied in `<head>` before paint, persisted
>   in `localStorage` `sf-scale`). CSS `zoom` scales text + the px layout together (a root font-size
>   would miss the px rules). Tests: `tests/web/test_ui_scale.py` (2). No ADR.
> - **Chart framework — slice 1 (operator's chosen next focus): shared hover call-outs.**
>   `chartframe.js` (already frames every `.chart-host` with zoom + full-screen) now adds ONE styled
>   tooltip that shows an instant call-out for any chart shape carrying a direct `<title>` child or a
>   `data-callout` attr — instantly upgrading every title-bearing chart (scatter, trend, scurve, cei,
>   path_evolution) and giving a hook for richer text. Broadened the float histogram (was title-less)
>   to emit per-bar call-outs (count + % of population). `.cf-tip` CSS. Tests:
>   `tests/web/test_chart_callouts.py`. Extended call-outs to the **SRA** finish histogram +
>   sensitivity tornado (operator named SRA).
> - **Chart framework — slice 2: stacked time-scale tiers (S-curve).** `scurve.js` now renders the
>   time axis as a stacked **Year / Quarter / Month** header (parsing the deck's `Mon-YY` labels),
>   with a `#scurveGran` granularity selector (Months = all 3 tiers / Quarters / Years). Additive in
>   the previously-empty top area (curves/legend/data-date marker untouched), guarded fallback to a
>   flat month tier on non-standard labels. Coordinate math node-verified (no headless browser
>   available, so **a visual eyeball is recommended**). Tests in `tests/web/test_chart_callouts.py`.
>   **Remaining chart-framework slices (NOT done):** wire the tier axis into the other time charts
>   (curves, evolution, SRA histogram); a day tier for daily-data charts; totals/counts toggle;
>   per-point curve call-outs; improve the zoom.
>
> ### SSI UID_145 intake arrived (git-ignored) — NOT Step 5, NOT a trivial re-pin
> The session upload was an **SSI Analysis (UID_145) Directional Path Analysis** bundle for the current
> `Project5_TAMPERED`/`Project2` (two `.mpp` + SSI `Driving Slack`/`Drag`/`Trace Log` workbooks + `.docx`),
> now under `00_REFERENCE_INTAKE/audit/ssi_uid145/`. It is the SSI driving-slack input (backlog #6) but
> for **focus UID 145**, whereas the repo's xfail golden is **`ssi_uid143`** — so it needs its own
> validation pass and does **not** auto-lift the `ssi_uid143` xfail.
>
> ### NEXT (operator must steer / re-attach)
> - **Re-attach `EVM3- Detailed Metric Report.xlsx`** → resume Step 5 (per-activity SPI(t), ADR-0110).
> - **Large operator UI list** (separate multi-PR efforts, not yet started): SRA file-selection;
>   Exec-Summary/S-Curve scaling under many files; remove the "Quality Trend" visual (DISAMBIGUATE which
>   — /trend has a "Quality drill-down & animation" panel AND a "Schedule-quality trends" panel);
>   multi-select on Finishes/Data-date finishes; **chart time-scale tiers (years/quarters/months/days,
>   3-tier stacked axis) + a scaling control + hover call-outs + totals/counts on ALL visuals**;
>   page-wide text-size/zoom + condensed spacing; Critical-Path-Evolution zoom-arrow fix + "show
>   completed"; **Driving-Path: per-schedule selection + animation, three columns
>   (critical/secondary/tertiary) with an operator threshold, driving-slack-degradation trend**;
>   **Executive Briefing reformatted like Acumen Fuse**. Recommend sequencing the chart-framework
>   (time-scale/scaling/hover/totals) first since many asks depend on it.
> - SSI parity (#6) using the new UID_145 export; progress-scheduler (#1, ADR-0108, deferred).

> ## STATUS (prev) — Acumen full-audit campaign: Steps 1–3 MERGED; NEXT = Step 5 (value-based ES)
>
> **`main` is green and current.** Build-order **steps 1–3 are merged**: step 1 `.aft` audit
> (ADR-0110, #206), step 2 P2→P5 chain cross-version reference (ADR-0111, #207), step 3 Project5 golden
> refresh (ADR-0112, #208). The parity backbone now runs against the **authoritative** Project5 file —
> exact on every Acumen-anchored figure; the tool correctly surfaces the deleted-logic tampering; SSI
> is xfail'd pending an export. Nothing is in flight; the next session starts a fresh branch.
>
> ### NEXT — Step 5: value-based Earned Schedule (#2), reframed by ADR-0110
> Per the operator's directive (do steps 3 **and** 5; step 4 deferred), step 5 is next. ADR-0110's
> `.aft` audit found Acumen's **`SPI(t)` is NOT count-vs-value ES** — it is a **per-activity
> duration-ratio average** (a different formula of the same name), which explains the EVM2 residual
> (engine 0.27 vs Acumen 0.56). The task is to **reproduce that formula**, not generic value-ES.
> - **Source on disk:** `00_REFERENCE_INTAKE/audit/.../EVM3- Detailed Metric Report.xlsx` (per-activity
>   SPI(t) reference) — git-ignored CUI intake; confirm it is present before starting.
> - **Plan:** (1) parse EVM3 to lock the exact per-activity duration-ratio SPI(t) definition + the
>   aggregate; (2) implement in `engine/metrics/evm.py` alongside the existing Earned-Schedule SPI(t)
>   (do NOT break the current `cei_*` / EVM parity); (3) add a parity/reference test (model on
>   `tests/engine/test_evm_acumen_reference.py`, skip-when-CUI-absent); (4) ADR-0113 + refresh
>   HANDOFF/SESSION-LOG + regen `METRIC-DICTIONARY.md` if `help.py` changes; (5) full gate + draft PR.
> - **Branch fresh from `main`** (squash-merges make stacked branches conflict — CLAUDE.md workflow).
>
> ### Backlog (actionable / input-blocked)
> 4. **Progress-scheduler (#1, ADR-0108)** — deferred per operator; validate vs
>    `evm_hist2/EVM1 Forensic Analysis Report.xlsx` per-task Start/Finish (unblocked now step 3 is done).
> 6. **SSI parity** — needs an SSI driving-slack export for the current Project5 (also lifts the step-3
>    `ssi_uid143` xfail; golden left intact for a trivial re-pin).
> 7. **Confirmed-missing inputs:** SSI export (current Project5), Acumen **§E PP&Change** export
>    (current P5-vs-P2 — to cross-validate the float/critical change subset), Large-Test-File `.mpp`
>    (CEI/HMI cross-version, ADR-0111), Large Project2 source `.mpp`.

> ## STATUS (prev) — Acumen full-audit campaign, part 4: refresh stale Project5 golden (ADR-0112, MERGED #208)
>
> Build-order **step 3 — refresh the stale Project5 golden** — MERGED to `main` as #208. Steps 1
> (`.aft` audit, ADR-0110, #206) and 2 (P2→P5 chain reference, ADR-0111, #207) merged before it.
>
> ### What shipped (step 3)
> Replaced `tests/fixtures/golden/project2_5/Project5.mspdi.xml` with the MSPDI convert of the
> **authoritative** `Project5_TAMPERED.mpp` (all four intake copies are byte-identical; 4 stored-critical,
> not the stale 37 — same 379-UID structure). Re-pinned `case.json` + the golden-dependent tests:
> - **Parity gate tightened & exact** on every Acumen-anchored figure — `DCMA06` P5 now **44** (the +1
>   residual is closed for both projects), `DCMA01`=5, `DCMA05`=1, `DCMA14`=0.59/27, `critical`=4,
>   `hard_constraints`=1. §C baseline-compliance / CEI / bow-wave were unchanged by the refresh.
> - **§A `missing_logic`** recorded all-scoped (7); Acumen's incomplete-scoped Missing Logic = `DCMA01`
>   = 5 (chain-test exact). **§E change metrics** pinned to engine pure-logic CPM on the authoritative
>   file (date subset Acumen-equivalent; float/critical subset awaits an Acumen §E PP&Change export).
> - **Derived/tool goldens** (float-bands, diff, forecast, manipulation, trend, recommendations,
>   path-evolution, schedule-card, web/AI views) re-pinned to engine output on the authoritative file.
> - **SSI driving-slack** (`ssi_uid143`, `test_ssi_driving_slack_exact` + `test_golden_ssi_driving_slack_parity`)
>   marked **xfail** — its golden was SSI-validated on the prior 37-critical file and there is no SSI
>   export for the authoritative file; left untouched for a trivial re-pin when an export lands. **ADR-0112.**
>
> ### Remaining build order
> 4. **Progress-scheduler (#1, ADR-0108)** — validate vs `evm_hist2/EVM1 Forensic Analysis Report.xlsx`
>    per-task Start/Finish (step 3 now done, unblocking this per ADR-0109).
> 5. **Value-based Earned Schedule (#2)** — ADR-0110 found Acumen's SPI(t) is a per-activity
>    duration-ratio average (not value-ES); reproduce *that* formula. `EVM3- Detailed Metric Report` on disk.
> 6. **SSI parity** — needs an SSI export for the current Project5 (also lifts the step-3 xfail).
> 7. **Still missing inputs:** SSI driving-slack export (current Project5), Acumen §E PP&Change export
>    (current P5-vs-P2), Large-Test-File `.mpp` (CEI/HMI cross-version), Large Project2 source `.mpp`.

> ## STATUS (prev-2) — Acumen full-audit campaign, part 3: P2→P5 cross-version reference (ADR-0111)
>
> **OPEN PR (branch `claude/cei-hmi-cross-version`, fresh from main after #206 merged):** build-order
> **step 2 — cross-version validation**. Step 1 (`.aft` audit, ADR-0110, #206) is **merged to main**.
>
> ### What shipped (step 2)
> `tests/engine/test_chain_acumen_reference.py` — loads the P2→P3→P4→P5 source `.mpp` (fresh MPXJ
> convert) and asserts the tool reproduces Acumen's `2345 - Metric History Report` per-version values
> across the chain. **All exact**, incl. **Project3 / Project4 for the first time**:
> BEI 0.74/0.67/0.58/0.59, BEI-complete 20/24/25/27, Critical=Zero-Float 41/40/37/4, High-Float-44d
> 44/42/41/44, Hard-Constraints 0/0/0/1, Negative-Float 0/0/0/0, Missing-Logic(incomplete) 4/4/4/5,
> status serials exact. P5 High Float = exact **44** on the authoritative file (confirms ADR-0109/#204).
> Skips when intake/JVM absent (CI), runs on operator machine; NOT parity-marked (all-exact reference).
> **ADR-0111.**
>
> ### CEI/HMI cross-version is input-blocked (NOT a tool gap)
> Acumen reports **`Critical CEI` = N/A** for every snapshot of the 2345 / TP / TP4 chains (no
> consecutive-period `Previous*` linkage), and the Metric-History template has **no HMI rows**. The
> only non-N/A CEI reference (`L12` = Large-Test-File v1→v2, Critical CEI 0.19) has **no source `.mpp`
> on disk this session**. → A CEI/HMI cross-version reference test awaits the Large-Test-File `.mpp`.
>
> ### Remaining build order
> 3. **Refresh stale Project5 golden** (NEXT) — `Project5_TAMPERED.mpp` + P2-P5 Acumen exports on
>    disk; the fresh convert already reproduces Acumen exactly (44 High Float, 4 critical). Re-pin the
>    ~37 golden-dependent tests; tighten DCMA-06 Project5 to exact (ADR-0109 anticipated it).
> 4. **Progress-scheduler (#1, ADR-0108)** — validate vs `evm_hist2/EVM1 Forensic Analysis Report.xlsx`
>    per-task Start/Finish; do step 3 first (ADR-0109).
> 5. **Value-based Earned Schedule (#2)** — but ADR-0110 found Acumen's SPI(t) is a per-activity
>    duration-ratio average (not value-ES); reproduce *that* formula. `EVM3- Detailed Metric Report` on disk.
> 6. **SSI parity** — no SSI export on disk yet.
> 7. **Still missing:** Large-Test-File `.mpp` (for CEI/HMI cross-version), any SSI export, Large
>    Project2 source `.mpp` (have its Acumen reports only).

> ## STATUS (prev-3) — Acumen full-audit campaign, part 2: `.aft` Bible formula audit (ADR-0110)
>
> **OPEN draft PR (branch `claude/gracious-faraday-i3u2mw`):** build-order **step 1 — the `.aft`
> formula audit** (read-only, NO engine changes). The operator re-attached the corpus + the metric
> library `NASA Metrics_Complete_20260423.aft` (759 metrics); unpacked into git-ignored
> `00_REFERENCE_INTAKE/audit/` (nothing tracked). All uploads are confirmed **test files, NOT CUI**.
>
> ### What shipped
> `tests/engine/test_aft_formula_audit.py` — a curated correspondence table (one row per the **93**
> documented `help.py` metrics) pinning the matching NASA metric Name + **verbatim** `<Formula>`, a
> verdict, and a note. 5 tests; the formula-pinning test **skips when the `.aft` is absent** (CUI →
> CI skips, operator machine runs it). Ran green locally with the Bible on disk → every pinned NASA
> formula is verbatim-correct. **ADR-0110.** Verdict tally: **34 match / 3 variant / 4 drift / 52
> not-in-bible.**
>
> ### The 4 definitional drifts (documented, NOT fixed — feed the backlog)
> 1. **DCMA-05 Hard Constraints** — engine counts `{MSO,MFO,SNLT,FNLT}`; NASA's headline `Hard
>    Constraints` excludes SNLT/FNLT (NASA's FC-IMS variant includes them — tool follows the DCMA/
>    FC-IMS convention). Latent: no parity impact unless a schedule carries SNLT/FNLT. Same for the
>    schedule-quality `hard_constraints` twin.
> 2. **DCMA-08 High Duration** — engine keys on **baseline** duration > 44d; NASA on current
>    `OriginalDuration` > 44d **and** `ActivityType=Normal`.
> 3. **SPI(t)** — biggest find. Tool = Earned Schedule / Actual Time; Acumen's `.aft` SPI(t) is a
>    **per-activity duration-ratio average** — a different metric of the same name. Explains the EVM2
>    residual (0.27 vs 0.56) and reframes the value-based Earned-Schedule work (#2): it is not purely
>    count-vs-value ES, it is a different formula.
>
> ### Remaining build order (unchanged; steps 1 now done)
> 2. **CEI/HMI cross-version** vs `cei/CEI - Metric History Report.xlsx` (LTF→LTF2). **BLOCKED on
>    inputs:** the CEI Metric-History report **and the Large Test File `.mpp`/converts are NOT in this
>    session's uploads** — ask the operator to re-attach the CEI bundle (the kickoff's
>    `CEI__Metric_History_Report.zip`). The `.aft` Bible itself arrived via a separate upload.
> 3. **Refresh stale Project5 golden** (`Project5_TAMPERED.mpp` + P2-P5 Acumen exports ARE on disk →
>    actionable now). 37-test re-baseline; tighten DCMA-06 Project5 to exact (ADR-0109 anticipated it).
> 4. **Progress-scheduler (#1, ADR-0108)** — needs step 3 first (per ADR-0109); validate vs
>    `evm_hist2/EVM1 Forensic Analysis Report.xlsx` per-task Start/Finish.
> 5. **Value-based Earned Schedule (#2)** — `EVM3- Detailed Metric Report.xlsx` on disk; but see drift
>    #3 — Acumen's SPI(t) is a duration-ratio average, so reproduce *that* formula, not just value-ES.
> 6. **SSI parity** — still no SSI export on disk.
>
> ### Inputs status this session
> ON DISK (git-ignored `00_REFERENCE_INTAKE/audit/`): the `.aft` Bible (`cei/`), `test_files.zip`
> corpus, `evm_hist2/` (EVM1 Forensic + reports), `largeP2/`, `2345_bundle/`. **MISSING:** the CEI
> Metric-History report + Large Test File (`.mpp`/converts) needed for step 2; any SSI export.

> ## STATUS (prev) — Acumen full-audit campaign: audit results & next steps (post #203/#204)
>
> **Both prior PRs merged** (`056020d` #203 EVM goldens + ADR-0108; `8949a34` #204 High Float + ADR-0109).
> `main` is at `8949a34`. The validation campaign is **mid-stream**, not finished.
>
> ### Operator mandate (verbatim)
> Validate **every** metric the tool produces against **Acumen Fuse v8.11.0** and **SSI** on `.mpp`
> inputs. Fix **all** fidelity gaps. Then do progress-scheduler (#1, ADR-0108) + cost/value-based
> Earned Schedule (#2). "Assume nothing."
>
> ### What this session validated (all on the authoritative `.mpp` the operator supplied)
> - **Project2 / Project5_TAMPERED** vs `P2-P5 - Metric History` — engine matches Acumen on Missing
>   Logic (4/5), Hard Constraints (0/1), Critical (41/4), Zero-Float (41/4), BEI (0.74/0.59), Negative
>   Float, High Duration, Invalid Dates. **DCMA-06 High Float fix shipped (#204)** → exact 44/44.
> - **EVM1 / EVM2** vs `EVM- Metric History Report` (PR #203 already covers it). Residuals = #1, #2.
> - **Large Test File (1723 non-summary activities)** vs `Large Test File - Metric History` —
>   **matches Acumen on every metric checked** (Missing Logic 22, Logic Density™ 3.14, Critical 33,
>   Hard Constraints 1, Negative Float 31, Insufficient Detail™ 43, Number of Lags 8, Leads 1).
> - **`.aft` Bible look-up settled an apparent inconsistency:** NASA's verbatim Missing Logic formula
>   is `SUM(((NoPreds & Start>=_PeriodStart) | (NoSucs & Finish<=_PeriodFinish))*1)` — period-windowed,
>   so "full-project" when run normally (LTF=22) and "to-go" when run from status (EVM2=1). The tool
>   already produces both: `schedule_quality.missing_logic` (full) and `DCMA01` (incomplete-only).
>
> ### KEY FINDING (still pending action)
> Committed **`tests/fixtures/golden/project2_5/Project5.mspdi.xml` is STALE** — the current
> `Project5_TAMPERED.mpp` has **4** stored-critical activities (= Acumen); the golden has **37**. A
> blast-radius measurement was run (golden swapped in → suite run → reverted): **37 tests fail.**
> Refreshing requires re-pinning trend / manipulation / web / parity values against the current
> Acumen exports (a deliberate re-baseline). Until refreshed, Project5's High Float stays a +1
> residual (engine 40 vs stale golden 41) and the parity gate documents why (ADR-0109).
>
> ### Reference corpus on disk — **DO NOT LOSE; all git-ignored**
> Read-only under `00_REFERENCE_INTAKE/audit/`:
> - `p2p5/` — `Project2.mpp`, `Project5_TAMPERED.mpp`, + Acumen DCMA / Metric-History / Detailed /
>   Quick-Add. Already audited.
> - `cei/` (**this session's biggest delivery**) — `Large Test File.mpp` / `Large Test File2.mpp`,
>   `Project2/3/4/5_TAMPERED.mpp`, `Project2(Duration Bomb).mpp`, EVM1/2 `.mpp`, the `TP*` suite
>   (`TP1..TP4_DataCenter_v1..v5`), `CEI - Metric History Report.xlsx` (cross-version LTF↔LTF2),
>   `Workbook1 - DCMA Report.xlsx`, **and `NASA Metrics_Complete_20260423.aft` — the Bible (763
>   metrics, verbatim formulas).**
> - `evm_hist2/` — `EVM- Metric History Report.xlsx`, `EVM1 Forensic Analysis Report.xlsx` (carries
>   Acumen's **per-task** Start/Finish/Early-Start/Early-Finish — the ground truth the
>   progress-scheduler #1 needs to model & validate against), Quick-Add, Detailed.
> - `largeP2/` — Acumen reports for "Large Project2" (source `.mpp` NOT supplied — can't validate yet).
> - `tp1/` — duplicate of the source `.mpp` set (overlaps `cei/`).
> - Fresh MPXJ-converted MSPDI XML co-located: `Project2_fresh.xml`, `Project5_fresh.xml`,
>   `LargeTestFile.xml` (the converter command is in CLAUDE.md).
>
> ### Confirmed-missing inputs (not blocking, but extend coverage)
> 1. Source `.mpp` for **Large Project2** (have its Acumen reports but no schedule).
> 2. Acumen reports for **Project3, Project4, Project2(Duration Bomb)** and the **TP1..TP4** suite —
>    the operator offered to generate them; preferred runs (decided this session):
>    - **Project2→3→4→5** as one workbook with each version a snapshot → Metric History Report
>      (unlocks CEI/HMI/BEI/FEI on the manipulation series).
>    - **TP4_DataCenter v1→v5** same treatment.
>    - **TP1/TP2/TP3** as separate-project runs (DCMA + Detailed each).
> 3. **Any SSI export** — the operator mandate names "SSI and Acumen Fuse"; only Acumen is on disk.
>
> ### Remaining work in priority order (this session's recommendation)
> 1. **`.aft` formula audit** (safest, highest value): for each of the tool's ~90 metrics in
>    `web/help.py`, parse the matching `<Metric>` from `NASA Metrics_Complete_20260423.aft` and assert
>    the tool's formula matches NASA's. Surfaces any hidden definitional drift before any engine
>    change. **No engine changes; tests only.**
> 2. **CEI/HMI cross-version validation** against `cei/CEI - Metric History Report.xlsx`
>    (Large Test File → Large Test File2 — the first cross-version reference on hand).
> 3. **Refresh the stale Project5 golden** — re-pin the 37 failing tests against the current Acumen
>    values; this is a re-baseline PR with `[golden refresh]` in the title, requires care.
> 4. **Progress-scheduler (#1, ADR-0108)** — now buildable. Validate against `EVM1 Forensic Analysis
>    Report.xlsx` per-task Start/Finish and the refreshed P5 golden (so prior failed-attempt symptoms
>    on P5 can be re-judged against a real reference).
> 5. **Cost/value-based Earned Schedule (#2)** — closes the SPI(t) residual on EVM2 (0.27→0.56).
> 6. **SSI parity** once any SSI export arrives.
>
> ### Gate green at end of this session
> Branch `claude/affectionate-mendel-t319hp` cleaned up after merges; `main` HEAD = `8949a34`. Full
> suite 1436 passed / 3 env-skips, **parity 10/10**, drift guard green. No staged or untracked
> changes outside the git-ignored intake.

> ## STATUS (prev) — Acumen full-audit campaign: DCMA-06 High Float fix + stale Project5 golden (ADR-0109)
> Operator supplied two **cost-loaded** test schedules (EVM1/EVM2 — test files, NOT CUI) + the Acumen
> Fuse export. Validated the tool against Acumen's Metric History: the **majority of metrics match**
> (Critical 10/8, hard/neg/high float 0, all-FS, BEI 0/0.25, DCMA-01 logic 2/1, EVM1 finish 09-12),
> **including this session's new checks** (Estimated Duration, Unsatisfied Constraints, Missing WBS —
> all 0/0). **OPEN PR (this branch):** committed `EVM1/EVM2` as MSPDI golden fixtures
> (`tests/fixtures/golden/evm/`) + `tests/engine/test_evm_acumen_reference.py` (pins the matches,
> documents the residuals). **ADR-0108.**
> - **The one real fidelity gap (documented residual, NOT fixed):** EVM2 finish 10-01 vs Acumen
>   10-04 → Net Finish Impact −19 vs −22, because the CPM schedules an in-progress task at
>   `start + full duration` instead of rescheduling its **remaining** from the **data date** (MS
>   Project progress override). **Two localized fix attempts regressed EVM1 AND broke Project2/5
>   parity** — MSP reschedules only when *behind*, an ahead/behind call I can't reverse-engineer
>   safely from two points (Law 2). Reverted; engine at validated baseline. A correct fix needs a
>   faithful progress-scheduler validated against MSP per-task Start/Finish (in the Forensic report) —
>   a dedicated effort, ideally with the Project2/5 Acumen exports to re-validate parity.
> - **Related follow-on:** cost/value-based Earned Schedule (Acumen SPI(t) 0.56 vs tool count-based
>   0.27); the `missing_logic` quality metric counts completed tasks (DCMA-01 already matches Acumen).
> - Gate green: ruff/format/mypy(strict)/bandit/node clean; full suite **1436 passed / 3 env-skips**;
>   **parity 10/10** (engine untouched). Reference files read-only under git-ignored `00_REFERENCE_INTAKE/evm/`.

> ## STATUS (prev) — Total-float distribution histogram (handbook §6.3.2.5.2.2; last D6 sub-item)
> The handbook D-list is fully merged (D1-D4, D6-D10 via #190-#201). This adds the remaining D6
> chart-component sub-item. **OPEN PR (this branch):** `static/histogram.js` + `_float_histogram_panel`
> on /analysis — bins each non-summary activity's `total_float_days` into DCMA-aligned bands
> (`< 0` / `0` / `1-5` / `6-10` / `11-20` / `21-44` / `> 44`), reusing the same `/api/analysis/<name>`
> activity rows the scatter uses (client-side binning; no engine numbers; air-gap kept; sr-only data
> table). Mass at 0/<0 = critical-and-behind core; a `> 44 d` spike = float padding / missing
> successor logic (DCMA-06). Tests: `tests/web/test_histogram.py` (2). Gate green:
> ruff/format/mypy(strict)/bandit/node clean; full suite **1430 passed / 3 env-skips**; coverage
> 70/85 satisfied. **No new ADR.**
> - **Remaining (small follow-ons):** stoplight rendering on the other panels; float-erosion
>   cross-version trend. **Deferred/blocked (need operator inputs):** D5/TFCI (a reference Acumen/
>   handbook export to validate the forecast-date sign), SRA cost-loaded JCL (cost data). The core
>   handbook extension plan is complete — a good point to ask the operator for the next priority.

> ## STATUS (prev) — Estimated-Duration importer field (plan D10 COMPLETE)
> The final D10 item, after vertical-integration merged (#200). **OPEN PR (this branch):** a model +
> importer + check change — `Task.is_estimated_duration` (model field) read from the MSPDI
> `<Estimated>` element (`mspdi._parse_task`), surfaced as an "Estimated (placeholder) durations"
> structural health check in `health_extra` (non-summary, non-milestone activities still flagged
> Estimated = a not-yet-firmed placeholder). The schema-freeze guard (`test_schema_freeze`) was
> updated for the new field. Tests: `test_health_extra.py` (+2) + `test_mspdi.py` (+1). Gate green:
> ruff/format/mypy(strict)/bandit/node clean; full suite **1428 passed / 3 env-skips**; coverage
> 70/85 satisfied. **No new ADR.**
> - **Handbook D-list COMPLETE:** D1–D4, D6–D10 shipped. **Deferred:** D5/TFCI (needs a reference
>   export to validate the forecast-date sign), SRA cost/JCL (needs cost inputs). **Smaller
>   follow-ons:** histogram chart component (D6 sub-item), stoplight on the other panels, float-erosion
>   cross-version trend. Good point to ask the operator for the next priority.

> ## STATUS (prev) — Inconsistent-vertical-integration check — plan D10 (constraint checks merged #199)
> After the constraint/deadline checks merged (#199), this is the next D10 slice. **OPEN PR (this
> branch):** `engine/metrics/vertical_integration.py` `compute_vertical_integration(schedule)` —
> parity-isolated `VerticalIntegration` dataclass (out of the Fuse ribbon and the metric-dictionary
> test). Flags **summaries whose stored date span does not envelope their WBS descendants** (parent
> starts after its earliest child, or finishes before its latest), deriving hierarchy from WBS-prefix
> nesting and comparing **stored** dates only — exactly verifiable against the file, no CPM. Summaries
> with no WBS code / no stored dates / no dated descendants are *not evaluable* and skipped. Surfaced
> as a "Vertical integration" panel on /analysis (next to Constraint health). Tests:
> `tests/engine/test_vertical_integration.py` (7) + `tests/web/test_vertical_integration_panel.py` (2).
> Gate green: ruff/format/mypy(strict)/bandit/node clean; full suite **1426 passed / 3 env-skips**;
> coverage 70/85 satisfied. **No new ADR.**
> - **D10 remaining:** only the **Estimated-Duration importer field** (MS Project "Estimated" duration
>   flag → model field + MSPDI importer support + a placeholder-duration health check). Other
>   follow-ons: stoplight on the other panels, float-erosion cross-version trend. **Deferred/blocked:**
>   D5/TFCI (reference export to validate the forecast-date sign), SRA cost/JCL (cost inputs).
>   Handbook D-list now: D1-D4, D6-D9 done; D10 nearly done (only the importer field left).

> ## STATUS (prev) — Constraint-health checks (unsatisfied constraint + deadline neg-float) — plan D10
> The first slice of D10, after D9 completed (#198 merged). **OPEN PR (this branch):**
> `engine/metrics/constraint_health.py` `compute_constraint_health(schedule, cpm)` — parity-isolated
> `ConstraintCheck` / `ConstraintHealth` dataclasses (out of the Fuse ribbon and the metric-dictionary
> test, like `health_extra`/`logic_integrity`/`float_erosion`/`evm.ScheduleVariance`). Two checks, both
> comparing the trusted CPM early dates to the activity's own imposed date (exactly verifiable):
> **Unsatisfied date constraints** (hard SNLT/MSO vs early start, FNLT/MFO vs early finish — MSO/MFO are
> solver-pinned so a conflicting must-date surfaces as negative float, DCMA-07) and **Deadlines breached**
> (early finish > a set deadline = artificial negative float). Surfaced as a "Constraint health"
> stoplight panel on /analysis (next to Logic integrity). Tests:
> `tests/engine/test_constraint_health.py` (8) + `tests/web/test_constraint_health_panel.py` (2). Gate
> green: ruff/format/mypy(strict)/bandit/node clean; full suite **1417 passed / 3 env-skips**; coverage
> 70/85 satisfied. **No new ADR.**
> - **D10 remaining:** Inconsistent Vertical Integration (hierarchy rollup); Estimated-Duration importer
>   field (model/importer change). Other follow-ons: stoplight on the other panels, float-erosion
>   cross-version trend. **Deferred/blocked:** D5/TFCI (reference export to validate the forecast-date
>   sign), SRA cost/JCL (cost inputs). With this, the handbook D-list is D1-D4, D6-D9 done + D10 partial.

> ## STATUS (prev) — Reliability-Dimension tags (plan D9 complete) — handbook framework overlay
> The nav regroup merged (#197); this finishes D9. **OPEN PR (this branch):**
> `help.reliability_dimension(metric_id)` tags every documented metric with the NASA handbook
> reliability dimension it most informs — **Comprehensiveness / Construction / Realism /
> Affordability** — via one auditable family-level mapping (cost EVM → Affordability; resource/
> census/network-completeness → Comprehensiveness; logic/constraint/float quality → Construction;
> everything else, the execution-performance bucket → Realism). Surfaced as a **Dimension** column on
> `/help` and in the regenerated `docs/METRIC-DICTIONARY.md`. Presentation-only organizational lens —
> engages no parity number. Tests: `test_reliability_dimension_tags_every_documented_metric` +
> `test_reliability_dimension_family_assignments` (`tests/web/test_help.py`). Gate green:
> ruff/format/mypy(strict)/bandit/node clean; full suite **1407 passed / 3 env-skips**; coverage
> 70/85 satisfied. **No new ADR. Plan D9 DONE.**
> - **Handbook D-list status:** D1-D4, D6-D9 shipped. **Remaining:** D10 (unsatisfied-constraint /
>   deadline-neg-float check → vertical-integration → estimated-duration importer field); smaller
>   follow-ons (stoplight on the other panels, float-erosion cross-version trend). **Deferred/blocked:**
>   D5/TFCI (needs reference export to validate the forecast-date sign), SRA cost/JCL (needs cost).

> ## STATUS (prev) — Handbook-framed nav regrouping (plan D9, partial) — Reliability tags remain
> The nav slice of D9 (the last big plan item). **OPEN PR (this branch):** the top nav is regrouped
> into the handbook's sub-functions (section C) as labeled clusters — **Overview / Assessment /
> Control / Risks / Reporting / Setup** — each a `<span class=nav-group>` with a
> `<span class=nav-grp-label>`. **Every existing route, href, and link label is preserved** (anchors
> unchanged → all nav-dependent tests stay green; no broken bookmarks). CSS `.nav-group` /
> `.nav-grp-label` in `base.css`. Test: `test_nav_is_grouped_by_handbook_function`
> (`tests/web/test_app.py`). Gate green: ruff/format/mypy(strict)/bandit/node clean; full suite
> **1405 passed / 3 env-skips**; coverage 70/85 satisfied. **No new ADR.**
> - **D9 remaining (follow-on):** per-metric **Reliability-Dimension** tags in `help.py`
>   (Comprehensiveness / Construction / Realism / Affordability). After that the handbook-plan D-list
>   is essentially complete except deferred items: D5/TFCI (needs reference export to validate the
>   forecast-date sign), float-erosion cross-version trend, stoplight on the other panels, D10
>   (unsatisfied-constraint / vertical-integration / estimated-duration importer field), SRA cost/JCL.

> ## STATUS (prev) — DCMA-14 stoplight / tripwire board (Figs 7-10..7-38) — plan D8
> After D7 merged (#195). **OPEN PR (this branch):** `_stoplight_board(audit.checks)` renders the
> DCMA-14 checks as a strip of green-PASS / red-FAIL / grey-N/A chips (value+unit, threshold in the
> tooltip) above the detailed audit table on /analysis — the handbook's canonical at-a-glance
> presentation. Pure presentation over the existing `AuditCheck.status` (no new thresholds/numbers).
> CSS `.stoplight-board` / `.sl-chip` / `.sl-pass|fail|na` in `base.css`. Test:
> `test_analysis_shows_dcma_stoplight_board` (`tests/web/test_app.py`). Gate green:
> ruff/format/mypy(strict)/bandit/node clean; full suite **1404 passed / 3 env-skips**; coverage
> 70/85 satisfied. **No new ADR.**
> - **Next:** D9 handbook-framed nav reorganization (the last big plan item); follow-ons — extend the
>   stoplight board to the other panels, float-erosion cross-version trend, and (when a reference
>   export exists to validate the sign) D5/TFCI. SRA cost/JCL still blocked on cost inputs.

> ## STATUS (prev) — Float erosion by WBS (Figs 7-34/7-35) — plan D7; D5/TFCI deferred
> After D4 completed (#194 merged), D5 (TFCI forecast) was **deferred**: its forecast-finish
> reconstruction has an ambiguous sign convention that can't be validated against a reference export
> in the air-gapped env — shipping an unvalidated forecast date would violate Law 2. Picked up **D7
> instead. OPEN PR (this branch):** `engine/metrics/float_erosion.py`
> `compute_float_erosion(schedule, cpm)` — parity-isolated `WBSFloat` / `FloatErosion` dataclasses
> (out of the Fuse ribbon and the metric-dictionary test, like `health_extra`/`logic_integrity`/
> `margin`/`evm.ScheduleVariance`). Per-top-level-WBS minimum & average **total float** (working
> days, progress-aware via `effective_total_float` — stored Total Slack preferred for Acumen parity),
> critical-activity count, and a stoplight on the group's minimum float (red < 0 / amber 0–10 wd /
> green > 10 wd). Surfaced as a "Float erosion by WBS" panel on /analysis (project-min/groups/eroded
> cards + per-WBS table). Tests: `tests/engine/test_float_erosion.py` (7) + `tests/web/
> test_float_erosion_panel.py` (2). Gate green: ruff/format/mypy(strict)/bandit/node clean; full
> suite **1403 passed / 3 env-skips**; coverage 70/85 satisfied. **No new ADR.**
> - **Next:** D8 stoplight rendering of existing metrics; D9 handbook nav reorg; float-erosion
>   cross-version trend (D7 follow-on). D5/TFCI awaits a reference export to validate the sign. SRA
>   cost/JCL still blocked on cost inputs.

> ## STATUS (prev) — Cross-version SV/SVt trend (Figs 7-12/7-13) — **plan D4 COMPLETE**
> The last D4 item, after the SVt metric (#192) and combined BEI/CEI/HMI panel (#193, both merged).
> **OPEN PR (this branch):** a zero-baselined SVt trend across versions. `trend.js` gains
> `varianceTrendChart(title, labels, values, desc, unit)` — a signed chart with a dashed zero line,
> faint favorable (≥0, ahead) / unfavorable (<0, behind) bands, sign-colored markers/labels, y-axis
> hi/0/lo ticks, legend, and an sr-only data table. `_trend_data` now emits `svt_days` per version
> (from the merged `compute_schedule_variance`), and the render overlays the SVt trend after the
> combined execution chart. Test: `test_trend_carries_svt_and_js_has_variance_trend`
> (`tests/web/test_trend_views.py`). Gate green: ruff/format/mypy(strict)/bandit/node clean; full
> suite **1394 passed / 3 env-skips**; coverage 70/85 satisfied. **No new ADR. Plan D4 done.**
> - **Next:** D5 TFCI / Predicted CPTF / TFCI forecast-finish (4th method in `engine/forecast.py`);
>   then D7 float-erosion-by-WBS; D8 stoplight rendering; D9 handbook nav reorg. SRA cost/JCL still
>   blocked on cost inputs.

> ## STATUS (prev) — Combined BEI/CEI/HMI execution panel (handbook Fig 7-21) — plan D4 follow-on
> The next D4 follow-on after the SVt metric (#192, merged). **OPEN PR (this branch):** a single
> overlaid trend chart of the three headline execution indices — **BEI** (cumulative baseline
> execution), **CEI** (this-period forecast execution), **HMI** (this-period baseline execution) —
> the handbook's combined "are we executing the plan?" panel (Fig 7-21). Pure presentation in
> `static/trend.js` (`execSeries` → `multiLineChart`, placed before the existing per-family index
> charts); the `/api/trend` payload already carried `bei` / `cei_tasks` / `hmi_tasks` per version, so
> no engine/route change. Test: `test_trend_js_has_combined_execution_index_chart` in
> `tests/web/test_trend_views.py`. Gate green: ruff/format/mypy(strict)/bandit/node clean; full suite
> **1393 passed / 3 env-skips**; coverage 70/85 satisfied. **No new ADR.**
> - **D4 remaining:** the cross-version **SV/SVt trend** with favorable/unfavorable bands (Figs
>   7-12/7-13). Then D5 TFCI forecast; D7 float-erosion-by-WBS; D8 stoplight rendering; D9 nav reorg.
> - **NOTE:** the GitHub MCP server disconnected mid-session — this PR may need to be opened once it
>   reconnects (branch is pushed). SRA cost/JCL still blocked on cost inputs.

> ## STATUS (prev) — Schedule variance in time (SVt = ES − AT) — handbook plan D4 (partial)
> Next deterministic handbook tranche (the SVt half of plan D4). **OPEN PR (this branch):**
> `evm.compute_schedule_variance(schedule, tasks)` — parity-isolated `ScheduleVariance` /
> `ActivityVariance` dataclasses (NOT `MetricResult`; out of the Fuse ribbon and metric-dictionary
> test, like `health_extra`/`logic_integrity`/`margin`). Project **SVt = ES − AT** in working days
> (reuses the canonical `earned_schedule`, so it can never diverge from SPI(t); `>= 0` ahead/
> favorable, `< 0` behind) with its ES/AT components, plus per-activity finish variance
> (actual − baseline finish on the calendar, working days; positive = late). Surfaced as a
> "Schedule variance (time)" panel on /analysis (favorable/unfavorable read, components,
> largest-finish-variance table; graceful "not computable" when no status date / completions /
> baselines). Tests: `tests/engine/test_schedule_variance.py` (6) + `tests/web/
> test_schedule_variance_panel.py` (3). Gate green: ruff/format/mypy(strict)/bandit/node clean; full
> suite **1392 passed / 3 env-skips**; coverage 70/85 satisfied. Plan D4 marked partial. No new ADR.
> - **D4 follow-ons:** combined BEI/CEI/HMI panel (Fig 7-21); cross-version SV/SVt trend with
>   favorable/unfavorable bands (Figs 7-12/7-13). Then D5 TFCI forecast; D7 float-erosion-by-WBS; D8
>   stoplight rendering; D9 handbook nav reorg. SRA cost/JCL still blocked on cost inputs.

> ## STATUS (prev) — Logic-integrity checks (out-of-sequence + redundant logic) — handbook plan D3
> Next deterministic handbook tranche after the SRA epic. **OPEN PR (this branch):**
> `engine/metrics/logic_integrity.py` `compute_logic_integrity(schedule)` (parity-isolated
> `LogicCheck` dataclasses, like `health_extra` — out of the Fuse ribbon and DCMA audit; no CPM
> needed). Two checks: **out-of-sequence** (an FS successor that recorded progress before its
> predecessor finished — `succ.actual_start < pred.actual_finish`, or pred has no recorded finish
> while succ already started; the classic status-override signature) and **redundant logic** (a
> direct `A→C` a longer `A→…→C` path already implies — iterative reverse-topological transitive
> closure so a long chain can't overflow the stack; reported *not evaluated* on a cyclic or oversize
> network). *Circular logic was intentionally dropped:* CPM refuses a cyclic network, so the panel —
> which renders only after CPM solves — would always read zero. Surfaced as a "Logic integrity"
> stoplight panel on /analysis beside the structural health checks (offenders written
> `pred→succ` by UniqueID). Tests: `tests/engine/test_logic_integrity.py` (13, incl. a 1500-deep
> chain proving no recursion overflow) + `tests/web/test_logic_checks.py` (2). Gate green:
> ruff/format/mypy(strict)/bandit/node clean; full suite **1383 passed / 3 env-skips**; coverage
> 70/85 satisfied. Plan D3 marked done in `docs/HANDBOOK-EXTENSION-PLAN.md`. No new ADR.
> - **Next deterministic tranches (plan D):** D4 SVt + combined BEI/CEI/HMI + SV/SVt panels; D5 TFCI
>   forecast; D7 float-erosion-by-WBS; D8 stoplight rendering; D9 handbook nav reorg. SRA cost/JCL
>   (A3 tail) still blocked on cost inputs.

> ## STATUS (prev) — SRA discrete-risk **register UI** on /sra (ADR-0106 follow-on; engine #189 merged)
> The discrete risk-driver engine landed in #189 (`RiskEvent`, `RiskDriver`, `compute_sra(…, risks=())`,
> `SRAResult.risk_drivers` — probability × triangular multiplicative impact, shared-driver emergent
> correlation). **OPEN PR (this branch):** the analyst-facing register on **/sra**. `SessionState.sra_risks`
> (+ `sra_risk_seq` for stable ids) holds the register; **`POST /sra/risk-event`** adds (name, probability %,
> 3-point impact %, affected UIDs — validated against the latest solvable schedule, dangling/summary uids
> dropped, ordered lo≤ml≤hi, prob clamped 0–1), removes one (`remove=id`), or clears all (`clear=1`);
> `/api/sra` now passes `risks=tuple(st.sra_risks)` to `compute_sra` and `_sra_data` emits a `risk_drivers`
> array (id/name/probability/hits/iterations/delta_days). UI: a "Risk register" panel (input form + register
> table + Remove/Clear) and a **risk-driver tornado** (`#sraRisk` in `sra.js`, mean finish slip per risk,
> red=slip/green=pull-in, +table) that is empty until a risk is registered. Wipe clears the register. New
> tests `tests/web/test_sra_risks.py` (13). Gate green: ruff/format/mypy(strict)/bandit/node clean; full
> suite 1368 passed / 3 env-skips; coverage gate 70/85 green.
> - **Next SRA:** cost-loading for true JCL (needs cost inputs). Then deterministic handbook tranches.

> ## STATUS (prev) — Schedule-margin metrics (ADR-0107); SRA fully shipped (engine+results+manual, ADR-0106)
> Operator gave the margin convention: **a schedule-margin task = any non-summary activity with "margin"
> in its name** (case-insensitive). **ADR-0107 (OPEN PR):** `engine/metrics/margin.py` `compute_margin`
> (lightweight dataclasses, parity-isolated) = total margin (working days) + **effective margin** (how far
> the finish pulls in if all margin is zeroed — reuses the ADR-0106 `compute_cpm(duration_overrides=…)`
> counterfactual, so no divergence from the deterministic numbers) + per-task on-critical; surfaced as a
> "Schedule margin" panel on /analysis (graceful "none found" when a schedule has no margin tasks). Margin
> **burndown across versions** is the next tranche. This PR also folds in the SRA parse-helper tests
> (cover `_to_float`/`_clamp_float`) left over from #186.
> - **SRA / Monte-Carlo COMPLETE & merged (ADR-0106):** #184 engine (`engine/sra.py`, seeded, reuses
>   `compute_cpm` via `duration_overrides`, validated == compute_cpm), #185 results page (/sra — confidence
>   S-curve + P10/50/80/90 + deterministic-vs-percentile gap, histogram, Spearman tornado/SSI, criticality),
>   #186 manual inputs (global Quick-Risk % + per-activity 3-point overrides; auto path = screening default,
>   labeled not-SME-validated). JCL deferred (needs cost). Next SRA: discrete-risk drivers + correlation.
> - **Also shipped this session (merged):** #177 Risks/Briefing "won't open" fix (async AI polish); #178/#180
>   Mission Control (evolution tile, lockstep play-all, uniform tiles + enlarge/shrink, S-Curve date); #179
>   Year-Phases animated; #181 handbook-extension plan; #182 scatter plot; #183 structural health checks.
> - **Remaining roadmap:** margin burndown; SRA discrete risks/correlation → cost/JCL; deterministic handbook
>   tranches (SVt + BEI/CEI/HMI panel, TFCI forecast, float-erosion-by-WBS, stoplight, nav reorg); restore
>   coverage to the 99.9 intent (drifted to ~99.66% via this session's defensive web branches; CI gate 70/85
>   is green). Full catalogue: `docs/HANDBOOK-EXTENSION-PLAN.md`.

> ## STATUS (post-#184) — Schedule Risk Analysis (Monte-Carlo) chartered & designed (ADR-0106)

> ## STATUS (current) — Schedule Risk Analysis (Monte-Carlo) chartered & designed (ADR-0106); engine building
> Operator chartered an SRA / Monte-Carlo module with BOTH a manual-input path and an AUTO "industry best
> practice" path. **ADR-0106** captures the source-cited design: triangular default on REMAINING duration,
> auto-default Min 90% / ML 100% / Max 110% (Deltek "Realistic", right-skewed; labeled a screening
> placeholder, not SME-validated, overridable); discrete risks = Bernoulli×triangular multiplicative
> (none auto unless a register is supplied); correlation never zero-without-warning (shared-driver emergent
> or ~0.3 default); 1000 iters (→10000), seeded `random.Random(base+i)`; outputs = finish CDF + P10/50/80/90,
> deterministic-vs-probabilistic gap, Criticality Index (% iters on the critical path, TF≤0), Spearman
> tornado, SSI = (σ_act×CI)/σ_proj; JCL deferred (needs cost — duration-only = SCL). Engine `engine/sra.py`
> is parity-isolated and validated against `compute_cpm` (deterministic most-likely run == compute_cpm
> finish). Staged: (1) engine+auto+outputs (this PR), (2) results page + animated visuals, (3) manual-input
> model fields + UI, (4) discrete risks/correlation, then cost-loading for true JCL. Verified sources:
> GAO-16-89G, NASA SP-2010-3403 / NPR 7120.5F / CEH App. J, AACE 57R-09, Vanhoucke/PMBOK, Deltek/Primavera/
> Safran. Full deck/handbook plan in `docs/HANDBOOK-EXTENSION-PLAN.md`.
> - **Shipped earlier this session (all merged):** #177 Risks/Briefing "won't open" fix (async AI polish);
>   #178/#180 Mission Control (evolution tile, lockstep play-all incl. overview lines, uniform tiles +
>   enlarge/shrink, S-Curve data date); #179 Year-Phases animated; #181 handbook-extension plan; #182
>   scatter plot; #183 structural health checks (handbook Fig. 6-9).

> ## STATUS (post-#176) — Target UID = analysis ENDPOINT (whole tool) + quantified 5×5 risk matrix (ADR-0105)
> Operator: (1) entering a UID in the top ribbon must apply to EVERY page with all metrics/visuals
> recomputed using the target as the endpoint — activities that don't drive it omitted; (2) the Risks page
> needs a quantified 5×5 (likelihood × impact) matrix + ranking. **OPEN PR (this branch, ADR-0105).**
> Endpoint rule chosen by the operator = **"target + its drivers"** (`path_trace.subschedule_to_target` =
> `ancestors_of(target) ∪ {target}`, frame preserved like `filter_schedule`), folded into the **one scope
> chokepoint** `SessionState.scope()` (so `analysis_for()` + `ordered()` carry it to every page/version);
> `set_target()` invalidates caches; a page-top **"Analysis endpoint: UID X (N omitted)"** banner everywhere;
> default (no target) is a no-op so **parity stays locked**. Risk scoring: `recommendations.Likelihood` +
> deterministic CPM-cited `_quantify` (float_days / impact_days exposure / driving_float_days when targeted /
> likelihood / impact_score·likelihood_score → risk_score 1–25); `/risks` renders a server-rendered 5×5
> heat-map (accessible table) + score-ranked list + per-finding quantified reads, AI narrative on top. Gate
> green: ruff/format/mypy(strict)/bandit/node clean; full suite passing (incl. new path_trace / target-endpoint
> / risk-matrix tests); parity 10/10. Earlier this day merged: a11y data tables + AI-model guide (#173),
> NASA-theme overhaul (#174), insignia vertical-axis spin (#175).

> ## STATUS (current) — test coverage raised to 99.9% (actual 99.97%); gate locked at fail_under=99.9
> Operator: improve coverage to 99.9%. From `main`@#171 (99.05%) a sub-agent cleared the engine/AI branch
> misses while the remaining `web/app.py` branches were covered in one new file
> (`tests/web/test_coverage_app_extra.py`, 26 tests): AI-status/second-backend/translate helpers, the
> forecast-ruler / WBS / DCMA-tooltip / counterfactual / briefing / settings / watchdog render helpers, the
> export-path / ask / translate / groups route guards, and the path-evolution & driving-corridor
> absent-from-version / "left the corridor" branches. `[tool.coverage.report] fail_under` 99 → 99.9. Full
> gate green: ruff/format/mypy(strict)/bandit/node clean; **1213 passed, 3 skipped**; overall **99.97%**
> (≥99.9 exit 0), engine ≥85 exit 0; deterministic across two runs. Two residual lines are genuinely
> dead/defensive (`forecast.py:90→98` — `months_to_go` can't be None once reached; `app.py:2944` —
> `day(None)` reachable only with neither a stored date nor a CPM timing). No new ADR (tests + gate bump).
> Earlier merged this day: coverage→99% + 20× QC (#171); session-wide Groups & Filters ADR-0104 (#168);
> CLAUDE.md onboarding (#169); empty-scope briefing/narrative 500 fix (#170).

> ## (prior) STATUS (post-#167) — Groups & Filters now scope the WHOLE tool (every page, every file)
> Operator: a filter chosen on the Groups tab must apply to every metric on every page, across all
> loaded project files (it was `/groups`-only + one version before). OPEN PR (this branch, **ADR-0104**):
> `SessionState.active_filter` + `scope()`/`set_filter()` (identity-stable scope cache, invalidated on
> change); `analysis_for` scopes internally (single-page views unchanged) and `ordered()` returns the
> scoped list the direct multi-version views (bow-wave/CEI, S-curve, curves) + `_solvable_versions`
> iterate; `ordered_versions()` stays raw for the filter UI. `/groups` gains **Apply to all pages** /
> **clear filter** (a bare row selection still previews without persisting), union field/value pickers
> across all files (`available_fields_union`/`distinct_values`), a per-file reach table, and a page-top
> **"Filter active"** banner on every page. Wipe clears it. Tests: session-level cross-file scoping +
> cache invalidation, and web apply/clear/preview/per-file/union behaviour. Gate green.
> - Earlier (now merged): Float Ratio™ #165 (ADR-0103); qc-checker subagent #166 + throttled
>   SessionStart QC trigger #167 (registering the hook in `.claude/settings.json` is left to the human —
>   the assistant is barred from editing its own startup config).

> ## (prior) STATUS (post-#164) — Float Ratio™ BUILT; the backlog has no blocked items left
> The operator asked to figure out Float Ratio and build a formula that works **period to period** — the
> one metric long marked "blocked, no formula." It was never unbuildable: the Bible (`.aft`) carries an
> explicit `<Metric Name="Float Ratio™">` with `<Formula>AVERAGE(TotalFloat / RemainingDuration)</Formula>`
> over Normal planned/in-progress activities. OPEN PR (this branch, **ADR-0103**): new
> `engine/metrics/float_ratio.compute_float_ratio` returns both Bible forms — `float_ratio` (mean of
> per-activity ratios, threshold-bearing, cites <0.1 offenders) and `float_ratio_aggregate` (ratio of
> means). `trend.compute_float_ratio_trend` scores each version and carries the period-over-period
> **delta**; surfaced on /trend ("Float Ratio™ across periods" chart) + per-version indices + metric
> dictionary + i18n term. Validated: formula verbatim from Bible; hand-computed unit tests (both forms,
> population, fallback, division guard, negative float, delta); **real-schedule denominator cross-check —
> the population's avg remaining duration = 18.4 wd ≈ Acumen's reported Avg. Remaining Duration ~18**
> (Acumen never exports Float Ratio itself, so this is the external anchor).
> - ALL Acumen metrics now built + validated: HMI exact, BEI 0.51 exact, CEI 0.19/0.17 + variants
>   (0.10/0-3/0.22) exact, FEI (components exact; ratios within mpxj tolerance), BRI 0.51 exact, Float
>   Ratio™ (Bible formula; denominator cross-checked vs Acumen). **No blocked items remain.**

> ## (prior) START HERE (post-#161) — operator: "complete ALL open options, validated multiple ways"
> **`main` at #161, green** (EN/ES language merged, ADR-0099). Working the remaining options as a series:
> **(A) FEI+BRI ← OPEN PR (ADR-0100, this branch); (B) CEI variants (Starts/Critical/adjusted) — NEXT;
> (C) i18n: expand ES catalog + add FR/DE.** All metric definitions PULLED FROM THE BIBLE (.aft) and
> validated against the operator's two-period Acumen comparison. Float Ratio™ stays blocked (no formula).
> - **FEI/BRI (ADR-0100, OPEN):** `engine/metrics/fei_bri.py`, single-snapshot over Normal value tasks,
>   `now`=status date. FEI starts=count(Start≥now)/count(BaselineStart≥now); FEI finish=count(Finish≥now &
>   not-finished-early)/count(BaselineFinish≥now); BRI=count(BaselineFinish≤now & finished≤now)/
>   count(BaselineFinish≤now). Surfaced on /trend (BRI in MEI/BEI/EPI chart; FEI own chart) + indices +
>   dict. **VALIDATED: BRI 0.51 & den 1228 EXACT; FEI start-num 828 EXACT, finish-den 316 EXACT; ratios
>   2.80/2.92 vs Acumen 2.78/2.89 = few-task mpxj-conversion residual (same as BEI).**
> - **CEI variants verified ready to build (B):** CEI Starts=count(current ActualStart>0)/count(prior.start
>   in (s1,s2]) = **0.10 EXACT**; adjusted=count(complete & prior.finish>s1)/denom = **0.22 EXACT**;
>   Critical=same but population filtered to current `stored_is_critical` = **0/3 EXACT**. Bible formulas
>   confirmed (PreviousFinish/PreviousStart, ProjectPreviousTimeNow). Extend `engine/metrics/cei.py`.
> - **OPS:** `/tmp/cei_v1.xml`,`/cei_v2.xml` = mpxj converts of v1/v2 (validation basis; ephemeral).
>   Convert: `java -cp tools/mpxj/classes:tools/mpxj/lib/* MpxjToMspdi <mpp> <out.xml>`. Bible (.aft) is
>   XML; parse `<Metric>` Name/Formula. CUI files in `/root/.claude/uploads/385dc707-.../` (don't commit).

> ## START HERE (post-#160) — EN/ES language toggle in flight; CEI validated & merged
> **`main` at #160, green.** #160 merged **CEI Acumen parity** (ADR-0098, exact 24/129=0.19, 1/6=0.17, on
> /trend beside HMI). **OPEN PR (this branch, ADR-0099): English/Spanish display language for the WHOLE
> UI + all AI results** (operator chose "everything in one pass" + translate imported content too).
> Design = two-layer: `web/i18n.py` hand-built EN→ES **catalog** (nav/titles/buttons/metric names/
> statuses — offline, authoritative) + **AI fallback** `POST /api/translate` (catalog→session cache→local
> model) for dynamic content (task/WBS/resource names, computed/AI prose). `SessionState.language` + nav
> selector (`POST /language`, returns via Referer); `<html lang>` + embedded catalog; `static/translate.js`
> walks DOM text nodes (skips scripts/inputs/[data-no-i18n]/numbers), applies catalog instantly, batches
> misses to /api/translate, MutationObserver covers AJAX grids/charts/AI answers; applied-output guard
> prevents re-translation loops. No model (Null backend) → keeps source text (never broken). Tests cover
> catalog + plumbing + the AI round-trip parser (live model path runs on the operator's machine). To
> WIDEN ES coverage: add entries to `web/i18n._ES`. Gate green, 1015 tests.
> - **CEI follow-on still offered:** add `compute_fei`/`compute_bri` (single-period, present in the
>   operator's files: FEI 2.78/2.89, BRI 0.51); CEI Starts/Critical/adjusted variants deferred. CEI
>   converts: /tmp/cei_v1.xml,/cei_v2.xml (ephemeral). **BLOCKED:** Float Ratio™ (no formula).


> ## START HERE (post-#159) — CEI VALIDATED & implemented; only Float Ratio remains (no formula)
> **`main` at #159, green.** Shipped/merged this stretch: …#156 path-export custom cols (ADR-0095), #157
> driving-path corridor animation (ADR-0096), **#158 file cap →100**, **#159 MS-Project value dropdown on
> /groups (ADR-0097)**. **OPEN PR (this branch, ADR-0098): CEI Acumen parity — VALIDATED EXACT.** Operator
> ran the **two-period Acumen comparison** (Large_Test_File v1 2025-02-07 → v2 2025-03-10); I reverse-
> engineered the CEI definition and built `engine/metrics/cei.compute_cei(prior, current)` (the
> **forecast-anchored** sibling of HMI): denom = activities the PRIOR schedule forecast to finish in
> `(prev_now, now]` & incomplete at prev_now; numerator = of those, actually complete by now; Tasks &
> Milestones separate; N/A single/non-advancing period. **Reproduces Acumen EXACTLY: CEI Value Tasks
> 24/129 = 0.19, Milestones 1/6 = 0.17.** `trend.compute_cei_trend` indexes per version; surfaced on
> `/trend` (chart beside HMI) + `indices.cei_tasks/cei_milestones`; metric-dictionary entries added. Unit
> tests on synthetic 2-period fixtures (real `.mpp`s are CUI — convert via
> `java -cp tools/mpxj/classes:tools/mpxj/lib/* MpxjToMspdi <mpp> <out.xml>`; /tmp/cei_v1.xml,/cei_v2.xml
> are the ephemeral converts I validated against). Note: the tool's pre-existing `/cei` (bow_wave) is a
> DIFFERENT monthly-forward CEI (gave 0.01) — left as-is; this is the DCMA by-status-dates CEI.
> - **STILL AVAILABLE to add from the SAME files (single-period, present, not yet built):** FEI Value
>   Tasks = 2.78/2.89, BRI Cumulative = 0.51 — could add `compute_fei`/`compute_bri` & validate. BEI
>   re-confirmed 0.51 (632/1228) EXACT. CEI "Starts" (~0.10), Critical, and "adjusted" variants deferred.
> **BLOCKED — no path:** **Float Ratio™ / composite Score** — **no extractable formula** (Acumen never
> published it). The only remaining externally-gated item.
>
> **SHIPPED (merged, all green):** #145 BEI→Bible (ADR-0085, CORRECTED by #149); #146 CPLI (ADR-0086);
> #147 **HMI** (ADR-0087); #148 **custom-field mapping** (ADR-0088); #149 **BEI corrected & Acumen-validated**
> (ADR-0089); #150 **grouping ENGINE** (ADR-0090); #152 **driving path 2-UIDs** (ADR-0091); #153 **Groups &
> Filters UI** (ADR-0092 — `/groups`: ≤5 filter rows → DCMA-14 scorecard over `filter_schedule`; breakdown
> per value w/ **BEI**; extracted `metrics.compute_bei`, no-CPM, single source of truth); #154 **custom-field
> display columns** (ADR-0093 — `_driving_data` rows carry `custom`, payload carries `custom_field_labels`,
> `path.js syncCustomColumns` adds a toggle per field).
> - **VALUE-VALIDATION vs the operator's new Acumen ribbon reports (2 versions of the Large File):**
>   **HMI is EXACT** (Acumen v2 = 0 of 24 due tasks, milestone 0 of 1, v1 N/A — `compute_hmi_trend`
>   reproduces it). **BEI was WRONG** → fixed to Acumen "BEI - Value Tasks" = complete NORMAL tasks /
>   NORMAL baselined-due (no baseline-dur filter, no missing-baseline term); goldens EXACT 0.74/0.59,
>   Large-File denominator EXACT 1228, numerator within 2 of 632.
>
> **NEXT (after ADR-0094 merges) — the 3 asks are complete; remaining backlog is value-validation + polish:**
> keep value-validating CEI / critical-path against the Ribbon Analysis sheet (CEI/FEI/BRI/TC-BEI/EVM by
> absolute column index — header row 9, v1 row 10, v2 row 11; NEEDS the CUI Acumen files re-attached);
> optional polish (custom cols in path export; animated Gantt for the driving-path corridor; Float
> Ratio™/Score still DEFERRED — no extractable formula).
>
> **MODEL/ENGINE recap:** custom fields = `Task.custom_fields` (tuple of (label,value); alias e.g. `CA-WBS`
> wins over `Text20`) + helpers `custom_field(label)`/`custom_field_map`; `Schedule.custom_field_labels`
> (populated, declared order). Schema **2.2.0**. Grouping = `engine/grouping.py` (`MAX_FIELDS=5`;
> `filter_schedule` = sub-schedule of matching tasks + internal rels so all metrics run unchanged;
> `group_values` = per-value UID groups; STANDARD_FIELDS = WBS/Activity Type/Constraint Type/Resource/
> Critical/% Complete).
>
> **MORE ACUMEN OUTPUT to validate against (in the edited DCMA report's `Ribbon Analysis` sheet, by
> absolute column index — header row 9, v1 row 10, v2 row 11):** CEI, FEI, BRI, TC-BEI, EVM (PV/EV/AC/
> SPI/CPI/EAC/VAC/BAC), Phase Analysis, Started/Completed-Delayed buckets. Use these to value-validate
> CEI/critical-path next.
>
> **OPS:** convert mpp→MSPDI via `java -cp tools/mpxj/classes:tools/mpxj/lib/* MpxjToMspdi <mpp> <out.xml>`
> (Java 21 ok; 9MB file ~30s). **CUI:** `.mpp`/`.xlsx`/`.aft` must NOT be committed (pre-commit guard).
> Uploaded files live in `/root/.claude/uploads/385dc707-.../` THIS session — a NEW session likely won't
> have them, so the kickoff prompt asks the operator to re-attach. **DEFERRED:** Float Ratio™ + composite
> Score (no extractable formula); D (Fuse year Trend/Phase — ASK binning); `/path` chart bug (needs shot).



> **External audit (7 roles, A1–A11) FULLY ADDRESSED (#133–#136 + ADR-0077).** Only easy
> follow-up left: **A3-follow-up** `.sr-only` data tables for the non-curves charts
> (cei/scurve/drift/trend/trend_drill/wbs — names already done; trivial with `SFA11y.table`).
> Operator feature backlog still open: **`/path` chart visual bug**
> (needs the operator's screenshot), **D** Fuse year Trend/Phase (parity-sensitive; binning ambiguous
> — ask the operator), **E** Data-Date/Slippage overlaid-line redesign w/ clickable legend, **F**
> Bow-Wave running totals + target highlight; **G** Fuse-proprietary metrics stay DEFERRED (no DAX). The operator backlog is being worked **bugs-first**:
> **#128 (ADR-0068) MERGED** the `/analysis` Gantt scaling fix (item A's `/analysis` half) + path
> filters/full-wrapped-names (item C); **#129 (ADR-0069) MERGED** item B (MS-Project checklist
> filters). The **OPEN draft PR on this branch carries ADR-0070** — an out-of-band operator fix:
> **the local AI (Ollama) wouldn't activate on the operator's corporate laptop** (system proxy
> intercepted the loopback probe) → bypass the proxy + actionable settings diagnostics + editable
> Ollama endpoint. The highest ADR on disk is **0070**. Recreate the work branch from fresh main,
> then continue the REMAINING items (the remaining **bug** — the `/path` driving-chart visual defect
> — needs the operator's screenshot; otherwise the Fuse year Trend/Phase view D, Data-Date/Slippage
> E, Bow-Wave F).
> **Container setup FIRST:**
> `pip install -e '.[dev]'` into the env, and drive the gate with **`python -m pytest`** (the PATH
> `pytest` is a separate uv tool that can't see the editable install). Gate: `ruff check .` ;
> `ruff format --check .` ;
> `python -m mypy` ; `python -m pytest --cov=schedule_forensics --cov-fail-under=70` ;
> `coverage report --include='*/schedule_forensics/engine/*' --fail-under=85` ;
> `python -m pytest -m parity` (10/10, non-negotiable) ; `bandit -q -r src`.

> **OPERATOR BACKLOG (the big multi-part request + follow-ups). SHIPPED this session:**
> 1. ~~Ask-the-AI + release local Ollama~~ — **MERGED #116, ADR-0059** (full local evidence; air-gap kept).
> 2. ~~Chart legibility + fullscreen/zoom + legends~~ — **MERGED #117, ADR-0060** (`chartframe.js`).
> 3. ~~Target-UID drives every page~~ — **MERGED #118, ADR-0061** (`target.js`; /card + /wbs panel).
> 4. ~~Critical-path "gained float" counterfactual~~ — **MERGED #119, ADR-0062** (/evolution What-if).
> 5. ~~Diagnostic Brief trends/risks/recovery~~ — **MERGED #120, ADR-0063**.
> 6. ~~DCMA 1–14 definitions on the Analysis page~~ — **MERGED #121, ADR-0064**.
> 7. ~~Animated S-Curve~~ — **MERGED #122, ADR-0065** + **#124** moved its data-date callout
>    bottom-right (no title overlap).
> 8. ~~Fuse workbook validation~~ — **MERGED #123, ADR-0066** (`docs/FUSE-VALIDATION.md`): tool
>    matches Fuse exactly on normal-completion (8/8) + TP4 v1–v4 finish; diffs documented.
> 9. ~~Fuse Ribbon metrics~~ — **MERGED #125, ADR-0067.** `engine/metrics/ribbon.py` + `/ribbon`
>    view, calibrated to Fuse: Logic Density™ (2L/N), Merge Hotspot (>2 preds), Missing Logic
>    (all open-ends), Critical (incomplete on path), Hard/NegFloat/Lags/Leads (DCMA), Avg/Max float.
>
> **REMAINING — each its own tested, parity-green draft PR (operator wants ALL):**
> A. **BUGS (do first — defects):**
>    - **Path Analysis driving/secondary/tertiary-to-target chart is WRONG** (`path.js` + `/api/driving`).
>      **STILL OPEN — needs the operator screenshot** (visual; can't verify rendering in-container).
>    - **Scaling wrong** on the per-project (`/analysis`) **driving-path trace + project-schedule
>      Gantt** — `app.js` positioned bars as % of the whole span squeezed into a fixed-width column
>      with NO adjustable scale/scroll. **✅ FIXED (ADR-0068, OPEN draft PR):** both `/analysis`
>      Gantts now use the `/path` px-per-day + horizontal-scroll model (shared `buildAxis`, a
>      `#vizZoom` scale slider, month ticks + data-date line in px, pixel-true header/body alignment).
>    - **OPEN QUESTION for operator (still owed):** a SCREENSHOT of the wrong `/path` chart + a
>      `/analysis` Gantt to fix the `/path` half precisely. The `/analysis` half above was fixed
>      against the known-good `/path` model without it; the `/path` defect needs the screenshot.
> B. **MS-Project-style dropdown filters** (select-all / deselect-some checklists) replacing the
>    substring filter inputs on the grid + path tier filter. **✅ DONE (ADR-0069, OPEN draft PR):**
>    reusable `static/checklist.js` (`window.SFChecklist`) — a search + Select-all/Clear checklist
>    of a column's distinct values; applied to the `/analysis` grid per-column filters and both tier
>    filters (`/path` `#pathTier`, `/analysis` trace `#ganttTier`, now multi-tier).
> C. **Path filter on BOTH pages** (operator-confirmed): `/analysis` gets Primary/Secondary/Tertiary
>    tier filter + hide-completed + adjustable time scale + full wrapped names; `/path` gets full
>    wrapped task names (it already has tiers/hide/px-day-zoom). **✅ DONE (ADR-0068, same OPEN draft
>    PR):** `/analysis` got the `#ganttTier` tier filter, the `#vizZoom` adjustable scale, and full
>    wrapped names (grid + trace); `/path` Name column now wraps to full text. (Overlaps A + B.)
> D. **Year Trend/Phase view** — Fuse Ribbon Browser + per-year (2017–2028) trend analysis
>    (reference values in docs/FUSE-VALIDATION.md).
> E. **Data-Date & Slippage redesign** — overlaid line families with a clickable show/hide legend (curves.js).
> F. **Bow-Wave (cei.js)** running totals + target-UID highlight during animation.
> G. **Deferred Fuse-proprietary metrics**: Insufficient Detail™, Float Ratio™ (+ EPI / RatioMeasure /
>    Start-and-Finish-Ratio) — NO simple formula matched in calibration; implement only when the
>    operator supplies the exact Fuse/DAX definition. Do NOT guess.
> **Ollama policy: free LOCAL analysis, KEEP the strict loopback-only air-gap (no data leaves the machine).**

> **PR — ADR-0078 (OPEN draft, this branch) — curves clickable show/hide legend (item E).** The
> `/curves` Data-Date + Slippage charts overlay one line per version (50+ lines on a real program);
> `curves.js` `buildLegend` replaces the static in-SVG legend with real `<button>` entries that toggle
> each line (`polyline.style.display`, `aria-pressed`, struck `.off`) — keyboard-operable + focus-ring;
> Show-all/Hide-all isolates one version from the clutter. Applied to all 3 curves charts; data-date
> marker / locked axis / accessible name / `.sr-only` table unchanged. Parity 10/10. Built on
> `main`@#137.

> **PR — ADR-0077 (MERGED as #137) — audit close-out (A9 / A10 / A11).** A9: a
> `@media (max-width:760px)` block wraps the header/nav and collapses the wide card grids to one
> column (also satisfies 200%-zoom reflow). A10: `theme.js` sets `aria-pressed` on the toggle and a
> first visit follows the OS `prefers-color-scheme` (saved choice still wins, no flash). A11:
> `test_state_docs.py` now requires the latest ADR in BOTH HANDOFF and SESSION-LOG (anchored on local
> ADR files). **External audit A1–A11 fully addressed.** Parity 10/10. Built on `main`@#136.

> **PR — ADR-0076 (MERGED as #136) — table scope + print stylesheet (audit A4 + A5).**
> A4: mechanical `scope=col` on every server-rendered `<th>` (all 43 are column headers). A5: a
> `@media print` block in `base.css` — hides chrome (`header`/`.cf-bar`/`.export-bar`/`.viz-controls`/
> `#askPanel`), forces light ink on white, `break-inside:avoid` on panels/cards/tables, prints the
> horizontal scrollers in full, `@page{margin:14mm}`. Parity 10/10. Built on `main`@#135.

> **PR — ADR-0075 (MERGED as #135) — chart accessible names + data tables (audit A3).**
> Shared `static/a11y.js` (`window.SFA11y`, shell-loaded): `label(svg, name)` gives every chart a
> real accessible name (`<title>` + `aria-label`) — fixes the nameless `role=img` on all 11 charts
> (trend ×4 by their title; curves ×3 via a name arg; cei/scurve/drift/path_evolution/trend_drill/wbs
> static); `table(caption, headers, rows)` builds a `.sr-only` data-table fallback, implemented on the
> curves page (Finishes / Data-date / Slippage). Parity 10/10; air-gap green. Built on `main`@#134.
> Follow-up: `.sr-only` tables for the other charts (names already done).

> **PR — ADR-0074 (MERGED as #134) — CSP + security headers (audit A7).** Every response
> now carries a `Content-Security-Policy` (`default-src`/`connect-src`/`img-src` = `'self'`,
> `frame-ancestors 'none'`, `object-src 'none'`) + `X-Content-Type-Options: nosniff`,
> `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`, set in the `create_app` http middleware via
> `setdefault`. Enforces the no-remote-asset air-gap in the browser at runtime. Permissive-inline
> (`'unsafe-inline'` style+script) so the inline Gantt px-widths + the 2 inline handlers (Quit /
> wipe-confirm) keep working — but remote scripts/styles are still forbidden. Air-gap scan still
> green + a new header test. Parity 10/10. Built on `main`@#133. Follow-up: tighten to strict
> `script-src 'self'` after moving the 2 inline handlers to addEventListener.

> **PR — ADR-0073 (MERGED as #133) — accessibility foundations (audit Group 1).** Pure
> presentation: (A1) a theme-aware `:focus-visible` outline ring using the orphaned `--focus` token;
> (A2) a `prefers-reduced-motion` CSS block + a guard in all 5 auto-play `toggleAuto()` handlers
> (under reduce-motion, Auto-play advances one frame instead of timer-flipping; Prev/Next unaffected);
> (A6) define `--border`/`--grid-line` in both theme blocks (were used with hardcoded fallbacks);
> (A8) a diagonal `repeating-linear-gradient` hatch on critical/driving Gantt bars (non-colour cue);
> plus the `.sr-only` helper as A3 groundwork. Parity 10/10; air-gap green. Built on `main`@#132.

> **PR — ADR-0072 (MERGED as #132) — configurable generation timeout for big models.**
> Operator wants the most powerful llama3.1 "even if it takes my machine longer". Each generation was
> capped at 120 s, so a large model (e.g. `llama3.1:70b` on CPU) got cut off → deterministic
> fallback. Added `AIConfig.gen_timeout` (default 300 s, clamped 30 s..1 h) wired into every local
> backend + a `/settings` "Generation timeout" field; the short availability probe (8 s) is
> untouched. Installing the model is a manual `ollama pull` on the operator's box (the air-gapped
> tool never fetches over the network — instructions given in chat). Parity 10/10. Built on
> `main`@#131. (Stashed a11y WIP still on this branch — pop after.)

> **PR — ADR-0071 (MERGED as #131) — local AI that just works.** Two operator follow-ups
> after ADR-0070: (1) **auto-manage Ollama** — `ai/ollama_process.py` `OllamaLauncher` starts a local
> `ollama serve` on desktop launch (background thread, never blocks) and stops it on exit, but ONLY if
> we started it (an already-running Ollama is left alone); wired into `launcher.main` (finally +
> atexit). Loopback-only, never `ollama pull` (Law 1). (2) **probe 2 s → 8 s** so a corporate laptop's
> slow first local connection ("timed out") still reads reachable. (3) **install-aware Model dropdown**
> on `/settings` — when Ollama is reachable the Model field lists installed models (configured-but-
> missing kept + flagged), because the operator's `llama3.1:8b` wasn't installed (they have
> `llama3.2:latest` / `schedule-analyst:latest` / `qwen2.5:7b-instruct`). Parity 10/10; 922 passed.
> NOTE the **stashed a11y WIP** on this branch (audit Group 1) — `git stash pop` after this PR.

> **PR — ADR-0070 (MERGED as #130) — local AI works on a corporate laptop.** Operator
> screenshot showed `/settings` reading **Active backend: null** with Ollama + `llama3.1:8b`
> configured (model never activated → only deterministic facts, no interpretation). Root cause: the
> local-AI HTTP client used urllib's default opener, whose **`ProxyHandler` reads the machine proxy**
> — on a managed Windows laptop that routes even `127.0.0.1:11434` through the corporate proxy, which
> refuses it (and would be a Law-1 egress risk). Fix in `ai/ollama.py` `_make_opener()`:
> `build_opener(ProxyHandler({}), _NoRedirect())` → **direct, no-proxy** loopback connection (covers
> the OpenAI-compatible backend too). Plus: actionable `/settings` diagnostics (`unavailable_reason()`
> → *connection refused / timed out / model not pulled* with a fix hint) and an **editable Ollama
> endpoint** field. The interpretive full-evidence prompt (`ai/qa.py`) was already correct — the only
> blocker was connecting. Parity 10/10; 913 passed. **Operator: `git pull` + relaunch to get it.**

> **PR — ADR-0069 (MERGED as #129) — MS-Project checklist filters (item B).** New
> reusable `static/checklist.js` (`window.SFChecklist.filter`): a button + fixed-position popup
> with a search box, **Select-all / Clear**, and a checklist of a column's distinct values;
> `onChange` gets the selected `Set` (or `null` = all = unfiltered; empty Set hides every row).
> Loaded once from the page-shell `<head>` (air-gap scan extended). Applied to the `/analysis`
> grid per-column filters (`filters[key]` is now a `Set|null`; `rowMatches` is membership;
> `distinctValues` is numeric/ISO-date-aware) **replacing the substring inputs**, and to both tier
> filters (`/path` `#pathTier`, `/analysis` trace `#ganttTier`) which become **multi-tier**
> checklist mounts. Pure presentation → parity 10/10. Built on `main`@#128.

> **PR — ADR-0068 (MERGED as #128) — /analysis Gantts go scalable + path filters.** The
> per-project `/analysis` driving-path trace (`#gantt`) and activity Gantt (`#grid` timeline) no
> longer squeeze the whole span into a fixed-width column as a % of span — both now use the `/path`
> px-per-day + horizontal-scroll model: a shared `buildAxis` in `static/app.js`, one page-level
> **Scale** slider (`#vizZoom`, 2–40 px/day), month ticks + the gold data-date line positioned in
> pixels, and pixel-true header/body alignment (zeroed horizontal padding on `.g-head`/`.g-cell`).
> The `/analysis` trace also gained a Primary/Secondary/Tertiary **tier filter** (`#ganttTier`),
> keeps the show/hide-completed toggle, and shows **full wrapped task names** (no 22-char
> truncation); the `/path` Name column wraps to full text too (`pv-name`). This closes item A's
> `/analysis`-scaling half + all of item C. **Still owed:** the `/path` driving-chart *visual*
> defect (item A's first half) — a follow-up commit on this same PR once the operator sends the
> screenshot. Pure presentation → **parity 10/10**; full suite **908 passed**; engine cov 97%.
> Air-gap unchanged (app.js stays dependency-free, same-origin).

> **AUDIT NOTE (2026-06-17):** the operator's 4 Acumen Fuse exports (Schedule Quality docx +
> Ribbon/Phase xlsx + DCMA Report) live ONLY in the ephemeral session uploads — their values are
> captured durably in `docs/FUSE-VALIDATION.md`. The reference `.mpp`/`.pbix` are NOT in the
> container (`00_REFERENCE_INTAKE/` empty) — re-deposit to validate Large File / Duration Bomb /
> Project3/4 / Project5_TAMPERED, which the workbook covers but the repo fixtures don't.

> **PR — ADR-0060 (chart full-screen / zoom / legible labels).** New `static/chartframe.js` +
> `.cf-*` CSS: any `class=chart-host` container gets an overlay toolbar (⤢ full screen via the
> Fullscreen API w/ `.cf-max` fallback; − / ＋ / Reset zoom rescaling the SVG in a scroller).
> Loaded once from the page shell; a MutationObserver re-applies zoom across stepper re-renders.
> `chart-host` marks trend/finishes/data-date/slippage/CEI/WBS/drift/analysis containers (the
> evolution Gantt keeps its own ADR-0055 zoom). `trend.js`+`curves.js` `shortLabels` now prefer
> the **data date** (uniform, sorted, non-overlapping) over long filenames; `drift.js` axis ticks
> are **adaptive** (year/quarter/month). Pure presentation → parity 10/10; full suite 876 passed.

> **PR — ADR-0059 (Ask-the-AI: full local evidence).** `ai/qa.py`: a live local model now
> gets the WHOLE cited sheet (`model_evidence`, frame-first + relevance-ordered, cap 48) with a
> senior-analyst prompt (answer + interpret + name risks + suggest recovery), while the analyst
> is still SHOWN the question-relevant `relevant_facts` slice. Strict mode unchanged; air-gap
> unchanged (`OllamaBackend` loopback-only — further scheme/redirect-hardened by ADR-0058/#115,
> `route_backend` fail-closed). `build_fact_sheet` adds the finish-driving count; the ask panel
> links to AI Settings to enable Ollama. Branched from `main`@#114, then merged up to #115
> (ADR-0058); re-verified green after the merge.

> ## START HERE (next session)
> 1. **One OPEN draft PR awaiting your merge: ADR-0059 — Ask-the-AI full local evidence /
>    release local Ollama (item 1 of the operator backlog above), branched from `main`@#114
>    and merged up to #115.** The prior audit-remediation PR (ADR-0058 — loopback AI-endpoint
>    scheme/redirect hardening + native-`.mpp` parity confirmation) has since MERGED as #115.
>    Earlier, the previous handoff
>    called PR #102 "OPEN"; it has since merged (as `f9b5b10`), and **PRs #103–#113 landed
>    after it** (ADRs 0047–0057, the post-M18 "tab visuals" / operator-feedback tranche — see
>    "What shipped — PRs #103–#113" below). Verified locally this sitting (2026-06-17):
>    **849 passed, 3 skipped; parity 10/10; engine 97%; ruff/format/mypy/bandit clean.**
>    Recreate the work branch from fresh main before any new work:
>    `git fetch origin main && git checkout -B <fresh-branch> origin/main`.
>    **Container gotchas:** the preinstalled `.venv` ships WITHOUT the web/dev deps — run
>    `pip install -e '.[dev]'` FIRST or the gate's mypy/pytest/parity/bandit all spuriously
>    fail. And the PATH `pytest` is a separate uv tool that cannot see the editable install —
>    drive the gate with **`python -m pytest`**, not bare `pytest`.
> 2. **M18 is COMPLETE (items 1–8) AND the operator's tab-visuals follow-ups (#103–#113) are
>    done. No feature backlog remains.** The open follow-ups are VERIFICATION / real-data
>    items, none blocking:
>    - **✅ Native-`.mpp` battery — VALIDATED this sitting (2026-06-17).** Operator re-deposited
>      all 14 reference `.mpp`s (non-CUI test files, attested) into `00_REFERENCE_INTAKE/mpp/`
>      (git-ignored, never committed). Each was checked against its committed MSPDI twin / pinned
>      values (method: the MSPDI fixtures are verified ground truth, so model-equivalence ⇒ every
>      downstream number holds). Results:
>      - **Duration Bomb** computes finish **2027-02-24** → ADR-0043 owed item **CLOSED**.
>      - **Project2** native parse is a **full model match** to the golden (145 tasks / 176 links /
>        finish 2027-08-30, zero field diffs).
>      - **TP4 v3→v4** fires `MANIP_ACTUAL_ERASED` + `MANIP_BASELINE_CHANGE` citing UID 19;
>        **v2→v3** fires neither — manipulation detection confirmed on native `.mpp` (matches pin).
>      - **Project5_TAMPERED** → tool flags `MANIP_DELETED_LOGIC` (UIDs 135/138); finish slips
>        2027-12-07 → 2028-01-25. Detector works.
>      - **Large File** parses faithfully — **1723** non-summary activities (exact ADR-0045 match),
>        2702 links. The documented driving chain's relative spacing reproduces SSI's **0/9/12/13**
>        to the day. ⚠️ Absolute reproduction is blocked because **ADR-0045 never recorded SSI's
>        target/focus UID** (doc gap — capture it next time the file is in hand).
>      - **TP1 / TP3 / TP4(v1–v5)** native `.mpp` match their MSPDI twin on task topology, logic
>        links, and computed finish; they differ only on `percent_complete` (+ a few durations) for
>        in-progress/summary tasks — MS Project recomputes progress/roll-ups on XML→`.mpp` import.
>      - ⚠️ **TP2 round-trip caveat (NOT a tool bug):** `.mpp` computed finish is **2026-09-24**, not
>        2026-11-04, because MS Project dropped the **4×10 Crew project calendar's 4 holiday
>        exceptions** on save (confirmed via MPXJ: project CalendarUID=1 has 0 exceptions; stock US
>        holidays landed on the non-default "Standard" calendar UID 2). The tool reads the project
>        calendar correctly; the canonical committed XML (4 holidays → 2026-11-04) is authoritative.
>        Details in `docs/PARITY-REPORT.md` / `docs/risks.md` (R-04).
>      - Minor, pre-existing & format-independent: TP4 **v4 and v5** both compute finish 2026-06-26
>        from the `.mpp` **and** the committed MSPDI, while `TEST-PROJECTS.md` lists v5 as 7/17/26 —
>        a fixture-vs-manifest question, not a native-`.mpp` issue. Flagged for separate review.
>    - **Real-file feedback** — watch how Path Analysis, Critical-Path Evolution (now with grid
>      columns / zoom / filter-by-path / specific reasons), ask-the-AI, float bands, `/forecast`
>      (with the explainer), `/trend` drill-down, and the Dashboard health cards read on real
>      `.mpp`/`.xer`. Importer tolerance lives in `importers/_common.py`; ALWAYS re-run
>      `pytest -m parity`.
>    - **Deck measures awaiting a DAX export** (EPI / RatioMeasure / Start-and-Finish Ratio) —
>      implement exactly when the operator provides the measure text; do not guess.
>
> ## ⚠️ PROCESS — verify ruff/format with EXPLICIT exit codes
> Twice this sitting a real `ruff check`/`ruff format --check` failure slipped to CI because
> a `cmd && echo ok` chain swallowed the failure while test counts still printed. **Run the
> CI-exact gate and read each exit code:** `ruff check .` ; `ruff format --check .` ; `mypy`
> (BARE — that's what CI runs, src only; do NOT add `tests`, which has known mypy noise CI
> never checks) ; `pytest --cov=schedule_forensics --cov-fail-under=70` ; `pytest -m parity`.

## What shipped — PRs #103–#113 (post-M18 "tab visuals" / operator feedback, 2026-06-16→17)
All merged to `main`; `main` is green at #113. These are the operator's "tab visuals"
follow-ups after M18 closed — the previous handoff stopped recording at #102, so this section
restores the record. Newest first:
- **#113 (ADR-0057)** — Critical-Path Evolution **reason specificity**: entered/left
  attribution now NAMES the specific slip (which activity consumed the float), CITES the exact
  predecessor/successor link(s) for `logic_added`/`logic_removed`, and shows the signed
  duration delta + percent for `duration_up`/`duration_down`.
- **#112 (ADR-0056)** — Evolution **filter-by-path**: a selector with four switchable modes
  scoping which activities the Gantt shows; applied to both critical rows and the dashed
  "left the path" ghost rows, composed after the hide-completed filter.
- **#111 (ADR-0055)** — Evolution **axis zoom/pan + target-UID focus** (`/evolution?target=`,
  mirrors `/trend?target=`; the session-wide target carries over across views).
- **#110 (ADR-0054)** — Evolution **per-activity grid columns** (% complete / duration /
  start / finish), smaller wrapped readable names, and the view's own **hide-completed** toggle.
- **#109 (ADR-0053)** — **schedules listed earliest→latest data date in EVERY view**
  (`SessionState.ordered_versions()` via `engine/trend.order_versions`; undated keep load order).
- **#108 (ADR-0052)** — **CEI re-verification**: there are TWO distinct indices both named
  "CEI" — EVM CEI (`engine/metrics/evm.py`) vs Bow-Wave CEI (`engine/bow_wave.py`, `/cei`).
  Both re-derived from first principles against the golden Acumen exports and **pinned to exact
  golden values** (replacing weak `is not None` assertions).
- **#107 (ADR-0051)** — **hide-completed robust flag**: real `.mpp`/`.xer` exports report a
  finished activity at 99.x% (MSP rounding / XER `CP_Units`) while carrying an actual finish, so
  `percent>=100` left done tasks visible. The toggle now keys on a robust complete flag (goldens
  are exactly 100.0, which masked the bug); behavior unified everywhere it appears.
- **#106 (ADR-0050)** — **Dashboard health cards**: `/api/dashboard` (`_dashboard_data`) — one
  health snapshot per loaded schedule (status mix, critical %, finish vs baseline, DCMA
  pass/fail) that clicks through to the detailed report; reuses the cached `_Analysis` (no
  CPM recompute).
- **#105 (ADR-0049)** — **every chart carries a legend + description; labels de-overlapped**
  (`trend.js` was the worst offender — no legend, no per-chart description, unthinned rotated
  x-labels smearing on 10+ version workbooks).
- **#104 (ADR-0048)** — Critical-Path **Evolution Gantt + entered/left attribution**: bars
  instead of a flat list, strong visual emphasis on added/removed activities, and a per-activity
  reason (logic change / new task / duration change / constraint).
- **#103 (ADR-0047)** — **Ask-the-AI relevance fix**: `relevant_facts` no longer padded every
  answer with the same leading facts, so the Null-backend answer is now question-specific
  (air-gap unchanged — no LLM prose ever leaves the machine).

> **SSI DRIVING-SLACK PARITY FIX (ADR-0045) — DONE + VERIFIED, shipped as PR #101.**
> Operator compared the tool's Path Analysis vs SSI on `Large Test File.mpp` (USA OTB Master
> IMS, 1723 acts): the tool's tiers were a consistent **~+1 day** off SSI (SSI 0-day driving
> path read as secondary; SSI 9/13 read 10/14). **Root cause:** ragged stored TIMES of day
> (afternoon-shift activities stored 13:00→12:00 → 420-min "1-day" spans) made activity spans
> sub-day; the backward pass's span subtraction ACCUMULATED that raggedness down a long chain
> and tipped whole-day slack over a boundary. **Fix:** snap each activity's SPAN to the
> nearest whole working day in `compute_driving_slack` (display dates unchanged — `date_basis`
> untouched). An earlier attempt that snapped the FINISH broke TP1 (sub-day DRIVING → full-day
> SECONDARY); snapping only the span preserves TP1 exactly. Verified: Large File matches SSI
> exactly (driving 0, near-path 9 and 12/13); **TP1 parity preserved (13/1/2/2)**; parity
> 10/10; full suite 813. Regression: `tests/engine/test_driving_slack_daygrid.py` + the updated
> TP1 battery pins (UID 11/12 now 60 min, not 210 — same DRIVING tier).


**This sitting (2026-06-16, cont. 5):** **#101 merged** (SSI driving-slack day-grid fix,
ADR-0045). Then **PR #102 (ADR-0046) — M18 item 8, the LAST backlog item**: the **Forecast
explainer** on `/forecast` (a plain-English "How the three forecasts are computed" panel — one
card per method with the formula in words + symbols + this version's value — plus a static
single-version inline-SVG "spread ruler" placing the data date, baseline finish, and the three
method dates on one timeline; server-side, no new JS) and the **Trend page expansion**:
`MetricTrend.offenders_by_version` (the offending activities per metric PER version),
`/api/trend` per-version counts + offenders (uid+name) + lower_is_better/worst_index, a new
**"Quality drill-down & animation"** panel (`static/trend_drill.js`: a Prev/Next/Auto-play
version stepper over a LOCKED-axis bar chart of per-metric offender counts, with a metric
selector listing the exact offending activities for the current version), and a full
per-version **"Quality offenders by version"** Excel/Word export table. Additive (forecasting
math / CPM / quality definitions untouched) → parity **10/10**; full suite **818 passed**;
engine cov 97%. Air-gap extended over `/forecast` + `trend_drill.js`. **M18 COMPLETE.**
Model/mode: Opus 4.8 (1M).

**This sitting (2026-06-16, cont. 4):** **#99 merged** (summary-logic fix, ADR-0043). Then
**PR #100 (ADR-0044) — M18 item 7, Critical-Path Evolution animation**: a new
**`/evolution` page** with a Bow-Wave-style Prev/Next/Auto-play stepper over the versions
(`engine/path_evolution.py` `compute_path_evolution` → `PathEvolution`/`CriticalSnapshot`).
Per version: the critical path with **entered** (green) / **stayed** (grey) / **▲dur** badge
and **left** (struck) activities, plus a callout for the **finish movement** and
**schedule-optics signals** (durations cut on the path + logic removed — reusing
`detect_manipulation`), flagging a path that sheds work while the finish holds. Nav +
dashboard links + xlsx/docx export (`path_evolution_tables`); air-gap extended. Verified on
golden P2→P5 (critical 43→37, 6 left, finish +99d). Parity 10/10; full suite 810 passed;
path_evolution 100% cov. **Remaining M18: item 8 (forecast explainer + Trend expansion).**
Model/mode: Opus 4.8 (1M).

**Prior this sitting (2026-06-16, cont. 3):** **#98 merged** (Carnac cards, ADR-0042). Then
**PR #99 (ADR-0043) — logic on summary tasks**: the Duration-Bomb verification (below) was
RESOLVED here. Root cause: the test file (an MS Project sample) attaches predecessor/
successor logic to **summary** tasks (e.g. summary UID 151 on an FS chain with 40–60wd
lags), which MS Project applies to the summary's children; our CPM dropped summary tasks
from the network and so ignored it, packing children at the front (computed 2026-08 vs
MSP's 2027-02). Fix (`engine/summary_logic.py`): `lower_summary_relationships` replaces each
summary endpoint of a relationship with the summary's **leaf descendants** (cross-product,
type+lag preserved; WBS segment-prefix hierarchy); `compute_cpm` now builds edges from the
lowered relationships. No-op without summary logic, so the goldens (zero summary logic,
pinned) are byte-identical → **parity 10/10**. Plus a new MEDIUM finding
`logic_on_summary_tasks` (cited, in the metric dictionary) flagging the DCMA/PMI anti-pattern.
**Verified: the Duration Bomb now computes 2027-02-24** (its stored "Wedding COMPLETE"
date), UID 17 lands on its stored 2026-07-27, the finding cites all 18 summaries.
Full suite 799 passed; engine cov (summary_logic 100%). Model/mode: Opus 4.8 (1M).

**Prior this sitting (2026-06-16, cont. 2):** **#97 merged** (PBIX pages 8/9 WBS pivots,
ADR-0041). Then **PR #98 (ADR-0042) — M18 item 6, PBIX page 13 (Carnac forecast cards)**:
the deck's *Carnac* KPI card row on the existing `/forecast` page (no new route/JS) —
earliest start, latest finish, project + remaining duration (wd), Forecasted End Date
(rate), Estimated End Date (ES, to-go), avg tasks/month, SPI(t) [deck "SPI 2"], ES (wd),
to-go count [deck "Tasks Completion Forecast"]. New engine `compute_carnac_summary` →
`CarnacSummary` (reuses CPM + ForecastSet; lightweight dataclass). Also **unified the
Earned-Schedule definition**: `forecast._earned_schedule` now delegates to the public
`metrics.evm.earned_schedule` (shared by SPI(t), WBS, forecast — golden pins unchanged).
Export gains a Carnac summary table. Parity 10/10; engine cov 97% (forecast 97%, no
uncovered lines). **PBIX reproduction spine COMPLETE: pages 1,4,5,6,7,8,9,12,13 done;
pages 2/3/10/11 are restatements.** Model/mode: Opus 4.8 (1M).

> **✅ DURATION-BOMB VERIFICATION (owed since #91) — RESOLVED 2026-06-16 (ADR-0043).**
> The test file (`00_REFERENCE_INTAKE/mpp/Project2_Duration_Bomb.mpp`, non-CUI) is a
> downloaded MS Project sample ("Formal Wedding Planner", 71 activities, 0% complete) that
> attaches logic to **summary** tasks. Operator's call: calculate as MS Project does (lower
> summary logic to children) AND flag it. Implemented in PR #99 (ADR-0043). The CPM now
> computes **2027-02-24** (matching the file's stored dates; the earlier "2026-08-05" was
> our CPM dropping summary logic), and `logic_on_summary_tasks` fires citing the 18 summaries.

**Prior this sitting (2026-06-16, cont.):** **#96 merged** (item 6 PBIX pages 6/7/12 —
Finish & Slippage curves, ADR-0040; post-merge main green). Then **PR #97 (ADR-0041) —
M18 item 6, PBIX pages 8 + 9 (WBS pivots)**: a new **`/wbs/{name}` page** with the
**Completion Metrics by WBS** pivot (counts/%, ahead/on/behind + avg days, longer/shorter,
duration ratio) and the **SPI(t) & Earned Schedule by WBS** combo chart + table. New engine
`engine/metrics/wbs_breakdown.py` (`compute_wbs_breakdown` → `WBSGroup`, grouped by
top-level WBS segment; lightweight dataclass NOT MetricResult). The count-based SPI(t)
core was factored out of `evm.py` into a public `earned_schedule(schedule, tasks)`
(reused by `_spi_t` and the per-WBS breakdown — one ES definition). Dashboard row "WBS"
action, xlsx/docx export (`wbs_breakdown_tables`), shared ask panel. Air-gap extended over
`/wbs/{name}` + `wbs.js`; engine cov 97% (new module 100%, evm 100%); parity 10/10; golden
groups reconcile (126/27 in Project5). PBIX-VISUALS pages 8/9 marked REPRODUCED.
**Remaining PBIX: Carnac forecast cards (13); pages 2/3/10/11 are restatements.**
Model/mode: Opus 4.8 (1M).

**Prior sitting (2026-06-16):** **#95 merged** (item 6 PBIX pages 4+5 — Cross File
Comparison + Float Analysis charts on the Trend page, ADR-0039; post-merge main green).
Then **PR #96 (ADR-0040) — M18 item 6, PBIX pages 6, 7, 12 (Finish & Slippage curves)**:
a new **`/curves` page** with three dependency-free SVG line charts on one shared month
axis — **Finishes** (latest version: actual vs baseline finishes/month), **DATA Date
Finishes** (one actual-finish curve per version — the bow wave as a line family), and
**Slippage** (per version, a start curve + a finish curve). New engine:
`engine/month_axis.py` (the shared `month_index`/`month_label`/`bucket` primitives,
extracted from bow_wave which now imports them) + `engine/month_curves.py`
(`compute_month_curves` → `MonthCurves`/`VersionCurves`, lightweight dataclasses NOT
MetricResult). Stored-date view (no CPM gate — every loaded version contributes, works
single-version too). Nav link + dashboard multi-version row + xlsx/docx export
(`month_curves_tables`). Air-gap extended over `/curves` + `curves.js`; engine cov 97%
(new modules 100%); parity 10/10. PBIX-VISUALS pages 6/7/12 marked REPRODUCED.
**Remaining PBIX pages: WBS pivots (8–9), Carnac cards (13).** Model/mode: Opus 4.8 (1M).

**Prior sitting (2026-06-13, cont.):** **#93 merged** (item 5 — forecast-drift animation +
locked axes; post-merge main CI green). Then **PR #94 (ADR-0038) — M18 item 6, PBIX
page 1**: a new **`/card/{name}` Schedule Card** reproducing the deck's *Metrics* page —
activity makeup, status split, completion-performance split, the **primary-constraint
distribution**, and a KPI stat-card row — all from the schedule's existing analysis plus
two new tested engine helpers (`compute_activity_makeup`, `compute_constraint_distribution`
in `engine/metrics/schedule_card.py`; lightweight dataclasses, NOT MetricResult, so the
dictionary-coverage test is untouched). Linked from the dashboard ("Card" row action),
carries the shared ask panel. PBIX-VISUALS.md page 1 marked REPRODUCED; the
constraint-distribution gap closed. Remaining PBIX pages (4,5,6–9,12,13) are the next
tranches. Model/mode: Opus 4.8 (1M context).

**Earlier 2026-06-13:** **#92 merged** (M18 item 4 — AI at full power; post-merge
main CI green). Then **PR #93 (ADR-0037) — M18 item 5**: the **forecast-drift animation**
(`/static/drift.js`, a Bow-Wave-style Prev/Next/Auto-play stepper on the /forecast page,
shown with ≥2 versions) plotting the three forecasts per version on a **LOCKED date axis**
(`_forecast_data` → `axis.min/max` across every version's forecasts + data dates +
baseline finishes), and the **Bow Wave count axis now locked** to the max bar across all
snapshots (`_cei_data` → `max_count`; `cei.js` no longer rescales each frame). Trend line
charts were already locked-by-construction (all versions on one fixed per-metric scale)
and the Path Gantt is a single-schedule timeline — both assessed, no change (ADR-0037 §4).
Pure presentation; parity untouched. **VERIFICATION STILL OWED (item 3, #91): the Duration
Bomb .mpp is NOT in this container** — on operator re-deposit, confirm computed finish
**2027-03-04**, completed tasks visible on /path, the "dates not supported by logic"
finding citing the template tasks. Model/mode: Opus 4.8 (1M context).

**Prior sitting (2026-06-12):** **#90 merged** (the eday fix), then **#91 merged** (M18 items 1–3,
ADR-0034: the **stored-date CPM mandate** — unstarted MANUAL tasks pin at their stored
start, unstarted logic-unbound auto tasks floor there, `CPMResult.date_driven` + the
cited **"N dates are not supported by logic"** finding, `Task.is_manual` model v2.1.0;
the **Path-Analysis stored-date display** — completed work at ACTUAL dates, per-row
`date_driven`, trace-coverage status line; the **full-width layout**). Post-merge main
CI green. Then **PR #92 (ADR-0035) — AI at full power, part 1**: `AIConfig.qa_mode`
(**interpretive default** — the model may analyze/derive grounded in the cited facts;
strict = the old wholesale figure-discard, still selectable), the **ask panel on EVERY
page** via the page shell (`_ask_panel_html` + `static/ask.js`, scope select = workbook
or any version; the /path-local panel removed, same ids/endpoint), **workbook-wide
facts** (`build_workbook_fact_sheet` reusing the briefing's cited statements +
latest-pair manipulation signals + latest forecasts; `POST /api/ask`), and the standing
**"AI can err — verify against citations"** disclaimer. The narrative/briefing
`reattach` gates and loopback-only egress are UNCHANGED. **VERIFICATION OWED: the
Duration Bomb .mpp is NOT in this container** — on operator re-deposit, confirm computed
finish **2027-03-04**, completed tasks visible on /path, and the logic finding citing
the template tasks. Model/mode: Fable 5 (1M context).

> READ THIS FILE FIRST to resume. Durable state lives here + `docs/STATE/SESSION-LOG.md` (append-only
> per-session history) + `docs/adr/` (decisions) + `docs/PLAN/RTM.md` (requirements). Never rely on
> chat history — everything important is committed to git.

## Repo / branch / PR mechanics (how this build runs)
- Repo: `polittdj/Schedule-Manipulation-Analysis-Tool-Experiment`. Everything ships to **`main`** via PRs.
- The harness assigns a fresh work branch each session (this sitting:
  `claude/inspiring-davinci-tez1dv`). Recreate it from `origin/main` for each new PR (the prior
  branch is deleted on squash-merge). To start fresh work:
  `git fetch origin main && git checkout -B <fresh-branch> origin/main`.
- Commit identity must be `Claude <noreply@anthropic.com>` (a Stop hook checks this — if it flags
  unverified commits run `git config user.email noreply@anthropic.com && git config user.name Claude`
  then `git rebase --exec "git commit --amend --no-edit --reset-author" origin/main`). **Force-push is
  blocked**; to publish a rebased branch whose remote tip moved, do an empty `git merge -s ours <old-tip>`
  so the push is a fast-forward (used this trick once already).
- After each push, open a **draft PR**. The operator merges PRs themselves (do NOT merge). Watch CI via
  the github MCP tools; CI **success is not delivered by webhook** — verify it explicitly. `send_later`
  is NOT available in this environment, so for the post-merge `main` run, use a short background
  `sleep` then re-check `actions_list`/`get_check_runs`. Unsubscribe once a PR is merged.
- CI: ruff + ruff format + mypy --strict + pytest (cov ≥70 overall, engine ≥85) + `pytest -m parity`
  (10/10, **non-negotiable**) + bandit + pip-audit, on push-to-main + every PR, Python 3.11 & 3.13.

## Build status
**COMPLETE — all milestones M1–M17 delivered** (M15 closed by PR #74/ADR-0030 after the operator
deposited the `.pbix`). The deck stays git-ignored CUI in `00_REFERENCE_INTAKE/pbix/` on the machine
that received it; it does NOT travel between cloud sessions (R-12) — if a future session needs it
again, ask the operator to re-deposit. Its DAX is XPress9-compressed: the reconstructed formulas are
in the metric dictionary; EPI / RatioMeasure / Start-and-Finish-Ratio await a DAX export.

## What shipped earlier sittings (PRs #58–#68)
- **#58** Full-audit remediation (ADR-0024): dropzone native form-submit; Windows `.mpp` temp-file fix;
  POST-only wipe/example; never-uncited citation; SPI(t); cached UID maps; one `_Analysis`/CPM per
  schedule; O(weeks) CPM date math (equivalence-swept); 2s Ollama probes; CI push-main-only + action
  bumps + pip cache; conftest golden fixtures; CSS/JS → `static/`; pyproject 1.0.0.
- **#59 / #60** Java discovery without admin: `SF_JAVA`→`JAVA_HOME`→PATH→**portable `tools/jre/` drop-in**
  (gitignored)→`%LOCALAPPDATA%\Programs`→machine roots, newest-version wins; actionable not-found error.
- **#61** Compare ordered by **data date** (not load order) + Net Finish Impact on the page.
- **#62** (ADR-0025) Trend across 10+ versions; Executive Briefing; **MS-Project-style Gantt** (timeline
  column, add/remove fields, milestones/summaries/critical/data-date). New `engine/trend.py`,
  `ai/briefing.py`.
- **#63** Docs/state refresh.
- **#64** Real-world `.mpp` tolerance (see lessons) + **schedule-level DCMA findings stay cited** (root-
  cause of the operator's "Internal Server Error") + resilient `/trend` `/compare` `/briefing` (skip &
  name unschedulable versions) + grid **per-column filters** + trace "show completed" toggle + waterfall
  driving Gantt + milestone diamonds.
- **#65** (ADR-0025 line) **Bow Wave / CEI** animated view (`engine/bow_wave.py`, `/cei`,
  `static/cei.js`): per-snapshot monthly finish bars (baselined/scheduled/finished), dashed
  data-date marker, "CEI – x.xx" callout, **Prev/Next + Auto-play movie**; CEI = finished ÷ what the
  prior snapshot planned for the month after its data date. Plus **Trend focus UID**
  (`/trend?target=<uid>`) and **de-overlapped chart labels** (strip common filename prefix, rotate −35°).
- **#67** Bow Wave / CEI hardening: capped month axis sheds the OLDEST months first (the newest
  status month + CEI period never fall off); CEI exactly 0.00 styles red/fail (falsy-zero bug).
- **#68** (ADR-0026) Full audit (3-agent fan-out; ~25 findings fixed: §6 citation crash class
  closed via NA-on-empty-populations + terminal citation anchors; BEI early completions;
  XER got MSPDI's tolerance classes + `complete_pct_type`-aware percents + UTF-16; MSPDI
  percent lags; NaN/Infinity = noise; `MANIP_ACTUAL_ERASED`; CUI redaction + JSON round-trip
  fidelity) + operator features: **session-wide Target UID** (`POST /target`, report panel +
  auto-trace, trend default focus, compare movement), **light/dark theme** (`theme.js`,
  CSS variables, live-re-theming SVG), **batch cap 10 → 20**.
  All of #58–#68 are **merged to `main`**.

## What shipped this session — PRs #69–#80 (all merged)

**PR #69 (ADR-0027) — the four ADR-0026 deferred items, MERGED:**
1. **Calendar-true day math**: every day↔minute boundary derives from
   `calendar.working_minutes_per_day` — the DCMA "44 working days" tripwire is now
   `forty_four_days_min(schedule)` (`metrics/_common.py`; DCMA06/DCMA08/Insufficient Detail),
   DCMA12 injects `100 working days` on the schedule's calendar, driving-slack tier bands +
   `driving_slack_days` convert per-calendar, and `float_analysis` day rendering does too.
2. **XER `CP_Units`** percent complete from TASKRSRC quantities (`_units_percent_by_task`):
   actual (`act_reg_qty`+`act_ot_qty`) ÷ at-completion (actual+`remain_qty`), summed per task;
   actual dates still rule; quantity-less / zero-at-completion falls back to the duration share.
3. **AI figure gate + per-request backend**: `reattach` keeps a rephrase only if it preserves
   the source's numeric figures exactly (`preserves_figures`, multiset; fail-closed to the
   verbatim sentence) — with that in place, the settings-selected backend now actually drives
   the prose: the report narrative is polished once per (schedule, backend, model)
   (`SessionState.polished`, `_polished_narrative`), the briefing builds with the routed
   backend, generation failure degrades deterministic (never a 500), and routing is cached 15s
   (`SessionState.backend_cache`, reset on settings save) so a down Ollama can't slow renders.
4. **Trend labels**: identical filenames no longer collapse to "…" — a label that empties
   after the common-prefix strip falls back to the version's data date (`trend.js shortLabels`).

**PR #70 (ADR-0028) — MSPDI/XER project-calendar parsing, MERGED:**
- Importers fill `Schedule.calendar` from the source's project calendar: **work weekdays**
  (source day 1=Sun..7=Sat → `weekday_from_source`), **per-day minutes** (span sums; differing
  days use the **dominant/modal** total — single-block model approximation), **holidays**
  (full non-working exceptions; working exceptions skipped + logged; weekend holidays dropped;
  ranges capped at 366 days).
- **MSPDI**: `Project/CalendarUID` resolved with a cycle-safe **base-calendar chain** (derived
  calendars inherit the base week; exceptions collect across the chain); legacy `DayType=0`
  and modern `<Exceptions>` both read; `DayWorking` with no times → 480. `.mpp` via MPXJ gets
  this for free.
- **XER**: `PROJECT.clndr_id` → CALENDAR row (fallback `default_flag=Y`); packed `clndr_data`
  read with anchored patterns (`(0||<1-7>()` day nodes, `s|HH:MM|f|HH:MM` spans,
  `(0||N(d|<serial>)` exceptions, Excel serial epoch 1899-12-30); grid-less rows walk
  `base_clndr_id`, then `day_hr_cnt`, then default.
- **Fail-soft**: any calendar surprise logs + degrades to the 8h/Mon-Fri default — never sinks
  the file. `Save .json` round-trips **holidays** now. Goldens' calendar IS the textbook
  standard (verified + pinned) → parity untouched.

**PR #71 (ADR-0029) — XER per-task cost roll-up:**
- `xer._costs_by_task` sums TASKRSRC assignment costs + PROJCOST expenses per task:
  `actual_cost` = act_reg+act_ot+expense act (ACWP basis); `cost` = actual + remaining
  (at-completion total); `budgeted_cost` = Σ target_cost **clamped ≥ 0** (the BAC/EV rule;
  credits in actual/remaining preserved). **Absence is honest**: fields set only when the
  file carried a value — cost-less `.xer` identical (EVM stays NA); the curated fixture has
  no cost columns (pinned). Cost-loaded `.xer` now drives real SPI/CPI/TCPI.

**PR #72 (merged) — self-review fix:** **recurring MSPDI exceptions** (Occurrences ≠ day
span) are skipped + logged instead of contiguously expanding into weeks of false holidays
(one weekly "Fridays off" pattern erased ~36 working days).

**PR #73 (merged) — calendar visibility:** the report page shows a **Working calendar** panel
(name, h/day + exact minutes, work week, holidays w/ 10-date preview) and `/api/analysis`
carries a `calendar` object — the imported time basis is verifiable on the page.

**PR #74 (merged, ADR-0030) — M15, the last milestone:** deck read locally (Layout JSON;
DataModel XPress9-compressed → reconstructed formulas, ambiguous measures deferred pending DAX
export); adopted **float bands** (0/<5/<10d, calendar-aware, offenders cited; 0-day band ==
Acumen Critical 41/37), **completion performance** (ahead/on/behind, avg days, duration
ratios, **MEI**, staleness), and the **three-method `/forecast`** (CPM / completion-rate /
IEAC(t)) with the per-version drift table; 22 metric-dictionary entries; RTM A6 +
FINAL-REPORT closed.

**PR #75 (merged) — exact-ratio IEAC(t):** the forecast divided by the 2-decimal display
SPI(t) (golden P5 read 9 days early); the math now uses the exact ES/AT ratio (display still
rounds). Plus a /forecast falsy-zero display trap (#67 class).

**PR #76 (merged) — user-docs catch-up:** USER-GUIDE + README now cover the imported
calendar, the three new report panels, and the /forecast page (everything #70–#75 shipped).

**PR #77 (merged) — the unique desktop icon + favicon:** `packaging/make_icon.py` redesigned
(stdlib, 4x supersampled, deterministic): dark tile + white ▲ + Gantt waterfall + gold
data-date line, 5-entry 256..16 PNG-in-ICO; same bytes = `/static/favicon.ico` + Linux PNG;
sync/determinism pinned by tests. Installer: `packaging\windows\Install-Desktop-Shortcut.ps1`.

**PR #78 (merged) — the icon opened a dead port:** `pythonw.exe` starts with
stdout/stderr = None; uvicorn's logging setup touched them and the server died right after
the browser-open timer. `launcher._ensure_streams()` rebinds missing streams to devnull
(never a log file — request paths carry schedule names). Regression drives the real
uvicorn.Config with None streams.

**PR #79 (merged, ADR-0031) — Path Analysis + ask-the-AI:** `/path` over the SSI-parity
driving-slack engine: target UID (session target pre-fills), user secondary/tertiary
day-bands, data grid LEFT (add/remove MS-Project fields; tier/substring filters;
hide-100%-complete), **scalable** Gantt RIGHT (px/day zoom, month ticks, gold data-date
line); `/api/driving` extended with grid fields + ISO dates. **Ask the AI** (`ai/qa.py`,
`POST /api/ask/{schedule}`): engine-computed cited fact sheet; Null backend = matching
facts verbatim; a model answer containing any figure the engine never computed is
discarded wholesale.

**PR #80 (merged, ADR-0032) — real-file fixes:**
- **Driving tiers classify on whole working days** (slack floored on the schedule's
  calendar): real stored dates carry time-of-day raggedness, so chains SSI shows at
  "0 days" carried 30–450 minutes here and fell out of DRIVING (operator measured **4 vs
  SSI's ~66**). Goldens are exact day multiples → parity untouched; boundaries pinned.
- **The server killed itself mid-load**: async `/upload` parsed on the event loop, starving
  heartbeats past the 10s grace → the auto-shutdown watchdog fired. Upload now runs in the
  threadpool; an in-flight request counter holds the watchdog; completions refresh the beat.

**PR #81 (merged) — state-docs recovery:** the prior session's final HANDOFF consolidation
was stranded on the work branch after #80's merge snapshot; restored as base + updated for
the merged state (this file's lineage).

**PR #82 (merged) — the synthetic verification battery (`docs/TEST-PROJECTS.md`):**
`tools/make_test_projects.py` deterministically generates 8 fictional MSPDI files into
`tests/fixtures/test_projects/` with an **MS-Project-faithful block calendar**: **TP1**
progressed + ragged actual times (driving tiers to UID 43 = 13/1/2/2; completed UIDs carry
210/210/120 MINUTES that floor to DRIVING — the #80 4-vs-66 class as a fixture); **TP2**
4×10 Mon–Thu 600-min calendar + 4 holidays (float bands 7/12/13; the exactly-44-day task
stays OUT of High Duration — calendar-true boundary); **TP3** hand-seeded DCMA counts
(Logic 4 / Leads 2 / Lags 3 / FS 76% / Hard 2 / Neg-float 3 / High-dur 2 / Invalid 4 /
BEI 0.62); **TP4 v1–v5** monthly series whose v4 erases UID 19's actual start AND quietly
slips its baseline (both MANIP signals fire, pinned; honest v2→v3 fires neither). Plus the
MSP **VBA module** (SF_VerifyImport / SF_SaveAsMpp / SF_ImportFolderToMpp) and per-file
SSI/Fuse recipes with pinned expected values. The operator's MSP import caught a real
generator bug (top-down summary rollup gave UID 0 a year-0001 baseline) — fixed
deepest-first + a battery-wide date/duration sanity guard.

## Lessons learned (carry forward)
- **Real stored dates are ragged to the minute; SSI thinks in whole days.** Any tier/driving
  classification must compare on the floored-day axis or real files undercount the driving
  path drastically (4 vs 66). And **never run imports on the event loop** — heartbeats starve
  and the auto-shutdown watchdog kills the server mid-load (in-flight requests now hold it).
- **The curated goldens (Project2–Project5) are self-contained; real `.mpp` exports are NOT.** The MSPDI
  importer (the `.mpp`→MSPDI→model path) was stricter than both the CPM engine and the XER importer.
  Real files need tolerance for: **external/cross-project predecessor links** (drop), self/duplicate
  links (drop), **ALAP** and **dateless constraints** (→ASAP), **timezone-tagged dates** (→naive local),
  **out-of-range %-complete** (clamp 0–100), **negative scheduled/actual costs** (keep; clamp only the
  baseline/BAC to ≥0). All in `importers/mspdi.py` + `importers/_common.py` + `model/task.py`.
- **The §6 "every statement cited" gate is a real crash surface.** A schedule-level DCMA check (Critical
  Path Test, CPLI) that FAILS had no per-activity offenders → uncited finding → `UncitedStatementError`
  → every page for that schedule 500'd. Fixed by citing the tested/most-negative-float activities AND a
  fallback in `recommendations._dcma_findings` (cite the finish-controlling chain for any offender-less
  failed check). **Any new finding source must guarantee a citation.**
- **Multi-version views must degrade, never 500** on one bad file — see `_solvable_versions()` in
  `web/app.py` (skip + name unschedulable versions).
- **Parity is the guardrail for all of this:** every tolerance/normalization only fires on constructs the
  curated files lack, so goldens parse byte-identically (145 tasks, 176/178 links) and `pytest -m parity`
  stays 10/10. Run it after any importer/engine change.
- **Acumen "summary" count excludes the UID-0 project row** (briefing uses 18, not 19).

- **Re-create the branch from origin/main after EVERY merge** before new work — building on
  the stale pre-squash tip made PR #80 initially dirty (it dragged the merged #79 commits);
  repair = cherry-pick onto fresh main + `-s ours` absorb of the old tip (no force-push).
- **The Stop hook flags GitHub's own squash commits** (committer noreply@github.com) when the
  local branch sits on main with nothing pushed: resolve with
  `git reset --hard origin/claude/clever-carson-uovtkk` — never rewrite merged history.
- **The GitHub MCP token can expire mid-session** ("requires re-authorization"): PR
  state can still be inferred via `git ls-remote origin main` (tip changes on merge);
  creating PRs/reading CI needs the operator to re-authorize the connector.
- **Heavy work must never run on the event loop** and **classification must use SSI's
  whole-day axis** (see PR #80 above) — both bit on the operator's first real-file run.

## Operator environment (CRITICAL — this caused most friction)
- **Windows, work laptop, NO admin rights.** Cannot run MSI installers (`winget` Java install exits 1602).
  → Java via the **portable JRE zip extracted into `…\tools\jre\`** (no admin). Steps are in
  `docs/USER-GUIDE.md` + `README.md`.
- Install folder: `C:\Users\dpolitte\Documents\Schedule-Manipulation-Analysis-Tool-Experiment`.
  PowerShell needs the `.\` prefix: `.\.venv\Scripts\Activate.ps1`. Editable install — after
  `git pull origin main` no reinstall is needed unless deps changed.
- The launcher prints `…serving the dashboard at http://127.0.0.1:<RANDOM-PORT>`; the dark
  **"▲ SCHEDULE FORENSICS"** page is the real tool. A separate **OLD program on `127.0.0.1:5000`**
  (white, "Schedule Manipulation Analysis **Tool**", JSON paste box) is a stale pre-greenfield app — NOT
  this codebase; tell the operator to ignore `:5000`.
- Operator workflow: merge each PR on GitHub, then `git pull origin main` + relaunch. They paste
  PowerShell logs/screenshots; red import notices name the file + reason (CUI-safe) — ask for that text.

## Green state
**Re-audited 2026-06-17 on fresh `main`@#126 (`d468bf8`) from scratch — full CI-exact gate:
906 passed, 3 skipped; parity 10/10; engine cov 97%; overall 95.21%; ruff/format/mypy/bandit all
exit 0.** The doc-guard `tests/test_state_docs.py` passes (this HANDOFF names ADR-0067, the highest
on disk); the air-gap/egress guards pass (36). The 3 skips are the real-`.mpp`/Java cases — no
`.mpp` fixture travels into the container (`00_REFERENCE_INTAKE/` is git-ignored + empty).
CI also runs pip-audit on Python 3.11 + 3.13. Verify locally:
`ruff check . && ruff format --check . && python -m mypy && python -m pytest --cov=schedule_forensics --cov-fail-under=70 && coverage report --include='*/schedule_forensics/engine/*' --fail-under=85 && python -m pytest -m parity && bandit -q -r src`.
(In a fresh remote container run `pip install -e '.[dev]'` FIRST — the preinstalled venv ships
without the web/dev deps. Use `python -m pytest`, not bare `pytest`: the PATH `pytest` is a
separate uv tool that cannot see the editable install. A doc-guard test
`tests/test_state_docs.py` requires this HANDOFF to name the highest ADR on disk.)

## Next steps / open items — THE M18 WORK ORDER (operator, 2026-06-12) — **COMPLETE**

**ALL EIGHT M18 ITEMS SHIPPED (see the strikethroughs below); the post-M18 tab-visuals
follow-ups #103–#113 are also merged.** This section is retained as the work-order record.
The only outstanding verification is real-data: re-deposit `Project2_Duration_Bomb.mpp` and
confirm the ADR-0043 computed finish **2027-02-24** (the pre-ADR-0043 mandate below quoted
2027-03-04 / 8-5-2026 — superseded once summary logic was lowered; see ADR-0043), completed
tasks visible on /path at their actual dates, the "dates not supported by logic" finding
citing the template tasks, and the hide-completed toggle (ADR-0051) acting on real rows.
The original backlog, for the record:

1. ~~Path Analysis completed tasks never show~~ (PR #91, merged; Duration Bomb
   re-verification owed, see above).
2. ~~Use the FULL screen width~~ (PR #91, merged).
3. ~~Sparse-logic CPM mandate~~ (PR #91/ADR-0034, merged; re-verification owed).
4. ~~AI at full power~~ (PR #92, COMPLETE: interpretive mode + ask panel on ALL
   pages with workbook-wide facts + standing disclaimer + Briefing reformat
   [ADR-0035] + the OpenAI-compatible second local backend with the dual-model
   figure-agreement cross-check [ADR-0036]; loopback-only egress preserved).
5. ~~Forecast-drift ANIMATION + locked axes on the animated visuals~~ (PR #93/ADR-0037:
   the /forecast Bow-Wave-style drift stepper on a locked date axis + the Bow Wave count
   axis locked to the global max across snapshots. Trend charts were already
   locked-by-construction across versions; the Path Gantt is a single-schedule timeline
   with no animated metric axis — both assessed, no change needed).
6. **PBIX visual reproduction** — docs/PLAN/PBIX-VISUALS.md is the spec (14 pages,
   engine coverage map; DAX intake complete, RatioMeasure is a dangling binding).
   **Page 1 (Metrics / Schedule Card) REPRODUCED** (PR #94/ADR-0038). NEXT tranches:
   Cross File Comparison (pg 4), Float Analysis (pg 5), the Finishes month curves
   (pg 6–7), WBS-grouped Completion + SPI/ES pivots (pg 8–9), Slippage curves (pg 12),
   the Carnac forecast cards (pg 13). Remaining gaps: activity-type profile, WBS
   pivots, start/finish curves, TotalFloat/FreeFloat sums, avg-tasks-per-month.
7. ~~CPM path-evolution animation~~ (PR #100/ADR-0044: the `/evolution` Bow-Wave-style
   stepper — per version the critical path with entered/left/stayed + duration-change
   badges, and a callout for finish movement + schedule-optics signals [durations cut on
   path, logic removed], flagging a path that sheds work while the finish holds steady).
8. ~~Forecast explainer + Trend page expansion~~ (PR #102/ADR-0046: the `/forecast`
   methodology explainer + static spread ruler; `MetricTrend.offenders_by_version` + the
   `/trend` "Quality drill-down & animation" panel [locked-axis per-metric offender-count
   stepper + per-version offender lists] + the full per-version Excel/Word offenders table).
   **M18 COMPLETE — all eight items shipped.**

1. **TP1-vs-SSI: CLOSED with full parity (2026-06-12).** All 18 traced tasks matched;
   live driving path UID-for-UID; non-zero slacks exact to SSI's display rounding;
   sub-day completed-task fractions are a documented model residual the whole-day floor
   absorbs (PARITY-REPORT + TEST-PROJECTS carry the verified tables). Remaining battery
   work: **Fuse re-run on a rebuilt TP3.mpp** (the Leads tasks-vs-links and
   Insufficient-Detail definitional rows), and **TP4 v1–v5 in the tool** (Compare must
   flag the UID-19 manipulation pair; Trend + Bow Wave/CEI on the five snapshots).
   The real-file 4-vs-66 re-test from #80 remains worthwhile but is now low-risk.
2. **Respond to operator feedback** on real `.mpp`/`.xer` files — tolerance classes live in
   `importers/_common.py`; ALWAYS re-run `pytest -m parity`. Watch how the new surfaces
   (Path Analysis, ask-the-AI, float bands, `/forecast`) read on real data.
3. **Deck measures awaiting a DAX export** (ADR-0030): EPI, RatioMeasure, Start-and-Finish
   Ratio — implement exactly when the operator provides the measure text; do not guess.
4. **per-task calendars** (P6 `TASK.clndr_id`, MSP resource calendars) — only if the
   operator's real programs mix calendars materially.
5. If the operator enables real Ollama generation: watch quality — narrative/briefing
   rephrases are figure-gated (`reattach`), ask-the-AI is figure-subset-gated (`ai/qa.py`).
6. **Tune the Bow Wave / CEI visuals** against real data vs the reference decks if they don't match.
7. Keep `docs/STATE/HANDOFF.md`, `SESSION-LOG.md`, and `docs/FINAL-REPORT.md` test counts current.

## Resume command for a NEW session
Paste this as the first message:
> Resume the Schedule Forensics build. Read `docs/STATE/HANDOFF.md` first — work the OPERATOR
> BACKLOG in its listed order. `main` is green & current at **#126** (`d468bf8`); the last CODE PR
> was #125 (Fuse Ribbon), #126 was a docs-only reconcile — there is no open code PR.
> Recreate the work branch from fresh main (`git fetch origin main && git checkout -B
> <fresh-branch> origin/main`), then tackle the REMAINING items, **bugs first**: (A) the Path
> Analysis driving/secondary/tertiary-to-target
> chart is wrong (`path.js` + `/api/driving`) and the `/analysis` driving-path + project-schedule
> Gantt scaling is wrong (it's %-squeezed with no adjustable scale — convert to the `/path`
> px-per-day + scroll model); **I owe you a question — please attach a screenshot of the wrong
> `/path` chart and a `/analysis` Gantt so I fix them precisely.** Then (B) MS-Project-style
> dropdown filters (select-all/deselect), (C) the path filter on BOTH `/analysis` and `/path`
> with hide-completed + adjustable scale + full wrapped task names, (D) the Fuse year Trend/Phase
> view, (E) Data-Date/Slippage redesign (overlaid lines + show/hide legend), (F) Bow-Wave totals
> + target-UID highlight. Insufficient Detail™ / Float Ratio™ / EPI / RatioMeasure stay DEFERRED
> until you supply the exact Fuse/DAX formula — don't guess. Setup: `pip install -e '.[dev]'`
> first; drive the gate with `python -m pytest` (PATH `pytest` is a separate uv tool); keep
> `pytest -m parity` 10/10; run bandit UNPIPED; open DRAFT PRs (don't merge — I do that); never
> let schedule data leave the machine (loopback-only air-gap). Model: Opus 4.8 (1M context).
