# ADR-0514 — Acumen Fuse's Total Float field is the stored slack rounded HALF-TO-EVEN to whole days; dcma14's two parity roundings are the reference's own rule, named as one helper (R-03 CLOSED; the probe fixture extended to the 44-day side)

**Status:** Accepted · **Date:** 2026-09-20 · **Extends:** ADR-0280 (Acumen parity mode), ADR-0467
(MF-08 — `round_half_up` at the MetricResult sites), ADR-0473 (the ribbon's Negative Float in whole
days) · **Relates to:** the sub-day negative-float probe fixture (PR #576) · **Row:** R-03 (T1, S)

## Context — what the row said, what the artifacts said

The audit row (R-03) named MF-08's residual inside `engine/metrics`: the two Acumen-parity
classifications in `dcma14.py`, `round(eff / mpd) < 0` (DCMA-07) and `round(…) > 44` (DCMA-06), use
Python's `round`, which is banker's rounding at an exact half — so a −0.5-day float reads 0 (not
negative) and a 44.5-day float reads 44 (not high). Its remedy: build a fixture at exactly −0.5 d and
44.5 d, pin what Acumen classifies for it from an operator's Fuse run, and switch to `round_half_up`
only if that oracle says so.

Reading everything first (QC-2) changed the shape of the unit three times:

1. **The fixture the row asked for already existed for the negative side.**
   `tests/fixtures/mspdi/NEGFLOAT_SubDay_Probe.xml` (PR #576, guarded by
   `tests/guards/test_negfloat_probe_fixture.py`) carries −0.25 / −0.50 / −0.75 d discriminators
   with whole-day controls, was written to be run through Fuse once, and never was: no state doc
   records an answer, and its ask had fallen off the operator list. The row's remedy duplicated it.
2. **The metric library cannot answer the question.** Both committed libraries
   (`NASA Metrics_Complete_20260423.aft`, `…_20260708.aft`) define "6. High Float" and "7. Negative
   Float" with an EMPTY `<Formula>` and a `PrimaryFilter` of `Baseline Duration > 0` AND a bare
   `Total Float > 44` / `Total Float < 0` (Planned + In Progress, Normal + Milestone). The grain of
   the **Total Float field** those filters read is the whole question, and no formula states it.
3. **The corpus does not contain the tie.** dcma14's own parity population over the 44 converted
   files (22,105 activities) holds **772** exact half-day floats — the Large Test File 178 on each of
   its three copies, Hard_File 12, `updated` 9, the logic-reestablished conversion 13 at −3.5 d — and
   **none** at −0.5 d or 44.5 d, none in (−1, −0.5) or (44.5, 45); near the thresholds only UID 5283
   at −0.29 d (Large_Test_File2), 45.0 d exactly (Project2 115 / 117, LTF 3849 / 3858 / 7233) and
   5582 at 45.27 d. A corpus census cannot decide the tie, and — the audit had not noticed — cannot
   decide rounding against truncation either.

**The oracle was in the intake all along.** Fuse's detail grids print a *Total Float* beside every
listed activity, and the operator's Large Test File exports (13 workbooks under
`00_REFERENCE_INTAKE/acumen_v8.11.0/`) hold **1,140** such grids — **3,637** distinct (project, Id)
pairs, no Id displayed with two different values anywhere. Against the engine's effective total
float (the stored slack, in exact days) on the matching goldens:

| snapshot | displayed activities | Ids not in the golden | `round` (half-even) | half away from zero | truncate | floor |
|---|---|---|---|---|---|---|
| Large Test File | 1,513 | 0 | **1,513** | 1,435 | 1,305 | 1,348 |
| Large Test File2 | 2,124 | 0 | **2,124** | 2,124 | 1,430 | 1,503 |

