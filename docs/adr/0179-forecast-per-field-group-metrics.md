# ADR-0179 — Forecast per-field group execution metrics + no-completed-work handling

## Status

Accepted. Operator 2026-07-09: "on the Forecast Page … have each schedule have metrics such as
BEI, HMI, SPI, CEI etc. calculated based off a field that the user selects from a dropdown …
all standard and custom fields … calculate all of the values for only tasks associated with
that [value] … as well as for tasks that are not assigned … and will just title those NA. For
measures that require that work to be completed and don't have work that has I want you to
research what the industry best practices are for such situations and come up with a way to
calculate these values … Provide me with your best analysis."

## Decisions

1. **`engine/metrics/field_forecast.py`** (`compute_field_forecast(schedules, field)`): every
   loaded version is split into one group per populated value of the chosen field (standard or
   custom, e.g. a CAM code) plus an **NA** group for unassigned tasks; each group is scored as
   a SUB-SCHEDULE with the exact engine functions the schedule-wide numbers use — cumulative
   BEI (`compute_bei`), HMI (`compute_hmi`), CEI Finish/Start + both SPI(t) methods
   (`compute_evm_indices`) — one source of truth, never re-implemented. `Resource` expands per
   assigned resource; groups are the union across versions (a group that disappears later still
   shows, 0 activities), NA last.
2. **No-completed-work handling (the research ask).** The finish-anchored indices (BEI / HMI /
   CEI-Finish / both SPI(t)s) have no qualifying data for a group that has completed nothing.
   Published practice — the NDIA Planning & Scheduling Excellence Guide's treatment of the
   BEI family and the DCMA construct — is explicit that an index without qualifying data reads
   **N/A**, never an imputed 0 (reads as catastrophic) or 1 (reads as perfect), because either
   poisons any forecast built on it. The accepted substitute is a **leading, start-anchored**
   indicator: work must start before it can finish, so this module adds a **Start Execution
   Index (SEI)** = activities started ÷ activities baselined-to-start-by-the-data-date (the
   shape of Acumen's own "BEI - Value Task Starts"), defined as soon as anything is due to
   start. The module therefore **never fabricates a finish index** — undefined finish measures
   stay `None` (rendered N/A) while SEI + the Started/To-go workoff counts give a real
   execution read; a `no_completed_work` flag drives the UI's "start-basis" badge. When the
   group completes its first activity the finish indices activate automatically.
3. **Forecast page panel** (`_field_forecast_panel`): a "Group by" dropdown of every standard +
   custom field, a per-(group, version) table of all the indices with N/A rendered honestly, a
   collapsible best-practice analysis explaining the no-completed-work derivation, and an Excel
   export (`/export/{fmt}/field-forecast`).

## Consequences

- Verified on the operator's Hard_File series grouped by Resource: e.g. the Trainer group
  (updated3) scores BEI 0.33 / SEI 0.33 with 1 of 4 complete, while a not-yet-started group
  reads N/A on every finish index but a real SEI. The NA group collects unassigned tasks.
- Pinned by `tests/engine/metrics/test_field_forecast.py` (grouping, NA group, cumulative BEI
  per group, no finish-index imputation + defined SEI, cross-version union) and
  `tests/web/test_forecast_views.py` (dropdown, table columns, N/A rendering, export + 404).
- `src/` changed → wheel + 9 installers rebuilt (ADR-0148 lockstep).
