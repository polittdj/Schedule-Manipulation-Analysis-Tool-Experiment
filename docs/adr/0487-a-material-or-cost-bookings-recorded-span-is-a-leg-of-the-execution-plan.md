# ADR-0487 — A material or cost booking occupies the span the file records for it: the recorded assignment window is a leg of the execution plan (R-56)

- **Status:** Accepted — 2026-09-12 (the plan-forward's R-56, the first row of the report's §3 after ADR-0486).
- **Version:** 1.0.257
- **Extends:** ADR-0474 (execution plans — the WORK-booking legs this ADR leaves untouched), ADR-0476 (the re-specification of R-56 this ADR closes: "add UID 385; seven heads"), ADR-0034 / ADR-0391 (the stored-input reads whose discipline it follows), ADR-0403 / ADR-0486 (unrelated; the same session's OR-16 unit is ADR-0488).
- **Shipped:** `model/assignment.py` (`start`, `finish`), `importers/mspdi.py` (the booking window, earliest start → latest finish per task+resource pair), `importers/json_schedule.py` (round trip), `engine/cpm.py` (`_recorded_span`, `_LegShape.recorded`, `_Exec.recorded`, the non-work leg in `_task_shape`, the two plan-forming rules, `CPMResult.booking_span_driven`), `tests/engine/test_recorded_booking_span.py` (11), `tests/parity/test_hard_file_stored_dates_oracle.py` (re-pinned + 1), `tests/importers/test_mspdi.py` (+1), the maximal JSON fixture.

## Context

R-56 was the whole of `Hard_File_updated3`'s remaining project-finish gap: after ADR-0476 the
engine read the finish **13 days early** (2026-11-29 vs the stored 2026-12-12 17:00), 60 of 110
activities within a day of MS Project, 9 of 68 stored slacks reproduced. ADR-0476 traced it to
two chain heads on unstarted work — **UID 385** (−15.3 d) and **UID 403** (−12.8 d) — called it a
duration-CONTOUR defect, and told the next session to tally the heads' `<Assignment>` units,
work and timephased data against the task duration before believing any rule.

### What the tally found (QC-1: measured, then refuted where it could be)

**The chain heads, re-derived on the live engine** (a finish disagreement of more than a day
whose every predecessor agrees): **five**, not seven — 385 (−15.33 d), 403 (−12.76 d), 302
(−1.88 d), 188 (−1.0 d) and 300 (−1.5 d, ADR-0476's day-boundary milestone) — with 45 rows
inherited from them. The seven in ADR-0476 counted at a different threshold; the mechanism it
named holds for two of them.

**The MSPDI carries no timephased data at all** (every golden: 0 `TimephasedData` elements on
tasks or assignments — MPXJ's MSPDI writer does not emit it by default), so the "contour" could
not be read from the XML. It was read from the **`.mpp` itself** through the vendored MPXJ
16.2.0 (`getRawTimephasedRemainingRegularWork`, `getWorkSplits`, `Resource.getType`,
`getVariableRateUnits`):

| UID | the work crews (ADR-0474's legs) | the non-work bookings | MS Project's task finish |
| --- | --- | --- | --- |
| 385 | CST 100 % / 4,224 min on the 16-hour calendar → 10-20 06:24 (**the engine's finish, exact**); Logistics 25 % / 1,056 min on 24 h → 10-16 15:24 | *AI Token Time* (MATERIAL, 100 %, 1 unit) 10-13 17:00 → 10-18 22:24 — 24 h of Standard time; *Cleaning* (COST, 0.06 %, 2.5 units) 10-14 08:00 → **11-04 14:24** — 125.4 h of Standard time | **11-04 14:24 = the Cleaning booking's finish** |
| 302 | CSL 100 % / 30 h on Standard → 10-19 15:00 (**the engine's finish, exact**); CST 30 h on 16 h → 10-15 15:00 | *AI Token Time* (100 %, 1 unit) and *Cleaning* (0.06 %, 0.15 units) BOTH 36 h of Standard time plus one 8-hour split gap → **10-21 12:00** | **10-21 12:00 = the Cleaning booking's finish** |
| 403 | CSL 100 % / 32 h, leveling delay 9,060 min honoured (start exact) | none | 11-05 09:12 — the `.mpp` shows **two work pieces seven days apart** (`getWorkSplits`): a leveling SPLIT the MSPDI does not carry |

So the engine's WORK legs are right to the minute on both heads, and MS Project's task finish is
the finish of a **material or cost booking the engine skipped** (non-WORK resources contribute no
leg, ADR-0474). The span of such a booking follows **no rule the file carries**: at 302 two
bookings with different quantities and rates share one 36-hour span; at 385 the 100 % booking
spans 24 h and the 0.06 % booking 125 h. Quantity ÷ rate, rate × duration, the task duration on
any of the file's calendars, and the work legs' spans were each tried against both tasks and each
fails at least one (the tally is in the session log). MS Project's own `Duration` field
(94 h 24 m at 385) is not the task's span on the project calendar either (125.4 h) — the
`.mpp` reports no split for 385 — so the mechanism is inside MS Project and not in any exported
quantity. **What the file DOES carry is the span itself:** every `<Assignment>` records its
`Start` and `Finish`.

**A data-date floor was refuted again** (ADR-0476's construction re-run: unchanged), and a
per-assignment "contour" of the WORK bookings was refuted by the `.mpp` (flat, one entry each).

### Provenance of the oracle (QC-2)

The intake `00_REFERENCE_INTAKE/mpp/Hard_File_updated3.mpp` is **not** the file the committed
fixture was converted from: the fixture is Revision 2 (saved 2026-07-09 10:12), the intake file
Revision 5 (2026-07-15 13:26), and they differ on **12 tasks and 12 bookings — all re-leveling**
(UIDs 129, 235, 237, 267, 281, 283, 289, 315, 392, 402, 403, 404; 403's finish 10-30 15:00 vs
11-05 09:12; 267's leveling delay 190,200 vs 262,200 tenths). Acumen Fuse's *update2 vs update3
Forensic Analysis Report* records UID 403 finishing **2026-11-05 09:12** — the fixture's value —
so **the fixture is the file Fuse analysed** and the intake `.mpp` is a later re-save Fuse never
saw. The fixture was therefore NOT regenerated; `Hard_File.mpp` (Revision 4 vs the fixture's 1)
and `Hard_File_updated2.mpp` convert to byte-identical task and booking sets.

## Decision

**A MATERIAL or COST booking occupies the span the file records for it.** `Assignment` carries
the booking's recorded window (`start`, `finish`; `None` when the source records none — every
earlier Save .json, every XER). For a non-WORK booking with a window, `_task_shape` adds one
execution leg on the crew's calendar (the resource's registered calendar, else the project's; a
non-24-hour task calendar wins, as for every leg) spanning `_recorded_span(calendar, start,
finish)` — the calendar's working minutes inside the window, **segment-aware at both ends**
(a 14:24 finish on a 08–12 / 13–17 day is 324 minutes into it, not the contiguous projection
ruler's 384: that ruler landed UID 385 one lunch gap late, at 15:24, when the rule was first
measured), elapsed time on a 24/7 calendar. The leg's ratio to the task duration may exceed 1,
so the two plan-forming rules admit it: legs that all sit on the project pattern still form a
plan when one outspans the duration (the fast path could never carry a task past its duration).
The task finishes at its latest leg, as every plan task does.

**A WORK booking's window is never read.** The engine reproduces it from work / units / calendar
(ADR-0474; exact on both heads above), and reading MS Project's placed dates for computed work
would be transcription of an output. A material / cost span is the opposite case: no input in
the file derives it, MS Project schedules by it, and the recorded window is the one fact the
file carries — read like the leveling delay (ADR-0474), a stored scheduling input, and
disclosed: **`CPMResult.booking_span_driven`** names every task whose PRIMARY (latest-finishing)
leg is a recorded span. Deliberately not merged into `date_driven` (not an unsupported date) nor
into the actual-start / actual-finish lists (not work begun) — ADR-0474's reasoning for
`leveling_driven`, applied once more.

Refused, and named: a data-date floor (refuted twice); a quantity-or-rate rule for the span
(no candidate survives both heads); regenerating the updated3 fixture from the intake `.mpp`
(it is not Fuse's file); reading a WORK booking's window (above); emitting the MSPDI
`TimephasedData` from the converter to recover leveling splits — a real unit for UID 403's
kind (registered below), not this row's.

## Verification

**Measured first, on a scratch copy of the engine with the spans read from the XML** (the rule
before a model field existed), pristine → rule, every golden:

| golden | project-finish gap | finish within a day | stored slack exact | Critical agreed |
| --- | --- | --- | --- | --- |
| **Hard_File_updated3** (both copies) | **−13.00 d → 0.00 d — exact** | **60 → 103** / 110 | **9 → 42** / 68 | 103 → 103 |
| Hard_File / _updated | −1 d / −1 d, unmoved | 92 / 100, unmoved | 3 / 52, unmoved | 108 / 110, unmoved |
| Hard_File_updated2 | −1 d, unmoved | 93, unmoved | 8, unmoved | 80 → **81** |
| Hard_File_updated3_24hr / updated4_24h | −2 d, unmoved | 100, unmoved | 4, unmoved | 70, unmoved |
| Large_Test_File / File2 / Leveled / ssi copies | unmoved | 1569 / 1589 / 1569 / 1670, unmoved | 842 / 668 / 780 / 946, unmoved | unmoved |
| Project2 / Project5 | **exact, unmoved** | 126 / 126 | **65/65, 95/95** | 124 / 126 |
| EVM2 | −2.21 d → −1.00 d | 5 → 6 / 11 | — | 11 |

**After the segment-aware span**, UID 385 lands on **2026-11-04 14:24** and UID 302 on
**2026-10-21 12:00** to the minute; the project finish is 2026-12-12 17:00 exactly. The
disclosure names **210, 302, 385** on updated3 — 210 is a completed fixed-duration task whose
24-hour crew leg alone would end four days early; its material window carries the plan to the
recorded finish, which ADR-0476's completed-window pin then confirms. UID 403 is unchanged
(10-23 15:00): a leveling split, registered as its own row.

**Red first.** `tests/engine/test_recorded_booking_span.py` cannot import on the pristine tree
(`_recorded_span` does not exist; `Assignment` refuses a window); the oracle module on the
pristine engine fails the re-pinned updated3 row and the new exact-instant test by name (2 failed
/ 8 passed). Green on this tree with the resource-calendar, completed-window, importer, JSON
and perf modules: 171 passed.

**The perf gate caught a real regression in the first cut:** the recorded legs were tracked in
a `set` keyed on the frozen `Calendar` model — 420 `Calendar.__hash__` calls across 20 solves,
exactly the value-keyed memo ADR-0474's latency amendment forbids on a solver the SRA calls a
thousand times. Keyed by calendar identity and span now; 0 hashes.

**Mutation battery — 12 mutants, 12 / 12 RED by name** on shadowed copies of `src` (the
instrument — the real tree and its tests — never mutated; the control run green): the non-work
leg removed · the contiguous ruler in place of the segment-aware span · the ratio-above-one
plan rule reverted (in `_task_shape`) · the same in `_execution_plans` · the recorded flag never
set · the disclosure never populated · the WORK guard removed (a work booking's window read) ·
the finish day's minutes dropped from the span · the importer dropping `Finish` · the JSON
writer dropping `finish` · the JSON parser dropping `start` · any recorded leg flagging the task
(not only the primary). **One instrument finding:** the last mutant read GREEN on the first run
because the "shorter window" rig had no off-pattern crew — the fast path dropped every leg and
the disclosure was empty under both versions, so the rig could not see the mutation; the rig
now carries the two-shift crew, and the mutant reads red.

## Consequences

- **R-56 is CLOSED-0487.** updated3's finish is exact; the report's row records the closure. The
  `-m parity` gate and the LTF / Project2 / Project5 pins are unmoved.
- Two rows the investigation exposed are registered: **R-60** — leveling SPLITS live only in the
  `.mpp`'s timephased data (403: two work pieces seven days apart; Hard_File's 14 / 401 the same
  class); the vendored converter could emit MSPDI `TimephasedData` (`MSPDIWriter.
  setWriteTimephasedData`) and the engine honour the gaps as it honours the delay. **R-61** — a
  FIXED_DURATION booking on an off-pattern crew spans the duration in CREW minutes (ADR-0474's
  rule) where MS Project keeps the task's window (UID 210's Content Developer booking: four
  project days recorded, 1.33 crew days computed), masked today by the completed-window pin.
- The intake `.mpp` / fixture provenance is recorded so no session regenerates the oracle from
  the wrong save; the Fuse report is the arbiter of which save is the reference.
- **Two pins moved with the base CPM and were re-pinned knowingly:** the `Assignment` schema freeze
  (the two new fields) and the change-effects sentence on the Hard_File → updated3 pair, 33 → 32 of
  33 reschedule artifacts without effect on the target finish — restoring UID 384's data-date SNET
  now moves the target −1 wd because its successor 385 sits on the driving chain exactly as in MS
  Project (ADR-0474's rule: an engine-derived counterfactual moves with the base CPM by design).
- `Assignment.start` / `finish` are new model fields: the JSON writer emits them when present,
  the D5 writer census pins that, and a Save .json written by this version reopens with them.
