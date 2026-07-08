# ADR-0164 — Schedule Integrity: never 500 with many files; two-file compare picker; briefing 3+4 duo

## Status

Accepted. Operator 2026-07-08: "When I tried to load like 20 or so schedule files and then open the
Schedule Integrity page I received [Internal Server Error] … I have tried far fewer files and I get
the same error … Figure out the root cause for the error and create a solution." And: "schedule
integrity seems to only work when there are two files, no more than two work. allow the user the
ability to select two files if there are more than two to compare and have the analysis run on."
And: "Fix number 3 and number 4 by splitting the available page space … so that the user does not
have to scroll … I don't want wasted page space."

## Context — two reproduced root causes for the 500

The change-effects panel (ADR-0162) runs a counterfactual CPM sweep per version pair, and the
Integrity page diffed **every** consecutive pair. Two unguarded exceptions were reproduced:

1. **`KeyError` on a summary target.** `compute_change_effects` indexed
   `base_cpm.timings[resolved_target]` directly. A summary / level-of-effort / unscheduled UID (the
   project-summary **UID 0** is the common one) is in `tasks_by_id` but excluded from CPM timings,
   so when the operator's focus **Target UID** resolved to such a task the index raised `KeyError`
   → unhandled → 500.
2. **`CPMError` on a cyclic revert.** Reverting a single detected change (restoring a removed
   predecessor link, dropping an added one, restoring a duration/constraint) can reintroduce a
   logic **cycle** the later version had broken. `compute_cpm` then raises `CPMError` — unhandled →
   500. With two well-matched files the single pair is usually clean (works); across many real
   program versions at least one pair hits a cyclic revert, so "only two files work."

Both were reproduced deterministically (a synthetic A→B→C / C→A pair for the cycle; golden
`Hard_File_updated` UID 0 for the summary target).

## Decisions

1. **Engine never raises (`change_effects.py`).** The target is required to be in `base_cpm.timings`
   (else return `None` — the panel is simply omitted). Each per-change re-solve is wrapped in
   `try/except CPMError`: a cyclic revert is **skipped** (from both the per-change list and the
   aggregate) and counted in `skipped_unsolvable`. The aggregate re-solve is likewise guarded
   (`aggregate_solved`); individual reverts are capped at `_MAX_CHANGE_EFFECTS = 60` (bounds the
   CPM-pass count on a huge diff) with the remainder counted in `skipped_capped`. Every omission is
   **disclosed** on the page (Law 2 — no silent drop).
2. **Web layer degrades, never 500s (`_integrity_body`).** `detect_manipulation`,
   `compute_change_effects`, and `compute_path_counterfactual` are each wrapped per pair; a failure
   logs a warning and drops that section rather than crashing the page.
3. **Two-file compare picker (operator request).** The page now analyzes **one** chosen pair —
   **Baseline (A)** vs **Comparison (B)** file selectors (`a`/`b` = file indices), defaulting to the
   two most recent, ordered prior→current chronologically regardless of pick order, and never
   collapsing to the same file. This matches "select two files to compare" **and** removes the
   multi-pair blow-up (one pair, bounded work). Legacy `?file=<label>` still resolves to
   (that file, its predecessor). With exactly two files the picker is implicit (hidden A/B).
4. **Briefing 3+4 (and 6+7) half-page duos.** `_briefing_body` pairs "3. The Critical Path — Then
   and Now" with "4. Schedule Health Dashboard" and "6. Recommended Actions" with "7. How to Verify
   Every Number" into full-width `.brief-duo` rows (1fr/1fr), and briefing tables gain a `max-height`
   scroll cap so a very long table (e.g. a 100+-row "No Longer Critical" list) scrolls inside its
   half instead of towering the page and wasting the width beside its short partner. Pairing is
   heading-anchored and only fires when both sections are present.

## Consequences

- `/integrity` returns **200** with 3/4/6+ files, with a summary Target UID set, with `a==b`, and
  with the legacy `file=` param — all previously-500 paths (verified end-to-end via TestClient +
  Chromium; new `tests/web/test_integrity_multifile_robust.py`, 9 tests). The known-good
  188→187 = **+23 working days** result on UID 155 is preserved through the picker.
- Briefing sections 3+4 render as balanced half-page partners with no wasted width and no page
  scroll (Chromium-verified). Law 1 untouched (pure in-memory recompute + client layout); Law 2
  upheld (every skip/cap disclosed; the aggregate figure is withheld, not faked, when it can't be
  solved). Parity suites unaffected.
