# ADR-0171 — Resources: day/week/month bucketing + click-a-bar over-allocation drill

## Status

Accepted. Closes backlog #74. Operator asked for the Resources loading histogram to support
day / week / month bucketing and a click-a-bar drill that lists the activities driving an
over-allocated (or any) bar.

## Context

The Resources page (ADR-0125) bucketed loading by **calendar month only**, and a bar carried no
way to see *which* activities produced it. Investigating an over-allocation meant eyeballing the
roster. Finer time resolution (week / day) and a per-bar activity breakdown are standard in
MS-Project / Primavera resource-usage views.

## Decisions

1. **Selectable granularity (`engine/resources.py`).** `compute_resource_loading(schedule, cpm,
   granularity="month")` now buckets by `day` (`YYYY-MM-DD`), `week` (ISO `YYYY-Www`), or `month`
   (`YYYY-MM`) via `_bucket_key`. Capacity scales with the working days in each bucket, so
   over-allocation is defined consistently at every granularity. Total work is invariant to the
   bucket. Unknown values fall back to `month`. `ResourceLoading` carries the chosen `granularity`.
2. **Per-bucket contributors (the drill data).** Each `ResourcePeriod` now records
   `contributors: tuple[(task uid, booked minutes), …]`, summing exactly to the bucket load,
   ordered by contribution desc — computed in the same time-phasing pass, no second walk.
3. **Bucket selector + drill (`web/app.py`, `static/resources.js`).** `/resources?bucket=` drives a
   Day/Week/Month `<select>` that auto-submits (the server recomputes, since capacity is
   granularity-dependent). `_resource_loading_json` embeds each period's `tasks` (uid, name, days),
   so **clicking any bar** opens an over-allocation drill (`#resDrill`) listing the activities
   behind that bucket — entirely client-side, same-origin (air-gap intact). Bars show a pointer
   cursor and a "click to drill" hint; x-axis labels thin out as buckets multiply.

## Consequences

- Live-verified in Chromium (Hard_File): month → 4 bars, week → 15, day → 68 (monotonic with
  granularity); the selector switches the bucket; clicking a bar opens the drill (a caught
  over-allocation read "18.19 d booked / 18 d capacity" with its three contributing activities);
  zero console errors. Pinned by `tests/engine/test_resources.py` (+3: granularity invariance,
  fallback, contributor sums) and `tests/web/test_resources_view.py` (+2: selector/drill wiring,
  default/bad-value → month).
- Parity-isolated (plain dataclasses, no `MetricResult`); std-lib only; Laws untouched (derived
  figures, offline, embedded server-side). `src/` changed (`resources.py` + `app.py` +
  `resources.js`) → wheel + 9 installers rebuilt in the same commit (ADR-0148 lockstep).
- Remaining from the operator work order: SRA editable-grid Gantt (#80).
