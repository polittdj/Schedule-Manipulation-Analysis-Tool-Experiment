# ADR-0252 — base-CPM single-calendar fail-soft disclosure (#26)

## Status

Accepted. Standing queue item **#26**. An additive, read-only **disclosure** — it changes no
computed number, no engine behavior, and no parity target.

## Context

Two established decisions set up a silent mixed basis:

- **ADR-0028** — the engine's base CPM models **one** schedule-level calendar
  (`schedule.calendar`). The forward/backward pass never consults a task's `calendar_uid`
  (confirmed: `engine/cpm.py` references `calendar_uid` nowhere).
- **ADR-0118** — per-task calendars *are* honored, but only by the driving-slack / SSI path
  (and by per-task Gantt shading, ADR-0243/0382).

So on a file that assigns some activities their own calendar, the base-CPM dates/float/critical
path are computed on the single **project** calendar — a single-calendar approximation for those
activities — with **no disclosure**. The `/analysis` "Working calendar" panel presented only the
one project calendar (its own docstring: "every computed date, float, and day-denominated
threshold rides this calendar"), letting the analyst read that single row as the whole time basis.

This gap was surfaced and queued during the ADR-0251 audit's mixed-basis sweep. It is independent
of **#13** (XER per-task calendars, parked pending the operator's real `.xer` files): #26 is
testable **today** against the committed, non-CUI leveled Large Test File (project calendar
"Dynetics Standard"; some activities on "ZIN Project Calendar", a materially different holiday
set) and the single-calendar Project5 golden.

## Decision

Disclose the single-calendar basis; do **not** change the base CPM.

- **`engine.cpm.off_project_calendars(schedule) -> tuple[Calendar, ...]`** — the deduplicated,
  uid-sorted calendars carried by **active, non-summary** tasks whose **working pattern**
  materially differs from `schedule.calendar`. "Material" compares only the fields the date/float
  math consumes (`working_minutes_per_day`, `work_weekdays`, `holidays`, `working_days`,
  `day_segments`), order-independently; `uid`/`name` are identity, not pattern — so a re-ordered
  or duplicate-pattern registry entry never cries wolf. Fail-soft: a task whose `calendar_uid` is
  absent from `schedule.calendars` cannot be compared and is skipped (never over-claims a
  divergence). Pure and read-only.
- **`_calendar_panel` disclosure** — when `off_project_calendars` is non-empty, the panel adds a
  `notice info` naming the off-project calendars and stating that the base CPM models the single
  project calendar (ADR-0028), so a date or float it computes (shown where the file carries no
  stored value of its own) is a single-calendar approximation for those activities, while the
  file's own stored dates and the Path Analysis / Driving Path views honor each task's own
  calendar (ADR-0118). Silent on single-calendar files.

## Consequences

- The analyst is no longer implicitly told the one project-calendar row is the whole time basis on
  a multi-calendar file. Honest mixed-basis disclosure, matching the ADR-0251 posture (name what a
  surface actually computes; never let one label imply more than it does).
- **No parity risk (Law 2).** The helper is read-only; the base CPM, driving-slack, and every
  metric are byte-unchanged — the `parity` gate stays green. Regression pins: the predicate
  (`tests/engine/test_off_project_calendars.py`: synthetic edge cases — same-pattern twin,
  summary/inactive exclusion, dangling `calendar_uid`, dedup/sort — plus real Leveled → ZIN and
  Project5 → none) and the panel (`tests/web/test_calendar_disclosure.py`: discloses on multi-cal,
  silent on single-cal).
- **Placement scope.** The disclosure lives on the canonical base-CPM surface (`/analysis`); the
  base-CPM float also feeds the DCMA / float-band panels on that same page, so one placement covers
  them. The SSI / driving-path pages already honor per-task calendars and need no disclosure.
- This does **not** make the base CPM multi-calendar. A true per-task-calendar base CPM is a much
  larger engine change (and, for XER inputs, still gated on #13's real reference files); if ever
  pursued it is its own ADR validated against a reference export — never a silent behavior change
  layered onto this disclosure.
