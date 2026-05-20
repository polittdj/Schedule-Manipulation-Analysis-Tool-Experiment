# DCMA Metrics 1-4

Each metric is a pure function `run_<name>(schedule, options) -> MetricResult`. Severity is
**binary PASS/FAIL** against a single cited threshold (see
`FIDELITY-DECISION-dcma-severity.md`). A metric whose denominator would be zero **raises**
`MetricError` rather than fabricating a result. Offenders are sorted by UniqueID (deterministic).

| # | Name | Numerator / Denominator | Threshold | Offenders | Offender `value` |
|---|------|-------------------------|-----------|-----------|------------------|
| 1 | Logic (Missing Pred/Succ) | tasks missing a pred and/or succ / all tasks | `<= 5%` | the missing-logic tasks | # of missing ends (1 or 2) |
| 2 | Leads (Negative Lag) | relations with `lag < 0` / all relations | `0%` (any lead fails) | the lead relations | lag minutes (negative) |
| 3 | Lags (Positive Lag) | relations with `lag > 0` / all relations | `<= 5%` | the lagged relations | lag minutes (positive) |
| 4 | Relationship Types | FS relations / all relations | `>= 90%` | the **non-FS** relations | predecessor UniqueID |

Notes:
- Metric 4 is an AT_LEAST metric: the numerator counts the *good* (FS) relations while the
  offenders are the *complement* (non-FS). `MetricResult.percentage` is the FS%.
- Relation-based offenders are keyed by the **successor** UniqueID (the task receiving the tie).
- Metric 1 `MetricOptions(exclude_project_bookends=True)` exempts a lone open start and a lone
  open finish (the DCMA convention that one start milestone may legitimately lack a predecessor
  and one finish milestone may lack a successor). The default is the strict literal count.
- Thresholds are the canonical DCMA 14-Point Assessment values; citations are by assessment name
  because the primary sources were unavailable this session (see
  `FIDELITY-COMPROMISE-dcma-citations.md`).
