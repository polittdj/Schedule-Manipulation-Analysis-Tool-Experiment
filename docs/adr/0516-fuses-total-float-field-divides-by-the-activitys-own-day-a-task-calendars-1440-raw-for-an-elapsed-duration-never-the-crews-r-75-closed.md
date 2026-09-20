# ADR-0516 — Acumen Fuse's *Total Float* field divides the stored slack by the ACTIVITY's own day — a task calendar's, 1440 for an elapsed duration (and then RAW), else the project's — never the crew's calendar and never the engine's execution calendar; the three parity callers pass it (R-75 CLOSED; the duration fields' divisor registered as R-76)

**Status:** Accepted · **Date:** 2026-09-20 · **Extends:** ADR-0514 (R-03 — the field is half-to-even),
ADR-0515 (R-04 — M6 named the divisor; its Forensic oracle's reader corrected here), ADR-0474 /
ADR-0503 (the execution calendar the engine schedules on — NOT this divisor) · **Row:** R-75 (T1, S) ·
**Registers:** R-76 (T1, S)

## Context — what the row said

ADR-0515's M6 found three Hard_File rows its half-even rule did not reproduce: UIDs 14 / 146 / 94
display −3 / −1 / 2 for a stored −4,320 / −1,440 / 2,190 minutes — the slack over 1,440 / 1,440 / 930
minutes, not the project's 480 — and `acumen_whole_day_float`'s three callers (dcma14's two parity
classifications, the ribbon's Negative Float) passed the project's day. On the 24-hour Hard_File the
engine's DCMA-06 read **2** (UIDs 302 / 385) where Fuse's ribbon reads **0**. The mechanism was left
open: UID 146 has NO task calendar and was still shown over 1,440 — the task calendar, the elapsed axis,
or the crew's calendar? Decide it FIRST, on the corpus.

## What the reference tool's own grids say (QC-2 / QC-3 — read everything, attack the plan first)

Every Hard_File workbook the operator delivered prints a Total Float beside every activity of its
detail grids. Four workbooks carry grids: the Fuse Analysis Report (Hard_File / Hard_File_updated, 19
grids), the update → update2 Analysis Report (29), the update2 → update3 Analysis Report (192) and the
7/15 Analyst report `HA296F~1.XLS` (374 grids; `HARD_F~3.XLS` duplicates it, `HARD_F~4.XLS` carries no
grid). Against the goldens' stored slack:

| measurement | population | result |
| --- | --- | --- |
| **M1** each workbook matched to the SAVE it was made from | the two `updated3` saves | by measurement, never by name: the 7/15 workbook reproduces the **rev-5** golden 141 / 141 (129 / 141 on rev 2 — UIDs 281, 289, 267, 402, 403, 404 differ between the saves; 12 tasks differ in stored slack); the 7/9 workbook reproduces **rev 2** 110 / 110 (104 / 110 on rev 5). |
| **M2** the divisor | **771** displayed floats over five snapshots (45 / 61 / 61 / 102 / 110 / 110 / 141 / 141) | **the activity's OWN day reproduces every one**: 1440 for an elapsed duration, else the task's own calendar's working minutes per day when it names one, else the project's. The project day misses exactly ten (UID 94 on `updated`; 14 and 146 on `updated2` and `updated3`; 14, 146, 302, 385, 389 on the 24-hour file). |
| **M3** the crew's calendar | the same rows | refuted BY NAME: UID 14's crew works 16-hour days (−4,320 / 960 = −4.5 → −4, shown −3); a task with no calendar of its own stays on the project day even when its crew works 24 hours (24-hour file UID 13: −10 for −4,800, the crew's 1440 would read −3 — 7, 141, 36, 9, 144 likewise); UID 389's crew is on the project pattern while its task calendar is 24 Hours (−14, not −41). |
| **M4** the engine's execution calendar (ADR-0474 / ADR-0503) | the same rows | refuted BY NAME: the crew under a 24-hour task calendar gives UID 14 −4; the task ∩ crew intersection (870 minutes) gives UID 94 3 for the displayed 2; every no-calendar activity with an off-pattern crew misses. Fuse's divisor is the task's OWN calendar, whatever the work is scheduled on. |
| **M5** the elapsed activity | UID 146 | **RAW, never rounded**: the 24-hour file displays −13.333333333333334 for a stored −19,200 minutes where UID 14, on a "24 Hours" task calendar with the SAME −19,200, reads −13 — the one non-integer cell in 771. The first reader of these grids filtered the value to integers, dropped that cell and read "140 of 140" for the elapsed case. Its behaviour at a tie (−0.5 < x < 0, 44 < x < 44.5) is **UNVERIFIED**: no elapsed activity in the corpus sits there (146's floats are 0 / 0 / −1 / −37 / −13.33; 24Hour Calendar.mpp's 0; Jacked Up Schedule 1's 2.625). The field is implemented as it is displayed. No elapsed activity carries a task calendar (0 of 16), so "elapsed first" is stated, not measured. |
| **M6** an own-day tie | UID 302 | 49,680 / 1440 = 34.5, shown **34** — half-to-even on the task's axis too (half away from zero would print 35). |
| **M7** the class in the 44-file corpus | 22,105 non-summary activities | 1,578 carry an off-pattern task calendar or an elapsed duration; **34** change their whole-day float (the Hard_File family, `24Hour Calendar.mpp` UID 17: 148 → 49, `Jacked Up Schedule 1.mpp` UIDs 19 / 20: 77 → 26, 8 → 3). The Large Test File pair's 138 off-pattern task calendars are 480-minute days ("ZIN Project Calendar", "Overtime Schedule Calendar") — 0 movers, its DCMA sets unmoved by construction. DCMA-06 membership moves only on the 24-hour Hard_File (302 / 385, three copies); DCMA-07 nowhere; the ribbon's Negative Float on no file. |
| **M8** the DCMA sets | the 7/15 workbook | ribbon "6. High Float" **0 / 0**, "7. Negative Float" **40 / 11**; the Negative Float grids list 40 and 11 UIDs (the 24-hour file's 7, 9, 13, 14, 36, 141, 144, 145, 146, 389, 409) — UID-exact against `compute_dcma14(acumen_parity=True)` on both saves after the change; before it the 24-hour file's DCMA-06 was {302, 385} (104 / 93 project-days; 34 / 31 days of their own calendar). |
| **M9** the duration fields (registered, R-76) | the same grids' Original / Remaining Duration columns | Fuse's Original Duration is ALSO on the task's own day (UID 14: 1,440 minutes on "24 Hours" shown **1**, not 3; the 24-hour file's 302 / 385 / 389: 2 / 3 / 1, not 5 / 9 / 3) — but an ELAPSED activity's Original Duration is on the PROJECT day (146: 2,880 minutes shown **6**) while its Remaining Duration is on 1440 (shown **2**); two remaining rows (UIDs 315 / 129: 247 / 242 minutes shown 0, not 1) are a different mechanism. ADR-0515's M1 saw only CHANGED rows, where no multi-calendar duration appears. Two corpus activities cross the 44-day duration threshold between the two divisors (`24Hour Calendar.mpp` 17: 100 → 33; `Jacked Up Schedule 1.mpp` 20's remaining 96 → 32), neither with a Fuse oracle. |
| **M10** ADR-0515's Forensic reader | the three Forensic Analysis Reports | Fuse's xlsx writer omits the cell reference on consecutive cells and writes it only where it SKIPPED a column — an empty ratio at a zero 'before', and every date-sheet row. The document-order reader slid such rows: the after value landed in the ratio slot and the row was dropped as non-numeric — 70 Hard_File float rows (pair 1: 39 → 109), 6 LTF float rows, 2 pair-2 rows and 4 / 7 LTF duration rows were never compared, and the (1, 14) divisor assertion never ran. Column-addressed now: **810 / 855 / 1,514** rows, every one half-even under the own-day rule; the date sheets read the same 1,225 / 1,516. |

## Decision

1. **The field's day is the activity's own** — `engine/metrics/_common.py::activity_day_minutes(schedule,
   task, by_uid=None)`: 1440 for an elapsed duration, the task's own calendar's working minutes per day
   when the schedule carries it, else the project calendar's. Never the crew's calendar, never
   `execution_calendar_of` (M3 / M4).
2. **The field itself** — `acumen_total_float_field(task, minutes, day)`: an elapsed activity's slack
   raw in elapsed days (M5); every other activity's slack rounded half-to-even to whole days of its own
   day (`acumen_whole_day_float`, ADR-0514). The three parity callers read it: dcma14's "6. High Float"
   (`> 44`) and "7. Negative Float" (`< 0`) under `acumen_parity`, and the ribbon's Negative Float in
   `schedule_quality`. No new `round()` — the site ledger's 374 rows stand.
3. **The pure-logic mode and the tool's own displays keep the project day.** The default DCMA-06 / 07
   compare minutes on the schedule's calendar, and the whole-day float sentences of the brief (2 sites),
   the driving view (2, at 1 dp) and the recommendations (1, at 1 dp) divide by the project's day —
   priced (5 sites) and HELD: they are the tool's reading on the schedule's declared day, the convention
   MS Project's own slack display follows (its hours-per-day setting) — **UNVERIFIED** here, no MS
   Project-rendered export in the intake; what settles it is a view export showing UID 14's Total Slack.
4. **Pinned** — `tests/parity/test_fuse_hardfile_float_divisor_oracle.py` (the 771 rows per workbook
   and save, the alternatives refuted by name, the raw cell, the 302 tie, the ribbon counts and the
   Negative Float grids UID-exact, the ribbon's own Negative Float unmoved at 49 / 15, the R-76 evidence);
   `test_dcma14.py` and `test_schedule_quality.py` (synthetic pins on both parity paths and the ribbon:
   a 24-hour task calendar at 103.5 / 133.5 project-days is 34 / 44 own-days and not high, an elapsed
   −0.42 d IS negative, an unknown calendar uid and no calendar fall to the project day);
   `test_fuse_forensic_rounding_oracle.py` re-pointed to the engine's rule and its reader corrected
   (M10), the populations re-derived: 806 / 848 / 1,436 → 810 / 855 / 1,514.
5. **R-76 registered (T1, S):** Fuse's Original / Remaining Duration fields divide by the task's own day
   (M9), the elapsed Original Duration by the project's and the elapsed Remaining Duration by 1440; the
   engine's DCMA-08 parity site and `duration_days_axis` price against it. Decide DCMA-08's population
   rule (baseline vs remaining, the `.aft`) on the 7/15 grids' 282 duration rows first.

## Verification (QC-1 / QC-3)

Ten assumptions written down and attacked before the first edit (the plan is in the session record):
the save matching (A1 — held, M1); the population (A2 — held once the reader kept the value it judged:
771, not 770 or 140); elapsed-over-task-calendar precedence (A3 — UNVERIFIED, 0 of 16, said so); the
calendar's day (A4 — 1440 decided by four rows; "Standard+Sat." 930 vs 960 undecidable on UID 94, the
model's 930 kept); the LTF pair unmoved (A5 — held, 480-minute calendars); the three callers the only
parity sites (A6 — held by grep; the five display sites priced); the ribbon unmoved (A7 — held, 0 of 44
files); DCMA membership moves only on the 24-hour file (A8 — held); the elapsed field raw (A9 — the
premise "rounded" FELL to the −13.333… cell); the 302 tie (A10 — held). **Red first, by value, on the
pristine engine:** the 24-hour file's DCMA-06 (302, 385) against the ribbon's 0; the synthetic parity
sets [1, 2, 3, 6] / [4, 5, 7, 8] against {3, 6} / {5, 7, 8}; the ribbon (1, 2, 3) against (1, 3); the two
oracle modules red at import. **Green after** (13 passed). **Mutants** (shadow copies, the import
asserted): the project day always → 5 pins red; the elapsed axis ignored → 3 (146 by name); the elapsed
activity rounded → 3 (the −13.333… cell, the −0.42 d pins); half away from zero on the own day → 2 (302's
34 → 35; 44.5 → 45); the execution calendar → 2 (94 / 14 / 13 by name). The 23 modules consuming the
DCMA or ribbon sets + the ledger guard: 327 passed. Statics green on ruff 0.15.8 and 0.16.8 over the
whole tree, `mypy --strict` 165 files, bandit, `node --check`.

Fell: the row's open question (the crew's calendar — refuted); the first reader's "140 of 140" (a filter
on the judged value); ADR-0515's Forensic reader (M10); and this unit's own first premise that the
ribbon's Negative Float equals the DCMA tile (49 / 15 against 40 / 11 — the ribbon metric has no
baseline filter; pinned as unmoved, not as equal).

## Deliberately NOT done

The five project-day display sites and the pure-logic DCMA thresholds (decision 3) · rounding the
elapsed field (M5 — the reference does not) · the duration fields (R-76 — mechanism and population
first) · the Large Test File field oracle's document-order reader (its grids are full-width and every
one of its 3,637 rows matches by value; a slid row would have failed by value) · a separate pin on
`HARD_F~3.XLS` (a duplicate of the pinned workbook) · the Free Float sheet (R-74's row).

## Consequences

R-75 CLOSED; R-76 registered. One shipped figure moves: the 24-hour Hard_File's DCMA-06 under parity,
2 → **0** (Fuse 0); every other figure in the 44-file corpus is unchanged (M7). Version **1.0.280**;
highest ADR 0516.
