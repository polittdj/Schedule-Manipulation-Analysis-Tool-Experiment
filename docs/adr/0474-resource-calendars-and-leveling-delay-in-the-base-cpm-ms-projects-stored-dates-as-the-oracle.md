# ADR-0474 — Resource calendars and leveling delay in the base CPM: MS Project's own stored dates as the oracle (R-44)

- **Status:** Accepted — 2026-09-07 (the plan-forward's R-44, the first row of the report's §3 after ADR-0473).
- **Version:** 1.0.244
- **Extends:** ADR-0322 (per-task calendars in the base CPM — the wall machinery this ADR generalises), ADR-0473 (the row it closes), ADR-0391 / ADR-0309 / ADR-0463 (the stored-date reads it keeps), ADR-0118 (the calendar registry), ADR-0151 (the Project2 / Project5 Fuse suite whose two documented divergences it closes).
- **Shipped:** `model/resource.py` (`calendar_uid`), `model/task.py` (`TaskType`, `task_type`, `ignore_resource_calendar`, `leveling_delay_minutes`), `model/calendar.py` (`working_pattern_key`), schema 2.12.0; `importers/mspdi.py` (`Resource/CalendarUID`, `Task/Type`, `IgnoreResourceCalendar`, `LevelingDelay`; the registry carries assigned crews' off-pattern calendars); `importers/json_schedule.py` (round trip); `engine/cpm.py` (execution plans, the slack axis, the finish-role late finish, the successor's delay in the backward pass, `injected_finish_wall`, `CPMResult.leveling_driven`); `engine/metrics/dcma14.py` (the plan-aware injection); `tests/engine/test_resource_calendar_cpm.py` (14), `tests/parity/test_hard_file_stored_dates_oracle.py` (9), `tests/importers/test_mspdi.py` (+2); the re-pins listed below.

## Context

R-44 (ADR-0473): Hard_File's CPM finish read **2026-12-17 where MS Project stores 2026-11-05 — 42
days late** — and the engine agreed with the file's stored Critical flag on 54 of 110 activities. The
row's diagnosis was the crews: `Customer Service Team` works a 16-hour calendar (06:00–12:00 +
13:00–23:00), `Content Developer` and `Logistics` a 24-hour one, and the base CPM (ADR-0322)
honoured a TASK's calendar but never a RESOURCE's. Every MSPDI carries the reference tool's own
computed `Start` / `Finish` / `EarlyStart` / `EarlyFinish` / `LateStart` / `LateFinish` /
`TotalSlack` / `Critical` per activity, so the oracle was in the file all along; a std-lib harness
compared the engine's instants with them on the five Hard_File snapshots, Project2 / Project5, the
Large Test Files and the EVM goldens, before and after every rule.

| Finding | Measured (stored · engine before) | Root cause |
| --- | --- | --- |
| Hard_File's finish | 2026-11-05 12:00 · 2026-12-17 11:00 (+42.0 d); updated +31.2 d, updated2 +34.8 d, updated3 +18.7 d | MS Project schedules an ASSIGNMENT on the resource's calendar: 78 of 87 Hard_File bookings span exactly the task duration on the crew's calendar (82 of 87 share the task's own Start / Finish); only 44 span it on the project calendar |
| twelve activities start hours to weeks after their predecessor | UID 403 starts 2026-09-22 15:00 after 402's 08-27 17:00; 179 / 178 Monday 08:00 / 17:00 after a Friday 17:00 | `<LevelingDelay>`, tenths of a minute, ELAPSED, added after the task's own calendar first admits it: Hard_File 12 / 12, updated 16 / 16, Project2 18 / 18, Project5 16 / 16 explained exactly (the unsnapped base explains fewer) |
| Project2 / Project5 finishes | 2027-09-14 · 2027-08-30 (−15 d); 2028-01-26 · 2028-01-25 | the same leveling delays (21 / 20 leveled activities); the "workbook's Project2 differs (08-30 vs 09-14)" note in FUSE-VALIDATION was this |
| stored Total Slack on a crew-driven task | UID 178: 240 · the crew calendar reads 720 | MS Project measures slack on the TASK's calendar (the project's when it has none) even when the booking runs on the crew's: start slack Mon 17:00 → Tue 13:00 = 240 project minutes, finish slack 480, the stored figure their minimum |
| a predecessor's late finish before a leveled successor | UID 14 LF 10-29 11:00 · UID 141 LS 21:00 (10 h delay); Project2 UID 36 LF Fri 17:00 · UID 37 LS Tue 08:00 (48 h) | the successor's late start less its delay, snapped BACK to a finish instant |
| Large Test File2 fixed-work bookings | 117 bookings with work / units below the duration: 78 span the duration, 0 span work / units | a FIXED_UNITS booking runs work / units (Hard_File UID 200: two 4-hour bookings on an 8-hour task); a fixed-duration / fixed-work booking spans the task with its work contoured over it |

