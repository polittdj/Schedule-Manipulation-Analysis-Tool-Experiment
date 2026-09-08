# ADR-0476 — A completed activity occupies exactly its recorded window (R-55, closing ADR-0391's named half)

Status: accepted (2026-09-08)

## Context

ADR-0391 made a recorded `actual_start` a forward **floor** and named, in its own module docstring,
the half it was leaving open:

> **Deliberately NOT done:** anchoring a completed task's actual FINISH. Its start is now honored,
> but its finish is still `start + duration` […] the remaining half of the completed-task anchoring
> gap.

That half is roadmap row **R-55** (`docs/STATE/AUDIT-2026-08-27-REPORT.md` §3, T1, priced M). It is a
T1 row — a figure an analyst would cite is wrong — because the artefact is not subtle: on
`Hard_File_updated3` twenty-one completed activities were scheduled **past** the date the file
itself records them finishing, worst **+38 days**, and on `Hard_File_updated3_24hr` fifty were. A
floor cannot fix any of them in the other direction either: an activity that finished **early**
computes `start + duration` and a floor may only push later.

### The oracle, measured before a line was written

Every MSPDI carries MS Project's own stored `Start` / `Finish`. Across six progressed goldens:

| | population | agreement |
| --- | ---: | ---: |
| completed activities: stored `Finish` == `ActualFinish` | 2,289 | **2,289 / 2,289** |
| started activities: stored `Start` == `ActualStart` | 2,601 | **2,601 / 2,601** |

Not "mostly". Every one. The reference tool does not *schedule* completed work at all — it
transcribes it — so pinning both ends of a completed activity reproduces MS Project by
construction rather than by fitting. This is the same oracle ADR-0474 used to close R-44, applied
to the rows R-44 deliberately left alone.

## Decision

**A completed activity occupies exactly its recorded window.** Where `is_recorded_complete` holds —
`percent_complete >= 100` **and** `actual_start` present **and** `actual_finish` present — the early
start is **pinned** at `actual_start` and the early finish **pinned** at `actual_finish`, in both
forward-pass branches (project axis and own calendar). Completed work is history: `start + duration`
is a *prediction of* a span the file already measured.

`_actual_finish_bounds` is the fourth and last member of the stored-date family
(`_stored_date_bounds`, `_resume_bounds`, `_actual_start_bounds`) and the only one that is a **pin in
both directions**. That licence is granted for one reason: a completed activity's dates are not a
schedule, they are a measurement.

Pinned UniqueIDs are reported on a new `CPMResult.actual_finish_driven`, the sibling of
`actual_start_driven` and deliberately **not** merged into `date_driven` — for exactly ADR-0391's
reason, that a transcribed record is evidence, not a date logic cannot support, and merging it would
emit a false manipulation signal on every progressed schedule.

### What is deliberately NOT pinned, and the measurement that decided it

**Work still IN PROGRESS keeps ADR-0391's floor.** Its start is a record but its finish is a
forecast. Three candidate rules were built on scratch copies and measured against the whole golden
corpus before one was chosen — the choice is the measurement's, not the author's:

| variant | updated3 | 24hr | per-task, vs pristine | verdict |
| --- | ---: | ---: | --- | --- |
| pin every started start + pin completed finish | −13 d | −2 d | 254 better / **60 worse** | **rejected** |
| pin *completed* start only, no finish pin | −13 d | −2 d | 199 better / 42 worse | **rejected** |
| **pin completed start AND finish** | **−13 d** | **−2 d** | **244 better / 37 worse** | **adopted** |

The first variant's cost is one number: `Large_Test_File` **UID 1489** (95 % complete, started out
of sequence) moved from 26 days early to **162 days early** — a 136-day swing in the direction Law 2
forbids — dragging five downstream activities with it. Pinning an out-of-sequence *in-progress*
start lets the network pull earlier; flooring it cannot.

