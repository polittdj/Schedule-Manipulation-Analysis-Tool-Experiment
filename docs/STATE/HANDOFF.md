# Handoff — 2026-06-17 (PRs #81–#115 MERGED; **one OPEN draft PR: ADR-0059 — Ask-the-AI full local evidence / release local Ollama**; M18 COMPLETE + tab-visuals tranche + 3rd-audit loopback hardening shipped)

> **IN FLIGHT (2026-06-17): Operator backlog from the big multi-part request.** The operator
> ordered a large set of UI/engine/AI improvements and chose the **start order**: (1) Ask-the-AI
> + release local Ollama [THIS PR, ADR-0059]; then the rest as separate PRs — chart legibility
> + zoom/fullscreen + legends on ALL charts; Target-UID actually driving every page;
> critical-path removal & "gained float" counterfactual analysis; Diagnostic Brief trends/
> risks/opportunities/recovery; Data-Date & Slippage redesign as **overlaid line families with
> a clickable show/hide legend**; Bow-Wave running totals + target-UID highlight during
> animation; surface the DCMA 1–14 definitions on the Interactive Analysis page. **Ollama
> policy decided: free local analysis, KEEP the strict loopback-only air-gap (no data leaves
> the machine).** Work each as its own tested, parity-green draft PR.

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
**CI: 872 passed, 3 skipped; parity 10/10; engine 97%; overall ~96%; egress + air-gap green;
bandit + pip-audit clean.** (Baseline `main`@#114 was **850/3**; this audit's open PR adds 22 guard
tests in `tests/guards/test_endpoint_scheme.py` → **872/3** in CI. The 3 skips are the real-`.mpp`
parity cases — no fixture travels into CI. **Locally with `Project2.mpp` deposited this session the
count is 874 passed / 1 skipped**: the two native-parse cases ran and matched golden — 145 rows /
144 activities / "Commercial Construction"; only the Project5 case skips.) **This session's open PR
(ADR-0058)** hardens the local-AI egress guard to validate URL **scheme + host** (`is_local_http_endpoint`
rejects `file://localhost`, `ftp://`, `gopher://`, remote `http(s)`) and refuse HTTP redirects
(`_NoRedirect`), and fixes the `test_parse_real_mpp` skip guard to gate per-file. CI also runs
pip-audit on 3.11 + 3.13. Verify locally:
`ruff check . && ruff format --check . && python -m mypy && python -m pytest --cov=schedule_forensics --cov-fail-under=70 && coverage report --include='*/schedule_forensics/engine/*' --fail-under=85 && python -m pytest -m parity && bandit -q -r src`.
(In a fresh remote container run `pip install -e '.[dev]'` into `.venv` FIRST — the preinstalled
venv ships without the web/dev deps. Use `python -m pytest`, not bare `pytest`: the PATH `pytest`
is a separate uv tool that cannot see the editable install.)

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
> Resume the Schedule Forensics build. Read `docs/STATE/HANDOFF.md` first. There is **one OPEN
> draft PR — ADR-0058** (loopback AI-endpoint scheme/redirect hardening + native-`.mpp` parity
> confirmation), branched from `main`@#114, awaiting the operator's merge; once it merges,
> recreate the work branch from fresh main before any new work. M18 (items 1–8) and the
> tab-visuals follow-ups (#103–#113) are all merged, so the only remaining work is
> verification/real-data. If the operator re-deposits the reference `.mpp`s
> (`00_REFERENCE_INTAKE/` is empty in a fresh container — the `.mpp`s and the SemanticModel zip
> live on the machine that received them; ask me to re-deposit), verify the Duration Bomb
> computes **2027-02-24** (ADR-0043) and the Large File's driving tiers match SSI (ADR-0045);
> otherwise watch how the live surfaces (Path Analysis, Critical-Path Evolution, ask-the-AI,
> float bands, /forecast, /trend, Dashboard cards) read on real `.mpp`/`.xer`. Recreate the
> harness-assigned work branch from fresh main (`git fetch origin main && git checkout -B
> <fresh-branch> origin/main`) after EVERY merge. Run `pip install -e '.[dev]'` into `.venv`
> first if tools are missing, and drive the gate with `python -m pytest` (the PATH `pytest` is a
> separate uv tool that can't see the editable install). Keep `pytest -m parity` at 10/10, run
> bandit UNPIPED, open draft PRs (don't merge — I do that), and never let schedule data leave
> the machine. Model: Opus 4.8 (1M context).
