# ADR-0037 — Forecast-drift animation and locked axes on the animated visuals

Date: 2026-06-13 · Status: accepted

## Context

M18 item 5 (operator): *"Forecast-drift ANIMATION across versions (Bow-Wave-style
stepper) and locked Y-axis scales on ALL animated visuals (scale = max of the metric
across every loaded version, held through the animation — bow wave, drift, trend,
path)."*

The Bow Wave / CEI chart recomputed its count axis **per snapshot**
(`top = maxCount(snap)`), so each frame renormalized — the very growth the bow wave is
meant to show was scaled away. And the forecast-drift surface was a static table only;
the operator wanted to *watch* the three forecasts slide right across versions.

## Decisions

1. **The Bow Wave count axis is locked** to the maximum bar across **every** snapshot.
   The max is computed server-side (`_cei_data` → `max_count`) and `cei.js` scales every
   frame to it. Bars now stay comparable frame-to-frame; the wave visibly grows.
2. **New forecast-drift animation** (`/static/drift.js`, panel in `_forecast_body`,
   shown only with ≥2 versions): a Bow-Wave-style stepper (Prev / Next / Auto-play)
   over the loaded versions, oldest first. Each frame plots that version's three finish
   forecasts (Schedule logic / Completion-rate / Earned-schedule) as labeled markers in
   per-method lanes, with the data-date and baseline-finish references; the prior
   version's markers stay as a faint trail with a drift arrow.
3. **The drift date axis is locked** (`_forecast_data` → `axis.min`/`axis.max`) spanning
   every version's forecasts + data dates + baseline finishes, held fixed through the
   stepper so the forecasts drift across a stable scale rather than the axis rescaling.
   `methods` carries the stable lane order/labels. No new engine math — the animation
   reads the existing `/api/forecast` payload.
4. **Trend and path were assessed, need no change.** The Trend line charts already plot
   every version on a single fixed per-metric scale (`lo=min`, `hi=max` over all known
   values) — locked across versions by construction, and not a stepper. The Path
   Analysis Gantt is a single-schedule timeline (a date x-axis, no per-version metric
   axis) and does not animate across versions. Both are documented here so the "all
   animated visuals" clause is provably covered.

## Locality / safety

Pure presentation: both visuals are dependency-free local SVG over existing local
endpoints (air-gap tests extended over `drift.js`); no engine figures change, parity is
untouched (10/10), and nothing leaves the machine.

## Remaining M18 items

6 — PBIX visual reproduction; 7 — CPM path-evolution animation; 8 — forecast explainer
+ trend page expansion.
