# ADR-0094 — Value autocomplete for the Groups & Filters page

Date: 2026-06-18 · Status: accepted · Builds on ADR-0090/0092 (grouping engine + UI)

## Context

The `/groups` filter (ADR-0092) takes a field and a free-text value. On a real file the operator has to
**know and type the exact value** (e.g. a CA-WBS code or a constraint-type string) blind — easy to
mistype, and the distinct values aren't discoverable without running a breakdown first.

## Decision

Progressive-enhancement autocomplete on each filter row's value input — the form still works with JS off.

- **Endpoint.** `GET /api/group-values?version=<key>&field=<field>` → `{"values": [...]}`, the distinct
  values of `field` in that version (`group_values(...).keys()`, capped at 500). Standard and mapped
  custom fields (ADR-0088) alike; an unknown/blank field returns `[]` rather than erroring.
- **Form.** Each value input is bound to a per-row `<datalist>` (`gf-dl-N`) and tagged `gf-value`; the
  field selects are tagged `gf-field`; the form carries `data-version` so the script knows which version
  to query even when there's no version picker.
- **Script (`static/groups.js`).** On field-select change (and on load for a query-string-preselected
  field) it fetches that field's values and fills the row's datalist; changing the version refreshes
  every row. Dependency-free, fails open (an empty datalist leaves the input fully usable).

## Consequences

- Filtering becomes pick-from-list instead of type-the-code, which removes the main friction in the
  grouping UI and surfaces a field's domain without first running a breakdown.
- No engine change — the endpoint reuses `group_values`; the page degrades gracefully without JS.
- Numbered 0094 because ADR-0093 (custom-field display columns) is in flight on a parallel PR.
