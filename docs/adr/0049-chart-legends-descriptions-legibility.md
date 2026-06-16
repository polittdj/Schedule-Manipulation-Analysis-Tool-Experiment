# ADR-0049 — Every chart carries a legend + description, with non-overlapping labels

Date: 2026-06-16 · Status: accepted

## Context

Operator standing requirement: **every graph/chart must include a legend and a description of
what it conveys**, and **the text on the charts must not overlap and must stay readable**. An
audit of the existing dependency-free SVG charts found:

- `cei.js`, `curves.js`, `wbs.js` — already compliant (in-SVG legend + x-label thinning +
  page-level descriptions).
- `trend.js` — the worst offender: the single-series line charts had **no legend**, **none**
  of the charts had a per-chart **description**, and **x-axis labels were drawn at every tick
  with no thinning** — so on a 10+ version workbook the rotated version labels overlapped into
  an unreadable smear.
- `trend_drill.js`, `drift.js`, and the server-rendered `/forecast` spread ruler — had no
  color-key **legend**.

## Decision

Adopt the rule for all charts (existing and future) and retrofit the gaps:

1. **`trend.js`** — a shared `chartWrap(title, desc)` adds a one-line **description caption**
   (`.chart-desc`) under every chart title; a shared `legend(wrap, items)` adds a color-key
   **legend** (`.chart-legend` + `.chart-swatch`) under every chart, including the
   previously-legendless single-series line charts; and `labelStep(n)` **thins the x-axis
   labels** (one every `ceil(n/14)`, rotated −35°) on all four chart types so they never
   overlap. Each call site passes a plain-English description of what the chart shows.
2. **`trend_drill.js`** — a description + a "selected metric / other metrics" legend under the
   per-version bar chart.
3. **`drift.js`** — a color-key legend mapping each forecast method to its color, plus the
   baseline / data-date reference key.
4. **`/forecast` spread ruler** (`_forecast_ruler`, server SVG) — an inline color-key legend
   using the same `.chart-legend` classes.
5. **CSS** — `.chart-desc`, `.chart-legend`, `.chart-legend-item`, `.chart-swatch` (swatches
   reuse theme variables so they recolor live with the light/dark theme).

The legibility convention (`chartWrap` + `legend` + `labelStep`) is the pattern the upcoming
dashboard / brief / path / analysis tab visuals will reuse.

## Scope / safety

Pure presentation — no engine, CPM, or data change; `pytest -m parity` untouched (10/10). The
charts remain dependency-free local SVG, so the air-gap posture is preserved (the air-gap test
already scans these JS files). A `test_visuals.py` guard pins that the chart JS/CSS carry the
legend, description, and label-thinning hooks, and that the forecast ruler ships its legend.
Node `--check` validates the rewritten JS. `cei.js` / `curves.js` / `wbs.js` were already
compliant and are unchanged.
