# ADR-0233 — Session-wide saved filter/group + highlight mode (feature #10, PR-C)

## Status

Accepted. PR-C of the flagship "Groups & Filters" feature #10. PR-A (ADR-0231) built the faithful
criteria evaluator; PR-B (ADR-0232) made `.mpp` saved filters/groups load. This PR wires those saved
views into the session so a chosen filter or group applies **everywhere at once**, adds a
**highlight** (mark-don't-drop) filter mode, and lands the A–Z ordering helpers. The `/groups` UI
that lets an operator pick them is the next PR (PR-D); this PR is the state + engine layer, tested by
direct calls (the same shape PR-A used).

## Context

The session already had a session-wide **field** filter (`active_filter`, ADR-0104): a flat AND of
`(field, value-set)` criteria that every page funnels through the single `SessionState.scope()`
chokepoint, so one filter reaches every metric on every page and every loaded version. A saved MS
Project filter is a different shape — a recursive tree with OR nodes, field-to-field comparands,
prompts, and up to 8+ clauses — so it cannot be expressed as `active_filter` and would trip the
field path's `MAX_FIELDS=5` guard. The two must coexist as two *sources* of one resolved scope.

Grouping, by contrast, was per-page only (a `breakdown`/`group_field` query param) — there was no
session-wide group state. And there was no way to *highlight* a filter's matches while keeping the
full population; the field filter only ever reduced.

## Decision

1. **Two filter sources, one chokepoint, mutually exclusive.** New `SessionState.active_saved_filter`
   (+ `saved_filter_prompts`) sits beside `active_filter`; setting either clears the other. A new
   private `_match_uids(sch)` resolves *whichever* source is active into a memoised UID set (the
   saved-filter tree walk can be called several times per request). `scope()` is rewritten to reduce
   via that set — routing both sources through one shared `grouping.filter_to_uids(schedule, kept)`
   primitive (refactored out of `filter_schedule`), so "reduce" means exactly one thing regardless of
   source. When the saved filter carries **show related summary rows**, the kept set is expanded with
   `grouping.with_ancestors` (outline-level parent walk) so the WBS context rows a filtered MS Project
   view keeps are restored — metrics are unaffected (the engine runs on non-summary tasks anyway).
2. **Highlight mode (mark, don't drop).** A session `filter_mode` (`reduce` | `highlight`) applies to
   both sources. In **highlight** mode `scope()` returns the population unchanged (only the Target UID
   can still truncate it), and a new `highlight_uids(sch)` exposes the match set for the grid/gantt to
   shade — so a metric is **never** silently changed by a highlight (forensic honesty; the future
   banner states this). Switching modes invalidates the scope cache (the population changes).
3. **Session-wide grouping, cheap by construction.** New `active_saved_group` + `set_saved_group()`.
   Grouping is ordering/banding only — it changes no metric population — so its setter deliberately
   does **not** invalidate the analysis/summary caches (a regroup never recomputes CPM). The engine
   realizes a multi-clause group as ordered `(label, uids)` buckets in new `engine/saved_grouping.py`
   `group_by_clauses`: each clause's `ascending` honored, clauses nested left-to-right, `groupOn == 2`
   clauses banded by the clause interval, blanks bucketed as `(none)`. Because a group clause
   references the **raw** MS Project field name (`Text9`, `% Complete`), lookups route through the
   PR-A raw-field resolver; a group whose first clause is unresolvable on a file degrades to a single
   `(ungrouped)` bucket rather than erroring.
4. **A–Z ordering + display names.** `SavedFilter`/`SavedGroup` gain a `display_name` property that
   strips MS Project's `&` keyboard-accelerator markers (`Mi&lestones` → *Milestones*, `&&` → literal
   `&`). New `saved_filters_union` / `saved_groups_union` gather the distinct saved views across every
   loaded version (dedup by name) sorted A–Z by `display_name.casefold()`, with `find_saved_filter` /
   `find_saved_group` for exact-name lookup — the pickers PR-D renders.

5. **Group-resolution fidelity (from a read-only audit against the real file, before merge).** A
   sandbox audit ran `group_by_clauses` over all 25 saved groups in the operator's real
   `Large Test File Leveled.mpp` and found four that collapsed to a single `(ungrouped)` bucket
   where MS Project shows real groups — none affecting a metric (grouping is presentation only), but
   fidelity gaps in a "faithful reproduction" feature. Fixed here:
   - MPXJ names a group's Duration column with the enum `DURATION_TEXT` (a custom duration as
     `DURATION8_TEXT`) — the same value, formatted. `msp_field_resolver` now strips a trailing
     `_TEXT` when the base names a real field, so `&Duration` / `Duration then Priority` group.
   - `% Complete` with `groupOn == 2` and a non-positive `interval` ("0") is MS Project's
     "Complete and Incomplete Tasks" built-in — now a two-bucket split at 100% (Complete /
     Incomplete), not one bucket per distinct percentage. (MPXJ carries no group-render oracle —
     unlike filters, where `Filter.evaluate()` exists — so this mirrors the documented built-in and
     the tool's own Complete/Incomplete convention; it would be reconfirmed against an MS Project
     rendering if one becomes available.)
   - `Task Mode` (the "Auto Scheduled vs. Manually Scheduled" group) now resolves from the model's
     `is_manual` flag.
   Groups referencing data the model does not carry — `Priority` / `Status` (deferred to a follow-up
   that adds those model fields) and `Board Status` / `Sprint` (MS Project Agile add-in fields, no
   source data) — still degrade to `(ungrouped)`, which is the honest behavior. Two SessionState
   nits from the same audit are fixed: `set_saved_filter(None)` no longer drops an unrelated active
   field filter, and `wipe()` clears `sra_focus_uid` alongside `target_uid` (they are coupled).

## Consequences

- A saved filter set on the session reaches every page/file automatically through `scope()` /
  `ordered()` / `analysis_for()` / `summary_for()` — zero per-page wiring, exactly like the field
  filter. `wipe` resets the saved filter (via `set_filter`), the saved group, and the mode.
- Behavior is unchanged when no saved filter/group/highlight is set: `scope()` still returns the
  schedule untouched when nothing narrows the population (the full existing filter/scope/group/target
  test suite stays green — 103 of those exercised directly).
- Two per-chart `filter_schedule` call sites (bow-wave S-curve, forecast) apply an *independent*
  field filter on top of the already-scoped `ordered()` versions — unaffected; the saved filter still
  reaches them via `ordered()`.
- `display_name` / `is_interactive` are computed **properties**, not fields, so the schema-freeze
  guard and JSON round-trip are untouched (no SCHEMA_VERSION change).
- The state layer is fully unit-tested by direct calls (saved-filter reduce/highlight, mutual
  exclusivity, show-summary-rows ancestors, cheap regroup, per-version reach); `engine/saved_grouping`
  and the shared reduction primitives have their own engine tests. No UI is wired yet — that is PR-D
  (pickers, prompt inputs, the highlight toggle, `data-highlight-uids` carrier + `highlight.js`, the
  banner, 4-theme DoD).
