# ADR-0524 — A late START is a start-role instant on the WALL path too, the blocker that deferred it died at ADR-0523, and the rule has no duration exception (R-69 CLOSED)

**Status:** Accepted · **Date:** 2026-09-22 · **Extends:** ADR-0348 (the day-boundary start/finish spelling), ADR-0523 / R-77 (the same rule one segment down, on the offset path) · **Closes a residual of:** ADR-0510 / R-67 (UID 147's carried Saturday instant), ADR-0512, and R-57's "named rather than counted" 60 minutes on UID 379 · **Row:** R-69 (T3, S) in `docs/STATE/AUDIT-2026-08-27-REPORT.md` §3

## Context

Roadmap row R-69 (T3, S). The row read:

> a wall-path task's late START is written at the END of a working block where MS Project writes
> the START of the next one (ADR-0510): `_retreat_wall` lands a block-exact retreat on the block's
> end (`_tod_at_worked`), so Hard_File UID 178 reads 08-04 **12:00** for the stored **13:00** …
> **742** late starts across the 44 files differ from the stored instant by this form alone (166 on
> Large_Test_File, 14 on Hard_File, 9 on updated), no slack and no late finish among them. NOT a
> one-line fix: the contiguous projection (`_wall_to_offset`, ADR-0322's two-ruler rule) of the
> 13:00 form reads 300 where 12:00 reads 240, so every project-calendar PREDECESSOR would inherit
> the lunch hour as float.

**The mechanism is exactly right. Its named witness is exact. Its population, its "no slack and no
late finish", and above all its BLOCKER are not.**

### The blocker died five commits ago

The row was written 2026-08-27. ADR-0523 landed 2026-09-22 and made `datetime_to_offset`
segment-aware; `_wall_to_offset` delegates to it, so it moved too — by construction, as ADR-0523's
own handoff records. Measured on this tree, on Hard_File's Standard calendar:

```
_wall_to_offset(ps, 2026-08-04 12:00) == 9360
_wall_to_offset(ps, 2026-08-04 13:00) == 9360      # the row predicts 240 vs 300
```

Both spellings are the **same working minute**, so re-spelling a late start cannot move an offset,
cannot move a link bound, and cannot hand any predecessor the lunch hour as float. The one sentence
that priced this row as "NOT a one-line fix" describes a tree that stopped existing. It is now
pinned by `test_the_projection_cannot_tell_the_two_spellings_apart`, so the day it stops being true
the arithmetic goes red instead of quietly wrong.

`_wall_to_offset`'s docstring still called itself "the CONTIGUOUS canonical ruler" and "deliberately
asymmetric" — prose describing the pre-ADR-0523 tree, and the direct source of this row's mispricing.
Rewritten here: documentation is in QC-2's scope, and this is what stale prose costs.

### The population does not reproduce, and the row measured a different surface

The 44-file corpus was rebuilt (29 path-keyed MPXJ conversions + the 15 committed goldens, 11 of
them gzipped) and reproduces **22,105 scheduled activities** exactly, so the instrument is the same
one ADR-0513 and ADR-0523 used. Classified on each task's OWN execution axis
(`_execution_plans(...)[tid].axis` — the calendar the engine measures that task's slack on):

| R-69 claims | measured on `TaskTiming.late_start_wall` | |
| --- | --- | --- |
| **742** late starts in the class | **47** | does not reproduce |
| **166** on Large_Test_File | **0** | does not reproduce |
| **14** on Hard_File | **10** | does not reproduce |
| **9** on Hard_File_updated | **5** | does not reproduce |
| "no late finish among them" | **24 late finishes** in the same class | **false** |
| Hard_File UID 178 reads 12:00 for a stored 13:00 | **exact** | the named witness holds |

**Where the row's 742 most likely came from.** An independent reconstruction on pinned v1.0.275 /
v1.0.286 / v1.0.287 extracts re-derived the 47 and the 24 exactly (49 and 26 before separating the
two instants that land on a non-working day), and found that the row's figures track a *different*
surface: a RENDERED oracle — `offset_to_datetime(project_start, tm.late_start, calendar)` against the
stored LateStart, over all 22,105 activities — reads **659** on v1.0.275, the tree the row was
registered against, with **149 per copy** for Large_Test_File against the row's 166. Neither 742 nor
166 is reproduced by any of the 24 oracle×class combinations tried. The row's prose names
`_retreat_wall`, which is the wall path; its numbers do not come from there.

That rendered oracle is worth naming precisely because it is **not** a display defect: `late_start`
and `late_finish` have **zero consumers anywhere in `src/` outside `cpm.py`**, so nothing in the
product renders a late start at all. This row's value is parity fidelity against the reference tool's
stored dates (Law 2), plus the one user-visible figure it corrects — UID 379's total float. Most of
Large_Test_File's rendered disagreement is a different class again: 1,279 instants at `17:00 → 08:00`
on the following day, which is ADR-0348's DAY boundary, not this row's segment boundary.

Large_Test_File's 251 wall-path late starts contain **no** instance of the class at all: its
disagreements are 36 at −1 minute (R-65's sub-minute family, held) and the large negatives of the
completed-record class (R-71's). A first census of my own read **38** rather than 47 because it
filtered on "the same working minute on EVERY calendar in the file" — Hard_File carries 24-hour
crews with no lunch gap, so the filter excluded the very rows it was built to find. Every crude
filter under-reports, in the direction that makes the work look done.

### The rule, measured from the files rather than assumed

The row names a direction but never measures it. Read from the files' own stored values — an oracle
independent of this engine, which is the point — over every instant landing on an internal block
boundary of the task's calendar:

| stored field | earlier (block END) | later (block START) | convention |
| --- | --- | --- | --- |
| **LateStart**, non-milestone | 26 | **754** | **LATER**, 96.7 % of 780 |
| **LateFinish**, non-milestone | **880** | 31 | **EARLIER**, 96.6 % of 911 |
| EarlyStart | 121 | 309 | LATER, 71.9 % |
| EarlyFinish | 482 | 3 | EARLIER, 99.4 % |
| milestone (LS and LF are one instant) | 58 | 54 | **no dominant form** |

The start/finish role rule ADR-0348 found at the day boundary and ADR-0523 found at the segment
boundary holds on the BACKWARD pass too — and holds *harder* there (96.7 % against the early dates'
71.9 %). `_snap_back_to_working` was already documented as the FINISH role; the START role simply
had no counterpart on the wall path.

## Decision

`_snap_start_role(wall, cal, day_start_tod)` returns the START spelling of an instant sitting on an
internal block boundary — the segment-level twin of `_snap_back_to_working`, and the wall-path twin
of `offset_to_start_datetime` vs `offset_to_datetime`. The backward pass applies it to `ls_w`, and
**never** to `lf_w`.

It deliberately does nothing at the day's first start or last end (that is ADR-0348's grid point,
not this one), on a non-working day, or on a calendar that declared no segments.

### The duration exception was in the first cut, and a mutation test refuted it

The rule shipped here has **no** zero-duration exception. The first cut had one, on the reading that
a milestone's single instant carries both roles and the corpus splits 58 / 54. The mutation battery
refuted it: removing the guard reddened nothing, because the 58 / 54 population is instants the FAST
path carries (`_carried_late_instant`), which this seam never reaches. Of the zero-duration instants
it *does* reach, **5 of 5** with a determinate stored answer take the later form, and the guard broke
all five to save none. A static simulation had priced the guard at +9 / −36; the live engine priced
it at +0 / −5. The simulation mis-modelled which code path those milestones take — measure the
engine, not a model of it.

The general milestone ambiguity remains ADR-0523's **named residual**, not a rule invented here.

## What it measured

Pristine → this tree, 44 files, 22,105 activities, against MS Project's own stored values:

* wall late-START instants exact **1,628 → 1,698**; wall late-FINISH instants exact **1,728 → 1,755**
* stored Total Slack exact **10,568 → 10,572**; goldens-only **4,098 → 4,100**
* per activity: **70** late starts and **27** late finishes moved **TOWARD** the stored instant and
  **NONE moved away**; 4 total floats moved, all 4 toward, none away
* **no early instant moved at all** (0 of 22,105), no free float moved, no `is_critical` moved

Three residuals registered by earlier rows close as a consequence, without being touched directly:

* **UID 147's carried Saturday instant** (ADR-0510's named residual, explicitly registered to this
  row) — it is 178's late start less 72 **elapsed** hours, so re-spelling 178 carries it to the
  stored Saturday 13:00. The milestone itself is never re-spelled; its driver is.
* **UID 379's 60 minutes**, which R-57 recorded as "closer, not exact, and named rather than
  counted": 17,521 → **17,581**, exactly MS Project's stored 175,810 tenths. The lunch hour had been
  float, which is the row's mechanism landing where the row did not look.

## How it was verified

**Red first, by name: 9 of 14 red on the pristine tree, 5 green as designed** (the projection claim,
MS Project's own convention, the fast-path milestone control, the late-finish-keeps-its-form control,
and the no-early-instant control are all true before the change and must stay true after). 14 of 14
green after.

**Mutation battery 7 of 8 red by name** — the duration guard re-added · the role inverted (`lf_w`
re-spelled too) · the non-working-day guard removed · the declared-segments guard removed · the day
edge re-spelled · the call removed · the helper neutered. **The eighth survived and that was a
finding about the CODE:** a redundant `is_24x7` short-circuit, already covered by the
`len(segments) < 2` test. Removing it was proven byte-identical across all 22,105 activities, so it
is gone rather than left as a branch no check can reach.

The two mutants that survived the FIRST battery (the duration guard, the role) each exposed a
toothless test, not a safe rule: the milestone pin was vacuous with respect to the guard it was
meant to protect. Both were replaced with witnesses measured from the mutants' own diffs.

## Pins moved deliberately, each with its reason and prior value

* `test_free_float_bounded_by_total.py` — golden total-slack exact **4,098 → 4,100**; both movers are
  UID 379 (Hard_File, Hard_File_updated). Free slack `(1142, 1075, 40, 27)` **unmoved**.
* `test_segment_aware_axis_pair.py` — the same `(4559, 4098) → (4559, 4100)`.
* `test_r57_assignment_leveling_delay_oracle.py` — UID 379 `total_float == 17521 and stored == 17581`
  becomes `total_float == stored == 17581`; the row's own "named rather than counted" residual.
* `test_r58_calendar_intersection_oracle.py` — 147's carried instant `12:00 → 13:00` and 178's late
  start `12:00 → 13:00`, both now equal to the file's stored values. The load-bearing relation (147
  == 178's late start less 72 elapsed hours) is unchanged; only the spelling of both moved.
* `test_hard_file_stored_dates_oracle.py` — 178 / 179 / 180's late start `12:00 → 13:00`; 147's
  carried instant folded onto `stored_lf[147]`. The late FINISHES there are untouched by design.

## Deliberately NOT done

* **The 24 late finishes in the mirror class.** MS Project spells a non-milestone late finish with
  the EARLIER form on 880 of 911, so the engine is already right on the convention; the 31 later-form
  late finishes are a minority with no discriminator measured. Applying the start form to `lf_w`
  breaks **52** already-exact late finishes — pinned as `test_the_late_finish_keeps_the_finish_form`.
* **The milestone spelling in general** (58 / 54 corpus-wide, 29 / 25 on the goldens). No rule in the
  files separates them; ADR-0523's residual stands.
* **The ±1-minute class** (R-65's family) and the completed-record class (R-71's) — both visible in
  Large_Test_File's late-start deltas and neither this row's.
* **Reconstructing the instrument behind the row's 742 / 166 / 14 / 9.** No oracle constructed here
  reproduces them, and this is stated as a failure to reconstruct, not as proof the row was invented.
