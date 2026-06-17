# ADR-0065 — Animated S-curve: cumulative planned vs actual/forecast progress

Date: 2026-06-17 · Status: accepted

## Context

Operator: *"I want to see an animated chart that shows the S-Curve for the schedules, and I want
it to be animated."*

The tool had finish/slippage month curves and the Bow-Wave animation, but no cumulative
progress S-curve — the standard planned-vs-actual lazy-S that shows, at a glance, whether the
program is ahead of or behind plan over time.

## Decision

New engine `engine/s_curve.py` → `compute_s_curve(schedules)` (oldest → newest): on a shared
calendar-month axis (reusing `engine/month_axis`), per version two cumulative curves over the
non-summary activities, as a percentage of that version's activity count —

* **planned** — running share whose **baseline** finish falls on/before each month;
* **actual / forecast** — running share whose **current** finish (actual where complete, else
  the scheduled/forecast finish) falls on/before each month.

Dates before the (capped, 60-month) window are folded into the starting running count, so
shedding the oldest months never drops already-completed work from the cumulative curve. Each
version also carries its data-date month index.

New **`/scurve` page** + `static/scurve.js` + `/api/scurve`: a Bow-Wave-style **Prev / Next /
Auto-play** stepper over the versions on a **locked 0–100% axis** (so frames are comparable),
drawing the planned (gold) and actual/forecast (blue) curves, the dashed data-date marker
(actuals to its left, forecast to its right), a legend, and a headline callout of the
planned-vs-actual gap at the data date. The chart container is a `.chart-host`, so it inherits
the full-screen + zoom toolbar from ADR-0060. Linked in the nav.

## Scope / safety

Additive and read-only over the loaded versions — no engine/CPM/metric change → **parity 10/10**.
`scurve.js` is dependency-free, same-origin, and on the air-gap scan (still clean). Engine
unit-tested (cumulative monotonicity, reaching 100%, the actual-lags-plan gap, the shared axis
across versions, the no-finish-dates error); a web test pins the page (stepper + chart-frame +
nav link) and that `/api/scurve` returns bounded, non-decreasing cumulative curves. Full suite
**892 passed**; engine cov 97%.
