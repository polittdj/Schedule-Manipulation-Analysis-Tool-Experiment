# MASTER RE-VERIFICATION & FIX-RECONCILIATION AUDIT — Schedule-Manipulation-Analysis-Tool

**Mode:** read-only / forensic / meta-falsification. **No remediation.** No source, test, fixture, config,
or threshold was modified. The only files created are this report and `audit/PARK-LIST.md`. The existing
`audit/AUDIT-REPORT.md` and `audit/PATH-FORWARD.md` were **not** overwritten. No network connection was
opened (air-gap verified by static inspection + a runtime guard call only).

**Ground truth:** HEAD `919d786` (clean tree) on branch `claude/schedule-tool-forensic-reaudit-7da8p1`.
Highest ADR on disk = **0130**, present in BOTH `docs/STATE/HANDOFF.md` and `docs/STATE/SESSION-LOG.md`
(`tests/test_state_docs.py` → 2 passed). Full gate re-run read-only this audit (raw output in §E):
ruff ✓ · ruff format ✓ (260 files) · mypy ✓ (85 files) · bandit exit 0 · **pytest 1670 passed / 7 skipped
/ 2 xfailed** · engine coverage 99.54% · `pytest -m parity` 10 passed / 1 xfailed · `node --check` ✓.

**Method:** the deps were not installed in the base image (`pydantic`/`fastapi` absent); a scratch venv was
built (`pip install -e ".[dev]"`, pydantic 2.13.4) **purely to execute** the existing code/tests read-only —
no repo file changed. Every claimed fix and every prior finding was re-derived by **re-executing the actual
code path or test**, never from a HANDOFF/ADR/report claim. Fan-out across four verification streams (M1+C2;
the ADR-0130 F-batch; the re-open hunt H1–H4/M2–M6; L-items + meta-falsification), each required to return
a live repro + `file:line`. The headline C1 round-trip and the new Float-Ratio defect were re-confirmed by
the auditor directly.

---

## 1. Executive summary (worst-first)

> **HEADLINE — a CRITICAL finding and ~15 other in-env-fixable findings are STILL OPEN, while the
> authoritative status doc says "only artifact-gated items remain."**

1. **C1 (CRITICAL) is STILL OPEN.** `to_json_text` (the Save .json path, `web/app.py:1159`) silently drops
   **12 fidelity-bearing fields** on a Save→reopen round-trip — including the Acumen-parity
   `stored_total_float_minutes` / `stored_is_critical`, plus `is_active` (which feeds the very M1 exclusion
   that *was* fixed), `custom_fields`, `calendar_uid`, and Calendar `working_days`/`day_segments`.
   Re-confirmed by a live round-trip this audit (§D, C1). **No ADR ever addressed it.** It was logged in
   `AUDIT-2026-06-25.md` as the #1 Critical, listed as "Wave 1 item 1" in two HANDOFF blocks, then dropped
   from the "current status" when the *other* audit trail's batch shipped (ADR-0130). This is the exact
   "Critical left open across sessions" failure the brief named — and it generalizes (below).

2. **The two audit trails were never merged, and the remediation followed only one of them.** ADR-0130
   executed the **F-set** roadmap (`audit/PATH-FORWARD.md`, findings F-01…F-12). ADR-0128/0129 closed the
   internal audit's two items that happened to carry standalone operator decisions (M1, C2). **Everything
   else in the internal audit's own 3-wave plan — C1, H1, H3, H4, M2, M3, M4, M5, M6, M7, M8, and the
   in-env Low items L2/L3/L5/L7 — was never executed and is still OPEN** (each re-confirmed live in §D).
   The only internal-audit Lows that got fixed (L1, L12) got fixed *because they were duplicated* in the
   F-set as F-04 and F-08. **Root cause: no single authoritative findings ledger** (see §F, Configuration
   Management). `docs/STATE/HANDOFF.md:3` states *"Audit in-env remediation batch DONE (ADR-0130); only
   artifact-gated items remain"* and its "REMAINING" block (`:23-35`) lists **only** artifact-gated items —
   silently dropping the internal audit's open in-env Wave-1/2/3 list that the *prior* HANDOFF block
   (`:57-61`) still correctly carried. **That top-line status is false:** C1 (Critical) and ~14 other
   findings are in-env-fixable and open.

3. **The ADR-0130 fixes that WERE made are real and verified** — F-02 (finish gap disclosed + guarded),
   F-03/F-07 (parity report synced to `case.json` + sync test), F-04 (critical-definition labeled), F-05
   (two new manipulation detectors firing on synthetic + the real UID-131 clamp), F-06 (title XSS escaped),
   F-08/F-12 (coverage config + docstring). M1 (inactive-task exclusion at 6 sites) and C2 (annotate-default
   AI mode) are likewise verified FIXED. **One ADR-0130 item is PARTIAL:** F-01's "engine-pinned / NOT
   Fuse-validated" marker exists in `PARITY-REPORT.md` prose (good for point-of-use disclosure) but **no
   test enforces it** — deleting the marker would fail no test, so the claim that "the circularity can't be
   silently forgotten" is not substantiated (§C, F-01).

