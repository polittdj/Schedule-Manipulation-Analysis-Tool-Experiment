# ADR-0503 — A task calendar meets a crew calendar on their INTERSECTION: R-58's witness was UID 94, not UID 14, and the one activity in the corpus whose crew cuts into its calendar lands on MS Project's five stored values (R-58 CLOSED)

- **Status:** Accepted — 2026-09-17 (the plan-forward's R-58, the report's §3 row after R-57 / ADR-0502).
- **Version:** **1.0.269** (`src/` changed: `engine/cpm.py` only — the plan builder's leg calendar, `booking_calendar`, and the helper that computes the intersection; no model, importer or schema change). Wheel and the nine installers rebuilt in lockstep.
- **Extends:** **ADR-0474** (the "any other task calendar wins" approximation this replaces; the task-calendar slack axis it keeps), **ADR-0492** (`booking_calendar` — the plan builder's rule stated once for the planned-value proration, now the same intersection), ADR-0476 (why the three recorded-complete snapshots of the witness adjudicate nothing), ADR-0487 (a MATERIAL / COST leg keeps the task calendar), ADR-0491 (the split gaps, now measured on the intersection where one exists), **ADR-0500 / ADR-0501** (the census discipline — a residual names its population, the `.mpp` corpus is twice the goldens), ADR-0502 (the sibling calendar quantities on a leg).
- **Shipped:** `_calendar_intersection` (identity-memoized like `_ruler`), `_intersect_calendars`, `_restricts`, `_blocks_intersection`, `_merged_blocks`, the leg-calendar rule in `_task_shape`, the same rule in `booking_calendar`; `tests/engine/test_calendar_intersection.py` (11 pins), `tests/parity/test_r58_calendar_intersection_oracle.py` (20 pins); `tests/engine/test_booking_calendar.py` re-pinned (dated); the module and builder docstrings; the closed R-58 row and the new **R-67** row.

## Context — what the row said, and the two things measurement changed about it

R-58 read: *a task calendar that is not 24-hour, intersected with a crew calendar, is approximated
by the task calendar (Hard_File UID 14 on ``Standard+Sat.`` with the 16-hour crew) (ADR-0474)*,
with the first step *a calendar-intersection helper (weekdays ∩, segments pairwise ∩, holidays ∪)
behind the plan builder; pin UID 14's stored span* and the oracle *the stored dates of a task
with both calendars*.

The mechanism is MS Project's own: a WORK booking is scheduled in the times that are working on
BOTH the task's calendar and the resource's, unless the task ignores resource calendars.
ADR-0474 modelled one case of it exactly — a 24-hour task calendar yields the crew's — and
approximated every other by the task calendar alone. Two things about the row were measured
before anything changed.

**The row's witness is mis-stated.** Read off the XML rather than the register, Hard_File UID 14
carries **calendar 10, `24 Hours`**, in all seven snapshots — the case the engine already had
exactly, which is why ADR-0491 found its stored span (10-26 20:00 → 10-29 11:00) reproduced to the
minute and the kickoff warned that it "already spans its stored dates". The task on
`Standard+Sat.` (calendar 12: 07:00-12:00, 12:30-19:00, 19:30-23:30, Monday to Saturday, 930
minutes) is **UID 94**, *Determine solutions for product points*, an 8-hour FIXED_UNITS activity
booked on the same crew (resource 1, calendar 3: 06:00-12:00 + 13:00-23:00, Monday to Friday).
The row conflated the two activities' calendars. ADR-0500's lesson applied to a witness rather
than a rule: a row's named activity is testimony about the file until the file is read.

**The population is one task.** Censused on the engine's own `_task_shape` (never a
re-implementation — the R-61 lesson), the 15 goldens carry **301** active tasks with an
off-pattern task calendar and a WORK booking: **294** on a calendar that is not 24-hour — 293 of
them Large Test File activities on the `ZIN Project Calendar` under same-pattern crews, whose
crews restrict nothing the task calendar works — and UID 14's seven on `24 Hours`. Exactly
**one** task's crew calendar cuts into its own: **UID 94, in five snapshots** (Hard_File,
updated, updated2, updated3 and the SSI copy of updated3; on the two `24h` snapshots the crew is
round-the-clock and restricts nothing). Three of the five are recorded-complete — pinned at their
record by ADR-0476, they adjudicate no scheduling rule (ADR-0501's correction) — so the oracle
has **two** unstarted witnesses. Over the repository's **29 `.mpp` files** (all converted; the
`Large Test File.mpp` / `Large_Test_File.mpp` name collision ADR-0501 warned about bit the first
conversion loop and was caught by counting artefacts, 28 ≠ 29) the population is the same task in
one more save, `Hard_File_updated_with_logic_reestablished`.

