# ADR-0231 — Faithful MS Project filter evaluator + saved-view model (feature #10, PR-A)

## Status

Accepted. PR-A of the flagship "Groups & Filters" feature #10 — reproduce MS Project's saved task
filters (and groups) *faithfully* ("exact reproduction", operator decision). This PR lands the
correctness-critical core — the criteria model, the raw-field resolver, and the evaluator — as pure,
CI-testable Python. The Java-side export that populates the definitions from a `.mpp`, the session-wide
grouping / highlight / A–Z, and the `/groups` UI are later PRs (PR-B/C/D).

## Context

MS Project stores named filters as a criteria **tree** (`org.mpxj.GenericCriteria` in the vendored MPXJ
reader). A read-only probe against the operator's real `Large Test File Leveled.mpp` extracted the 10
real task filters + 25 groups, which define the reproduction target: leaf tests
(`CONTAINS`/`EQUALS`/…), recursive `AND`/`OR`, **interactive prompts** ("Date Range…"), **field-to-field**
comparison (`Duration9 > Duration8`), null/empty tests (`Actual Finish EQUALS <null>`, `Text19 EQUALS ''`),
and typed values (dates, durations, booleans, and custom `Text9`/`Flag6`/`Duration8` fields).

The subtle semantics were taken from the **MPXJ 16.2.0 bytecode** (`javap -c` on `GenericCriteria`
/ `TestOperator`), not guessed. Two crux findings shaped the design:

1. **Asymmetric normalization + null ordering.** A *field* value is normalized by its data type (DATE →
   truncated to its day; DURATION → the tool's working-minute axis with `None` → 0; STRING `None` → `""`;
   else untouched). A *literal* RHS is not date-truncated. In an ordered compare a `None` field sorts
   **greater**. Strings have three regimes: `EQUALS` case-sensitive whole-string, `CONTAINS`
   case-insensitive substring, `CONTAINS_EXACTLY` case-sensitive substring.
2. **Filters reference the *raw* field name** (`Text9`), but `Task.custom_fields` is keyed by the
   operator's **label** (`IPT/ SUB`) — the raw name was discarded at import. Faithful evaluation needs a
   raw-name → label indirection that did not previously survive.

## Decision

- **`model/saved_view.py`** — frozen `Criterion` (leaf / AND-OR branch), `Operand`
  (literal / field-ref / prompt / null), `SavedFilter`, `SavedGroup`, `GroupClause` — the faithful
  *shape* of a source definition (no evaluation/coercion in the model).
- **`Schedule.custom_field_by_raw_name`** — a `(raw_name, label)` map persisted by the MSPDI importer
  (`_parse_extended_attribute_raw_names`), so the resolver can bridge `Text9` → `IPT/ SUB` → the stored
  value. Also `Schedule.saved_filters` / `saved_groups` (empty until PR-B populates them from the Java
  export). All three round-trip through the tool's JSON format (`SCHEMA_VERSION` 2.6.0 → 2.7.0).
- **`engine/msp_field_resolver.py`** — resolves a raw field (by MPXJ enum, else display name) to a typed
  task value + `FieldKind`: core scheduling fields (a table, no coercion) and the custom families via the
  two-hop label lookup with family coercion (`Flag` → bool, `Duration` → minutes, `Date` → datetime,
  `Number`/`Cost` → float). Source-absent fields (`Board Status`/`Sprint`) and by-design-dropped ones
  (row `ID`) resolve to `UNRESOLVED` so the UI can degrade gracefully.
- **`engine/msp_filters.py`** — evaluates a `SavedFilter` against a task with the exact MPXJ semantics
  above (asymmetric normalization, null-aware compare, three string regimes, inclusive/order-independent
  `IS_WITHIN`, field-to-field, prompts, recursive short-circuiting `AND`/`OR`, `criteria is None` =
  match-all). Durations compare on the integer working-minute axis (exact), so MPXJ's float-hours
  tolerance and its symbolic-duration HOURS→0 quirk do not arise.

## Consequences

- No behavior change to any existing surface — the modules are new, the model fields are additive with
  defaults, and the importer addition is a new accessor. Parity untouched.
- Tested against the **10 real filters** (hand-authored fixtures + a synthetic population whose expected
  matches are checkable by eye), plus per-operator units, the resolver, and the raw-name-map importer
  path. A `.mpp`-driven parity test against MPXJ's own `evaluate` on the real file is deferred to PR-B
  (which brings the Java export that loads the definitions).
- Version 1.0.42 → 1.0.43; wheel + 9 installers rebuilt in lockstep. Remaining #10 increments:
  PR-B (Java export + ingest), PR-C (session-wide grouping + A–Z + highlight), PR-D (`/groups` UI).
