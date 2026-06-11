# ADR-0029 — XER per-task cost roll-up from TASKRSRC assignments + PROJCOST expenses

- **Status:** accepted
- **Date:** 2026-06-11
- **Drivers:** the next remaining deferred item after ADR-0028 — XER imports carried no
  cost data at all (the fields the MSPDI path fills), so every `.xer` reported the
  cost-based EVM indices (SPI/CPI/TCPI) as NOT_APPLICABLE even when the file was
  cost-loaded.

## Decision — roll assignment + expense costs onto the task's three cost fields

`xer._costs_by_task` sums per task across all `TASKRSRC` assignment rows and `PROJCOST`
expense rows:

- **`actual_cost`** (the ACWP basis) = Σ(`act_reg_cost` + `act_ot_cost`) + Σ expense
  `act_cost`;
- **`cost`** (the current at-completion total — the MSPDI `Cost` analogue) = actual +
  Σ `remain_cost`;
- **`budgeted_cost`** (the BAC / EV basis) = Σ `target_cost`, **clamped to ≥ 0** — the
  same rule the MSPDI importer applies to a negative baseline cost (EV is never earned
  against a negative budget). Negative actual/remaining values (credits, adjustments)
  are preserved as real data.

**Absence is honest:** a field is set only when the file carried at least one
contributing value for that task — a cost-less schedule keeps `None` (and the model's
`budgeted_cost=0.0` default), so the EVM indices stay NA exactly as before. Non-finite
values (`NaN`/`Infinity`) read as absent via the established `parse_float` noise rule.

## Parity / fidelity

The curated XER fixture's `TASKRSRC` has no cost columns and no `PROJCOST` table — its
tasks keep `(None, None, 0.0)` (pinned by test). The MSPDI goldens are untouched.
`pytest -m parity` stays 10/10.

## Consequences

**612 passed, 3 skipped** (4 new tests: multi-assignment + expense roll-up with
per-field absence, the negative-budget clamp vs preserved credits, an end-to-end
cost-loaded XER driving real CPI/SPI values, and the cost-free fixture pin); coverage
≈98% overall / ≈98% engine; ruff + format + mypy --strict + bandit clean; zero new
dependencies. Remaining deferred: per-task calendars (ADR-0008; only if the operator's
programs mix calendars materially) and the externally-gated **M15 (.pbix)**.
