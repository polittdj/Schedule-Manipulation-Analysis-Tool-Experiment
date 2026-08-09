# ADR-0376 — Phase 3 slice 12: the /analysis family, and the largest prefix undercount yet

- **Status:** Accepted
- **Date:** 2026-08-09
- **Continues:** ADR-0350 (the kernel; the 3+-family components threshold applied again), ADR-0351
  (the descent rule + per-definition byte-identity), ADR-0352 (the span-scoped pre-flight probe),
  ADR-0365 (closure-before-cut), ADR-0372 (the oracle recipe + the three normalizers), ADR-0373
  (the live-chain aim), ADR-0374 (the render-condition rule), ADR-0375 (the header ruling this
  slice completes for `_where_we_stand_header`; the title-stripped TP4 pool)
- **Related:** ADR-0197 (chapter 01 "Where we stand"), ADR-0291 (the projection memo whose spies
  this slice re-adjudicated), ADR-0327 (the target panel's contract)

## Decision

**Extract the /analysis page family — verbatim — into `web/analysis.py` (1,297 lines): 25 names
in nine regions** (app.py 6894–9201, non-contiguous): `_analysis_body`, `_analysis_data`,
`_where_we_stand_header` (moved with its family exactly as ADR-0375 ruled), the six DCMA
cell/card builders (`_dcma_label`, `_dcma_measure`, `_dcma_card`, `_dcma_definition_cell`,
`_dcma_metric_cell`, `_dcma_count_cells`), `_cites_cell`, the twelve analysis-page panels
(`_stoplight_board`, `_float_bands_panel`, `_completion_panel`, `_health_checks_panel`,
`_schedule_variance_panel`, `_float_erosion_panel`, `_constraint_checks_panel`,
`_vertical_integration_panel`, `_logic_checks_panel`, `_margin_panel`, `_scatter_panel`,
`_float_histogram_panel`, `_calendar_panel`) and the two constants they read (`_WEEKDAY_NAMES`,
`_EROSION_BADGE` with its `#:` line). **One descent rides the slice — the first since sra:**
`_target_panel` (67 lines) → `web/components.py`, referenced by THREE families
(`_analysis_body` + the /card and /wbs routes), the ADR-0350 components threshold;
components' state import widens to `_Analysis, SessionState`. `app.py` **13,358 → 12,096**
(wc-truth). `LAYER_ORDER` becomes `… → forecast → portfolio → analysis → app`; the re-export
block lands before chrome's (a-n-a < c-h-r); `analysis.py` joins pyproject's per-file E501 list;
`VIEW_MODULES` and both whole-view-layer guard tuples gain `"analysis.py"` (alphabetically
first). The export route contributes NO movers (engine tables + the shared export machinery —
the mission shape, fourth consecutive slice).

## The re-measure: the prefix undercounts by 3.6× — the largest ratio yet

The queue said "analysis 356" — the two `_analysis_*` names plus the where header. The
behaviour-seeded closure over `/analysis/{name}` + `/api/analysis/{name}` +
`/export/{fmt}/analysis/{name}`: **26 names / 1,275 region lines** (1,175 ast-span + `#:` blocks
+ separators). Seventeen of the eighteen app.py-resident names `_analysis_body` references are
sole-referrer movers the prefix never saw — the page's panels carry no `_analysis` prefix. The
sra slice's ratio was 2.1× (847 → 1,756); this one is 3.6×. **Stays, each adjudicated by
referrer:** `_unschedulable_panel` (2 routes, no eponymous page — shared machinery),
`_find_schedule` (3 routes), `_FLOAT_HIST_BANDS` + its `#:` block (sole referrer the
`export_float_band` route — the histogram panel itself is JS-rendered and never reads it),
`_HB_CONSUME_SEC` + its 10-line citation comment (ZERO referrers; the deliberate stay
`components.py:335` already documents), `_BRIEFING_/_BRIEF_XLSX_TITLE` (briefing/brief),
`_stack_not_measured` (`_work_piling_header`), `_count_bar_table` (`_card_body`), `_num`
(`_wbs_body`).

## The oracle — 498 labels, the ADR-0375 shape widened

Rebuilt per the ADR-0372 recipe with the ADR-0375 title-stripped TP4 pool (the five snapshots
upload with `<Title>` stripped and pool as ONE untitled five-version population — asserted in
the harness before any render: /evolution and /compare must NOT contain the ADR-0258
placeholder). Surface: every parameterless GET (60, pages AND APIs, 4xx bodies kept) · both
fmts × all 27 parameterless `{fmt}` exports · the 7 `{name}` pages AND all 8 `{name}` exports
both fmts on TP4 v5 · the established variants (`/trend?target=22`, the three ADR-0352
/evolution shapes aimed at UID 22, the seeded `/api/sra/ssi?iterations=300`, the four
`[grouped]` labels) — 146 labels × three target states, plus an `[empty]` stage widened to ALL
60 parameterless GETs (the 494 reference carried 56; excluding nothing is strictly wider, and
no-silent-caps outranks count-matching) = **498**. The three loaded stages' 4xx histogram —
**88** (17×400 + 12×404 + 59×422) — matches ADR-0375's post-title-strip count exactly, so the
pooled population is the same shape as the prior widest reference. Three normalizers inherited;
the launch token is normalized by exact value (the harness owns the `SessionState` it serves).
Double-render determinism across two separate processes: **0 flapping — proven before any
claim.** Target UID **22** (live 22→26 chain head, 50%, finish-moving).

## Pre-flight probe — 26/26 render-proven, ZERO dark members (third consecutive slice)

Span-scoped anchor mutations in place in app.py (anchor count == 1 asserted in-file, anchor line
asserted inside the member's ast span, render-path literals — never docstrings; restores
md5- and anchor-grep-verified). Branch states read off the rendered v5 body BEFORE anchor
choice (ADR-0374's rule): margin takes its NO-candidates branch on TP4, erosion has groups,
variance is computable, 7 findings exist (so `_cites_cell` executes).

| members | labels moved (of 498) |
| --- | --- |
| the 20 page-side movers | 3 each — `/analysis/{name}` [v5] in loaded/t-set/t-clr |
| `_dcma_measure`, `_dcma_card`, `_analysis_data` | 3 each — `/api/analysis/{name}` [v5] × 3 states |
| `_dcma_label` | 6 — BOTH surfaces × 3 states (the only two-surface member) |
| `_target_panel` | 3 — /analysis, /card, /wbs [v5] in **target-set only** (its exact render condition, measured live) |

## Proof

- **Per-region byte-identity: 9/9 + descent IDENTICAL** — asserted inside the cut script BEFORE
  writing and re-verified from disk after; re-verified a third time after `ruff --fix` dropped
  app.py's 14 mover-only imports; `ruff format --check` passed with zero reformats.
- **Multiset (final tree): 100 added / 3 removed — zero code lines removed.** The 3:
  `ActivityVariance,` and `off_project_calendars,` (parenthesized members whose names re-land in
  analysis.py's single-line imports) and components' `SessionState`-only state import
  (superseded by its `_Analysis, SessionState` widening). Every other moved line cancels
  verbatim.
- **Dropped-import sweep:** zero readers of the 14 dropped names through `web.app`
  (`from web.app import X` and `app_mod.X` shapes both swept; the pattern is live — 181 test
  files import from web.app).
- **498/498 routes byte-identical**, pristine vs cut, on the double-render-verified oracle.
- **Falsified in the new locations: 26/26 EXACT** — every member re-mutated in
  analysis.py/components.py with the probe's own anchors moved exactly its pre-flight label
  LIST; anchors additionally asserted ABSENT from post-cut app.py; restores md5-verified.

## The sweeps

- **Monkeypatch + attribute-read sweep** (all 71 names analysis.py binds, defined or imported):
  **two hits, both in `test_manifest_projection_memo.py`, both adjudicated** — the standing
  `app_mod.non_summary` positive control AND `app_mod.compute_activity_makeup`, which
  analysis.py now also imports. Both spies count the `/api/dashboard` projection path, which
  runs through app.py's OWN binding (line 11485 post-cut) and renders no /analysis page;
  analysis.py's import is outside the patch's reach by design — the ADR-0297 trap shape,
  verified not tripped (the module runs green post-cut).
- **Source-text sweep:** the ≥6-char literals of all 33 source-reading test files intersected
  against the moved text; every hit adjudicated — rendered-page assertions
  (`test_forecast_views` asserts `client.get(...).text`, unchanged by 498/498), static-JS
  readers, `test_gantt_find_coverage` reads **driving.py** via `__file__`, chrome.py readers
  repointed in phase 2. `panelkit.js` ∈ `test_axis_titles` ∩ `_analysis_body` is the designated
  positive control; `_TS_CAPTION_MARK` / `data-ts-caption` / the drilldown script tag verified
  ABSENT from the moved text. **Zero reader repoints — third consecutive slice.**

## Verification

Six mutations, each an exact-match splice landed-count-asserted in-script, each run against the
WHOLE module (no `-k`), each exactly ONE named failure with the twins green (the ran-signature
rule), each restored from a scratchpad copy (never `git checkout`), md5 + anchor-grep verified,
each module re-run green after restore:

| mutation | named failure | split |
| --- | --- | ---: |
| re-export deleted from `app.py` | `…reexported_by_app…[analysis.py]` | 1 / 31 |
| deferred upward import in `_analysis_data` (in-body) | `…imports_downward[analysis.py]` | 1 / 31 |
| `"analysis.py"` dropped from `test_bar_drill` | `…read_the_whole_view_layer[test_bar_drill.py]` | 1 / 31 |
| `"analysis.py"` dropped from `test_presentation_fixes` | `…[test_presentation_fixes.py]` | 1 / 31 |
| `"&mdash;"` sentinel planted in `analysis.py` (in-body) | `test_no_mdash_entity_sentinel_values…` | 1 / 5 |
| second `drilldown.js` include in `analysis.py` (in-body) | `test_drilldown_runtime_is_loaded_globally…` | 1 / 6 |

Mutations 3–4 are the enumeration guard's **fifteenth and sixteenth consecutive live catches**.
Mutations 2 and 5 used the in-body form from the start (ADR-0373's defensive-overlap finding
applied, not re-derived).

**One measurement was discarded as self-polluted.** The first multiset diff ran WHILE the
falsification battery held a member mutated, and the diff itself carried the battery's `PRB12X`
marker line — the standing "never mutate a running suite's tree" trap in its reverse form:
*never MEASURE a tree a battery is mutating.* The multiset was re-run on the quiescent tree
(tree first re-verified against the post-cut snapshots by md5) and only that clean 100/3 figure
is reported anywhere.

## Deliberately NOT done

- **`_HB_CONSUME_SEC` stays in app.py with zero referrers.** It is outside the closure (no mover
  references it), and `components.py:335` already documents the deliberate stay from the
  ADR-0350 descent round. Deleting or moving an unreferenced citation constant is cleanup, and
  cleanup does not ride a verbatim slice.
- The slice-7 crafted v4/v2 SSI setup-load sequences were not rebuilt into this oracle
  (ADR-0372/0374/0375 precedent, same reasoning): this cut does not touch `_apply_ssi_setup`'s
  machinery.
- `groups` (315 by prefix) stays outside the phase-3 candidate list while ADR-0343 feature work
  is queued against it.
- `CLAUDE.md`'s phase-3 + E501 prose still lag by design (the standing doc-drift sweep owns
  them — analysis.py now also joins the unpatched E501 list there); `analysis.py` DID join
  pyproject's per-file E501 list.

## Consequences

- The remaining slice queue, by the post-cut prefix census (each family still owes its OWN
  closure before cutting, and this slice re-prices the expectation: a page family's closure can
  run **3.6×** its prefix): **evm 299** · **performance 279** · resources 255 · scurve 212 ·
  path 194 · compare 166.
- The **498-label oracle** (untitled-pool population, the widened all-60 `[empty]` stage, the
  full-surface target sequences, the [grouped] labels) is the widest reference yet; the
  title-strip remains load-bearing, and the 88-count 4xx histogram is its population
  fingerprint — a future oracle whose loaded-stage 4xx count differs has formed a DIFFERENT
  population and must be adjudicated before use.
- `_target_panel` now lives in components.py: when /card and /wbs are cut (they are single-name
  bodies inside other families' censuses today), their closures will find the panel already
  below them — the sra-stays shape repeating.
- The monkeypatch sweep's adjudication list can GROW as families move: `compute_activity_makeup`
  joined `non_summary` this slice because analysis.py now binds a name the projection-memo spies
  also patch. The adjudication holds while the spied path stays inside app.py; a future slice
  that moves the DASHBOARD family must repoint those spies to the module whose code calls them.