The first snapshot carries **196** activities whose stored slack is an exact half day (42 distinct
values from 24.5 to 781.5): **118** with an odd integer part are displayed rounded UP (513.5 → 514,
525.5 → 526, 579.5 → 580) and **78** with an even integer part rounded DOWN (24.5 → 24, 514.5 → 514,
528.5 → 528, 630.5 → 630). Half-to-even reproduces all 196; half-away-from-zero misses the 78;
truncation misses the 118 — and UID 605's 154.75 d displayed as 155 refutes truncation on a non-tie
as well. Every displayed value is a whole number (0 decimals in 3,637): the field itself is whole-day.

**The classifications read that field.** The "Large Test File vs Large Test File2 - Analyst Quick Add
Metrics" workbook carries the COMPLETE detail sets of the two DCMA metrics (the other workbooks hold
truncated views of 66 / 75 / 9 / 13 / 717 / 38 / 40 / 10 rows, or the generic "Negative Float" /
"High Float 44d" variants without the baseline filter — four extra activities, 156 / 157 / 5288 /
5746, carry no baseline duration). Against `compute_dcma14(…, acumen_parity=True)`:

| snapshot | "6. High Float" (Fuse / engine) | "7. Negative Float" (Fuse / engine) | symmetric difference |
|---|---|---|---|
| Large Test File | 814 / 814 | 35 / 35 | ∅ / ∅ |
| Large Test File2 | 660 / 660 | 112 / 112 | ∅ / ∅ |

UID 5283 (−139 min = −0.29 d) is displayed **0** and is absent from Fuse's Negative Float set; a raw
`Total Float < 0` would have listed it. ADR-0280's "UID-exact" claim is thereby re-verified on the
detail tables themselves, not on the ribbon counts.

### QC-3 — the plan attacked before the first edit

| # | assumption | check | result |
|---|---|---|---|
| 1 | no corpus activity sits at the tie in dcma14's parity population | census with dcma14's own population helpers, 44 files | 0 of 22,105; 772 half-day floats elsewhere — held (the tie is unobservable in the corpus) |
| 2 | Fuse's Total Float FIELD is whole-day and its rule at .5 is observable in the exports | every detail grid with a Total Float column vs the goldens | 3,637 / 3,637 under half-to-even; 196 half-day pairs 118 odd / 78 even — held |
| 3 | the DCMA filters read that field, not the raw slack | the Analyst workbook's full sets vs the engine's parity sets | UID-exact on both snapshots; 5283 absent — held |
| 4 | `round` is therefore the reference's rule and `round_half_up` would flip both ties away from Fuse | half-even(−0.5) = 0, half-even(44.5) = 44; `round_half_up` gives −1 / 45 | held — the row's remedy would have introduced a parity defect |
| 5 | the filter's reading EXACTLY at the tie is inferred from 2 + 3, never observed | no corpus case (1) | **UNVERIFIED at the tie**; the probe fixture is the direct instrument (optional) |
| 6 | the Id column of a Fuse grid is the MS Project UID | 0 of 3,637 Ids missing from the goldens; the values reproduce 100 % | held (the column is a STRING in the sheet XML — a reader that expects a number reads 0 rows) |
| 7 | the negative-side probe fixture exists and was never run | the fixture, its guard, every state doc | held — its ask had been dropped from the operator list |
| 8 | naming the rule as one helper is behaviour-preserving | `test_dcma14` + `test_schedule_quality` + `test_dcma_audit` (42), the Fuse parity oracles + ribbon (113), mypy, both ruff binaries | held — every figure unchanged |
| 9 | the new pins can fail | two mutants of the helper on a shadow copy (half away from zero; truncation) | held — red by name under both (below) |

## Decision

**No flip.** The engine's rule is Fuse's rule, and it is now **named**:

- `engine/metrics/_common.py::acumen_whole_day_float(minutes, minutes_per_day) -> int` — the stored
  slack in whole working days, half-to-even, with the measurement in its docstring. Its callers are
  dcma14's two parity sites (DCMA-06 / DCMA-07) and the ribbon's Negative Float in
  `schedule_quality.py` (ADR-0473, which had left the tie to R-03). R-04's sweep of `round()` sites
  toward `round_half_up` must leave these three alone: a displayed figure follows the reference
  tool's own rounding, which is **measured per figure**, never assumed to be half-up.
