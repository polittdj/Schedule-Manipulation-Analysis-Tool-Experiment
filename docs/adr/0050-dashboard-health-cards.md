# ADR-0050 — Dashboard dive-in visuals (per-schedule health cards)

Date: 2026-06-16 · Status: accepted

## Context

Operator request (tab-visuals, item 1 of 4): turn the Dashboard's loaded-schedule overview
into **KPI/health visuals** — status mix, critical %, finish vs. baseline, DCMA pass/fail at a
glance — that **click through to the detailed report**. The Dashboard was a hero + dropzone +
a plain "Loaded schedules" table (name / activities / source / file actions) with no visual
summary.

## Decision

1. **`/api/dashboard`** (`_dashboard_data`) — one health snapshot per loaded schedule, reusing
   the **cached** per-schedule `_Analysis` (one CPM each; no recompute): activity status mix
   (complete / in-progress / planned) and `% complete` from `compute_activity_makeup`, the
   **critical** count/percent from the `float_total_0` band, the **computed finish** vs. the
   stored **baseline finish** (`finish_delta_days`, + = a slip), the data date, and the
   **DCMA-14 verdicts** (`metric_id` / name / PASS·FAIL·NA) for the ribbon. An unschedulable
   file degrades to a flagged card (never a 500).

2. **`dashboard.js`** renders the cards **async** (the landing page stays instant): each card
   is a link to `/analysis/{key}` ("dive in") with a KPI stat row, a **status-mix bar**, and a
   **DCMA-14 ribbon** (green pass / red fail / grey n/a chips). Every visual carries a **legend
   and a one-line description** (ADR-0049 standard); the status bar and chips wrap, so nothing
   overlaps.

3. **Dashboard page** gains a "Schedule health" panel (the `#dashboardHealth` container +
   description) above the existing table, which is retained for the file actions (Open /
   Card / WBS / Save .json).

## Scope / safety

Additive presentation over the existing cached analysis — no engine/CPM/data change; parity
untouched (10/10). The new `dashboard.js` is dependency-free local SVG/DOM (air-gap test
extended over it; the `/` page is already scanned). Verified on golden P5: 126 activities,
27/2/97 status mix (21.4% complete), critical 37 (37.4%), computed finish 2027-12-07 vs.
baseline 2027-07-09 (+151 d), 16 DCMA checks — all cross-checking the report/forecast values.
Tests pin the `/api/dashboard` contract and the page wiring. First of the four tab-visual
passes (Dashboard → Diagnostic Brief → Path Analysis → Report/Analysis).