4. **META-FALSIFICATION — a NEW defect neither prior audit found:** the **Float Ratio metric mixes two
   day-axes for elapsed-duration activities.** Remaining duration is put on the wall-clock axis (÷1440) while
   total float is always on the working-day axis (÷480) — a **3.0× (1440/480) distortion** for any elapsed
   in-progress activity, directly contradicting the metric's own docstring which claims unit-consistency
   "even with elapsed durations." Live-confirmed (§D, NEW-1): an activity whose unit-consistent ratio is
   **0.33** (tight) is reported as **1.0** (generous). LOW–MEDIUM: it corrupts a reported/citable number and
   the parity gate is blind to it (no golden carries an elapsed in-progress Normal activity).

**Bottom line.** "Everything is fixed" is false. The F-set roadmap was executed well; the internal audit's
roadmap was orphaned, leaving a Critical (C1) and a cluster of HIGH/MEDIUM importer-crash-safety and
fidelity findings open. The single most important corrective action is **not a code fix but a process fix:
one unified findings ledger** (this document is a first instance), so an in-env Critical can never again be
masked by a "batch DONE" status that refers to only one of two trails.

---

## 2. Unified findings ledger

Severity is the original trail's. **TRUE status** is this audit's re-derived verdict (evidence in §C/§D).
Confidence: CONFIRMED = reproduced live this audit; SUSPECTED = code read only, not executed this round;
UNVERIFIABLE-IN-ENV = needs an external artifact. **Testimony-defensible?** applies to any finding affecting
a reported number/parity claim: is the methodology/limitation disclosed *at the point of use* and
reproducible from committed artifacts?

