# ADR-0491 — A leveling split is honoured inside the task the way the leveling delay is: the converter writes the timephased data, the importer reads a booking's pieces, and the engine carries every gap nobody works through (R-60)

- **Status:** Accepted — 2026-09-14 (the plan-forward's R-60, the row the kickoff put first).
- **Version:** 1.0.259
- **Extends:** ADR-0474 (execution plans — the leg this ADR gives a shape), ADR-0487 (the recorded-window leg and the registration of R-60; its "the fixture is NOT regenerated" premise is lifted here by evidence), ADR-0476 / ADR-0391 (the progress rules the split leg runs under), ADR-0152 (the intake in git — where the fixture's own save was found).
- **Shipped:** `tools/mpxj/MpxjToMspdi.java` + `classes/MpxjToMspdi.class` (`setWriteTimephasedData(true)`), `model/assignment.py` (`WorkPiece`, `Assignment.work_pieces`), `model/__init__.py` (SCHEMA_VERSION 2.13.0), `importers/mspdi.py` (`_timephased_pieces`), `importers/json_schedule.py` (round trip), `engine/cpm.py` (`_Leg` with gaps, `_LegShape.gaps`, `_split_gaps` / `_worked_windows` / `_covered_span`, `_leg_finish` / `_leg_retreat`, the two plan-forming rules, `_plan_scaled`, `CPMResult.split_driven`), `tools/regenerate_timephased_goldens.py` + `tests/fixtures/golden/PROVENANCE.json` (14 goldens regenerated from their own saves), `tests/engine/test_leveling_split.py` (14), `tests/guards/test_golden_provenance.py` (17), `tests/importers/test_mspdi.py` (+3), `tests/importers/test_mpp_mpxj.py` (+1, Java-gated), `tests/parity/test_hard_file_stored_dates_oracle.py` (re-pinned), the schema freeze and the maximal JSON fixture.

## Context

R-60 (ADR-0487): MS Project's resource leveling can split a booking into pieces of work with
zero-work gaps between them; the split lives only in the `.mpp`'s timephased data, which the
vendored converter did not write, so the engine ran the pieces contiguously. Hard_File_updated3's
UID 403 read 2026-10-23 15:00 against the stored 11-05 09:12 — the whole of that file's remaining
per-activity gap — and Hard_File's UIDs 14 / 401 were named as the same class.

### What was measured first (QC-1 / QC-2)

**The fixture's own save is in git history, and it is provably the golden's.** The committed
updated3 golden is Revision 2 (saved 2026-07-09 10:12); the intake `.mpp` is Revision 5. ADR-0487
recorded the golden as "NOT regenerated — the same save is not available". `git show
af4d154f:00_REFERENCE_INTAKE/mpp/Hard_File_updated3.mpp` (uploaded 2026-07-09, deleted, re-uploaded
as Revision 5 on 07-15) is blob `1908d073`; converted with the vendored converter it differs from
the golden on **32 lines** — `CurrentDate` and four resource elements (`MaxUnits` 1 → 2,
`OverAllocated` 1 → 0, `AvailableTo 2026-08-01` → `AvailableFrom 2026-08-02`, `StandardRate` 10
→ 30 with its overtime rate): the writer resolves those at CONVERSION time, and the golden was
converted on 07-09 — while the `<Tasks>` and `<Assignments>` sections are **byte-identical**. The
same test over every historical blob of every intake `.mpp` (36 blobs, 30 paths, all converted)
matched **14 of the 16 MSPDI goldens** to one save each by identical task and assignment sections
(the two EVM goldens have no committed source); `tests/fixtures/golden/PROVENANCE.json` records
each golden's blob, commit, revision and save time, and `tests/guards/test_golden_provenance.py`
pins every golden's own header to it. The register's "provenance by the Fuse report's figure"
is now provenance by section diff — stronger, and executable.

**UID 403 on the fixture's save is THREE pieces, not two** (the register's two were the intake's
Revision 5): 14 h → 10-21 12:00, nothing until 11-02 13:00 (eight working days), 12 h → 11-03
17:00, nothing until 11-04 11:12 (3.2 h), 6 h → 11-05 09:12; a 9,060-minute elapsed leveling delay
the engine already honoured puts its start at 10-19 15:00, exactly the stored start. MS Project's
stored LateStart 11-25 13:48 and TotalSlack 12,888 minutes retreat from the stored LateFinish
12-11 17:00 through the pieces AND the gaps in **working minutes** of the calendar (12-11 17:00 −
1,920 − 3,840 − 192 = 11-25 13:48; ES → LS = 12,888) — the file's own arithmetic settles the unit a
gap is measured in.

**Splits are corpus-wide, not one activity.** MPXJ's `getWorkSplits` over the saves: Hard_File 5
unstarted split bookings (14, 321, 398 (one of three), 401, 403), updated2 2, updated4-24h 16
(mostly completed), the 24Hour Calendar save 8; the Large Test Files carry a daily pattern on UID
5265 (afternoons only, sixteen gaps in one booking) and dozens downstream of it.

**The writer flag, priced.** `MSPDIWriter.setWriteTimephasedData(true)` writes every assignment's
raw remaining / actual / baseline series as `<TimephasedData>` (Types 1, 2, 3, 4, 5 seen; the
importer reads 1 and 2). Large_Test_File (1,723 activities): 21.4 → 23.0 MB (+7 %, 5,158 elements),
the same wall time under the `--server` heap cap (`-Xmx1g`); the Python parse 2.1 → 2.5 s;
Hard_File_updated3 867 KB → 1,044 KB (+20 %, 617 elements, 498 of them baseline).
`setGenerateMissingTimephasedData(true)` throws a `NullPointerException` inside MPXJ 16.2.0 on
that file and is refused (a generated series would carry no split anyway).

**Type codes verified by measurement, not memory:** Type 1's blocks equal MPXJ's
`getRawTimephasedRemainingRegularWork` and Type 2's `getRawTimephasedActualRegularWork`
block-for-block on the Revision-2 save (starts, finishes, 840 / 720 / 360 minutes).

## Decision

**The vendored converter writes the timephased data** (`writer.setWriteTimephasedData(true)` in
`convert()`, rebuilt at bytecode level 61 — the level the shipped class had). Every ingest carries
it from now on; the importer ignores every series but the booking's own work.

**The importer reads a WORK booking's pieces.** `_timephased_pieces` takes the assignment's Type 1
and Type 2 blocks in time order; every maximal run of worked blocks is one `WorkPiece` (start,
finish, work minutes), a block with no `Value` or a zero one between two runs is the split, a zero
block at either edge bounds nothing, and fewer than two runs is no split (`Assignment.work_pieces ==
()`, the ordinary contiguous leg). A pair recorded in several rows gathers its pieces in time
order. The JSON Save writes and reads them; an XER, an earlier Save and an earlier conversion have
none. `SCHEMA_VERSION` 2.12.0 → 2.13.0 — and the ledger records, retroactively, that ADR-0487's
`Assignment.start` / `finish` shipped without the bump (the 2.9.0 case: the freeze test asserts a
literal and cannot see an un-bumped add).

**The engine carries the gap between the pieces that no other booking of the task works through,
in working minutes of the leg's calendar, forward and backward.** A leg is now `_Leg(calendar,
span, gaps)` with `gaps = ((after, minutes), …)`: once `after` of the leg's minutes are worked,
`minutes` of the calendar's working time pass with no work. `_split_gaps` derives them from the
pieces — the share of the booking's work performed before each gap, and `_recorded_span` of the
calendar between the pieces (a night, a lunch, a weekend between two day-blocks measures zero and
is no gap) — **less the working minutes other WORK bookings of the task work inside that window**
(`_covered_span`, their pieces or their recorded windows, clipped and merged). The share scales
with the leg (an SRA duration override moves the gap's place in the work, as every leg quantity
scales); the gap's minutes do not (a calendar quantity, like the delay). `_leg_finish` advances
piece, gap, piece; `_leg_retreat` is its mirror, so the backward pass and float pass through the
gaps as MS Project's do; `_plan_scaled` (the resume floor) keeps a gap still ahead of the remaining
tail and drops one in the consumed head. A split leg forms a plan even on the project pattern
(the fast path cannot carry a gap — ADR-0487's rule for a recorded span, applied again). Every task
whose plan carries a gap is disclosed on **`CPMResult.split_driven`** — a stored scheduling input
read like the delay and the recorded span, neither an unsupported date nor evidence of work begun.

**The task-split test is the finding of this unit.** The first cut honoured every gap. Measured on
the corpus, one chain moved AWAY from its stored dates by three weeks: Large_Test_File2 UID 5308, a
FIXED_DURATION task of 228 h with eight bookings, one of which (resource 76) records ten minutes of
work, then nothing for three weeks, then 28 h — while the other seven work straight through the
window, and MS Project's 228-hour Duration already spans it (its stored finish IS that booking's
finish, at the duration's end). A gap another booking works through is that booking's own contour,
inside the duration; a gap NOBODY works is the TASK's split, which MS Project's Duration excludes —
UID 5265 on every Large Test File (its only booking's daily afternoon-only pattern: a 36.85-hour
duration over a 15-day span) and UID 403 are that case, and they land exact. Two unit tests pin the
two sides (a fully covered gap: undisclosed, the finish at the duration; a half-covered gap: the
uncovered half honoured).

**The goldens are regenerated from their own saves, by splice, with the proof inside the tool.**
`tools/regenerate_timephased_goldens.py` extracts each golden's blob from git (`git cat-file
blob`), converts it with the shipped converter, PROVES the same save (the `<Tasks>` section
byte-identical; the `<Assignments>` section identical once every `<TimephasedData>` is removed),
and writes the old golden with the new `<Assignments>` section spliced in — so the only change is
the timephased data; the header and the resources keep the values the golden was converted with,
because the writer's `CurrentDate`, `MaxUnits`, `OverAllocated`, `AvailableFrom` / `To` and rates
are wall-clock artefacts of the conversion, not properties of the save. Gzipped goldens are
written with a zero mtime and no name.

**Refused, and named:** an elapsed reading of a gap (the file's own LateStart arithmetic refutes
it — see "Deliberately NOT done" for what the corpus cannot tell); regenerating the goldens from
the intake paths' current bytes (Revision 5 is not the file Fuse analysed); a full regeneration
that would inherit today's wall-clock resource values (two resources' `MaxUnits` would change
under the resource-loading view for no reason of the save's); honouring a gap another booking
works through (the 5308 finding).

## Verification

**Measured on every golden, the pristine engine on the pristine goldens → this engine on the
regenerated goldens** (`tests/parity/test_hard_file_stored_dates_oracle.py`'s census, re-run
outside the suite; movers = activities whose early start or finish changed):

| golden | project-finish gap | finish within a day | stored slack exact | Critical agreed | movers toward / away |
| --- | --- | --- | --- | --- | --- |
| **Hard_File** | **−1.00 d → 0.00 — exact** | **92 → 103** / 110 | 3 → 5 / 76 | 108 | 20 / 0 |
| **Hard_File_updated** | **−1.00 d → exact** | **100 → 108** | 52 → 60 / 70 | 110 | 20 / 0 |
| **Hard_File_updated2** | **−1.00 d → exact** | **93 → 109** | **8 → 36** / 76 | **80 → 107** | 24 / 0 |
| Hard_File_updated3 (both copies) | exact, unmoved | 104 → 106 | 43 → 46 (SSI copy 45) / 68 | 103 | 2 / 0 |
| Hard_File_updated3_24hr / updated4_24h | −2 d, unmoved | 100 | 4 / 19 | 70 | 0 / 0 (14 completed split tasks, pinned) |
| **Large_Test_File** | −0.62 d, unmoved | **1569 → 1666** / 1723 | **842 → 865** / 1022 | **1682 → 1721** | 100 / 0 |
| **Large_Test_File2** | exact, unmoved | **1589 → 1687** / 1722 | 668 / 936 | **1686 → 1717** | 104 / 0 |
| Large_Test_File (SSI copy) | unmoved | 1670 | 946 | 1723 | 0 / 0 (3 completed) |
| Large_Test_File_Leveled | −0.62 d, unmoved | **1569 → 1645** | 780 → 787 | **1676 → 1720** | 99 / 4 |
| Project2 / Project5 | exact, unmoved | 126 / 126 | 65/65, 95/95 | 124 / 126 | 0 / 0 |
| EVM1 / EVM2 | unmoved (no source, not regenerated) | — | — | — | — |

The four "away" movers are UID 5306's chain on the leveled golden: **+24.1 h → +24.2 h** — the
8 minutes MS Project's own arithmetic carries (its stored finish is its start plus its 39 h 47 m
duration plus four 2:36 daily gaps, 10:24; the engine's integer-minute calendar reads 2 × 4 = 8)
on a start already a day late for a reason that is not a split. Before the task-split test, the
same census read Large_Test_File2 **24 away** (the 5308 chain, +410 to +498 h) — the measurement
that produced the rule.

**To the minute:** updated3's UID 403 finishes 11-05 09:12 with LateStart 11-25 13:48 and TotalSlack
12,888 (the stored values; the chain's UID 404 exact); Hard_File's UID 14 spans its stored
10-26 20:00 → 10-29 11:00; UID 401 spans 5.6 days like MS Project's and, with its chain 400 → 404,
sits one working day early because milestone 387 upstream hangs on an external predecessor the
MSPDI cannot resolve (UID −65535) — named, registered below, not a split. updated2's UID 269 (a split
plus a leveling delay) lands exact; Hard_File_updated2's Critical agreement 80 → 107 follows from
its project finish becoming exact.

**Red first.** `tests/engine/test_leveling_split.py`, the schema freeze and the maximal JSON test
cannot import on the pristine tree (`WorkPiece` does not exist; `Assignment` refuses
`work_pieces`; `CPMResult` carries no `split_driven`); the importer's two new tests fail by
`ImportError` at the call; the oracle's re-pinned updated3 row fails by name on the pristine engine
(10-23 15:00 against 11-05 09:12; LateStart 12-08 08:00 against 11-25 13:48). The first green run of
the rig then refuted the RIG: two pieces declared as 240 minutes over a 480-minute window — the
engine trusts the work minutes, and the expectation was corrected, not the engine.

**Mutation battery — 18 mutants, 18 / 18 RED by name** on shadowed copies of `src` (a plugin
asserts the imported package IS the copy; the control run green): the forward advance ignoring
the gaps · the backward retreat ignoring them · no gaps derived · a gap in elapsed minutes · the
shape rule dropping split legs · the plan rule dropping them · the disclosure never populated ·
the task-split veto removed · the veto applied to every gap · the scaled plan dropping its gaps ·
the importer reading the baseline series · a zero block not closing the run · one run returned as
pieces · the JSON writer dropping the pieces · the parser dropping them · pieces unsorted across
rows (the one survivor of the first pass — no test pinned it; `test_a_pair_recorded_in_several_
rows_gathers_its_pieces_in_time_order` now does) · the converter's flag off (a mutated class under
a scratch `SF_MPXJ_HOME`; the Java-gated test reads no pieces) · the provenance manifest naming
the Revision-5 save (the guard, in memory).

**The gate:** both ruff binaries clean, `ruff format --check` clean, mypy strict clean, the
oracle module 10 passed, the engine / importer / JSON / schema / guard modules green; the full
suite and the installer rebuild are recorded in the session log (2026-09-14).

## Consequences

- **R-60 is CLOSED-0491.** The report's row records the closure and the numbers above.
- **Registered: R-63** — the converter's output depends on the conversion date: `CurrentDate`, and
  a resource's `MaxUnits` / `OverAllocated` / `AvailableFrom` / `AvailableTo` / `StandardRate` /
  `OvertimeRate` resolve at "now" (measured: the same save converted 07-09 and 09-14 differs on
  exactly those; `MaxUnits` feeds the resource-loading view's capacity). **R-64** — Hard_File's
  milestone 387 (and the chain 400 → 404 behind it, one working day early) hangs on an external
  predecessor link (`PredecessorUID` −65535) the MSPDI cannot resolve.
- **Left, measured:** the engine's integer-minute calendar rounds a 2:36 gap to 2 minutes (UID
  5306: 8 of 10:24); the leveled SSI golden's stored slack 780 → 787 was re-measured, not pinned.
- **Every ingest now carries timephased data** (+7 % on the largest file, +0.4 s of parse); the
  goldens grew accordingly. A Save .json written by this version reopens with the pieces; the D5
  writer census pins them.
- Two pins moved with the base CPM and were re-pinned knowingly: the stored-dates oracle (every
  Hard_File row exact; the floors raised; the 403 comments rewritten to name 387's external link)
  and the schema freeze (`WorkPiece`, `work_pieces`, 2.13.0). ADR-0430-style teeth pins were
  re-read: none cites the contiguous 403 as its reason.

## Deliberately NOT done

- **Gap semantics when the START moves.** Every stored start in the corpus equals the recorded
  first piece's start, so the corpus cannot tell a working-minute gap from an elapsed one when a
  predecessor slips; the file's backward-pass arithmetic (403's LateStart) is the one observation
  and it is working-minute. `test_the_gap_is_working_minutes_of_the_leg_calendar_not_elapsed_time`
  pins the chosen reading so a future re-pin is deliberate.
- **Dropping the baseline series from the converter output** (Types 4 / 5 are 81 % of the
  elements): MPXJ 16.2.0's `ResourceAssignment` exposes no setter for them; a post-filter in Java
  would be a second serializer. Priced at +7 % and left.
- **A task-level `<Splits>` element** in the model: the split is a property of the bookings, and
  the task-split test derives the task's gap from them; a model field would be derived data.
- **Sub-minute gaps** (the model's integer minutes); **R-57** (an assignment's own leveling delay:
  Hard_File UID 398's RA 277 is a split ON a delayed assignment — its gap is honoured, its delay
  is not), **R-58**, **R-61**: untouched, each its own row.
- **The EVM goldens** are not regenerated (no committed source) and carry no splits.
