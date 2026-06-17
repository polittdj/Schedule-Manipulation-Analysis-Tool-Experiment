# ADR-0062 — Critical-path "gained float" counterfactual: what the finish would be if cut work were restored

Date: 2026-06-17 · Status: accepted

## Context

Operator: *"Provide an analysis on tasks that were removed from the critical path that did not
complete, and calculate what the effect on the target UID would have been if they had not had
their duration changed, logic changed, or constraints added. Exclude tasks that completed.
Also explain how a task 'gained float' and was therefore removed from the critical path."*

The `/evolution` view already attributes why each activity **leaves** the critical path
(`completed`, `duration_down`, `logic_removed`, `constraint`, `gained_float`), but it never
**quantified** the schedule impact of the changes — i.e. how much of an apparently-recovered
finish came from cutting/removing work on the path rather than from real progress.

## Decision

New engine `engine/path_counterfactual.py` → `compute_path_counterfactual(prior, current,
prior_cpm, current_cpm, *, target_uid)`:

1. Take the activities that **left** the critical path (`prior.critical − current.critical`),
   **excluding** ones that are now **complete** (you cannot un-complete delivered work) and ones
   removed from the schedule.
2. Split the rest:
   - **Reverted** — the activity's own **duration / constraint / logic** changed. These changes
     are reverted to their prior-version values (duration restored, constraint restored, removed
     links re-added / added links dropped — only between endpoints that still exist).
   - **Gained float** — the activity is **unchanged**; it left only because a slip elsewhere made
     another chain longer. Nothing to revert; reported + explained (this is the plain-English
     "how a task gains float").
3. Re-run `compute_cpm` on the counterfactual schedule and report the **project finish** (and,
   when a target UID is set, that activity's finish) **actual vs counterfactual + the day delta**.
   A positive delta is schedule time the *changes*, not progress, removed from the path. An
   unsolvable counterfactual network (e.g. a re-introduced cycle) degrades to naming the
   activities without a finish.

Surfaced as a server-rendered **"What-if: work removed from the critical path"** panel on
`/evolution` (latest version pair, honoring the session target UID), with the reverted-activity
table and the gained-float explanation.

## Scope / safety

Additive: the CPM/metric/parity definitions are untouched (the counterfactual builds a *separate*
`Schedule.model_copy` and runs the existing `compute_cpm`; the loaded versions are never
mutated) → **parity 10/10**. New engine module unit-tested (duration cut, completed exclusion,
logic removal + gained float, gained-float-only, no-target); a web test pins the panel + the
"gained float" explanation on `/evolution`. Full suite **883 passed**; engine cov 97%. Follow-on
chart items (Bow-Wave totals + target highlight; Data-Date/Slippage redesign) and the Diagnostic
Brief / DCMA-definitions items remain their own PRs.
