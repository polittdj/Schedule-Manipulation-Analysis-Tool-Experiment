# ADR-0523 — The project axis is WORKING MINUTES in both directions: the stored-date family and the rendering move as one segment-aware pair, and R-77's own population did not reproduce (R-77 CLOSED)

**Status:** Accepted · **Date:** 2026-09-22 · **Extends:** ADR-0348 (the day-boundary start/finish spelling), ADR-0517 / R-73 (`_stored_instant_offset`, the segment-aware read of a stored Resume), ADR-0522 / R-74 (the free-float bound whose control pin this moves) · **Supersedes in part:** ADR-0322's two-ruler rule (int→wall segment-aware, wall→int contiguous) · **Row:** R-77 (T2, M) in `docs/STATE/AUDIT-2026-08-27-REPORT.md` §3

## Context

Roadmap row R-77 (T2, M). The row read:

> the stored-date family projects with the CONTIGUOUS ruler on an axis that is working minutes …
> the actual-start floor, the completed-window pin, the stored-start pin / floor, constraint dates
> and deadlines, ADR-0309's residual floor, and the rendering all read a mid-day instant with
> `clamp(tod − start_tod)` … **4** started activities whose 13:00 actual start reads the gap late,
> **25** completed activities whose pinned finish reads 54–60 minutes late, and **212** unstarted
> finishes exactly one lunch gap off their stored instant; EVM2's chain diverging at UID 23 is the
> same mechanism.

The mechanism is right. The row's numbers and its named witness are not.

### The row's population does not reproduce, and it is not drift

The 44-file corpus was rebuilt from scratch — 29 path-keyed MPXJ conversions of the intake `.mpp`
files plus the 15 committed goldens (11 of them gzipped) — and reproduces ADR-0513's population
exactly: **22,105 scheduled activities**. Measured on it:

| R-77 claims | best reproduction found | |
| --- | --- | --- |
| **212** unstarted finishes one gap off | **104** rendered / **2,506** by stored-instant projection | neither is 212 |
| **25** completed finishes 54–60 min late | **23** at exactly +60 / **34** across the band / **0** rendered | neither is 25 |
| **4** started, 13:00 actual start | **4** | **exact** |
| EVM2 UID 23 diverges | start delta **0**, finish delta **0** | the named witness is clean |

The identical census run against the **v1.0.281** tree (a worktree at `601be5d3`) returns the same
figures to the row, so the discrepancy is not drift from ADR-0517/0519/0520/0521/0522. Only the
class-1 four reproduces — and it reproduces only under the measure the row's *prose* does not state:
the projection error at the STORED instant, not the rendered round trip. A pin that is projected
contiguously and rendered contiguously **cancels its own error**, so the first census built here was
blind to exactly the class the row names. That blindness is the finding, not the row's arithmetic.

### The class the row does not count is the one that matters

**15,224 of 22,105** rendered finishes sat exactly one lunch gap EARLY. A 17:00 stored finish
projects through `clamp(1020 − 480, 0, 480)`, **saturates at 480**, and `offset_to_datetime`
un-saturates it to 08:00 + 480 = **16:00**. The round trip is lossy by exactly the gap width, on
every gapped calendar, every day. The row names this only in its remedy ("an end-of-day finish
renders 17:00, not 16:00") and counts it nowhere; it is two orders of magnitude larger than the three
classes it does count.

## Decision

`datetime_to_offset` and `offset_to_datetime` become a **segment-aware pair**, using the helpers
ADR-0517 already built (`_worked_before` / `_tod_at_worked`). ADR-0322 refused a segment-aware read
at any ONE site because projecting wall→int segment-aware while the constraints, the stored pins and
the rendering still measured contiguously made a single instant carry two offsets — a successor
rendered BEFORE its predecessor's finish, a same-instant SNET out-bounding the link inside one
`max()`. That hazard is a property of the ASYMMETRY, not of the segment-aware reading: with the pair
moved together there is one ruler again, and `_wall_to_offset` (whose body *is* `datetime_to_offset`)
moves with it by construction. R-77's plan-forward asked for the pair to move *and* for
`_wall_to_offset` to stay unchanged; that is not satisfiable, and the pair wins.

Two rules the naive change got wrong, both found by QC-3 before the first edit to the tree:

* **The segment-aware arithmetic is GUARDED on `r.declared_segments`, not routed through
  `_Ruler.segments`.** That helper re-anchors its fallback block to MIDNIGHT whenever
  `day_start_tod + minutes_per_day > 1440`, so an undeclared calendar with a late project start is
  silently re-based — **1,150 projection and 400 expansion divergences** in a sweep of project-start
  times of day. R-77's premise that "the fallback is the contiguous block by construction, so
  synthetic fixtures and P6 exports are byte-identical" is **FALSE as written**; the guard makes it
  true by construction.
* **The intraday term is measured RELATIVE to the project start's own worked position.**
  ADR-0312's importer precondition bounds only `start_tod + minutes_per_day <= 1440` and, inside
  that domain, `anchored_project_start` returns the start **UNCHANGED** — a 09:00 start on an
  8-hour day is legal and untouched. The contiguous pair read its own origin as 0 for every such
  start by construction (`clamp(tod − tod)`); a segment-aware pair anchored at the SEGMENTS reads
  it as 60, and on a declared 24-hour day an 08:00 start as a whole **480** — an axis shifted by a
  working day, silently, on a legal file. This was found by the adversarial blast-radius sweep
  AFTER the first push and fixed in the same PR. It moves **no** measured figure: every one of the
  44 corpus files starts at 08:00 on an 08-12 / 13-17 calendar, where the start's worked position
  is 0 and the relative form is algebraically identical to the absolute one (measured: 44 of 44).
* **An offset on an internal block boundary has two spellings, and the role picks.** 12:00 and 13:00
  are both "240 minutes worked". A FINISH takes the earlier, a START the later — ADR-0348's
  day-boundary rule one segment down, shipped as `_tod_at_worked_start` and consumed by
  `offset_to_start_datetime`. Without it four 13:00 stored starts rendered 12:00.

## What it measured

Against **MS Project's own stored slack** over the 44 files — an oracle independent of the engine:

| | pristine (v1.0.286) | this tree | |
| --- | --- | --- | --- |
| stored **Total Slack** exact | 10,610 / 12,680 | **11,041** | **+431** |
| stored **Free Slack** exact | 3,004 / 3,315 | **3,094** | **+90** |
| free float reading HIGH | 198 | **134** | −64 |
| free float reading LOW | 113 | **87** | −26 |
| rendered **start** instants exact | 17,009 / 22,105 | **20,990** | +3,981 |
| rendered **finish** instants exact | 5,444 / 22,105 | **20,960** | +15,516 |

The pristine column reproduces ADR-0522's recorded figures to the digit (10,610 / 12,680 and
3,004 / 198), which is how the instrument is known to be the same one. The free-float residual falls
on BOTH sides at once, so the gain is not one direction bought with the other.

