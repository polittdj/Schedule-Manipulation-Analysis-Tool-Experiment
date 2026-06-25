# ADR-0128 — Exclude inactive tasks from the CPM and metric populations

## Status

Accepted.

## Context

`Task.is_active` is read from the source file (MSPDI `<Active>0</Active>` ⇒ `is_active=False`; XER has no
per-task flag, so always `True`) but **no engine code consumed it** — inactive tasks entered the CPM
network and counted in every metric denominator (DCMA-01/05/06/07/08/10/11, schedule quality, float
bands/ratio/erosion, EVM, completion performance, resources, CEI, FEI/BRI, …).

MS Project and Acumen Fuse **exclude inactive tasks** from scheduling, rollups, and metric populations —
an inactive task is treated as if it were not in the schedule. So on a real production schedule that
carries inactive tasks, the tool's numbers diverged from the reference tools (a Law-2 fidelity gap). The
golden parity files carry **no** inactive tasks, so the parity gate could not catch this; the QC audit
(`docs/STATE/AUDIT-2026-06-25.md`, finding M1) surfaced it.

## Decision

Treat an inactive task (`is_active=False`) the same way a summary task is treated: a **real, schedulable
activity is one that is neither a summary nor inactive**. The exclusion is applied at the two central
chokepoints, plus the few scattered scheduling sites that gather their own population:

1. **`engine/metrics/_common.non_summary`** — now returns `not is_summary and is_active`. This is the
   population for nearly every metric, so the DCMA / float / EVM / quality / resource denominators all
   drop inactive tasks (and link-based DCMA metrics drop links to inactive tasks, because they filter
   relationships to `real_ids = {t.unique_id for t in non_summary(...)}`).
2. **`engine/cpm._scheduled_tasks`** — now `not is_summary and is_active`. Inactive tasks never enter the
   CPM network; the network is keyed on this set, so their links drop with them and they cannot appear
   on the critical path or carry derived float. SRA (built on the CPM result) follows automatically.
3. Scattered scheduling-population sites mirrored for consistency: `driving_path` (endpoint validity),
   `driving_slack.date_basis` (the as-scheduled axis), `metrics/vertical_integration._dated`, and the
   `DCMA12` critical-path-test target filter.

**The forensic diff / manipulation layer is deliberately NOT changed.** `engine/diff.py` and
`engine/manipulation.py` read `schedule.tasks` directly, so a task being *deactivated* between versions
remains a detectable change — deactivating an activity is itself a manipulation vector and must not be
hidden by the metric-population filter.

## Consequences

- On schedules containing inactive tasks, CPM dates/float and every metric now match MS Project / Acumen
  (inactive tasks and their logic are excluded), closing the Law-2 gap.
- **No golden parity number moves** — the goldens have zero inactive tasks, so every `non_summary` /
  `_scheduled_tasks` result is identical; `pytest -m parity` stays green. A new synthetic test
  (`tests/engine/test_inactive_tasks.py`) pins the new behavior directly (CPM, DCMA population,
  driving-slack basis), since no golden exercises it.
- No model or `SCHEMA_VERSION` change; std-lib / offline / air-gap posture unchanged.

## Alternatives considered

- **Document retention instead of excluding.** Rejected: the operator chose to match MS Project / Acumen,
  which is the correct forensic-parity behavior; keeping inactive tasks in the population would knowingly
  diverge from the reference tools the numbers are tested against.
- **A pre-filtered `Schedule`.** Rejected: the model is frozen and shared, and summary exclusion already
  uses per-population helpers; mirroring that pattern is lower-risk and keeps the raw task list available
  to the diff/manipulation layer.
