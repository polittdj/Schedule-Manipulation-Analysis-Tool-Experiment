# ADR-0517 — Every started activity's remaining work is scheduled from its stored Resume, read in working minutes of the calendar's own segments; the contiguous projection of the stored-date family is registered as R-77 (R-73 CLOSED)

- **Status:** Accepted — 2026-09-20 (the plan-forward's R-73, the report's §3 row after R-72 / ADR-0513; written under QC-1 / QC-2 (ADR-0393) and QC-3 (ADR-0509)).
- **Version:** **1.0.281** (`src/` changed: `engine/cpm.py`'s forward pass on both paths — the remaining portion of EVERY started, incomplete activity, and `_stored_instant_offset`, the segment-aware read of the stored Resume; no model, importer, schema, web or metric-formula change). Wheel and the nine installers rebuilt in lockstep.
- **Extends:** **ADR-0513** (whose narrow rule — the out-of-sequence class only — is generalized to every started activity; its five decisions stand), **ADR-0309** (the resume floor is subsumed for every started activity with a recorded actual start; it stays for a source recording a reschedule on an activity without one), **ADR-0391** (the record stays the start), **ADR-0512** (an in-sequence started successor still anchors its predecessor's free float at its RECORD), **ADR-0322** (the two-ruler rule is honoured: the segment-aware read is a floor under `max()`, never a projection the network's ordering depends on).
- **Shipped:** the rule (`engine/cpm.py`); `tests/engine/test_started_work_resumes_remaining.py` (11 pins — 9 red on the pristine package by name, 2 controls named as such); the R-72 module's in-sequence crew pin re-derived; the stored-dates oracle (`tests/parity/test_hard_file_stored_dates_oracle.py`: the Large Test File rows re-pinned UPWARD, the 24-hour snapshot's slack floor 15 → 16, UID 1489's pin re-derived to EXACT, an R-73 witness pin on 4616 / 7378 / 5505 and EVM1's 18 / 17); the report's R-73 row closed and R-77 registered; `docs/PARITY-REPORT.md` re-measured.

## Context — what the row said, what the plan said, and what fell

R-73 read: *every started activity's finish is `Resume + RemainingDuration` on its execution calendar
(1,113 of 1,159 from the file alone); the engine reads `actual_start + duration` for started work that
is NOT out of sequence, so an actual portion that ran long or short lands the finish off the stored
instant — Large_Test_File UID 4616 106 days early, 5505 43 early, 7378 three late, the 24Hour_Calendar
file's UID 17 64 days late and that file's project finish with it. The wide model was measured under
ADR-0513 and held back: the contiguous project axis reads an after-lunch Resume up to the lunch gap
LATER (EVM1 UID 18's 15:00 Resume carries that golden's finish across midnight), and a dropped-zero
remaining reads 0 on one file and the whole duration on another.* Its remedy: decide the stored
instant's projection FIRST.

**The plan was written and attacked before the first edit (QC-3), with a census instrument over the
15 goldens and 29 fresh conversions of the intake `.mpp` files (44 files, 22,105 scheduled activities,
1,159 started and incomplete), every stored date read from each file's own XML and keyed by path, and
two candidate engines built on shadow copies and measured on the whole population before one was
chosen.** The pristine census reproduced ADR-0513's figures to the number (1,144 starts exact, 1,107
finishes within a day, 11,543 late-finish instants, 11,177 stored slacks, 22,069 Critical flags).

