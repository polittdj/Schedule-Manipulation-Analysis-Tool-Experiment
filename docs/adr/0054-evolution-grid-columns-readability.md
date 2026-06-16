# ADR-0054 — Critical-Path Evolution: per-activity grid columns, readable names, hide-completed

Date: 2026-06-16 · Status: accepted

## Context

Operator asked for a set of usability enhancements to the **Critical-Path Evolution** view
(the Gantt stepper, ADR-0044/0048). This ADR covers the first, cohesive batch:

- per-activity **grid columns**: % complete, duration, start, finish;
- **smaller, wrapped** activity names (they were truncated at 30 chars);
- a **hide-completed** toggle — ADR-0051 explicitly deferred the evolution view's own
  hide-completed control to "the follow-on evolution-enhancements work", which is this.

(Zoom, target-UID focus, and filter-by-path are a separate follow-up PR.)

## Decision

**Server (`_evolution_data`).** Each Gantt row (both the critical rows and the dashed
"left the path" ghost rows) now carries three grid fields:

- `percent_complete` (int, rounded),
- `duration` (working days, e.g. `"12wd"`),
- `complete` — the robust flag from ADR-0051 (`is_complete` **OR** an actual finish), so a
  real `.mpp`/`.xer` reporting a finished activity at 99.x% still counts as complete.

For a row that **left** the path, the grid `%`/`duration` read from the **prior** version
(where the ghost bar is drawn), but `complete` reflects the **current** version — so an
activity that left *because it completed* hides under the toggle even though its prior-position
bar shows it still running.

**View (`path_evolution.js`).** The Gantt gains a left-hand grid (header row + columns:
Activity, %, Dur, Start, Finish) ahead of the bars. Names are no longer clipped — they wrap to
up to two small lines (`wrapName`, word-aware, last line ellipsized) prefixed with the UID. A
`hide completed` checkbox filters rows on the `complete` flag and re-renders, and the section
heading reports how many completed rows are hidden. Canvas widened (980→1180) and row height
raised (20→30) to fit the columns and wrapped names. Still dependency-free inline SVG
(air-gap posture intact).

## Scope / safety

Presentation + three additive row fields — no engine/CPM/attribution change; the
`compute_path_evolution` model and every existing evolution test are untouched. New tests pin
the grid fields on the API rows, that a left-because-completed row carries `complete=True`, and
that the page/JS expose the hide-completed control and the grid columns. Full suite green
(835 passed); ruff/format/mypy clean.
