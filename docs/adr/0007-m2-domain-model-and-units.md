# ADR-0007: M2 domain model & units (source-only fields, deterministic days)

- **Status:** Accepted
- **Date:** 2026-06-05 (session A4 — Phase 2 build, milestone M2)
- **Relates to:** §3 (units), §6.B (UniqueID-only matching; all metadata representable), §7 (TDD/RTM)
- **Supersedes:** the prior build's single-module `schemas.py` (study reference at commit `0324ba4`)

## Context
M2 builds the trust-root data model the entire engine (CPM, driving slack, DCMA-14, EVM,
forensic diff) computes on. The prior build's frozen `schemas.py` reached full parity and is the
proven anchor; its key lesson (confirmed by re-reading the module + downstream consumers) is that
it stores **only source-of-truth fields** and computes every derivative on demand, "to avoid
storing derived state that could drift from inputs." A forensic/testimony tool must never let a
persisted number contradict the file it came from (Law 2).

## Decision
1. **Frozen + strict + closed models.** Every model subclasses `StrictFrozenModel`
   (`ConfigDict(frozen=True, extra="forbid", strict=True)`): immutable + hashable, no silent type
   coercion, and an unknown field is an error (importer drift surfaces loudly, metadata is never
   silently dropped). An inconsistent schedule is *unconstructable* (referential-integrity
   validator: unique task/resource UIDs; relationship endpoints must exist; no self-loops).
2. **Source-of-truth fields only.** The model holds what the schedule file records (identity,
   durations, constraints, progress, baseline/actual dates, cost, resources, logic, calendars).
   CPM early/late dates, total/free float, driving slack, and all DCMA/EVM metrics are **computed
   by the engine, never stored on the model** — so they cannot drift from their inputs.
3. **UniqueID is the sole identity.** `Schedule` is keyed by `Task.unique_id` (immutable
   `tasks_by_id` view, `task_by_id`, `predecessors_of`/`successors_of`) — never row ID, never name.
4. **Curated, comprehensive, change-controlled field set (not an `extra` bag).** Rather than a
   generic overflow mapping (which would break frozen-hashability and weaken the strict contract),
   the typed field set is widened up front to cover everything M5-M8/M11 metrics read (per
   `METRICS-CATALOG.md`), avoiding the prior build's v1.0→1.2 churn. `SCHEMA_VERSION = "2.0.0"`;
   any field change must bump it and update `tests/model/test_schema_freeze.py` in the same commit.
5. **Deterministic units boundary (`units.py`).** Durations/floats/lags are integer working
   minutes internally (480 min == one 8-hour day; the DCMA 44-day == 21120-min axis). Conversion to
   days happens only at the presentation boundary, via **`Decimal` + `ROUND_HALF_UP`** — *not*
   `minutes / 480.0`, which would reintroduce the binary-float drift U3 forbids. `format_days`
   renders `"<n> day(s)"` (U1); `format_percent` always carries its `%` sign with signed variants
   for deltas (U2); a non-8h calendar passes its own `minutes_per_day`.
6. **`pydantic>=2`** added as the first runtime dependency: a local, pure data-validation library
   with no remote/cloud client, so the CUI egress guard (`net_guard.py`) stays green. The
   `pydantic.mypy` plugin is enabled for precise strict typing of model construction.

## Consequences
- The engine can rely on an immutable, validated, UID-keyed schedule; derived analytics are always
  recomputed, never stale.
- Widening the field set now means importers (M3/M4) have a typed home for the metadata the metrics
  need; genuinely novel fields still go through the freeze-test change-control gate.
- Every rendered day/percent value is reproducible bit-for-bit (Decimal), which matters in a
  forensic context and keeps parity assertions stable.
- `model/` + `units.py` are at 100% unit coverage; full suite 163 passing; ruff/mypy(strict)/
  bandit/pip-audit clean; egress guard green with pydantic declared.
