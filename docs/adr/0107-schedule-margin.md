# ADR-0107 — Schedule-margin metrics (total + effective margin)

Status: accepted (2026-06-20)

## Context

The operator asked for schedule-margin analysis (margin burndown / effective margin), flagged in
`docs/HANDBOOK-EXTENSION-PLAN.md` (A4) as blocked because the model had no way to identify margin
tasks. The operator supplied the convention: **every schedule-margin task has the word "margin"
somewhere in its task name.** That unblocks the epic, and the `duration_overrides` hook added for
the SRA engine (ADR-0106) makes the handbook's "effective margin" counterfactual a single extra
CPM pass.

## Decision

- **Identification (operator convention):** `is_margin_task(task)` = a non-summary activity whose
  name contains "margin" (case-insensitive substring). Summaries are excluded even if named so.
  Centralised in `engine/metrics/margin.py` so the rule is configurable later if the convention
  changes.
- **`compute_margin(schedule, cpm) -> MarginAnalysis`** (lightweight frozen dataclasses, NOT
  `MetricResult` — parity-isolated, out of the metric-dictionary coverage test, like
  `health_extra.py`):
  - **Total margin** = sum of the margin tasks' durations (working days).
  - **Effective margin** = how far the project finish **pulls in if all margin is removed** —
    computed by re-running the trusted `compute_cpm(schedule, duration_overrides={uid: 0 …})` over
    the margin UIDs and measuring the finish movement. This is the buffer *actually* protecting the
    finish (margin on a slack path contributes 0 effective margin though it still counts toward
    total). Reusing the canonical solver means zero divergence from the deterministic numbers
    (Law 2).
  - Per-task: duration (working days) and whether it sits on the critical path (total float ≤ 0).
- **Surfaced** as a "Schedule margin" panel on the analysis page (total, effective, on-critical
  count, the margin-task table), reusing the existing stoplight styles; a graceful "no margin tasks
  found" note when a schedule has none. The convention is stated on the panel.

## Consequences
- Margin analysis works on any schedule that follows the naming convention, with no model/importer
  change; the rule is one helper, easy to adjust.
- Effective margin is defensible (it is the canonical CPM with margin zeroed — no re-implementation).
- Next tranche: **margin burndown across versions** (total + effective margin per submission) on the
  trend surface.

## Verification pointers
NASA Schedule Management Handbook §7.3.3.1.6 (schedule margin / effective margin — margin on the
critical path is the buffer that moves the finish); the effective-margin counterfactual reuses the
ADR-0106 `duration_overrides` mechanism and `engine.path_counterfactual` thinking.