- `tests/parity/test_fuse_total_float_field_oracle.py` (parity-marked, std-lib xlsx reader, the 13
  workbooks named and required): every displayed Total Float equals the half-even day of the stored
  slack (the populations 1,513 / 2,124 and the 196 half-day pairs with their 118 / 78 split pinned,
  the alternatives refuted BY NAME on that population), and the two DCMA sets are UID-exact on both
  snapshots with UID 5283 absent.
- `tests/engine/metrics/test_dcma14.py::test_acumen_parity_float_ties_follow_fuses_half_even_field`
  — synthetic stored floats at −0.25 / −0.50 / −0.75 / −1.00 and 44.25 / 44.50 / 44.75 / 45.00 /
  44.00 d: parity flags {−0.75, −1.00} and {44.75, 45.00}; pure-logic flags every sub-day negative and
  everything past 44 exact days; and the delta the row asked for is written beside it —
  `round_half_up` would read −1 and 45 at the two ties.
- The probe fixture now carries the **44-day side**: UIDs 109–113 (+45.00 control, +44.75 / +44.50 /
  +44.25 discriminators, +44.00 control) authored by a 46-day PROJECT-DRIVER; the +8 d control keeps
  its float through its own FNLT constraint; every control label names its metric. The guard pins the
  DCMA-06 discrimination, the two ties present by value, and every role the operator reads. Its run is
  now a **confirmation** of assumption 5 (expected: 102 not counted by 7. Negative Float, 111 not
  counted by 6. High Float), not a blocker — moved to the operator's optional list.
- Version **1.0.279**; the wheel and the nine installers rebuilt after the last `src/` edit.

## How it was verified

- **Red first, by name, on two mutants of the helper** (a shadow copy of `src/`, the package asserted
  by the mutcheck plugin): half away from zero → the tie pin reads `{2, 3, 4} != {3, 4}` and the
  display oracle fails on the 78 even-part halves (795 at 524.5 → 524, 7438 at 514.5 → 514, …);
  truncation → the tie pin reads `{4} != {3, 4}` and the display oracle fails on the odd halves and the
  non-tie fractions (3721 at 521.77 → 522, 3734 at 511.71 → 512, …). The set oracle stays green under
  both mutants **by design** — the corpus has no tie, so that pin's teeth are the population and the
  set identity, not the tie; the display oracle and the synthetic pin carry the tie. The guard's pins
  are shape pins and stay green under an engine mutant, as they should.
- Control: the two oracle pins green on this tree (32 s); the dcma14 / schedule-quality / DCMA-audit
  modules 42 passed; the Fuse parity oracles and the ribbon modules 113 passed; the extended guard 11
  passed; `mypy --strict` (165 files); ruff 0.15.8 and 0.16.8 (check + format) over the whole tree;
  the installer lockstep 68 passed.

## Consequences

- **R-03 is CLOSED** with no engine flip: banker's rounding at the DCMA ties IS the reference's field.
- **R-04 amended:** the three `acumen_whole_day_float` callers are exempt from the sweep, and the
  sweep's rule is restated — measure each displayed figure against the reference tool's own rounding.
- **The operator's Fuse run of the probe fixture is optional** (assumption 5's direct confirmation);
  the kickoff carries it as such, with the expected reading.
- **Named, not taken:** the pure-logic mode is untouched (minute grain, `> 44 × mpd`); the 20260423
  library's generic "Negative Float" / "High Float 44d" variants without the baseline filter are not
  modelled (the DCMA ones are); the truncated grids are not oracles; `margin.py` / `wbs_breakdown.py`'s
  1-dp `round()` displays are R-04's, not classifications.