**What was wrong, on the pristine engine (ADR-0502's tree, measured in a separate worktree):**

| | stored (MS Project) | engine, task calendar alone |
| --- | --- | --- |
| UID 94 finish, Hard_File | 2026-07-23 **17:00** | 16:30 — the task calendar resumes at 12:30 |
| UID 94 finish, updated | 2026-08-12 **17:00** | 16:30 |
| UID 94 late finish, updated | **Friday** 08-14 23:00 | **Saturday** 08-15 23:30 — a day the crew never works |
| UID 94 late start, updated | 08-14 14:30 | 08-15 15:00 |
| UID 94 total slack, updated | **2,190** | 3,180 |
| UID 157 (its successor) start / finish | 17:00 / 08:00 | 16:30 / 07:30 on both snapshots |

The late finish is the decisive one: 157's stored late start less its 6,660-minute elapsed
leveling delay lands on Sunday 08-16 00:00, and snapped back to a finish instant on
`Standard+Sat.` that is Saturday 23:30 — on the intersection it is the stored Friday 23:00.

## Decision — the leg calendar is the intersection

`_task_shape` runs a WORK booking's leg on **`_calendar_intersection(task calendar, crew
calendar)`** whenever the task carries a calendar of its own that is not the project pattern AND
the crew names a calendar in the file. `booking_calendar` (ADR-0492's public statement of the
same rule, the planned-value proration's ruler) returns the same object.

| rule | what it does | pinned by |
| --- | --- | --- |
| weekdays intersect | a Saturday only the task calendar works is not worked | the synthetic Saturday; updated's Friday late finish |
| intraday blocks intersect pairwise (merged) | 12:30-19:00 ∩ 13:00-23:00 = 13:00-19:00 — the common afternoon begins at 13:00 | UID 94's 17:00 on both snapshots |
| a holiday of either is a holiday | the crew's Tuesday off is the leg's | the synthetic holiday, both directions |
| an extra working day survives only when both work it | the task's worked Saturday needs the crew to work it too | the synthetic extra, both directions |
| a calendar the other restricts nothing of stands for the intersection **by identity** | a 24-hour task calendar → the crew's object (ADR-0474's case, UID 14, unchanged by construction); a task calendar inside a 24-hour crew → its own; core hours inside the project pattern → their own | `is` pins in both modules |
| WORK crews that name a calendar only | a MATERIAL / COST booking has no calendar to intersect with (its leg is its recorded window on the task calendar, ADR-0487); a crew the file names no calendar for (an XER, an older Save) has an UNKNOWN one — the task calendar governs as ADR-0474 had it | the synthetic material / unknown-crew pins |
| disjoint calendars fall back to the task calendar | MS Project refuses to schedule such a booking; the engine keeps ADR-0474's reading rather than invent a calendar — **UNVERIFIED**, no witness | the synthetic night-shift-under-a-day-crew pin |
| the slack axis stays the TASK calendar | ADR-0474's rule, confirmed again: UID 94's 6,360 (base) and 2,190 (updated) are working minutes of `Standard+Sat.`, the smaller of its start and finish slack there | the axis pin; the parity five-value pin |
| the late finish snaps back on the primary leg's calendar — now the intersection | a need inside the weekend lands on the Friday the crew works to | the synthetic Saturday snap-back; updated's late finish |

The derived calendar carries every intraday block explicitly (a single common block would
otherwise be re-anchored at the project's day start by the ruler's single-block fallback), the
task calendar's duration-scale settings, uid **−2** and both names. It is memoized per (task
calendar, crew calendar) OBJECT pair and day start — found by identity, retired with either
object by a `weakref.finalize`, never hashed (the ADR-0474 perf gates are unmoved), never stored,
never in `Schedule.calendars`. `_task_shape` is derived once per schedule object, so the
intersection is too.

## What it measured — every golden, before and after

The pristine baseline was taken in a **separate worktree at `origin/main`**, the candidate in the
working tree, both with one instrument (a per-task dump of every timing, diffed).

| golden | exact finishes | exact stored slack | activities moved (toward / away) |
| --- | --- | --- | --- |
| **Hard_File** | 38 → **40** (94, 157) | 37 → **39** (95, 412) | 6 / 0 |
| **Hard_File_updated** | 106 → **108** (94, 157) | 99 → **101** (94, 157) | 6 / 0 |
| the other 13 goldens | unmoved | unmoved | **byte-identical** — every timing, every disclosure list, every project finish |

Twelve activities moved across the two snapshots: 94 and 157 onto MS Project's instants, and
95 / 96 / 97 / 412 (the chain upstream of 94, on the project calendar) by the 30 minutes of late
window that 94's later finish hands back — two of them (95, 412) onto their stored 2,880. Project
finishes unmoved; `date_driven`, `leveling_driven`, `booking_span_driven`, `split_driven` and
`assignment_leveling_driven` unmoved on every golden.

**On `updated`, UID 94 reproduces all five stored values** — Start 08-12 08:00, Finish 17:00,
LateStart 08-14 14:30, LateFinish 08-14 23:00, TotalSlack 2,190 — and 157 lands exact with it
(TotalSlack 1,440). **On the base snapshot UID 94's finish is exact and its slack reads 6,510
against 6,360; the 150 minutes are not this rule's.** 157's late finish is read from milestone
147's late start, which MS Project keeps at **Saturday 2026-08-01 13:00** — an instant on the
elapsed axis inside the weekend, the minimum over its leveled successors' late starts less their
elapsed delays (ADR-0476's day-boundary class) — and snapped back on the crew's 16-hour
calendar that instant IS 157's stored Friday 23:00: ADR-0474's backward arithmetic is exact when
fed it. The engine's integer axis has no Saturday instant, so 147 reads Monday 08:00, 157's late
finish follows it two hours later on the crew's axis, and 94's late window is 150 minutes of
`Standard+Sat.` later. Registered as **R-67**, computed in the oracle (if 147 moves, the pin
fails and the residual is re-read).

**The 29-file `.mpp` corpus** (ADR-0501's population): **26 files byte-identical**; the three
that move are the three Hard_File saves carrying UID 94 — 18 task-moves, every finish move toward
the stored instant, none away, project finishes unmoved. On
`Hard_File_updated_with_logic_reestablished` the finish lands on the stored 17:00 while its slack
reads −7,440 against a stored 0 (was −7,410). That save disagrees with MS Project wholesale, before
and after this unit and for reasons this unit does not touch: 85 of its 110 activities read
negative float where the engine reproduces 0 of its 103 stored slacks, 18 finishes sit within a
day and the project finish reads three days late — pristine and candidate identical on every one
of those counts. It is not a golden and no row covers it; the 30 minutes are the same mechanism as
the finish; named, not chased.

## How it was verified

* **Red before green, in the pristine worktree.** The synthetic module cannot import
  (`_calendar_intersection` does not exist); the parity oracle fails **10 of 20 by name** — the
  witness's derived calendar, both 17:00 finishes, the five-value pin, both 157 pins, the residual
  pin, the population pin, both floors — and the re-pinned `booking_calendar` case fails. The 10
  that pass on the pristine tree are the seven UID 14 pins (what was already exact) and the three
  completed-snapshot pins (ADR-0476's record) and are meant to.
* **The rig was refuted twice before the engine was.** The first residual pin asserted the 150
  minutes as the FINISH-slack gap (it is the START-slack gap; the finish-slack gap is 120, and both
  are now computed and pinned), and the first population pin claimed 301 non-24-hour tasks (301 is
  the off-pattern count; 294 are non-24-hour and 7 are UID 14 on `24 Hours`). Both expectations
  were recomputed from the rig's own numbers, not the engine's.
* **Mutation battery** 13 cuts on a shadow copy of `src/` (a `-p mutcheck` plugin asserts the engine measured IS the copy; `cpm.py`'s checksum changed under every cut; the control run green, 50 passed, before and after): M01 the old rule, the task calendar wins → 19 red · M02 blocks not intersected → 16 · M03 weekdays not intersected → 6 · M04 holidays not unioned → 2 · M05 extras from the task alone → 1 · M06 no identity shortcuts → 2 · M06b the general path never returning the crew → 1 · M07 material / unknown crews intersected too → 1 · M08 `booking_calendar` on the old rule → 3 · M09 the memo never consulted → 1 · M10 the late finish snapped back on the task calendar (pre-existing code) → 6 · M11 the empty-intersection fallback returning the crew → 1 · M12 the plan builder never intersecting → 19. **13 / 13 red by name. M06b SURVIVED the first pass** — the identity shortcut for a task calendar that CONTAINS the crew's pattern (a Mon–Sat task calendar over a crew on the project's Mon–Fri) had no pin; it is not dead code and its effect is real (the leg is the crew's real calendar object, the thing R-59's disclosure will name) — killed by a pin naming that case, and the whole battery re-run.
* **The perf gates are unmoved:** shapes derived once per schedule object, zero `Calendar`
  hashes across 20 solves, the network built once.
* Statics green on **both** ruff binaries (0.15.8 and 0.16.8), `ruff format`, `mypy --strict`,
  `bandit` (exit 0), `node --check`.
* **Gate on the final tree:** the full suite (5,546 collected = the previous 5,515 + this unit's 31; `-m parity` collects 170 = 150 + 20, attributed by `--collect-only`) was still running at the first push, 2,627 verdicts in with 0 failures — its figures are recorded in the follow-up docs-only commit

## Deliberately NOT done — registered, or named

* **R-67** (new row, T2): a fast-path milestone's late start that MS Project keeps on the elapsed
  axis inside a weekend (Hard_File base UID 147: Saturday 13:00) is projected onto the integer
  axis, so its 16-hour-crew predecessor 157 reads its late finish two hours late and UID 94's
  slack inherits 150 minutes. First step: carry a leveled successor's late-start need to a
  fast-path predecessor as a wall instant and re-measure 157's stored Friday 23:00 and 94's 6,360.
* **The empty-intersection fallback** (a booking whose two calendars share no working time) keeps
  the task calendar and is UNVERIFIED against MS Project — no witness in the goldens or the 29
  `.mpp` files. A file carrying one is the signal to measure it.
* **An exception day's own working times.** The model records a DayWorking exception as a date
  only (its hours follow the calendar's blocks); the intersection inherits that. Not this row's.
* **A crew the file names no calendar for** (every XER resource) is not intersected: the crew's
  calendar is unknown, and intersecting with the project calendar would narrow a night-shift task
  on the strength of nothing the file says. Documented in the rule, pinned.
* **R-59** is next and unchanged by this: the derived calendar is never listed on `/analysis`; the
  page still names task calendars only.
* **Refused, and named:** intersecting a MATERIAL / COST leg (a material resource has no
  calendar; ADR-0487's window rule stands) · re-anchoring the slack axis on the intersection
  (refuted by UID 94's own stored 6,360 / 2,190, both on the task calendar) · a `CPMResult`
  disclosure for the intersection (it is a calendar rule, not a stored scheduling input; the
  disclosures name inputs) · registering the derived calendar in `Schedule.calendars` (derived
  data; the registry is what the pages list and the Save writes).
