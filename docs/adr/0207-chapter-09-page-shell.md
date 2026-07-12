# ADR-0207 — Mission Ops redesign step 3 (page shell): chapter 09 "Where it lands"

## Status
Accepted. Ninth page shell of step 3, applying the template to chapter 09 "Where it lands" =
Forecast at `GET /forecast`. Presentation only; every figure is read from the finish-forecast set
(`compute_finish_forecasts`) the page already computes.

## Decisions
- **`_where_it_lands_header(sch, fset)`** (latest version):
  - **Takeaway h1** — "`N of M forecasting methods place the finish between <earliest> and
    <latest>; CPM logic lands on <cpm>, D days behind/ahead of the baseline.`" (honest when no
    method can place a date).
  - **6-KPI strip** — Methods with a date · CPM finish · Earliest · Latest · Spread (days) ·
    vs Baseline.
  - **Two composition bars** (`_status_stack`): **Progress to the finish** (Complete vs Still to
    go) and **Method agreement** (methods that placed a date vs inputs missing).
- Data from `ForecastSet` (per-method `finish` dates, `planned_finish`, completed/remaining
  counts). Missing inputs render em dash / "inputs missing" — never a fabricated date.

## Consequences
- Forecast reads as chapter 09. Chromium-verified console + daylight, zero console errors ("4 of 4
  methods place the finish between 01/25/2028 and 02/01/2029; CPM logic lands on 01/25/2028, 200
  days behind the baseline"). Part of the bundled 08-12 PR.
