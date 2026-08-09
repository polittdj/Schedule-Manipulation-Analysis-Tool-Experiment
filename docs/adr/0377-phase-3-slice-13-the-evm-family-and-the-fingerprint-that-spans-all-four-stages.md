# ADR-0377 — Phase 3 slice 13: the /evm family, and the fingerprint that spans all four stages

- **Status:** Accepted
- **Date:** 2026-08-09
- **Continues:** ADR-0350 (the kernel), ADR-0351 (the descent rule — applied to a mover+stayer
  pair again), ADR-0352 (the span-scoped pre-flight probe), ADR-0365 (closure-before-cut; the
  mover+stayer descent precedent), ADR-0372 (the oracle recipe + the three normalizers),
  ADR-0374 (the render-condition rule; `_field_forecast_panel` already below), ADR-0375 (the
  title-stripped TP4 pool; the header ruling this slice completes for
  `_how_we_execute_evm_header`), ADR-0376 (the 88-count population fingerprint this slice
  re-scoped)
- **Related:** ADR-0161 (the 95% threshold family `_threshold_legend` documents), ADR-0179
  (the field-forecast treatment the /evm route shares), ADR-0291 (the projection-memo spies)

## Decision

**Extract the /evm page family — verbatim — into `web/evm.py` (378 lines): six names in one
contiguous block** (app.py 9816–10149): `_threshold_legend`, `_evm_idx_str`, `_evm_days_str`,
`_evm_explainer`, `_how_we_execute_evm_header` (moved with its family exactly as ADR-0375
ruled), `_evm_body`. **One descent rides the slice:** `_metric_scorecard_table` (19 lines,
app.py 9795–9813) → `web/components.py`, needed by a MOVER (`_evm_body`, 3 call sites) AND by
a STAYER (`_groups_body:10851` — the /groups family, outside phase 3 while ADR-0343 is queued)
— the ADR-0351/0365 mover+stayer shape, sixth application; components' import surface gains
`MetricResult`. `app.py` **12,082 → 11,735** (wc-truth; the handoff's carried 12,096 was
superseded by the measured tree — wc decides). `LAYER_ORDER` becomes
`… → portfolio → analysis → evm → app`; the re-export block lands between driving's and
evolution's (d-r-i < e-v-m < e-v-o); `evm.py` joins pyproject's per-file E501 list (ten
explainer/tip lines at 101–107 chars, over-long inside app.py's exempt region — verbatim
outranks re-wrapping); `EXTRACTED`, `LAYER_ORDER`, `VIEW_MODULES` and both whole-view-layer
guard tuples gain `"evm.py"`. The export route contributes NO movers (engine tables + the
shared export machinery — the mission shape, **fifth** consecutive slice).

## The re-measure: nearly census-exact, and both unprefixed members were predicted

