# ADR-0202 — Mission Ops redesign step 3 (page shell): chapter 05 "How it moved"

## Status

Accepted. Fifth page shell of step 3, applying the chapter-01/02/03/04 template
(ADR-0197/0198/0199/0200) to chapter 05 "How it moved" = the multi-version Trend at
`GET /trend`. Presentation only: no `engine` / `importers` / `ai` change; every figure is
read from the trend the page already tabulates.

## Context

`/trend` opened straight into the version table and quality-trend sentences with no
headline. The route already computes `trend_across_versions(schedules, cpms)` — per-version
`TrendPoint`s carrying the CPM `project_finish`, completed / in-progress / critical counts —
and the ch01 `compute_activity_makeup` is available for the latest version's status mix, so
a data-driven headline needs no new computation. Chapter 05's chrome already fires because
`/trend`'s title "Trend" is registered to the chapter in the spine, and the header renders
only past the existing `len(schedules) < 2` guard.

## Decisions

- **`_how_it_moved_header(schedules, cpms)`** prepends to the trend body:
  - **Takeaway h1** — "`Across N versions the finish <slipped D calendar days / pulled in D
    / held steady> — S of K updates slipped it — and the current forecast finish is
    <date>.`" (singular/plural agreement; the net move is first→last finish in calendar
    days, matching the evolution page's slip basis).
  - **6-KPI strip** (`_stat_cards`) — Versions compared · Current finish · Net finish move ·
    Updates that slipped (`S / K`) · Biggest single move (max |per-update delta|) · Critical
    now.
  - **Two composition bars** (`_status_stack`): **Update behaviour** (per-update finish
    deltas bucketed Slipped / Held / Improved) and **Where the work stands** (latest
    version's Complete / In progress / Not started over the activity total).
- **Data sources are all pre-existing** — `TrendPoint.project_finish` date deltas for the
  moves, `TrendPoint.critical` for the criticality KPI, and `compute_activity_makeup`
  (already used by chapter 01 and the trend API's version rows) for the status mix.
- The trend scaffold (version table, quality-trend sentences, pairwise signals, focus form,
  trend.js charts, export bar) is untouched — the header is additive above it. No new CSS
  (reuses the ADR-0197 classes).

## Consequences

- Trend now reads as chapter 05: kicker → takeaway → slippage KPIs → behaviour & work bars →
  the version table and charts → Continue → Chapter 06. Verified in Chromium (console rail +
  daylight top bar), zero console errors; counts are internally consistent (Complete 27 +
  In progress 2 + Not started 97 = 126 in scope on the golden pair; net +148 d = the known
  P2→P5 slip, agreeing with chapter 04's takeaway).
- Version 1.0.11 → 1.0.12 (cache-bust); wheel + nine installers rebuilt in lockstep.
  Chapters 06-12 follow, one per PR; the chart-contract toolbar remains a dedicated
  follow-up.
