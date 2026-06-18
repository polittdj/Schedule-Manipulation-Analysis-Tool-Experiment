# ADR-0085 — BEI: align to the Bible "Tasks" formula (formula-audit)

Date: 2026-06-18 · Status: accepted · Builds on ADR-0010 (DCMA-14)

## Context

First fix from the **formula-audit** the operator requested for the metric families that have no Acumen
*output* in the supplied reports — compare each implemented tool formula/inclusion to the authoritative
`NASA_Metrics_Complete.aft` library and fix mismatches. The Bible's BEI:

```
SUM((BaselineDuration>0)*(ActivityStatus="Complete"))
/ ( SUM((BaselineFinish<=ProjectTimeNow)*(BaselineDuration>0))
    + SUM((((OriginalDuration<>0)+(BaselineDuration<>0)) * ((BaselineStart="")+(BaselineFinish="")) > 0) * 1) )
```

The tool's BEI counted **all** activities finished by the data date over **all** baselined-due activities —
it omitted the Bible's two refinements: the **`BaselineDuration>0`** filter (the "Tasks" variant, so
milestones are not counted — they score via MEI) and the **missing-baseline** denominator term.

## Decision

`compute_dcma14`'s BEI now matches the Bible exactly: numerator = complete activities with
`baseline_duration > 0`; denominator = `(baselined-due tasks with baseline_duration > 0)` + `(activities
with a duration but missing a baseline start/finish)`. Early completions still count (BEI may exceed 1.0).

## Validation / parity

**The goldens validate the Bible formula:** it reproduces Acumen's pinned BEI **0.74 / 0.59** exactly
(same numerator/denominator: 20/27, 27/46; the goldens have no milestones-completed or missing baselines,
so the value is unchanged → **parity 10/10**). On the seeded **TP3** fixture the value moves 0.62 → **0.54**
(7 of 13 — one completed *milestone* is now correctly excluded); on the Large Test File the counts become
the Bible's 646 / 1246 (= 0.52). Two synthetic DCMA-14 unit tests were updated to give their baselined
tasks a real baseline (start + duration), as the Bible requires. `docs/METRIC-DICTIONARY.md` regenerated;
full gate green (946 passed); ruff/format/mypy/bandit clean.

## Note on the formula-audit

BEI's value is **unchanged on every case validated against Acumen output** (the goldens) — the fix is a
definitional refinement that only moves files with completed milestones or missing baselines. Because the
remaining families (HMI/CEI, critical-path, Industry Standards) have **no Acumen output** in the supplied
reports, the audit can only confirm formula structure, not values; this BEI fix is high-confidence only
because the goldens happen to pin it. Where a formula change would move a golden value, it would need
Acumen output to validate before adopting.
