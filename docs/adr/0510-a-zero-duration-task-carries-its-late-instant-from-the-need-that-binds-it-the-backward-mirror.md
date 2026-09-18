# ADR-0510 — A zero-duration task carries its LATE instant from the need that binds it: the backward mirror of ADR-0505 — a wall-path predecessor retreats from the milestone's own instant, a binding deadline is an instant too, and a carried milestone's slack is measured between its two instants (R-67 CLOSED; R-69 and R-70 registered)

- **Status:** Accepted — 2026-09-18 (the plan-forward's R-67, the report's §3 row after R-65 / ADR-0508; the first unit written under QC-3, ADR-0509).
- **Version:** **1.0.275** (`src/` changed: `engine/cpm.py`'s backward pass carries a wall instant on project-axis zero-duration tasks — `ms_late_wall`, `_carried_late_instant` — exposes it on `TaskTiming.late_start_wall` / `late_finish_wall`, hands it to a wall-path predecessor through `_succ_ls_wall` / `_succ_lf_wall`, and measures a carried milestone's slack between its instants; no model, importer, schema, web or metric-formula change). Wheel and the nine installers rebuilt in lockstep.
- **Extends:** **ADR-0505** (the forward carry this mirrors — its "late walls stay None: the late instant is still the axis's (R-67)" is superseded here), **ADR-0474** (the backward pass on the wall path — the successor's late start less its elapsed delay is the candidate this ADR hands a milestone), ADR-0322 (the two-ruler rule that makes one project-axis minute stand for two instants), ADR-0476 (the day-boundary milestone class it named), ADR-0503 (which measured UID 94's 150 minutes and named them this row's), ADR-0509 (the rule this unit was the first to run under).
- **Shipped:** the carry and its consumers (`engine/cpm.py`); `tests/engine/test_milestone_carried_late_instant.py` (14 pins — 10 red on the pristine engine by name, 4 controls named as such); the stored-dates oracle re-pinned (`tests/parity/test_hard_file_stored_dates_oracle.py`: a late-finish-instant census column read from each golden's own XML, a late-finish floor per Hard_File row, the slack floors raised, a dated chain pin on the base and the 24-hour snapshots, Project2 / Project5 and the Large Test Files' late finishes pinned as the controls they are); the R-58 oracle's residual test rewritten as the agreement it now is; ADR-0505's "late walls None" pin and a multicalendar fast-path proxy re-pinned; the report's R-67 row closed and R-69 / R-70 registered; `docs/PARITY-REPORT.md`'s stored-dates table re-measured.

## Context — what the row said, what the plan said, and what fell

R-67 read: *Hard_File's base snapshot: milestone 147 has a stored LateStart of Saturday 2026-08-01
13:00 — the minimum over its leveled successors' late starts less their elapsed delays; the engine's
integer axis has no Saturday instant, 147 reads Monday 08:00, its crew predecessor 157 reads its
late finish there (two hours after the stored Friday 23:00), and UID 94's total slack inherits 150
minutes (6,510 vs 6,360)*. ADR-0505 had named it the backward mirror of the forward carry and left
a milestone's late walls `None` for it. The kickoff plan: carry a leveled successor's late-start need
to a fast-path predecessor as a wall instant, red-first on 157's Friday 23:00 and 94's 6,360.

**The plan was attacked before the first edit (QC-3), on the pristine tree, with executable probes
over the 15 goldens and 29 fresh conversions of the intake `.mpp` files.** Two of its four
assumptions fell — the full table is in ADR-0509; the two that matter here:

| assumption | result |
| --- | --- |
| the carried instant comes from a wall-path SUCCESSOR (the mirror of ADR-0505's gating) | **fell.** On `Hard_File_updated3_24hr` the chain head is milestone **155**, whose late instant is its **deadline** (11-05 17:00) — it has no successor at all. Its predecessor milestone 411 and the 24-hour crew UID 146 below read the minute's start-role rendering, **11-06 08:00, fifteen crew hours late**, and the chain 145 → 144 → 9 → 36 → 156 inherited them (156: −4,320 for the stored −4,740 — the row's own witness). The same deadline-headed chain sits over a 24-hour crew on updated2 and updated3. 27 fast-path milestones across the 44 files are bound by a raw deadline or date constraint; 26 on files with wall-path tasks. |
| the row's one milestone is the class | **fell.** Of 2,210 zero-duration tasks across the 44 files, **155** carry a stored LateStart OUTSIDE the project calendar's working time (a weekend, a night, a lunch hour), **1,740** on a block boundary, 315 interior; the engine's late-start instant was exact on 508. |

And two facts the attack established that the row did not state: the same rule fires **twice on the
same chain** (milestone 181's late instant is the crew successor 189's late start, 08-04 **21:00**, an
instant outside the Standard day; 178 / 179 / 180 read 08-05 08:00 for it and sat four crew hours
late, and 178's need less its 72 elapsed hours is 147's Saturday); and the arithmetic below the
milestone, fed the stored Saturday, reproduces every stored value to the minute (157: 07-31 23:00 /
15:00 / 2,760; 94: 07-31 15:00 / 07-30 22:00 / 6,360) — the row's "exact when fed the stored
Saturday" was testimony until that run.

## Decision

**A fast-path zero-duration task carries its late instant from the need that binds it, and a
wall-path predecessor retreats from that instant.** In the backward pass, once the integer pass has
placed a zero-duration task (`late_finish == late_start`), `_carried_late_instant` collects the
instants of every need that BINDS its late finish: a lag-0 FS / SS successor's late start less its
elapsed leveling delay (a wall-path successor's `ls_wall`, ADR-0474's own candidate; a carried
milestone's instant; a project-calendar successor's start-role rendering), a lag-0 FF / SF
successor's late finish, and — only on a file with wall-path tasks (`target_wall` is not `None`) — the
raw instant of a binding deadline or date constraint and the backward target itself. **The earliest
wins**, MS Project's `min` over instants. Nothing is carried unless some binding need is an instant
the axis LOST — a wall-path successor's, a carried milestone's, a raw cap's or the target's; a
milestone bound by project-calendar successors only is untouched, a lagged BINDING link leaves the
rendering in charge (a lag is a quantity of the integer axis), a non-binding successor contributes
nothing and blocks nothing, and every single-calendar file is byte-identical (no cap or target can
carry there; the fast-path sentinel — `early_start_wall is None` — still holds). The instant rides
`TaskTiming.late_start_wall` / `late_finish_wall` (both, one instant), feeds `_succ_ls_wall` /
`_succ_lf_wall` (a wall-path predecessor's finish or start need — 157 retreats from Saturday and
lands on Friday 23:00; 146 retreats from the deadline and lands on 11-05 17:00), and a milestone
whose EARLY instant is carried (ADR-0505) measures its total float between its two instants on the
project calendar — the axis's contiguous projection of a mid-day instant drifts by the lunch gap
(UID 404 read 9,420 where MS Project stores 9,480; the milestone's early instant is 10-08 15:00).

**Two candidate rules were measured on the population before one was chosen** (the R-65 lesson):
the carry alone, and the carry with the slack-between-instants form. Their late-date movement is
identical; the second gains **four** more exact stored slacks (UID 404 on the four Hard_File entries)
and loses none. The second is the rule.

**The carry itself moves no integer minute.** Every candidate projects to the minute the integer pass
chose (the synthetic pin asserts `late_finish == late_start == 1440` beside the carried Wednesday
21:00). The integer late minutes that DID move across the 44 files — 162 late finishes and 181 late
starts, 342 wall-path tasks' late instants — are wall-path tasks retreating from corrected instants
and the tasks upstream of them; ten of those are fast-path milestones whose wall-path successor's
late start moved (six are UID 149, a completed milestone whose stored slack is a record; four are on
the non-golden `Hard_File_updated_with_logic_reestablished`), each verified to have such a successor.

## What it measured

**The per-task census, pristine tree → this tree, every golden and every conversion** (the late
finish and late start against the stored instants, exact to the second; the slack against the stored
figure on incomplete activities):

| golden | late finish exact (of n) | late start exact | stored slack exact |
| --- | --- | --- | --- |
| **Hard_File** | 78 → **94** of 110 | 73 → **86** | 101 → **108** of 110 |
| Hard_File_updated | 83 → **87** | 79 → 83 | 101 of 103, unmoved |
| Hard_File_updated2 | 27 → **37** | 20 → **39** | 36 → **38** of 76 |
| Hard_File_updated3 | 30 → **45** | 29 → **48** | 46 → **48** of 68 |
| **Hard_File_updated3_24hr** | 3 → **15** | 1 → **15** | 7 → **15** of 19 |
| Project2 / Project5 | 108 / 99 of 126, unmoved | 106 / 97, unmoved | 106 / 99, unmoved |
| Large_Test_File / File2 | 918 → 919 / 824 | 685 → **703** / 719 → **744** | 874 / 736, unmoved |
| the SSI Large Test File / Leveled | 956 → 957 / 916 → 917 | 724 → 742 / 801 → 819 | 948 / 841, unmoved |

Across the 44 files (22,105 scheduled activities): **268 late finishes moved toward the stored
instant, 17 away; 260 late starts toward, 17 away; 50 stored slacks newly exact, 0 lost**; late-finish
instants exact 11,312 → 11,491, late starts 9,582 → 10,021, stored slack 10,948 → 10,998 of 13,453;
milestone late starts exact 508 → 831; **26 files changed, 18 byte-identical on every timing field —
every single-calendar file among them** (EVM1, the three FX saves, the three TP4 saves, Jacked up
Schedule 2) and every Project2 / Project5 save. The full-field dump (every `TaskTiming` and
`CPMResult` field, 44 files) changed 1,473 timings: 1,416 / 1,424 late walls, 162 / 181 integer late
minutes, 222 total floats.

**The 17 "away" are two named mechanisms, neither this rule's.** Fifteen sit on chains whose late
dates MS Project derives past a **completed or started successor** the engine's backward pass still
runs through: on `Hard_File_updated3` UID 188's stored LateFinish is **12-12 17:00** while its only
successor, the completed UID 291, is stored with a late start of 09-08 08:00 — MS Project does not
let finished work bind a predecessor's late dates; the engine binds 188 to 291's need, reads 09-08,
three months early, and 189 / 181 / 178 / 179 / 180 above it follow (the carry moves them 305 minutes
on top, toward 181's carried instant); the same on the non-golden logic-reestablished file below the
started, out-of-sequence UID 187. Censused from the files alone, **67** incomplete activities across
the corpus carry a stored LateFinish later than a completed successor's stored LateStart, and the
engine follows the completed successor on 34 — **R-70**, registered. Two are Leveled's UID 1248, a
**completed milestone** whose late dates are a record (ADR-0507's reading), moved a lunch hour by a
carried successor.

**One form left, named and registered — R-69.** The engine writes a block-exact late start at the
END of the working block where MS Project writes the START of the next one: UID 178 reads 08-04
**12:00** for the stored **13:00** (`_retreat_wall` → `_tod_at_worked`'s block-end form), the same
working minute on every calendar in the file, so 147's carried instant reads Saturday 12:00 for the
stored 13:00. **742** late starts across the 44 files differ from the stored instant by this form
alone (166 on Large_Test_File, 14 on Hard_File), no slack or late finish among them. It is not a
one-line fix: the contiguous projection (ADR-0322's two-ruler rule) of the 13:00 form reads 300
minutes into the day where 12:00 reads 240, so every project-calendar PREDECESSOR would inherit the
lunch hour as float — the form is right for the axis and wrong for the instant, and the decision
belongs to its own row.

## How it was verified

* **Red first, in a separate worktree at `origin/main` (`bb5cef0d`), the package under test asserted
  by a `-p mutcheck` plugin.** Ten of the fourteen synthetic pins fail on the pristine engine by name
  — the milestone carries no late instant; the crew predecessor retreats from Thursday 08:00 and
  reads 960 for 720; the carried milestone's slack reads 540 for 600; the deadline is not carried
  (960 for 480); the finish milestone's late walls are None; the delayed successor's need is not
  handed on; the chain, the FF consumer, the tie and the non-binding lagged successor — and four are
  controls named as such (the lagged binding link, the project-calendar-only binding, the
  single-calendar file, the non-binding crew successor). Seven oracle pins are red there by name: the
  five Hard_File rows (the late-finish floors and the raised slack floors), the dated chain pin, and
  Large_Test_File's late-finish floor; Project5's and File2's late-finish pins equal their pristine
  values by construction and are the controls they are documented as.
* **Every expectation in the synthetic module was derived by hand from the two calendars before the
  first run**, and the run agreed on every one (a number that matches the hypothesis is the moment to
  re-derive it, not to write it down — none needed re-deriving).
* **Mutation battery, 17 cuts on fresh shadow copies of the FINAL `src/`** (each cut md5-verified to
  change the file, the plugin asserting the shadow on every row, the control 84 green): M01 the carry
  never stored → **15** red · M02 `_succ_ls_wall` ignores it → 10 · M03 `_succ_lf_wall` ignores it →
  1 · M04 the "lost" guard dropped → 2 · M05 a lagged binding link carries → 1 · M06 "lost" ignores a
  carried successor → 3 · M07 the cap candidate dropped → 4 · M08 the target candidate dropped → 4 ·
  M09 the latest instant wins → 3 · M10 the single-calendar gate dropped → 1 · M11 the zero-duration
  condition dropped → 17 · M12 the binding check dropped → 2 · M13 FS reads the successor's late
  FINISH → 14 · M14 the walls not exposed → 14 · M15 the slack stays the axis's → 3 · M16 the slack
  measured to the rendering → 1 · M17 the delay subtracted twice → 7. **17 / 17 red by name.** The
  battery's FIRST run read 16 / 17: **M12 survived** — no test exercised a NON-binding successor, so
  the check that keeps a non-binding lagged link from blocking the carry and a non-binding crew
  successor from making a rendering-bound milestone carry was unpinned. The code was right and the
  pins were missing; two were written (one dated, one a control) and the whole battery re-run.
* **Three existing tests moved, each for a stated reason:** ADR-0505's "late walls stay None" pin on
  the finish milestone (written knowing R-67 would supersede it) now pins the finish instant; a
  multicalendar fast-path test that read late walls as a proxy for "not on the wall machinery" now
  reads the early wall (Jacked Up Schedule 1's UID 22, a milestone, carries a late instant — and its
  stored late start is now exact); the R-58 oracle's test whose witness was the engine's
  DISAGREEMENT with MS Project (94's 150 minutes) now pins the agreement (ADR-0505's doctrine: such a
  test goes red when the engine is fixed).
* **Statics** green on both ruff binaries (0.15.8 and 0.16.8) over the whole tree, `ruff format`,
  `mypy --strict` (165 files), `bandit` (exit 0), `node --check` per file; the wheel built after the
  last `src/` edit and the last format; the lockstep pins green.
* **The full gate and `-m parity`** were measured in a separate worktree at this unit's code commit;
  the figures are in the session log and the handoff.
* **A render diff was NOT run**: the view layer is untouched, no consumer outside `engine/cpm.py`
  reads a late wall, and the suite's web tests render every page over the fixtures.

## Consequences

- **R-67 is CLOSED.** On the base snapshot the chain 94 → 157 → 147 → 178 / 179 / 180 → 181 → 189
  lands on every stored late date and every stored slack (94: 6,360; 157: 2,760; 178 / 179 / 180:
  240 / 480 / 720; 181: 480; 189: 240; 404: 9,480); on the 24-hour snapshot the chain 155 → 411 →
  146 → 145 → 144 → 9 → 36 → 156 → 141 lands on every stored late date and slack (146: −19,200; 156:
  −4,740; 141: −4,800).
- **R-69 and R-70 are registered** with their measured populations (742 and 67 / 34), each with the
  reason it is not this unit's.
- A carried milestone's late walls are populated on multi-calendar files (1,379 milestones across
  the corpus carry one, 154 before — the 154 are milestones on the wall path themselves). No
  consumer in `src/` outside the engine reads a late wall; tests that asserted `None` for a
  milestone's late walls were the two re-pinned above.
- ADR-0505's "the milestone's float stays the axis's" is narrowed: a milestone whose early instant is
  carried measures its slack between its instants; one whose early instant is not carried (147,
  driven by its FNET constraint) keeps the axis's, which is exact (0) on the witness.
- Version **1.0.275**; the wheel and the nine installers rebuilt after the last `src/` edit.

## Deliberately NOT done — registered, or named

* **The block-end form of a late start (R-69).** Measured, 742 across the corpus; changing the form
  hands every project-calendar predecessor the lunch hour through the contiguous projection — its own
  decision.
* **The backward pass through a completed or started successor (R-70).** Measured, 67 / 34; MS
  Project drops finished work from a predecessor's late dates; a started successor's remaining work
  needs a rule measured first.
* **A carried milestone's FREE float** stays the axis's (`link_slack` on integers) — no witness in
  the row and none found; named.
* **The forward analogue of the deadline case** — a milestone bound by a raw SNET / MSO date with
  project-calendar predecessors only and a crew SUCCESSOR reading the finish-role rendering of a
  start-of-day date. ADR-0505 gates the forward carry on a wall-path driver; whether the corpus holds
  such a milestone was NOT censused this unit — **UNVERIFIED**, named for the next reader of the
  forward carry.
* **A required finish** (`required_finish_offset`, the driving-slack analysis) hands the target as a
  finish-role rendering, exactly what every wall-path task already retreats from; a milestone at that
  target carries the same rendering. Unchanged behaviour for the analysis; named.
* **Late walls on single-calendar files** stay `None` by the file gate — a half-populated pair with
  no consumer would over-claim, and byte-identity on those files is the invariant ADR-0505 set.
