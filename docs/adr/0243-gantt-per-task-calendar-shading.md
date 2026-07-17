# ADR-0243 — Gantt non-working shading follows each task's own calendar (Option B)

## Status

Accepted. Operator directive (2026-07-17): the Gantt's non-working-time shading must reflect
the calendar the schedule actually runs on, not a nominal project-level default. The operator
chose this ("Option B") after an exhaustive investigation showed the existing shading was
technically correct but misleading on a mixed-calendar file.

## Context

The operator loaded `Hard_File_updated4 24 hour calendar.mpp` and reported the Gantt's gray
weekend shading as "wrong." Investigation (headless Chromium + DOM/gradient probes + a
date-alignment test) established:

- The shading was **correctly aligned** — gray bands landed on real Saturdays/Sundays at every
  zoom (0/18 date mismatches), matching the file's project calendar, which POLARIS imports as
  "Standard" (Mon-Fri, 480 min/day — MPXJ confirms it is the project default). MS Project shades
  the same way by default.
- But the file is **mixed-calendar**: 105 of 110 non-summary tasks run Mon-Fri (the project
  calendar), 4 run on a "24 Hours" calendar, and 1 on "Standard+Sat." **All five non-Standard
  tasks are on the critical path**, and one of them — UID 389 "Certify new resources" — is the
  exact red-hatched bar in the operator's screenshot.
- So a weekend-working critical task (24-hour calendar) was drawn against gray "non-working"
  weekend shading, which reads as the task working during non-work time. That is the misleading
  behavior the operator saw.

A global default calendar cannot fix this: keying off the project default (Standard) leaves the
weekend gray; keying off the modal task calendar also gives Standard (105/110); blanking weekends
globally would be wrong for the 105 Mon-Fri tasks. The only correct realization is **per-task**.

## Decision

Shade each Gantt row's non-working time per **that row's own task calendar** (the operator's
"Option B" — "shading follows the calendar the schedule runs on," read per task):

- **Payload:** `_activity_rows` and the driving-trace rows now carry a `calendar` field — the
  name of the task's governing calendar, resolved `calendar_uid → registered calendar name`,
  falling back to the project calendar when the task has none (MS Project inheritance semantics).
  The name matches one the client already registers via `SFTimescale.setCalendars`.
- **Shading layer:** `SFTimescale.nonworkStyle(axis, cellCal)` / `decorateCell(cell, axis,
  cellCal)` and `SFGantt.paintNonwork(cell, axis, cellCal)` take an optional per-row calendar.
  Precedence: an **explicit** calendar picked in the Timescale dialog forces that one for every
  row (the MS-Project-style uniform backdrop); otherwise **Auto** (the new default) shades per the
  row's own `cellCal`; if a caller supplies no per-row calendar, it falls back to the project
  calendar — byte-identical to the previous behavior.
- **Dialog:** the Non-working-time "Calendar" picker gains an "Auto — each task's own calendar"
  option (value `""`), now the default.
- **Callers wired:** the `/analysis` activity grid and its driving-path trace, plus the
  standalone `/driving-path` page, pass each row's calendar. Other Gantts (path-evolution, SRA
  grid) keep the project-calendar fallback until their row payloads carry a calendar — no
  regression.

## Consequences

- **No-op for normal single-calendar schedules:** every task inherits the project calendar, so
  every row resolves to it and the shading is identical to before (verified on Project5 — all
  rows still shaded).
- **Correct on mixed-calendar files:** the 4 twenty-four-hour critical tasks (incl. the operator's
  UID 389) now render with no weekend gray, while the 105 Mon-Fri rows keep it — Chromium-verified
  per row.
- **Deviates from MS Project's naive global backdrop by design** — the operator accepted this
  trade for forensic truthfulness, and the dialog's explicit-calendar pick restores the uniform
  MSP behavior on demand.
- Engine, metrics, and parity are untouched — this is a presentation-layer change over the
  already-computed schedule; the `calendar` name is derived from the same `Task.calendar_uid` the
  driving-slack parity already consumes (ADR-0118).
