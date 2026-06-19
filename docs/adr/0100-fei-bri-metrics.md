# ADR-0100 — FEI and BRI metrics (Acumen Bible formulas, validated)

Date: 2026-06-19 · Status: accepted · Builds on ADR-0089 (BEI), ADR-0098 (CEI)

## Context

Two more SEM indices appear in the operator's Acumen reports and were extractable from the NASA Acumen
metric library (the "Bible", `.aft`): **FEI** (Forecast Execution Index) and **BRI** (Baseline Realism
Index). Both are single-snapshot (unlike the pairwise CEI/HMI), so they could be validated directly from
the files already provided.

## Decision

`engine/metrics/fei_bri.py`, over the Normal value-task population (non-summary, non-milestone), with
`ProjectTimeNow` = the schedule's status date — exact Bible formulas:

- **FEI (Forecast Execution Index)** — forward / to-go, two cuts:
  - `fei_starts = count(Start ≥ now) / count(BaselineStart ≥ now)`
  - `fei_finish = count(Finish ≥ now AND not finished early) / count(BaselineFinish ≥ now)`
  - `> 1` ⇒ more remaining work is forecast in the window than the baseline placed there (a to-go bow
    wave). NA when nothing is baselined into the window / no status date.
- **BRI (Baseline Realism Index, cumulative)** — backward-looking:
  - `bri = count(BaselineFinish ≤ now AND actually finished ≤ now) / count(BaselineFinish ≤ now)`
  - The baselined-due activities that did **not** finish are the offenders (citable).

Surfaced per version on the Trend page (`/trend`): **BRI** joins the MEI/BEI/EPI index chart and **FEI
(Starts/Finish)** gets its own chart; the per-version `indices` carry `fei_starts`/`fei_finish`/`bri`.
Documented in the metric dictionary.

## Consequences

- **Validated against the operator's Large Test File** (status date 2025-03-10):
  - **BRI = 0.51, denominator 1228 EXACT** (= the BEI baselined-due population).
  - **FEI Starts numerator 828 EXACT**, FEI Finish denominator 316 EXACT; the ratios (≈ 2.80 / 2.92 vs
    Acumen 2.78 / 2.89) carry a few-task residual from the `.mpp`→MSPDI **conversion** (mpxj vs Acumen's
    native read), not the formula — the same tolerance the BEI validation documented.
- Verified multiple ways: the Bible formula, the exact component counts (828 / 316 / 1228), the ratio,
  and hand-verified synthetic unit tests checking numerator and denominator independently.
- BRI Current (the 30-day-window variant) and FEI milestone cuts are deferred (not shown in the operator's
  report); the cumulative/task cuts validated here are what shipped.