**The two halves must also ship together.** The second variant — a completed start pinned while its
finish stayed `start + duration` — moved `Large_Test_File` UID 7113 from **exact** to **85 days
early**. Pinning one end of a window and computing the other is worse than computing both.

The 37 remaining "worse" rows under the adopted rule are all `percent_complete == 0` activities
downstream of the residual below; none is a new defect (see *What this exposed*).

## Verification

**Corpus (engine vs MS Project's stored dates), pristine → this ADR:**

| golden | project finish | disagreements | engine-LATE | completed activities past their record |
| --- | ---: | ---: | ---: | ---: |
| Hard_File / _updated | −1 d / −1 d (unmoved) | 43 / 21 (unmoved) | 0 / 0 | 0 → 0 |
| Hard_File_updated2 | −1 d (unmoved) | 39 → **27** | 13 → **0** | 13 → **0** |
| Hard_File_updated3 | −6 d → **−13 d** | 76 → **52** | 31 → **0** | 21 → **0** |
| Hard_File_updated3_24hr | **+17 d → −2 d** | 75 → **14** | 68 → **0** | 50 → **0** |
| Hard_File_updated4_24h | **+17 d → −2 d** | 75 → **14** | 68 → **0** | 50 → **0** |
| Large_Test_File | −1 d (unmoved) | 188 → **173** | 32 → 21 | 11 → **0** |
| Large_Test_File2 | 0 d (unmoved) | 180 → **150** | — | — |
| Large_Test_File_Leveled | −1 d (unmoved) | 187 → **172** | — | — |
| **Project2 / Project5** | **0 d / 0 d — UNMOVED** | **0 / 0 — UNMOVED** | 0 / 0 | 0 / 0 |

**No completed activity anywhere in the corpus is now scheduled past the date its file records.**
The family absolute error over the eight Hard_File/LTF rows falls from 45 days to 22.

**Float and Critical against the same stored oracle — nothing degrades:**

| golden | Critical agreed | stored TotalSlack exact |
| --- | --- | --- |
| Hard_File / _updated / _updated2 | 108 / 110 / 80 of 110 — unmoved | 3 / 52 / 8 — unmoved |
| Hard_File_updated3 | 96 → **103** of 110 | 6 → **9** of 68 |
| Hard_File_updated3_24hr | 62 → **70** of 110 | 0 → **4** of 19 |
| Large_Test_File / _Leveled | 1682 / 1676 of 1723 — unmoved | 842 / 780 of 1022 — unmoved |
| Project2 / Project5 | 124 / 126 and 126 / 126 — unmoved | **65/65 and 95/95 — exact, unmoved** |

**The named arbiter is unmoved.** The SSI driving-slack goldens, `test_ssi_leveled_uid152`,
ADR-0391's Fuse TP4 v5 / TP1 pins, `test_progressed_finish_fidelity`, the three ADR-0391/0467
actual-start modules and `test_cpm_stored_dates` — 58 tests — are green before and after.
`pytest -m parity` is green (96 selected); `tests/engine` + `tests/parity` together, 1,213 passed.

**Red first.** The 18 tests of `tests/engine/test_recorded_completed_window.py` were observed to
fail 18 / 18 on the pristine engine, together with the four re-measured oracle rows.

**Mutation battery — 15 / 15 caught RED BY NAME**, each on a fresh scratch copy under `PYTHONPATH`,
with the repo tree md5-verified unchanged: the finish pin removed from each branch; the completed
start reverted to a floor in each branch; each of `is_recorded_complete`'s three tests dropped; the
disclosure merged into `date_driven`, and never reported; the bounds map emptied; the window-order
guard dropped; the pin reading `actual_start`; and ADR-0309's resume floor allowed to override a
completed record; DCMA-12's target filter removed; and the backward-pass recorded-span retreat
reverted in each branch.

**Six of those fifteen came back GREEN across the runs, and each was a finding about the TEST.**
They are recorded because that is the point of the exercise: the own-calendar start-pin, the
`percent_complete >= 100` test, the window-order guard and the resume-floor precedence were all
covered only by fixtures that could not distinguish the rule from its mutation. A corpus census
explains why — across **every** committed MSPDI golden there are **zero** part-complete activities
carrying an `ActualFinish`, **zero** completed activities with `resume > stop`, and **zero**
inverted actuals. Those three branches are pinned by hand-authored synthetic rigs, named as such
in the test module, because no committed fixture can reach them.

## Two defects the pin exposed in code that had to move with it

Neither was caused by this change; both were latent behind an engine that could not read a
recorded finish, and both are fixed here because shipping the pin without them would ship a
wrong number.

### The backward pass must retreat by the span the forward pass PLACED

A recorded-complete activity occupies the window its file records — what the work *took*.
`duration_minutes` is what it was expected to take, and on any activity that ran long or short
the two differ. The backward pass still retreated by the planned duration, so `LS - ES` and
`LF - EF` disagreed and ADR-0463's `min()` of the two reported **spurious negative float on work
that is already finished** — measured at **-13 working days** on a completed activity, which also
dragged it onto the critical path and failed DCMA-12 and DCMA-13. Fixed in both branches: the
fast path retreats by `early_finish - early_start`, and the execution-plan path by
`_retreat_wall` over the recorded span on the task's own axis rather than by the plan's legs.
Float in the past is not a forecast, but it must at least be self-consistent.

**The goldens are byte-identical across this fix** — Critical and stored-slack agreement
unchanged on all nine — so it is scoped to the pathological case it was found in.

### DCMA-12 may not inject its delay into work that has already finished

`_critical_path_test` delays the lowest-UID critical activity and requires the project finish to
move by exactly that delay. Once a completed activity is pinned it is **immovable**: the finish
cannot move, and *should not* — you cannot delay work that is done. The check would then report a
broken critical path for a reason that has nothing to do with logic continuity. The target set now
excludes `is_recorded_complete` activities.

Scoped to that predicate rather than to `percent_complete >= 100` because the disqualifying
property is being **immovable**, which only the pin confers; a task reported complete but carrying
no actuals is still scheduled by logic and stays a valid target. Measured: the filter changes the
chosen target on exactly one golden — **Project2, UID 26 -> UID 29, excluding 2 of 43 critical
candidates** — and DCMA-12's verdict and counts are byte-identical on every golden.

## The synthetic battery: a fixture whose progress data had never been read

`tests/test_projects/test_pass_fail_battery.py`'s `clean_program` went from 41 passing to 9
failing. Every one traced to the fixture, not the rule. Its three completed leaves each record an
**8-working-day window against a declared 10-day duration**, and each **starts before its
predecessor finished** (a 7-calendar-day stagger — 5 working days — against 10-day tasks). The
pre-ADR-0476 engine ignored `actual_finish` entirely and its actual-start floor never bound (an
out-of-sequence start is EARLIER than logic), so **the fixture's progress data was inert and the
contradiction invisible**; its docstring's claim to be "progressed consistently" was false and
nothing could detect it.

The oracle settles who is right. Across the real corpus, out-of-sequence completed work is rare —
2, 2, 1 and 3 cases on updated3 / _24hr / LTF / LTF2 — and in **8 of 8 MS Project's stored Start
equals the ActualStart**: the reference tool honours the record even out of sequence. And the pin
introduces **zero** new negative float on any real golden: 269 engine-negative against MS Project's
own 423, sign agreement 4,369, engine-only 18 — *identical* before and after.

So the fixture was left as it is and its expectations re-measured, with the reason recorded at each
one: the CPM forecast leg 2026-12-04 -> 2026-11-17 (the stored-date leg is the control and does not
move), the wide program's negative-float count 0 -> 16 (UIDs 200-215, the predecessors of the
out-of-sequence merge point), DCMA-09's collateral gaining DCMA-13 (its seed moves a completed
actual finish ten days past the data date, which is now real scheduling input — before, the seeded
date was inert on the network, so the check could not see the very thing the seed injects), and
the forecast test's "the pure-logic answer stands still" claim, which was true only of an engine
blind to completion. Three redesigns of the fixture were measured and rejected first: they moved
the completed work and cascaded into the EVM and forecast pins (**16 and 7 failures against this
version's 3**).

## What this exposed, and what it did not fix

`Hard_File_updated3`'s project finish moves **further** from MS Project's, −6 d to −13 d. That is
not a regression this ADR introduced; it is a second defect this ADR stopped masking. The
pre-ADR-0476 engine pushed 31 activities on that file **later** than MS Project has them, and that
spurious lateness was partly cancelling an understatement underneath. Every per-activity measure
improves; only the composed project finish moves, and it moves because the compensation is gone.

The underlying cause was traced, not assumed. Of updated3's 52 remaining disagreements, seven are
chain heads (every predecessor already agreeing) and 45 are inherited from them. The two heads that
carry the 15- and 13-day gaps are **UID 385** and **UID 403** — both `percent_complete == 0`, both
starting on exactly the right date, both finishing far too early:

| UID | duration | engine span | MS Project span |
| --- | ---: | --- | --- |
| 385 "Determine success metrics" | 5,664 min | ~6 working days (944 min/d) | ~17 working days (**333 min/d**) |
| 403 "Acquire executive sign-off" | 1,920 min | ~5 working days (384 min/d) | ~14 working days (**137 min/d**) |

That is **R-56** — the contoured / part-time booking residual, HELD — and it is a duration-contour
defect on *unstarted* work, so no progress rule can touch it. Note for the roadmap: the report names
only UID 403; **UID 385 is the larger driver**, and there are seven heads rather than one.

A data-date hypothesis was constructed and **refuted**: `Hard_File_updated3` carries
`StatusDate 2026-10-12T17:00`, and the engine starts only 5 of its 68 unstarted activities before it
(MS Project: 0) — just 1 of the 50 disagreeing ones. A data-date floor would close one row of fifty.

The two remaining heads, **UID 300** and **UID 323**, are the "milestone snaps", and the mechanism is
now measured rather than described: a recorded instant is converted to the working-minute axis, and
an `actual_finish` that falls at a day boundary or on a non-working instant cannot round-trip.
`UID 323`'s `Wed 2026-08-19 08:00` has zero elapsed working minutes on the 19th and renders back as
`Tue 08-18 16:00`; `UID 300`'s **Sunday** `08-30 04:00` clamps back to `Fri 08-28 16:00`. It is **not
milestone-specific** — UID 292, not a milestone, loses an hour the same way (17:00 → 16:00, date
intact). Only the day-boundary and non-working cases lose a whole day: 2 of 42 completed activities
on updated3, 19 of 699 on Large_Test_File. Carrying the raw instant would mean populating the wall
fields on the project-axis path, which today *signal* "off-calendar task" throughout the codebase —
a structural change, not this row's.

## Consequences

- ADR-0391's named residual is closed; `cpm.py`'s module docstring states the new rule, the
  in-progress exception and the two measurements that decided them, in place of the old caveat.
- `CPMResult` gains `actual_finish_driven`. Consumers that need real per-task dates may keep reading
  the stored ones first (`driving_slack.py`); they now agree far more often.
- `tests/parity/test_hard_file_stored_dates_oracle.py`'s pins were **re-measured, not re-fitted**:
  updated3's tolerance 6 → 13 d with its finish-within-a-day floor 42 → 60 and Critical 96 → 103,
  updated2's 87 → 93, Large_Test_File 1558 → 1569, Large_Test_File2 1563 → 1589 and stored-slack
  655 → 668. Its docstring says which row loosened, why, and that closing R-56 is what tightens it
  back — so no future session can read the 13 as a licence.
- **R-55 is CLOSED-0476.** R-56 is unchanged and now better specified (add UID 385; seven heads).
  A new residual is registered: the working-minute axis cannot carry a recorded instant that lands
  on a day boundary or a non-working moment.
