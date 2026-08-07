# ADR-0369 — /integrity discloses what it cannot measure: target banner, skipped identities, baseline magnitudes

**Status:** Accepted · **Date:** 2026-08-08 · **Extends:** ADR-0162 / ADR-0358 · **Relates:** ADR-0366

## Context

Audit F2/F4 (2026-08-07) caught three disclosure gaps on /integrity, all of the same species —
a silence where Law 2 demands a statement:

1. `compute_change_effects` returned **None** for BOTH "the target cannot anchor a
   measurement" and "no changes detected", so the page omitted the change-effects panel
   **silently** when the operator's focus UID did not resolve (absent, unscheduled, summary).
2. Skipped reverts (logic-cycle unsolvable; beyond the 60-revert cap) were disclosed
   **count-only** — never *which* changes went unmeasured.
3. The DECM-29I401a baseline finding named the activities but stated **no magnitude**: FX-06's
   frozen finish rendered "UID 131" with neither the old/new baseline dates nor a day delta.

## Decision

1. **Target-unavailable sentinel + banner.** An unresolvable target returns a
   `ChangeEffectsReport` with `target_unavailable=True` carrying the failed target's identity —
   per_change empty, every figure 0, `aggregate_solved=False` — and /integrity renders a
   change-effects panel stating WHY nothing is measured and what to do ("pick a different focus
   activity or clear the focus"). "No changes detected" still returns None (contract kept).
2. **Skipped identities.** The report carries `skipped_unsolvable_labels` /
   `skipped_capped_labels` (`len == count` by construction); the page lists them in
   `<details class=skipped-changes>` collapsibles under the existing count notes, in both the
   normal and the all-skipped branches.
3. **Baseline magnitudes.** The DECM-29I401a detail names each movement — "UID n baseline
   finish 2025-02-01 → 2025-03-03 (+30 calendar days)", with "set to … (was unset)" and
   "erased (was …)" for one-sided changes — first 6 verbatim, the remainder counted, every
   activity cited as before.
4. **The qa fact base never states a figure for a non-measurement**: the sentinel emits no
   change-effect facts at all, and the aggregate fact is emitted only when at least one revert
   measured AND the joint re-solve succeeded — phrased "EVERY detected change" only when
   nothing was skipped, else "the N individually-measured change(s) … (skipped changes
   excluded)" (the page's ADR-0358 wording; the old fact overclaimed "EVERY" on partial
   aggregates and stated "+0 working day(s)" even when nothing had been measured).

## Verification

Engine: sentinel + twins (`test_target_unavailable_returns_a_disclosed_sentinel_not_none`),
cycle-fixture labels, cap-fixture label census (`len == count`). Manipulation: the
moved/set/erased magnitude matrix with derived day counts. Web
(`tests/web/test_integrity_disclosure.py`): banner + twin, identity list, FX-06-class baseline
magnitude render, qa unavailable-target + twin. Proven able to fail by four reverts: sentinel
back to None → 2 named; qa aggregate unconditional → 1 (after fixing the revert itself — the
first splice re-declared the function and changed nothing); labels uncollected → 3; pristine
magnitude → 2. All restored, 31/31 green.

## Deliberately NOT done

- The banner is text-in-panel only — no new tokens, no chart, no DD-line involvement.
- Baseline movement deltas are **calendar days, labeled as such** — a working-day walk over
  baseline dates would need the baseline calendar, which the file does not carry.
- The capped-labels list can be long by design (cap 60); it sits behind `<details>` and costs
  no CPM pass.