| ID | Trail(s) | Sev | Fix claimed? (where) | TRUE status | Evidence (file:line / test) | Conf | Testimony-defensible? |
|----|----------|-----|----------------------|-------------|------------------------------|------|------------------------|
| **C1** | Internal | **CRIT** | none | **OPEN** | `json_schedule.py:180` to_json_text omits 12 fields; live round-trip §D | CONFIRMED | **N** — silent fidelity loss, not disclosed; reopened file degrades DCMA float |
| **C2** | Internal | **CRIT** | ADR-0129 | **FIXED** | `qa.py:426-430`, `backend.py:54` default `annotate`; live 3-mode repro | CONFIRMED | Y — guarantee re-scoped per mode in CLAUDE.md |
| **H1** | Internal | HIGH | none | **OPEN** | `app.py:6131` no isinstance guard; TestClient `affected:5`/`null`→500 + partial mutation | CONFIRMED | N/A (crash-safety, not a number) |
| **H2** | Internal | HIGH | none (by-design) | **OPEN (accepted-as-design)** | `citations.py:25,71-78` digit-only multiset; prose tamper survives | CONFIRMED | Y — CLAUDE.md concedes "guards digits, not prose" |
| **H3** | Internal | HIGH | none | **OPEN** | `xer.py:168` `_req_int` over all tasks; injected `task_id=GARBAGE`→ImporterError | CONFIRMED | N/A |
| **H4** | Internal | HIGH | none | **OPEN** | `xer.py:415-416` strict before drop-filter; `task_id=BADSUCC`→ImporterError | CONFIRMED | N/A |
| **M1** | Internal | MED | ADR-0128 | **FIXED** | 6 sites consult `is_active` (`_common.py:81`, `cpm.py:114`, +4); live DCMA pop 3→2 | CONFIRMED | Y |
| **M2** | Internal | MED | none | **OPEN** | `.githooks/pre-commit:13` regex omits `aft`/`docx`; `.gitignore` lacks both | CONFIRMED | N/A (Law-1 spec gap; low exposure — intake dir git-ignored) |
| **M3** | Internal | MED | none | **OPEN** | `json_schedule.py:168` fabricates `2025-01-06`; `parse_json_text('{"tasks":[]}')` repro | CONFIRMED | N — invents a CPM-anchor forensic input |
| **M4** | Internal | MED | none | **OPEN** | `mspdi.py:602` filters raw `<Summary>` not `uid==0`; crafted UID-0 leaks 2099 baseline | CONFIRMED | N — leaks into CPLI basis |
| **M5** | Internal | MED | none | **OPEN** | `app.py:5758` `round(rem/mpd,3)` vs `:5874` unrounded; `sra_risk.js:27-39` | CONFIRMED | N (sub-day) — magnitudes diverge client/server |
| **M6** | Internal | MED | none | **OPEN** | `citations.py:25` `\d+...` sign-blind; `preserves_figures("-5 days","5 days behind")`→True | CONFIRMED | N — sign is load-bearing (variance/float/slip) |
| **M7** | Internal | MED | none | **OPEN** | `path.js:404` no debounce; `gantt.js:146-155` per-cell styles | CONFIRMED | N/A (perf) |
| **M8** | Internal | MED | none (doc) | **OPEN** | `completion_performance.py:185-212` MEI can exceed 1.0; `help.py:742-748` no note | CONFIRMED | Y-ish — number correct, caveat missing |
| **L1** | Internal=**F-04** | LOW | ADR-0130 | **FIXED (labeled)** | `float_analysis.py:14-22` caveat + docstring 37→4; code still pure-CPM (by design) | CONFIRMED | Y — two surfaces now labeled distinctly |
| **L2** | Internal | LOW | none | **OPEN** | no `math.isfinite` in `app.py`; `_to_float("inf")`→inf; 422 later | CONFIRMED | N/A |
| **L3** | Internal | LOW | none | **OPEN** | `shutdown_offload` only at `app.py:1056`; no atexit/lifespan hook | CONFIRMED | N/A (mitigated by ProcessPool atexit) |
| **L4** | Internal | LOW | none | **SUSPECTED-OPEN** | not re-executed this round; prior: `sra_risk.js:51` early return | SUSPECTED | N/A |
| **L5** | Internal | LOW | none (ADR-0110 drift) | **OPEN / disclosed** | `dcma14.py:177` keys current `duration_is_elapsed`, not baseline | CONFIRMED | Y — ADR-0110-disclosed |
| **L6** | Internal | LOW | none | **SUSPECTED-OPEN (as-designed)** | not re-executed; prior: EVM BCWS finish-gated, scope-correct | SUSPECTED | Y — scope-documented |
| **L7** | Internal | LOW | none | **OPEN** | `mspdi.py:220` `_int`; `OutlineLevel=n/a`→ImporterError (whole file) | CONFIRMED | N/A |
| **L8** | Internal | LOW | none | **SUSPECTED-OPEN** | not re-executed; prior: `gantt.js` header-width-only offsets | SUSPECTED | N/A |
| **L9** | Internal | LOW | none | **SUSPECTED-OPEN** | not re-executed; prior: sra_risk.js derive math only substring-asserted | SUSPECTED | N/A |
| **L10** | Internal | LOW | none | **SUSPECTED-OPEN** | not re-executed; prior: brittle source-string offload test | SUSPECTED | N/A |
| **L11** | Internal | NIT | none | **SUSPECTED-OPEN** | not re-executed; prior: MSPDI lag-only dup links collapse | SUSPECTED | N/A |
| **L12** | Internal=**F-08** | LOW | ADR-0130 | **FIXED** | `pyproject.toml:119` `fail_under=70.0`; comment corrected | CONFIRMED | Y |
| **F-01** | F-set | HIGH | ADR-0130 | **PARTIAL** | marker in `PARITY-REPORT.md:153-155` prose; **no test asserts it** (sync test pins numbers only) | CONFIRMED | Y (disclosed) / parity is self-consistency |
| **F-02** | F-set | HIGH | ADR-0130 | **FIXED (disclosed+guarded)** | `forecast.py:101` as_scheduled; `test_data_date_finish_gap.py` 2 pass; engine still understates (06-26) but labeled | CONFIRMED | Y — stored finish surfaced + labeled |
| **F-03** | F-set | HIGH | ADR-0130 | **FIXED** | `test_parity_report_sync.py` 1 pass; stale −99/41-37/43-40 only as struck-through history | CONFIRMED | Y |
| **F-04** | F-set=L1 | MED | ADR-0130 | **FIXED (labeled)** | see L1 | CONFIRMED | Y |
| **F-05** | F-set | MED | ADR-0130 | **FIXED** | `manipulation.py:221,265`; `test_manipulation.py` 11 pass incl. real UID-131; live synthetic fire/no-fire | CONFIRMED | Y |
| **F-06** | F-set | MED | ADR-0130 | **FIXED** | `app.py:882` `_e(title)`; `test_title_escaping.py` 1 pass; live render no raw `<svg` | CONFIRMED | Y |
| **F-07** | F-set | MED | ADR-0130 | **FIXED** | `risks.md` R-02/R-13 updated; `adr/0045*.md:45` erratum present | CONFIRMED | Y |
| **F-08** | F-set=L12 | MED | ADR-0130 | **FIXED** | see L12 | CONFIRMED | Y |
| **F-09** | F-set | LOW | none (FS-scoped) | **SUSPECTED-OPEN (as-designed)** | not re-executed; `cpm.py:139` documents FS-scoping | SUSPECTED | Y — documented |
| **F-10** | F-set | LOW | none (ADR-0010) | **SUSPECTED-OPEN (as-designed)** | not re-executed; 17:00 vs 16:00 contiguous-calendar model | SUSPECTED | Y — documented |
| **F-11** | F-set | LOW | none (by-design) | **OPEN (accepted)** | `citations.py:71-78` digit presence not role; bounded to ungated interpretive | CONFIRMED | Y — CLAUDE.md "digits not prose" |
| **F-12** | F-set | LOW | ADR-0130 | **FIXED** | `qa.py:6-19` lists annotate(default)/strict/interpretive | CONFIRMED | Y |
| **F-13** | F-set | LOW | partial (ADR-0128/0130) | **OPEN (minor)** | `manipulation.py` shortened-dur scope; `is_active` not in `diff._TRACKED_FIELDS` (deactivation detected as change, no dedicated flag) | SUSPECTED | Y |
| **F-14** | F-set | LOW | none | **OPEN (doc)** | `driving_slack.py:73-74`, `health_extra.py:25` unsourced thresholds | SUSPECTED | partly UNVERIFIABLE — handbook absent |
| **NEW-1** | *this audit* | LOW-MED | n/a | **OPEN (new)** | `float_ratio.py:78-82` (÷1440) vs `:90` (÷480); docstring `:25-27` false; live 3× distortion §D | CONFIRMED | **N — docstring asserts a property the code violates** |
| **NEW-2** | *this audit* | LOW | n/a | **OPEN (new, weak)** | `manipulation.py:247-249` `MANIP_CALENDAR_LOOSENED` fires on net-zero weekday swap | CONFIRMED (low sev) | Y-ish — MEDIUM "confirm authorized" flag by design |

