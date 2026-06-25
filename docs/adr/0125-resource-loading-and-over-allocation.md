# ADR-0125 — Resource loading & over-allocation (Resources section)

## Status

Accepted.

## Context

The operator asked for a Resources section: a true resource-loading histogram plus over-allocation
detection. The model already carried resource **names/UIDs** per task (`Task.resource_names` /
`resource_ids`, for the DCMA Resources check) and the `Resource` roster (with `max_units`), but it did
**not** carry each assignment's **work** or **units** — the quantities a loading histogram needs. The
MSPDI `Assignments` block does carry them (`<Work>`, `<Units>`), and the golden Project5 file has 158
assignments with real work.

## Decision

1. **Schema (model migration, `SCHEMA_VERSION` 2.3.0 → 2.4.0).** Add a frozen `Assignment`
   value object (`resource_id`, `work_minutes`, `units`) and `Task.resource_assignments:
   tuple[Assignment, ...] = ()`. Additive and optional (default empty), so a schedule that records
   only names/UIDs is still valid. `tests/model/test_schema_freeze.py` is updated in the same change
   (change control).

2. **Importers.** MSPDI `_parse_assignments` now also reads each assignment's `Work` (→ working
   minutes via the existing `iso_duration_to_minutes`) and `Units`, summing work per task+resource
   into one `Assignment` per resource. The friendly JSON importer/exporter round-trips
   `resource_assignments` (and `resource_ids`) so a saved schedule keeps its loading data.

3. **Engine (`engine/resources.py`, parity-isolated).** `compute_resource_loading(schedule, cpm)`
   time-phases each task's assignment work **evenly across the working days** of the task's CPM span
   (early start → early finish) and totals it per calendar **month**, per resource. A resource's
   monthly **capacity** is `max_units × working-minutes-per-day × working-days-in-the-month`; a month
   whose booked work exceeds capacity is **over-allocated**. Plain dataclasses, std-lib only; never a
   `MetricResult`, never stored on the model.

4. **Web (`/resources` + nav).** A per-resource monthly work-vs-capacity histogram (vendored SVG,
   `resources.js`; over-allocated months in red, a capacity tick per month), a roster table, summary
   KPIs, user tips and a method explainer.

## Consequences

- The even-spread assumption gives **exact monthly totals** but an approximate within-task shape when
  the source file carries no time-phased work contour — documented on the page. A future enhancement
  could honour a `TimephasedData` contour when present.
- The deterministic CPM/DCMA/EVM numbers are untouched (the engine only reads dates + assignments).
- Offline / std-lib-only / CUI laws preserved; nothing leaves the machine.
