# ADR-0092 — Groups & Filters UI (scope every metric by field value; per-value breakdown)

Date: 2026-06-18 · Status: accepted · Builds on ADR-0090 (grouping engine), ADR-0089 (BEI)

## Context

ADR-0090 shipped the grouping/filter **engine** (`engine/grouping.py`) but no surface for it. The
operator's ask: "choose a field (e.g. CA-WBS) and a value and the tool only looks at tasks with that
value — for **all** metrics; combine up to 5 fields; and break a field into its values." They chose
**both** filter and breakdown.

## Decision

A server-rendered **`/groups`** page ("Groups & Filters", in the nav) wiring the existing engine — no new
analysis math:

- **Controls.** A version picker, up to `MAX_FIELDS` (5) filter rows (`<field> = <value>`, value blank =
  "field populated"), and a "break down by" field. Field options come from `available_fields(schedule)`
  (standard built-ins + mapped custom fields, ADR-0088). All state lives in the query string, so a view
  is shareable/bookmarkable and needs no JS.
- **Filter → scorecard.** The chosen criteria build a sub-schedule via `filter_schedule` (matching tasks
  + their internal logic), over which the page shows the population (`N of M activities match`), the
  activity makeup, and the **full DCMA-14 scorecard** (`compute_dcma14` on the subset) — i.e. every
  metric scoped to the selection, exactly the engine's intended semantics. A non-solvable scope degrades
  to a notice rather than 500-ing.
- **Breakdown.** `group_values(sub, field)` splits the (already-filtered) population into its distinct
  values; each row reports the activity count, % complete, and **BEI** for that group. Filter and
  breakdown compose (breakdown runs over the filtered subset).
- **BEI refactor.** The DCMA-14 BEI formula (Acumen "BEI - Value Tasks", ADR-0089) was extracted from
  `compute_dcma14` into `metrics.compute_bei(schedule)` — pure counts, no CPM — so the breakdown scores
  BEI per group cheaply and from one source of truth. `compute_dcma14["DCMA14"]` now calls it; a parity
  test pins them equal and the golden BEI (0.74 / 0.59) is unchanged.

## Consequences

- The grouping engine is now reachable end-to-end; "BEI per CA-WBS code" is one click.
- BEI is reusable without a CPM solve, which keeps the per-group breakdown fast (only the single filtered
  scorecard solves a CPM).
- The breakdown surfaces a field's values, which an operator can copy back into a filter row.
- Deferred: an interactive (JS) value-autocomplete and a multi-metric breakdown (BEI only today besides
  counts); both can layer on without changing the engine.