**Tally of TRUE status:** FIXED = 12 (C2, M1, L1/F-04, L12/F-08, F-02, F-03, F-05, F-06, F-07, F-12; counting
the L/F duplicates once → 10 distinct fixes) · PARTIAL = 1 (F-01) · OPEN (confirmed live) = **C1 + H1, H2,
H3, H4, M2, M3, M4, M5, M6, M7, M8, L2, L3, L5, L7, F-11** = 18 · SUSPECTED-OPEN (not re-executed, LOW/NIT) =
L4, L6, L8, L9, L10, L11, F-09, F-10, F-13, F-14 · NEW = 2 (NEW-1 confirmed, NEW-2 weak).

---

## 3. Re-verified fix table (Phase C — claimed fixes, evidence only)

| Claim | Verdict | Evidence (re-executed) |
|-------|---------|------------------------|
| **M1 / ADR-0128** inactive tasks excluded at `_common.non_summary`, `cpm._scheduled_tasks`, `driving_path`, `driving_slack.date_basis`, `vertical_integration`, DCMA12 | **FIXED** | All 6 sites quote `is_active`: `_common.py:81`, `cpm.py:114`, `driving_path.py:78-79`, `driving_slack.py:118-121`, `vertical_integration.py:55`, `dcma14.py:362`. diff/manipulation still read `schedule.tasks` (`diff.py:79`, `manipulation.py:75-76`) → deactivation stays detectable. Live: inactive task absent from CPM, DCMA pop 3→2. Goldens: 320×`<Active>1`, **0**×`<Active>0`. `test_inactive_tasks.py` 4 pass. |
| **C2 / ADR-0129** annotate(default)/strict/interpretive; `_annotate_unsourced`; strict discards; interpretive verbatim | **FIXED** | `backend.py:54` default `"annotate"`; gate `qa.py:426-430`. Live with fake backend emitting unsourced `31415`: strict→`None`, annotate→kept + `[AI-derived …31415]` footer, interpretive→verbatim. `test_qa.py`+`test_ask_everywhere.py` 28 pass. CLAUDE.md scoping accurate. *(Cosmetic: `answer_question` signature default is `strict` (`qa.py:365`); harmless — every caller passes the `annotate` config.)* |
| **F-01** §E change-metrics carry an "engine-pinned / NOT Fuse-validated" marker **that a test enforces** | **PARTIAL** | Marker prose present (`PARITY-REPORT.md:153-155`, `case.json` `change_P2_to_P5_engine_pinned`, `risks.md:9`). **But no test asserts the marker** — `test_parity_report_sync.py` pins only the numbers (Critical 4, DCMA06 44/44, −148, no_longer_critical 34) + forbids stale strings; deleting the "NOT Fuse-validated" label fails no test. The disclosure goal is met; the "can't be silently forgotten" guard is not. |
| **F-02** as-scheduled stored finish surfaced; TP4 v5 reported finish 2026-07-17 pinned; TEST-PROJECTS over-claim fixed | **FIXED** | `forecast.py:101` `FinishForecast("as_scheduled", …)`; `app.py:1881-1893` renders it; `test_data_date_finish_gap.py` 2 pass (CPM 06-26 vs stored/forecast 07-17). Engine pure-logic CPM **still** computes 06-26 (unchanged — disclosed, not silently understated). `TEST-PROJECTS.md:18` corrected to `finish>0`. |
| **F-03 / F-07** PARITY-REPORT regenerated from case.json; sync test; risks.md; ADR-0045 erratum | **FIXED** | `test_parity_report_sync.py` 1 pass; headline P5 Critical 4 / High-Float 44/44 / BSC 41-25 / −148 / focus 145; stale −99/41-37/43-40/UID-143 only as struck-through history. `risks.md` R-02/R-13 updated; `adr/0045*.md:45,56` erratum. |
| **F-04** float "critical" labeled distinct from stored critical; docstring 37→4 | **FIXED** | `float_analysis.py:14-22` "Definition caveat (ADR-0130 / audit F-04)"; docstring active value 4 (37 marked historical); code still pure-CPM `is_critical` (intentionally not unified — see ADR-0130 §5). |
| **F-05** MANIP_CONSTRAINT_ADDED (≤0 float clamp) + MANIP_CALENDAR_LOOSENED; fire on synthetic + real UID-131; silent on legit | **FIXED** | `manipulation.py:221,265`; reads `diff` constraint deltas + a calendar diff. `test_manipulation.py` 11 pass incl. real UID-131 ASAP→MSO + negative cases. Independent synthetic repro: both fire on the abuse signature, silent on benign re-plan/tightening. *(But see NEW-2: calendar detector FPs on a net-zero weekday swap.)* |
| **F-06** `_e(title)` at layout boundary; hostile title inert | **FIXED** | `app.py:882` `title=_e(title)` at `_LAYOUT.render`. `test_title_escaping.py` 1 pass. Live render of `</title><svg onload=alert(1)>` → escaped, no raw `<svg`. |
| **F-08** pyproject `fail_under==70` matches CI; comment corrected | **FIXED** | `pyproject.toml:119` `70.0`; comment `:114-118` accurate; `ci.yml:60` `--cov-fail-under=70`. |
| **F-12** `ai/qa.py` docstring lists 3 modes, annotate default | **FIXED** | `qa.py:6-19`. |

