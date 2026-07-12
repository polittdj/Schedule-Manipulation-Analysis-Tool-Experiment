# ADR-0206 — Mission Ops redesign step 3 (page shell): chapter 08 "Who is overloaded"

## Status
Accepted. Eighth page shell of step 3, applying the chapter-01…07 template (ADR-0197…0205) to
chapter 08 "Who is overloaded" = Resources at `GET /resources`. Presentation only: no engine /
importers / ai change; every figure is read from `compute_resource_loading` — the same loading
the page already charts.

## Decisions
- **`_who_is_overloaded_header(st, granularity)`** prepends to the resources body (latest solvable
  version); returns **empty** when the file carries no resources (the body shows its own notice).
  - **Takeaway h1** — "`O of R resources are over-allocated in at least one <bucket> — the worst
    is <name>, over capacity in N <bucket>s.`" ("all R resources stay within capacity" when clean).
  - **6-KPI strip** — Resources loaded · Over-allocated · Within capacity · Total work (days) ·
    Busiest resource · <Bucket>s covered.
  - **Two composition bars** (`_status_stack`): **Resource allocation** (Within capacity vs
    Over-allocated resources) and **Overload concentration** (the busiest resource's timeline —
    over vs within capacity per bucket).
- Data sources are all pre-existing (`ResourceLoad.over_allocated_periods`, `peak_period`,
  `total_work_minutes`, the bucket periods). No new math.

## Consequences
- Resources now reads as chapter 08. Chromium-verified console + daylight, zero console errors
  ("4 of 32 resources over-allocated — the worst is Electric Contractor, over capacity in 2
  months" on the golden). Part of the bundled 08-12 PR; version bump + lockstep are in the
  bundle's finalization.
