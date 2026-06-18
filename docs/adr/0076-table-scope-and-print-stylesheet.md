# ADR-0076 — Table header `scope` (A4) + a print-ready stylesheet (A5)

Date: 2026-06-18 · Status: accepted

## Context

Two bounded, presentation-only audit items:

* **A4 (WCAG 1.3.1).** No `<th>` in the server-rendered tables carried `scope`, so assistive tech
  couldn't reliably associate a dense forensic table's headers with its cells.
* **A5.** The README and the `/brief` + `/briefing` pages advertise **print-ready** output, but there
  was no `@media print` / `@page` / page-break control. Ctrl-P printed the global nav (13 links),
  chart toolbars, the theme toggle, and dark backgrounds (ink-heavy, often unreadable).

## Decision

1. **`scope=col` on every server-rendered column header (`web/app.py`).** All 43 `<th>` are header
   cells (the tables are column-oriented, `<td>` bodies), so a mechanical, consistent
   `<th>` → `<th scope=col>` is correct everywhere. (The JS-built grid + the `SFA11y.table` fallback
   already emit `scope`.)
2. **A `@media print` stylesheet (`base.css`).** Hides the chrome (`header` nav, `.cf-bar` chart
   toolbars, `.export-bar`, `.viz-controls` / path controls, `#askPanel`), forces **light ink on
   white** (`body{background:#fff;color:#000}`, links black), keeps panels/cards/tables from
   splitting across pages (`break-inside:avoid`), prints the horizontal scrollers **in full**
   (`.cf-scroll`/`.gantt-scroll`/`#grid`/`.path-view`/`.evo-gantt`/`#forecastRuler`
   `overflow:visible`), and sets a sensible `@page{margin:14mm}`.

## Scope / safety

No engine/CPM/metric change → **parity 10/10**. Air-gap unchanged (no remote asset). Tests
(`tests/web/test_accessibility.py`): the analysis + metric-dictionary pages carry `scope=col`; the
print block hides chrome (`#askPanel`), forces light, avoids page breaks, and prints scrollers in
full. The `<th>`→`<th scope=col>` change broke no existing assertion (the full web suite stays green).
Full gate green; ruff/format/mypy/bandit clean.

Remaining audit PRs: A9/A10 (responsive nav + theme `aria-pressed`/`prefers-color-scheme`), A11
(HANDOFF-drift test), and the A3 follow-up data tables for the non-curves charts.
