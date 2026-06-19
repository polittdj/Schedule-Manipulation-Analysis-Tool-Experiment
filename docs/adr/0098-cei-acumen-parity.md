# ADR-0098 — Current Execution Index (CEI), Acumen parity (period-over-period)

Date: 2026-06-19 · Status: accepted · Builds on ADR-0087 (HMI), validated vs the operator's Acumen two-period comparison

## Context

The tool already had two distinct "CEI"s — the **bow-wave** monthly index (`engine/bow_wave.py`, forward,
per calendar month) and the EVM baseline `cei_finish` — but **neither is Acumen's DCMA "CEI - Value
Tasks"**. The operator ran the two-period comparison (Large_Test_File v1 2025-02-07 → v2 2025-03-10) and
asked to validate CEI. The single-period reports show CEI = N/A everywhere, confirming CEI is inherently
pairwise. Reverse-engineering the comparison report pinned the exact definition.

## Decision

Add `engine/metrics/cei.compute_cei(prior, current)` — the DCMA **Current Execution Index**, the
**forecast-anchored** sibling of HMI (which is baseline-anchored). For the period `(prev_now, now]`:

- **denominator** = activities the **prior** schedule scheduled to finish in the period and not yet
  complete at `prev_now` (`prior.finish ∈ (prev_now, now]` and incomplete at `prev_now`);
- **numerator** = of those, the ones **actually complete by `now`** in the current schedule
  (`actual_finish <= now`);
- `CEI = numerator / denominator`. Tasks (Normal) and milestones are scored separately. N/A when the
  period is undefined/non-advancing or nothing was forecast in it (matching Acumen's single-period N/A).
  Offenders are the **misses** (forecast-due that did not complete) — citable.

`engine/trend.compute_cei_trend(schedules)` indexes it per version (first = None) like
`compute_hmi_trend`. The Trend view (`/trend`, `static/trend.js`) draws a "Current Execution Index (CEI)
across periods" chart beside the HMI one, and the per-version `indices` carry `cei_tasks`/`cei_milestones`.
Documented in the metric dictionary (`cei_tasks`/`cei_milestones`).

## Consequences

- **Validated EXACT vs Acumen** on the operator's two-period comparison: CEI Value Tasks **24 / 129 =
  0.19**, CEI Value Milestones **1 / 6 = 0.17** (the real `.mpp`s are git-ignored CUI, so the parity
  numbers live here and in `docs/STATE`; committed unit tests pin the formula on small synthetic
  two-period fixtures).
- The tool now reports HMI (baseline-anchored) **and** CEI (forecast-anchored) per period — the two DCMA
  execution indices, distinct from the bow-wave monthly CEI which remains on `/cei`.
- Deferred (smaller, also in the report): the "by status dates **Starts**" variant (~0.10), the
  `Critical` CEI subset, and the "adjusted" (early-completion-credited) variant; the headline finish CEI
  is what shipped. Not yet built: FEI / BRI (single-period, present in the same reports).
