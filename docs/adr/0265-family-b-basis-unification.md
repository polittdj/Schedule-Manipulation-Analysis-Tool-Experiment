# ADR-0265 — family-B basis unification: one basis per counterfactual page

## Status

Accepted. Executes the behavior work ADR-0251 queued ("unify the family-B option plumbing so
every element of a counterfactual page shares one basis"), which ADR-0251's own disclosures
had honestly bridged until now. Family A (the SSI-parity stored-date trace: /path,
/api/driving, the default full-trace export) is untouched — its parity anchor stays exactly
as pinned.

## Decisions (the three queued sub-items)

1. **The stepper shares the page's basis.** `/api/evolution` accepts
   `ignore_constraints`/`ignore_leveling` and applies the same `_optioned_versions`
   transform as the server-rendered panels; `/evolution` embeds its active options as
   `data-ignore-*` attributes on the chart host and `path_evolution.js` forwards them.
   Defaults (and the /mission wall, which embeds no attributes) reproduce the
   stored-schedule payload byte-for-byte.
2. **The full-trace export runs on the page's basis.** `/export/{fmt}/path/{name}` gains
   `basis` (default `stored` = today's SSI-parity trace, byte-identical — pinned including
   `basis=resolve` with no options being a no-op). The /driving-path link passes
   `basis=resolve`: with options active the export is computed on the SAME re-solved
   network as the tiers panel (the transform embodies the options at the network level, so
   the trace's family-A flags are then off — never double-applied), and the workbook title
   carries a "counterfactual re-solve basis" marker. The /path page's export keeps the
   stored basis.
3. **The drill (and its Excel) stop mixing bases.** The added-field columns come from the
   BASE analysis rows; the solve-dependent ones (Start, Finish, Total float, Critical) are
   now HIDDEN while the options are active — on screen (`SOLVE_DEPENDENT` filter +
   explanatory note in the columns bar) and in the tiers export (server-side filter, belt
   against hand-crafted URLs). Basis-independent input columns (durations, % complete,
   WBS, resources, baselines, custom fields) always remain. Hiding was the ADR-0251
   sanctioned alternative to option-solving `/api/analysis`, whose blast radius (an
   option-aware analysis cache tier) is not justified by convenience columns.

The active-options banner, the drill caption, and `_completed_on_path_panel`'s docstring now
state the unified truth (the old mixed-basis disclosures are gone because the mix is gone);
the ADR-0251 route-divergence pin was re-targeted accordingly.

## Consequences

- Tests: `tests/web/test_family_b_unify.py` (8 — stored default byte-identity for feed and
  export; the optioned feed serves the re-solved network; page embeds/JS forwards the
  options; the wall stays stored-basis; `basis=resolve` differs from the stored trace
  exactly when options are active; the tiers export drops solve-dependent columns under
  options and keeps input columns; the JS hide list names exactly the stored-basis fields).
  `test_path_options.py`'s family-divergence pin updated to assert the unified state.
- Browser-verified (Chromium): the live stepper fetch carries the option, the drill note
  renders, the export link carries the page basis, zero console errors on both pages.
- Family A byte-identity everywhere: no default changed, no engine math touched, parity
  green. Version 1.0.70 → 1.0.71; wheel + 9 installers in lockstep.
