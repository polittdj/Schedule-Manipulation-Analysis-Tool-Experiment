# ADR-0198 — Mission Ops redesign step 3 (page shell): chapter 02 "Can we trust the plan?"

## Status

Accepted. Second page shell of step 3, applying the chapter-01 template (ADR-0197) to chapter 02
"Can we trust the plan?" = the Schedule Quality Ribbon at `GET /ribbon`. Presentation only: no
`engine` / `importers` / `ai` change; every figure is read from the ribbon/audit the page already
computes.

## Context

The Quality Ribbon opened straight into its Fuse-style metric matrix with no headline. Chapter 01
established the page-shell pattern (data-driven takeaway h1 → KPI strip → composition bars) and the
reusable `_status_stack` / `_stat_cards` / `page-takeaway` styling. Chapter 02's chapter chrome
(kicker + Continue footer) already fires here because `/ribbon`'s title "Schedule Quality Ribbon" is
registered to chapter 02 in the spine — so this chapter needs no `chapter=` binding, only the header.

## Decisions

- **`_can_we_trust_header(sch, analysis, ribbon)`** prepends to the ribbon body, anchored on the
  **latest** loaded (schedulable) version:
  - **Takeaway h1** — "`X of Y DCMA-14 quality checks pass — <top structural weaknesses>.`" where
    the weakness clause names the top one or two of: activities missing logic, carrying negative
    float, or sitting on hard constraints (correct singular/plural agreement), or reads "logic is
    complete, with no negative float or hard constraints" when clean.
  - **6-KPI strip** — DCMA checks passed (`X / Y` scored) · Missing logic · Hard constraints ·
    Negative float · Logic density · Insufficient detail.
  - **Two composition bars** (`_status_stack`): **DCMA-14 checks** (Pass / Fail / N/A) and **Logic
    completeness** (Logic wired vs Missing logic over the activity total).
- **Data sources are all pre-existing** — the per-version `RibbonMetrics` the route already builds
  (`compute_ribbon`) and the cached `analysis.audit.checks` (reusing `_status_class` to bucket
  pass/fail/na, so no enum import and no new threshold). Counts are honest; `Y` is the *scored*
  check count (n/a checks excluded), shown as an em dash if nothing is scorable.
- The ribbon matrix, the per-cell drill (`rib-cell` / `ribbon_drill.js`), the export bar, and the
  skipped-version notice are untouched — the header is purely additive above them.
- No new CSS: reuses `page-takeaway` / `ws-kpi` / `ws-bars` / `status-stack` from ADR-0197.

## Consequences

- The Quality Ribbon now reads as chapter 02: kicker → takeaway → quality KPIs → DCMA & logic bars →
  the matrix → Continue → Chapter 03. Verified in Chromium (console rail + daylight top bar), zero
  console errors; the takeaway agrees grammatically and its counts match the matrix.
- Establishes that later chapters that already carry a static title need only the header helper (no
  `_page` chapter binding). Version 1.0.7 → 1.0.8 (cache-bust); wheel + nine installers rebuilt in
  lockstep. Chapters 03-12 follow, one per PR; the cross-cutting chart-contract toolbar remains a
  dedicated follow-up.
