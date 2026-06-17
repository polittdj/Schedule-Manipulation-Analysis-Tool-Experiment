# ADR-0063 — Diagnostic Brief: trends over time + risks / opportunities / recovery plan

Date: 2026-06-17 · Status: accepted

## Context

Operator: *"On the Diagnostic Brief, in addition to what you have, write a high-level summary of
the trends you observe over time from schedule to schedule. Identify risks, opportunities, and
define potential recovery plans and suggestions. Use proper English and make it easy to read."*

The `/brief` page (`ai/brief.py`, `build_brief`) had four sections — *What this brief covers*,
*The finish story*, *Questions the data raises*, *How to verify* — all deterministic, every
paragraph cited (§6). It surfaced outliers as questions but offered no consolidated trend read
and no risk/opportunity/recovery guidance.

## Decision

Add two sections (everything still engine-computed and **cited**):

1. **"Trends over time"** (`_trends_section`) — a plain-English read of what moved across the
   loaded versions: the computed finish (days + direction), overall completion %, the **count of
   incomplete critical activities** (a growing critical path = a more fragile plan), and the
   **count of activities behind their logic** (negative total float = schedule pressure). With a
   single version it states that there is no trend yet and to load earlier updates. Inserted
   after *The finish story*.

2. **"Risks, opportunities, and recovery plan"** (`_risk_recovery_section`) — each item is
   computed from the newest version and pairs the finding with a concrete recovery lever:
   - **Risk** — negative-float activities (cited, with "re-sequence / fast-track / renegotiate
     the date, then re-run").
   - **Opportunity / risk** — high-float (> 44 wd) incomplete activities (slack to pull the path
     in, but likely missing successor logic — "tie them in").
   - **Opportunity** — activities finished ahead of baseline (earned margin to protect).
   - **Risk** — a wide finish-forecast spread (> 45 days) between the logic-based and pace-based
     methods (unmanaged uncertainty — "reconcile / re-estimate to-go durations").
   - A healthy-plan fallback when none of these fire. Inserted after *Questions the data raises*.

The page (`_brief_body`) and the Word export (`brief_blocks`) iterate `brief.sections`
generically, so both pick up the new sections with no further change.

## Scope / safety

Additive and deterministic — no engine/CPM/metric change → **parity 10/10**. Every new paragraph
carries citations (the §6 brief test covers all sections; new tests also pin the two sections, a
recovery suggestion, and the single-version trends note). Reuses existing thresholds
(`HIGH_FLOAT_DAYS`, `FORECAST_SPREAD_DAYS`) and helpers (`_drivers`, `non_summary`,
`compute_finish_forecasts`). Full suite **885 passed**; engine cov 97%. (AI rephrasing of the
brief prose remains figure-gated as before; this change only adds cited content.)
