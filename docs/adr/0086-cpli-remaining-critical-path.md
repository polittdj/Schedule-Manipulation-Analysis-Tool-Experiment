# ADR-0086 — CPLI: remaining critical-path length, not the full span (formula-audit)

Date: 2026-06-18 · Status: accepted · Builds on ADR-0010 (DCMA-14), ADR-0085 (formula-audit)

## Context

Second fix from the formula-audit. The Bible's **CPLI** (`13. CPLI`):

```
(ProjectRemainingDuration + ProjectMinimumTotalFloat) / ProjectRemainingDuration
```

`compute_dcma14._cpli` used `result.project_finish` as the denominator — the network's latest early
finish measured as a working-minute offset **from `project_start`**, i.e. the **full** project span. The
DCMA standard and the Bible both use **`ProjectRemainingDuration`**: the remaining critical-path length
from the **data date (status)** to the project finish. Using the full span *dampens* the CPLI deviation:
with a project N working days long but only R remaining, a fixed negative float pulls
`(N+float)/N` toward 1.0 far less than the correct `(R+float)/R`.

## Decision

`_cpli` now takes the schedule's status offset and computes the denominator as
`project_finish − max(status_offset, 0)` — the remaining critical-path length. With no status date it
falls back to the full span (unchanged behaviour). `ProjectMinimumTotalFloat` (the minimum total float
across the network) is unchanged.

## Validation / parity

The minimum total float is **0 on every supplied file** (Project2, Project5, Large Test File have no
imposed deadline), so CPLI = 1.0 with *either* denominator → **parity 10/10, value unchanged**, and the
existing negative-float regression (`_broken_cp_schedule`, no status date) still reads 0.9 via the
fallback. The fix is therefore **latent on the available data** — it only moves a schedule that has both
an imposed deadline (non-zero project float) *and* a data date partway through. A new deterministic test
(`test_cpli_denominator_is_the_remaining_critical_path_from_the_status_date`) proves it: a status date 5
working days into a 10-day broken network sharpens CPLI from the full-span 0.9 to the correct **0.8**
(`(5−1)/5`). `docs/METRIC-DICTIONARY.md` regenerated; full gate green (947 passed); ruff/format/mypy/
bandit clean.

## Note

Like ADR-0085 (BEI), this is value-neutral on every Acumen-validated case (all give 1.0) and is adopted
on Bible/DCMA-definition authority, not against Acumen *output* for CPLI (none was supplied). It is
parity-safe and corrects a genuine denominator error that would understate CPLI on any real
deadline-driven, in-progress schedule.
