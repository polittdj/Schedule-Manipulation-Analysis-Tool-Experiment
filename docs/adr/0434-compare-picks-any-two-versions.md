# ADR-0434 — /compare picks any two versions, and the workbook can never describe a different pair than the page

**Status:** Accepted · **Date:** 2026-08-20 · **Extends:** the /integrity a/b picker (operator 2026-08-08 family)

## Context

Operator ask (2026-08-20): "On the What Changed page I want the user to be able to select any
two schedules and have the program do a comparison of the two and show what has changed and not
just the last two status dates."

Measured baseline: `/compare` took NO query parameters and hardcoded `schedules[-2]`/`[-1]`;
`/export/{fmt}/compare` hardcoded the same pair separately. `/integrity` had already solved this
exact problem (a/b indices + an index-resolution guard whose comment records the Law-2 bug it
defends: an out-of-range baseline wraps to `schedules[-1]`, the NEWEST file, and silently renders
a chronologically REVERSED diff).

## Decision

- `/compare` and `/export/{fmt}/compare` take `a`/`b` (baseline/comparison indices into the
  data-date-ordered analyzable list), resolved by ONE shared `_resolve_pair_indices` —
  /integrity's guard verbatim: default to the two most recent, re-pick an in-range neighbour for
  any bad index, and order prior → current chronologically regardless of pick order
  (`test_pick_order_never_reverses_chronology` asserts a=1&b=0 renders byte-identical to
  a=0&b=1).
- **The bare URL keeps its exact byte shape** (the ADR-0320 emit-only-non-default rule): default
  pair → bare export target and unchanged chip ordinals, so every existing pin, remembered URL
  and oracle label still holds. A picked pair threads `?a=&b=` through the export bar and the
  signals panel's `data-export` (`_compare_body(..., export_qs=)`), so ⤓ EXCEL always downloads
  the pair on screen.
- The picker renders only when there is a choice (n > 2): a plain `viz-controls` GET form —
  deliberately NOT a shelled panel, so the pinned ⛶/panel counts on the two-version default page
  do not move.
- The chip ordinals become `prior_idx+1 → cur_idx+1` (identical to before on the default pair).
- Nav/home copy updated from "the two most recent" to "any two versions you pick"
  (state.py role card, the home link, and the i18n catalog entry in all four locales).
- The render oracle gains the hand-authored variant `[picked-pair] GET /compare` —
  `/compare?a=0&b=1` — because the bare label always renders the default pair, so the resolver
  and the non-default export target were unreachable by the corpus (labels regenerated in the
  same commit, per the corpus guard's own instruction).

## Consequences

- Any two of N loaded versions can be diffed on the page and in the workbook, with chronology
  guaranteed; the engine layer needed no change (every diff entry point already took an
  arbitrary prior/current pair).

## Deliberately NOT done

- **The version-pair basis stays `_pair_versions()`** (filter-scoped, never target-truncated,
  ADR-0371) — the picker changes WHICH two, never HOW they are scoped.
- **/integrity's picker was not unified into a shared component** — the two pages' pickers have
  different markup contexts (a shelled panel there, bare controls here); the RESOLVER is the
  shared piece, and it is one function.
