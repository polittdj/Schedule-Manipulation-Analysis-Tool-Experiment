# ADR-0234 — Priority / Status / Project / Outline Number group fidelity (feature #10, PR-C.2)

## Status

Accepted. The small follow-up ADR-0233 §5 planned: after PR-C's fixes, four of the operator's real
saved groups still collapsed to `(ungrouped)` because the fields they bucket on did not exist in
the model or the resolver — `&Priority`, `Status`, `Priority Keeping Outline Structure`
(Project / Outline Number / Priority), and any other view referencing those columns. This PR makes
them resolve faithfully.

## Context

MS Project group clauses reference four more columns the tool did not carry:

* **Priority** — a stored 0-1000 integer (default 500) driving resource leveling;
* **Outline Number** — the stored dotted outline position ("1.2.3");
* **Project** — the source file's base name (what MSP and the SSI exports show per task);
* **Status** — **computed**, not stored: MS Project derives Complete / On Schedule / Late /
  Future Task from the task's progress against the file's status date. Its documented rule judges
  progress by the stored **Stop** date (the date actuals run through): progress reaching at least
  the day before the status date is On Schedule, short of it is Late, a task starting after the
  status date is a Future Task, and 100% is Complete.

The resolver's `_CORE` accessors deliberately see only the `Task`, so a status-date-relative field
cannot be a core row. MSPDI carries `<Priority>`, `<OutlineNumber>`, and `<Stop>` on every task
(verified in the golden fixtures and the real converted `Large Test File Leveled.mpp` — 2,926
`<Stop>` values), so the inputs are all real stored data.

## Decision

1. **Three new stored `Task` fields** (SCHEMA_VERSION 2.7.0 → 2.8.0): `priority` (0-1000, `None` =
   source didn't carry it), `outline_number` (string, presentation/grouping only — never an
   identity key), and `stop` (datetime, the progress-through date). MSPDI reads `<Priority>`
   (tolerant + clamped to MSP's own 0-1000 scale — a garbled cosmetic value never sinks a file),
   `<OutlineNumber>`, and `<Stop>`. XER leaves all three `None`: P6's `priority_type` is a 5-level
   enum on a different axis (mapping it would invent numbers), and the P6 analogue of the outline
   number is the WBS path already on `Task.wbs`. JSON save/reopen round-trips all three.
2. **Status and Project are resolved at the `resolve_field` level**, where the `Schedule` is in
   scope — not as `_CORE` task-only accessors and not as stored fields. `_msp_status` reproduces
   MS Project's documented rule (Complete → Future Task → On Schedule / Late via `stop` against
   the day before `status_date`); a file with no status date yields `None` (a blank bucket) — the
   tool never fabricates "today" for a forensic artifact. `Project` = the source file's base name,
   exactly as the operator's SSI exports print it.
3. **Resolver rows** for `PRIORITY` (NUMERIC), `OUTLINE_NUMBER` (STRING), `STOP` (DATE) +
   display-name aliases, and a `_SCHEDULE_LEVEL_KINDS` table for `STATUS`/`PROJECT` so
   `field_kind` stays a pure function of the name.

## Consequences

- On the real file every resolvable saved group now buckets faithfully: `Status` yields exactly
  MS Project's four buckets, `&Priority` groups by value (all 500 in this file), and
  `Priority Keeping Outline Structure` produces one bucket per outline row under the project name
  — MSP's "keep the outline" semantics. Only `Board Status` / `Sprint` (Agile add-in fields with
  no source data) still degrade, which is the honest behavior.
- The `Status` computation is engine-side and cited to MS Project's documented field reference;
  it is exercised by unit tests for all four states plus the no-status-date blank. If a future
  reference export ever disagrees on an edge (e.g. partial-day stop conventions), the parity
  fixture wins and the rule gets refined there.
- Filters referencing these fields (none in the operator's current 10, but standard MSP filters
  like "In Progress Tasks" use them) now resolve too — the evaluator consumes the same resolver.
- Schema/freeze/JSON-writer guards updated in lockstep (2.8.0); MSPDI/XER importer behavior for
  every previously-carried field is byte-identical.
