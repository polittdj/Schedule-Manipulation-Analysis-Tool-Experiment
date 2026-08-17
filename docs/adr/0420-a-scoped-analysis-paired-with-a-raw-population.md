# ADR-0420 — the three MIXED-POPULATION rows were one class: a scoped analysis paired with a raw population

**Status:** Accepted · **Date:** 2026-08-17 · **Closes:** `ANALYSIS-HEADER-MIXED-POPULATION`,
`RIBBON-MIXED-POPULATION`, `ANALYSIS-EXPORT-QUALITY-UNSCOPED` (audit 2026-08-16) ·
**Extends:** ADR-0263, ADR-0417 · **Ships:** `web/app.py`

## Context

`SessionState.analysis_for(key, sch)` computes over `st.scope(sch)` and hands the exact population
back as `_Analysis.scoped`. ADR-0263 added that field precisely so a caller pairs the analysis with
the population it was computed **from**, instead of re-resolving the scope in a second lock window.
`ordered_versions()`'s own docstring says its schedules are **UNSCOPED** and that callers "hand the
schedule to `analysis_for` (which scopes it)".

Several routes did both: they handed `sch` to `analysis_for` **and then also passed that same raw
`sch` straight to engine functions alongside the scoped `analysis.cpm`. A CPM solved on one task
set grading a different task set is incoherent — tasks the solver never saw get scored by it, and
the page states two population sizes at once.

## The measurement — differential, with a load-bearing control

The oracle is the one ADR-0417 proved: change the scope, then diff two surfaces against each
other. A genuinely scoped figure **moves**; a raw one does not. On the shipped example
(9 activities, 1 milestone) with an `Activity Type: Normal` reduce filter (9 → 8):

| surface | unfiltered | filtered | |
| --- | --- | --- | --- |
| `analysis.scoped` size — **the control** | 9 | 8 | MOVED (the filter really bit) |
| `/analysis` header `stack-foot` | 9 activities | **9 activities** | STATIC — raw |
| `/analysis` grid takeaway | 9 in the grid | 8 in the grid | MOVED — scoped |
| `/api/analysis` `tasks` vs its own `activities[]` | 9 = 9 | **9 vs 8** | disagree in ONE payload |
| `/ribbon` "Missing logic" / "Logic wired" | 2 / 7 | **2 / 7** | STATIC — the filter is ignored outright |
| honest scoped quality | 2 of 9 | **5 of 8** | what the ribbon and the workbook should say |

So one filtered `/analysis` page rendered `<div class="stack-foot">9 activities</div>` **and**
`8 activities in the grid`, while the chrome told the operator a filter was active. The exported
workbook's Schedule-quality sheet shipped `2 / 9` where the page's own population gives `5 / 8` —
the MF-02 / ADR-0417 family again: an export disagreeing with the screen, in an artefact that
leaves the tool and gets quoted.

## It is a CLASS, not three rows

A computed AST census over the whole view layer (attributing each hit to the **innermost**
enclosing function — `create_app` lexically contains every route, so walking it whole unions
unrelated bindings and manufactures false positives) found the same shape in **five more route
functions** the ledger never named:

`schedule_card` (×2) · `standards_view` · `_schedule_facts` (×2 — the fact sheet the **AI is
allowed to cite**) · `export_ribbon` · `export_ribbon_drill`.

Leaving `export_ribbon` alone while fixing `/ribbon` would have re-created the very screen-vs-export
split being closed. All of them are fixed.

## Decision

Pass `analysis.scoped` wherever the analysis is paired with a population. This is safe and
narrowly scoped:

* `filter_to_uids` is a `model_copy` touching only `tasks`/`relationships`, so **file identity is
  preserved** (name, `source_file`, calendar, project frame) — provenance chips and titles are
  unaffected.
* `st.scope()` returns the schedule **unchanged** when nothing narrows, so every change is a
  literal no-op in the unfiltered case. That is what the unfiltered controls in the new tests pin.

**A hand-maintained call-site list is a stale list waiting to happen**, so the contract is enforced
by a standing **computed census** (`test_no_view_pairs_a_scoped_analysis_with_a_raw_population`)
that re-derives the sites and asserts the set is empty — the same shape as ADR-0415's standing
sweep, and the reason a new route cannot quietly reintroduce the defect.

## Verification

* **Red first.** Four differential tests in `tests/web/test_scoped_population_contract.py`, all
  observed failing before the fix, plus a `test_the_filter_actually_narrows_this_fixture`
  guard-the-guard so none of them can go vacuous.
* **One test was caught being unable to fail.** The export test's first draft asserted on a
  re-derivation of what the route *should* compute, and passed against the broken route. It now
  parses the **shipped workbook bytes**. Its first red was also the wrong red — a `StopIteration`
  from a mis-cased label ("Missing logic" vs the workbook's "Missing Logic"); mutant M4 confirms it
  now fails on the assertion.
* **Mutation battery 5/5 killed by name** (each fix site reverted individually; every mutant
  confirmed `landed: True` first), and the census guard separately proven to fire against the real
  tree by reintroducing a violation in `export_ribbon` and in `_schedule_facts` — **2/2 killed by
  name**. The guard also carries a synthetic positive control, because "reports zero" is what a
  blind census reports too (the ADR-0418 lesson).
* Batteries ran in a detached worktree, never in the tree under measurement.
