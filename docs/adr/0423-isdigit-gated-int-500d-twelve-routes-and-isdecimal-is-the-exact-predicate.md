# ADR-0423 — `isdigit()`-gated `int()` 500'd twelve routes, and `isdecimal()` is the exact predicate

**Status:** Accepted · **Date:** 2026-08-18 · **Closes:** `ISDIGIT-INT-500` (audit 2026-08-16 —
REPORTED as *medium*, one site; measured as **12 routes across 5 sites**) ·
**Ships:** `web/app.py`, `web/system.py`, `engine/metrics/wbs_breakdown.py`,
`importers/_common.py`, `importers/mspdi.py`

## Context

`str.isdigit()` is **True** for superscripts (`²`), circled forms (`①`) and many other Unicode
numeric characters that `int()` rejects with `ValueError`. An `isdigit()`-gated conversion is
therefore not a guard at all: it admits the value and then raises. Typing a superscript into an
ordinary form field answered **500**.

The tool already knew this. `sra_grid_save`'s local `_uid` helper carries the comment *"int()
directly (not isdigit(), which admits values int() rejects — '--5', '²', … — and would 500 the
endpoint); a clean parse or None (audit L5)"*. That lesson was applied to exactly one endpoint;
five other sites kept the broken pattern. As with ADR-0421, the codebase contradicting itself is
what settles the intended semantic without needing an external oracle.

## How the population was measured — and why the ledger's "one site" was low

This came out of the route × test coverage census (below). Fuzzing only the 25 routes the census
flagged as having **no adverse-path coverage** found **6**. Fuzzing *every declared field of every
route* found **12** — routes that DO have adverse coverage carry the same bug on a different
field. The narrower sweep looked exhaustive and was not, which is the same shape as ADR-0418's
"four modules" that were 23 and ADR-0420's "three surfaces" that were eight.

| site | routes |
| --- | --- |
| `_parse_uid` (`app.py`) | `/api/activities/drill`, `/driving-path`, `/export/{fmt}/activities-drill`, `/scurve`, `/sra/correlation-matrix`, `/sra/risk`, `/sra/risk-register`, `/target` |
| `export_activities` (`app.py`) | `/export/{fmt}/activities/{name}` |
| `sra_branch` (`app.py`) | `/sra/branch` |
| `ssi_run_config` (`app.py`) | `/sra/ssi-run-config` |
| `ssi_set_factor` (`app.py`) | `/sra/factor` |

Three further sites of the same class are not route-reachable and were fixed with them:
`web/system.py` (parsing `vm_stat`), `engine/metrics/wbs_breakdown.py` (a WBS label going to
`float()`), and `importers/mspdi.py` (a calendar UID from file input).

## Decision — and a correction to this ADR's own first fix

Replace the predicate with **`str.isdecimal()`**, keeping each caller's own sign policy.

The first attempt was `isascii() and isdigit()`, and it was wrong in the **opposite** direction.
Measured across all 788 single-character numeric code points:

| predicate | disagrees with `int()` on |
| --- | --- |
| `isdigit()` | **128** (the bug: accepted, then raises) |
| `isascii() and isdigit()` | **650** (over-narrow: rejects what `int()` parses fine) |
| `isdecimal()` | **0** |

`isdecimal()` is exactly the set `int()` accepts. The ASCII version would have silently stopped
resolving Arabic-Indic digits — turning a crash into a wrong answer, which under Law 2 is worse.

**That error was caught by this change's own guard-the-guard test**, not by review: the probe-value
assertion (`every probe value must be isdigit()-true AND make int() raise`) failed on `٣`, because
`int("٣") == 3`. A control written to keep the sweep from passing vacuously is what stopped a bad
fix from shipping.

## Consequences

`tests/web/test_route_input_robustness.py` — 4 tests, population **computed** from the live app
(every `APIRoute`'s every declared parameter, 290 field slots), never a hand list, because this
class hides in whichever field nobody thought to fuzz. Both halves are pinned:

- `test_no_route_raises_on_unicode_digit_input` — the crash half;
- `test_the_fix_narrowed_nothing_that_int_accepts` — the half a crash-only test cannot see, and
  the one that reddens on the ASCII version.

Mutation **2/2 by name**, both landed: reverting to `isdigit()` reddens both tests; the
over-narrow ASCII version reddens the narrowing test alone.

Before: 12 routes raised across 255 probed field slots (the sweep bailed early on crashing
routes). After: **0 across 290**. `pytest -m parity` **72 passed**, unmoved — the
`wbs_breakdown` / `mspdi` edits touch no parity value.

**Not claimed:** that no route can 500 on any other input. This closes one predicate class. The
fuzz probed single hostile values per field, not combinations, and 35 endpoints declare no fields
at all.
