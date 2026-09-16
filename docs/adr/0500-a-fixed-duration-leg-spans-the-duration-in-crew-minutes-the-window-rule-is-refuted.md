# ADR-0500 — A FIXED_DURATION leg keeps spanning the DURATION in crew minutes: R-61's "the window is the rule" is REFUTED, and its witness is masked by neither rule the row names (R-61 CLOSED)

- **Status:** Accepted — 2026-09-16 (the plan-forward's R-61, the report's §3 row after R-50 / ADR-0499).
- **Version:** unchanged — **no `src/` change**. The finding is that the engine is already right; the deliverable is the census, the corrected premise, the refutation and the tripwire that stops the refuted rule landing silently.
- **Extends / re-reads:** ADR-0474 (execution plans; the type rule this row proposed to change), ADR-0476 (the completed-window pin the row names as a mask), ADR-0487 (the material / cost recorded leg the row names as the other mask, and the standing rule that a WORK booking's window is never read), ADR-0491 (the leveling splits the refuted rule would undo).
- **Shipped:** `tests/parity/test_r61_fixed_duration_leg_oracle.py` (10), the R-61 row in `docs/STATE/AUDIT-2026-08-27-REPORT.md` → CLOSED. `engine/` untouched.

## Context

The register's row R-61 read:

> a FIXED_DURATION booking on an off-pattern crew spans the DURATION in crew minutes
> (ADR-0474's type rule) where MS Project keeps the task's window: `Hard_File_updated3` UID 210's
> Content Developer booking is recorded over four project days and computed as 1.33 days on the
> 24-hour calendar — masked today by the completed-window pin (ADR-0476) and by the material leg
> (ADR-0487)

with the first executable step: *census every FIXED_DURATION task with an off-pattern crew across
the goldens, recorded booking window vs the computed leg; if the window is the rule, a
fixed-duration leg spans the task's window on the crew calendar*, and the oracle: *the stored
booking windows of those tasks*.

The census was run. It settles the row three times over, and not in the direction the row
expected.

## What the census measured

### 1. The population is ONE task, in five snapshots of ONE file

Across all **15 MSPDI goldens**, the set of (golden, task) pairs where an **active
FIXED_DURATION** task carries a **WORK leg on a calendar that differs materially from the
project calendar** is exactly five rows — **UID 210 in `Hard_File_updated2`, `_updated3`,
`_updated3_24hr` and the two `ssi_hardfile_24h_uid155` snapshots**. There is no second task
anywhere in the corpus, no *unstarted* witness, and none without a project-calendar co-booking.

The row's arithmetic on that witness is correct: the task's duration is **1,920 minutes**
(4 project days), the leg spans 1,920 minutes of the 24-hour *Content Developer* calendar
(= 1.33 days there), and the file records the booking over **7,740** of those minutes — a
5,820-minute disagreement. The booking's window is the **task's own window** exactly
(2026-08-20 08:00 → 2026-08-25 17:00): MS Project writes the task window onto all four of
this task's assignments, work and material alike.

### 2. The row's premise is mis-stated — neither named rule is the mask

Read off the live plan builder rather than inferred, UID 210's plan on `Hard_File_updated3` is:

| leg | calendar | span | finishes from 2026-08-20 08:00 |
| --- | --- | --- | --- |
| **primary** | `Standard` (the project calendar) | 1,920 | **2026-08-25 17:00 — the stored finish, exact** |
| | `Content Developer` (24 h) | 1,920 | 2026-08-21 16:00 |

The finish-placing leg is the **`Standard`-calendar WORK leg of the Logistics Apprentice
booking** — the same 1,920 minutes consumed on the *project* calendar. The off-pattern crew leg
finishes four days earlier and **has never placed this task**. Measured on a shadow copy of the
engine with each rule cut in turn:

| tree | UID 210's early finish | vs the stored 2026-08-25 17:00 |
| --- | --- | --- |
| pristine | 2026-08-25 17:00 | **exact** |
| ADR-0476's completed-window pin CUT | 2026-08-26 14:00 | **+1,260 min — LATE** |
| pin CUT **and** ADR-0487's material leg CUT | 2026-08-26 14:00 | +1,260 min, **unmoved by the second cut** |

So the material leg is not the mask (cutting it moves nothing at 210, though it moves the file's
project finish 12-12 → 12-06 and within-a-day 106 → 44, so the cut plainly has teeth elsewhere),
and the pin does not mask a leg that reads *early* — without it the task reads **late**. The
row's sign is wrong.

### 3. The proposed rule is INERT as written, and REFUTED when generalized

R-61's rule was implemented on the shadow engine exactly as the row specifies — a FIXED_DURATION
leg spans `_recorded_span(crew calendar, booking.start, booking.finish)` instead of the duration.
It **fires**: the leg's ratio goes 1.0000 → 4.0312, its span 1,920 → 7,740, and its finish
2026-08-21 16:00 → 2026-08-25 17:00. And it changes **nothing**: project finish, within-a-day
count and stored-slack-exact count are **byte-identical to pristine on all 15 goldens**. Its only
consequence is a *regression of a disclosure* — the crew leg ties with the `Standard` leg and
sorts first, so UID 210 drops off `CPMResult.booking_span_driven` (ADR-0487).

MS Project has no separate scheduler for FIXED_DURATION, so "the leg spans the recorded window"
is a claim about **ratio-1.0 WORK legs** generally (the corpus has **267** tasks whose
finish-placing leg is one). Generalized and measured per task against the files' own stored
finishes:

| | within-a-day, pristine → rule |
| --- | --- |
| `fuse_ltf/Large_Test_File` | 1,666 → **1,568** |
| `fuse_ltf/Large_Test_File2` | 1,687 → **1,585** |
| `ssi_uid152_leveled/Large_Test_File_Leveled` | 1,645 → **1,567** |
| every Hard_File snapshot, Project2 / Project5, EVM1 / EVM2, `ssi_uid152` | unmoved |

**Per-task toward/away census across all 15 goldens: 315 activities move AWAY, ZERO move
TOWARD** (worst mover +309,865 minutes). The mechanism is already understood: a split booking's
recorded window spans the leveling gaps ADR-0491 honours *separately*, so reading the window
overrides them. The pinned witness is `Large_Test_File` UID 5231, whose recorded window (89,760
crew minutes) is **26,880 minutes SHORTER** than the occupancy the engine correctly places
(89,760 span + 26,880 of ADR-0491 gap) — reading the window would collapse the very split
ADR-0491 was built to honour.

### 4. The one alternative worth refuting on its own merits, refuted

Because the correct placement at UID 210 comes from a leg on the **project** calendar, a second
hypothesis is available that the row does not name: MS Project's FIXED_DURATION duration is a
property of the **task**, not of the assignment, so such a leg might run on the *task's* axis
rather than the crew's. Measured the same way: **0 toward, 5 away** (the five UID 210 rows). It
drops the task off the wall path entirely, so ADR-0476's pin lands on the integer axis at
2026-08-25 **16:00** — the day-boundary representation residual ADR-0476 names — 60 minutes
away. Refuted.

## Decision

**R-61 is CLOSED as REFUTED. ADR-0474's type rule stands: a non-FIXED_UNITS leg spans
`ratio 1.0 × the task's effective duration` on its leg calendar, and a WORK booking's recorded
window is still never read (ADR-0487).** No `engine/` change is made, and none may be made on
this evidence: under QC-1 a change with no check in the corpus capable of refuting it does not
get to touch the engine, and the only candidate rule is refuted 315-to-0 where it *can* be
tested.

What ships instead is the measurement, pinned so it cannot be quietly re-opened:
`tests/parity/test_r61_fixed_duration_leg_oracle.py` carries the census population, the
witness's two numbers, the corrected premise (the primary leg is `Standard`, not the crew), the
five stored-finish oracles, the ADR-0491 refutation witness, and one **tripwire** on the type
rule itself — labelled a tripwire in its own docstring, because a shape pin is not evidence
about MS Project and must not be read as any.

## The residual, named and NOT closed by this ADR

The corpus cannot prove that no such task can exist: it proves there is **no oracle in this
repository** that can validate any change to the rule, and that the one proposed change is
refuted at the only scale where it is testable. **What would settle it:** a production IMS
carrying a FIXED_DURATION activity on an off-pattern crew **with no project-calendar
co-booking**, alongside MS Project's own stored dates for it. Until such a file exists in the
corpus, the census test names the population, and a sixth row appearing in it is the signal to
re-read this ADR. Do **not** re-chase the window rule without one.

## Verification

* **The census, run over all 15 goldens through the engine's own `_task_shape`** — population 5
  rows / 1 task, pinned by name and file.
* **Red first / mutation battery: control green, 6 of 6 mutants red BY NAME** on a shadow copy
  of `src/` (a `-p mutcheck` plugin asserts the modules measured ARE the copy):
  M1 R-61's proposed rule → 3 red · M2 the crew calendar never resolved → 10 red ·
  M3 ADR-0491's gaps not honoured → 1 red · M4 the legs sorted earliest-first → 1 red ·
  M5 ADR-0476's pin cut → 5 red · M6 `_recorded_span` reading elapsed minutes → 2 red.
  Every one of the module's 10 pins is red under at least one mutant; none is a test that
  could never fail.
* **The battery caught a hole in this unit's own first cut**, and it is the finding worth
  carrying: the census originally re-implemented the plan builder's three leg-calendar lines
  inside the test. It was **green under M2** — the mutant that breaks exactly that resolution —
  because it was measuring the re-implementation, not the engine. Re-aimed onto `_task_shape`,
  it goes red. A parallel implementation in a test is an oracle for itself.

## Refused, and named

Reading a WORK booking's recorded window (refuted above, and already refused by ADR-0487 for its
own reasons) · running a FIXED_DURATION leg on the task's axis (refuted, §4) · changing
`engine/` on a witness that no golden can discriminate · renumbering or relaxing any ADR-0474 /
0476 / 0487 / 0491 pin to accommodate either candidate · a `src/` comment in place of the
executable tripwire (prose is what this repo's own audit calls load-bearing data with nothing
asserting it is still there).
