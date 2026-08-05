# ADR-0350 — Monolith split, phase 3: the shared kernel comes out first

- **Status:** Accepted
- **Date:** 2026-08-05
- **Opens:** ADR-0297's **phase 3** (the presentation helpers), by extracting the layer that
  every page slice would otherwise have fought over
- **Related:** ADR-0297 (phase 1, `state.py` — the method), ADR-0349 (phase 2, `chrome.py` — the
  proof technique), ADR-0298 (the panel contract this kernel implements), ADR-0195 (never
  big-bang)

## Context

Phase 3 was queued as "slice by page family, one per PR, largest first" — `driving` (585 lines),
then `evolution` (429), `integrity` (402), and so on. That plan was written from a line census,
not from a dependency measurement. Measuring it first is what ADR-0349 established as the
method, and here the measurement contradicted the plan.

`app.py` stood at **20,192 lines** after ADR-0349. **92 functions / 8,913 lines** match the
strict `_*_body|_panel|_data|_header|_html` presentation-helper pattern, spread across 59 page
families.

## What the measurement said

An AST transitive closure of each family's entry points over `app.py`'s **309** defined
top-level symbols gives, for `driving`, **15 names / 870 lines**. But only seven of those are
`driving`'s own. The rest are shared primitives, and two of them are load-bearing for the whole
UI:

| symbol | reached by | direct referrers |
| --- | ---: | ---: |
| `_panel_head` | 47 families | 62 |
| `_shell_tools` | 41 families | 52 |
| `_prov_chip` | 21 families | 15 |
| `_stat_cards` | 16 families | 22 |

**Cutting `driving` first would have moved `_panel_head` into a page module**, leaving 60-odd
unrelated helpers still in `app.py` importing their panel header from `web/driving.py`. Every
later slice would have inherited that inversion, or duplicated the primitive. The queued order
was not merely suboptimal; it was the one order that poisons the remaining thirteen slices.

So phase 3 opens with the shared layer instead.

## Decision

**Extract the shared presentation kernel — verbatim — into `web/components.py` (308 lines):**
the panel-contract strip (`_panel_head`, `_shell_tools`, `_prov_chip`, `_pair_prov_chip`,
`_series_prov_chip`), the KPI `_stat_cards`, `_metric_help_cell`, `_status_stack`,
`_export_bar`, the shared formatters (`_mdY`, `_user_tip`, `_status_class`), the analysis-export
pair (`_ANALYSIS_XLSX_TITLE`, `_analysis_export_attr`) and the two SRA resolvers
(`_latest_solvable`, `_sra_selected`). `app.py` drops to **19,944 lines** (−248) and re-exports
all 16 names with the explicit `X as X` idiom.

**Membership is the closure's verdict, not a judgement call.** A symbol is in iff **three or
more** page families reach it — then no single page can own it. That set is **16 names / 233
lines of moved code, and it is CLOSED**: it calls nothing that stays behind.

**Why the threshold is 3 and not 2.** Both are closed, but they are different things. The
2-family band (25 more names, 503 lines) is not a primitives layer at all — it is **page-pair
machinery**. `_conditional_section`, `_unified_risk_section`, `_branch_section`, `_OCC_EXACT`,
`_OCC_RANDOM`, `_CONSEQUENCE_HINT` are all reached by "sra, ssi" and every one of them has
`_ssi_panel` as its only direct referrer; `_render_counterfactual` (179 lines) is reached by
"counterfactual, evolution" and referred to by `_counterfactual_panel` alone. Those belong with
their pages, and the right home is obvious once the pair moves — guessing it now would be the
adjacency error in a new costume. A shared-components module holding a 179-line counterfactual
renderer is not a components module.

**Layering.** `app` → `components` → `chrome` → `state` → engine/model, acyclic, now pinned by a
test. `components` imports `_e` from `chrome` because ADR-0349 put it there. That direction reads
slightly odd — a primitive importing from the page shell — and is deliberate anyway: moving `_e` a
second time would repoint phase 2's source-text guards for no behavioural gain. `_e` is a
candidate to descend into `components` in a later phase, when something else forces the file open.

**`components.py` takes the E501 exemption.** Exactly **one** line needs it: a `_metric_help_cell`
docstring line that was already over-long inside `app.py`'s exempt region. Re-wrapping it to earn
a clean E501 would break the byte-for-byte property the entire extraction rests on. Verbatim
outranks a rule that exists for code, and the exemption travels with the code as it did for
`chrome.py`.