## Decision

1. **Execution plans.** A task that does not run its whole duration on the project calendar's integer
   fast path carries an execution plan: one leg `(calendar, span)` per WORK-resource booking on the
   resource's registered calendar (the project calendar when the resource carries none or a
   same-pattern one), `span = duration × min(1, (work / units) / stored duration)` for a FIXED_UNITS
   task and the full duration otherwise; a task calendar intersects — a 24-hour task calendar yields
   the crew calendar exactly, any other task calendar wins (approximation, R-58). The task starts at the
   earliest leg's first working instant and finishes at the latest leg's finish; the latest-finishing
   ("primary") leg is the retreat axis. A material booking, a zero-work booking, a same-pattern crew
   and `IgnoreResourceCalendar` leave the fast path untouched (pinned). ADR-0322's task-calendar and
   elapsed plans are the one-leg case; the fast path is byte-identical.
2. **Leveling delay** is elapsed time added after the plan first admits the task (then admitted again);
   delayed UniqueIDs ride `CPMResult.leveling_driven` — a stored scheduling input, neither an
   unsupported date nor evidence of work begun. A project-calendar task with a delay gets a one-leg
   plan so the arithmetic runs segment-aware. In the backward pass a successor's late-start NEED is its
   late start less its delay (`ls_need`), on both the wall and the integer paths.
3. **The slack axis is the task's calendar**, never the crew's; the late finish is the tightest need
   snapped back to a FINISH instant on the primary leg (a fast-path successor's need arrives as a
   start-role instant); the late start retreats every leg; total slack is the smaller of the start and
   finish slack on the axis (MS Project's rule, ADR-0463).
4. **The registry** carries the calendars of the crews any task is assigned to, when their pattern
   differs from the project calendar's (`Calendar.working_pattern_key`, moved onto the model so the
   importer and the engine apply one test). Hard_File registers `[1, 3, 6, 8, 10, 12]`; Large Test
   File2 eighteen crew calendars that differ from the project's only by holidays.
5. **DCMA-12** injects its 100-day probe through `injected_finish_wall` — the finish the task's plan
   reaches with the longer duration — so a multi-leg task's expected movement is the plan's, not the
   primary calendar's alone.
6. **Not behind a flag.** The row asked for a flag; the pass is on by default because every parity
   pin that moved, moved onto the reference (below) and the two Large Test Files did not move at all.
   `IgnoreResourceCalendar` is the per-task off switch MS Project itself provides.

## Verification

- **Red first.** `tests/parity/test_hard_file_stored_dates_oracle.py` against a `git archive HEAD src`
  scratch copy on `PYTHONPATH`: 7 failed / 2 passed by name (the two "Large Test Files unmoved" pins
  pass on both, as designed). The synthetic module cannot import on that tree (the fields do not
  exist); on this tree 14 passed, each rule in isolation.
- **After, on the committed fixtures** — finish gap · finishes within a day · Critical flag agreed (of
  110) · stored slack exact: Hard_File −1.0 d · 92 · 108 · 3 / 76 (was +42.0 · — · 54); updated −1.0 d
  · 100 · 110 · 52 / 70 (was +31.2 · 59); updated2 −1.0 d · 87 · 80 · 8 / 76 (was +34.8 · 73); updated3
  −6.0 d · 42 · 96 (was +18.7 · 65). Project2: finish exact (was −15 d), 126 / 126 within a day (was
  66), stored slack 65 / 65 exact (was 7), late finish within an hour 108 / 126 (was 38), Critical
  124 / 126; Project5: exact (was −1 d), 126 / 126, 95 / 95 (was 8), 99 / 126 (was 29), 126 / 126.
  Large Test File / File2: 1 558 / 1 723 and 1 563 / 1 722 within a day, 842 / 1 022 and 655 / 936
  slack-exact — the pre-ADR figures exactly (the type rule restored them: a first cut ran every
  booking at work / units and read 1 520).
