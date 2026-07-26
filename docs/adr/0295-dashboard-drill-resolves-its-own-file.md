# ADR-0295 — A drill trigger resolves ITS OWN version, manifest-wide; a named miss is an error

- **Status:** Accepted
- **Date:** 2026-07-25
- **Related:** ADR-0258 (dashboard = session manifest, every Project), ADR-0288 (lazy segment
  drill), ADR-0291 (named the `status_mix_uids` trim this fix must precede), ADR-0284 (Fix E — the
  previous cross-project leak in this family)

## Context

Found while scoping the dashboard `status_mix_uids` payload trim (ADR-0291's residual): the
generic activity drill (`/api/activities/drill` + `/export/{fmt}/activities-drill`) resolved its
`file` parameter through `_pick_scorecard_version`, which searches **the active Project's
population only** (`ordered_versions()`) and silently falls back to `versions[-1]` when the
requested key is not found.

But the dashboard is the session **manifest** (ADR-0258): one card per loaded file, *every*
Project, and each card's status bar marks its segments with that card's own key. So with two
Projects loaded, clicking the non-active Project's card resolved against the **active** Project's
latest version instead. Reproduced on the golden pair (Alpha/Project2 + Bravo/Project5, Bravo
active):

```
card Project2   card.complete=20   drill rows=20   resolved file=Project5
```

Those 20 rows are Project5 activities that happen to share UIDs with Project2's complete set —
**wrong data presented under the right label**, the exact failure class Law 2 exists to prevent.
The planned lazy-segment trim would have made it *worse*, not better: `segment=complete` against
the substituted file returns 27 rows — Project5's own complete set — a fully self-consistent,
entirely wrong answer, with no visual tell at all. That is why this fix lands **before** the trim,
in its own PR (a correctness fix never rides with a perf change).

## Decision

A new `_pick_drill_version(file)`, used only by the two drill endpoints:

1. **`file=""` is unchanged** — latest solvable of the active population. That is how the
   UID-only triggers (sra.js's per-activity bars) have always worked.
2. **The active population is searched first, exactly as before** — every trigger that resolved
   correctly yesterday resolves identically today; a label duplicated across Projects still
   prefers the active one. The widened search only *adds* resolution where the old path
   substituted.
3. **Then the manifest** (`all_versions()`) by key or label, running the version through
   `analysis_for` (epoch-keyed, single-flight) so the drill sees the same scoped schedule the
   card was projected from.
4. **A named version that cannot be resolved (unknown, or unsolvable) is an error** — 400 on the
   JSON endpoint, 422 on the export, naming the requested version. Never a substitution.

The scorecards pages keep `_pick_scorecard_version` unchanged: they are analysis views with their
own version selector, where "fall back to latest" is visible navigation behaviour, not a silent
data swap under a clicked element's label.

## Consequences

- Every dashboard card now drills against its own file, both by explicit UID list and by lazy
  segment; `tests/web/test_dashboard_drill_scope.py` pins card-vs-drill agreement per segment for
  **both** Projects, the named-miss error on both endpoints, and the two behaviours that must not
  change (unnamed fallback, active-population resolution). 5 of its 7 tests fail on the pre-fix
  tree; the other 2 are the anti-regression pins.
- Clicking a non-active card computes that version's `_Analysis` on demand (one CPM pass, cached
  under the standard (key, scope-epoch) key). That cost is paid only on an explicit operator
  click, matches what `dashboard_core_for` already does for every card at render time, and the
  cache makes the second click free.
- The `status_mix_uids` trim (ADR-0291's residual) is now safe to build: the forward guard in the
  new test file asserts the server-resolved segment equals the card's own count for every card in
  the manifest.
- Blast radius verified before the change: only `drilldown.js` calls these two endpoints, and
  every other trigger family (trend, CEI, performance, volatility, ribbon, WBS) passes either an
  active-population key/label or an empty `file` — both preserved bit-for-bit by (1) and (2).
