# ADR-0415 — TST-01: the single-CPM gate could not see the primary solve

**Status:** Accepted · **Date:** 2026-08-17 · **Closes:** TST-01 (audit 2026-08-16) ·
**Delivers:** ADR-0352's promised standing sweep · **Ships:** tests only

## Context

`tests/web/test_single_compute.py` is the W5 regression gate: one CPM solve per schedule, with
the JSON and driving views reusing the cached `_Analysis`. It patched a hand-written tuple of
ten modules — `_CPM_HOLDERS` — and counted calls through them.

Two independent failures had accumulated in that tuple:

1. **`web.state` was absent.** ADR-0297 moved the session machinery (and with it
   `_compute_analysis`, the **primary** solve) out of `app.py` into `state.py` *after* the tuple
   was written. The gate could not see the solve it exists to guard.
2. **`web.app` was listed but no longer binds `compute_cpm` at all**, and the loop's
   `if getattr(mod, "compute_cpm", None) is not None:` skipped it **in silence** — a fail-open
   that looked like coverage.

Measured: **24** modules in the package bind `compute_cpm`; the tuple named 10, one of them
dead. Injecting two extra `compute_cpm` calls into `state.py`'s warm path left the module
**passing**.

## What the finder got right, and what it got wrong

The finder's claim ("`_CPM_HOLDERS` is stale") is **true**, and its mutation probe genuinely
left the test green. Its *diagnosis* of that probe was wrong, and the lead re-verification found
it — which is the point of the rule that no finding is reported until it is re-verified.

With the sweep repaired, the injected solves **are** counted: `after_page` moves 2 → 4. The test
still passed, because the assertion is `calls["n"] == after_page` — a **self-baseline**. Anything
added inside the page build lands in `after_page` on both sides of the comparison and cancels.
So the staleness and the blindness were two separate defects, and fixing only the one the finder
named would have left the gate exactly as blind as before while looking repaired.

## Decision

**Compute the holder set; pin the build.**

- `_cpm_holders()` walks the package, imports every module (so a lazily-imported call site
  cannot hide) and returns every module binding `compute_cpm`. A new call site is now
  *discovered*, not remembered. This is the "standing sweep" ADR-0352 promised and never built.
- `test_the_cpm_holder_sweep_reaches_the_primary_solve` asserts the sweep names `web.state`,
  `engine.cpm` and `engine.recommendations`, and that it has not collapsed (`>= 20` as a
  **floor**, explicitly not a census — adding a solver module must not fail it, a broken walk
  must).
- The counting test asserts `holders` is non-empty before patching, so a vacuous 0 can never
  read as success.
- The page build is pinned as a **ceiling**: `after_page <= 2` (the one `_compute_analysis`
  solve plus DCMA-14's deliberate critical-path re-solve), with a failure message that tells
  the next engineer to justify and re-baseline rather than silently widen.

## Verification (QC-1)

- **Blind proven first**, on the shipped tree: two extra solves injected into `state.py`'s warm
  path in a PYTHONPATH shadow → `1 passed`. The gate demonstrably could not fail.
- **Sighted proven after**: the same mutated shadow now fails **by name** on the ceiling —
  *"the page build made 4 network solves, was 2"* — while the real tree stays green.
- **Sweep guard mutation-proven 2/2 by name**: S1 the sweep collapsed to the definition module
  only; S2 the sweep restricted to `engine.*` (re-hiding exactly the ADR-0297 move that caused
  this). Both caught. The test file was restored byte-identical afterwards and md5-verified —
  this battery mutates an *instrument*, so the restore is part of the measurement.

## Consequences

- The `2` is a measured constant and says so. That is the "measured, then pinned" trap this
  repo has paid for before, so it is a ceiling with a named reason and an actionable message,
  not a bare number.
- A hand-maintained list of call sites is a stale list waiting to happen. Where a guard needs to
  know "everywhere X is referenced", it should compute it. The ten-module tuple was correct the
  day it was written; nothing warned when the code moved out from under it.
