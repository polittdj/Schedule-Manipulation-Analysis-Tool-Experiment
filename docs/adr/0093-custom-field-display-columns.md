# ADR-0093 — Display mapped custom fields as optional activity-table columns

Date: 2026-06-18 · Status: accepted · Builds on ADR-0088 (custom-field mapping)

## Context

ADR-0088 mapped MSPDI `ExtendedAttributes` into `Task.custom_fields` (label → value, alias-aware) and
`Schedule.custom_field_labels`, and ADR-0090/0092 made them groupable/filterable. The last of the
operator's three asks — "let me select which custom fields to **display**" — was still unmet: the mapped
values were not visible per activity anywhere in the UI.

## Decision

Surface every mapped custom field as an **optional column** in the Path Analysis grid — the app's
activity table, which already has an add/removable column-picker (`static/path.js`). No new page, no new
table machinery.

- **Payload (`_driving_data` → `/api/driving`).** Each row gains `custom` — a `{label: value}` map of the
  custom fields populated on that task (`task.custom_field_map`). The response gains
  `custom_field_labels` (the schedule's declared custom fields, in order) so the grid discovers the
  columns from the data rather than hard-coding them.
- **Grid (`path.js`).** On each load, `syncCustomColumns()` appends one toggle per label (keyed `cf:<label>`,
  **off by default**, marked `field-custom`); the cell renderer reads custom values from `r.custom[label]`.
  Toggle state lives in the module-level `FIELDS`, so a chosen custom column persists when the operator
  changes target or version. Unpopulated values render as the grid's usual `—`.

## Consequences

- The mapping shipped in ADR-0088 is now visible end-to-end: on the real file the operator can switch on
  CA-WBS / CAM / etc. beside any traced activity, with zero per-file configuration.
- Columns are discovered per schedule, so files with different custom fields just work.
- Deferred: custom columns in the **export** (`driving_table` still emits the fixed column set) and custom
  fields in tables other than the Path grid (the established activity table); both can layer on the same
  payload without engine changes.
