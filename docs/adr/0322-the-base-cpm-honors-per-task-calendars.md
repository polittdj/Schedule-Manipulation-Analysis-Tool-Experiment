# 0322 — The base CPM honors per-task calendars, and a violated pin reports its violation (OR-05)

Date: 2026-07-31
Status: accepted

## Context

Operator-directed engine-correctness deep dive (OR-05). Two MS Project files built by the
operator's SME with KNOWN scheduling traps — `Jacked Up Schedule 1.mpp` and
`Jacked up Schedule 2.mpp` — are committed under `00_REFERENCE_INTAKE/mpp/` beside the
6-slide `Politte Schedule Tool.pptx` that explains them. The PowerPoint plus MS Project's
own STORED values (slack stored in tenths of a minute) are the oracle; the tool was known
to be wrong on these files.

Measured variances on the pre-change engine (single project calendar, ADR-0028):

- **Jacked 1** (Standard calendar with the ENTIRE September 2026 non-working): the
  120-hour task on the **"24 Hours" calendar** was burned as fifteen 8-hour project days
  across the void → computed project finish **2026-10-28 vs MS Project 2026-10-07**, the
  task wrongly ON the critical path with TF 0 vs stored 36 900 min (76.88 d), and every
  downstream float inflated (23 d vs 8 d on the dangling pair, 15/16 d vs 1 d).
- The **eDays task** (DurationFormat 8, PT768H) had correct successor math but its
  cap-space slack collapsed the void: 0 once the finish was fixed, vs stored 3 780 min
  (2.63 edays).
- **Jacked 2**: the violated **Must-Finish-On** milestone (predecessor chain finishes
  08-21 against an MFO of 08-14) recomputed TF 0 vs MS Project's stored **−2 400 min
  (−5 d)** — the es-pin + lf-cap architecture reported a placid zero on the pinned task
  while its predecessor showed −5 d.
- The **dangling pair** (an FF-only predecessor / an SS-only successor) was invisible to
  every logic check (see ADR-0323).
- Deadline handling was already correct end-to-end (importer + backward cap) — the
  committed Jacked 2 file itself does NOT carry the slide's deadline: MPXJ provably reads
  MPP14 deadlines (Hard_File UID 155, Large-Test UID 157), reads none here, and the
  file's last save (09:23 EDT) predates the PowerPoint's final edit (10:29 EDT) — the
  deadline was added in the live MS Project session after the last save. Documented as a
  file-vs-slide divergence, not "fixed" toward an unreachable number; re-saving the .mpp
  with the deadline will flow through the existing pipeline (pinned by a new test).

ADR-0240 protocol: a three-lens adversarial design review (MS Project semantics / engine
architecture / parity blast radius) ran BEFORE implementation; every blocker it raised is
resolved in the shipped design below, and its parity-adjudication split (which pins may
move toward the reference vs which must not move at all) was followed.

## Decision

**1. Per-task execution calendars in the base CPM.** Every active task resolves an
*execution calendar*: elapsed durations → a synthetic 24/7 calendar (1 440 min/day, the
former special-case generalized); a `calendar_uid` whose working pattern MATERIALLY
differs from the project calendar (same `_working_pattern_key` the disclosure already
used) → that calendar; everything else → the project calendar on the untouched integer
fast path. For an off-calendar task:

- The **canonical axis stays integer working minutes on the project calendar**; the
  task's true instants ride on new optional `TaskTiming.*_wall` fields (and
  `CPMResult.project_finish_wall`), because the axis cannot represent a date inside a
  project-calendar void.
- Forward: predecessor anchors are recovered as **wall instants** (finish-role /
  start-role, segment-aware — an exact-multiple offset is END of the previous working
  day for a finish and START of the next for a start) and propagated **directly between
  off-calendar tasks** (never round-tripped through the lossy axis). Constraint floors,
  MSO/MFO pins, ADR-0034 stored-date pins/floors, and ADR-0309 resume floors all use
  their RAW stored datetimes on this path.
- Backward: the target is a **wall instant** (max true early-finish wall — this is what
  keeps QC-audit-D2's "no fabricated negative float on a weekend-finishing elapsed task"
  true), successor needs are wall instants, and **total/free float are working minutes
  of the TASK'S OWN calendar** between its instants — exactly MS Project's stored Total
  Slack basis (display still divides by the project's minutes-per-day, matching MSP).
- Cross-calendar link **lag** stays on the project axis — a documented approximation
  (both oracles carry only zero lags; MSP's lag calendar is unpinned until an oracle
  exists). Shared helpers (`datetime_to_offset`, `offset_to_datetime`,
  `_count_working_days`…) are byte-untouched; all new machinery is additive and runs
  only for off-calendar tasks (fast-path purity pinned by a sentinel test).

**2. A violated pin reports its violation.** For MSO/MFO tasks the engine keeps the
logic-only early start it already computed and sets
`total_float = min(backward_float, pin − logic_es)` — on the task's own float axis. A
violated pin now carries MS Project's negative slack (Jacked 2 UID 30: exactly −2 400);
an unviolated pin is unchanged. Dates stay pinned; `is_critical` stays `total_float <= 0`.
The engine models MSP's "honor constraint dates" mode unconditionally (HonorConstraints=0
projects are out of scope, documented).

**3. DCMA-12 injects on the execution calendar** (generalizing the QC-D3 elapsed fix):
the 100-day probe delay and its expected finish movement are computed on the tested
activity's own calendar via the new wall helpers.

## Verification

