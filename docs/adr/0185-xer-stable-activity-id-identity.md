# ADR-0185 — XER identity: key tasks by Activity ID (CRC32), not P6's renumbering task_id

## Status

Accepted. Operator 2026-07-10: "Why is CEI not being calculated. Figure this out and make sure
that CEI is calculated correctly." (Trend page, 7-file Primavera XER series: CEI flat 0.00
across every period while BEI read 0.96–0.99 and HMI 0.62–0.91.)

## Context

CEI is the only headline execution index that joins tasks **across** versions by `unique_id`
(the prior schedule's forecast set looked up in the current schedule via
`current_by.get(t.unique_id)` — `engine/metrics/cei.py`). BEI and HMI are single-schedule, so
they kept working on the same files, proving actual finishes existed every period.

The XER importer set `unique_id = task_id` — P6's **internal database row id**, which P6
renumbers whenever a project is re-imported or copied between monthly submittals (the norm for
contractor XER deliverables). Every cross-version UniqueID lookup therefore missed, the CEI
numerator was 0 with a non-empty forecast window, and the chart honestly plotted the genuine
engine value 0.00 for every pair. The same renumbering silently degraded every other
cross-version consumer (diff, change-effects, trend task series) into "everything was removed
and re-added". This violated the repo's own identity law: "`unique_id` is the sole
cross-version identity — never the row id, which renumbers."

The identity P6 users actually maintain is the **Activity ID** (`task_code`, e.g. "A1000"),
which survives re-import; the importer only used it as a name fallback.

## Decisions

1. **Stable remap (`importers/xer.py::_stable_uid_map`)** — when EVERY in-scope task row
   carries a parseable `task_id` and a unique non-empty `task_code`, the model
   `unique_id = CRC32(task_code) & 0x7FFFFFFF` (stdlib `zlib`, deterministic across exports
   and sessions). Real P6 exports always carry `task_code` and P6 enforces Activity-ID
   uniqueness per project, so the remap engages on real files.
2. **All-or-nothing** — any missing/duplicate code or any 31-bit CRC collision returns the
   whole file to raw `task_id` keys (logged by count, never the code text). Mixed keying could
   silently mis-join versions, which is worse than honestly not joining.
3. **Reference translation** — `TASKPRED` endpoints (raw `task_id`s in the file) pass the
   existing scope/dangling/self-loop/duplicate checks on raw ids and are translated through
   the map at `Relationship` construction. `TASKRSRC`/`PROJCOST` lookups stay keyed by raw
   `task_id` internally (they are consumed inside `_parse_task` before the remap is applied to
   the model object).
4. **Traceability** — every code-bearing task carries `("Activity ID", task_code)` in
   `custom_fields`, so citations, grouping, and drills expose the human P6 handle regardless
   of which keying engaged.
5. **Tests** — regression proving CEI computes a real value (0.5, with the miss citable as an
   offender) across two versions whose `task_id`s were renumbered but whose Activity IDs are
   stable; identity-stability, fallback (missing code, duplicate code), and
   relationship-translation cases; fixture pins in `tests/importers/test_xer.py` re-derived
   via a `_uid(task_code)` helper documenting the new keying.

## Consequences

- CEI (all five variants), cross-version diffs, change-effects, and trend task joins now align
  on renumbered XER series — the user-visible flat-0.00 CEI becomes a real execution rate.
- Displayed UniqueIDs for XER files are 31-bit hashes rather than small P6 row ids; the
  Activity ID custom field carries the human-readable identity everywhere.
- MSPDI ingestion is untouched (MS Project's `<UID>` is already re-import-stable).
- A code-less or duplicate-coded XER (synthetic/degenerate) behaves exactly as before.
