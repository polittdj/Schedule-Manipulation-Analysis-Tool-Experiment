# ADR-0508 — A leveling gap is measured in working seconds and the leg honours the nearest minute of the CUMULATIVE gap; the recorded span reads the nearest minute of its seconds (R-65 CLOSED)

- **Status:** Accepted — 2026-09-18 (the plan-forward's R-65, the report's §3 row after R-62 / ADR-0507).
- **Version:** **1.0.274** (`src/` changed: `model/calendar.py` (`Calendar.intraday_worked_seconds`; the minutes form now delegates to it), `engine/cpm.py` (`_recorded_seconds`, `_nearest_minute`, `_covered_seconds` replacing `_covered_span`, `_split_gaps` rounding the cumulative gap, `_recorded_span` the nearest minute of its seconds, `working_minutes_between`'s docstring)). Wheel and the nine installers rebuilt in lockstep. Schema **2.16.0 unchanged** — a method, not a field; every instant the arithmetic reads was already in the model with its seconds (`WorkPiece.start` / `finish`, `Assignment.start` / `finish`, `isoformat` round-tripped by the Save).
- **Extends:** **ADR-0491** (the split gaps — their ruler is this ADR's), **ADR-0501** (which measured the residual and registered R-65), ADR-0487 (the recorded-window leg — its ruler rounds now), ADR-0502 (the sub-minute class it named: "R-65's class, not a rule error"), ADR-0474 (the type axis the census filters on), ADR-0476 (why a completed booking's window adjudicates nothing).
- **Shipped:** `tests/parity/test_r65_gap_granularity_oracle.py` (10, NEW — the population per golden, the witnesses by name, the class beside the row, the residual left, the leveled 5306), `tests/engine/test_leveling_split.py` (+4), `tests/engine/test_recorded_booking_span.py` (+1), `tests/model/test_calendar.py` (+1), `tests/parity/test_hard_file_stored_dates_oracle.py` (2 pins re-derived upward, dated), the report's R-65 row closed, `docs/PARITY-REPORT.md`.

## Context — what the row said, and what the kickoff demanded before pricing it

R-65 read: *the engine's honoured leveling gaps (ADR-0491) land 1–28 minutes short of the window
MS Project records for the same split booking — systematic and one-directional across ~100
bookings in the 29-file `.mpp` corpus (UID 5342 occupancy 2,757 vs window 2,758; UID 5316 9,329 vs
9,333; UID 5273 4,687 vs 4,688)*, with three suspects — rounding in `_recorded_span`, the
share→`after` conversion, MPXJ's timephased block boundaries — and the kickoff's four checks:
re-count the population on fresh conversions, name the exact count per file and the duplicates;
read the three suspects before believing any; dump the block boundaries (they carry SECONDS)
beside the engine's minute axis for the three witnesses; test whether the residual is the sum of
per-block sub-minute truncations before touching a rounding. Every check ran before a line changed.

### What was measured first (QC-1 / QC-2)

**The population, on fresh conversions of all 29 intake `.mpp` files** (43 s with the vendored
converter, every artefact asserted to exist): **239 split WORK bookings** (two or more work
pieces, on an active non-summary task with a duration, resource calendars honoured); **173 differ**
from the window `_recorded_span` reads for the booking's own `Start` / `Finish`; and the same
arithmetic re-done at SECONDS resolution from the raw XML splits the 173 into three classes:

| class | bookings | mechanism |
| --- | --- | --- |
| **window = duration + uncovered gaps EXACTLY at seconds resolution; short by 1 to 62 whole minutes** | **102** | the row's class — the minute truncation, and nothing else |
| window SHORTER than the occupancy, at seconds resolution too | 70 | 49 completed records (UIDs 5231 × 4 crews, 5249 × 3, in seven files — ADR-0476: a completed booking's window is its actual; the engine pins it, finish delta 0) and 21 bookings whose window begins after the task's or ends before it: 5270 / 5274 carry ADR-0502's absorbed booking delay (window + delay = occupancy, to the truncation), 5267's bookings finish 4 h before their task |
| window LONGER by 540 minutes | 1 | `Hard_File_updated4 24 hour calendar` UID 401, completed: its recorded `Start` precedes its first worked block by nine hours on a crew calendar that save declares no segments for — a record, engine delta 0, not this class |

The "~100" is **102 booking-rows = 76 + 16 + 10**: the four saves of the Large Test File2 schedule
(`SRA Large Test File2.mpp` at the root, under `mpp/` and under `ssi/` — three different blobs —
and `Large Test File2.mpp`) carry the same **19** bookings each, `Large Test File Leveled.mpp`
16, `Large Test File.mpp` 10 — **24 distinct (task, crew) bookings on 14 tasks**; the two
byte-identical duplicate saves in the corpus (`Project2.mpp` twice, `Project5.mpp` =
`Project5_TAMPERED.mpp`) carry no split at all. `Large_Test_File.mpp` (underscore, the SSI
golden's save) has 8 split bookings and **none** in the class — its 7 differing ones are the
completed records. Every member is a FIXED_WORK task at 0 %, ratio 1.0, on the ZIN Project
Calendar. The "1–28" was the range ADR-0501 happened to print: the class runs **1 to 62 minutes**
(UID 5278, 69 gaps: 7, 28 and 62 in the three saves), and the residual never exceeds the number
of gaps plus one.

**The mechanism, per gap.** MS Project places a split boundary in tenths of a minute: **every one
of the 3,742 boundaries in the corpus is a multiple of six seconds** (a piece ends on the
minute; the next begins 6, 12, 24, 36, 48 or 54 seconds past one). `_recorded_span` read a
boundary as `hour * 60 + minute` — both ends truncated — so each gap read **0.0 to 0.9 minutes
short and never long** (1,398 gaps: 33 exact, 548 short by 0.9); the window, read the same way,
gained or lost its own fraction. Over the class the engine's occupancy (duration + the honoured
gaps, whole minutes) was 1 to 62 minutes under a window it should have equalled.

**The other two suspects, refuted by reading and by measurement.** The share→`after` conversion
(`round(share × span)`) places a gap inside the leg's work; it does not size one, and the
occupancy is the same working-minute sum wherever the gaps sit. MPXJ's block boundaries are MS
Project's own instants — the `Assignment/Start` / `Finish` window carries the same seconds (the
window's first instant IS the first piece's start and its last the last piece's finish on 217 of
the 239 bookings; the 22 others are the absorbed-delay class and UID 401) — so the boundaries are
not a converter artefact but the file's statement, and truncating them is the engine's.

**Three readings, measured on every split booking before one was chosen** — the leg run from
the STORED start against the STORED finish, in working seconds of the leg's calendar:

| reading of the gaps | corpus class, |Δ| ≤ 30 s | ≤ 60 s | worst |
| --- | --- | --- | --- |
| each gap's two ends truncated to the minute (pristine) | 0 of 98 | 0 | 62 minutes short |
| each gap rounded to its nearest minute on its own | 8 | 24 | 4.8 minutes short, 6.1 long (UID 5316, nineteen gaps) |
| **the CUMULATIVE gap rounded at every boundary** | **67** | **77** | 72 s (the START's own truncated seconds, up to 59, plus the duration's) |

The cumulative reading makes every boundary the nearest minute of the true gap so far and their
sum the nearest minute of the whole, so the occupancy meets the window to the rounding of the
duration; per-gap rounding drifts by up to half a minute per gap and was refused.

## Decision

**The gaps are measured in working SECONDS and handed to the leg as whole minutes by rounding the
cumulative gap at every boundary.** `Calendar.intraday_worked_seconds` is the minutes rule at
seconds resolution (the same segments, the same contiguous fallback; the minutes form delegates
to it — one rule); `_recorded_seconds` is `_recorded_span` unrounded; `_covered_seconds` clips
the other bookings' windows on the same ruler; `_split_gaps` keeps the true gap so far in seconds
and appends, at each boundary, `_nearest_minute(cumulative) − honoured` when it is positive — so
a 24-second gap is no split (undisclosed) and a 30-second one is a minute (half up, the importer's
own rounding of a duration). Nothing downstream changed: `_execution_plans`, `_leg_finish`,
`_leg_retreat` and `_plan_scaled` consume the same `(after, minutes)` tuples; the task-split veto
(ADR-0491) runs on seconds and subtracts exactly.

**`_recorded_span` reads the nearest whole minute of its working seconds** — a material / cost
window (ADR-0487) whose ends carry different seconds is no longer truncated at each; one whose
ends carry the same seconds — a material booking spread over whole days — reads the same either
way (**106 material / cost windows in the corpus, 41 carrying seconds, 0 read differently**; the
goldens' 9 such windows, LTF and File2's UIDs 5276 / 5308–5312 / 5333, likewise). The planned-value
proration (`working_minutes_between`, ADR-0492) inherits the rule; the EVM parity pins are unmoved.

**Refused, and named:** per-gap rounding (measured above); carrying the gaps at seconds through
the leg (the model's axis is integer working minutes — Law of the model; every leg quantity is a
whole minute and `_advance_wall` consumes whole minutes); reading the duration's seconds (the
importer rounds a duration at import and the model stores integer minutes — the one residual left,
below); regenerating any golden (the goldens already carry the timephased data with its seconds).

## Verification

**Red first on the pristine package** (a separate worktree at `27ae8893`, `PYTHONPATH` on its
`src/`, the `-p mutcheck` plugin asserting the imported package): **17 failed by name / 51 passed**
over the six modules — the four new leveling-split pins (the four 2:36 gaps read 8, the three
36-second gaps read 0, the 30-second gap is no split, the lunch-hour boundary read as a whole
minute), the recorded-span pin (324), the calendar pin (no such method), the ten parity pins
(5342: 2,757; 5316: 9,329; 5273: 4,687; 5317: 3,103 for 3,118; 5306: 8; the three populations
short on 10 / 19 / 16; the class beside the row; 5268), and the two re-derived stored-slack pins.

**Mutation battery — 9 cuts, 9 / 9 RED by name** on fresh shadow copies of the FINAL `src/`
(control green on the shadow, every cut checksum-verified, the plugin asserting the shadow on
every row, every row with a verdict): M01 both ends truncated again · M02 per-gap rounding · M03
floor for half-up · M04 the seconds form ignoring the segments · M05 `_covered_seconds` returning
0 (the existing ADR-0491 pins bite too) · M06 the honoured minutes not subtracted (the 403 shape
reads 11-17 for 11-05) · M07 `_recorded_span` truncating · M08 the 24-hour branch in whole minutes
· M09 zero-minute gaps appended (the disclosure boundary) — red by name **13 · 12 · 12 · 32 · 8 · 20 · 8 · 4 · 2**.

**Measured, pristine → this tree.** The corpus class: **102 of 102 read occupancy == window**
(0 of 102 before); the 66 already-exact split bookings stay exact except **UID 5268** (below); the
negative class moves by −4 to +1 minute (its gaps re-read; its windows are records or delays).
The 15 goldens, per task, in WORKING minutes of the task's execution calendar against the stored
finish (a wall-clock census lies at a day boundary: a finish that now lands exactly at the day's
end renders as the next morning's first instant):

| golden | finish movers | toward | away | finish-within-a-day | stored slack exact | Critical |
| --- | --- | --- | --- | --- | --- | --- |
| Large_Test_File (fuse_ltf) | 66 | **66** | 0 | 1666 → 1666 | **867 → 874** / 1024 | 1721 |
| Large_Test_File2 | 104 | **101** | 0 (3 same) | **1687 → 1689** | **730 → 736** / 998 | 1717 |
| Large_Test_File_Leveled (SSI) | 100 | **96** | **4** | 1645 → 1664 | 789 → 841 / 1024 | 1720 |
| every other golden (Hard_File × 5, Project2 / 5, EVM1 / 2, the SSI Large_Test_File) | 0 | — | — | unmoved | unmoved | unmoved |

The four "away" are one chain — Leveled's **5306 → 6873 → 5307 → 6521**: 5306's four 2:36 daily
gaps now read 3, 2, 3, 2 = **10** where ADR-0491 recorded 8 and MS Project carries 10:24, so its
leg is **0.4 minutes** from MS Project's occupancy; the chain sits 494.6 working minutes late
because 5306's START is a day and fifteen minutes late (03-17 14:04 against the stored 03-16
13:49) for a reason that is not a split — the leg moved toward, the chain reads two minutes
further because the start's error and the leg's used to cancel by that much. `-m parity`
**187 → 197 green** (the ten new pins; the two re-derived floors). Statics green on both ruff
binaries, `ruff format`, `mypy --strict` (165 files), `bandit` (exit 0), `node --check` per file;
the wheel built after the last format; lockstep pins 68 passed.

**A render diff was NOT run** (the view layer is untouched; the movers are stored finishes of
Large Test File activities a page would print as dates — the full suite's web tests render every
page over the fixtures, and the goldens' census above is the measurement of what moved).

## Consequences

- **R-65 is CLOSED-0508.** The report's row records the closure and the numbers above.
- **Left, pinned by name, deliberately not chased:** File2's **UID 5268** — 8,157.8 minutes of
  duration (read 8,158 at import) plus 2,554.5 of gap (read 2,555) against a window of 10,712.3
  (read 10,712): two halves rounded up, one whole rounded down, **one minute LONG** — the only
  such booking in the corpus (exact before by the coincidence of two truncations). Closing it
  needs the duration's seconds to survive import; the model's integer minutes are a Law.
- The leveled golden's 5306 chain keeps its day (the start), now with the leg exact.
- The kickoff's trap list gains: **a residual's range is the range the last census printed**
  (1–28 was 1–62) · **a wall-clock census lies at a day boundary — count toward / away in
  working minutes** · **name the class beside the row before pricing the row** (70 of the 173
  were never this class) · **measure every candidate rounding on the population before choosing
  one** (per-gap rounding looked right and drifted six minutes).

## Deliberately NOT done

- **The duration's seconds** (UID 5268, above). · **A seconds axis in the model or the leg.** ·
  **The START's own truncation** (`_snap_to_working` reads `hour * 60 + minute`; a booking that
  starts at 08:00:54 begins at 08:00 — up to 59 s, inside every pin's resolution; the stored
  start is the corpus's own instant and no golden turns on it). · **The 21 absorbed-delay and
  early-finishing bookings** (5267 / 5270 / 5274 — ADR-0502's class and a booking that does not
  span its task; not this row's). · **UID 401 on the 24-hour snapshot** (a completed record whose
  Start precedes its first block; the crew calendar of that save declares no segments — a
  separate observation, registered in the handoff, no row). · **A render diff** (above).
