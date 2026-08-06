# ADR-0354 — Duration literals conform to the vendored MPXJ, and populations move visibly (V3 closed)

**Status:** Accepted · **Date:** 2026-08-06 · **Extends:** ADR-0310 (the two-axes contract) ·
**Closes:** audit finding **V3 / external H4** (elapsed duration literals), the last P2 item's
sibling in the 2026-08-03 remediation order, reserved for Fable 5 Max under ADR-0240.

## Context

`engine/msp_filters.py` was the sole violator of the repo-wide elapsed convention (ADR-0310:
zero `duration_is_elapsed` reads against 24 elsewhere): its `_DUR_UNIT_MINUTES` hard-coded a
480-minute day, and its regex captured the elapsed marker in group 2 and **discarded** it, so
`'2 ed'` (elapsed: 2880 wall-clock minutes) evaluated byte-identically to `'2 d'` (960 working
minutes) and an unknown unit silently read as days. The executed example
(`audit/VALIDATION-20260729.md` §V3c): `Duration > 2 ed` matched 6 of 8 tasks where a correct
elapsed reading matches 2.

**The reference was read from its own bytecode, not from memory.** The repo vendors the exact
MPXJ the converter runs (`tools/mpxj/lib/mpxj-16.2.0.jar`); `javap` on it settled every rule:

- `GenericCriteria` normalizes every Duration operand to **HOURS** via
  `Duration.convertUnits(HOURS, m_properties)` — comparing integer minutes preserves MPXJ's
  ordering exactly (both sides scale by 60), keeping the module's documented equivalence.
- `Duration.convertUnits`' factor table (locals: minutesPerDay, minutesPerWeek, daysPerMonth):
  DAYS × mpd · **WEEKS × mpw** (not 5×day) · MONTHS × mpd×dpm · **YEARS × mpw×52** (not 240
  days) · ELAPSED_DAYS × 1440 · ELAPSED_WEEKS × 10080 · ELAPSED_MONTHS × 43200 (30 d) ·
  **ELAPSED_YEARS × 524160 (364 d = 52×7, not 365)** · `%`/`e%` fall through the switch
  **default** (the value passes as minutes — a quirk mirrored, not repaired).
- The literal text domain is **closed**: the views sidecar writes criteria operands via
  `String.valueOf(value)` = `Duration.toString()` = `<double><token>` over exactly
  `m h d w mo % y` + `e`-prefixed elapsed forms (14 tokens, from `TimeUnit`'s static init).

So the audit's headline (elapsed) sat on top of **two more conformance defects the audit could
not see**: the working-year rule (v1: 115200 = 240 d; MPXJ: mpw×52 = 124800 on the standard
calendar) and the week basis (v1: a constant; MPXJ: the file's declared `MinutesPerWeek` — a
4×10 calendar's 2400 ≠ 5×600). ADR-0310 already reduced V3 from a product decision to a
conformance fix; the bytecode read defines "conform" precisely.

## Decision

1. **`_parse_duration_literal(text, calendar)` implements `Duration.convertUnits` verbatim.**
   Ordinary units scale by the schedule's own `working_minutes_per_day` /
   `minutes_per_week` / `days_per_month`; elapsed units are the wall-clock constants above;
   `%`/`e%` pass through; a bare number reads as days (MS Project's default unit). An unknown
   token **fails closed** (`None`, the malformed-leaf convention) — the vocabulary is closed,
   so an unknown unit can only mean a corrupted sidecar, and v1's silent 480-minute guess is
   exactly the defect class this repo does not ship. Long-form aliases (`"5 days"`) stay, for
   hand-typed prompt answers.
2. **`Calendar` carries the two project properties** (`minutes_per_week`, `days_per_month`,
   both `None` = "the source didn't provide it"); the MSPDI importer reads
   `MinutesPerWeek`/`DaysPerMonth` (a degenerate 0 stays `None`); the Save-format writer/reader
   round-trip them (the writer-coverage introspection guard caught the writer half). Absent
   values fall back to MPXJ's own defaults (2400 / 20), never a derived guess.
3. **Evaluator versioning + the migration report** — the gate the audit phrase required, now
   defined: `EVALUATOR_VERSION = 2`; v1's parser is kept **verbatim, report-only**, behind a
   ContextVar; `selection_migration_delta(schedule, filt, prompts)` returns
   `(v1_selection, v2_selection)` for any filter whose leaves compare a DURATION field against
   a literal/prompt (`filter_reads_duration_literals`), `None` for version-invariant filters.
   The `/groups` Active-scope panel renders the delta — "this filter now selects N (was M)" —
   whenever the sets differ, so the operator sees the shift instead of silently inheriting it.
4. **Prompt answers are stored RAW and coerced per schedule at selection** (`SessionState`
   stores the typed strings; `scope()` coerces on `sch.calendar`): one session filter across
   many files must scale a `"3d"` answer on *each* file's own calendar. The
   1,500-minute-task discriminator is pinned by test (survives on the 8-hour file, drops on
   the 10-hour one, for the same answer).

## Verification

- Every factor pinned against the bytecode read
  (`test_duration_literal_table_matches_mpxj_convert_units`), on three calendars including
  absent-properties fallback; the audit's executed example inverted into a pin (`> 2.0ed` →
  2 matches, was 6; unknown unit → 0, was 6); the delta helper, the ContextVar reset, the
  importer read, the Save round-trip, the per-schedule prompt coercion, and the `/groups` note
  (renders on movement, absent on a version-invariant filter) each have their own test.
- **Five mutations, each failing exactly its guard** (original-anchor-absent re-read each
  time; restores from scratchpad copies): elapsed-day → 480 · year → mpw×48 · ContextVar reset
  dropped · importer stamp dropped · per-schedule calendar → default. The fifth fired only
  after the prompt test gained the 1,500-minute discriminator — its first draft passed under
  the mutation (the identity-case trap, same lesson as ADR-0353, caught in-session).
- Engine + importer + affected web suites 1,264 passed; `pytest -m parity` 49 passed.

## Consequences

- **No committed artifact moves.** The fixture corpus carries no views sidecar, and the ten
  real filters pinned from the operator's Leveled export use duration fields only
  field-to-field (version-invariant). Population movement exists on synthetic evidence and on
  any future real filter with a duration literal — where the `/groups` note discloses it.
- A duration literal on a non-standard calendar now selects what MS Project selects; the cost
  is that `_parse_duration_literal` needs a `Calendar`, threaded through `_coerce_literal` /
  `_resolve_operand` / `coerce_prompt_answers`.

## Deliberately NOT done

- **`%`/`e%` pass-through is mirrored, not "fixed"** — it is MPXJ's own switch default;
  inventing a percent→minutes scale would be fabrication (Law 2).
- **Field-side elapsed handling is untouched** — stored minutes are already wall-clock for
  elapsed tasks (the eight conforming display sites divide by 1440), so field-to-field
  comparisons were never wrong.
- **The XER/P6 path gains nothing here** — P6 has no saved-filter sidecar in this tool.
- **MPXJ's 1e-5 float-hours tolerance stays un-replicated** — both sides remain exact integer
  minutes; the module docstring's equivalence argument is unchanged by the new factors.
