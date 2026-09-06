# ADR-0467 — WP6b: the ledger TAIL verified by execution — eleven rows CONFIRMED and fixed red-first, six REFUTED, three UNVERIFIABLE as filed, one measured and left

- **Status:** Accepted — 2026-09-06 (POLARIS² audit campaign, WP6b; SOLO lead, fix-as-verified)
- **Version:** 1.0.240 (1.0.239 is claimed by the open draft PR #640 / ADR-0466; ADR numbers 0467+ for the same reason)
- **Extends:** ADR-0463 (WP6 — the method: re-derive the finder's line as of `1b833c6a`, build the refuting check, fix as verified), ADR-0391 (the actual-start floor), ADR-0309 (the resume floor), ADR-0430 (negative float on the stored basis), ADR-0446/0465 (the drill panels' family), ADR-0457 (I-01 population disclosure), ADR-0466 (function-string waits), ADR-0393 (QC-1/QC-2)
- **Ledger:** `docs/STATE/AUDIT-2026-08-27.md` (WP6b row) · row source `docs/STATE/AUDIT-2026-08-16.md` (REPORTED — round 2/3 finder claims; the detail of MF-07/09/10 and MC-08 was lost with the round-3 pool)
- **Shipped:** `engine/cpm.py` · `engine/sra.py` · `engine/manipulation.py` · `engine/metrics/_common.py` (+ `cei` · `completion_performance` · `dcma14` · `evm` · `fei_bri` · `field_forecast` · `float_bands` · `schedule_quality`) · `importers/json_schedule.py` · `importers/xer.py` · `web/app.py` · `web/components.py` · `web/margin.py` · `web/analysis.py` · `web/ssi.py` · `web/help.py` (+ `docs/METRIC-DICTIONARY.md` regenerated) · `ai/brief.py` · `static/histogram.js` · `static/ribbon_drill.js` · `static/findings_drill.js` · `static/driving_tiers.js` (r11 digest re-baselined, dated) · `static/dashboard.js` · 15 NEW test modules · TST-02/TST-03/IMP-03 repaired in place · the r11 `driving_tiers.js` digest

## Context

Twenty-seven rows had sat REPORTED since 2026-08-16. Each was re-derived from the finder's line as it
read then (`git show 1b833c6a:…`) or, where the finder's detail was lost, from the mechanism the row
names in the current tree; each got a check built to REFUTE it and run on a sandbox before a line
changed. Red was observed first on the pristine tree (21 failures + 1 module red at import across the new
modules; every guard that holds on both trees passed), green after, and a 23-mutation battery on scratch
copies of the FINAL code under `PYTHONPATH` went red BY NAME 23/23 — after the battery itself was caught
reporting a mutation that had not landed (an anchor missed a blank line; the runner now aborts loudly
on a failed patch, and the M23 verdict below is the re-run).

| row | finder claim (08-16) | what execution showed | verdict |
| --- | --- | --- | --- |
| **CPM-03** "docstring states the ADR-0391 rule unconditionally" | The rulebook promised `es = max(logic_es, actual_start)` for every started task; both forward passes applied the floor only in the no-pin branch. A started MSO/MFO task was scheduled at its CONSTRAINT date (synthetic: MSO 2026-03-02, actual start 03-16 → ES offset 0, finish two weeks early, successor pulled with it). Oracle: MS Project's own stored Start equals the Actual Start on **240 of 240** started tasks in the fixture corpus, constraint or not; no golden carries a started MSO/MFO task (the 10 started+constrained are SNET at their actual start), so the corpus is byte-identical by construction. | **CONFIRMED-FIXED** — the floor applies after the whole pin/stored chain in BOTH passes (the stored-pin branches only ever hold unstarted tasks); the pin's logic-vs-constraint violation is still measured first; a task started BEFORE its pin keeps the pin (a floor never moves earlier) |
| **CPM-04** "`network_finish` default 0 fabricates a finish" | `compute_cpm` on a summary-only schedule returns empty timings and `project_finish == 0` — the project start. Measured on a served summary-only session: the analysis takeaway ("computed finish 01/01/2024"), the brief ("its network computes a finish of 2024-01-01"), the margin page + `/api/margin/dashboard` + `/api/margin/risk`, `/api/dashboard`'s `cpm_finish`, `/api/sra` and `/api/sra/ssi` all printed the project start under a finish label. | **CONFIRMED-FIXED at the presentation** — the engine's empty result stays (a well-defined degenerate CPM; `recommend`, month curves and the terminal-citation fallback rely on it): the analysis header says "no schedulable activity, so no computed finish" with an em dash, the brief sentence says so, every multi-version resolver (`_solvable_versions` ×3, `_latest_solvable`, `_sra_selected`, the margin resolver) skips a FILE with no schedulable activity by name (the skipped notice names it) and the dashboard card ships `cpm_finish: null` (its script prints an em dash). **The skip is scoped to the FILE, never to a filter that left nothing in scope** — the first cut skipped both and turned the I-01 disclosure test red ("nothing to compare" became "load two versions"); that regression is now mutation M23 |
| **MF-03** "the published `critical` / `negative_float` formulas describe a basis the code does not use" | `critical` scores on the source tool's STORED Critical flag (`is_effective_critical`, pure-logic float only where no flag is stored) while the dictionary said `count(total_float <= 0 and incomplete)`; `negative_float` already stated its stored basis (ADR-0430). | **CONFIRMED (critical) — doc fixed; REFUTED (negative_float)** |
| **MF-04** "the lag/lead counters describe a basis the code does not use" | The ribbon's `number_of_lags` / `number_of_leads` count DISTINCT successor ACTIVITIES (the Fuse activity scope QC audit D22 fixed for the DCMA twins) while their formulas said `count(lag > 0) / activities`. | **CONFIRMED — doc fixed** (dictionary regenerated; `test_help_formula_basis.py` pins the words) |
| **MF-06** "`cei_critical` reads `stored_is_critical` instead of `is_effective_critical`" | The finder's proposed basis would EXCLUDE every completed activity (`is_effective_critical` requires `is_incomplete`), emptying the CEI numerator by construction; the stored-flag basis is the one validated EXACT against Acumen (ADR-0101). On a file whose source writes no flag (a P6 XER: 5 of 5 fixture tasks) the metric reads N/A — an honest N/A, not a wrong number. | **REFUTED as a defect** — the dictionary now says the N/A and its reason |
| **MF-08** "banker's rounding" | Every MetricResult value at 1–2 dp went through plain `round()` (half to even) while the one Fuse-measured place (logic density, D19) and `derived._half_up` round half up. Ties are common in small populations: CEI 1 of 8 read **0.12**, Critical 1 of 8 incomplete read **12 %**. | **CONFIRMED-FIXED** — `_common.round_half_up` (half away from zero, the spreadsheet ROUND rule) at the 30 MetricResult-feeding sites in `engine/metrics`; `-m parity` unmoved (no golden pin sits on a tie) |
| **MF-07 / MF-09 / MF-10** "docstring contradictions; two axis/unit mismatches" | The finder's detail did not survive the round-3 pool; nothing in the current tree names them. | **UNVERIFIABLE as filed** — what would settle them: the finder's cited lines (not recoverable); no blind sweep |
| **MC-04** "branch endpoint gating" | A branch whose FS tie is absent is dropped from the augmented network and reported `applied=False` in `SSIBranchStat`; the routes' docstrings say "accepted but reported inert after the run (never silently dropped)". | **REFUTED as "silent"** |
| **MC-05** "`_finish_of` silent project-finish substitution" | `_finish_of` returned the PROJECT finish whenever the focus UID was absent from the timings — a summary, an inactive/deleted activity, a stale UID from a setup file (`set_target` mirrors any target into the SRA focus, ADR-0196). `compute_sra_ssi(target=<summary>)` and `target=999999` both ran and reported the project finish under the focus's label. | **CONFIRMED-FIXED** — refused by name (`ValueError: SRA focus UID n is not a schedulable activity …`); the JSON routes already turn a ValueError into a 422 with the message |
| **MC-06** "a docstring guarantee" | The two guarantees in the family that could be identified hold by execution: `compute_jcl` raises `ValueError` on a schedule that is not cost-loaded; fragnet uids are assigned above every existing uid. | **REFUTED for the identifiable guarantees; the finder's target is otherwise UNVERIFIABLE as filed** |
| **MC-07** "a silent `(0.0, 0.0)` fallback in `RiskFactorTable.for_factor`" | A table not covering factors 1..5 answered a missing factor with `(0.0, 0.0)`: a Best Case of 0 % OF the ML and a +0 % Worst Case — a triangular (0, ML, ML) that halves the mean in silence. Unreachable from the form (always five rows) but reachable from an SSI setup file (five rows, duplicated factors) and from any Python caller. | **CONFIRMED-FIXED** — the table validates its factor set at construction (`ValueError` by name); the setup restore refuses a table that would not construct and keeps the session's rows |
| **MC-08** (the fifth MC row) | Detail lost with the round-3 pool. | **UNVERIFIABLE as filed** |
| **IMP-02** "`Schedule`'s unconstructable-inconsistency guarantee is not enforced" | The three promised invariants raise (duplicate task UID, dangling relationship at either end, duplicate resource UID). Not promised and not enforced: an assignment's `resource_id` with no resource, a `calendar_uid` with no calendar, a duplicated relationship — tolerated on purpose (the importers fall back by name) and named here. | **REFUTED as stated** |
| **IMP-03** "the schema change-control gate covers 6 of 11 model classes" | True: the five saved-view models (`Operand`, `Criterion`, `SavedFilter`, `GroupClause`, `SavedGroup`) sat outside `_EXPECTED_FIELDS`. | **CONFIRMED-FIXED** — frozen (a slipped field goes red, M21) |
| **IMP-04** "`_percent_complete` infers finished/started from the raw presence of `act_end_date`" | The only XER in the tree (5 tasks) carries NO `status_code` at all, so the date-presence rule is the only basis it offers; no reference XER exists to test P6's `status_code` against it. | **NON-REPRODUCED** — what would settle it: a real P6 export with `status_code` populated, diffed against the presence rule |
| **IMP-05** "XER maps `target_start_date` / `target_end_date` (P6 current plan) as baseline" | CONFIRMED by an independent oracle: MPXJ 16.2.0's `TableProjectReader` maps those columns to `PLANNED_START` / `PLANNED_FINISH`, never to a baseline; the importer's own comments (lines 228, 482) already say the P6 baseline lives in a separate project. P6 shows an activity's planned dates as its BL dates only while no baseline project is assigned. | **CONFIRMED — disclosed, values kept**: an import note names the provenance (rendered by /analysis). Setting the fields to None would blank HMI/BEI on every XER, including files where P6 itself shows the planned dates as BL; what settles the stricter choice is a Fuse export on an XER (UNVERIFIED) |
| **IMP-06** "save→reopen not model-identical when the calendar registry is empty" | `to_json_text` padded an empty registry with the project calendar; `model_dump` differed on `calendars`. | **CONFIRMED-FIXED** — the registry is written as is; the loader's older-save fallback is untouched |
| **MAN-02** "a resource-edit finding cites the CURRENT file for a task that exists only in the PRIOR" | `Deleted later (UID 7, current.xml)` — measured. | **CONFIRMED-FIXED** — cited to the prior file, the count said in the detail |
| **MAN-03** "an ABSENT remaining-work figure read as 0" | `(before or 0) != (after or 0)` — a None→N booking was counted among those that "only burned down remaining work with progress". No figure was fabricated (the row keeps its None); the sentence was. | **CONFIRMED-FIXED (wording)** — bookings that gained or lost a remaining-work figure between exports are counted apart from burn-down |
| **JS-02** "a document-level `fullscreenchange` listener per framed chart, never removed" | /mission: 29 listeners for 29 frames; a manual re-scan adds none. One listener per frame, no growth. | **REFUTED as a leak** (a per-frame listener where one delegated listener would do — observed) |
| **JS-03** "in four drill panels the text filter is destroyed by its own keystroke" | Chromium: typing `ab` left the filter at `a` with `document.activeElement === BODY` on /ribbon and /integrity; `driving_tiers.js` is the same pattern (`drilldown.js` redraws only its grid; `path_evolution.js`'s box is server-rendered — two of the finder's "four" were not affected). | **CONFIRMED-FIXED** — a rebuild the filter's own keystroke caused hands focus and the caret back to the new input, in the three panels; browser-driven on all three; `driving_tiers.js`'s r11 digest re-baselined with the reason |
| **JS-04** "panelkit's data-drawer branch is dead" | `/onepager` and `/onepager-compare` emit `data-sf-data` since ADR-0446/0465 and ten test modules drive it. | **REFUTED by now** |
| **JS-05** "CSS rules matching nothing" | 831 class/id tokens across the five stylesheets; 72 match nothing in the served views or scripts, 56 after crediting dynamic prefixes (`"sev-" + level`, `` `g-tier-${unit}` ``). | **MEASURED, deliberately not removed** — a rule that matches nothing renders nothing; removal is a design-system change with its own census, not an audit fix. The 56 are listed in the ledger |
| **JS-06** "`bucketOf` mislabels fractional float at band edges" | The bands are upper-bound inclusive (`0 < v <= 5`); a 0.75-day float (EVM1) and the XER's 0.5 sat under `1–5`, a 5.5 under `6–10`. | **CONFIRMED-FIXED** — labels `≤ 5 · ≤ 10 · ≤ 20 · ≤ 44`, the drill heading spells the open lower bound ("over 0 and up to 5 working days"), the export's mirror table matches by index in ASCII |
| **TST-02** "a zero-iteration loop" | `recommend(summary-only) == ()` — the loop asserted nothing. | **CONFIRMED-FIXED** — the measured outcome is pinned and the terminal-citation fallback the comment describes is tested directly (red when it returns nothing, M20) |
| **TST-03** "`sum(x) == sum(x)`" | A self-comparison. | **CONFIRMED-FIXED** — the population is counted independently from the schedule; red when the axis clips (M19) |
| **RC-02** the three never-2xx routes | `GET /export/{fmt}/ribbon-drill/{name}`, `GET /export/{fmt}/resource-drill`, `POST /sra/factor-table` each driven through a real success path. All three passed on the pristine tree — the gap was coverage, not the routes. | **CLOSED** (the 15 never-adverse POSTs stay WP7) |

## Decisions

1. **CPM-03 — the actual-start floor applies in every branch of both forward passes.** MS Project's rule
   is the oracle (240/240). The pin's `pin_violation` is still measured against logic before the floor;
   a task started before its pin keeps the pin.
2. **CPM-04 — the empty CPM stays an engine fact; the presentation says what it is.** Sentence sites
   fixed (analysis header, brief), resolvers skip an activity-less FILE by name, the dashboard ships null.
   A filter that empties the scope is never skipped (I-01 owns that disclosure) — pinned by M23.
3. **MF-08 — one rounding rule for displayed metric values:** `round_half_up` in `engine/metrics`.
   Left as measured: the two float-band integer roundings in `dcma14.py` (parity-locked classification),
   and the 176 `round(` sites outside `engine/metrics` (minute arithmetic, dashboards, trend deltas) —
   a follow-up census, not a blind sweep.
4. **MC-05 / MC-07 — refuse by name, never substitute in silence.** An SRA focus the network does not
   time raises; a factor table that does not cover 1..5 does not construct; the setup restore keeps the
   session's table when a file's would not.
5. **IMP-05 — provenance is said, the value kept.** The import note is the honest minimum until a Fuse
   oracle on an XER settles whether planned dates should stand in for a baseline at all.
6. **JS-03 / JS-06 — the drill filter keeps its caret; the band labels admit what they hold.** The
   `driving_tiers.js` digest re-baseline is dated and reasoned in the r11 contract.
7. **Docs are code here:** `help.py` formulas describe the basis the code uses; the dictionary is
   regenerated; `test_help_formula_basis.py` pins the words.

## Verification (QC-1)

- **Red first, on the pristine tree:** 21 failed + `test_round_half_up.py` red at import across the
  15 new modules; the guards that hold on both trees (63) green — among them the three RC-02 success
  paths (the routes were never broken, only never driven).
- **Green:** the 15 modules + the three repaired ones **90 passed** (the JS-03 module in Chromium on
  three drills); the 108-module web/ai/guard subset the changes touch **1,120 passed / 3 skipped / 1
  failed** on the first run — the failure was the I-01 regression above, fixed and now M23; the
  engine + importer + model + parity suites: figure in the session log (the first run was killed
  without a summary under five concurrent jobs; re-run alone).
- **Mutation, on scratch copies of the FINAL code under `PYTHONPATH` (the shadow proven by
  `schedule_forensics.__file__`), each red BY NAME — 23/23:** the floor skipped under a pin (main pass
  2, exec-calendar pass 1) · MAN-02 cited to the current file · MAN-03 burn-down miscount · IMP-06
  padding restored · IMP-05 note dropped · MC-07 validation removed (engine 2 + setup guard 1) · MC-05
  silent fallback restored (2) · MF-08 banker's rounding restored (3) · MF-03 formula reverted · JS-06
  chart labels reverted · JS-06 mirror table reverted · JS-03 refocus removed in each of the three drills
  (3, browser) · CPM-04 analysis header reverted · CPM-04 SRA resolver accepting an activity-less file ·
  CPM-04 brief sentence reverted · TST-03 axis clipping · TST-02 fallback returning nothing · IMP-03 a
  slipped saved-view field · RC-02 the export refusing a known metric · **M23** the pair resolver skipping
  an empty filter scope (the I-01 disclosure test red).
- **Statics:** ruff (whole tree) · format · mypy --strict (163 files) · bandit exit 0 · `node --check`
  every static file.

## Deliberately NOT done (measured, left alone)

- `evm.py`'s `actual_cost or 0.0` ACWP on a mixed population (its own EVM parity row, unchanged from
  ADR-0463) · `path_evolution`'s pure-logic per-version critical list · MF-05 · the 6 dead E501s ·
  the `citations.reattach` pin · the evolution 0 % cell.
- The 56 CSS tokens matching nothing (JS-05) — measured, listed, not removed.
- The `dcma14.py` float-band integer roundings and the `round(` sites outside `engine/metrics` (MF-08's
  residual) — a census first.
- IMP-05's stricter option (planned dates set to None on XER) — needs the Fuse-on-XER oracle.
- The 15 never-adverse POST routes (RC-02) — WP7.
- MF-07 / MF-09 / MF-10 / MC-08 — unverifiable as filed; no blind sweep.

## Consequences

- 11 rows move from REPORTED to CONFIRMED-FIXED with their measurements, 6 to REFUTED (each with the
  probe that refuted it), 3 to UNVERIFIABLE-as-filed, 1 to MEASURED, 1 to NON-REPRODUCED; RC-02's
  never-2xx list is empty.
- A started task under a constraint pin is scheduled when it started; no page prints the project start
  as a finish for a network with nothing in it; an SRA focus outside the network is refused by name; a
  factor table cannot silently zero a Best Case; a P6 import says where its baseline dates come from.
- Version 1.0.238 → **1.0.240** with ADR-0468 (1.0.239 / ADR-0466 ride the open #640); wheel + nine
  installers rebuilt in lockstep as the LAST step.
