# ADR-0088 — Map MSPDI custom / extended fields (CA-WBS, CAM, …)

Date: 2026-06-18 · Status: accepted · Schema 2.1.0 → 2.2.0

## Context

Operator request: "map all the custom fields in the `.mpp` files so the user can select those fields"
— the foundation for (a) displaying custom columns and (b) grouping/filtering every metric by a custom
field such as **CA-WBS**. The `.mpp` importer converts to MSPDI via MPXJ, then parses the XML; custom
fields ride along in MSPDI `<ExtendedAttributes>` (project-level `FieldID → FieldName/Alias` definitions)
plus per-task `<ExtendedAttribute><FieldID>/<Value>` pairs. The parser previously ignored them.

The supplied `Large_Test_File2.mpp` defines ~85 custom fields; **69 are populated**, including the
operator's example **CA-WBS (Text20)** — 12 WBS groups (e.g. `4.1.4.1` = 880 tasks) — plus CAM, CLIN,
IPT/SUB, Work Package ID, EVT, Outline Codes, and the SSI/SRA toolset fields.

## Decision

- `Task.custom_fields: tuple[tuple[str, str], ...]` — `(label, value)` pairs, label = MS Project
  **alias** when set (`CA-WBS`) else the field name (`Text20`). A tuple keeps `Task` frozen + hashable
  (like `resource_names`). Helpers: `custom_field_map` (dict view) and `custom_field(label)`.
- `Schedule.custom_field_labels: tuple[str, ...]` — the labels actually **populated** on ≥1 task, in
  project-declared order (the picker shows fields with data, not every empty slot).
- MSPDI parser: `_parse_extended_attribute_defs` builds the `FieldID → label` map;
  `_task_custom_fields` reads each task's values (a value whose `FieldID` lacks a project-level
  definition is dropped — it can't be labelled). Schema version bumped to **2.2.0** (change control).

## Validation

New `tests/importers/test_mspdi.py` cases: alias mapping, orphan-value drop, populated-only label list
in declared order, and the no-extended-attributes path (goldens stay empty). End-to-end on the real
converted `Large_Test_File2.mpp`: 2125 tasks, 69 populated custom fields, CA-WBS groups resolved. Full
gate green (958 passed); ruff/format/mypy/bandit clean.

## Follow-ups (separate PRs)

This is the data layer only. Still to come: a column picker to **display** selected custom fields, a
**group-by/filter** layer letting the user scope every metric to up to 5 fields (standard + custom) by
value, and the driving-path-between-two-UIDs-over-time view. Number/Date/Duration custom values are
stored as their raw MSPDI strings for now; typed coercion can follow if a consumer needs it.
