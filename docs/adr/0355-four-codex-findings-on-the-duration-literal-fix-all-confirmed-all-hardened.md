# ADR-0355 — Four Codex findings on the duration-literal fix: all confirmed, all hardened

**Status:** Accepted · **Date:** 2026-08-06 · **Extends:** ADR-0354 ·
**Source:** the operator relayed four automated (Codex) review comments on merged PR #545;
each was independently re-verified against the code and the vendored MPXJ bytecode before any
edit (ADR-0240: findings have been wrong before — these four were not).

## The findings, adjudicated

**C1 — the day scale is the DECLARED setting, not the derived day length. CONFIRMED,
partly self-inflicted:** the ADR-0354 bytecode read correctly identified `ProjectProperties`
as `convertUnits`' context, then the implementation threaded `calendar.working_minutes_per_day`
(the derived dominant day length) instead of the file's `Project/MinutesPerDay` property. On a
file declaring an 8-hour duration setting over a 10-hour calendar, `1d` evaluated as 600 where
MPXJ says 480. Fixed: `Calendar.declared_minutes_per_day` (SCHEMA 2.11.0), read from
`Project/MinutesPerDay`, used by the literal parser with MPXJ's 480 default when absent —
which also corrects the absent-property fallback for `d`/`mo` (previously the derived length,
now MPXJ's default, matching what MPXJ itself would do).

**C2 — the v1 migration leg received v2-coerced prompts. CONFIRMED (the limitation was even
documented in the shipped docstring instead of fixed):** prompt-only population movement could
never produce the migration notice. Fixed: `selection_migration_delta` takes the RAW typed
answers and coerces them under EACH parser — the ContextVar covers prompt coercion and literal
evaluation alike, so the v1 leg genuinely re-lives v1 (`"3d"` = 1,440 min) while v2 uses the
calendar-true value. Pinned by a delta of `((1,), ())` on a 1,500-minute border task.

**C3 — `model_copy(update=...)` bypasses `gt=0`. CONFIRMED (documented pydantic behavior):**
a malformed document with a negative `MinutesPerWeek` produced a calendar with negative scale
factors and inverted week/year thresholds. Fixed: the importer sanitizes non-positive values
to `None` before the copy (the JSON path already constructs and therefore validates).

**C4 — "fails closed" was only half-true. CONFIRMED by re-derivation:** an unparsable
duration literal returned `None`, which is the REAL `EQUALS <null>` operand and rides MPXJ's
null-ordering rules — so `Duration < 5xyz` and `!= 5xyz` matched EVERY task (fail-open in the
broadening direction), while only the `>`/`>=`/`EQUALS` directions failed closed (exactly the
directions ADR-0354's test happened to pin). Fixed: a `_Malformed` sentinel distinct from
`None`; any leaf touching it returns False whatever the operator, including both WITHIN
bounds. `EQUALS <null>` semantics are untouched, and a malformed *typed prompt answer* keeps
the pre-existing "unanswered" posture (sentinel never enters `PromptValues`).

## Verification

Four mutations, each failing exactly its guard, each original-anchor-absent-checked, each
restored from scratchpad copies: sentinel→`None` · declared→derived · v1-prompt coercion
hoisted outside the token · sanitizer→raw `_int`. **The C1 mutation survived its first pin** —
the test population made the 480 and 600 thresholds select identically; a 600-minute
discriminator task was added before the mutation was accepted (the third
identity-case/discriminator failure caught in one day, after ADR-0353's and ADR-0354's).
Statics green; impacted suites 457 passed; parity 49; full suite run before commit.

## Consequences

- `EVALUATOR_VERSION` stays **2**: v2 shipped hours earlier with no operator exposure on any
  real filter (no views sidecar in the corpus), so these are corrections *to* v2, not a v3 —
  the migration report still compares against the long-lived v1.
- The conformance test's absent-property row changes meaning: a calendar with a 600-minute
  derived day but no declared properties now evaluates `1.0d` as **480** (MPXJ's default),
  not 600 — deliberate, re-baselined with the ADR named.

## Deliberately NOT done

- **DATE literals share C4's `None` shape** (`parse_datetime` → `None` → null-ordering) — a
  PRE-existing, pre-ADR-0354 behavior outside this unit's scope; recorded here so the next
  session inherits a citation, not a surprise. The duration argument (closed vocabulary ⇒
  malformed = corruption) does not transfer cleanly to dates, which accept operator-typed
  prompt answers on the same path.
- **`working_minutes_per_day` remains the engine-wide day length** for duration→days display
  everywhere else; only filter LITERALS read the declared setting, exactly mirroring MPXJ's
  split between calendar time and `TimeUnitDefaultsContainer`.