---

## 4. Re-open hunt (Phase D — live repro of items no ADR addressed)

### C1 — round-trip field-by-field diff (the headline)
Live (scratch venv): build a maximal `Task` and round-trip `parse_json_text(to_json_text(sch))`:

```
calendar_uid                42 -> None        *** LOST
outline_level                3 -> 0           *** LOST
is_estimated_duration     True -> False        *** LOST
is_level_of_effort        True -> False        *** LOST
is_active                False -> True         *** LOST   (re-activates an inactive task; defeats M1)
physical_percent_complete 33.0 -> None         *** LOST
stored_total_float_minutes -240 -> None        *** LOST   (Acumen-parity stored float)
stored_is_critical        True -> None         *** LOST   (Acumen-parity stored critical)
custom_fields  (('CA-WBS','X1'),('Risk','High')) -> ()  *** LOST   (group/filter population)
```
`to_json_text` (`json_schedule.py:215-259`) writes none of these; the model carries them
(`task.py:53,57,68,73,74,87,95,96,124`). The same omission drops `Schedule.custom_field_labels`
(`schedule.py:44`) and Calendar `working_days`/`day_segments` (`calendar.py:34,40`) → **12 fields total**,
matching the internal audit's "11+". This is the **only** Save path: `/download/{name}` → `to_json_text`
(`app.py:1152-1161`, linked from the "Save .json" UI at `:1071`); there is no `model_dump_json` alternative.
**Status: OPEN, CONFIRMED. Not testimony-defensible** — a reopened progressed file silently loses the
stored progress-aware float/critical that DCMA metrics prefer, with no disclosure.

