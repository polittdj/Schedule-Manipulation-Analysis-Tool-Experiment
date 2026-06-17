# ADR-0060 — Chart usability: full-screen + zoom on every chart, readable version labels

Date: 2026-06-17 · Status: accepted

## Context

Operator feedback on the visuals (the second item of the big backlog, after Ask-the-AI):
*"Fix the Trend charts — especially Schedule Progress. The scaling is horrible, the dates all
overlap and are unreadable, the filenames are unreadable. Fix all of that for all charts. Make
it so that if you select any chart it goes full screen and you can revert, and give the option
to zoom in/out on each chart. Make sure there are legends on all visuals. The Forecast-drift
scale is unreadable and makes no sense."*

State before this change: the SVG charts already carried legends + one-line descriptions and
thinned/rotated their x-labels, but (1) there was **no way to enlarge or zoom** a chart, (2)
the version axis labels were **filename-derived** — long, prefix-stripped, truncated strings
that still overlapped on 10+ version workbooks, and (3) the **Forecast-drift** axis drew
**year-only** ticks, so a forecast window inside a year or two showed an almost-empty scale.

## Decision

1. **Generic chart frame (`static/chartframe.js` + `.cf-*` CSS).** Any container marked
   `class="chart-host"` gets an overlay toolbar: **⤢ full screen** (Fullscreen API, with a
   fixed-position `.cf-max` fallback and Esc/✕ to revert) and **− / ＋ / Reset zoom** (rescales
   the SVG width inside an `overflow:auto` scroller). The toolbar lives *outside* the host's
   content and a `MutationObserver` re-applies the current zoom to SVGs drawn later, so the
   Bow-Wave / drift / stepper charts that rebuild their SVG each frame keep their frame and
   zoom. Loaded once from the page shell, so it reaches every chart. `.chart-host` is applied
   to the trend, finishes/data-date/slippage, CEI/bow-wave, WBS, forecast-drift, and the
   interactive-analysis chart containers. (The Critical-Path Evolution Gantt already has its
   own axis zoom/pan from ADR-0055 and is left as-is.)
2. **Readable version labels (`trend.js`, `curves.js`).** `shortLabels` now prefers the
   **data date** (`status_date`, `YYYY-MM-DD`) as the axis/legend label — short, uniform, and
   the exact order the versions are sorted by (ADR-0053) — so a many-version workbook no longer
   collapses into an unreadable smear of long filenames. Filenames (prefix-stripped, truncated)
   remain the fallback only when a version carries no data date.
3. **Adaptive forecast-drift ticks (`drift.js`).** The locked date axis now picks
   **year / quarter / month** granularity from the span (≈ a dozen ticks), labelling sub-year
   ticks `Mon YY`, so a short forecast window shows a meaningful, readable scale instead of one
   lonely year mark.
4. **Robustness:** the Trend "Project finish (days vs first)" series now bases its delta on the
   first *non-null* finish (a missing first finish no longer turns the whole series to NaN).

Legends + per-chart descriptions were already present on every chart (verified, unchanged).

## Scope / safety

Pure presentation — no engine/CPM/metric/forecast change, so **parity is untouched (10/10)**.
`chartframe.js` is dependency-free and same-origin only (added to the air-gap scan, which still
passes — nothing the UI serves points off-machine). Tests: a new `test_visuals` case pins that
`chartframe.js` is served and shell-loaded, that every chart container carries `chart-host`,
that the frame CSS is present, that trend/curves prefer the data-date label, and that the drift
axis is adaptive; the air-gap scan now covers `chartframe.js`. Full suite **876 passed**;
engine cov 97%. The remaining chart items (Bow-Wave running totals + target-UID highlight; the
Data-Date/Slippage redesign into selectable overlaid line families) are tracked as their own
PRs and rely on the operator's feedback against real data.
