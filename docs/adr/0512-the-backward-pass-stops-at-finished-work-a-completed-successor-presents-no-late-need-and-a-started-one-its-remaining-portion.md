# ADR-0512 — The backward pass stops at finished work: a recorded-complete successor presents no late need and anchors no free float, and a started successor presents its REMAINING portion — its late start floored where the remaining work resumes (R-70 CLOSED; R-71 and R-72 registered)

- **Status:** Accepted — 2026-09-18 (the plan-forward's R-70, the report's §3 row after R-67 / ADR-0510; written under QC-1 / QC-2 (ADR-0393) and QC-3 (ADR-0509)).
- **Version:** **1.0.277** (`src/` changed: `engine/cpm.py`'s backward pass — `_late_need`, `_remaining`, `rem_need` / `rem_ls_wall`, the free-float links; no model, importer, schema, web or metric-formula change). Wheel and the nine installers rebuilt in lockstep.
- **Extends:** **ADR-0476** (a completed activity's window is a record — this ADR reads the same record on the BACKWARD side), **ADR-0507** (a finished activity's stored slack is a zero by fiat and adjudicates nothing — its decision 3 is applied here to the late-date census), **ADR-0510** (whose 17 "away" movers and 67 / 34 census are this row; its carried-late binding check now reads the same need), ADR-0391 / ADR-0309 (the started task's floor and resume floor the remaining portion is measured from), ADR-0463 (total float as the smaller of the two slacks — unchanged).
- **Shipped:** the rule (`engine/cpm.py`); `tests/engine/test_backward_pass_past_finished_work.py` (13 pins — 11 red on the pristine engine by name, 2 controls named as such); the stored-dates oracle (`tests/parity/test_hard_file_stored_dates_oracle.py`: the late-finish census counts INCOMPLETE work only, the floors raised, the row's witness pinned); four pins re-derived with dated reasons (`test_actual_start_floor_own_calendar`, `test_resume_floor_total_float`, `test_float_analysis`'s Project2 count, `test_recorded_completed_window`'s DCMA-12 premise, now on a rig); the report's R-70 row closed and R-71 / R-72 registered; `docs/PARITY-REPORT.md` re-measured.

## Context — what the row said, what the plan said, and what fell

R-70 read: *the backward pass runs THROUGH a completed or started successor that MS Project drops:
Hard_File_updated3 UID 188's stored LateFinish is 12-12 17:00 while its only successor, the
completed UID 291, is stored with a late start of 09-08 08:00; the engine binds 188 to 291's need
and reads 09-08, three months early, and 189 / 181 / 178 / 179 / 180 follow. Censused from the
files alone, 67 incomplete activities carry a stored LateFinish later than a completed successor's
stored LateStart and the engine follows the completed successor on 34.* The kickoff's candidate
rule: drop a recorded-complete successor's need from the backward pass; a started successor's
remaining work needs its own measurement first, the logic-reestablished file's 187 the witness.

**The plan was attacked before the first edit (QC-3), with executable probes over the 15 goldens
and 29 fresh conversions of the intake `.mpp` files (44 files, 22,105 scheduled activities), every
stored late date read from each file's own XML and keyed by path.**

| assumption | result |
| --- | --- |
| the row's mechanism: the engine binds 188 to 291's late-start need | **held.** Walked on the engine's own network: 188's late finish equals the bound from 291 (integer 21,600, 09-08 17:00); 189 / 181 / 178 / 179 / 180 read −12,305 minutes of float behind it. ADR-0510's 67 / 34 re-measured as 67 predecessors / 29 engine-follows on this instrument (72 links). |
| a completed activity's stored late dates are a record | **held, on every one.** LateStart = ActualStart and LateFinish = ActualFinish on **8,644 of 8,644** completed activities, stored slack 0 or absent on every one, Critical set on none. And the same for started work: LateStart = ActualStart on **1,159 of 1,159**. |
| dropping a completed successor reproduces MS Project | **held.** A prediction from the FILE alone — the minimum over the project finish, the caps and the stored needs of the other successors — reproduces the stored LateFinish of every predecessor whose successors include finished work: **40 of 40** (the binding rule: 0 of 40). |
| a started successor should be dropped too | **fell**, to one witness. On `Hard_File_updated_with_logic_reestablished` UID 188 (unstarted) is stored at 08-17 17:00 — not at the next successor's 09-07 (dropping), not at 187's record (08-05, its stored LateStart), and not at the unfloored late start of 187's remaining work (08-12 13:00). It is 187's **Resume**: the instant the remaining 48 h are scheduled to start, after 188 finishes. 187 itself carries −3.5 days. |
| the started rule can be chosen without the population | **fell.** Four candidates measured on the **222** predecessors of started work: the remaining portion's late start FLOORED where it resumes **217**, the unfloored remaining-work late start 215, resume alone 195, the record 193, dropping 138. The five misses are ONE activity's own clamped date on five copies of Large_Test_File2 (R-71, below), not the rule. The floored form is the only one consistent with all 24 SS / FS links into started work: the two binding FS links (the witness and EVM1's 17 → 18) match it and "resume" alone; the 22 SS links never bind, and "the record" and "resume" would pull those predecessors earlier than MS Project stores them. |
| a started successor's free-float anchor is its remaining portion | **fell.** EVM1 UID 17 stores FreeSlack **0** against UID 18's actual start (its stored Start), not the 360 the remaining portion's start would give; the two anchors measured equal on the whole corpus (2,349 exact either way), so the recorded start stays. |
| every started task carries a remaining duration | **fell.** Ten do not (the 99 %-complete 267 / 302 / 385 on the three 24-hour snapshots and EVM1's 17), each with ActualDuration equal to Duration: the MPXJ writer drops the zero, class-blind, exactly as ADR-0507 measured for `TotalSlack` (none of the 24-hour snapshot's 111 completed activities carries the element either). The engine reads the percent-derived remainder (0 at 100 %, 9 to 42 minutes on those four); the importer inference is named below, not taken. |

## Decision

**A successor's need on its predecessor follows the successor's progress.**

1. **A recorded-complete successor presents no late need and is no free-float anchor.** Its dates
   are a record (ADR-0476); MS Project derives the predecessor's late dates from the project finish,
   the caps and the live successors, and its free slack the same way (188's FreeSlack equals its
   TotalSlack). A predecessor with no live successor measures both to the backward target.
2. **A started successor presents its REMAINING portion.** For FS and SS links the need is the
   remaining work's late start — the successor's late finish less its remaining duration, on the
   successor's own legs on the wall path (`_plan_scaled`'s tail) — **never earlier than its early
   finish less the same remaining**, the instant the remaining work is scheduled to start. FF and
   SF needs keep the successor's late finish: the remaining work's finish IS the task's. The
   leveling delay precedes the work and a resumed tail is past it. The SRA's override on an
   in-progress task is its remaining (the `_resume_bounds` rule); an absent remaining is the
   percent-derived remainder of the planned duration.
3. **An unstarted successor is unchanged**, and so is every task's OWN late start (`LF − duration`,
   R-08's held form). The carried-late binding check (ADR-0510) reads the same need.

## What it measured — pristine tree → this tree, 44 files

| population | pristine | this tree |
| --- | ---: | ---: |
| late-finish instants exact, incomplete work | 11,473 | **11,512** (93 toward, **0 away**, 39 newly exact) |
| late-start instants exact, incomplete work | 10,003 | **10,022** (71 toward; 22 started activities away under the LF − duration form, R-08) |
| stored slack exact (13,453 incomplete) | 10,998 | **11,034** (69 toward, 0 away) |
| free slack exact (3,315) | 2,320 | **2,349** (41 toward, 0 away) |
| Critical agreed (22,105) | 21,877 | **22,061** |

By golden (the oracle's rows): Hard_File_updated3_24hr's Critical agreement **70 → 110 of 110**
and late finishes 15 → 17 of 19 (302 / 385 on the crew's own 11-19 01:00); updated3 103 → 109 with
the witness's slack now exact (49 of 68); updated2 107 → 109; Project2 124 → **126** — its
pure-logic critical count is MS Project's own **41** (the two completed activities that read
critical carry the project finish's float) and every incomplete activity's late-finish instant is
exact (**106 of 106**; Project5 **99 of 99**); Large_Test_File / File2: slacks 874 → 876 and
736 → 740, late finishes 919 → 921 and 824 → 828, Critical 1721 → 1723 and 1717 → 1721; EVM1
10 → 11. Four files are byte-identical on every timing field — the base Hard_File (twice) and the
two Jacked Up schedules, the files with no progress recorded.

**The movement AWAY is the record class alone.** 6,176 completed activities' computed late
finishes moved — 18 coincided with the record before, 0 after — because their stored late dates
are their actuals, which the engine does not model (R-71). The oracle census therefore counts
late-finish exactness over incomplete work only, ADR-0507's decision 3 applied to the late dates.
One file lost Critical agreement, the logic-reestablished conversion, 109 → 102: the chain above
the witness (94 → 157 → 147 → 178 / 179 / 180 → 181 → 189 → 188) now reads **+4 days** where the
file stores 0 and the pristine engine read **−8**. Its forward placement is exact to the minute up
to 188; 187, started 08-05 out of sequence and floored to 188's finish, is re-spanned for its FULL
120 h from 08-17 17:00 and finishes 08-27 08:00 where MS Project resumes the remaining 48 h and
finishes 08-20 17:00 — so the remaining portion's scheduled start, the need 188 reads, is four days
late. R-70 exposes that placement; it does not cause it (R-72).

## How it was verified

- **Red first on the pristine package** (a separate worktree at `origin/main` = `4d931ba7`, the
  `-p mutcheck` plugin asserting the imported package): 11 of the 13 synthetic pins fail by name —
  the completed successor's need, its free-float anchor, the chain above it, the completed-among-live
  case, the remaining portion, its floor, the percent fallback, the crew successor's own legs, the crew
  predecessor of finished work, the SS link, the carried milestone — and two are controls named as
  such (an FF link into started work, an unstarted successor); the oracle's witness pin is red there
  by name. Every expectation was derived by hand from the two calendars before the first run; one
  derivation was wrong (the FF control's placement) and was re-derived from the pristine reading.
- **Mutation battery, 12 cuts on fresh copies of the FINAL `src/`** (each cut md5-verified, the plugin
  asserting the copy, the control 30 green): M01 a completed successor's need kept → 6 red · M02 a
  started successor presents its whole task → 12 · M03 the fast-path floor dropped → 2 · M04 the
  wall-path floor dropped → 1 · M05 the absent-remaining fallback reads the full duration → 2 · M06 /
  M07 free float keeps completed anchors (fast / wall) → 2 / 1 · M08 the wall-path needs keep a
  completed successor → 4 · M09 nothing is ever started → 13 · M10 a wall-path predecessor ignores the
  remaining portion's instant → 1 · M12 the no-live-successor free float reads 0 → 1. **M11 — the
  carried-late binding check reading the whole task — SURVIVED the first run (30 green): a milestone
  between a crew predecessor and a started crew successor was pinned nowhere.** The pin was written
  (the milestone carries Thursday 17:00, its crew predecessor retreats from it), red on the pristine
  engine and red under the cut. **12 / 12.**
- **Four pins moved, each re-derived with its reason:** the own-calendar floor's predecessor reads
  the pour's remaining portion (five days, was four); the resume-floored chain's predecessor reads
  13 days (was 9 — a re-do of the four days already done); Project2's pure-logic critical count is
  41 (was 43); the DCMA-12 premise (UID 26, finished, on Project2's critical path) no longer holds on
  the corpus and is pinned on a rig where a finished activity carries negative float.
- **Statics** green on both ruff binaries (0.15.8 and 0.16.8) over the whole tree, `ruff format`,
  `mypy --strict` (165 files), `bandit` (exit 0), `node --check` per file; the wheel built after the
  last `src/` edit; lockstep 68 passed. The full suite and `-m parity` were measured in a separate
  worktree at this unit's code commit; the figures are in the session log and the handoff.
- **Not done:** a render diff — the view layer is untouched; free float reaches the activity rows
  through `float_analysis`, and the suite's web tests render every page over the fixtures.

## Consequences

- **R-70 is CLOSED.** Hard_File_updated3 UID 188's late finish is the backward target, its free
  float its total float, and its chain's floats sit within the half-minute of its sub-minute
  recorded finish (14:05:30) of the stored figures; the 24-hour snapshot's three 99 %-complete
  activities read the project finish, two on the crew's own instant. The target's instant on
  updated3 is a crew's Saturday, 12-12 17:00; a non-zero-duration activity on the project axis reads
  the minute's Friday rendering — ADR-0510's carry is for zero-duration tasks by design, named here.
- **R-71 registered (T3):** the record's own late dates. A completed activity's stored LateStart /
  LateFinish are its actuals, slack 0, never Critical (8,644 / 8,644); a started activity's stored
  LateStart is its actual start (1,159 / 1,159); and MS Project writes a started activity's
  LateFinish no earlier than its remaining work can start after the status date while its stored
  slack keeps the unfloored figure (**22** activities across the corpus, four distinct: 5539 /
  5263 / 6444 on the Large_Test_File2 family, 389 on the 24-hour snapshots — e.g. 5539: LateFinish =
  EarlyFinish 2027-09-02 with FinishSlack −209,147 minutes). The engine computes all three from
  logic. Pinning them as records changes `is_critical` for every finished activity and the critical
  path with it — its own decision.
- **R-72 registered (T1):** a started activity whose start the floor moved past its actual start is
  re-spanned for its FULL duration where MS Project spans the remaining work from Resume
  (ADR-0391's floor, ADR-0309's resume floor as a floor). Census: 192 of 1,159 started activities
  are floored past their actual start; 25 finish more than a working day after the stored Finish,
  **7 of them floored** (one activity on each of the six Large Test File copies and the
  logic-reestablished 187), 18 unfloored (other placements), 40 finish more than a day early.
- **Named, not taken:** the importer inference for an absent `RemainingDuration` (the dropped zero,
  ADR-0507's pattern — ten activities, all at 99 %, all reading 1 % of their duration here); a free
  float floored at zero (MS Project stores no negative FreeSlack anywhere in the corpus; the engine
  can read one on out-of-sequence work); the logic-reestablished file as a golden (it is the only
  witness for the floor and is a non-golden conversion — the floor is pinned synthetically).
- Version **1.0.277**; the wheel and the nine installers rebuilt after the last `src/` edit.
