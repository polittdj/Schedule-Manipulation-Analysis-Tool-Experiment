# ADR-0504 — The `/analysis` calendar disclosure names every calendar the base pass runs on — the crews' calendars, the derived intersections, the elapsed clock — read off the engine's own execution plans (R-59 CLOSED)

- **Status:** Accepted — 2026-09-17 (the plan-forward's R-59, the report's §3 row after R-58 / ADR-0503).
- **Version:** **1.0.270** (`src/` changed: `engine/cpm.py` gains one read-only public listing, `plan_calendars`, beside `off_project_calendars`; `engine/__init__.py` exports it; `web/analysis.py`'s `_calendar_panel` is rewritten from it; `web/app.py` re-exports the two new panel helpers. No model, importer, schema or calculation change). Wheel and the nine installers rebuilt in lockstep.
- **Extends:** **ADR-0474** (the crews' calendars the base pass honours — the thing the page never named), **ADR-0503** (the derived intersection, which now has a name on the page), ADR-0322 (task calendars in the base pass — the float axis the notice states), ADR-0492 (the precedent: a consumer that needs the plan builder's rule gets it under a public name in `cpm.py`, never a re-implementation), ADR-0028 / ADR-0118 (the sentence the page carried, and the one clause of it that was still true), ADR-0195 (the design system's Definition of Done, which this page change ran), ADR-0128 (the population the "of N" counts).
- **Shipped:** `CalendarUse`, `PlanCalendars`, `plan_calendars` (`engine/cpm.py`, exported); `_calendar_uses`, `_calendar_disclosure` and the rewritten `_calendar_panel` (`web/analysis.py`, re-exported by `web/app.py`); `tests/engine/test_plan_calendars.py` (12 pins, the Hard_File one derived from the file's own fields); `tests/web/test_calendar_disclosure.py` rewritten (7 pins, the Hard_File page sentence among them); the `off_project_calendars` docstring re-pointed; the closed R-59 row.

## Context — what the page said, and why it was false

R-59 read: *`off_project_calendars` and the /analysis calendar disclosure name task calendars only;
the crews' calendars the CPM now honours (ADR-0474) are undisclosed on the page, so the analyst reads
"single calendar" under a multi-calendar result* — first step *list the crew calendars a plan uses
beside the task calendars (uid-deduplicated) and pin the /analysis sentence on Hard_File*, oracle
*the sentence on the page*.

Two things were measured before a line changed.

**The page's sentence was not merely incomplete; it was false.** The Working-calendar panel's notice
read, verbatim: *"The engine's base CPM models the single project calendar (ADR-0028), so a date or
float it computes … is a single-calendar approximation for those activities."* ADR-0322 made the base
pass honour a task's own calendar, ADR-0474 made it schedule a WORK booking on the crew's, and
ADR-0503 made a task calendar meet a crew calendar on their intersection. The panel disclosed an
approximation the engine had not made for seven weeks — and "a disclosure that over-claims is worse
than none" (ADR-0502's lesson) applies to an over-claimed *limitation* exactly as it does to an
over-claimed *rule*: an expert reading it would discount every date on the page for nothing.

**The predicate cannot see the thing the row asks it to name.** `off_project_calendars` reads a
task's own `calendar_uid`; a crew's calendar reaches the plan through the *assignment's resource*, a
field the predicate never touches. Censused on the engine's own plan shapes over the 15 goldens
(`_plan_shapes`, never a re-implementation — the R-61 lesson):

| golden (project calendar) | what the page named (task calendars) | what the plans actually run legs on, off the project pattern |
| --- | --- | --- |
| **Hard_File** (Standard) | `24 Hours`, `Standard+Sat.` | **Customer Service Team** (25 activities), **Content Developer** (18), **Logistics** (1), **`Standard+Sat. ∩ Customer Service Team`** (1: UID 94) — none of the four named |
| the other six Hard_File snapshots | the same two | the same crews (24–26 / 19 / 1–2) and, on the two `24h` snapshots where the crew is round-the-clock, `Standard+Sat.` itself as UID 94's leg |
| Large_Test_File / File2 / the SSI copies (Dynetics Standard) | `ZIN Project Calendar` (+ `Overtime Schedule Calendar` on File2) | `ZIN Project Calendar` — 138 activities, 73 of them through crew legs that are ZIN by identity (183 legs) and 65 through a one-leg plan |
| Project2 / Project5 / EVM1 / EVM2 | nothing | nothing (single-calendar files — the page must stay silent) |

A tempting shortcut was priced and refused: listing `booking_calendar(schedule, task, a)` over every
assignment (the public per-booking rule, ADR-0492) **over-claims** against the plan — on the two
`24h` snapshots it names `24 Hours` on 9 bookings no leg runs on (three tasks under
`IgnoreResourceCalendar`, whose plans run on the task calendar), and on every snapshot it names the
Content Developer on UID 146, an ELAPSED task whose crew the plan builder ignores. The listing had to
read the plans, not the assignments.

## Decision

**1. One listing, in the engine, read off the execution plans.** `plan_calendars(schedule)` builds
the plans exactly as one un-overridden solve does (`_execution_plans` over `_scheduled_tasks` at the
stored durations — the shapes are derived once per schedule object, so this is cheap) and reports,
for every active non-summary task, the calendar its **total float is measured on** (`axes` — the
task's own, ADR-0474's slack axis; never the project calendar, never the elapsed clock), the
calendars its **execution legs run on** (`legs` — a crew's own calendar, a task calendar the crew
restricts nothing of, or their intersection), the tasks whose duration is **elapsed** (they run round
the clock; a duration property, not a calendar the file carries — counted, not listed), and the
**population** (ADR-0128's, the "of N"). A leg the plan builder drops (a zero-work booking, a
milestone's, a booking under `IgnoreResourceCalendar`, an elapsed task's crew) is not listed; a leg
it keeps is listed on exactly the calendar OBJECT it runs on, so a derived intersection is named
`<task> ∩ <crew>` and never as a parent. Deduplicated by object — every derived calendar shares uid
`-2`, so uid cannot be the key — registered calendars first in uid order, derived ones after by name,
one count per activity however many legs it runs there.

**Why the engine, when the design system says a UI change never touches `engine/`.** That rule
protects one property — no computed number moves under a presentation change — and this unit proves
it directly (below: the `/api/analysis` payload is byte-identical on three goldens; the parity gate is
unmoved). The alternative, the web layer importing the private `_plan_shapes` / `_execution_plans`,
would have been the first private engine name ever imported by `web/` (there is no precedent; the
one aliased import in `web/state.py` is of a public name), against the repo's own precedent that a
disclosure predicate lives in `cpm.py` (`off_project_calendars`) and that a consumer needing the plan
builder's rule gets it under a public name there (ADR-0492's `booking_calendar`). The operator may
overrule the seam; moving a 40-line read-only function is trivial and nothing else depends on where
it lives. `off_project_calendars` stays — a public, eight-pin predicate — with its docstring
re-pointed; the page no longer reads it.

**2. The panel says what the engine does, in the design system's voice.** On a multi-calendar file
the takeaway (`sf-take`, a sentence with its numbers) reads, on Hard_File: *Standard (8 h/day, a
5-day work week, 0 holiday(s)) is the time basis for 65 of 110 activities; the other 45 run wholly or
partly on 6 other calendars, named below.* The notice then names each calendar with the activities it
touches, in three sentences the engine's structure dictates — the task calendars *("2 activities carry
a calendar of their own, and their total float is measured in that calendar's working minutes
(ADR-0322 / ADR-0474): 24 Hours (1), Standard+Sat. (1)")*, the leg calendars *("44 activities have a
booking scheduled on the calendar the task and its crew share — the crew's own calendar, the task's
when the crew restricts nothing it works, or their intersection (ADR-0474 / ADR-0503): Customer
Service Team (25), Content Developer (18), Logistics (1), Standard+Sat. ∩ Customer Service Team (1 —
UID 94; a derived calendar: the working time the task calendar and the crew calendar share)")*, the
elapsed count — and closes with the float-axis rule (MS Project's stored-slack basis, ADR-0474) and
the one clause of the old sentence that was still true (the path views measure a link's float on the
successor's calendar, ADR-0118). A derived calendar cites its activities (up to five UIDs) because it
is the one line the analyst cannot open in the source tool. **On a single-calendar file the panel is
byte-identical to before** — no notice, the old takeaway verbatim (Project5 renders identically end
to end). The `/api/analysis` payload is untouched: its `calendars` list is the file's registry, and a
derived calendar is never registered (ADR-0503).

## What it measured

| render, pristine → this tree | `/analysis` page | `/api/analysis` |
| --- | --- | --- |
| Hard_File | **2 lines** differ — the takeaway and the notice, nothing else | byte-identical |
| Large_Test_File | the same 2 lines (*"1585 of 1723 activities; the other 138 … 1 other calendar"*, ZIN 138 / 138) | byte-identical |
| Project5 | **byte-identical** | byte-identical |

Rendered in a real Chromium at 1440 px (the `/analysis/Hard_File` page, the panel located by its
heading): no page errors; `scrollWidth == innerWidth == 1440` in all four themes (the R-20 / ADR-0477
contract holds); the notice's colour, tint and border differ per theme (console / daylight / apollo /
jarvis read four different token values — nothing styles itself); the notice measures 148 / 127 / 190
/ 148 px tall on a 1148 / 1384 / 1148 / 1148 px panel. Observed and not this row's: in daylight the
page's fixed telemetry HUD (CPU / RAM / GPU / DISK) overlays the right edge of every full-width panel
at 1440 px — pre-existing chrome, named in the handoff's residuals.

## How it was verified

* **Red first, in a separate worktree at `origin/main` (`a95482c1`).** Both new modules cannot
  import (`plan_calendars` / `CalendarUse` do not exist). Probed with the import bypassed, the
  pristine panel is **silent** on a crewed project-calendar task (no notice at all — nothing about
  the task says "16 Hour Work Days") and on a task-calendar task carries the "single-calendar
  approximation" sentence, cites ADR-0028 and names neither the crew's calendar nor the intersection.
  The web module's docstring states exactly that, from the probe, not from the assumption it was
  first written with.
* **The rig was refuted three times before the engine was — the same class each time, an unstated
  population filter.** The Hard_File pin derives its expectation from the XML's own fields (each
  task's `Active` / `Summary` / `Duration` / `DurationFormat` / `IgnoreResourceCalendar` /
  `CalendarUID`, each assignment's `Work` / `Units`, each resource's `Type` / `CalendarUID`): (1) the
  first derivation counted crews 4 / 5 / 7, whose calendars the importer does not register because
  their pattern equals the project's — the test now asserts the registry as its premise and filters
  on it; (2) it excluded the elapsed UID 146 before the booking loop and then asserted the crew had
  booked it; (3) the Large Test File pin read the shape map, which covers every task, and met
  summary UID 5334 (a ZIN material leg on a task never scheduled) — the CPM population (ADR-0128)
  is now applied to the shapes explicitly. None of the three was the engine.
* **Mutation battery, 12 cuts on a shadow copy of `src/`** (a `-p mutcheck` plugin asserts the
  package measured IS the copy; every cut's file checksum changed; the control run green, 19 passed,
  before and after): M01 the listing always empty → **12** red · M02 dedup by uid (every derived
  calendar folds into one) → 1 · M03 the derived calendar named as its task parent → 5 · M04 the
  off-pattern filter dropped (the project calendar listed) → 2 · M05 elapsed tasks listed as an
  axis, never counted → 3 · M06 inactive / summary tasks in the population → 3 · M07 counted once per
  LEG → 2 · M08 the page ignores the listing → 3 (web pins only — the engine pins stay green, which
  is what proves the page pins are the page's) · M09 the stale single-calendar sentence restored → 2
  · M10 axes and legs swapped → 7 · M11 the derived flag never set → 5 · M12 the takeaway keeps the
  old sentence on a multi-calendar file → 2. **12 / 12 red by name, no survivor.**
* **Statics** green on both ruff binaries (0.15.8 and 0.16.8) over the whole tree, `ruff format`
  (1,271 files), `mypy --strict` (165 files), `bandit` (exit 0), `node --check` per file. The 141
  neighbouring tests (the monolith-split contract, `test_app`, the four calendar / intersection /
  booking-calendar engine modules) green.
* **The full gate**, measured in a separate worktree at this unit's code commit (never in the tree
  the docs were being written in): **5,553 passed / 1 failed / 7 skipped in 46:47** and **`-m parity`
  170 / 0 in 8:26**. The one failure is the handoff version-pin guard, red on the code commit's tree
  because that commit carried the bump without the rotated handoff (a wasted CI cycle on #694's
  first run — the lesson is in the log); the docs commit carries the pin and the final tree reads
  5,554 green. Attributed: 5,561 collected = 5,546 + 19 − 4; parity 170 = 170.

## Deliberately NOT done — registered, or named

* **A calendar table** (each listed calendar's hours / day, work week, holidays) beside the names.
  The row's oracle is the sentence; the table is a Library-page question for the operator's design
  queue. Named, not built.
* **A machine-readable `calendar_basis` in `/api/analysis`.** The payload is untouched by design
  (byte-identical is the proof no number moved); a derived calendar is never registered (ADR-0503),
  so the API's `calendars` list still carries the file's registry only. If the operator wants the
  disclosure exportable, it is one dict on the existing payload.
* **The elapsed clock as a calendar line.** An elapsed duration is a property of the task, not a
  calendar the file carries; it is counted in its own sentence, never listed beside `24 Hours`.
* **Retiring `off_project_calendars`.** No production caller remains, but it is public API with
  eight pins and the correct answer to a narrower question (which task calendars are in play). Kept,
  docstring re-pointed.
* **The notice's client-side translation.** As before, the notice is translatable and the takeaway
  is `data-no-i18n`; a model may reword the prose (the calendar names ride in `<b>` as they did).
  Unchanged exposure, unchanged posture.
* **The daylight telemetry HUD overlap** (above) — observed, pre-existing, named for the operator.
* **Refused, and named:** a per-booking `booking_calendar` listing as the source (over-claims: 9
  `24 Hours` bookings with no leg, the elapsed UID 146's crew) · re-implementing the plan builder's
  filters in `web/` (a parallel implementation is an oracle for itself) · importing `_plan_shapes`
  into `web/` (the seam argument above) · any change to the `_execution_plans` / `_task_shape` rule
  (the listing reads them; it never edits them).
