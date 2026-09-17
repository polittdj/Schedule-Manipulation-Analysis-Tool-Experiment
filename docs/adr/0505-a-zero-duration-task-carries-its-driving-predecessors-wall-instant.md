# ADR-0505 — A zero-duration task carries its driving predecessor's wall instant: the project axis cannot tell Friday 17:00 from Monday 08:00, and a crew successor read from that minute's rendering started fifteen hours early (R-64 CLOSED with its mechanism corrected; R-66 CLOSED with it)

- **Status:** Accepted — 2026-09-17 (the plan-forward's R-64, the report's §3 row after R-59 / ADR-0504; R-66 falls with it).
- **Version:** **1.0.271** (`src/` changed: `engine/cpm.py`'s forward pass carries a wall instant on project-axis zero-duration tasks and exposes it on `TaskTiming.early_start_wall` / `early_finish_wall`; no model, importer, schema, web or metric-formula change). Wheel and the nine installers rebuilt in lockstep.
- **Extends:** **ADR-0474** (the crews' calendars in the base pass — the instants this ADR stops losing), **ADR-0322** (the two-ruler rule: int→wall expansion is segment-aware, wall→int projection contiguous — the rule that made one project-axis minute stand for two instants), ADR-0491 (which registered R-64 and named the wrong mechanism), ADR-0502 (which registered R-66 and measured 381 / 396 / 398's 240 minutes), ADR-0476 (the day-boundary milestone class it named).
- **Shipped:** the carry (`engine/cpm.py`: `ms_wall`, `_carried_instant`, carried-aware `_pred_finish_wall` / `_pred_start_wall` / `_succ_early_start_wall` / `_succ_early_finish_wall`, the finish instant); `tests/engine/test_milestone_carried_instant.py` (17 pins, 12 red on the pristine engine by name, 5 controls named as such); the stored-dates oracle re-pinned (`tests/parity/test_hard_file_stored_dates_oracle.py`: every Hard_File floor raised, a stored-slack floor added, the 24-hour snapshot given its own row, the chain's dated pins, the wrong mechanism replaced by the measured one); the R-57 oracle re-pinned (`tests/parity/test_r57_assignment_leveling_delay_oracle.py`: 381 / 396 / 398 exact — R-66); `tests/importers/test_mspdi_zero_slack_inference.py`'s Hard_File witness rewritten (its 480 / 360 were this chain's artefact); `tests/web/test_ch01_critical_basis.py`'s "not pure logic" witness moved to the progressed updated3 snapshot (on the base snapshot the two bases now coincide, 110 of 110 — pinned as the agreement it is); the report's R-64 and R-66 rows closed and R-67 annotated as the backward mirror; `docs/PARITY-REPORT.md`'s stored-dates table re-measured.

## Context — what the row said, and what the file says

R-64 read: *Hard_File's milestone 387 ("Business Performance Planning") hangs on an external
predecessor link (`PredecessorUID` −65535) the MSPDI cannot resolve, so it sits one working day early
(08-17 16:00 vs the stored 08-18 17:00) and the chain 400 → 399 → 401 → 402 → 403 → 404 inherits the
day* — first step *read the link's `CrossProject` / external-task fields if the MSPDI carries them,
else treat a milestone whose only predecessor is external as stored-date driven and disclose it*.
ADR-0491's text, the stored-dates oracle's comments and the kickoff prompt all repeated it.

**The mechanism was refuted before a line changed — by the activity's own XML, the R-58 lesson.**
UID 387's one `PredecessorLink` is UID 386 (`Type` 1, `LinkLag` 0, `CrossProject` 0), in every one of
the five Hard_File goldens. Censused over the whole corpus, every `PredecessorLink` of every file:

| population | files | links | unresolvable endpoint | `CrossProject=1` | `ExternalTask=1` rows | negative UIDs |
| --- | --- | --- | --- | --- | --- | --- |
| the 15 MSPDI goldens | 15 | 11,979 | **0** | 0 | 0 | 0 |
| the 29 intake `.mpp` files, converted fresh by the vendored MPXJ | 29 | 21,609 | **0** | 0 | 0 | 0 |

The only −65535 in Hard_File is a `ResourceUID`: MS Project's *unassigned-work placeholder*, on 27
assignments — one of them (assignment UID 249) on milestone 387 itself, another on milestone 184.
ADR-0278 had already named that placeholder in 2026-07; the row read an assignment as a link.

**The arithmetic was right and the head was nine links higher.** Walking the engine's own network
upstream from 404 against the stored dates (the plan printed, sorted, every leg's finish — the
2026-09-16 lesson), the first activity to disagree with MS Project is not 387 but **milestone 181**,
six links above 384 and fifteen above 404:

| UID | activity | runs on | stored (MS Project) | engine, pre-ADR-0505 | engine, this tree |
| --- | --- | --- | --- | --- | --- |
| 178 | On-site support | the 16-hour crew, 72 h of leveling delay | 08-03 17:00 → **08-04 08:00** | exact | exact |
| 181 | Design of customer service contact scenarios COMPLETE | a milestone on the project axis | **08-04 08:00** | rendered **08-03 17:00** | carried 08-04 08:00 |
| 189 | Identify types of problems to be solved | the 16-hour crew | 08-04 08:00 → 17:00 | 08-03 **17:00** → 08-04 08:00 (−15 h / −9 h) | exact |
| 188 | Identify service delivery options | the crew | 08-04 17:00 → 08-05 08:00 | 08-04 08:00 → 17:00 | exact |
| 187 | Determine required skill sets (120 h) | the crew | 08-05 08:00 → **08-14 17:00** | 08-04 17:00 → **08-14 08:00** (−9 h) | exact |
| 184, 148 | two milestones | the project axis | 08-14 17:00 | 08-13 17:00 (−24 h) | exact |
| 384 | Determine business objectives of support services | the Standard calendar | **Monday 08-17** 08:00 → 17:00 | **Friday 08-14** 08:00 → 17:00 | exact |
| 385, 386, 387, 400, 399, 401, 402 | the crew's chain, 401 with ADR-0491's split | | | one working day early, every one | exact |
| 403 | Acquire executive sign-off (25 d 7 h delay, a split) | the crew | 09-22 15:00 → 10-08 15:00 | 09-21 15:00 → 10-07 15:00 | exact |
| 404 | Customer Service Program Development COMPLETE | a milestone | 10-08 15:00 | 10-07 16:00 | exact (slack 9,420 vs 9,480 — R-67's family) |

The 16-hour crew (06:00–12:00 + 13:00–23:00) ends UID 178 at Tuesday 08:00. Milestone 181 is stored
there — MS Project neither snaps a milestone to its calendar nor rounds it to the day (updated2's 387
is stored at **23:00** on the Standard calendar; the 24-hour snapshot's 156 on a **Sunday** 17:00). The
engine's project axis is integer working minutes of the project calendar, on which Monday 17:00 and
Tuesday 08:00 are ONE minute; a project-axis milestone kept only the minute, and `_pred_finish_wall`
handed the crew successor that minute's *finish-role* rendering, Monday 17:00 — an instant the crew
works. 189 ran its evening shift a day early; 187 finished nine hours short; nine crew-hours before
08-14 17:00 is Friday morning on the Standard calendar, so 184 → 148 handed UID 384 a Friday instead
of the stored Monday, and every activity below inherited the working day. The same handoff appears
three more times on the same file — 216 → 241, 381 → 396 (**R-66**, registered by ADR-0502 as a
"snapshot-specific defect upstream of leveling": it was this) and 387 → 400 — and is a class, not a
file: censused on the engine's own plans over the 44 files, **2,056** zero-duration project-axis
tasks, **230** driven by a crew-calendar activity, **111** of those rendered off their stored instant,
**22** crew successors started on a wrong one.

## Decision

**A zero-duration project-axis task carries the wall instant of its driver, and a wall-path successor
starts from it.** In the forward pass, once the integer pass has placed a zero-duration task (`ef ==
es`), `_carried_instant` collects the instants of every driver of its early start — a lag-0 link's
endpoint (a wall-path predecessor's `ef_wall` / `es_wall`, another carried milestone's instant, or a
project-calendar activity's finish rendering), a raw SNET / FNET / MSO / MFO date, a manual task's
stored start, a recorded actual start — and the latest wins, MS Project's `max` over instants. The
integer offsets are untouched: every candidate projects back to the minute the integer pass chose or
IS that minute's rendering, so nothing about the axis moves and every project-calendar successor is
byte-identical. Nothing is carried unless some driver's instant is one the axis LOST (a wall-path or
carried predecessor): a milestone among project-calendar activities only is untouched, a lagged
driver leaves the rendering in charge (a lag is a quantity of the integer axis), and a
single-calendar file cannot be touched at all. The instant rides `TaskTiming.early_start_wall` /
`early_finish_wall` (the milestone's float stays the axis's; its late walls stay `None`), feeds
`_pred_finish_wall` / `_pred_start_wall` (the successor's start), `_succ_early_start_wall` /
`_succ_early_finish_wall` (a wall-path predecessor's free float — zero into a milestone that sits on
its finish, not the two hours to the next rendering) and the network's finish instant (an SNET
milestone tying a crew's 23:00 ends the project at its own 08:00).

**Two lines were deleted before they shipped.** A projection guard (`_wall_to_offset(carried) == es`,
else abstain) was proved inert — every candidate satisfies it by construction, and the one that can
differ (a project-calendar activity's mid-day rendering) is the rendering the successor would read
anyway — and a stored-start FLOOR candidate can never fire: the floor exists only for a task without
predecessors (`_stored_date_bounds`), and a carried milestone has one. A line that cannot fire is
deleted, not kept as comfort (ADR-0502's lesson).

## What it measured

**The per-task census, pristine tree → this tree, every golden and every conversion** (the finish
instant against the stored Finish; the oracle's own `_census` for the goldens' floors):

| golden | finishes within a day | exact finishes | stored slack exact | Critical agreed | project finish |
| --- | --- | --- | --- | --- | --- |
| **Hard_File** | 103 → **110 of 110** | 40 → **110** | 39 → **101** of 110 | 108 → **110** | exact, unchanged |
| Hard_File_updated | 108 → **110** | 108 → 110 | 101 of 103 | 110 | exact |
| Hard_File_updated2 | 109 → **110** | 106 → 109 | 36 of 76 | 107 | exact |
| Hard_File_updated3 | 106 → **110** | 101 → 110 | 46 of 68 | 103 | exact |
| Hard_File_updated3_24hr (now its own oracle row) | 100 → 109 | 92 → 104 | 4 → **7** of 19 (407's 1,920; 411 / 155's −4,320) | 70 | 11-17 01:00 → **11-19 01:00, the stored, EXACT** |
| Project2 / Project5 | 126 / 126, unmoved | unmoved | 106 / 99, unmoved | 124 / 126 | exact, unchanged |
| Large_Test_File / File2 / Leveled / the SSI copies | 1,666 / 1,687 / 1,645, unmoved | unmoved but two milestones (below) | 867 / 730 / 789, unmoved | unmoved | unchanged |
| EVM1 / EVM2 | unmoved | EVM2 UID 25's START is now the stored 09-21 17:00 (its finish, stored a day later, unchanged) | unmoved | unmoved | unchanged |

Across the 44 files (15 goldens + 29 conversions, 22,050 scheduled activities): **220 finishes moved
toward the stored instant, 41 away, 21,789 unmoved**; exact finishes 19,791 → 20,011; within a day
21,343 → 21,387; stored slack exact 10,666 → 10,800; Critical agreement 21,873 → 21,877; late dates
moved on 30 rows (ten on each copy of the 24-hour snapshot, whose backward target moved to the now
exact finish — UID 407's stored slack 1,920 and 411 / 155's −4,320 became exact with it).

**The 41 "away" are two named mechanisms, neither this rule's.** Seven are two milestones on the
Large Test File family (UID 168 on File2 and its four copies, UID 7107 on Leveled and its copy): each
now sits ON its predecessor's finish (08-04 14:58, 01-12 14:31) where it used to render one lunch
hour after it (15:58, 15:31) — the contiguous projection's documented drift (ADR-0322's two-ruler
rule) no longer displayed on a milestone; both predecessors are themselves ~20 h and ~70 h early for
reasons of their own, unchanged. Thirty-four are ONE chain in the non-golden
`Hard_File_updated_with_logic_reestablished` below UID 187, an activity MS Project starts on 08-05
08:00 — 60 % complete, out of sequence, before its predecessor 188's stored 08-17 17:00 finish;
ADR-0391's floor keeps the logic start (the conservative reading, by design), and the chain below it
moved one day later WITH its now-exact predecessor (188 was a day early; it is exact).

**Rendered, not inspected — the real app, pristine tree → this tree, three goldens, seventeen
labels:** on Hard_File the `/analysis` page differs in **8 lines**, all inside the Total-float
distribution and low-float-bands panels; `/api/analysis` differs in the float figures of 65 of 142
activity rows (64 `total_float_days`, 8 `free_float_days` — UID 189's 1.0 → 0.5 is its stored 240
minutes) and the two float-band counts; `/api/driving` in 64 rows' `total_float_days` and nothing
else. **Project5 and Large_Test_File are byte-identical on all three surfaces**, and the eight
session pages (`/`, `/driving-path`, `/path`, `/integrity`, `/margin`, `/curves`, `/dashboard`,
`/api/driving-path`) are byte-identical.

## How it was verified

* **Red first, in a separate worktree at `origin/main` (`3db94b14`), the package under test asserted
  by a `-p mutcheck` plugin.** Twelve of the seventeen new pins fail on the pristine engine by name —
  the milestone carries no instant; the crew successor starts Monday 17:00; the 23:00 milestone
  snaps; the tie's earlier instant wins; the chain of milestones carries nothing; SS from a carried
  milestone reads the start-role rendering; the own-calendar predecessor reads 120 minutes of free
  float; the SNET / manual / recorded ties lose; SS into the milestone hands it nothing; FF into it
  reads free float — and five are controls named as such in their docstrings (the lagged driver, the
  project-calendar-only milestone, the project-calendar successor, and the two gating cases that
  exist for the mutants). The stored-dates oracle's crews test and every raised floor are red there.
* **Mutation battery, 18 cuts on a shadow copy of `src/`** (checksums verified, the plugin asserting
  the package IS the copy, the control 62 passed): M01 the carry never stored → **18** red · M02 the
  predecessor finish ignores it → 12 · M03 the predecessor start ignores it → 1 · M04 the "lost"
  guard dropped (project-calendar-only milestones carried) → 4 red + 15 errors · M05 a lagged driver
  carries → 1 · M06 "lost" ignores a carried predecessor → 4 · M07 the link roles swapped → 18 · M08
  the constraint candidate dropped → 1 · M09 the manual pin dropped → 1 · M10 the recorded start
  dropped → 1 · M11 the earliest instant wins → 7 · M12 the zero-duration condition dropped → 1 ·
  M13 the finish-equals-start condition dropped → 1 · M14 / M15 the instant not exposed on the
  start / finish wall → 10 / 7 · M16 / M17 a successor's start / finish ignores it → 1 / 1 · M18 the
  network's finish instant ignores it → 1. **18 / 18 red by name, no survivor.** The battery's FIRST
  run was discarded: the oracle was re-pinned while it ran, its control went red and its rows carried
  two generations of parametrize ids — the instrument moved under the measurement, exactly the QC-1
  trap; the second run began only after every test edit was final.
* **The rule was written from the corpus's own witnesses**, not from a belief about MS Project:
  updated2's 387 at 23:00, updated3's at 22:24, the 24-hour snapshot's 156 on a Sunday, 181 at 08:00
  — each a stored instant no snap or rounding would produce.
* **Statics** green on both ruff binaries (0.15.8 and 0.16.8) over the whole tree, `ruff format`,
  `mypy --strict` (165 files), `bandit` (exit 0), `node --check` per file.
* **The full gate**, measured in a separate worktree at this unit's code commit: **1 failed / 5,571 passed / 7 skipped in 41:39** (19:18–20:00Z, `-v`, the package under test asserted by the plugin, no stall) and **`-m parity` 171 passed / 0 failed in 6:42**. The one failure is `tests/test_state_docs.py::test_handoff_top_section_pins_the_current_pyproject_version`, red on the code commit's tree (`ae8ee1de`) because it carries the 1.0.271 bump without the rotated handoff; the docs commit carries the pin, its module is green on the final tree, and the final tree differs from the measured one under `docs/` only — so the final tree reads **5,572 green / 0 failed / 7 skipped**. Attributed: **5,579 collected = 5,561 + 17** (the new module) **+ 1** (the oracle's 24-hour row); 5,554 + 18 − 1 = 5,571; parity 170 + 1 = 171. The 7 skips are the documented set (the loopback-allowlist pair, three INCIDENTAL_SVG axis cases, the two LibreOffice interop skips that are correct in this container).

## Consequences

- **R-64 is CLOSED-0505** with its mechanism corrected in the report's row, and **R-66 is CLOSED-0505**
  with it (381 / 396 / 398 exact to the minute on the base snapshot, stored slacks 17,521 / 18,480 /
  18,481 exact; R-57's oracle is reached on both snapshots). **R-67 is the backward mirror** — a
  milestone's LATE instant from a wall-path successor's late-start need — annotated as such, still
  open: re-measured unchanged (UID 94's slack 6,510 vs 6,360; on the 24-hour snapshot milestone
  156's late finish reads 11-02 17:00 against the stored 11-02 09:00, −4,320 vs −4,740), and 404's
  9,420 vs 9,480 is its family.
- The stored-dates oracle's Hard_File rows now pin **110 of 110** finishes within a day on the four
  Standard-calendar snapshots, a stored-slack floor per row (101 / 101 / 36 / 46), and the 24-hour
  snapshot's exact finish (109 / 70 / 7). `tests/importers/test_mspdi_zero_slack_inference.py`'s
  Hard_File witness (241 / 249 recomputing to 480 / 360) was this chain's artefact and now pins the
  engine's own zero beside the inferred stored zero.
- **Two tests whose witness was the engine's DISAGREEMENT with MS Project lost it** — the zero-slack
  inference test (241 / 249 recomputing to 480 / 360) and the chapter-01 Critical-basis test (the
  stored count differing from the pure-logic count on Hard_File). Each now pins the agreement on
  the base snapshot and keeps its divergence witness where one still exists (the synthetic cases;
  updated3's 7 disagreeing flags). A test that needs the engine to be wrong is a test that goes red
  when the engine is fixed; both are documented as such.
- **A milestone's early walls are now populated on multi-calendar files.** Consumers that branch on
  `early_start_wall is not None` (`driving_facts`, DCMA-12's continuity test, three test helpers)
  read the carried instant where they read a rendering before; a single-calendar file still carries
  no wall field at all (the fast-path sentinel holds).
- Version **1.0.271**; the wheel and the nine installers rebuilt after the last `ruff format`.

## Deliberately NOT done — registered, or named

* **The backward carry (R-67).** A milestone's late instant from its wall-path successor is the
  mirror rule; this ADR carries the EARLY instant only, because that is the row's oracle and the
  backward half has its own witnesses (147's Saturday 13:00, 156's 09:00) and its own row.
* **A completed milestone's recorded instant without a crew driver.** A milestone recorded at 14:24
  on a single-calendar file still renders 15:24 (the lunch hour of the contiguous projection); the
  carry needs a driver whose instant the axis lost, by design, so that a single-calendar file stays
  byte-identical. The 24-hour snapshot's 387 (stored 10-20 14:24) is exact only because its crew
  predecessor ties. Named, not built: the wider rule belongs with the two-ruler asymmetry itself.
* **A lagged driver's instant.** A lag lives on the integer axis; carrying the predecessor's instant
  plus a lag would need a calendar for the lag that the engine does not assign. The status quo
  rendering stands, pinned by the lagged control.
* **EVM2's UID 25** — a milestone MS Project stores with a Finish one working day after its Start;
  its start is now exact, its finish untouched, not this row's.
* **`Hard_File_updated_with_logic_reestablished`'s 187** (out-of-sequence progress) and the
  `24Hour Calendar` intake file (23 of 126 exact, unmoved) — each its own row, neither a golden.
* **`late_start_wall` / `late_finish_wall` on a carried milestone** stay `None`: its late instant is
  still the axis's (R-67), and a half-populated pair would over-claim.
