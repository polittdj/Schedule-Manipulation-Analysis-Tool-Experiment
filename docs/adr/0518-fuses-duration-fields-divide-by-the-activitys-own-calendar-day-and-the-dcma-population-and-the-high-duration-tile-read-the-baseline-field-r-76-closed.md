# ADR-0518 — Acumen Fuse's *Original* / *Remaining* / *Baseline Duration* fields divide by the ACTIVITY's own CALENDAR day (the Original and Baseline fields ignoring the elapsed flag, the Remaining field taking 1440 for it), and the DCMA-14 parity population and the "8. High Duration" tile read the Baseline Duration FIELD — a whole-day field of 0 leaves every population (R-76 CLOSED; Float Ratio™'s whole-day formula registered as R-78, the DCMA-09 tile's denominator as R-79)

**Status:** Accepted · **Date:** 2026-09-20 · **Extends:** ADR-0516 (R-75 — the Total Float field's
divisor; M9 registered this row), ADR-0514 (R-03 — the classifications read the rounded field),
ADR-0280 / ADR-0283 (the parity population "Baseline Duration > 0"), ADR-0473 (DCMA-08's basis is
the Baseline Duration) · **Row:** R-76 (T1, S) · **Registers:** R-78 (T1, S), R-79 (T1, S)

## Context — what the row said

ADR-0516's M9 read the duration columns beside the floats it was measuring: Fuse's Original
Duration for UID 14 (1,440 minutes on a "24 Hours" task calendar) displays **1**, not 3; the
24-hour file's 302 / 385 / 389 display 2 / 3 / 1, not 5 / 9 / 3; the elapsed UID 146's 2,880 minutes
display **6** as an Original Duration (the PROJECT day) but **2** as a Remaining Duration (1440); and
two Remaining rows (315 / 129: 247 / 242 minutes shown 0) were "a different mechanism". The engine's
DCMA-08 parity site compared the baseline duration to 44 project-days (44 × 1440 for an elapsed one)
over every incomplete activity, and `duration_days_axis` divided by the project day. The row asked
for DCMA-08's population rule FIRST (baseline or remaining; the `.aft` filter and the Detailed
Metric Reports' marks), then the 7/15 grids' 282 duration cells, then the two sites.

## What the reference tool's own workbooks say (QC-2 / QC-3 — attacked before the first edit)

