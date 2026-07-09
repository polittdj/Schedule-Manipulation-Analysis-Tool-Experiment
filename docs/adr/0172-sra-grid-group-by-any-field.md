# ADR-0172 — SRA editable grid: group-by-any-field (Gantt parity)

## Status

Accepted. Closes backlog #80. Operator asked for the SRA editable-grid Gantt to "match the other
Gantts (rows, fill page, filters/grouping/timescale)."

## Context

The `/sra` editable schedule grid (`sra_grid.js`, ADR-0123) already matched the other Gantts on
most axes: full-height **rows** via the shared `SFGantt` renderer, **fill-page** timeline
(`fitToProject` subtracts the measured frozen-column width), MS-Project per-column checklist
**filters**, and the **Timescale** dialog (tiers / units / Size %). The one capability the Path
Gantts had that it lacked was **group-by-any-field** — grouping rows under headers by WBS,
resources, criticality, or a custom field.

## Decision

Add group-by to the SRA grid, mirroring the Path-page pattern (ADR-0155's `path.js`):

- A **Group by** `<select id=ssiGridGroupBy>` in the grid toolbar, seeded with WBS / Resources /
  Critical / Milestone / Outline level, and **any custom field** appended client-side from the
  loaded rows' `custom` maps (`populateGroupCustom`, like `path.js`'s `populateGroupBy`).
- `sra_grid.js` groups the already-**filtered** row list (`groupList` / `groupKeyOf`, `custom:`
  prefix supported; booleans render Yes/No) and, when a group field is chosen, inserts a
  `.sra-branch-head` header row (label + member count) before each group's rows — the same visual
  as the Path Gantt's `.path-branch-head`. The grid stays fully editable (factor / BC / WC inputs,
  focus radio) and filterable within groups; `(none)` restores the flat view.

No engine/server-data change beyond the toolbar control; grouping is client-side over the existing
`/api/sra/grid` payload.

## Consequences

- Live-verified in Chromium (Hard_File): group-by offers the standard fields **plus** the file's
  custom fields ("Invoice Status", "Project Status Date"); grouping by Critical yields
  `No (108)` / `Yes (34)` headers (= 142 rows); the grid stays editable (inputs intact) and
  filterable; `(none)` clears the headers; zero console errors. Pinned by
  `test_sra_grid.py::test_grid_group_by_control_and_mechanics`.
- `src/` changed (`app.py` + `sra_grid.js` + `app.css`) → wheel + 9 installers rebuilt in the same
  commit (ADR-0148 lockstep). Laws untouched (presentation-only, offline).
- With this the SRA grid reaches parity with the other Gantts on rows / fill-page / filters /
  grouping / timescale — closing the operator's Gantt-parity work order (#80 was the last item).
