# ADR-0087 — HMI (Hit or Miss Index): new period-over-period metric

Date: 2026-06-18 · Status: accepted · Builds on ADR-0085/0086 (formula-audit), ADR-0010 (DCMA-14)

## Context

The formula-audit asked whether the tool's **MEI** (Milestone Execution Index) should be reconciled
with the Bible's **HMI** (Hit or Miss Index). Investigation showed they are **different metrics**, not a
mismatch:

- **MEI** is *cumulative / single-snapshot*: milestones finished by the data date ÷ milestones the
  baseline placed by then (BEI restricted to milestones). Correct as-is — left untouched.
- **HMI** is *period-over-period*: every Bible HMI formula uses **both** `ProjectPreviousTimeNow` and
  `ProjectTimeNow`, scoring hits/misses **within the current status period**. It needs *two* consecutive
  snapshots.

The operator chose to **implement HMI as a new metric** (it was simply missing, not miscomputed).

## Decision

New `engine/metrics/hmi.py` :func:`compute_hmi(current, previous_time_now)` implementing the Bible
`HMI - Value Tasks` / `HMI - Value Milestones` formula exactly:

```
hits   = activities with PrevTimeNow < BaselineFinish <= TimeNow,
         complete, and Finish (actual finish) > PrevTimeNow
due    = activities with PrevTimeNow < BaselineFinish <= TimeNow
HMI    = hits / due
```

Tasks (Normal activities) and milestones are scored separately (Bible PrimaryFilter inclusions:
`HMI - Value Tasks` = Normal only; `HMI - Value Milestones` = milestones only). An activity baselined
to finish this period whose work actually landed in an **earlier** period (`Finish <= PrevTimeNow`) is
**not** credited here — it was a hit in its own period — matching the standard (non-"adjusted") formula.
Offenders are the **misses** (citable, §6). NA (count 0 of 0) when the period is undefined (no
current/previous data date or non-advancing) or empty — never a fabricated value.

Because HMI is inherently between two snapshots, `engine/trend.py` adds `HMISeries` +
:func:`compute_hmi_trend(schedules)`: each version is scored against its **predecessor's** data date
(versions ordered oldest→newest; the first version has no predecessor → `None`). It is surfaced in the
Trend view (`/api/trend` per-version `indices.hmi_tasks` / `hmi_milestones`) and drawn by `trend.js` as
a dedicated "Hit or Miss Index (HMI) across periods" chart, alongside the cumulative MEI/BEI/EPI.

## Validation

New `tests/engine/metrics/test_hmi.py` (7 cases): hit, miss (cited), out-of-period exclusion, the
earlier-period non-credit nuance, task/milestone separation, NA guards, and the trend series (first
version `None`, ordering). On the real goldens, Project5 vs Project2 reads **HMI(Tasks) = 0.05** (1 hit
of 19 baselined-due that period, 18 misses) — a meaningful period-performance signal. Full gate green
(954 passed); ruff/format/mypy/bandit clean; `METRIC-DICTIONARY.md` regenerated with both HMI entries.

## Notes

Purely additive — no existing metric or value changes (parity untouched). The Bible also defines
"adjusted" HMI variants (re-baseline tolerant) and Start-based HMI; this ADR ships the standard
finish-based Tasks/Milestones HMI as the primary metric. The others can follow if the operator wants
them.
