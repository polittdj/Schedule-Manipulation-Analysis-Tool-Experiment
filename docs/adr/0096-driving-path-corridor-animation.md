# ADR-0096 — Animated date-axis Gantt for the driving-path corridor

Date: 2026-06-19 · Status: accepted · Builds on ADR-0091 (driving path between two UIDs)

## Context

ADR-0091 shipped the driving path between two UIDs and its cross-version evolution, but the
`/driving-path` page rendered it only as server-side **chips + a textual diff**. The operator's original
ask (#2) wanted to see "how it changes over time" the way the Trend / Critical-Path-Evolution views
animate — a visual the chips didn't provide.

## Decision

Add an animated, scalable **date-axis Gantt** of the corridor to `/driving-path`, alongside the existing
chips (which remain as the no-JS fallback and the per-version reason diff).

- **Data (server).** `_driving_path_gantt(...)` enriches each version's `DrivingPathSnapshot` with the
  corridor activities' **dates** — reusing `date_basis` (stored dates, else the CPM forward pass) exactly
  as the Path Analysis grid does — plus the `entered` flag (new on the corridor vs the prior version) and
  milestone flag. The payload is embedded in the page as a `<script type="application/json" id=dpData>`
  (JSON with `</` escaped), so no extra endpoint and the view is fully testable from the HTML.
- **Render (`static/driving_path.js`).** Draws the current version's corridor as a name column + a
  px-per-day timeline track (month ticks, the gold data-date line), on a date range computed across
  **all** versions so the axis is held fixed and the corridor visibly shifts between frames. A
  prev/next/**auto-play** stepper walks the versions; zoom ± changes px/day; activities that **entered**
  the corridor are outlined (`.dp-entered`). Dependency-free; reuses the Path page's Gantt CSS.
- **Gating.** Shown only when there is more than one loaded version and at least one has a corridor;
  otherwise just the chips (a single version has nothing to animate).

## Consequences

- The "how does the corridor move over time" question now has the animated answer the operator expected,
  consistent with the Trend / Evolution visuals.
- All dates come from the same basis the Path grid displays, so bars line up with that view; nothing is
  fabricated.
- This clears the last *buildable* polish item. Remaining backlog is **blocked on inputs**: CEI /
  critical-path value-validation needs the CUI Acumen ribbon files re-attached; Float Ratio™ / composite
  Score has no extractable formula. Smaller deferral: custom columns in the corridor Gantt rows.
