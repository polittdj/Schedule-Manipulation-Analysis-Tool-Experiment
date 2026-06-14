# ADR-0039 — PBIX pages 4 + 5: Cross File Comparison + Float Analysis charts

Date: 2026-06-14 · Status: accepted

## Context

M18 item 6 (PBIX visual reproduction). Pages 1 (Metrics/Schedule Card) was delivered in
ADR-0038. This PR delivers the next two analytical pages from the spec in
`docs/PLAN/PBIX-VISUALS.md`:

- **Page 4 (Cross File Comparison)** — multi-version stacked bars (activity
  status + type by data date), line charts of MEI/BEI/EPI across versions, clustered
  columns of completion performance (ahead/on-schedule/behind), Start-to-Finish Ratio
  line.
- **Page 5 (Float Analysis)** — TotalFloatSum + FreeFloatSum bar chart per version,
  clustered columns of % total/free float at 0-day / <5-day / <10-day bands per
  version.

## Decisions

1. **New engine helper** (`engine/metrics/float_bands.py`): `FloatSums` (frozen
   dataclass `total_days`, `free_days`) + `compute_float_sums(schedule, cpm)` — sum of
   total/free float in working days across the incomplete population. Negative float is
   included (forensic signal; a plan already behind schedule drags the sum negative).
   Deliberately a lightweight `@dataclass`, not a `MetricResult`, so the
   metric-dictionary coverage test is unaffected (same pattern as `ActivityMakeup`).

2. **`_Analysis` CPM reuse** — `compute_float_sums` accepts a pre-solved CPM so the
   trend endpoint does not re-solve any schedule. A new `_solvable_versions_full()`
   helper (parallel to `_solvable_versions`) returns the cached `_Analysis` objects
   alongside the schedules and CPM results; `trend_json()` uses it to pass analyses to
   `_trend_data()` without duplicating computation.

3. **Extended `_trend_data()` API** — the `/api/trend` response gains per-version
   fields:
   - `makeup` (milestones/normal/summaries counts — PBIX p4 stacked bars)
   - `status_split` (complete/in-progress/planned — PBIX p4 stacked bars)
   - `completion_perf` (ahead/on_schedule/behind — PBIX p4 clustered columns)
   - `indices` (mei/bei/epi/sfr — PBIX p4 multi-line and SFR line; `None` when the
     population is zero, never fabricated as 0)
   - `float_sums` (total_days/free_days — PBIX p5 grouped bar)
   - `float_bands` (count+pct per key — PBIX p5 % clustered columns; already computed
     in `_Analysis.float_bands`)

4. **Extended `trend.js`** — the existing `lineChart` and `shortLabels` helpers are
   retained; three new helpers added: `multiLineChart` (series with legend, used for
   MEI/BEI/EPI), `stackedBarChart` (PBIX p4 status/type/completion), and
   `groupedBarChart` (PBIX p5 float sums + float-band % columns). Section headings
   (`sectionHead`) group the existing and new charts within the single "Trend charts"
   panel — no new route or page required (the Trend page IS the deck's p4 + existing
   p3 counterpart). All SVG, all local, no CDN.

5. **No new route** — the deck's page 4 is a subset of the Trend page's multi-version
   view; page 5's float charts are added as a second section in the same panel. The
   `/api/trend` endpoint is backward-compatible (new fields are added, not changed).

## Scope / safety

Pure presentation over existing engine outputs plus one additive tested helper;
parity untouched (10/10); air-gap test unaffected (no new routes or static files added
to its allow-list); nothing leaves the machine. `FloatSums` is not a `MetricResult` so
the metric-dictionary coverage test is unaffected. `RatioMeasure` (dangling deck
binding) remains unimplemented (ADR-0033).

## Remaining PBIX pages (next PRs)

Finishes / DATA Date Finishes month curves (6–7) · WBS-grouped Completion + SPI/ES
pivots (8–9) · Slippage curves (12) · Carnac forecast cards (13).
