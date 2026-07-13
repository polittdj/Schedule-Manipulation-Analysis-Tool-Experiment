# ADR-0216 — Click-to-drill on the per-activity bar charts

## Status

Accepted. Operator directive 2026-07-13 (live-testing v1.0.26), pointing at the CP-Volatility Tenure
leaderboard: "I want … to click on any of these … bars … see the underlying data … add columns …
export to excel … applied the same way to all other bars in the tool like those."

## Context

The shared activity drill (ADR-0214 / #348) let the operator click a scorecard row or a server-rendered
stacked-bar segment to list the activities behind it (filter / add-remove columns / sort / Excel) via a
delegated `sf-drill` handler in `drilldown.js` and the `/api/activities/drill` endpoint. But the
**JS-drawn categorical bar charts** — where each bar *is* an activity or activity-set — were not wired:
the CP-Volatility tenure/jumper leaderboards, dwell histogram and entry/exit waterfall, the Performance
duration-ratio (DRM) histogram, and the SRA duration-sensitivity tornado. `drilldown.js` was also only
included on three pages, so those charts' pages lacked the runtime.

## Decision

- **Load the drill runtime globally.** `drilldown.js` moves into `_LAYOUT` (one `<script>` on every
  page); the three per-page includes are removed so no page double-registers the delegated listeners.
  `SFDrill` gains a `mark(node, uids, file, title)` helper that stamps the `sf-drill` contract
  (class + `data-uids`/`data-file`/`data-title` + `role`/`tabindex`) — it works on an SVG `<rect>`
  because the handler matches via `classList`. An empty UID set leaves the bar inert.
- **Tag the per-activity bars.** Each chart marks its bar rects:
  - Volatility leaderboards (`volTenure`/`volJumpers`) — one activity per bar (`[t.uid]`); dwell
    histogram — the activities in that tenure bucket; entry/exit waterfall — the newly-added server UID
    lists (`entered_uids` present in the "to" version, `left_uids` in the "from" version).
  - Performance DRM histogram (`g5Hist`) — the `DRM.points` whose ratio falls in the bin, keyed to the
    stepper's current version.
  - SRA sensitivity tornado (`sraSens`) — one activity per bar.
- **Multi-version `data-file`.** `_workbench_drill_rows` drops UIDs absent from the resolved version, so
  the leaderboard/dwell bars use the newest version's key (embedded as `latest` in `_volatility_data`),
  the waterfall bars the specific from/to version, and the DRM bars the stepper's current version.

## Consequences

- Every per-activity bar in the tool is now click-to-drill with the same grid, add-columns and Excel
  export the scorecards use — Chromium-verified on the CP-Volatility page (28 clickable bars; the grid
  opens with the activity, add-column and export work).
- Presentation only — the drill lists activity sets the engine already computed (`entered_uids`/
  `left_uids` are `b−a` / `a−b` of the effective-critical sets; DRM/tornado UIDs come straight from the
  SRA/DRM payloads). No engine or metric change (Law 2). Pinned by `tests/web/test_bar_drill.py`.
- Genuinely non-activity bars stay inert by design (SRA finish-histogram = simulation outcomes; trend
  status/float bars = counts/sums; risk tornado = risks). The stacked/grouped trend bars carry no
  per-bar value labels, so no bar-total de-overlap was needed.
