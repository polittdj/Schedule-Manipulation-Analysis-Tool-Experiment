# ADR-0051 — Hide-completed toggle: robust "complete" definition

Date: 2026-06-16 · Status: accepted

## Context

Operator: on Path Analysis the **"hide 100% complete"** toggle does not work — **completed
tasks still show** — and the hide-completed behavior should work **everywhere** it appears.

Root cause (confirmed with the operator): the toggles tested `percent_complete >= 100` in the
browser. Real `.mpp` / `.xer` exports routinely report a **finished** activity at **99.x%**
(MS Project rounding, XER quantity-based `CP_Units` percent) while still carrying an
**actual finish** date — so those done activities slipped past the `>= 100` test and stayed
visible. On the bundled goldens every completed task is exactly `100.0`, which is why it
"worked on the example."

## Decision

Introduce a single robust definition of "complete" for display filtering and compute it
**server-side** so every view shares it:

```
complete = task.is_complete or task.actual_finish is not None
```

i.e. an activity is complete if it reports ≥100% **or** it carries an actual finish (in MS
Project / P6 semantics an actual finish means the activity is done). The `complete` flag is
added to both row builders — the driving rows (`/api/driving`) and the activity rows
(`/api/analysis`).

The hide/dim logic now reads `r.complete` instead of `percent_complete >= 100`:

- **Path Analysis** (`path.js`) — the "hide 100% complete" filter, the done-row class, and
  the done bar styling; the partial-progress overlay is only drawn for genuinely in-progress
  rows.
- **Report trace** (`app.js`) — the "show completed" trace filter and the done bar styling.
- **Report grid Gantt** (`app.js`) — a complete activity fills its progress overlay to 100%
  even when it reports 99.x%.

## Scope / safety

Presentation-layer fix plus two additive row fields — no engine/CPM/data change; parity
untouched (10/10). On the goldens (all completed tasks at exactly 100%) the flag equals the
old test, so nothing visible changes there. A unit test pins the real-file case (actual finish
present at 99% → `complete = True`; not-started → `False`), and a view test pins that the rows
carry the flag and the JS filters on it. The Critical-Path Evolution view gains its own
hide-completed toggle in the follow-on evolution-enhancements work.
