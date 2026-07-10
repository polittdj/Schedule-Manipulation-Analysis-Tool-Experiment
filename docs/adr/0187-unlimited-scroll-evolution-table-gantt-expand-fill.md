# ADR-0187 — Unlimited Gantt right-scroll, evolution table Gantt, expand fills the page, callout coverage

## Status

Accepted. Operator 2026-07-10 (screenshots: the Path Analysis Gantt scroll stopping at the last
bar; an expanded chart rendering tiny in an empty page): (1) "click on the arrow on the right
and have it continue to scroll to the right and not be limited … for all Gantt charts";
(2) "I also don't have the Reset All button on all of the pages or Gantt Charts … the Path
Analysis page … Driving Path Page or the Critical-Path Evolution Page"; (3) "On the Critical
Path Evolution page format the Critical Path Gantt chart like the other Gantt Charts";
(4) "Fix all charts and graphs so that if I expand them they don't look like this … utilize the
page space and I want Titles on all Graphs to show in all views"; (5) "call-outs on all graphs
and charts that explain what they are conveying, how to use them, and examples how the
information can be used."

## Decisions

1. **Unlimited right scroll — `SFGantt.attachEdgeExtend(pane, onExtend)`**: when a Gantt pane is
   scrolled to its right edge, the page's callback EXTENDS its time axis (+60 days per hit) and
   re-renders; the helper restores the scroll position, so holding the scroll arrow keeps
   travelling into future time instead of hitting a wall. Wired into the Activities grid + the
   driving-path trace (app.js `extraRightDays`), /path (path.js), the /driving-path corridor
   (shared `t1` growth), the SRA grid, and the rebuilt evolution Gantt. Fires only when the pane
   actually overflows — a fill-to-page timeline has no scrollbar to extend. "View entire
   project"/Reset returns to the natural span.
2. **Reset view is `position:fixed`** (bottom-right, above the telemetry chip, appended to
   `<body>`): the ADR-0186 float-right button was rendered but easily lost in busy page tops —
   the operator read it as missing on /path, /driving-path and /evolution. Now unmissable on
   every page.
3. **CP Evolution = the standard table Gantt** (`path_evolution.js` rewritten): the SVG chart is
   replaced by the same `table.gantt-grid` construction every other Gantt uses — frozen data
   columns (UID / Name / % / Dur / Start / Finish / Why), `SFGantt.buildTierScale` +
   `gridLines` + non-working shading (so the Timescale… dialog now applies — button added),
   per-column checklist filters, drag-to-resize + movable columns, sticky bottom scrollbar,
   dates-on-bars, edge-extend, row-click Task Information. Kept: the LOCKED cross-version axis,
   entered/stayed/left colouring (+ tier colours in all-tiers mode), ghost rows for
   "left the path" (dashed, struck-through, prior-version provenance), ▲ duration badges,
   reason chips with hover detail, focus-UID highlight, the four path filters, hide-completed,
   the stepper, and the SFA11y data table. Zoom buttons now change pixels-per-day (like every
   other Gantt); pan buttons scroll the pane; "View entire project" clears the px zoom.
4. **Expanded charts contain-fit the viewport** (`chartframe.js`): the ADR-0158-era
   `FS_FONT_CAP` (×1.25 of design size) made expanded charts tiny on large screens — the SVG now
   scales to the largest size that fits BOTH the available width and height (never overflowing;
   user −/＋ zoom multiplies on top). A `.cf-title` mirroring the nearest preceding heading is
   revealed in the expanded modes (the original heading covers the normal view), and it inherits
   the heading's `data-sf-hint` explainer so the callout is available in every view.
5. **Callout coverage** (audit-driven): ~40 new `vizhints.js` catalog entries (WHAT / EXAMPLE /
   HOW TO READ / PM USE), closing the audited gaps — all 18 Trend-page charts, the dead
   "finishes &" key (em-dash headings), Worst/Largest variance tables, "Driving path:",
   driving-tier table, CP-Volatility page + scoreboard, Performance Summary, what-if
   added/removed, execution-by-field-group, working calendar, SRA OAT, the evolution
   sub-headings, and the Risks/Issues/Opportunities panels — plus specific-before-broad
   reordering fixes (finish-date confidence vs s-curve; risk-factor form vs risk ranking). The
   trend drill's dynamic title carries its own inline hint. `chartframe.js` callouts now also
   read HTML `title=` attributes, so the table-Gantt bars get the instant styled call-out (not
   just the slow native tooltip).

## Consequences

- Chromium-verified (16 checks, zero console errors): fixed Reset visible on the three reported
  pages; evolution renders the standard table Gantt (columns, tiers, frozen columns, filters,
  Timescale button, dates-on-bars, Task Info) and its axis extends at the right edge; the
  Activities grid extends at the right edge; an expanded chart fills 98% of the page width with
  its title showing; 31/31 headings on /trend carry explainers.
- Tests pinned to the old SVG evolution internals / FS_FONT_CAP were re-pinned to the new
  implementations (accessibility: the table Gantt is natively accessible; mission: `bar.title`
  call-outs; visuals: shared tier scale; gantt-consistency: `pxZoom = null` fit).
