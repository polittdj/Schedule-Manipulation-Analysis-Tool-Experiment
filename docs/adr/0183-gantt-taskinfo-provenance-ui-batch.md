# ADR-0183 — Gantt interaction batch, Task Information dialog, provenance-everywhere, exports-everywhere

## Status

Accepted. Operator 2026-07-10 (multi-item work order + two follow-ups).

## Decisions

1. **"show completed tasks" fix.** The Activities & Gantt toolbar checkbox only filtered the
   driving-path trace; it now scopes the WHOLE grid + Gantt (`rowVisible` hides 100%-complete
   rows — a fully complete summary too — and the change listener re-renders the grid).
   Verified: 142 → 93 rows on Hard_File_updated3.
2. **Task Information dialog.** Clicking any task / summary / milestone row opens an
   MS-Project-style tabbed popup (General / Predecessors / Successors / Resources / Advanced /
   Notes / Custom Fields) with a provenance footer (file + UID + name). `_activity_rows` now
   carries the full payload (actuals, constraint + deadline, work/cost, per-assignment
   units/work, predecessor/successor lists with type + lag, mode flags, notes).
   **`Task.notes` added to the model** (MSPDI `<Notes>`, JSON round-trip, SCHEMA 2.5.0→2.6.0).
3. **Dependency link lines** on the Activities Gantt: an SVG overlay in the scroll pane draws
   MS-Project-style elbows (FS/SS/FF/SF anchor geometry + arrowheads) between visible bars;
   the new "links" toolbar checkbox shows/hides them (115 links drawn on updated3; toggle → 0).
4. **Gridlines.** Solid row/column lines on every `.gantt-grid` data cell; the row line
   continues across the timeline as a light dotted line (`.g-cell` border).
5. **Column mover.** `SFGantt.attachColumnMovers` decorates every gantt-grid header with a
   hover grip → "Move left / Move right" menu; a cancelable `sf-colmove` event lets a page
   reorder its own column model (the Activities grid persists the order); the DOM fallback
   covers every other grid. The timeline column never moves.
6. **Year Phases page removed** (operator: no value) — route, /api, body, phases.js, engine
   module, i18n entry, tests.
7. **EVM per-field grouping.** The ADR-0179 Forecast grouping panel (same engine functions,
   honest N/A) now renders on /evm too (`_field_forecast_panel(action=...)`).
8. **Resources drill: columns + Excel.** The bar-click drill gains a persisted Columns picker
   (standard + custom fields via /api/analysis, localStorage set-once) and an Excel export
   (`/export/{fmt}/resource-drill` — recomputes the bucket server-side and joins task fields).
9. **Provenance everywhere.** `_page` renders an always-on source banner (loaded files,
   oldest first) on EVERY page; animated visuals caption the file per step (the shared
   sfCaption already did; the new Performance stepper does; quads ring the current file's dot).
10. **Performance Summary automation + sizing.** Per-version G1–G5 series embedded; a master
    Prev/Play/Next stepper animates every chart through the loaded files with the file name
    captioned per step; tiles are Mission-Control-sized (no tile-wide; 640-viewBox charts).
11. **Exports everywhere.** New export routes + page buttons: `evm`, `scurve`, `resources`,
    `risks`, `mission` (trend + evolution series), joining the existing per-page exports so
    every graph/table on every page reaches Excel.

## Consequences

- Chromium-verified end to end on the four-version Hard_File series (zero console errors):
  completed-toggle counts, 115 link lines + toggle, gridline computed styles, 7-tab dialog
  with citation footer, column move (UID↔Name), Performance stepper captions + quad ring,
  volatility gauge caveat + instability-sorted heatmap, resources drill columns + source
  line + Excel, EVM group panel + export, global source banner.
- `src/` changed → wheel + 9 installers rebuilt (ADR-0148 lockstep).
