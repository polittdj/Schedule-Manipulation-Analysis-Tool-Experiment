# ADR-0362 — Battery phase 2: the seven queued families, measured then pinned

- **Status:** Accepted
- **Date:** 2026-08-07
- **Extends:** ADR-0361 (the pass/fail battery this completes the queue of), ADR-0083/0161/0176
  (the EVM semantics the pairs now pin), ADR-0108 (the pure-logic float posture the wide
  program surfaces), ADR-0246 (state ritual)

## Context

ADR-0361 shipped the known-pass/known-fail framework with DCMA-14, float bands, completion,
manipulation and the page-render sweep, and queued seven families on it: **cei, hmi, fei/bri,
evm, schedule_quality, forecast, and the SRA-readiness gate**. The operator's "Continue"
resumed the standing queue at exactly that line.

Every figure was **measured before it was pinned** (a probe script ran each family on the
clean program and every candidate seed first). Two structural facts fell out of the
measurement, and they dictate the design:

1. **The bare 25-task program cannot honestly pass two families.** Acumen's Missing Logic
   counts the two structural open ends (first task, terminal milestone) over ALL activities —
   a 2/N floor, 8% on N=25 — and Insufficient Detail divides by the **stored-finish span**,
   which is 1 day on a fixture that carries no stored dates (everything flags). These are not
   engine defects; a real export carries stored dates and hundreds of activities. So phase 2
   adds two enriched variants instead of touching either the metric or the phase-1 program:
   `_dated` (stored start/finish = actuals-else-baselines, plus WBS — also required by FEI/CEI
   forecast reads and the readiness WBS gate) and `_wide` (16 fully-linked parallel tasks,
   N=41, putting the structural floor at 4.9%).
2. **Three families are informational by design** (cei, hmi, fei/bri: status always NA), so
   their pairs pin **values and offender uids**, not CheckStatus flips.

## Decision

`tests/test_projects/test_pass_fail_battery.py` gains a phase-2 section (20 tests, 41 total):

- **CEI** — a rolled-back prior snapshot (PREV = Jan 19) whose stored forecasts place tasks
  2/3's finishes and task 4's start inside the coming period. Clean: 2/2 = 1.0, starts 1/1,
  adjusted 2/2, milestones/critical honestly NA. Seeded (task 3 un-finished): 1/2 = 0.5
  citing exactly UID 3, the start cut unmoved.
- **HMI** — clean 1/1; seeded 0/1 citing UID 2; a non-advancing period reads NA, never a
  fabricated ratio.
- **FEI/BRI** — clean FEI starts 20/22 = 0.91, finish 21/22 = 0.95 (under 1.0: the to-go
  window is no heavier than the baseline placed it); slipping tasks 2/3 wholesale past the
  data date pushes 22/22 = 1.00 and 23/22 = 1.05 — the bow wave crosses the line. BRI 2/2 =
  1.0 → 1/2 = 0.5 citing UID 2.
- **EVM** — the clean program passes all **thirteen** thresholds (SPI 1.75 · CPI 1.0 · TCPI
  1.0 · SPI(t) 1.5 · SPI(t)-Acumen 1.08 · the six on-time/late ratios · CEI finish/start),
  and four seeds must flip **exactly** their declared sets — set equality, stronger than
  phase 1's no-undeclared rule: an expected flip that fails to happen also fails the battery.
- **schedule_quality** — on `_wide`: Missing Logic PASS 2/41 citing exactly (1, 99); the
  orphan seed FAILs it citing (1, 9, 10, 11, 99); three 40-wd durations FAIL Insufficient
  Detail citing (8, 9, 12) — the stored span stays fixed at 335 days because seeding
  `duration_minutes` does not move stored dates, so the ratio is honest; three lagged links
  FAIL Number of Lags citing (6, 8, 10); hard-constraint / negative-float / merge-hotspot
  informational counts pinned by offenders.
- **forecast** — all four methods answer on the dated program (CPM 2026-12-04 ·
  as-scheduled 2026-12-06 · rate 2026-08-26 · earned-schedule 2026-08-14; execution ran
  twice plan speed, so the performance methods land earlier than the logic methods).
  Un-finishing tasks 2/3 pushes rate to 2027-12-06 and IEAC(t) to 2027-11-05 while the logic
  and stored answers stand still — the divergence IS the finding. Missing inputs answer
  `None` with the honest basis strings, on both the no-data-date and no-stored-dates cuts.
- **SRA-readiness** — the dated program passes all seven scored gates (three-point stays
  INFO by design); seven seeds flip exactly their gate, with ONE declared collateral: the
  hard-constraint seed also fails the critical-path gate — the same physical defect phase 1
  declared as DCMA05 → DCMA12 collateral, resurfacing through the scorecard's mapping. The
  offender pins hold (stripped WBS cites (7, 8); LOE cites (6,)), and the phase-1 rule that
  one self-pinning MFO rides inside the hard-constraint tolerance ("1 of 25 (4.0%)", still
  PASS) while defeating the CP test is pinned verbatim.

**Two measured semantic edges are pinned as permanent discriminators** (they can never again
silently blur):

| edge | measured behaviour |
| --- | --- |
| work that **never starts** | SPI 0.5 FAIL and Earned-Schedule SPI(t) 0.5 FAIL, but **SPI(t)-Acumen stays PASS at 1.44** — the per-activity average only sees *started* work; it is structurally blind to work that never begins (ADR-0176 population) |
| a **late-vs-baseline** start | Started Late FAILs at 50%, but **Baseline Start Compliance stays 100% PASS** — its Half-Step-Delay numerator compares the actual start to the baseline *finish* (ADR-0083's documented asymmetry) |

## Verification

Eight targeted engine mutations, each run against only its family's pair, each red, each
module restored byte-identical from a scratchpad copy (never `git checkout`): CEI numerator
counts everything → red; HMI hits = due → red; BRI done = due → red; the 95% on-time bar
dropped to 5% → 3 red; Missing Logic threshold 5→50% → red; `_DAYS_PER_MONTH` → 3.0 → red;
the standard-calendar upper bound 12h→48h → red; `_zero_bar` always-PASS → red. Full battery
41/41 green after restore.

## Consequences

Every metric family the tool surfaces now has a measured known-pass AND known-fail
demonstration. The phase-1 corpora, seeds and helpers are reused where the physics is the
same (`_seed_missing_logic`, `_seed_hard_constraints`, `_seed_cp_broken`,
`_seed_missing_resources`, `_seed_negative_float`).

## Deliberately NOT done

- **No engine changes.** Nothing the measurement surfaced was a defect; this lands tests-only
  (no version bump, no wheel/installer rebuild — the shipped tree is byte-identical).
- The wide program's `critical` reading 38/38 (100%) is pure-logic CPM float on a progressed
  serial chain — the standing ADR-0108 posture, informational, pinned by count only.
- The bare program's Insufficient-Detail span trap (span 1 day without stored finishes) is
  documented in `_dated`'s docstring, not "fixed": importers always store dates, and a guard
  that fires on a synthetic-only condition would be noise.
- `cei_critical` stays NA on the battery corpus (no stored critical flags) — eliciting it
  would need a stored-slack fixture, which belongs to a future Acumen-parity fixture, not
  this battery.
