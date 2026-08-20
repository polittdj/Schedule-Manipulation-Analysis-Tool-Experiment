# ADR-0433 — The Resources page loads P6 files, honors per-resource max units, and shows the whole roster

**Status:** Accepted · **Date:** 2026-08-20 · **Extends:** ADR-0125 (resource loading), ADR-0298 rank 10 (panel contract)

## Context

Operator report (2026-08-20): "The resources page is not calculating correctly. There are
multiple resources in these projects with different max units. The tool should allow the user to
see all resources, and the visuals should also convey this information accordingly."

Measured defects behind that sentence (each observed RED before the fix):

| Defect | Where | Consequence |
| --- | --- | --- |
| XER never built `Task.resource_assignments` | `importers/xer.py::_parse_assignments` returned names/ids only | `engine/resources.py:148` skipped every task → EVERY P6 file rendered "This schedule has no resource assignments to load" |
| XER never read max units | `RSRC.max_qty_per_hr` / the `RSRCRATE` table unparsed | every P6 resource landed `max_units=None` → the engine's assumed 1.0 |
| Roster built from assignments only | `compute_resource_loading` iterated `tasks_seen` | a declared-but-unassigned resource was invisible, not even a zero row |
| Assumed 1.0 indistinguishable from declared 1.0 | `ResourceLoad.max_units: float` | the roster printed "1" for a file that said nothing |
| Only single-resource visuals | `resources.js::draw(selected())` | nothing conveyed utilization across ALL resources |

The capacity formula itself (`max_units × wmpd × working-days-in-bucket`) always honored
per-resource max units — the differing-max-units engine test passed on first run, the
true-positive twin proving the gap was the DATA and the roster, not the math. The audit had
already measured that every committed fixture carried a uniform 1.0, so no existing test could
fail on the operator's condition.

## Decision

1. **XER parses max units**: the resource's own `max_qty_per_hr` column when present, else the
   `RSRCRATE` rate IN EFFECT at the data date (latest `start_date` not after it; a file whose
   rows all start in the future keeps the earliest; none → `None`, never a fabricated 0). P6
   stores the ratio (1.0 = 100%), the exact analogue of MSPDI `<MaxUnits>`.
2. **XER builds real `Assignment` objects** from `TASKRSRC`: work minutes = at-completion HOURS
   (actual regular + overtime + remaining, else the budgeted `target_qty`) — and only for
   hour-booking resource types: a material's quantities are in MATERIAL units (tons, m³), so a
   material/cost assignment is recorded with zero work minutes rather than fabricated hours.
   `units` = `target_qty_per_hr` (the assignment Units/Time ratio); negatives clamp to the
   model's `ge=0` floor.
3. **The roster is the union** of the file's resource table and the assigned ids: an unassigned
   resource is a row with honest zeros; an assignment against an undeclared id keeps its
   "Resource {id}" fallback row.
4. **`ResourceLoad.max_units_declared`** rides along so the view can render "—" for the engine's
   documented 1.0 assumption instead of a fabricated figure (Law 2); a DECLARED 0.0 still prints
   0 (ADR-0125's audit fix preserved).
5. **A fourth shelled panel, "Utilization by resource"**: every resource's peak booked load as a
   share of its OWN capacity, worst first, 100%-of-capacity line, "over (no capacity)" for load
   against zero capacity — rendered as plain rows (deliberately NOT a `.chart-host`, so
   chartframe never bolts a zoom bar onto a div list). Verified rendered in chromium with
   hand-checked figures (Welder 80 h vs 0.5 × 20 wd → 100%; Iron Crew 160 h vs 2.0 × 20 wd → 50%).
6. The r10 panel contract re-baselined 3 → 4 (heads, tools, chips, takes, exports, `data-sf-big`,
   the whole-file resources.js digest) — the 11-line axis-caption call-site block digest is
   UNCHANGED, the same shape as the ADR-0319/0342 refreshes.

## Consequences

- P6 files load the Resources page at last; multi-resource projects with differing max units are
  judged each against their own capacity, and the whole roster is visible at a glance.
- The histogram picker now lists unassigned resources too; `draw()` already handled an empty
  series ("No work recorded for this resource.").

## Deliberately NOT done

- **The even-spread load formula and `Assignment.units` weighting are untouched** — booked work
  minutes remain the load basis (units would double-count where work already reflects them), and
  no reference-tool export for a P6 histogram exists in the repo to validate a change against
  (Law 2: no churn without an oracle).
- **The engine's missing-max-units 1.0 default stays** — only its DISPLAY changed to "—". A
  capacity of nothing-at-all would suppress over-allocation entirely, which ADR-0125's audit
  already rejected.
- **Time-varying RSRCRATE availability** is collapsed to the rate at the data date; a full
  per-period availability model is future work and is stated in the explainer.