Over the fifteen committed goldens alone: total slack exact **3,897 → 4,098** of 4,559; free slack
exact **1,034 → 1,075** of 1,142, high **69 → 40**, low **39 → 27**.

**Instants lost: three**, all `Hard_File_updated4`'s **UID 305** across that file's three copies — a
completed, zero-duration milestone whose 13:00 instant MS Project spells with the LATER form even
though it is a finish. No rule in the file separates the two spellings: measured over all 941
internal-boundary instants in the corpus, **81 milestones spell a finish EARLIER and 3 spell it
LATER**, while **306 non-milestones spell a start LATER and 81 milestones spell it EARLIER** — the
milestone flag and zero duration each fail as a discriminator in both directions. The dominant
convention is taken per role and those three are a named, unfixed residual rather than a
special case invented to cover them.

## How it was verified

* **Red first on the pristine engine, BY NAME — 5 of 9 red, 4 declared controls green.**
* **Mutation battery 4 of 4 red by name**: the guard removed (only the byte-identical control goes
  red) · the start-role spelling removed (only the block-boundary test) · the projection half
  reverted · the expansion half reverted. The last two also turn
  `test_an_offset_survives_a_trip_through_the_wall_and_back` red — a test green on BOTH the pristine
  and the shipped engine, because each is self-consistent, and red only when HALF the pair moves.
  That is the direct guard against ADR-0322's two-ruler hazard.
* The population control is not vacuous: a plain `*.xml` glob sees **4** of the 15 goldens because
  **11 are gzipped**, and the first cut of the goldens test failed on its own population assertion
  rather than its pin.

## Pins moved deliberately, each with its reason and prior value

* `tests/engine/test_free_float_bounded_by_total.py::test_the_total_float_is_untouched_by_this_change`
  — `(4559, 3897)` → `(4559, 4098)`. Its subject is ADR-0522's bound, which still never writes the
  total; the total moves here because the AXIS moved, and it moves **toward** MS Project by 201
  figures. The docstring is amended to say which change is being controlled for.
* `tests/engine/test_free_float_bounded_by_total.py::test_the_goldens_reproduce_the_stored_free_slack_at_the_pinned_rate`
  — `(1142, 1034, 69, 39)` → `(1142, 1075, 40, 27)`.
* `tests/parity/test_hard_file_stored_dates_oracle.py` — the two crew-calendar parameterisations and
  the out-of-sequence test.

## Deliberately NOT done

The three UID 305 instants (no rule in the file separates the boundary spellings; measured, not
assumed) · the **±1-minute** residual class (828 instants, MS Project stores sub-minute boundaries —
R-65's family, unchanged by this and not a gap error) · collapsing `_stored_instant_offset` into
`datetime_to_offset` now that they compute the same thing (they are the same function but not the
same CONTRACT — the former is only ever a floor under `max()`; a merge is a separate decision) ·
`_recorded_span`'s already-segment-aware reading · R-77's own 212 and 25 as reproducible figures.