- **Re-pins, each toward the reference:** Net Finish Impact −148 → **−134 = Fuse's HSD10** (the CPM
  finishes ARE the stored finishes: the `-148 = -134 - 15 + 1` bridge is now `-134 = -134 - 0 + 0`);
  the SN04 96↔99 membership swap CLOSED (both bases agree once UID 96's 21-day delay is honoured);
  forecast CPM finish 2027-08-30 → 2027-09-14 and 2028-01-25 → 2028-01-26 (the stored finishes; the
  `/api/forecast` and narrative / trend pages follow); float summary 391 → 402 and 497 → 498 working
  days; float bands `float_total_lt10` 46 → 45, `float_free_0` 71 → 68, Project5 `float_free_lt10`
  73 → 69; `test_fuse_reference` pins Project2 at the workbook's 2027-09-14 (a "documented
  difference" since 2026-06, closed). ADR-0322's Jacked-Up oracles, the actual-start, resume-floor,
  DCMA-14, SRA and driving-slack suites: unmoved.
- Statics: ruff (whole tree) · format · mypy --strict 163 files · bandit exit 0. The gate figures are
  in the SESSION-LOG follow-up.

## Deliberately not done — registered as rows

- **R-55 (T1, M) — progress semantics.** updated3's −6 d and updated3_24hr's +17 d are not calendars:
  a started activity is FLOORED at its actual start (ADR-0391) so logic can still push it later
  (updated3's completed UIDs 291–298 land 36 days after their actual finish), and a completed
  milestone's actual instant is snapped to the project calendar. Pinning started work at its actual
  start (measured in a scratch copy) reads updated3 −13 d / updated3_24hr −2 d — a rule for its own
  unit with the SSI goldens as arbiter.
- **R-56 (T1, HELD) — bookings the MSPDI cannot explain:** UID 14 (200 % on a 24-hour task calendar
  with a 16-hour crew) spans 40 h for 24 h; UID 401 56 h for 40 h; UID 403 twelve working days for 4
  days in every snapshot (a contour the XML carries as timephased data only); UID 385 (four bookings,
  two of them material). They are why the three early snapshots read one day early.
- **R-57 (T2, S)** — assignment-level `LevelingDelay` (UID 398's two bookings, UID 188) is not read.
- **R-58 (T2, S)** — the task ∩ crew calendar intersection is approximated (UID 14 on `Standard+Sat.`).
- **R-59 (T3, S)** — `off_project_calendars` and the /analysis disclosure still name task calendars
  only; the crews the engine now honours are undisclosed on the page.
- Late finishes on Hard_File agree within an hour on 64 / 110 — the successors' late chains carry the
  R-56 bookings and the milestone snaps; not chased.
- The XER importer carries no resource calendar (P6 `clndr_id` on `RSRC`); `calendar_uid` stays
  `None` there and the task / project calendar governs, as before.

## Amendment (2026-09-07, later the same day) — the latency follow-up: the wall path must not tax the SRA

**Observed.** #649's `browser (measured-box proof)` job went red on the final head: `/sra: no captions
rendered` in all twelve theme × zoom cells of `tests/web/test_axis_titles_visual.py` (page loaded,
no page errors — the SRA data had not arrived inside the proof's caption wait). Measured on the
committed goldens: `compute_cpm` on Project2 / Project5 1.3 / 1.3 ms → 3.7 / 4.1 ms, and
`GET /api/sra` (the legacy run: 1 000 solves of the selected schedule) 1.58 s → 4.27 s.

**Root cause — per-solve work that depended on the schedule alone, on a solver called a thousand
times per request.** Three mechanisms, each measured by profile: (1) the execution plans were
re-derived from every assignment on every solve (~300 `working_pattern_key` calls per pass — 0.41 ms
of a 3.7 ms solve); (2) the day tests behind every wall helper went through a memo keyed on the
frozen `Calendar` model (`lru_cache`), which paid a full-model `__hash__` + `__eq__` on EVERY lookup
(~1.1 µs, ~400 lookups per solve — 8 607 hashes across 20 solves); (3) the network (the lowered
summary logic, the topological order) and the stored-date bounds (~130 stored-date projections) were
rebuilt per solve — pre-existing cost, but the same class.

**Decision — purely lookup-structure changes, byte-identical by construction and by measurement.**
Everything that is a function of the schedule alone is derived once per schedule OBJECT and found by
identity (`id()` re-checked against a weak reference; a `weakref.finalize` drops the entry with the
object, so nothing outlives the schedule that owns it): a `_Ruler` per `Calendar` (the frozensets,
the segments per day start, and memos of the three day-walking cores — `[d0, d1)` counts, the k-th
working day after / before a day — capped, cleared, never evicted piecemeal), the `_PlanShape` per
task (the legs' calendars and ratios; only the spans scale with a solve's durations), and the
`_Network` per schedule (the scheduled tasks, edges, order, adjacency, stored-start / actual-start
bounds). The backward target's wall instant is derived once per solve instead of per task, and a
one-leg plan skips the generator. The counting loops keep the model's own holiday tuple so even a
duplicated holiday counts exactly as before.

**Measured after:** `compute_cpm` Project2 / Project5 **1.8–2.1 / 1.7–1.8 ms**; `GET /api/sra`
**2.0 s** (was 4.27 s; the pre-ADR tree read 1.58 s). The remaining excess over the pre-ADR tree is
the wall arithmetic of the 21 / 20 leveled activities themselves (~35 µs each) — the fidelity the
ADR bought, not overhead.

**Proof (QC-1).** A std-lib harness dumped EVERY `CPMResult` / `TaskTiming` field (integer offsets,
wall instants, floats, critical flags, the driven lists) for every schedule fixture in the repo (31
files: the goldens, the Hard_File snapshots, the Large Test Files, the test projects, the XER, the
shipped demo) under three solves each (plain, a required finish, every duration halved), the
DCMA-12 injection surface per task, and a fixed-seed legacy SRA on Project2 / Project5 / Hard_File:
7.7 MB BEFORE the change, byte-identical AFTER each of the two rounds. Three deterministic count
gates in `tests/perf/test_perf_regression.py` (in the file's own doctrine — counts, never a
wall-clock threshold): the shapes, the network + stored-date bounds, and the calendar rulers are
derived once per schedule object and never by value. Red first: the pristine engine fails the shapes
and network gates (21 / 21 rebuilds), the ADR-0474 head fails the hash gate (8 607); a targeted
three-mutation scratch copy (each memo disabled) fails all three by name; the real tree passes.
`test_cpm_date_equivalence` (the randomized day-by-day oracle of the date cores), the synthetic
resource-calendar module, the stored-dates oracle and the multi-calendar suite: unmoved.

**Lesson, promoted.** An engine change is priced on the SRA before it ships: `compute_cpm` runs a
thousand times per `/api/sra` request, so a per-solve cost that is a function of the schedule alone
is a bug there whatever it costs once — profile a leveled golden inside the Monte-Carlo, and never
key a hot memo on a frozen pydantic model (its `__hash__` / `__eq__` walk every field on every
lookup; find the object by identity and let a weakref retire the entry).

### The seven floor-job pins (2026-09-07, later still)

The `floor (declared minimum)` job runs the whole suite without coverage and finished where the
`test` jobs were cancelled: seven failures the first cut never saw (its local full suite died at
58 %). Every one reproduces on the tree; every one is this ADR's, and they split into two kinds.

**Six engine-derived pins, each adjudicated before it moved.**

- **The dashboard payload on the Large Test File (`ssi_uid152`, three hashes).** Diffing the
  canonical JSON of both modes across the two engines moves exactly two things: the pure-logic
  `critical_count` **2 → 33**, and DCMA-12 "Critical Path Test" **NA → FAIL** (a critical path now
  exists to test). MS Project's own stored `Critical` flags on that file number **33**; the old
  engine agreed on 2 of them, the new engine on all 33 with none extra. "Unmoved" in this ADR's
  finish-within-a-day measure (1 558 / 1 723) was never "unmoved" — the critical SET was the thing
  that moved, onto the reference, and only the dashboard's byte pin was looking at it. The three
  hashes are re-pinned with that adjudication written beside them.
- **The 188→187 counterfactual on Hard_File (three assertions).** Restoring the removed FS link on
  the updated snapshot and re-solving now moves UID 155 **+12 wd** (was +15; +23 and +21 before
  ADR-0391 / ADR-0322). An engine-derived counterfactual moves with the base CPM by design: the
  restored link now pushes the target through a path that already carries the crew-calendar
  bookings and stored leveling delays MS Project applied (the snapshot's finishes sit within a
  day of MS Project's on 100 of 110 activities). Old value reproduced on the pristine engine, new
  value stable across two processes; the test's point — a NON-ZERO effect the AI cannot round
  to "no effect" — is unchanged.

**One product defect, fixed.** The Driving Path page's `ignore_leveling` option promises a
"0-day leveling delay" re-solve. Before this ADR the engine had no leveling delay, so clearing
incomplete tasks' stored dates WAS that re-solve; once the base CPM honoured
`leveling_delay_minutes`, clearing the dates left the delay inside the "pure-logic" network and
the toggle went nearly inert — a census of every target on both goldens found **2 of Project5's
and 0 of Project2's** driving tiers diverging under the flags, where the contract test records
**33 / 39** before the ADR. `_optioned_versions` now also zeroes `leveling_delay_minutes` on
incomplete tasks under the option: **50 / 56** targets diverge, the test's UID 70 among them and
its UID 67 anchor still anchored. The SSI-parity family (`/api/driving`) keeps the stored-date
trace and is unchanged, as ADR-0251 documents. Lesson: an option that EMULATED a feature goes
inert the day the engine implements it — re-read every toggle named after the thing you just
built.