The queue said "evm 299" (the five `_evm`/header names — exactly the five seeds' ast total).
The behaviour-seeded closure over `/evm` + `/export/{fmt}/evm`: **seven names / 343 ast-span
lines** (1.15× — the mildest undercount since mission). The two names the prefix never saw:
`_threshold_legend` (25 lines; sole referrer `_evm_body` — a mover) and
`_metric_scorecard_table` (19 lines; the descent). Stays, each adjudicated by referrer:
every engine import the routes share (`compute_evm_indices` — export_evm + `_standards_body` +
`_performance_data`; `compute_schedule_variance` — export_evm; `non_summary`, `compute_bei`,
`MetricResult`, `CheckStatus` — multi-family); `_status_class` (components-resident already;
`_standards_rows` and the scorecards family keep reading it through app.py's re-export). The
only import app.py DROPS is `compute_baseline_compliance` (zero uses outside the moved
region), re-landing in evm.py's single-line import.

## The oracle — 498 labels, and the fingerprint's stage-scope pinned

Rebuilt per the ADR-0372 recipe with the ADR-0375 title-stripped TP4 pool (five snapshots,
`<Title>` stripped, pooling as ONE untitled five-version population — asserted in the harness
before any render: /evolution and /compare must not contain the placeholder). Surface
unchanged from ADR-0376: every parameterless GET (60 — 59 `APIRoute`s **plus `/openapi.json`**,
a plain starlette `Route` the isinstance-filtered enumeration misses; "pages AND APIs, no
silent caps" includes it) · both fmts × all 27 parameterless `{fmt}` exports · the 7 `{name}`
pages AND all 8 `{name}` exports both fmts on TP4 v5 · the established variants
(`/trend?target=22`, the three ADR-0352 /evolution shapes aimed at UID 22, the seeded
`/api/sra/ssi?iterations=300`, the four `[grouped]` labels) — 146 × three target states + the
all-60 `[empty]` stage = **498**. Target UID **22** (live 22→26 chain head), POSTs
303-asserted. Three normalizers inherited. Double-render determinism across two separate
processes: **0 flapping** (one flap was caught and adjudicated by payload during harness
bring-up: four `/api/whoami` labels moved because the token placeholder was non-UTF-8 and the
pid normalizer's JSON parse silently failed — the payload diff showed `pid` as the only mover,
the normalizer was fixed, and the re-run proved 0).

**The fingerprint finding this slice pins: the 88-count 4xx histogram spans ALL FOUR stages,
not "the three loaded stages" as ADR-0375/0376's prose said.** The first fingerprint check
here compared the three loaded stages and read **69** (12×404 + 57×422) — a mismatch that
tripped the adjudicate-before-use rule exactly as designed. The payload-level adjudication:
all seventeen 400s are the `[empty]`-stage no-schedule guards (`/api/cei`, `/api/trend`, the
two template exports, …), and the three loaded stages carry 12×404 + 57×422 = 69 — which is
ADR-0374's own three-state histogram verbatim. Per-stage shape: `[empty]` {200:41, 400:17,
422:2}; each loaded stage {200:123, 404:4, 422:19}. The pooled population is IDENTICAL; the
prose scope was wrong, not the population. A future oracle must compare the all-stages
histogram to 88 (or the loaded-stages histogram to 69) — comparing the loaded stages to 88
false-alarms every time.

## Pre-flight probe — 7/7 render-proven, ZERO dark members (fourth consecutive slice)

Branch states read off the rendered v5 body BEFORE anchor choice (ADR-0374's rule): the
header renders its BEI-FAIL clause (BEI 0.58 below the 0.95 bar), SPI(t) 0.62 and SVt −40
all render, the body takes its NOT-cost-loaded branch, `sv.worst` is non-empty (the variance
table renders), the CEI clause renders. Span-scoped anchor mutations in place in app.py
(anchor count == 1 asserted in-file, anchor line asserted inside the member's ast span,
render-path literals — never docstrings; two anchors were widened to multi-line exact spans
when the short form collided: `_evm_idx_str`'s return and the scorecard table's header row);
restores md5- and anchor-grep-verified.

| members | labels moved (of 498) |
| --- | --- |
| the six movers | 6 each — /evm bare AND `[grouped]` × 3 loaded stages |
| `_metric_scorecard_table` | **9** — the six /evm labels PLUS `/groups` × 3 states |

The descent's probe is the first whose second family was **measured live in the same probe**:
`/groups` moved for `_metric_scorecard_table` and for nothing else — the `_groups_body`
referrer is render-proven, not just closure-proven, so the mover+stayer adjudication rests on
behaviour.

## Proof

- **Per-region byte-identity: 1/1 + descent IDENTICAL** — asserted inside the cut script
  BEFORE writing, re-verified from disk after, and re-verified a third time after
  `ruff --fix` dropped app.py's single mover-only import; `ruff format --check` passed with
  zero reformats.
- **Multiset (final tree): 48 added / 1 removed — zero code lines removed.** The 1:
  `compute_baseline_compliance,` (parenthesized member re-landing in evm.py's single-line
  import — the ADR-0375 import-shape artifact). Additions: evm.py's preamble + import block,
  app.py's 10-line re-export insert, the `_metric_scorecard_table` re-export line, components'
  `MetricResult` import. Every moved line cancels verbatim. Measured on the quiescent tree,
  md5-verified against the post-cut snapshots first (ADR-0376's reverse-trap applied, not
  re-paid).
- **Dropped-import sweep:** zero readers of `compute_baseline_compliance` through `web.app`
  (control live: 181 test files import from web.app).
- **498/498 routes byte-identical**, pristine vs cut, on the double-render-verified oracle;
  the fingerprint held on the cut tree.
- **Falsified in the new locations: 7/7 EXACT label lists** — every member re-mutated in
  evm.py/components.py with the probe's own anchors moved exactly its pre-flight list;
  anchors additionally asserted ABSENT from post-cut app.py; restores md5-verified.

## The sweeps

- **Monkeypatch + attribute-read sweep** (all 25 names evm.py binds, defined or imported):
  **one hit — the standing `app_mod.non_summary` projection-memo patch**, which doubles as
  the sweep's live positive control. Adjudication unchanged from ADR-0365/0376 and re-verified
  by running the module green post-cut: the spied path is `/api/dashboard` through app.py's
  OWN binding, no /evm render occurs in the test, and evm.py's import (evm.py now also binds
  `non_summary`) is outside the patch's reach by design. `compute_activity_makeup` is NOT
  bound by evm.py, so slice 12's second adjudication does not grow here.
- **Source-text sweep** (every ≥6-char literal of all 5 app.py-source-reader test files ∩ the
  moved text): every hit adjudicated — `panelkit.js` ∈ `test_axis_titles` ∩ `_evm_body` is
  the designated positive control; `test_presentation_fixes`' `"BEI (throughput)"` is a
  `_stat_cards` CALL ARGUMENT (a components unit test asserting rendered output, not an
  app.py source assertion); `latest`/`static`/`&mdash;` and the rest are generic words or the
  whole-view-layer aggregate that now reads evm.py via the widened tuple.
  `_TS_CAPTION_MARK` / `data-ts-caption` / the drilldown script tag verified ABSENT from the
  moved text. **Zero reader repoints — fourth consecutive slice.**

## Verification

Six mutations, each an exact-match splice landed-count-asserted in-script, each run against
the WHOLE module (no `-k`), each exactly ONE named failure with the twins green (the
ran-signature rule), each restored from a scratchpad copy (never `git checkout`), md5 +
anchor-grep verified, each module re-run green after restore:

| mutation | named failure | split |
| --- | --- | ---: |
| re-export deleted from `app.py` | `…reexported_by_app…[evm.py]` | 1 / 33 |
| deferred upward import in `_evm_body` (in-body) | `…imports_downward[evm.py]` | 1 / 33 |
| `"evm.py"` dropped from `test_bar_drill` | `…read_the_whole_view_layer[test_bar_drill.py]` | 1 / 33 |
| `"evm.py"` dropped from `test_presentation_fixes` | `…[test_presentation_fixes.py]` | 1 / 33 |
| `"&mdash;"` sentinel planted in `evm.py` (in-body) | `test_no_mdash_entity_sentinel_values…` | 1 / 5 |
| second `drilldown.js` include in `evm.py` (in-body) | `test_drilldown_runtime_is_loaded_globally…` | 1 / 6 |

Mutations 3–4 are the enumeration guard's **seventeenth and eighteenth consecutive live
catches**. Mutations 2 and 5–6 used the in-body form from the start (ADR-0373's
defensive-overlap finding applied, not re-derived).

## Deliberately NOT done

- **The slice-7 crafted v4/v2 SSI setup-load sequences were not rebuilt into this oracle**
  (ADR-0372/0374/0375/0376 precedent, same reasoning): this cut does not touch
  `_apply_ssi_setup`'s machinery.
- `groups` (430 by prefix post-cut, `_saved_*` included) stays outside the phase-3 candidate
  list while ADR-0343 feature work is queued against it — even though this slice's descent
  serves it: `_groups_body` now reads `_metric_scorecard_table` through app.py's components
  re-export, and the eventual groups closure will find the table already below it.
- `CLAUDE.md`'s phase-3 + E501 prose still lag by design (the standing doc-drift sweep owns
  them — evm.py now also joins the unpatched E501 list there); `evm.py` DID join pyproject's
  per-file E501 list.

## Consequences

- The remaining slice queue, by the post-cut prefix census (wc-truth; each family still owes
  its OWN closure before cutting; membership named because the prefix sweep is a finder, not
  the definition): **performance 326** (`_performance_body` 121 + `_performance_data` 75 +
  `_perf_version_block` 47 + `_how_we_execute_header` 83) · **resources 306**
  (`_resources_body` 157 + `_resources_explainer` 20 + `_resource_loading_json` 51 +
  `_who_is_overloaded_header` 78) · scurve 212 · path 194 (incl. `_what_drives_header` 80) ·
  compare 166 (incl. `_what_changed_header` 79).
- **The oracle recipe's fingerprint is re-scoped**: 88 over ALL FOUR stages (69 over the
  three loaded stages). Future slices must compare like with like; a loaded-stages histogram
  of 69 is the SAME population.
- The 60-count parameterless-GET class includes `/openapi.json` (a plain starlette `Route`);
  an isinstance-filtered enumeration reads 59 and undercounts the class — enumerate
  `app.routes` by method + path, not by route class.
- `_metric_scorecard_table` now lives in components.py: when /groups is eventually cut, its
  closure finds the table already below it — the sra-stays shape repeating, now for a
  descent whose second family was probe-proven live.
