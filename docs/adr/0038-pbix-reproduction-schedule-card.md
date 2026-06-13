# ADR-0038 — PBIX reproduction, page 1: the Schedule Card (Metrics page)

Date: 2026-06-13 · Status: accepted

## Context

M18 item 6 (operator): reproduce the reference deck's visuals; the 14-page spec lives
in `docs/PLAN/PBIX-VISUALS.md`. The work is multi-PR. This PR delivers **page 1
("Metrics" — the schedule's ID card)**, the deck's landing page, which the coverage map
flagged as needing only two new engine pieces; the rest of its visuals reuse the
completion-performance and CPM outputs the engine already computes.

## Decisions

1. **Two new engine helpers** (`engine/metrics/schedule_card.py`, lightweight dataclasses
   — deliberately *not* `MetricResult`, so the metric-dictionary coverage test is
   unaffected):
   - `compute_activity_makeup` — the deck "Schedule Task Makeup" (milestone / normal /
     summary counts) and the activity-status split (complete / in-progress / planned).
     Population is non-summary activities; the summary *count* excludes MS Project's
     UID-0 project row (the Acumen convention, shared with `ai/briefing.py`).
   - `compute_constraint_distribution` — the deck "Primary Constraint" table: count +
     percent per `ConstraintType`, most-common first, ties broken by name. These were
     the two documented engine gaps behind page 1.
2. **A new `/card/{name}` page** (`_card_body`) reproduces page 1: the four count/percent
   tables (makeup, status, completion performance, constraint distribution — rendered as
   tables with inline percent bars, dependency-free) and the KPI **stat-card row**
   (earliest start, computed finish, data date, % activities complete, critical-incomplete
   count, to-go activities, to-go milestones, avg days ahead/late, % elapsed since last
   finish). Every figure is reused from the schedule's existing `_Analysis` (no CPM
   recomputation) and is verifiable on the full report (linked).
3. **Reachable from the dashboard** (a "Card" row action per schedule) and carries the
   shared Ask-the-AI panel like every page. The full report (`/analysis/{name}`) is
   unchanged — the card is the deck-faithful *overview*, the report stays the deep view.

## Scope / safety

Pure presentation over existing engine outputs plus two additive, tested helpers; parity
untouched (10/10); air-gap test extended over the new page; nothing leaves the machine.
RatioMeasure stays unimplemented (it does not exist in the deck's model — ADR-0033), and
the four documented deck defects are **not** reproduced.

## Remaining PBIX pages (next PRs, `docs/PLAN/PBIX-VISUALS.md`)

Cross File Comparison (4) · Float Analysis (5) · the Finishes / DATA Date Finishes
month curves (6–7) · WBS-grouped Completion + SPI/ES pivots (8–9) · Slippage curves
(12) · the Carnac forecast cards (13). Each reuses existing metrics plus the few
remaining gaps (activity-type profile, WBS pivots, start/finish curves, float sums).
