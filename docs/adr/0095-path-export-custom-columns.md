# ADR-0095 — Custom-field columns in the Path Analysis export

Date: 2026-06-19 · Status: accepted · Builds on ADR-0093 (custom-field display columns)

## Context

ADR-0093 added mapped custom fields as optional **on-screen** columns in the Path Analysis grid, but the
xlsx/docx export (`driving_table`) still emitted only the fixed column set — an operator who turned on a
CA-WBS column and exported lost it in the file (an explicit ADR-0093 deferral).

## Decision

The path export mirrors the grid's chosen custom columns.

- **`reports.tables.driving_table(rows, target_uid, custom_labels=())`** gains a `custom_labels`
  argument: one extra column per label, read from each row's `custom` map (the `{label: value}` the
  payload already carries, ADR-0093); a missing value renders as an empty cell. With no labels the table
  is byte-for-byte unchanged.
- **`export_path`** accepts `&cols=<comma-separated labels>`, intersected with the schedule's own
  `custom_field_labels` (unknown names dropped, order preserved, deduped) before passing them through —
  so a stray/foreign column can't appear.
- **`path.js`** keeps the export links in sync: `updateExportLinks()` appends `&cols=` with whichever
  custom columns are currently toggled **on**, recomputed both on load and whenever a column toggle
  changes. Standard columns are unaffected (the export's fixed set already covers them).

## Consequences

- "Show CA-WBS, then export" now round-trips: the deliverable carries the same custom columns the
  operator sees on screen.
- Validation is server-side (only the file's real fields), so the query param is safe.
- Still deferred (smaller): mirroring the on/off state of the *standard* columns in the export (today the
  export always carries the full fixed set); custom fields in tables other than the Path grid.
