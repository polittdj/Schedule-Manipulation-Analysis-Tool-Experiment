# ADR-0166 — Integrity crash-fix hardening (adversarial-review findings)

## Status

Accepted. Follow-up to ADR-0164: an adversarial multi-agent review of the Schedule-Integrity 500
fix surfaced four confirmed defects (one high-severity fidelity bug + three disclosure/robustness
gaps). All are fixed here.

## Findings and fixes

1. **(HIGH — Law 2 fidelity) Out-of-range baseline reversed the diff.** With `comparison_idx == 0`
   (reachable via `/integrity?b=0` with the baseline omitted, or the legacy `?file=<oldest file>`),
   the baseline resolved to `cur - 1 == -1`; the `if base == cur` collapse guard did not catch a
   *negative* index, so `schedules[-1]` — the **newest** file — was used as the prior, silently
   rendering a chronologically **reversed** diff (every added link read as removed, every duration
   increase as a decrease) as authoritative forensic output. Fixed by broadening the guard to
   `if base == cur or not (0 <= base < n)`, re-picking an in-range chronological neighbour. The
   pair now always reads prior → current oldest-first.
2. **(low) Ribbon-drill / float-band Excel exports could 500.** `export_ribbon_drill` and
   `export_float_band` called `st.analysis_for(name, …)` unguarded; a direct/bookmarked URL to an
   **unsolvable** file (cycle / ALAP / constraint-without-date) raised `CPMError` → 500. Both now
   `try/except CPMError → 422`, matching every other `analysis_for` call site.
3. **(low — Law 2) All-skipped reverts hid the disclosure.** When a pair had detected changes but
   every isolated revert cycled (all `skipped_unsolvable`), `if not effects: return None` fired
   before the report was built, so the page silently omitted the change-effects panel. Now the
   engine returns a report with empty `per_change` when any change was detected-but-skipped, and
   the page discloses "N change(s) detected but none could be measured individually."
4. **(low — Law 2) "Every change reverted together" over-claimed its population.** The aggregate
   re-solve folds in only the individually-measured reverts (skipped/capped ones are excluded), yet
   the headline said "every change." Now the wording states the honest count — "all N change(s)
   reverted together" — and, when any change was skipped/capped, "the N individually-measured
   change(s) reverted together (the skipped change(s) noted below are excluded)." The engine also
   only computes an aggregate when at least one revert was measured (`aggregate_solved` reflects it).

## Consequences

- The reversed-diff fidelity bug is closed: `?b=0` and `?file=<oldest>` render a chronological pair
  (verified — prior label is never a later "updated" file). The +23-working-day 188→187 result and
  the "all N change(s)" honest aggregate are preserved. Unsolvable-file exports return 422, never
  500. Every skip/cap is disclosed. New regression tests in `test_integrity_multifile_robust.py`
  cover the reversed-diff guard, the all-skipped disclosure, and the export guard. Laws 1 and 2
  upheld; parity suites unaffected.