### H1–H4, M2–M6 (each re-confirmed live)
- **H1 OPEN** — `app.py:6131` `tuple(u for u in item.get("affected", []) …)` has no isinstance guard; TestClient `POST /sra/ssi/load` with `affected:5`→500, `affected:null`→500; `sra_factor_rows`/`sra_focus_uid`/`sra_low/ml/high`/`sra_overrides`/`sra_factors`/`sra_bcwc` assigned before the crash → session half-mutated; `sra_risks` never reached.
- **H2 OPEN (by-design)** — `citations.py:25` `\d+(?:\.\d+)?`; `preserves_figures(src, "DELIBERATELY CONCEALED fraud: …")` with digits unchanged → True.
- **H3 OPEN** — `xer.py:168` `_req_int` over all tasks; `task_id=GARBAGE` in any TASK row → ImporterError (whole file).
- **H4 OPEN** — `xer.py:415-416` `_req_int` on TASKPRED endpoints before the drop-filter; `task_id=BADSUCC` → ImporterError even for a droppable link.
- **M2 OPEN** — `.githooks/pre-commit:13` `\.(mpp|mpt|mpx|xer|xml|pmxml|csv|xls|xlsx|pbix|mspdi|pkl|pickle)$`; `x.aft`/`x.docx`→ALLOWED; `.gitignore` lacks both.
- **M3 OPEN** — `json_schedule.py:168`; `parse_json_text('{"tasks":[]}')` → `project_start = 2025-01-06 08:00:00`.
- **M4 OPEN** — `mspdi.py:602` skips only raw `<Summary>`; crafted UID-0 (no `<Summary>`, baseline 2099) → model `is_summary=True` yet `project.baseline_finish = 2099` (correct leaf was 2030).
- **M5 OPEN** — `app.py:5758` emits `round(rem/mpd,3)`; `_affected_avg_remaining_days` (`:5874`) averages unrounded; `sra_risk.js:27-39` averages the rounded map → sub-day divergence (lines shifted from the audit's 5753/5853 but the gap is intact).
- **M6 OPEN** — `citations.py:25` no leading `-`; `preserves_figures("-5 days","5 days behind")` → True.

### M7, M8, L2, L3, L5, L7 (live/static re-confirm)
- **M7 OPEN** `path.js:404` no debounce; `gantt.js:146-155` per-cell inline styles per paint.
- **M8 OPEN (doc)** `help.py:742-748` MEI doc has no ">1.0 possible" note.
- **L2 OPEN** no `math.isfinite` in `app.py`; `_to_float("inf")`→inf (422 later).
- **L3 OPEN** `shutdown_offload` only at `app.py:1056`; no `atexit`/`@app.on_event`/`lifespan`.
- **L5 OPEN/disclosed** `dcma14.py:177` keys current `duration_is_elapsed`, not a baseline flag (ADR-0110).
- **L7 OPEN** `mspdi.py:220` `_int`; `OutlineLevel=n/a` → ImporterError (whole file).

### Meta-falsification — NEW defect (mandatory §2 obligation)

**NEW-1 — Float Ratio mixes day-axes for elapsed-duration activities (CONFIRMED).**
`engine/metrics/float_ratio.py:78-82` computes `remaining_days` via `duration_days_axis(..., is_elapsed=
t.duration_is_elapsed, …)` → for an elapsed task this divides by **1440** (wall-clock, `_common.py:25-31`).
`:90` computes `float_days = effective_total_float(t, recomputed) / per_day` → **always** ÷ `per_day`
(working min/day, e.g. 480), regardless of `duration_is_elapsed`. The two operands of the ratio are on
**different axes** for elapsed tasks. The docstring (`:25-27`) explicitly claims both are "converted to
working days … unit-consistent even with elapsed durations" — **false**.

Live repro (8-h calendar; one elapsed in-progress task, remaining 5 edays = 7200 min, stored float 5 working
days = 2400 min):
```
float_days (code, /480):              5.0
remaining_days (code, elapsed /1440): 5.0
REPORTED ratio (code):                1.0     ("generous" band)
CONSISTENT ratio (both /1440):        0.3333  ("tight" band)
distortion factor:                    3.0000  (= 1440/480)
```
**Why new:** neither trail names "Float Ratio" or this axis mismatch; the closest priors (F-09 free-vs-total
float on SS/FF links; L5/F-13 DCMA-08 elapsed-flag) are different metrics/quantities. **Severity LOW–MEDIUM:**
it corrupts a reported, citable number (the Float Ratio value and its `<0.1` "very-tight offender" list) — a
Law-2 fidelity issue with testimony exposure, since a genuinely tight elapsed activity can be misreported as
healthy or band membership can flip. Kept below HIGH because Float Ratio is informational (no DCMA pass/fail),
elapsed in-progress Normal activities are uncommon, and the goldens contain none — **so the parity gate is
blind to it** (the same blind spot the audit calls out). Pure-working-duration schedules are unaffected
(both axes collapse to `per_day`). Fix direction: put both operands on the same axis.

**NEW-2 — `MANIP_CALENDAR_LOOSENED` false-positive on a net-zero weekday swap (CONFIRMED, weak).**
`manipulation.py:247-249` fires on any added working weekday; a Mon–Sat → Mon–Fri+Sun swap (same 6 working
days, same minutes) fires `MANIP_CALENDAR_LOOSENED` with no actual increase in available working time. Kept
weak/not-elevated: the detector is a MEDIUM "confirm authorized" review flag by design (its course-of-action
asks the operator to justify added working weekdays), so surfacing a swap for review is defensible, and it
does not corrupt a reported metric value.

---

## 5. Parity re-confirmation (Phase E)

**Raw gate output (re-run read-only this audit, scratch venv):**
```
ruff check src/ tests/            All checks passed!
ruff format --check .             260 files already formatted
mypy src/ (strict)                Success: no issues found in 85 source files
bandit -q -r src                  exit 0  (only nosec B105 warnings on i18n.py — not failures)
pytest -q --cov --cov-fail-under=70   1670 passed, 7 skipped, 2 xfailed  (engine TOTAL 99.54%)
coverage report --include='*/engine/*' --fail-under=85   TOTAL 99.54%  exit 0
pytest -m parity                  10 passed, 1668 deselected, 1 xfailed
node --check  web/static/*.js     all OK
```
Test count moved up from the recorded ~1664 baseline to **1670** — consistent with the ADR-0130 batch adding
tests (`test_data_date_finish_gap` ×2, `test_title_escaping` ×1, `test_parity_report_sync` ×1, manipulation
cases). **The +6 is accounted-for new tests, not silent change.**

**The 7 skips** are all legitimate CUI/Java intake gates: `.aft` Bible absent (`test_aft_formula_audit.py:669`),
chain `.mpp` absent (`test_chain_acumen_reference.py:102,110`), `Project2/5.mpp` absent
(`test_loader.py:93`, `test_mpp_mpxj.py:53` ×2). **The 2 xfails** are the stale `ssi_uid143` golden (ADR-0112)
with a **live passing UID-145 replacement** (`test_ssi_driving_slack_uid145_exact` is in the 10 parity passes).
**No failing test is masked by a skip/xfail.**

**Per-row verdicts — the honest ceiling is `ENGINE==GOLDEN`, not `ENGINE==FUSE`:**

| Parity row | ENGINE==GOLDEN (verifiable here) | GOLDEN==FUSE/SSI |
|------------|----------------------------------|-------------------|
| §A Schedule-Quality (P5 critical=4, etc.) | **PASS** (`test_parity_gate.py`) | **PARKED** — no committed Fuse export |
| §B DCMA-01..14 (DCMA06 44/44) | **PASS** | **PARKED** |
| §C Baseline-compliance (BSC 41/25) | **PASS** | **PARKED** |
| §E date-deterministic (net_finish_impact −148) | **PASS** | **PARKED** (date arithmetic; −148 vs PARITY-TARGETS −99 pairing differs) |
| §E float/critical (new_critical, no_longer_critical 34, float_erosion) | **PASS as self-consistency only** | **PARKED + CIRCULAR** — engine-pinned (F-01); marker disclosed in prose but **not test-enforced** |
| SSI driving slack (focus 145, 108/108) | **PASS** (recorded SSI golden) | **PARKED** (transcription) |
| EVM cost (BCWS/BCWP/DCMA/BEI) | **PASS** (`test_evm_acumen_reference.py` 6 pass; EVM1/2 ARE committed Fuse exports) | **partially ENGINE==FUSE** for matched rows; SPI(t)/finish/NFI residuals = ADR-0108 gap |
| Native `.mpp` parity | **UNVERIFIABLE-IN-ENV** (no `.mpp` data; MPXJ+Java present) | PARKED |

**Prose-claim regression check (F-03/F-07):** no live doc states "matches Acumen Fuse/SSI" without the
"against our transcribed targets" qualifier; the stale `−99 / 41-37 / 43-40 / UID-143` strings survive only
as explicitly struck-through history in `PARITY-REPORT.md`. **PASS.**

**Both non-negotiable laws hold (static + one runtime guard call):** `net_guard.forbidden_runtime_dependencies()`
→ `set()`, `importable_cloud_sdks()` → `set()`; zero external URLs in `static/*.js` (only the w3.org SVG
namespace); no forbidden HTTP client imported in runtime `src/` (outside `net_guard`); no committed CUI
(`git ls-files` → none outside `tests/fixtures/`); CSP on every response (`app.py:971-979`,
`default-src 'self'`; the `'unsafe-inline'` is the F-06-noted weakness, not a remote path); no model-id leak
in `src/`.

---

## 6. Industry-best-practice scorecard (Phase F)

**Lifecycle/process traceability (ISO/IEC/IEEE 12207-style — names for framing only).** Strong where an ADR
exists (M1→0128→`test_inactive_tasks`; C2→0129→`test_qa`; F-batch→0130→named tests). **Orphans:** (a) **C1
has no fix, no test, no ADR** despite being the #1 Critical — the worst traceability gap; (b) **F-01's marker
has no enforcing test** (fix + disclosure but no guard); (c) the **internal-audit Wave-1/2/3 in-env items
(H1, H3, H4, M2–M8) have no fix and no carry-forward in the current HANDOFF** — they fell out of the
status-of-record entirely.

**Product quality (ISO/IEC 25010).** *Functional correctness:* parity is gate-locked and green
(`ENGINE==GOLDEN`); but NEW-1 shows a reported metric (Float Ratio) that is wrong off-golden, and C1 silently
degrades a reopened file — both invisible to the gate. *Reliability:* importer crash-safety is the thin spot
— H1 (session half-mutation), H3/H4 (one bad id sinks a multi-project XER), L7 (cosmetic field sinks the
file) are all open. *Security:* F-06 closed the title XSS; CSP `'unsafe-inline'` remains a tracked
defense-in-depth gap (F-06/H2 family). *Maintainability:* the single ~8.9k-line `web/app.py` is a real
concentration risk (line numbers in findings drift between audits — e.g. M5 5753→5758 — because the file
churns). *Portability:* Py 3.11+3.13 CI is a genuine strength.

**Verification rigor (IEEE-1028-style).** The parity tests are **external oracles only up to the
transcription** — `ENGINE==GOLDEN` is real, `GOLDEN==FUSE` is unproven in-env (correctly disclosed). The
F-01 self-consistency subset is the one place the gate could read as parity but isn't, and its marker is
prose-only. Coverage gating (F-08) is fixed but remains CI-side (local `pytest` still runs no `--cov` unless
asked).

**Configuration management — the root cause.** There is **no single authoritative findings status-of-record.**
Findings live scattered across `AUDIT-2026-06-25.md` (C/H/M/L numbering), `audit/AUDIT-REPORT.md` (F numbering),
`audit/PATH-FORWARD.md`, `HANDOFF.md`, and 130+ ADRs. The two trails were **never cross-referenced**, so:
(i) overlaps were de-duplicated only by luck (L1≡F-04, L12≡F-08 got fixed; C1/H1/H3/H4/M2–M8 did not); and
(ii) when the F-set in-env batch shipped, `HANDOFF.md:3` declared *"in-env remediation batch DONE … only
artifact-gated items remain"* and its REMAINING block (`:23-35`) lists **only** artifact-gated items —
**dropping** the internal audit's still-open in-env list that the prior block (`:57-61`) had carried verbatim.
A reader trusting the top-line status would conclude C1 (a Critical, in-env-fixable) is closed. **This is the
precise mechanism that let C1 stay open across sessions, and it is still active.** Recommendation: maintain
ONE ledger (this report's §2 is a starting instance) keyed by a stable finding ID, with a single TRUE-status
column updated every session; the drift guard (`test_state_docs.py`) could be extended to assert no finding
is marked "remaining: artifact-gated only" while an in-env OPEN finding exists.

**Forensic/testimony-admissibility (Daubert-style — engineering-defensibility only; not legal advice).**
- C1: a reopened `.json` silently produces **different DCMA float/critical numbers** than the original, with
  no disclosure — the worst testimony exposure here. *Consult counsel* on disclosure obligations; as
  engineering, the limitation is **not** disclosed at point of use.
- NEW-1: the Float-Ratio docstring **asserts a unit-consistency property the code violates** — a doc that is
  actively wrong is worse than a missing caveat for a reader who quotes it.
- F-01: a reader running `pytest -m parity` could believe the §E float/critical rows are Acumen-validated;
  they are engine self-consistency. The prose marker mitigates this at point of use (good), but nothing
  prevents the marker's silent removal.
- M3/M4/M6: each can place a **fabricated or sign-flipped number** into a forensic input or narrative
  (invented project_start; leaked 2099 baseline; dropped sign) — all open.
- **Strengths:** NA discipline (never a fabricated 0), the honestly-disclosed `ENGINE==GOLDEN` vs
  `GOLDEN==FUSE` split, the refusal to relabel the SSI golden as engine-truth (xfail not deletion), and F-02's
  now-disclosed finish gap are all genuinely testimony-defensible.

---

## 7. Mandatory declarations (Phase G)

**Blind-spots — what I could NOT verify, and the exact artifact required:**
1. **`GOLDEN==FUSE` for §A/§B/§C/§E** — no committed Acumen Fuse v8.11.0 export of Project2/Project5.
   *Need:* the operator's Fuse workbook/ribbon/DCMA/§E exports. (Cost-EVM is the exception — EVM1/EVM2 ARE
   committed Fuse exports; matched rows pass.)
2. **Literal `.aft` formula match** — `NASA_Metrics_Complete_*.aft` absent; the in-repo AUDIT table is itself
   a transcription.
3. **Native `.mpp` behavior** — no `.mpp` data (Java 17 + vendored MPXJ ARE present & runnable). *Need:* the
   `.mpp` files only.
4. **L4, L6, L8, L9, L10, L11, F-09, F-10, F-13, F-14** were **not re-executed this round** (LOW/NIT; marked
   SUSPECTED in §2). Prior audit confirmed them; I did not re-derive. *Need:* a focused JS/engine re-run.
5. **No live server/browser/model execution** — CSP enforcement, autoescape inertness, and the air-gap are
   established by source + read-only Python (incl. a runtime `_LAYOUT.autoescape` check and a `net_guard`
   call), not a rendered page or live model.
6. **Exhaustiveness of the ~8.9k-line `web/app.py` escaping/mutation sweep** — sinks and the SSI route were
   traced; I cannot claim every f-string/route was inspected. The H1-class "partial mutation on failure"
   pattern was confirmed for the SSI route but not exhaustively swept across all POST routes.
7. **NEW-1 real-world frequency** — I proved the axis bug and its 3× magnitude on a crafted task; I did not
   measure how often elapsed in-progress Normal activities occur in production schedules.

**Prior-audit-miss declaration:**
- **`audit/AUDIT-REPORT.md` (F-set) MISSED** (real, still OPEN, found by the internal audit): **C1 (CRITICAL)**,
  H1, H3, H4, M2, M3, M4, M5, M6, M7, M8 — the entire importer-crash-safety / serialization-fidelity /
  session-mutation / spec-drift class. It found **zero** of these.
- **`docs/STATE/AUDIT-2026-06-25.md` (internal) MISSED** (real, found by the F-set): F-01 (parity
  circularity), F-02 (finish understatement), F-03 (stale parity report), F-05 (missing manipulation
  vectors), F-06 (autoescape/CSP), F-07 (doc-drift cluster), and the F-09/F-10/F-13/F-14 nuances. It found
  **zero** of the parity-provenance / testimony-doc-drift class.
- **BOTH MISSED** (this audit's meta-falsification): **NEW-1** — the Float-Ratio elapsed-duration axis
  mismatch.
- **Cross-trail orphan that let C1 persist:** C1 + H1/H3/H4/M2–M8 existed only in the internal trail, were
  never reconciled into the F-set/PATH-FORWARD, and were dropped from the current HANDOFF status when the
  F-set batch shipped (§6, Configuration Management). C1 is the known example; the whole internal-audit
  in-env Wave set is the rest.

**Assumptions / low-confidence points:** (a) the committed golden MSPDI faithfully represents the source
`.mpp` (project assertion, unverifiable here); (b) `case.json`/`PARITY-TARGETS.md` transcriptions equal Fuse
(the core residual risk — if a transcription is wrong, the engine "exactly matches a wrong number" and the
gate stays green); (c) NEW-2's severity (a defensible review-flag vs a real FP) is a judgment call; (d) the
SUSPECTED L/F items are carried from the prior audit, not re-derived.

---

## 8. Attack on this verification (Phase §12) — how it could fail, and the mitigation

- **(a) Rubber-stamps by reading ADRs** → mitigated: every FIXED verdict cites a re-executed test/repro
  (§3/§4); C1, F-01, NEW-1 were re-run by the auditor directly.
- **(b) Re-confirms circular parity** → mitigated: §5 splits `ENGINE==GOLDEN` (verifiable) from `GOLDEN==FUSE`
  (PARKED); the F-01 self-consistency subset is called PARTIAL, not FIXED.
- **(c) Calls C1/H1/H3/H4/M3–M5 "fixed" on a doc claim** → mitigated: each was re-derived by a live repro
  (§4), independent of HANDOFF/ADR text — which is how the false "only artifact-gated remains" status was
  caught.
- **(d) Finds nothing new and calls that success** → mitigated: NEW-1 found and live-confirmed (3× distortion).
- **(e) Trusts a wrong golden** → mitigated: §5 holds that only an external Fuse/SSI export can upgrade
  `ENGINE==GOLDEN` to `ENGINE==FUSE`; every "matches Acumen" stays qualified (§7 assumption b).
- **(f) Expert-witness lens invents legal conclusions** → mitigated: §6 flags "consult counsel" for
  disclosure-obligation questions and asserts only engineering-defensibility.
- **Residual risk:** the SUSPECTED L/F items (§7 #4) and transcription-correctness (§7 assumption b) are the
  two places this audit's confidence is genuinely bounded; both are disclosed rather than papered over.
