# ADR-0044 — Critical-path evolution animation (M18 item 7)

Date: 2026-06-16 · Status: accepted

## Context

M18 item 7: a Bow-Wave-style animation of how the **critical path** evolves across loaded
versions — which activities enter/leave the path, duration changes on it, and the
schedule-optics signals (durations cut on the path, logic removed) that show a slip being
absorbed rather than recovered. The PBIX reproduction spine (item 6) is complete; this is
the next forensic surface.

## Decisions

1. **New engine module** (`engine/path_evolution.py`): `compute_path_evolution(schedules,
   cpms)` → `PathEvolution` of per-version `CriticalSnapshot`s (oldest → newest). Each
   snapshot carries the version's critical path (`cpm.critical_path`), the set deltas vs the
   prior version (**entered / left / stayed**), the **duration changes on the path**, the
   calendar-day **finish movement**, and the schedule-optics signals — **durations shortened
   on the path** and **logic links removed** — which **reuse the canonical
   `engine.manipulation.detect_manipulation`** (filtered to the current critical set) so the
   flags match the Compare/Trend pages exactly. Lightweight frozen dataclasses, not
   `MetricResult` (the established PBIX-era pattern); nothing fabricated (the first version
   has no prior, so its change fields are empty).

2. **New `/evolution` page** (`_evolution_body` / `_evolution_data`,
   `static/path_evolution.js`): a Prev/Next/Auto-play stepper (mirroring `cei.js` /
   `drift.js`) rendering each version's critical path as a list — entered (green), stayed
   (grey), a `▲dur` badge for a duration change — with activities that left listed struck
   through, and a callout for the finish movement + optics signals. The callout flags the
   red-flag combination: the path **shedding work** (left / shortened / logic removed) while
   the finish **holds or improves**. Reachable from the header nav (always) and the
   dashboard's multi-version action row (≥2 versions). Requires ≥2 analyzable versions.

3. **Export** — `/export/{fmt}/evolution` (xlsx + docx) via `path_evolution_tables`
   (per-version critical count, finish move, entered/left/duration-changed/shortened/removed
   counts), consistent with every other view.

## Scope / safety

Pure analysis over the cached per-version CPM results plus one additive, tested engine
module; parity untouched (10/10 — the critical-path definition and CPM are unchanged); the
air-gap test extended over the new page and `path_evolution.js`; nothing leaves the machine.
The optics signals delegate to the existing manipulation detector rather than re-deriving
them. Verified on the golden P2→P5 pair: critical path 43 → 37, 6 activities left, finish
slipped 99 days (the known Net Finish Impact), no shortened-on-path / removed logic (a clean
pair). Remaining M18 item: 8 (forecast explainer + Trend page expansion).
