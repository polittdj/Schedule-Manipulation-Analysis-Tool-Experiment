# ADR-0502 — A booking's own leveling delay is honoured on that leg alone, on ADR-0474's type axis (R-57 CLOSED)

- **Status:** Accepted — 2026-09-16.
- **Version:** **1.0.268** (`src/` changed: model, both importers, the CPM plan builder). Wheel and the nine installers rebuilt in lockstep.
- **Extends:** **ADR-0474** (the task's own leveling delay, and the type/ratio rule this one rides), **ADR-0501 / ADR-0500** (R-61: a non-`FIXED_UNITS` leg spans ratio 1.0 × the effective duration — the rule that decides which delays are absorbed), ADR-0487 (a MATERIAL / COST leg IS its recorded window, so its delay is never read), ADR-0491 (the split gaps, the sibling calendar quantity).
- **Shipped:** `Assignment.leveling_delay_minutes` (schema **2.15.0**), the MSPDI and Save-`.json` readers/writer, `_Leg.delay` / `_LegShape.delay` through the plan builder and both passes, `CPMResult.assignment_leveling_driven`, `tests/engine/test_assignment_leveling_delay.py` (10 pins) and `tests/parity/test_r57_assignment_leveling_delay_oracle.py` (8 pins).

## Context — what the row said, and the two things measurement changed about it

R-57 read: *assignment-level `LevelingDelay` (Hard_File UID 398's two bookings, UID 188) is not
read — only the task's delay is honoured (ADR-0474)*, with the first step *"read
`Assignment/LevelingDelay` onto the Assignment model and delay that leg alone"* and the oracle
*"the stored finish of UID 398"* (2026-08-27 11:59).

The mechanism is real. MS Project can level ONE crew off a task without moving the task or its
other crews, and stores that per assignment, in tenths of a minute, distinct from the task's own
`LevelingDelay`. Hard_File UID 398's Technology Lead booking is the row's witness and it is both
**split** (ADR-0491 — honoured since #679) and **delayed** (not honoured): the file starts it
2026-08-25 **16:59**, 239 minutes after the task's 13:00, and finishes it 08-27 11:59 — which is
the task's own stored finish. Fed that start, the engine's existing leg arithmetic already
lands on 11:59 to the minute. Only the delay was missing.

Two things the row got wrong, both found before anything was changed.

**The population is wider than the row.** Six of the fifteen goldens carry an assignment-level
delay — **24 delayed bookings on 17 tasks** — including every `Large_Test_File` snapshot, not
the two Hard_File activities the row names. This is ADR-0500's lesson applied before the fact
rather than after it: a rule measured on the two activities a row happens to name is a claim
about those two activities.

**"Delay that leg alone" is right for six of the 24 bookings and a REGRESSION for the other
eighteen.** Implemented as written, it cost `Large_Test_File` **93 of its 1,666**
finishes-within-a-day and took UIDs 5266 / 5267 / 5270 from EXACT to days late. That number is
why this ADR exists in the shape it does: the first cut was measured against the whole golden
census before it was believed, and the census refuted it.

## Decision — the delay rides ADR-0474's type axis, it does not cut across it

A booking's delay is applied to **that leg alone**, in **working minutes of the leg's own
calendar**, before any of its work begins — and whether it moves the finish is decided by the
same ratio that decides the leg's span:

| the leg | its delay | why |
| --- | --- | --- |
| has its OWN span (`FIXED_UNITS`, ratio < 1) | **PUSHED** — starts late and still owes all its work, so the finish moves out | ADR-0474 gives it work / units, independent of the task's window |
| SPANS THE TASK (ratio 1.0) | **ABSORBED** — starts late and still ends with the task | the delay lies inside the span it shares with the task |

The split is **6 push / 18 absorb** and it falls exactly on the file: every pushed booking is
Hard_File's (`FIXED_UNITS`), every absorbed one `Large_Test_File`'s (`FIXED_WORK`). The absorb
half is not an assumption — on **16 of those 18** bookings the file's own `Assignment/Finish`
**IS** its `Task/Finish`; the two that are not are co-bookings that finish earlier either way.

**The TASK's start does not move.** On all 17 witness tasks `Task.Start == min(Assignment.Start)`,
and every one of them also carries an undelayed booking, so `min(all starts)` and
`min(undelayed starts)` are indistinguishable here — 17/17 each. The engine takes the
non-double-counting reading (the delay never enters `_plan_snap`); a task whose bookings are
**all** delayed would read its start early, and **no such task exists in the corpus**, so that
case is **UNVERIFIED** and registered rather than claimed.

**The delay is read to the NEAREST minute, not truncated.** Against MS Project's own
`Assignment/Start` on the 24 bookings, rounding reproduces **17** and truncating **14**, and
rounding is never the worse of the two on any single booking. Every one of the 7 misses is
**sub-minute** (12–78 s) and is the engine's integer-minute floor meeting `Large_Test_File2`
task starts that carry seconds — R-65's class, not a rule error. Note the inconsistency this
creates: ADR-0474's **task-level** reader still truncates (`// 10`). Whether it should also
round is **registered, not measured here**, and is not changed in this unit.

**A MATERIAL / COST booking's delay is never read**: its leg IS its recorded window (ADR-0487),
which already embeds whatever wait MS Project applied.

**The delay joins the leg's IDENTITY.** The plan de-dupes legs by (calendar, span, gaps); without
the delay in that key a leveled crew collapses onto its unleveled twin and vanishes.

**Disclosure.** `CPMResult.assignment_leveling_driven` names a task only when the delayed leg is
the one that **places** the finish, measured from the task's REAL early start — not from the
project start the legs are sorted by. The first cut disclosed on the sort order and produced a
false positive on `Hard_File_updated2` UID 398, whose delayed crew finishes before its co-crew
and whose finish the delay does not decide. In a testimony context a disclosure that over-claims
is worse than none.

## What it measured — every golden, before and after

`engine/` changes nothing outside Hard_File; **`Large_Test_File`, `Large_Test_File2`,
`Large_Test_File_Leveled`, `Project2`, `Project5`, `Hard_File_updated3` and the SSI golden are
BYTE-IDENTICAL** on every column (activities, finishes-within-a-day, exact finishes, exact
stored slack, Critical agreement, project finish).

| golden | exact finishes | exact stored slack |
| --- | --- | --- |
| `Hard_File_updated` | 58 → **61** | 93 → **99** |
| every other golden | unmoved | unmoved |

**The row's oracle is reached — on `Hard_File_updated`.** UID 398 goes from 2026-08-26 17:00 to
MS Project's own **2026-08-27 11:59**. On the base `Hard_File` snapshot it is NOT exact, and the
residual is not this rule's: **UID 381 finishes a full day early there** (08-20 11:59 against the
stored 08-21 11:59), 396 inherits it, and 398 then lands early by **exactly the 240 working
minutes 396 is early by** — computed in the pin, not copied. ADR-0474's task-delay arithmetic is
EXACT on both snapshots when fed the stored predecessor finish, so the blocker is upstream of
leveling entirely. Registered as **R-66**.

`Hard_File_updated2` UID 188 moves from **15 h 45 m early to 66 seconds** under MS Project's
instant (its booking's work is 348.x minutes and the engine floors to whole ones — R-65).

## How it was verified

* **Red before green.** Both modules fail on the pristine tree: `Assignment` refuses
  `leveling_delay_minutes` (extra forbidden) and `CPMResult` carries no
  `assignment_leveling_driven`.
* **The census refuted the first cut before it was reported.** The "push everything" reading was
  measured against all ten goldens and lost 93 finishes-within-a-day; the type guard exists
  because of that measurement, not in anticipation of it.
* **Mutation battery: 9 cuts, 9 red BY NAME, control green before and after**, each cut checksum-
  verified to have changed the file and the file checksum-verified restored. M6 — dropping the
  delay from the BACKWARD pass — **survived the first pass**: every other check was green
  without it. It is not cosmetic; it is worth **three exact stored slacks** on
  `Hard_File_updated` (99 → 96), on UIDs **321 / 381 / 396**, the very chain that feeds 398. The
  survivor was killed by a pin naming those three.
* **A line that could not fire was deleted rather than shipped.** The first `_leg_finish` snapped
  to the next working instant after the delay, justified by MS Project reporting a delayed
  booking's start there. Swept over **31,479** delay / span / gap combinations — 6 of them
  landing exactly on a segment end — the snap never moved a leg finish, because the work that
  follows is itself an `_advance_wall`, which counts a segment END and the next segment's start
  identically. The corpus agreed but weakly (its one segment-end delay is on an absorbing leg),
  so the sweep is what settles it.
* Statics green on **both** ruff binaries (0.15.8 and 0.16.8), `ruff format`, `mypy --strict`,
  `bandit` (exit 0).

## Consequences

* A forensic reader can now see that a **crew's own leveling**, not the activity's, is what
  finished an activity — a distinct manipulation signature from a task-level delay.
* The delay is dropped from `_plan_scaled`: a resumed TAIL is already past it.
* Registered, not taken: **R-66** (UID 381's day on the base snapshot), the task-level reader's
  truncation, and the all-bookings-delayed task start (no witness anywhere in the corpus).
