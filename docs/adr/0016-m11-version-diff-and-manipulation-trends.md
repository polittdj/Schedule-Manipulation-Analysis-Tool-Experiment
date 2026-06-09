# ADR-0016: M11 UniqueID version diff + manipulation-trend detection

- **Status:** Accepted
- **Date:** 2026-06-08 (session A13 — Phase 2 build, milestone M11, continuous A7 sitting)
- **Relates to:** §6.D (forensic / manipulation trends), §6.B (UID-only matching), `BUILD-PLAN.md M11`, RTM D1/B3
- **Builds on:** ADR-0013 (§E change metrics), ADR-0015 (Finding/Citation), ADR-0010 (CPM/critical)

## Context
§6.D requires the local analysis to surface **schedule-manipulation trends** — deleting
logic, shortening durations, deleting tasks, and (DECM 29I401a / 06A504*) changing baseline
or actual dates to keep a target/critical path from slipping — plus a CPM trend, each
**cited** (file + UID + task). M11 builds the structural diff this rests on and the
detector, and validates it against the P2/P5 golden.

## Decision
1. **`engine/diff.py`** — `diff_versions(prior, current)` matches by **UniqueID only**
   (summaries excluded) and returns a `VersionDiff`: `added_tasks` / `deleted_tasks`,
   `changed_tasks` (per-UID `TaskDiff` of `FieldDelta`s over a fixed tracked-field set:
   durations, baseline/actual/forecast dates, % complete, constraint), and `added_links` /
   `removed_links` (relationship set diff keyed by pred+succ+type+lag). It states *what*
   changed; intent is the detector's job. This is the substrate for the comparison views.
2. **`engine/manipulation.py`** — `detect_manipulation(current, prior)` emits cited
   `Finding`s (reusing M10's `Finding`/`Category`/`Severity`/`Citation`) for: **deleted
   tasks** (HIGH if the task was on the prior critical path), **deleted logic**, **shortened
   durations** on still-incomplete activities, **baseline-date changes** (29I401a, HIGH),
   and **edited actual dates** (06A504*, HIGH — a *date→different date* edit, not a normal
   None→date progress update). Severity-ordered; every finding carries the underlying delta
   as citations — no manipulation is ever *asserted* without the evidence attached.
3. **No false positives on honest progress (validated).** For the P2→P5 golden the detector
   returns **nothing**: baselines are unchanged, no tasks/logic were deleted, no actuals
   were edited, and no incomplete duration was shortened — the −99-day slip came from the
   data date advancing, not manipulation. The diff confirms it (0 added/deleted, 106 changed
   forecast/progress fields, 2 links added, 0 removed). A test asserts this silence; the
   synthetic tests prove each detector fires on a real signal. This separation (honest slip
   vs manipulation) is the forensic value.
4. **`trend_across_versions(schedules)`** — for an ordered series (≤10) returns a `TrendPoint`
   per version (CPM project-finish date, completed / in-progress / critical counts), the
   §6.D CPM-and-progress trend that feeds the dashboard charts and the narrative. P2→P5:
   finish 2027-08-30 → 2027-12-07, completed 20 → 27, critical 41 → 37.

## Consequences
- RTM **D1 → ▣** (the deterministic manipulation/diff/trend engine is done and cited; the
  AI *story* over it is M12) and **B3** gains the explicit UID-only `diff_versions` evidence.
- `VersionDiff` + the manipulation `Finding`s + `TrendPoint`s are the inputs for the M12
  narrative (the AI only rephrases these cited facts), the M13/M14 comparison & trend views,
  and the M17 final report.
- diff 100% / manipulation 98% line+branch cov; full suite 385 passing; parity gate green;
  ruff/mypy(strict)/bandit clean.
