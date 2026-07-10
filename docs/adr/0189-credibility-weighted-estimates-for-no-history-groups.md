# ADR-0189 — Credibility-weighted estimates for groups with no completion history

## Status

Accepted. Operator 2026-07-10: "research and come up with a way for groups with remaining work
but no completion history to not be flagged as unforecastable and find a way to forecast them
even if you have to make some logical estimations and quantify them and note them using best
industry practices and statistical analysis best practices."

## Context

ADR-0188's group-weighted forecast rollup honestly listed groups with to-go work but zero
completions as *unforecastable* — their own throughput is 0/elapsed and extrapolating it is a
division by zero. On real programs (a CAM whose scope starts late, a phase that hasn't opened)
this is common, and "unforecastable" is unhelpfully silent about work that WILL consume time.
The fidelity law forbids silent imputation — but it does not forbid a **quantified, labeled,
statistically grounded estimate**, which is exactly what standard actuarial and program-analysis
practice prescribes for a cell with zero observations.

## Decision — the estimation method (each step is standard, citable practice)

1. **Partial pooling / Bühlmann credibility (empirical Bayes).** The credibility estimate is
   `Z · own-history + (1 − Z) · pooled`, with `Z = n / (n + k)`. A group with zero completions
   has `n = 0 → Z = 0`, so its estimate is **entirely the pooled prior**: the project-wide
   per-activity completion throughput `total completions / (elapsed months × total activities)`,
   scaled by the group's own activity count. This is the same shrinkage logic actuarial science
   uses for cells with no claims history (Bühlmann credibility; empirical-Bayes shrinkage).
2. **Start-execution discount (leading indicator, NDIA PASEG-style).** A group that also isn't
   *starting* on time should not inherit the full pooled rate. The group's SEI (actual starts ÷
   baseline-due starts at the data date) discounts the borrowed rate — **penalize-only**
   (`min(1, SEI)`, a group can't borrow *better*-than-pooled performance from starting early)
   and **floored at 0.25** (a zero-starts group still gets a finite, pessimistic forecast
   instead of infinity). Start-based indices as leading indicators for groups without earned
   history follow the NDIA PASEG / IPMD predictive-measures guidance.
3. **Reference-class range (Flyvbjerg's outside view).** The point estimate is bracketed by the
   P75 (early) / P25 (late) of the per-activity rates the groups **with** history actually
   demonstrated on this project — an empirical distribution of comparable executions, not a
   model assumption. Requires ≥ 2 history groups; otherwise the range is honestly omitted.
4. **Quantified + labeled, never silent.** Every estimated group carries a `basis` string
   stating the borrowed rate, Z = 0, the SEI discount applied, the floor, and the
   reference-class bound. The UI renders estimates in a separate "Estimated groups" table with
   a methodology note; the bottleneck finish gets an **ESTIMATED** badge when an estimated
   group is the limiter (`rate_finish_is_estimated`).
5. **Two coverages, side by side.** `weighted_spi_t`/`ieac_finish` stay **direct-only**
   (measured groups, exactly as ADR-0188 shipped); `weighted_spi_t_all`/`ieac_finish_all` add
   the estimated groups (pooled exact SPI(t) × their SEI adjustment, weighted by to-go count).
   The panel shows *Rollup (direct only)*, *Rollup (full coverage)*, and *Top-down* columns so
   the estimate's effect is itself visible, never blended invisibly.
6. **"Unforecastable" survives** — reserved for the truly impossible: no data date, no elapsed
   time, or zero completions anywhere in the project (no pooled prior exists to borrow).

## Consequences

- `engine/forecast.py`: `EstimatedGroupForecast` (frozen), extended `GroupRollup`
  (`weighted_spi_t_all`, `ieac_finish_all`, `estimated`, `rate_finish_is_estimated`),
  `compute_group_rollup` rewritten around per-group tuples + `_percentile`.
- `/forecast` "Project rollup" panel: 3-column comparison, estimated-groups sub-table with
  per-group basis, methodology explainer, ESTIMATED badge; vizhints callout updated.
- Tests: the Hot/Cold rollup schedule asserts Cold is *estimated* (not unforecastable), the
  discount is bounded `[0.25, 1]`, the basis is labeled ("ESTIMATE", "Z = 0"), full-coverage
  SPI(t) ≤ direct-only (the discount can only pull down), and a no-data-date schedule still
  lands in `unforecastable`.
- Sources: Bühlmann credibility (Loss Data Analytics, ch. Credibility), empirical-Bayes
  shrinkage, NDIA PASEG v6 / IPMD Predictive Measures Guide (start-based leading indices),
  Flyvbjerg reference-class forecasting.