| assumption | result |
| --- | --- |
| MS Project's rule reproduces ~1,113 of 1,159 from the file alone | **held**: 1,111 of the 1,149 that store a remaining; the 38 misses are ADR-0513's four split bookings (5376 / 5669 / 6565 / 7260 across their copies — a gap inside the remaining portion the MSPDI does not carry) and UID 5505's minute (the model's whole-minute grid reads 614 for 614.4). |
| every started activity with an ABSENT `RemainingDuration` has `Finish = ActualStart + Duration` | **held, with a mechanism**: all 10 are MPXJ's dropped zero on a 99 % activity with `ActualDuration == Duration` (EVM1 UID 17; the 24-hour snapshots' 267 / 302 / 385). Two shapes: Stop = Resume = the ACTUAL START (17, 267 — `Resume + 0` would finish them the minute they began) and Stop = Resume = the FINISH (302 / 385 — `Resume + 0` IS the finish). No single reading fits both; the wide model reads only a STORED remaining, and the class keeps the plan from the record (17 exact; 267 the axis's hour; 302 / 385 on that snapshot 6 h / 55 h early, R-56's bookings on that save — named, not this row's). |
| the stored Resume is projected by walking the remaining on the calendar's true segments and projecting the FINISH with the contiguous ruler (the wall→int rule) | **FELL.** The first candidate did exactly that and read 1,111 started finishes "exact" — while the stored slacks exact fell **11,177 → 9,930** and free slacks 2,367 → 2,041. The instrument had compared two contiguous projections (the engine's finish and the stored finish's) and agreed with itself by construction; the stored slack, a working-minute quantity independent of any ruler, refuted it. The axis IS working minutes: `start + duration` on it counts them exactly, and the contiguous ruler is wrong only where it PROJECTS a mid-day instant (15:00 on a 08-12 / 13-17 day is minute 420 there and 360 in worked minutes). The projected finish landed after-lunch finishes the gap late on the axis and every successor's slack with them. |
| the stored Resume read SEGMENT-AWARE (true worked minutes), the remaining added on the axis | **held — the shipped rule.** Every boolean measure moved toward the file with none lost (below); EVM1's 18 and 17 unchanged; 4616 / 5505 / 7378 / 1489 / the 24Hour_Calendar file's 17 on their stored finishes and slacks. |
| a segment-aware read of ONE instant gives it two offsets — the ordering trap ADR-0322 named | **held as stated, and it does not bite here**: the read is a FLOOR under `max()` against the link bounds, which stay on the contiguous projection, so a restart can never precede a linked predecessor's finish; a same-instant constraint, actual start or pin keeps its contiguous reading (a 60-minute inconsistency between two tasks' placements, the class the engine already carries between its arithmetic and its projections — R-77). |
| the disclosure counts do not grow on Resume == Stop files | **held, and 35 fell**: `date_driven` 525 → 490. The ten lost (LTF2's 3948 / 3951 / 3981 / 6998 / 7206, the Leveled file's 3948 / 3951 / 3981 / 5452 / 7206, over their copies) each have an after-lunch Resume that TIES its finish-to-finish bound (the pair is scheduled to finish together); the contiguous floor had read the Resume past the tie by the gap and disclosed a date logic supports. |
| free slacks exact do not fall (the record anchors an in-sequence successor) | **held**: 2,367 → 2,428, none away. |
| stored slacks exact rise with no mover away unnamed | **held**: 11,177 → 11,383, no boolean lost; 39 distinct slacks on Large Test File2 (65 rows over its copies) read farther by the 30–60 minutes their early finish had been LATE by — their late finishes sit 1,450 / 4,330 minutes off before and after (R-56's chains on that file) and the early-finish error had been cancelling part of it. |
| `-m parity` holds (the SSI file's 105 of 108 started activities have Resume > Stop and were already floored at R + rem) | **held**: `tests/parity` green in the 1,563 (with `tests/engine` and `tests/test_projects`), the SRA and SSI oracles unmoved. |
| the wall-path class reproduces with `_plan_scaled` tails | **held**: 24 wall-path started activities; the 24Hour_Calendar file's UID 17 (a task calendar) EXACT and its project finish 2027-08-23 → the stored 2027-08-04 17:00. |
| the after-lunch class is small and axis-exact under the rule | **held**: 73 Resumes off a segment boundary across the 44 files (the LTF family's status-date instants, TP4 v3's UID 19, EVM1's 18); 71 axis-exact under the rule, the two others 5505's minute. |

## Decision

**A started activity's remaining work is scheduled from where the file says it resumes, whether or
not its progress ran ahead of its logic.**

1. **Every started, incomplete activity with a recorded actual start, a restart instant (`Resume`, else
   `Stop`) and a STORED remaining (or the SRA's override, which is a remaining — the `_resume_bounds`
   rule)** starts at its record and its remaining portion starts at the later of the stored Resume and
   the link bounds evaluated for the remaining (FS / SS as for any activity, FF / SF retreating the
   remaining, never a date constraint); its finish is that restart plus the remaining on its own legs.
   The out-of-sequence class keeps ADR-0513's percent fallback for an absent remaining; in sequence an
   absent element is MPXJ's dropped zero and the activity keeps `actual_start + duration`.
2. **The stored Resume is read segment-aware** (`_stored_instant_offset`): whole working days plus the
   working minutes of the calendar's own segments consumed before the instant's minute of the day. The
   axis is working minutes; the contiguous ruler's clamp is not. On the wall path the raw instant is
   snapped onto the plan's tail as before.
3. **The backward pass retreats such an activity by the remaining it was placed with** — its total
   float is its finish slack, MS Project's TotalSlack on started work — and R-70's need is unchanged.
4. **An in-sequence started successor anchors its predecessor's free float at its RECORD** (ADR-0512);
   an out-of-sequence one at its restart (ADR-0513).
5. **Disclosure:** a recorded reschedule (Resume > Stop) that places the remaining past both logic and
   the record's own plan joins `date_driven`, as ADR-0309's floor disclosed it; contiguous progress
   (Resume == Stop) resuming where it stopped is not an unsupported date; the out-of-sequence class
   keeps ADR-0513's disclosure (the Resume past the logic). ADR-0309's floor stays only for a source
   recording a reschedule on an activity without an actual start.

## What it measured — pristine → this tree, 44 files, 22,105 activities

| measure | pristine | this tree | toward / away |
| --- | ---: | ---: | --- |
| started finishes exact (segment-aware axis / the wall) | 1,050 | **1,114** | 64 toward, 0 away |
| started finishes within a day | 1,107 | 1,126 | — |
| unstarted starts / finishes exact | 19,144 / 20,375 (all classes) | 19,376 / 20,687 | 232 / 248 toward, 0 away |
| incomplete late-finish instants exact | 11,543 | **11,645** | 102 toward (100 unstarted, 2 started), 0 away |
| stored slacks exact (incomplete) | 11,177 | **11,383** | 206 toward (159 / 47), 0 away |
| free slacks exact | 2,367 | 2,428 | 61 toward, 0 away |
| Critical agreed | 22,069 | **22,095** of 22,105 | 26 toward, 0 away |
| project finishes exact | 27 | **28** of 44 | the 24Hour_Calendar file |
| `date_driven` | 525 | 490 | 35 contiguous-tie artefacts gone |

The witnesses, in working minutes from the stored finish (engine − stored): 4616 −34,080 → 0 (its
float 161,760 → the stored 127,680); 7378 +480 → 0 (306,720 and its free slack 60,240 exact); 5505
−14,400 → −1 (the minute grid; its slack by that minute); 1489 +60 → 0 (98,880 exact); the
24Hour_Calendar file's 17 +92,160 → 0 (its slack 3,180 → the stored 70,860, its late finish exact);
EVM1's 18 held at 2012-08-21 17:00 (the 09-12 project finish kept) and 17 at its stored 360 with its
free float 0; TP4 v3's 19 exact before and after (its actual portion was on plan). 45 started finishes
remain off the stored instant, every one named: the four split bookings (32 rows), 5505's minute (4),
the dropped-zero trio on the 24-hour snapshots (9).

## How it was verified

- **Red first on the pristine package** (a copy of `src/` at `b0545572` under `PYTHONPATH`, the
  `-p mutcheck` plugin asserting the import): 9 of the 11 new pins fail by name — the mechanism, the
  ran-short finish and its finish slack, the after-lunch Resume in working minutes, the predecessor's
  late finish at the restart, the stored remaining over the percent, the SRA override, the reschedule
  disclosed only past the plan, the FF need on the remaining — and two are controls named as such
  (the dropped zero; a source recording neither Resume nor Stop); the R-72 module's in-sequence crew
  pin, re-derived by hand from the two calendars (Resume + 16 crew hours → Wednesday 17:00, the float
  the finish slack 2,880), fails there too. Every expectation was derived from the calendar before the
  first run.
- **Mutation battery, 8 cuts on fresh copies of the FINAL `src/`** (each md5-verified, the import
  asserted, the uncut control green): the Resume projected contiguously (5 red — the after-lunch pin,
  the anchor / late-finish pin, the disclosure pin, 1489's oracle pin, the R-73 witness); the fast-path
  rule restricted to the out-of-sequence class (9); an absent remaining read as the percent remainder
  (2 — the dropped-zero control and the witness); the retreat by the whole duration (4); the anchor at
  the restart for an in-sequence successor (2); contiguous progress disclosed (1); ADR-0309's contiguous
  floor re-applied over the placed remaining (1 — the reschedule shortened past the plan); the wall-path
  rule restricted (1 — the crew pin). **8 / 8 red by name.**
- **The suites on this tree:** `tests/engine` + `tests/parity` + `tests/test_projects` 1,563 passed;
  the CPM counterfactual's consumers in `tests/web` (change effects, integrity, the SRA's stored axis,
  the panel contract, path options) + `tests/importers` + the SRA 470 passed; `tests/installer` 68
  (lockstep) after the rebuild; statics green on ruff 0.15.8 and 0.16.8 over the whole tree, `ruff
  format`, `mypy --strict` (165 files), `bandit`. The full suite is read in the session log with the
  PR.
- **The final tree reproduces the chosen candidate on every one of the 22,105 activities** (0
  differing timings between the shadow census and the tree's).

## Consequences

- **R-73 is CLOSED.** Every started activity finishes at `Resume + RemainingDuration`; the four named
  witnesses and 60 more sit on their stored finishes; 206 more stored slacks, 102 more late-finish
  instants and 26 more Critical flags agree with the file; the 24Hour_Calendar file's project finish is
  the stored instant.
- **R-77 registered (T2, M):** the rest of the stored-date family — the actual-start floor, the
  completed-window pin, the stored-start pin / floor, constraint dates, deadlines, ADR-0309's residual
  floor — and the rendering ruler (`offset_to_datetime`) still project contiguously. Measured on this
  tree: 4 started activities whose 13:00 actual start reads the gap late (15 starts inexact in all, 11
  the holiday / clamp class), 25 completed activities whose pinned finish reads 54–60 minutes late, and
  212 unstarted finishes exactly one lunch gap off their stored instant. ADR-0322's trap is the reason
  it is a family, not a site: the projections and the rendering must move to a segment-aware pair
  together, or one instant carries two offsets across a link.
- **Named, not taken:** reading an absent remaining as zero (302 / 385 exact, 17 / 267 the morning
  they began); a seconds-aware Resume (5505's minute is R-65's grid); the late START of started work
  (LS = AS — R-71); the free-float cap (R-74); the four split bookings (R-60's tail); a finish-slack-only
  total for the wide class (unneeded: the retreat by the remaining makes `min()` the finish slack
  wherever the record precedes the restart).
- Version **1.0.281**; the wheel and the nine installers rebuilt after the last `src/` edit.
