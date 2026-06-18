# ADR-0090 — Field-based grouping & filtering engine (filter + breakdown)

Date: 2026-06-18 · Status: accepted · Builds on ADR-0088 (custom fields)

## Context

Operator request: "define what field to group tasks by for analysis for all metrics … choose CA-WBS
and the tool only looks at tasks with a particular value … select up to 5 fields (standard + custom) at
once." When asked filter-vs-breakdown, the operator chose **both** (filter first, then breakdown).

## Decision

New `engine/grouping.py` — a small, dependency-light layer the rest of the engine consumes unchanged:

- **Fields**: `STANDARD_FIELDS` (WBS, Activity Type, Constraint Type, Resource, Critical, % Complete) +
  the mapped custom fields (`Schedule.custom_field_labels`, ADR-0088). `available_fields(schedule)`
  lists them (standard first, then custom); `field_value(schedule, task, field)` resolves a task's
  value (custom field wins).
- **Filter**: `select(schedule, criteria)` → matching UIDs; `task_matches` is a logical **AND** across
  up to `MAX_FIELDS = 5` `(field, value)` criteria (empty value = "field populated"; `Resource` is
  multi-valued, so it matches when the task *carries* the resource). `filter_schedule` returns a
  **sub-schedule** of the matching tasks and the relationships *among* them, preserving the project
  frame — so every existing metric (`compute_dcma14`, `compute_schedule_quality`, CPM, …) runs over the
  subset with no per-metric changes. More than 5 fields raises.
- **Breakdown**: `group_values(schedule, field)` → `{value: (uids…)}` (sorted; `Resource` expands per
  assignment), so a metric can be computed once per group (e.g. one BEI per CA-WBS code).

Filtering to the subset's *internal* relationships is deliberate: "only look at tasks associated with a
value" means logic checks reflect the selected population (cross-group links become out-of-scope).

## Validation

`tests/engine/test_grouping.py` (7 cases): custom-vs-standard resolution, AND matching + Resource
containment + empty-value semantics, the `MAX_FIELDS` cap, sub-schedule keeping only internal
relationships, the empty selection, and per-value/Resource-expanded grouping. End-to-end on the real
`Large_Test_File2.mpp`: filtering to **CA-WBS = 4.1.4.1** scopes every metric to 880 tasks (BEI 0.58),
and a CA-WBS breakdown surfaces the weak groups (4.1.5.1 BEI 0.38, 4.1.5.2 0.37 vs 4.1.6.1 0.68). Full
gate green (965 passed); ruff/format/mypy/bandit clean.

## Follow-ups (separate PRs)

UI to drive it — a field/value picker that scopes the dashboard (filter) and a per-group scorecard
(breakdown) — plus the column-picker to *display* selected custom fields, and the driving-path-between-
two-UIDs-across-versions view (an existing `engine/path_trace.py` already gives `ancestors_of`/
`topo_order` to build on). Number/Date custom values match as their raw strings for now.