- `tests/engine/test_multicalendar_cpm.py` (17 tests) pins the full oracle: finish dates
  10-07/10-09, the complete per-task float table in exact minutes (36 900 / 3 780 /
  3 840 / 480 / −2 400 / 6 240), critical sets, wall instants through the void
  (08-31 17:00 → 09-05 17:00; 08-27 17:00 → 09-28 17:00), free floats, stored-vs-
  recomputed equality sweeps on BOTH files, null-row exclusion, the deadline pipeline,
  off-calendar chaining, offset-0 start-role, and the fast-path sentinel. Proved able to
  fail: 14 of the original 19 failed on the pre-change engine with exactly the oracle
  variances.
- Deliberate re-baselines, each via its own pin with the oracle as evidence: the QC-D2
  elapsed-chain pin `{1: 0} → {1: 1440}` (Jacked 1's eDays task stores 3 780 for the
  same finish-in-nonworking-time shape — the cap-space 0 under-measured real slack), and
  TP3 ribbon `negative_float 3 → 4` (the violated MFO UID 41; the workbook's 3 was
  captured against a TP3 artifact whose finish differs from the committed fixture by
  5 days per FUSE-VALIDATION.md's own "to reconcile" row).
- Everything the blast-radius review said must NOT move did not move: the full parity
  gate (SSI driving-slack goldens, SRA calibration, Fuse Hard_File, project2_5) and the
  engine suite pass with only the two documented re-pins.

## Residuals (documented, not chased)

- Elapsed-task slack DISPLAYS on the project 480-axis (7.88 d where MSP shows
  2.63 edays); the minutes beneath are now exact and the presentation choice is CC-01's
  rendering-half debt (Phase 3) — metric surfaces keep /480, which is the proven
  Acumen-parity basis on the committed exports.
- A violated MFO whose violation arrives via the ADR-0309 resume floor (EF raised, not
  ES) under-reports the violation term; no oracle exercises it.
- `TaskTiming.late_start/late_finish` integer fields for off-calendar tasks are lossy
  axis projections (the walls are exact); nothing outside `cpm.py` reads them today.
- MSP's lag calendar on cross-calendar links (above) awaits an oracle file.

From the post-implementation adversarial review (find → per-finding executable
refutation → lead re-validation). Every CONFIRMED finding was fixed with a regression
test in the same tree:

- **`datetime(hour=24)` crash** when a working day ends at minute 1440 (a 24-hour
  PROJECT calendar with an off-calendar task) — reproduced, fixed via the `_at_minute`
  midnight+timedelta helper at every wall construction site, pinned by the
  24-hour-project-calendar test.
- **Two-ruler intraday defect** (review overturned the draft design): projecting
  wall→axis with a segment-aware ruler while constraints/rendering measure contiguously
  made one instant carry two offsets — a successor rendered BEFORE its predecessor's
  finish, and a same-instant SNET out-bound the link inside one `max()`. Final rule:
  int→wall EXPANSION stays segment-aware (an end-of-day offset expands to MS Project's
  true 17:00 — the oracle instants), wall→int PROJECTION is the canonical contiguous
  ruler (`_wall_to_offset` ≡ `datetime_to_offset`). Cost: a mid-day wall instant on a
  gapped calendar projects up to the gap width LATER than its true worked minutes (never
  earlier, one boundary per off-calendar link) — conservative and disclosed; the true
  instants ride the walls.
- **DCMA-12 false-FAILed a perfect two-task elapsed chain** (the downstream task's
  weekend collapse shifts the axis delta) — fixed with the wall-axis continuity check:
  when the exact-axis equality misses and finish walls exist, the test passes iff the
  PROJECT finish instant shifted by exactly the tested activity's own wall shift.
- **Dangling checks dropped summary-endpoint links** — a summary link is a real tie
  (ADR-0043 lowering); fixed with active-endpoint filtering and both-direction tests.

Recorded, not chased: a Standard-calendar tested activity with an off-calendar successor
can still miss BOTH DCMA-12 equalities in exotic phase cases (no oracle exercises it);
and an SRA `duration_override` cannot flip a task's elapsed/normal execution-calendar
membership mid-simulation (membership keys on the STORED duration — the pre-existing
elapsed-branch convention, preserved).

## Performance addendum (same PR, post-CI observation)

The first CI run on this change ran 3+ hours: the wall helpers' day-by-day walks (with
O(len(holidays)) tuple membership per step) dominated the SRA Monte-Carlo — 138+
off-calendar tasks x ~2000 solves x month-scale slack spans, multiplied by coverage
tracing. Fixed as a pure lookup/arithmetic change with byte-identical outputs, proven
by a canonical digest over every task's full timing (ints + wall instants) on
Large_Test_File before/after (`e3741aecd11d8dfb` both), plus the whole oracle suite and
parity gate: (1) a memoized per-calendar frozenset index (`_worked_day_sets`; the
`Calendar` model is frozen/hashable) replaces tuple scans; (2) `_shift_worked_days` and
`_wall_minutes_between` use the SAME full-weeks + holiday-adjust arithmetic as the
long-proven `_advance_working_days`/`_count_working_days` (a new `_retreat_working_days`
mirrors the jump backward; calendars WITH `working_days` extras keep the exhaustive
per-day step — extras break the weekly period and are rare). Measured: 836 -> 62
ms/solve on Large_Test_File (off-calendar overhead now at par with the 33 ms fast-path
base); the local parity gate dropped from ~28 minutes to 2m38s (46 passed).
