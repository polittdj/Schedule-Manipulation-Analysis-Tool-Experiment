# ADR-0089 — BEI: Acumen "BEI - Value Tasks", validated against real Acumen output (corrects ADR-0085)

Date: 2026-06-18 · Status: accepted · Supersedes the BEI formula of ADR-0085

## Context

ADR-0085 adopted a "Bible Tasks" BEI (numerator = complete activities with `baseline_duration > 0`;
denominator = baselined-due-with-baseline-duration **plus a missing-baseline term**). It matched the
goldens (0.74 / 0.59) but there was **no Acumen BEI output for the Large File** to check the counts.

The operator then supplied Acumen "Quick Add Metrics" / DCMA ribbon reports on the Large File (two
versions). Those give Acumen's actual BEI **and its components**, and the `.aft` library gives the exact
metric definition:

```
BEI - Value Tasks  =  countif(PercentComplete,"=100%") / SUM(IF(BaselineFinish<=ProjectTimeNow,1))
PrimaryFilter: Normal=true, Milestone=false, Summary=false      (Normal activities only)
```

So Acumen's BEI is simply **complete Normal tasks / Normal tasks baselined-due** — milestones and
summaries excluded by **activity type**, with **no baseline-duration filter and no missing-baseline
term**. ADR-0085's two refinements were both wrong; on the Large File they produced 668 / 1269 = 0.53
vs Acumen's **632 / 1228 = 0.51**.

## Decision

`compute_dcma14`'s BEI now implements the exact formula: numerator = complete Normal tasks
(non-summary, non-milestone, `percent_complete >= 100`); denominator = Normal tasks with
`baseline_finish <= status`. Early completions still count (BEI may exceed 1.0); offenders are the
baselined-due Normal tasks not actually finished.

## Validation (against real Acumen output)

- **Goldens EXACT:** Project2 20/27 = **0.74**, Project5 27/46 = **0.59** (parity 10/10, unchanged).
- **Large File denominator EXACT:** v2 = **1228** (Acumen 1228); numerator 634 vs Acumen 632 — within
  **2 tasks of 632** (a ~0.16 % residual; 1 is the lone LOE-flagged task, the other an unmapped MSPDI
  edge — tracked, like the High-Float residual of ADR-0012). BEI 0.52 vs Acumen 0.51 is that rounding.
- TP3 seeded fixture re-pins 0.54 → **0.67** (8 complete Normal / 12 Normal baselined-due; the milestone
  the baseline placed this period is now correctly excluded from the denominator by type).
- The two synthetic DCMA-14 BEI unit tests still pass unchanged. Full gate green (958); ruff/format/
  mypy/bandit clean; `METRIC-DICTIONARY.md` regenerated.

## Note

This is the BEI fix done *right* — with hard Acumen output, not Bible-formula authority alone. It is the
first metric reconciled against the operator's new Large-File ribbon reports; the same reports also
**validate HMI exactly** (v2 = 0 of 24 due tasks, milestone 0 of 1, v1 = N/A — matching `compute_hmi`)
and carry CEI/FEI/BRI/TC-BEI values for future audits.
