# ADR-0140 — Save .json completeness: full calendar registry, resources, and an introspection guard

## Status

Accepted. Completes ADR-0131's C1 fix; part of the 2026-07-01 QC audit remediation (batch R3).

## Context

ADR-0131 made the Save .json round-trip carry every *task-level* fidelity field, and its guard test
passed — but the 2026-07-01 QC audit showed the round-trip was still lossy at the *schedule* level
(each confirmed with live reproductions):

- **D5 (HIGH).** The writer emitted a single-element `"calendars"` list built from
  `schedule.calendar` only, while its own comment claimed the SSI parity inputs round-trip. A
  multi-calendar schedule (per-task calendars — the ADR-0118 driving-slack parity inputs) reopened
  with every non-default calendar gone and `Task.calendar_uid` dangling; `engine/driving_slack.py`
  then silently fell back to the project calendar and the driving-slack numbers changed with no
  error. The C1 guard test used exactly one calendar, so it could not see this.
- **D9 (MEDIUM).** A strict `Schedule.model_dump_json()` document parses successfully through the
  *friendly* path (the documented strict fallback is dead code), and the friendly reader set
  `calendar = calendars[0]` — in a uid-ordered registry that need not be the project calendar, so a
  reload could silently swap the project calendar (every duration↔day conversion shifts).
- **D10 (MEDIUM).** `Schedule.resources` was never serialized: after Save/reopen every resource
  degraded to `"Resource {id}"` / type WORK with `max_units` gone — over-allocation analysis
  silently changed.
- **D24 (LOW).** `project_finish` / schedule-level `baseline_finish` were write-only;
  `parse_json` never stamped `source_file` (unlike MSPDI/XER); identity coercion (`unique_id: 1.5`
  truncated to task `1`; `"name": null` became the literal string `"None"`; an empty-string WBS
  collapsed to `None`).

## Decision

1. **Write everything.** `to_json_text` now emits the project `"calendar"` **and** the full
   `"calendars"` registry, `"resources"` (all fields), `project_finish`, and schedule-level
   `baseline_finish`; `wbs` is emitted whenever it is not `None` (an empty string is a value).
2. **Read it back correctly.** `_from_friendly` reads `"calendar"` as the project calendar when
   present (falling back to `calendars[0]` only for older single-calendar saves), plus
   `resources`, `project_finish`, `baseline_finish`. This also makes a strict `model_dump_json`
   document reload faithfully through the friendly path (D9), project calendar included.
3. **Strict identity types.** A new `_int()` reader rejects booleans and fractional values with a
   field-named `ImporterError` — `unique_id: 1.5` fails loud instead of truncating the sole
   cross-version identity key; applied to every integer field for consistency. A null/empty task
   name falls back to `Task {uid}` (matching MSPDI/XER) instead of `"None"`/`""` — which also
   removes the empty-name vector into the AI figure gate (ADR-0138 D6).
4. **`parse_json` stamps `source_file`** with the file basename, like every other importer.
5. **A model-introspection guard test**
   (`test_writer_covers_every_model_field_introspection_guard_qc_d5`) walks `model_fields` of
   `Schedule`/`Task`/`Relationship`/`Calendar`/`Resource`/`Assignment` against the emitted JSON of
   a maximally-populated schedule: **adding a model field without a writer line now fails a test**
   instead of silently losing data. The only documented exclusion is `Schedule.source_file` (a
   runtime citation label the loader re-stamps on open). A companion test asserts a full
   `model_dump` round-trip is byte-equal on the maximal schedule, with the project calendar
   deliberately not first in the registry.

## Consequences

- Save .json → reopen now preserves per-task calendars (driving-slack parity inputs), the resource
  registry, and the schedule-level finish dates; the "genuinely lossless" C1 claim is finally true
  at every level the model can express, and the introspection guard keeps it true structurally.
- One error-message improvement is pinned: `unique_id: None/1.5` now raises the specific
  `invalid integer for 'unique_id'` instead of the generic wrapper text.
- Backward compatible: older saves (single-entry `"calendars"`, no `"calendar"` key) load exactly
  as before.

## Alternatives considered

- **Route strict dumps through `Schedule.model_validate`.** The friendly path now reads a strict
  dump faithfully, so forcing a format sniff adds a second code path for no fidelity gain; the
  strict fallback remains as belt-and-braces.
- **Persist `source_file`.** Rejected: it is a runtime label; persisting it would go stale on
  rename and conflict with the loader's stamp.
