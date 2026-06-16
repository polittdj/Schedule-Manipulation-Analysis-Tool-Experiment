# ADR-0046 — Forecast explainer + Trend drill-down/animation (M18 item 8)

Date: 2026-06-16 · Status: accepted

## Context

M18 item 8 — the last backlog item. Two operator asks:

1. **Forecast explainer** — `/forecast` shows three method dates (CPM / completion-rate /
   IEAC(t)) and an animated multi-version drift stepper, but nothing on the page explains
   *how* each method is computed or *how to read* a disagreement between them.
2. **Trend page expansion** — more room, a **per-metric drill-down to the offending
   activities per version**, an **animation**, and an **Excel export of the series**. The
   Trend page carried per-metric trend lines and prose sentences, but the only offenders it
   exposed were the *worst* version's (`MetricTrend.worst_offender_uids`); you could see that
   "Critical decreases 41 → 37" without seeing *which* 41/37 activities, per version.

## Decisions

1. **Forecast explainer (server-side, no new JS).** Two helpers on the `/forecast` body:
   - `_forecast_explainer(ForecastSet)` — a "How the three forecasts are computed" panel with
     one plain-English card per method (what it measures, the formula in words **and**
     symbols, when it is available vs. reads "—", and *this version's* value). Every figure
     reuses the existing `ForecastSet`; nothing is recomputed.
   - `_forecast_ruler(ForecastSet)` — a static, single-version **inline-SVG "spread ruler"**
     placing the data date, the baseline finish, and the three method forecasts on one
     timeline (one lane per method, matching `drift.js` lane colors), with a caption naming
     the day-spread between the earliest and latest method. Inline SVG (no JS, no fetch) so it
     renders for a single version and never collides with the animated drift stepper
     (`id=forecastRuler`, never the literal "Forecast drift" / `driftChart`).

2. **Trend per-version offenders (engine).** `MetricTrend` gains
   `offenders_by_version: tuple[tuple[int, ...], ...]` (parallel to `values`,
   oldest → newest); `compute_quality_trend` fills it from each version's
   `MetricResult.offender_uids`. `worst_offender_uids` is retained (the Briefing uses it) and
   is now just one slice of the full series. A neutral ratio (Logic Density) carries empty
   offenders per version. Additive default — no golden pin moves; parity untouched (10/10).

3. **Trend drill-down + animation (web + JS).** `/api/trend`'s `quality` entries now carry,
   per metric: `lower_is_better`, `worst_index`, full per-version `counts`, and per-version
   `offenders` resolved to `{uid, name}` against **each version's own** task map. A new
   **"Quality drill-down & animation"** panel (`static/trend_drill.js`) is a Prev/Next/
   Auto-play stepper over the versions that draws, on a **locked y-axis** (the global max
   offender count across every metric and version, so frames stay comparable), a bar per §A
   metric = its offending-activity count in the current version. A metric selector (and
   clicking a bar/label) lists the exact offending activities (UID + name) for that
   (metric, version) — the drill-down — in a scrollable panel. Mirrors the
   `cei.js`/`drift.js`/`path_evolution.js` stepper idiom.

4. **Excel/Word export of the series.** `trend_tables` gains a third table, **"Quality
   offenders by version"** — one row per (metric, version) with the offending count and the
   **complete** offender-UID list. The two existing tables (overview, worst-version) are
   unchanged in shape; the worst-version UID list is also now uncapped.

5. **No caps (Law 1).** Per the operator's call, the on-screen drill-down, the `/api/trend`
   payload, and the Excel series carry the **full** offender set (the machine is the
   operator's; nothing leaves it). The on-screen list is scrollable so a large set stays
   usable; bar heights always reflect the true count.

## Scope / safety

Presentation + one additive engine field + one additive export table; the forecasting math,
the CPM, and the quality-metric definitions are all unchanged, so `pytest -m parity` stays
**10/10** and every golden pin holds. The air-gap test is extended over `/forecast` and
`static/trend_drill.js`; the new inline-SVG ruler and JS reference only theme CSS variables
and the local `/api/trend` — nothing leaves the machine. Verified on the golden P2→P5 pair:
the Critical drill-down lists the full 41 (P2) / 37 (P5) activities; the forecast ruler shows
P5's CPM 2027-12-07 / rate 2028-06-10 / ES 2029-02-01 spanning 422 days off the 2027-07-09
baseline. **M18 is complete with this item.**
