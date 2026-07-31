# 0318 — `data-noprint` gets its one global rule in the A5 print block (operator decision C1)

Date: 2026-07-31
Status: accepted

## Context

The `data-noprint` attribute was set at 12 literal sites — 8 in `app.py` (including the
`_shell_tools` helper behind ~57 contract-panel toolbars, and the `/analysis` version chips)
and 4 in vendored JS (`trend.js` ×2, `curves.js`, `scatter.js` since ADR-0317) — but **zero
CSS rules referenced it**, so every marked control still printed. ADR-0305 measured this and
left it "decision-ready, not shipped" because one rule changes ten-plus merged contract pages
at once; DESIGN-SYSTEM §7's DoD checkbox ("controls hidden in print") was unsatisfiable until a
rule landed. The operator answered the briefed decision on 2026-07-30 (**C1**, recorded in
`docs/STATE/PLAN-20260730.md`): one global rule in base.css's A5 print block, with three
sub-answers — the `/analysis` version chips stay print-hidden as marked; a single-theme print
check suffices (the print block forces black-on-white over the theme tokens); the two
`viz-controls` carriers keep their now-redundant attribute for uniformity.

ADR-0076 already records base.css as THE print home, and `test_accessibility.py`'s print test
pins the rules there — a separate `print.css` was foreclosed (brief option C2).

## Decision

One line inside the existing `@media print` block:

    [data-noprint]{display:none!important}

`!important` is required twice over: `app.css`'s later `.tile-actions{display:flex}` wins the
cascade otherwise, and even inside base.css the later `.sf-tools{display:inline-flex}` ties the
attribute selector on specificity — and the A5 block's existing idiom is already `!important`.
The rule is self-maintaining: a new screen-only control opts in by carrying the attribute,
which keeps §7's wording true exactly as written.

## Verification

- Content pin (`test_accessibility.py::test_data_noprint_marked_controls_are_hidden_in_print`):
  the rule exists AND sits inside the `@media print` braces (never a screen hide).
- Measured (`tests/web/test_print_noprint.py`, real chromium, single theme per sub-answer 2):
  on `/analysis` — a page carrying the shared toolbars and the version chips — print-media
  emulation computes `display:none` for every `[data-noprint]` element (≥5 on the page) while
  the panel content (h2) still prints, and flipping back to screen media restores the
  controls. Proved able to fail: with the rule stashed, both tests fail (2 failed, read).

## Consequences

Ten-plus merged contract pages now print without their screen-only chrome, as §7 always
promised. The two `.viz-controls` carriers are doubly hidden (harmless, per the sub-answer).
Print output changes on every page whose panels carry `_shell_tools` — that page-wide sweep is
this decision's point, and the operator chose it with that stated cost.
