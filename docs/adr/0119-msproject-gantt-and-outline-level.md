# ADR-0119 — Mirror Microsoft Project's Gantt on every page (shared timeline + WBS indentation)

- Status: accepted
- Date: 2026-06-24
- Relates: ADR-0088 (custom fields, the prior SCHEMA_VERSION bump to 2.2.0), the M14 interactive
  visuals, and the prior tier-axis DRY pass (#224, `timeaxis.js` / `SFTimeAxis` for the line charts)

## Context

Operator request, against the `/analysis` screenshot beside Microsoft Project: "Make the Gantt on
this page **and on all other pages that have Gantt charts** mirror the format in which Gantt charts
are presented in Microsoft Project in all aspects — the way tasks are indented based on their WBS /
outline level, the gridlines, the way the timeline is separated into three tiers, the ability to
zoom in or out, and the way you can filter / add / remove columns. Mirror Microsoft Project on all
pages in regards to options, UI, and functionality." Clarification: "There could be more or less
outline levels depending on the project" — the indent must be driven by each task's **actual**
outline level, to any depth, never a fixed count.

Before this change each Gantt drew its **own** single-tier month-tick header (`pv-tick` / `g-tick`
month ticks): the `/analysis` activity grid and driving-path trace (`app.js`), the `/path`
workspace (`path.js`), and the driving-path corridor animation (`driving_path.js`) each had a
near-duplicate copy, and none indented by WBS or showed quarter/year context. The schedule model
carried no outline-level field, so the importer could not even express WBS depth.

`SFTimeAxis` (`timeaxis.js`) already draws a stacked Year/Quarter/Month header, but it is **SVG and
month-index based** — built for the bucketed line charts (curves, S-curve), not the pixel-per-day,
continuous-date Gantt bars laid out in HTML tables. It is the wrong primitive for the bar Gantts.

## Decision

1. **Model + importer.** `Task` gains `outline_level: int = 0` (MSPDI `<OutlineLevel>`; 0 = the
   project-summary row, 1 = a top-level WBS, deeper levels nest further — the *value*, not a fixed
   count, sets the indent). The MSPDI importer reads it. This is an additive field-set change, so
   `SCHEMA_VERSION` bumps **2.2.0 → 2.3.0** and the schema-freeze test is updated in the same commit.

2. **One shared timeline primitive.** New vendored `static/gantt.js` exposes `window.SFGantt` with
   `timeTiers` / `buildTierScale` (the stacked Year/Quarter/Month header, narrow bands collapsing
   their label exactly as MS Project does) and `gridLines` / `paintGrid` (month-faint /
   quarter-medium / year-heavy vertical gridlines, pixel-aligned to the header). It operates on a
   tiny axis contract `{ t0, t1, width, x(ms) → px }`, so each page keeps its own axis construction
   (zoom = pixels-per-day differs per view) and only swaps its old single-tier header for
   `buildTierScale` and paints `gridLines` down each track. Loaded once in the page shell.

3. **Adopt it everywhere a bar Gantt exists.** `app.js` (activity grid + driving-path trace),
   `path.js`, and `driving_path.js` drop their local month-tick loops and call `SFGantt`; the
   activity grid additionally indents the Name column by `outline_level` (any depth) and renders
   rows in **file/outline order** (not UID order) so parents sit above their children. The SVG
   path-evolution Gantt (`path_evolution.js`) gains the same stacked quarter/year bands + graduated
   gridlines in SVG. Existing zoom, column add/remove, and the MS-Project-style checklist filters
   are preserved.

`phases.js` (a per-year activity histogram) and `cei.js` (a grouped monthly bow-wave bar/curve
chart) are **categorical bar charts, not date-axis Gantts**, and are deliberately left unchanged.

## Consequences

- Every HTML Gantt on the site now reads identically — three stacked tiers, MS-Project gridlines,
  WBS indentation on the full activity tree, and a user-adjustable pixels-per-day zoom — from one
  implementation, removing four near-duplicate header loops.
- `outline_level` is optional/additive (defaults to 0), so non-MSPDI sources and older fixtures are
  unaffected; CPM, DCMA/EVM metrics, and parity goldens are untouched (presentation-only change).
- Tests: the importer reads `<OutlineLevel>` (`test_outline_level_is_read`); the analysis payload
  exposes `outline_level` + `order` and the rows arrive in ascending file order; a cross-page test
  asserts `SFGantt` is loaded once and used (with gridlines, no `pv-tick`) on app/path/driving_path
  and that the SVG evolution Gantt grows quarter/year bands.
