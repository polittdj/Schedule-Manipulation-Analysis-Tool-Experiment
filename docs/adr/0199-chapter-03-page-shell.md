# ADR-0199 — Mission Ops redesign step 3 (page shell): chapter 03 "What drives the date"

## Status

Accepted. Third page shell of step 3, applying the chapter-01/02 template (ADR-0197/0198) to
chapter 03 "What drives the date" = Path Analysis at `GET /path`. Presentation only: no
`engine` / `importers` / `ai` change.

## Context

`/path` is an interactive, client-side trace (`path.js` over `/api/driving`) — its body renders
controls and an empty view, computing nothing server-side. But the per-schedule `analysis.cpm`
(built server-side, and already **scoped to any global Analysis Target**) carries the critical
path, so a data-driven headline can be rendered without any new computation or a chosen target.
Chapter 03's chrome already fires because `/path`'s title "Path Analysis" is registered to the
chapter in the spine.

## Decisions

- **`_what_drives_header(sch, analysis)`** prepends to the path body, anchored on the **latest**
  loaded version:
  - **Takeaway h1** — "`The finish rides on a critical path of N activities carrying <float
    phrase> — its longest single activity is <name> at D working days.`" The float phrase reports
    0 / negative float honestly; N=0 degrades to "No critical path resolves for this version."
  - **6-KPI strip** — Critical-path activities · Path total float · Longest driver (days) · On the
    critical path (%) · Computed finish · Near-critical (≤ 4d).
  - **Two composition bars** (`_status_stack`): **Critical exposure** (incomplete activities by
    total-float band 0 / 1-4 / 5-9 / 10+ d) and **Path composition** (Critical path vs Has slack).
- **Data sources are all pre-existing** — `cpm.critical_path` (unique_ids with total_float ≤ 0,
  already scoped), `cpm.timings[u].total_float` for the path float, `Task.duration_minutes` for the
  longest single driver, `offset_to_datetime` for the finish, and `analysis.activity_rows` float
  values for the exposure bands (the same bucketing chapter 01 uses). No target UID needed — the
  scoped CPM already reflects the global target.
- The interactive trace (`#pathControls`, `path.js`, `#pathView`, the SSI directional-path options,
  drag analysis, export bar) is untouched — the header is additive above it. No new CSS (reuses the
  ADR-0197 classes).

## Consequences

- Path Analysis now reads as chapter 03: kicker → takeaway → drivers KPIs → exposure & composition
  bars → the interactive trace → Continue → Chapter 04. Verified in Chromium (console rail +
  daylight top bar), zero console errors; counts are internally consistent (critical + slack = total
  activities; float bands sum to the incomplete count).
- Version 1.0.8 → 1.0.9 (cache-bust); wheel + nine installers rebuilt in lockstep. Chapters 04-12
  follow, one per PR; the cross-cutting chart-contract toolbar remains a dedicated follow-up.
