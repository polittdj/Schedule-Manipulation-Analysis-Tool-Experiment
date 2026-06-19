# ADR-0097 — MS-Project-style value dropdown (multi-select) on the Groups & Filters page

Date: 2026-06-19 · Status: accepted · Builds on ADR-0090/0092 (grouping engine + UI), ADR-0094 (autocomplete)

## Context

The `/groups` filter took a typed value (ADR-0092), later helped by a datalist autocomplete (ADR-0094) —
but the operator still typed one value per field. The request: pick the field, then choose its values
from **a dropdown of all the schedule's values with a Select-all**, the way MS Project's AutoFilter works,
and filter to **any** of the chosen values.

## Decision

Reuse the app's existing **`SFChecklist`** widget (the MS-Project-style column filter already used on the
Analysis grid and Path page: a button → popup of checkboxes with **All / None** and a search box) for the
`/groups` value picker, and generalise the filter to multiple values per field.

- **Engine.** `grouping.Criterion` widens from `(field, str)` to `(field, str | Sequence[str])`.
  `task_matches` now OR's the value(s) within a field (a task matches if its value is **any** of the
  chosen ones; `Resource` matches if it carries any), still AND'ing across fields. A single string is the
  one-element case (fully backward-compatible); an empty value/sequence still means "field populated".
- **Web.** Each filter row renders a `select` (field) + a checklist mount + a hidden-inputs box. `groups.js`
  fetches the field's values (`/api/group-values`, ADR-0094) and mounts `SFChecklist`; the checked values
  are written into hidden `value{i}` inputs the GET form submits (one per row, so each field keeps its own
  set). The server-rendered hidden inputs round-trip the current selection and keep the form working
  without JS. The route reads per-row `value{i}` (and still honours the legacy single `value` list).
  Select-all emits all the field's values (filter to that field populated); a strict subset filters to it.

## Consequences

- Filtering is now pick-from-checklist with Select-all, matching MS Project and the rest of the app's
  filter UX; the engine change is a clean superset (old single-value URLs and callers are unaffected).
- One widget (`SFChecklist`) now serves the grid, the Path tiers, and the group filter — no new UI code.
- Deferred (small): a per-row "match none" state (unchecking everything currently reads as no value
  restriction); the breakdown remains single-field.