| measurement | population | result |
| --- | --- | --- |
| **M1** the tile's basis | the Large Test File pair's Analyst / MS Excel Quick Add ribbons and Metric History | "8. High Duration" reads **87 / 86** = the History's "High Baseline Duration (44d)" (87 / 86), not "High Planned Duration (44d)" (124 / 120); the `.aft`'s DCMA metric carries `Baseline Duration > 44` as its primary filter and `Baseline Duration > 0` as its population, planned + in-progress, Normal + Milestone. The X-marks are UID-exact against the engine under every candidate rule (no oracle activity sits in the tie zone 44 < d < 44.5; UID 4235 at exactly 44.0 is not marked, 1562 at 45.0 is). |
| **M2** the tile's denominator | the same ribbons' ratio block | **0.09 / 0.10** = 87 / **927** and 86 / **904** — the baselined-incomplete population; the engine's every-incomplete 1,024 / 998 would print 0.08 / 0.09. Project2 1 / 106 → 0.01 either way. |
| **M3** the Original and Baseline fields | every cell the four Hard_File analysis workbooks display (771 Original / 771 Remaining / 297 Baseline over five snapshots, saves matched by the Total Float field as ADR-0516 did) and the AlltheProjects Analysis Report (every label whose save is a committed fixture — 9,935 / 9,935 / 1,085 more; 10,706 floats reproduce 100 %) | **the minutes over the task's own CALENDAR day, half-even, the elapsed flag IGNORED** reproduces every Baseline cell and every Original cell but one: Large Test File2's UID 5267 stores `PT107H59M36S` (13.4992 days, displayed 13) where the model's minute grid holds 6,480 (13.5 → 14; R-65's class). The project day misses 14 / 302 / 385 / 389 and Jacked Up Schedule 1's 19; 1440 for an elapsed Original misses 146 and Jacked Up 1's UID 20 (46,080 → 96, not 32); the floor misses 1,409 distinct rows; half away from zero misses the 240-minute baselines (UIDs 99 / 642 display 0 — half-even at the tie). |
| **M4** the Remaining field | the same cells | **1440 for an elapsed activity, else the task's own calendar day, half-even** — 146's 2,880 → 2 (its Original 6), Jacked Up 1's UID 20 → 32 (its Original 96) — misses only 5267 (the minute grid) and the two named summaries: 315 / 129 on the 24-hour snapshot, 99 % complete with `ActualDuration == Duration` and no RemainingDuration in the MSPDI (MPXJ's dropped zero, ADR-0517's class); Fuse shows the file's 0, the percent fallback derives 247 / 242 minutes → 1. |
| **M5** the population rule | the 24-hour Hard_File's ribbon | Fuse's "Baseline Duration > 0" reads the FIELD on the own day: UIDs 302 / 385 carry a 480-minute baseline on the 1,440-minute "24 Hours" calendar (0.33 → **0**) and leave the population — "7. Negative Float" **0.92 = 11 / 12** (the engine's 14 prints 0.79), "9. Invalid Forecast Dates" **0.08 = 1 / 12** (1 / 14 → 0.07), and the tile's own detail grid lists UID **267 alone** where the unfiltered Quick-Add "Invalid Forecast Dates" grid lists 267 / 302 / 385 — the engine's parity DCMA-09 read those three. The exact tie is witnessed at the FIELD: Large Test File's UID 642 (a 240-minute baseline on 480, incomplete) displays a Baseline Duration of **0** on both snapshots, so the field reading leaves it out (927 / 904 — the ribbon's 2-dp ratios cannot separate 927 from 928, so the population's reading of the tie follows the displayed field, as the float classifications do). The (0.5, 1) own-day band has no witness (no corpus activity sits there): the field reading is chosen over "≥ 1 own day" for consistency with ADR-0280's "whole days"; UNVERIFIED between them. |
| **M6** the corpus | 44 files, 13,461 incomplete activities | population movers: 302 / 385 on the three 24-hour Hard_File copies only. DCMA-08 parity movers: `24Hour Calendar.mpp` UID 17 only (28,800-minute baseline: 60 project-days, 20 days of its 24-hour calendar — no Fuse oracle). Large Test File 87 / 86, Project2 1, Project5 0, every Hard_File snapshot 0: unchanged. |
| **M7** `duration_days_axis` (Float Ratio™'s remaining term) | the AlltheProjects ribbon's Float Ratio™ for 17 projects, recomputed from Fuse's OWN displayed fields | Fuse's `AVERAGE(TotalFloat/RemainingDuration)` averages its WHOLE-DAY fields over Normal, planned-or-in-progress activities and reads **N/A whenever a Remaining Duration field is 0**: −10.9446 → −10.94 (Hard_File_updated3, 52 rows), 14.0076 → 14.01 (Project2), 0.7678 → 0.77 (Jacked Up 1), 0.2667 → 0.27 (Jacked Up 2), 0.3427 → 0.34 (TP4 v3); N/A ⇔ a zero field on 9 of 9 N/A projects and 0 of 8 numeric ones (the 24-hour file: UID 389's 480 minutes on 1440; Hard_File: UID 99's 240). The engine averages MINUTES and skips a zero remaining: **−11.85** for −10.94 on the rev-5 updated3, 119.61 / 3.98 / 3.21 where Fuse reads N/A (Large Test File / Hard_File / EVM1); exact on the six single-calendar unprogressed projects. A divisor change alone does not reach the reference — **R-78**. |
| **M8** DCMA-09's denominator | Large Test File2's ribbon | "9. Invalid Forecast Dates" **322 / 0.36** reproduces only with the baselined-incomplete 904 (998 → 0.32, the engine's every-baselined 1,568 → 0.21); the tile counts FIELDS (322) where the engine counts activities (173 — the documented divergence). **R-79**. |

## Decision

1. **Two day selectors.** `engine/metrics/_common.py::activity_calendar_day_minutes(schedule, task,
   by_uid=None)` — the task's own calendar's day when it names one the schedule carries, else the
   project's, NO elapsed axis: the divisor of the Original and Baseline Duration fields.
   `activity_day_minutes` (R-75) delegates to it after its elapsed branch and stays the divisor of the
   Total Float and Remaining Duration fields.
2. **The duration field.** `acumen_duration_field(minutes, day_minutes)` — whole days, half-even; the
   same arithmetic as `acumen_whole_day_float` and implemented as a call to it, so the tree gains no
   `round()` site (the ledger and the report's census are unchanged).
3. **The parity population reads the Baseline field.** dcma14's `_baselined` is
   `acumen_duration_field(baseline, activity_calendar_day_minutes(...)) > 0` — a baseline under half
   a day of its own calendar reads 0 and leaves every parity population (DCMA-01 / 04 / 05 / 06 / 07 /
   08 / 09 / 10 / 11). On the 24-hour Hard_File: Negative Float 11 / 12, Invalid Dates 1 (UID 267),
   High Float population 12.
4. **DCMA-08 under parity** is the Baseline Duration field > 44 over the baselined-incomplete
   population; the pure-logic mode keeps raw minutes against 44 project-days (44 × 1440 for an
   elapsed baseline) over every incomplete activity, byte-identical. Reading the whole-day field at
   44 < d < 44.5 follows ADR-0514's float classifications — **UNVERIFIED** at the tie (no oracle
   activity sits there; a mutant that compares raw minutes is red only on the synthetic pin).
5. **`duration_days_axis` is HELD** (priced: its only consumer is Float Ratio™, whose whole formula
   is R-78's — the field-based mean and the N/A on a zero divisor). The five project-day display
   sites of ADR-0516's decision 3 stay held.
6. **Pinned** — `tests/parity/test_fuse_duration_fields_oracle.py`: every duration cell of the
   Hard_File and AlltheProjects workbooks under the shipped helpers (populations pinned; the misses
   exactly the three named residuals; the alternatives refuted by name; the minute-grid `Duration`
   read back from the MSPDI; the dropped-zero summaries' fallback 247 / 242), the 24-hour ribbon's
   0.92 = 11 / 12 and 0.08 = 1 / 12 with the tile's detail grid (267) against the unfiltered one
   (267 / 302 / 385), the tile 87 / 927 → 0.09 and 86 / 904 → 0.10 and the pristine denominators'
   0.08 / 0.09, Project2 1 / 106, the Hard_File snapshots 0, and the R-78 / R-79 registrations
   (Fuse's Float Ratio™ recomputed from its own fields to 4 dp; the engine's −11.85 / 119.61 / 14.01
   today; File2's 322 / 904 → 0.36 against the engine's 1,568). `test_dcma14.py`: the synthetic pins
   on both modes (34.5 own-days not high, an elapsed 90 project-days high, the 44.4-day field 44, a
   480-minute baseline on 1440 out of every population, the denominator 6 not 8).

## Verification (QC-1 / QC-3)

Eleven assumptions written down and attacked before the first edit (the plan is in the session
record): the tile's basis and denominator (A1 — held, M1 / M2); the Original / Baseline rule (A2 —
held with one named minute-grid residual); the Remaining rule (A3 — held with the dropped-zero pair
named); the population rule (A4 — held by two ratios and a UID-exact grid); the tie zone and the
elapsed axis of the classification (A5 — UNVERIFIED, stated); the corpus consequences (A6 — held);
`duration_days_axis` (A7 — FELL as a divisor question: the whole Float Ratio™ formula differs,
registered as R-78); the default mode (A8 — held, `test_acumen_parity_default_is_identical_to_prior`
and the count-keyed golden pins); no new `round(` site (A9 — held, 0 in dcma14.py before and after);
the DCMA-09 consequence (A10 — held: 3 → 1 on the 24-hour file, the denominator registered as
R-79); the doc guards (A11 — run before the push). **Red first on the pristine package, by name:**
the field oracle and the synthetic pin (`ImportError: activity_calendar_day_minutes`), the population
pin (11, 14) ≠ (11, 12), the tile pin (87, 1024) ≠ (87, 927); the R-78 registration green on both
trees as designed. **Green after.** **Mutants** (fresh copies of `src/`, the import asserted):
recorded in the session log by name — the pristine population rule, the every-incomplete denominator,
the project day at the tile, the elapsed axis in the calendar day, the floor, half away from zero,
raw minutes at the tile (the synthetic pin alone — the UNVERIFIED tie, exactly), a raw `> 0`
population; the uncut control green. The DCMA and parity consumers (197), `tests/engine` +
`tests/test_projects` (1,353), the full suite and `-m parity` as recorded in the session log.
Statics green on ruff 0.15.8 and 0.16.8 over the whole tree, `ruff format`, `mypy --strict`, bandit,
`node --check`.

## Deliberately NOT done

`duration_days_axis` and Float Ratio™ (R-78 — the formula, the N/A, the population's Normal filter;
priced S, the oracle named) · DCMA-09's parity denominator and its field-vs-activity count (R-79) ·
reading an absent remaining as zero for the Remaining Duration field (the two summaries are disclosed
by name; ADR-0517's class keeps the CPM's reading) · the minute grid (R-65) · the "≥ 1 own day"
alternative for the population (no witness in (0.5, 1)) · the pure-logic thresholds and the five
project-day display sites (ADR-0516 decision 3) · the AlltheProjects labels whose saves the repo does
not hold (EVM2 8 / 11, Hard_File_updated2 42 / 110, the five TP4 versions 7–13 / 15) and the intake-only
`.mpp` labels — excluded from the committed oracle by name; the session's wider run over them read
15,314 / 15,314 / 2,180 cells with the same residuals.

## Consequences

R-76 CLOSED; R-78 and R-79 registered. Shipped figures that move, under parity only: the 24-hour
Hard_File's DCMA populations 14 → **12** (Negative Float 78.6 % → 91.7 %, Fuse's 0.92), its DCMA-09
count 3 → **1** (Fuse's 1), and every file's DCMA-08 denominator from every incomplete activity to the
baselined-incomplete population (Large Test File 8.5 % → 9.4 %, Fuse's 0.09; File2 8.6 % → 9.5 %,
Fuse's 0.10); `24Hour Calendar.mpp` UID 17 leaves High Duration (60 project-days, 20 own-days — no
oracle). No pure-logic figure moves. Version **1.0.282**; highest ADR 0518.
