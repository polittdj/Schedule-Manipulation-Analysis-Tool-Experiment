# ADR-0078 — Data-Date / Slippage: clickable show/hide legend for the overlaid line families (item E)

Date: 2026-06-18 · Status: accepted

## Context

Operator backlog item E (and the operator's own screenshots of `/curves`): the **DATA Date
Finishes** and **Slippage** charts overlay one line per loaded version (and, for slippage, two lines
per version). On a real program with 15–30 versions that is **50+ overlapping lines** — an
unreadable tangle. The chart drew a **static, non-interactive** legend inside the SVG, so there was
no way to isolate or hide a version.

## Decision

Replace the static in-SVG legend with a **clickable, keyboard-operable HTML legend** (`curves.js`
`buildLegend`):

* Each series gets a real `<button class="curve-legend-item">` carrying a line-style colour swatch +
  its label. Clicking (or Enter/Space — it is a native button, so it is focusable and gets the
  ADR-0073 focus ring) **toggles that line's visibility** (`polyline.style.display`) and flips the
  button's `aria-pressed` + a struck-through `.off` style. So a user can hide the clutter and read
  one or a few versions.
* With more than two series, a **Show all / Hide all** pair lets you blank the chart and reveal a
  single version (isolate-from-clutter) in two clicks.
* Applied uniformly to all three `/curves` charts (Finishes / Data-date / Slippage). The dashed
  data-date marker, the locked count axis, the accessible name, and the `.sr-only` data-table
  fallback (ADR-0075) are all unchanged.

## Scope / safety

Pure presentation (JS/CSS) — no engine/CPM/metric change → **parity 10/10**. Dependency-free and
same-origin (air-gap intact). Keyboard-operable and labelled (`aria-pressed`), consistent with the
audit's a11y work. Tests (`tests/web/test_curves_view.py`): `curves.js` builds the `buildLegend`
clickable legend (`curve-legend`, `aria-pressed`, `polyline.style.display` toggle, Show-all/Hide-all)
and the old static in-SVG legend is gone; `app.css` carries `.curve-legend-item`. Full gate green;
ruff/format/mypy/bandit clean.

Remaining operator backlog: F (Bow-Wave running totals + target-UID highlight), D (Fuse year
Trend/Phase — parity-sensitive; binning needs the operator's confirmation), and the `/path` chart
visual bug (needs the operator's screenshot). The deferred Fuse-proprietary metrics still await the
exact DAX.
