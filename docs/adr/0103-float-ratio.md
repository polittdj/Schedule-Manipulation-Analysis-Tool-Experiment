# ADR-0103 — Float Ratio™, computed period to period

Date: 2026-06-19 · Status: accepted · Builds on ADR-0087 (Bible formula extraction), ADR-0080
(stored vs recomputed float), ADR-0100/0101 (FEI/BRI, CEI variants — the single-snapshot + trend
pattern this follows)

## Context

Float Ratio™ was the one Acumen Fuse metric the project had carried as **blocked** ("proprietary, no
extractable formula"). The operator asked to figure out how to calculate it and build a formula that
works **period to period**. Re-reading the NASA Acumen metric library (the "Bible", the same `.aft`
that supplied BEI/HMI/CEI/FEI/BRI) shows that was wrong: the library carries an explicit, named
`<Metric>` for it — it was never unbuildable, just un-found.

```
<Name>Float Ratio™</Name>
<Description>Average of activity float divided by remaining duration.</Description>
<Formula>AVERAGE(TotalFloat / RemainingDuration)</Formula>     ← canonical, threshold-bearing entry
<Remarks>… Includes normal activities that are planned or in-progress.</Remarks>
```

The library also carries a second algebraic form on other entries — `AVERAGE(TotalFloat) /
AVERAGE(RemainingDuration)` (the ratio of the means) — plus near-CP and CP-filtered variants. The
`PrimaryFilter` on every entry agrees: Normal activities, Planned **or** In-Progress, **not** Complete,
not Milestone/Summary/Hammock.

## Decision

Add `engine/metrics/float_ratio.compute_float_ratio(schedule, cpm_result=None)` returning **both**
Bible forms over that population:

- `float_ratio` — the canonical **mean of per-activity ratios**, `AVERAGE(TotalFloat/RemainingDuration)`
  (threshold-bearing); offenders cited are the very-tight activities (per-activity ratio `< 0.1`, the
  Bible's "Low" band).
- `float_ratio_aggregate` — the **ratio of means**, `sum(TotalFloat)/sum(RemainingDuration)`; robust to
  activities with a tiny remaining duration, which can otherwise blow up the mean-of-ratios.

Total float is the source-tool's **stored** progress-aware value where present (`effective_total_float`,
ADR-0080), else recomputed CPM float; remaining duration is the stored value, else `duration ×
(100−%complete)/100`. Both are converted to working **days** on the schedule's own calendar before
dividing (unit-consistent even with elapsed durations), and activities with no remaining duration are
skipped (division guard). The metric is informational — `IncludeInDCMA=false`, no pass/fail — so the
result status is `NA` and the bands (`<0.1` very tight · `0.1–0.3` tight · `0.3–0.6` healthy · `>0.6`
generous) live in the metric dictionary.

**Period to period.** Float Ratio is single-snapshot, so `trend.compute_float_ratio_trend` scores each
version on its own and carries the **delta** (`this − prior`, `None` on the first version) alongside the
per-version value and the aggregate. `/trend` renders a "Float Ratio™ across periods" chart (mean +
aggregate lines) and the per-version `indices` carry `float_ratio` / `float_ratio_aggregate` /
`float_ratio_delta`.

## Consequences

- The last deferred Acumen metric is now implemented and surfaced; the operator's backlog has no
  remaining blocked items.
- **Validation (multiple ways).** (1) Formula verbatim from the authoritative Bible. (2) Hand-computed
  synthetic unit tests pin both forms, the population filter, the remaining-duration fallback, the
  division guard, negative float, and the period-over-period delta. (3) Real-schedule cross-check: on
  the Large Test File the Float Ratio population's **average remaining duration = 18.4 working days**,
  matching Acumen's reported **Avg. Remaining Duration ≈ 18** on the comparison files — a direct check
  of the denominator population against real Acumen output (Acumen does not itself export Float Ratio,
  so this is the strongest available external anchor). On that (deliberately loose) test schedule the
  ratio is high — the correct forensic signal: "High Float 44d" covers ~70% of activities, i.e.
  excessive float / probable missing logic, exactly the Bible's `>0.6` "generous — check for poor
  logic" band.
- The mean-of-ratios form is, by construction, sensitive to near-zero-remaining-duration activities
  (inherent to Acumen's own `AVERAGE(TotalFloat/RemainingDuration)`); the aggregate form is shipped
  alongside as the stable companion, and the very-tight offenders are cited per §6.