**Deliberately left in `app.py`:** `_SRA_XLSX_TITLE` and `_BRIEFING_XLSX_TITLE` — the two sibling
⤓ EXCEL hover strings that sit immediately beside `_ANALYSIS_XLSX_TITLE` and read as a coherent
group of three. They are reached by two families and one family respectively, so they stay. This
is ADR-0349's `_TS_CAPTION_MARK` ruling applied again: **adjacency is not cohesion**, and it cuts
against tidiness here rather than for it.

## The trap, and it is phase 2's — one module wider

ADR-0349 warned that tests reading a module's **source text by path** do not fail when their
subject moves; they quietly search a file that no longer contains it. That trap fired again, in
its second form: not "the subject moved out of the file the guard reads" but **"the view layer
grew a module the guard does not read."**

`test_presentation_fixes`'s em-dash sentinel guard asserts `'"&mdash;"' not in src` across
`app.py` + `chrome.py`. `_stat_cards` — the function the very next test in that file exercises
for this exact double-escape bug — moved to `components.py`. The guard would have stayed green
over a subject that had shrunk. `test_bar_drill`'s "exactly ONE `drilldown.js` include anywhere in
the view layer" count has the same shape. Both now read **all three** view modules.

A guard whose claim is *"nowhere in the view layer"* has to enumerate the view layer, and the view
layer is exactly what a monolith split changes. So the enumeration is no longer left to whoever
does the next cut: `test_monolith_split_contract` now pins the module list and fails when a view
module is added without widening those guards.

## Proof

- **Verbatim, mechanically proved.** Non-blank-line multiset of the original `app.py` against
  `app.py + components.py`, setting aside the generated re-export block and the new module's
  preamble: **19,100 → 19,100**. The 52 added lines are *entirely* the re-export block (25) and
  the preamble (27); the single removed line is `field_or_metric_doc`, which `ruff --fix` dropped
  from `app.py` because its sole consumer moved.
- **Every served page is byte-identical: 60/60.** All 60 routes rendered with the example
  schedule — including the parametrized `/analysis/{name}`, `/card/{name}` and `/wbs/{name}`,
  which is where this kernel is used most, and which a page-list oracle would have missed.
- **The oracle was not deterministic, and that was found before it was trusted.** Two runs of the
  *unchanged* tree disagreed on **34 of 61** routes. Cause: a per-process launch token
  (`<meta name=sf-launch>` / `/api/whoami`) plus the pid — stable within one interpreter, which is
  precisely why ADR-0349's "in the SAME interpreter" phrasing mattered. Normalizing those two
  values leaves one route varying by construction (`/api/system`, live uptime/rss), which is
  excluded by name. Only then does 60/60 mean anything.
- **The oracle was falsified.** One character changed in `_panel_head` moves **20 of 60** hashes.
  The 40 that hold are the `/api/*` JSON endpoints plus twelve pages verified to contain zero
  `class=panel-head` in their rendered HTML — checked directly, not assumed, with `/margin`
  (4 occurrences, moved) as the positive control.

## The new guards, and that they can fail

`tests/web/test_monolith_split_contract.py` is extended rather than duplicated: the re-export and
acyclicity tests are now parametrized over the extracted modules, the layering test replaces
"chrome never imports app" with the full `app → components → chrome → state` order, and the
view-layer-enumeration test is new. Five mutations, each verified to have landed by re-reading the
file and each restored from a scratchpad copy (never `git checkout`):

1. Re-export of `_panel_head` deleted from `app.py` → fails, naming `_panel_head`.
2. A **deferred** `from schedule_forensics.web import app` inside a `components.py` function →
   fails the layering test. The deferred form is the one worth guarding: the module-level spelling
   detonates on its own with a circular import, while this one imports cleanly and runs fine.
3. `"components.py"` dropped from `test_bar_drill`'s module tuple → the enumeration test fails.
4. A `"&mdash;"` sentinel planted in `components.py` → the repointed em-dash guard fails, which is
   what proves the repointing actually widened its reach.
5. A second `drilldown.js` include planted in `components.py` → the repointed double-load guard
   fails, likewise.

## Consequences

- The remaining phase-3 slices are now unblocked and genuinely per-page: with the kernel out,
  `driving`'s closure is its own five entry points plus `_task_iso_dates` and `_corridor_chips`.
- Two 2-family names (`_task_name_across`, `_EVO_TIER_LABEL`) still straddle page pairs. They stay
  in `app.py` until both owners have moved; the last slice of a pair collects them.
- The view-module list is now a tested constant. Phase 4 must add its module to `LAYER_ORDER` and
  `VIEW_MODULES`, and the contract test says so by failing.
