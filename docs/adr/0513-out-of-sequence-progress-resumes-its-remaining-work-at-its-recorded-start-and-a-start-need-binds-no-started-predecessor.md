# ADR-0513 — Out-of-sequence progress resumes its REMAINING work at its recorded start, from the later of the stored Resume and the logic bounds for the remaining; a start-type successor need binds no started predecessor (R-72 CLOSED; R-73 and R-74 registered)

- **Status:** Accepted — 2026-09-20 (the plan-forward's R-72, the report's §3 row after R-70 / ADR-0512; written under QC-1 / QC-2 (ADR-0393) and QC-3 (ADR-0509)).
- **Version:** **1.0.278** (`src/` changed: `engine/cpm.py`'s forward pass — the remaining portion of an out-of-sequence started activity on the project axis and on the wall path — and its backward pass — the retreat span, the start-type needs on a started predecessor, the free-float anchors; no model, importer, schema, web or metric-formula change). Wheel and the nine installers rebuilt in lockstep.
- **Extends:** **ADR-0391** (the actual-start floor could not bind on this class — the logic start was the later instant — and the whole duration ran from it; the start is now the record on it), **ADR-0476** (whose "pin every started start" measurement is re-read: UID 1489's 136-day swing belonged to the FULL-duration re-span from a pinned start, not to the start), **ADR-0309** (the resume floor becomes the span on the out-of-sequence class; the floor stays for every other started activity), **ADR-0512** (R-70's need now reads a remaining portion placed where MS Project places it), **ADR-0322** (the two-ruler rule — the contiguous axis reads an after-lunch Resume an hour late — is the reason the general model is registered as R-73 and not taken), ADR-0467 (a constraint on a started activity yields to the actual start — on the remaining portion too).
- **Shipped:** the rule (`engine/cpm.py`); `tests/engine/test_out_of_sequence_progress_remaining.py` (18 pins — 17 red on the pristine engine by name, 1 control named as such); the stored-dates oracle (`tests/parity/test_hard_file_stored_dates_oracle.py`: the Large Test File rows re-pinned UPWARD, an R-72 witness pin on the golden's UIDs 1489 / 4581 / 5535); the report's R-72 row closed, R-73 (T1) and R-74 (T2) registered, R-71 amended; `docs/PARITY-REPORT.md` re-measured.

## Context — what the row said, what the plan said, and what fell

R-72 read: *a started activity whose start the ADR-0391 floor moved past its actual start is
re-spanned for its FULL duration from the floored start, where MS Project spans the REMAINING work
from Resume. `Hard_File_updated_with_logic_reestablished` UID 187 (60 %, 48 h left, started 08-05
out of sequence) is floored to 188's finish, 08-17 17:00, and finishes 08-27 08:00 for the stored
08-20 17:00 — and under R-70 its remaining portion's scheduled start, the need 188 reads, is four
days late; the chain 94 … 188 reads +4 days where the file stores 0.* The kickoff's candidate: a
floored started activity spans its REMAINING from the later of the floor and Resume, measured
against ADR-0476's rejected variants on the whole corpus first, UID 1489's 136-day swing the trap.

**The plan was attacked before the first edit (QC-3), with executable probes over the 15 goldens
and 29 fresh conversions of the intake `.mpp` files (44 files, 22,105 scheduled activities, 1,159 of
them started and incomplete), every stored date read from each file's own XML and keyed by path, and
six candidate rules built on shadow copies of the engine and measured on the whole population
before one was chosen.**

| assumption | result |
| --- | --- |
| MS Project's rule for a started activity is `Finish = Resume + RemainingDuration` on its execution calendar | **held.** From the file alone, with the engine's calendar ruler as the instrument: **1,113 of 1,159**. The 46 misses are three classes, none the rule: the dropped-zero 99 % activities (EVM1 17 and the 24-hour snapshots' 267 / 302 / 385 — the writer's absent zero reads as the WHOLE duration on two of them and as 0 on the other two), `updated`'s 187 (eight crew hours the split reading carries), and four Large Test File bookings with a gap inside the remaining portion (5376 / 5669 / 6565 / 7260). |
| every started activity carries a Resume; every file was scheduled with split-in-progress on | **held.** `Resume` present on 1,159 of 1,159 (later than `Stop` on 1,119 — the status date's night or weekend); `SplitsInProgressTasks` = 1 on 44 of 44 files. |
| "the floor moved the start" is the row's mechanism | **partly.** 192 of the 1,159 started activities sit past their actual start; 574 are floor-bound and 393 at their record. The 25 finishing more than a day late are 7 "past" (187 and 4581 × 6), 17 floor-bound (5669 × 8, 7378 × 5), 1 at the record (the 24Hour_Calendar file's 17); the 40 early are 15 past (5376 × 8, 1489 × 6), 16 floor-bound, 9 at the record. The class BESIDE the row is larger than the row. |
| the floor that moved the start is a link | **fell**, on UID 4581: its one FS predecessor finished in 2024, and the instant that held its start at 2025-04-01 is a Start-No-Earlier-Than constraint MS Project ignores on started work — its Resume is the status date's next working instant and its stored Finish is that plus 288 h. A constraint binds nothing once the work has begun, on the remaining portion as on the start (ADR-0467). |
| the whole-task logic start is the right bound for the remaining portion | **fell**, on UID 1489: TEN finish-to-finish links from finished work put its whole-task start (their finish less 229 days) past its actual start; the remaining portion's FF bound (their finish less 11.45 days) lies before its Resume. An FF / SF need must be evaluated for the REMAINING, or a restart plus the remaining ends before the predecessor's finish and the link is violated. |
| UID 1489 is the trap for a remaining-based rule | **fell the other way.** Its stored Finish is Resume + remaining to the minute; the 26 days early the pristine engine read and the 136-day swing ADR-0476 measured were both the FULL-duration re-span (from the logic start, from a pinned start). ADR-0476's rejected variant was rebuilt (V3 below) and reproduced its 60 unstarted movers away; the remaining-based rule reads 1489 on its Resume + remaining. |
| the narrow rule (the out-of-sequence class only) is the right population | **held, for this unit — measured, not assumed.** The WIDE model (every started activity with a stored remaining) gains more on every measure but pays the contiguous axis's hour on every after-lunch Resume (V2 / V6 below): EVM1 UID 18's 15:00 Resume carries that golden's finish date across midnight, TP4's UID 19 and Large_Test_File's 5505 / 5452 move a working hour that crosses a weekend. Registered as R-73 with the measurement; the axis's projection is ADR-0322's decision, not this row's. |
| a respanned activity's early start should stay the logic start | **fell.** MS Project stores Start = ActualStart on every started activity; with the finish anchored at the restart plus the remaining, the record can no longer pull the network earlier, and a logic start with a remaining-based finish is a span that lies (4581's would read nine hours for 36 days of work). The record: 181 starts newly exact, six more exact slacks, nothing away. |
| the start-type (SS / SF) successor needs of a started predecessor are harmless | **fell**, found by the wide model's own regressions: UIDs 631 / 6147 / 5535 lost an exact late finish because an SS need bounds a predecessor's late START plus its span, and a started predecessor's start is a record (LateStart = ActualStart on 1,159 of 1,159, ADR-0512). Measured alone on the pristine engine (V0s): 13 started late finishes toward the stored instant, 11 newly exact, nothing away — 5535's 2027-07-02 for the stored 11-05 was the pristine engine's own error. 73 started predecessors carry 84 such links across the corpus. |
| a respanned successor's free-float anchor is its remaining portion's start | **held**: MS Project stores no negative FreeSlack anywhere in the corpus, and an anchor at the record — before the predecessor's own finish — reads one. 18 free slacks newly exact. |
| the wall path's tail carries the remaining portion's gaps | **held**: `_plan_scaled` keeps a split gap ahead of the consumed head; 5376's FF-driven remaining lands within its day. |

Two anomalies were read case by case and are not this row's: UID 3849's start reads one day past
its record on every Large Test File copy (its actual start is the observed New Year holiday, a
non-working instant the axis cannot hold), and UID 408 on the witness file — the ONE mover away
in 22,105 — sits on its stored dates with its successor on theirs and its total float exact
(16,740) while its free float reads 18,960: MS Project's stored FreeSlack never exceeds its
TotalSlack (0 of the 3,315 activities storing both; equal on 1,116) and the engine's does on 1,870
incomplete activities (R-74).

## Decision

**An activity whose progress ran ahead of its logic resumes its REMAINING work; its actual work is
a record.**

1. **Out-of-sequence progress** is a started, incomplete activity whose logic start — after the
   constraint pins and floors and the stored-start rules — lies PAST its recorded actual start. Its
   early start is its **record** (the actual start, on the project axis or snapped onto its own
   legs), disclosed on `actual_start_driven`. Its **remaining portion** starts at the later of the
   stored `Resume` (else `Stop`) and the link bounds evaluated FOR THE REMAINING: FS / SS as for any
   activity, FF / SF retreating the remaining (the plan's tail on the wall path), never a date
   constraint. Its finish is that restart plus the remaining on its own legs — the SRA's override
   IS the remaining (the `_resume_bounds` rule), an absent remaining is the percent-derived
   remainder. When the stored Resume, not logic, places the work, the activity is disclosed on
   `date_driven` (ADR-0309's disclosure). A source that records neither `Resume` nor `Stop` (a P6
   export, a synthetic fixture) is unchanged: the row's oracle is MS Project's.
2. **The backward pass retreats such an activity by the remaining it was placed with** — its late
   start is the remaining portion's, the instant R-70's need reads — and its total float is its
   finish slack (MS Project's own TotalSlack on 187: the FinishSlack, StartSlack absent).
3. **A start-type (SS / SF) successor need binds NO started predecessor**, respanned or not: its
   start is a record and only its finish is still scheduled. Every other need (FS / FF, the caps,
   the target) binds as before.
4. **A predecessor's free float anchors at a respanned successor's restart**, not at the recorded
   start that precedes the predecessor's own finish; a started successor that is not out of
   sequence keeps its recorded start as the anchor (ADR-0512).
5. **Started work that is NOT out of sequence keeps `actual_start + duration`**, ADR-0309's floor
   included — the general `Resume + remaining` model is R-73's.

## What it measured — the candidates on the 44 files, and pristine → this tree

| candidate | started finish exact / within a day | > 1 d late / early | starts exact | late finishes exact | stored slacks exact | free slacks exact | Critical agreed | movers AWAY from a stored value |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| pristine (`5b605970`) | 343 / 1,094 | 25 / 40 | 963 | 11,512 | 11,034 | 2,354 | 22,061 | — |
| V1 the row's candidate, logic start | 346 / 1,107 | 18 / 34 | 963 | 11,532 | 11,158 | 2,372 | 22,069 | 0 on dates and slacks |
| V1b + the recorded start | 346 / 1,107 | 18 / 34 | 1,144 | 11,532 | 11,164 | 2,372 | 22,069 | 1 (UID 408's free float) |
| V5d + start-type needs dropped on every started predecessor (**shipped**) | 346 / 1,107 | 18 / 34 | 1,144 | 11,543 | 11,177 | 2,372 | 22,069 | 1 (UID 408's free float) |
| V0s the start-type drop alone | 343 / 1,094 | 25 / 40 | 963 | 11,523 | 11,047 | 2,354 | 22,061 | 0 |
| V2 the WIDE model, logic start | 351 / 1,115 | 22 / 22 | 963 | 11,617 | 11,229 | 2,387 | 22,095 | 10 started finishes, 23 started late finishes, 9 unstarted, 3 completed late finishes |
| V6 the WIDE model, recorded start, needs dropped (R-73) | 351 / 1,115 | 22 / 22 | 1,144 | 11,636 | 11,256 | 2,387 | 22,095 | 10 started finishes, 9 started free slacks, 9 unstarted starts / finishes, 7 unstarted late finishes, 3 completed late finishes — EVM1's chain, TP4's 19 and 5452 the axis's hour, UID 34 the record |
| V3 ADR-0476's rejected pin + full span | 342 / 1,099 | 18 / 42 | 1,144 | 11,532 | 11,162 | 2,370 | 22,069 | 60 unstarted, 8 started |

Populations: 1,159 started activities; 13,461 incomplete activities for the late finishes; 13,453
stored slacks and 3,315 stored free slacks on incomplete work; 22,105 activities for Critical.

**Pristine → this tree, by class:** 13 started finishes toward the stored instant (3 newly exact),
192 started starts toward (181 newly exact), 13 started late finishes toward (11 newly exact), 26
started slacks and 6 started free slacks toward; 173 unstarted successors' starts and finishes
toward (104 / 67 newly exact), 20 unstarted late finishes newly exact, 185 unstarted slacks and 31
unstarted free slacks toward, 8 unstarted Critical flags now agreeing; 7 completed late finishes
toward; **one** figure away (UID 408's free float, R-74). One project finish moved: the
logic-reestablished conversion's, 11-15 08:15 → the stored **11-12 12:00**, exact; its Critical
agreement 102 → **110 of 110** (R-70 had read 109 → 102) and 187 / 188 / 184 / 94 on their stored
dates and slacks (187: −1,680, the stored −16,800 tenths). The Large Test File golden: finishes
within a day 1,666 → 1,682, stored slacks exact 876 → **882** of 1,024, late finishes exact 921 →
922; File2: 740 → 741 and 828 → 829. Every Hard_File golden, Project2 / Project5 and the EVM goldens
are byte-identical on every timing field.

## How it was verified

- **Red first on the pristine package** (a separate worktree at `origin/main` = `5b605970`, the
  `-p mutcheck` plugin asserting the imported package): 17 of the 18 synthetic pins fail by name —
  the mechanism, the stored Resume past the logic, the backward retreat and the predecessor's need,
  the FF need evaluated for the remaining, the FF need retreating the remaining, the SS bound, the
  constraint binding nothing, the start-type need on a started predecessor (fast and crew), the
  free-float anchors (fast, crew predecessor of a fast successor, crew predecessor of a crew
  successor), the percent fallback, the SRA override, the witness's own shape on the crew's legs,
  the wall-path FF need, the wall-path Resume == Stop past the logic — and one is a control named
  as such (a source recording neither Resume nor Stop); the oracle's Large Test File rows and its
  R-72 witness pin are red there by name. Every expectation was derived by hand from the two
  calendars before the first run; three derivations were wrong (a crew activity begun before the
  project start, which the axis clamps; a Friday counted as a Thursday; 1489's slack, which carries
  the axis's hour on its 13:24 Resume) and were re-derived from the file's own calendar, never from
  the engine's answer alone.
- **Mutation battery, 21 cuts on fresh copies of the FINAL `src/`** (each cut md5-verified, the
  plugin asserting the copy, the uncut control green on the three modules): the fast-path and
  wall-path respans removed, the start left at the logic start on either path, the FF / SF bound
  evaluated for the whole task (fast) and the whole plan (wall), constraints kept in the restart,
  the stored Resume ignored on either path, the backward retreat by the full duration / the whole
  plan, the start-type needs kept on either path, the free-float anchor at the start on either path,
  the percent fallback reading the full duration, the SRA override ignored, each disclosure
  dropped, Stop read before Resume, the trigger widened to every started activity. **21 / 21 red by name on the third run**, the uncut control green each time: the first run left FOUR
  survivors and the second two, every one a missing WALL-PATH pin and not a code hole — an FF need
  into a crew activity (M06), a stored Resume later than the logic on the crew's legs (M09: the
  first pin written had Resume > Stop, the shape ADR-0309's floor already covers, and survived; the
  discriminating shape is Resume == Stop PAST the logic, the work having run on), a start-type need
  on a started crew predecessor (M13), and a crew predecessor's free-float anchor at a crew
  successor's restart (M15: the first pin's successor sat on the fast path, whose anchor is another
  line) — each written, red on the pristine engine and red under its cut.
- **The shadow run** of `tests/engine`, `tests/parity` and `tests/test_projects` against the
  candidate engine before the first edit: 1,507 passed, the two Large Test File oracle rows the only
  failures (both floors move UP), 10 errors the copy's missing `tools/mpxj` (an artefact of the
  copy, green on the tree). The working tree's own census reproduces the candidate's on every one
  of the 22,105 activities.
- **Statics** green on both ruff binaries (0.15.8 and 0.16.8) over the whole tree, `ruff format`,
  `mypy --strict` (165 files), `bandit` (exit 0), `node --check` per file; the wheel built after the
  last `src/` edit; lockstep 68 passed. The full suite and `-m parity` were measured in a separate
  worktree at this unit's code commit; the figures are in the session log and the handoff.
- **Not done:** a render diff — the view layer is untouched; the suite's web tests render every
  page over the fixtures.

## Consequences

- **R-72 is CLOSED.** The logic-reestablished 187 finishes on its stored 08-20 17:00 with its
  stored slack, 188's late dates are exact, the chain 94 … 188 reads the stored 0, and that file's
  project finish is the stored instant. UID 1489 reads Resume + remaining; 4581 its stored start and
  finish; 5535 its stored late finish.
- **R-73 registered (T1, M):** the general `Finish = Resume + RemainingDuration` model for every
  started activity — 1,113 of 1,159 by the file; 4616 106 days early, 5505 43 early, 7378 three late
  and the 24Hour_Calendar file's 17 (and its project finish) 64 days late under the shipped rule —
  held back by the contiguous axis's hour on an after-lunch Resume (ADR-0322) and the dropped-zero
  remaining's two readings.
- **R-74 registered (T2, S):** free float above the total float — MS Project's stored FreeSlack
  never exceeds its TotalSlack; the engine's does on 1,870 incomplete activities (UID 408).
- **R-71 amended:** two of its parts are taken (the start-type needs on a started predecessor; an
  out-of-sequence activity's late start as its remaining portion's); the record's own late dates,
  the 22 clamped late finishes and the Critical flag on finished work remain its scope.
- **Named, not taken:** the wide model (R-73); the free-float cap (R-74); the importer's
  dropped-zero remaining (ADR-0512's class — it reads as 0 on 302 / 385 and as the whole duration on
  EVM1's 17 and 267, so no single inference fits); UID 3849's holiday actual start; the witness file
  as a golden (its shape is pinned synthetically, and 1489 / 4581 / 5535 on the Large Test File
  golden carry the oracle).
- **Three Hard_File-derived pins moved with it and were re-derived, not re-fitted (2026-09-20,
  after PR #702's first CI read — `floor` and `test (3.11)` on `dc862dbf`, 3 failed / 5,306 passed /
  269 skipped, the three the only red):** the 188→187 counterfactual on Hard_File →
  Hard_File_updated, target UID 155, reads **+12 → +6 wd** (`test_change_effects_integration.py` ×2,
  `test_integrity_multifile_robust.py`; +23 / +21 / +15 before ADR-0322 / ADR-0391 / ADR-0474).
  UID 187 is 60 % complete with 2,880 crew-minutes left on the Customer Service Team's 16-hour day —
  three project days — and with the removed link restored its logic start (188's finish, day 32)
  lies past its recorded start (day 20): the pristine engine re-spanned the whole 8-day plan from
  188's finish (day 40); this rule resumes the remaining after it (day 35); 155 moves 3,120 min =
  6.5 wd, **+6** under `round()`'s half-even (the rounding sites are R-04's; the exact minutes ride
  on the `ChangeEffect` but nothing renders them above a day). 187 is the ONLY mover: the other
  five change rows read +0 on both engines and 155's 2,400-min difference is 187's own finish. The
  aggregate (every change reverted together) reads +0 for the pristine +2: the joint revert pulls
  188's finish to day 21.9, before 187's stored Resume (day 25), so the remaining resumes where the
  record says. Red on the 5b605970 worktree by name (3 failed, each on the `+6` literal, the page and
  the fact base reading +12) and green here (3 passed, the imported package asserted); the tests'
  point — a NON-ZERO effect the AI cannot round to "no effect" — stands. Caught by CI, not by the
  worktree suite, which died at 57 % unread: the counterfactual's consumers live in `tests/web`,
  outside the `tests/engine` + `tests/parity` shadow run.
- Version **1.0.278**; the wheel and the nine installers rebuilt after the last `src/` edit; the
  pin re-derivation is a tests + docs commit with no `src/` change.
