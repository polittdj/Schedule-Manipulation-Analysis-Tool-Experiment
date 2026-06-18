# ADR-0083 — Baseline compliance: Normal-only population + Half-Step-Delay BSC (Acumen-exact)

Date: 2026-06-18 · Status: accepted · Supersedes the ADR-0013 baseline-start-compliance residual

## Context

The operator supplied the authoritative Acumen Fuse metric library (`NASA_Metrics_Complete.aft`) and
Acumen's actual reports for a real progressed schedule ("Large Test File", 2,125 activities, Time Now
2/7/2025). Auditing the tool's `compute_baseline_compliance` against Acumen's **Program-Summary** /
**Advanced** report exposed two faults:

1. **Population.** The tool counted over *all* non-summary activities. Acumen's baseline-compliance
   metrics are **Normal-only** (the Bible inclusions carry `Milestone=false`), so the tool over-counted
   every bucket by the milestone count — on the Large File **+131** (1,333 vs 1,202 forecast-to-finish,
   etc.).
2. **Baseline Start Compliance (BSC).** The tool computed BSC as *started-on-time / forecast* (actual
   start ≤ baseline **start**). The Bible formula is the **Half-Step-Delay** definition —
   `count(actual start ≤ baseline FINISH) / forecast_to_be_started` — which is asymmetric with Baseline
   Finish Compliance. This is the long-standing **ADR-0013 documented residual** (engine 38/23 vs Acumen
   41/25 on the goldens).

The Bible formulas also pin two details the tool had slightly off: "due" is strict (`baseline < now`,
not `≤`), and the on-time/late comparisons are **INT (date-only)**; "Not Completed" is `percent_complete
< 100` over the forecast-to-finish set.

## Decision

Rebuild `compute_baseline_compliance` to the Bible exactly:

* **Population** = non-summary **and non-milestone** (Normal) activities.
* **Due** = strict `baseline < status`.
* **Completed On Time / Late** over activities that have actually finished (`actual_finish < now`),
  compared **by date** (`INT`): on-time `finish_date ≤ baseline_finish_date`, late `>`. **Not Completed**
  = forecast-to-finish with `percent_complete < 100`.
* **Started On Time / Late** by date against the baseline **start**; **Not Started** = no actual start.
* **Baseline Start Compliance** = `count(started AND actual_start_date ≤ baseline_finish_date) /
  forecast_to_be_started` (Half-Step-Delay).
* **CEI (Start)** stays = *Started On Time %* (`started_on_time / forecast`) — it is **distinct** from
  BSC; the old test that asserted `CEI(Start) == BSC` only passed because BSC was mis-computed as the
  started-on-time ratio. CEI (Finish) remains = Baseline Finish Compliance.

## Validation / parity

Against Acumen's real report on the Large Test File, **all 10 baseline-compliance metrics now match
exactly**: Forecast-to-Finish 1202, On-Time 116, Late 488, Not Completed 594, BFC 10%; Forecast-to-Start
1228, On-Time 200, Late 515, Not Started 513, **BSC 22%**.

Parity-safe and **tightened**: the goldens carry **0 milestones**, so the population change does not move
them; every golden baseline count is unchanged, and **BSC now equals Acumen exactly (41 / 25)** — the
ADR-0013 residual is *resolved*, so `test_parity_gate` / `test_evm` flip from asserting the residual to
asserting the exact golden. `pytest -m parity` **10/10**; full gate green (946 passed);
`docs/METRIC-DICTIONARY.md` regenerated; ruff/format/mypy/bandit clean.

## Scope of the wider audit

This is one fix from the standing audit of the tool against the authoritative library. Confirmed already
matching Acumen on the Large File: the 9-metric Schedule-Quality ribbon's **8** float/logic metrics
(Missing Logic 22, Logic Density 3.14, Critical 33, Hard 1, Negative Float 31, Lags 8, Leads 1, Merge
156 — ADR-0079/0080/0081). Open residual: **Insufficient Detail™** (tool 41 vs Acumen 43) — the Bible
`OriginalDuration / ProjectDuration > 0.1` reproduces 43 only with *current* duration while the operator's
earlier TP3 Fuse run (8) needs *baseline* duration; the two Acumen-verified files demand contradictory
fields, so it is held as a characterised proprietary-™ residual rather than re-pinned on an imperfect
formula. Further metric families (BEI/HMI/CEI bow-wave, critical-path, industry standards) remain to audit.
