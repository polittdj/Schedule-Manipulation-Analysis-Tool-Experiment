# ADR-0374 — Phase 3 slice 10: the /forecast page family, and the first slice with no dark member

- **Status:** Accepted
- **Date:** 2026-08-09
- **Continues:** ADR-0350 (the kernel), ADR-0351 (the descent rule + per-definition byte-identity),
  ADR-0352 (the span-scoped pre-flight probe), ADR-0365 (closure-before-cut), ADR-0372 (the oracle
  recipe + the three normalizers), ADR-0373 (the live-chain aim, applied here at design time)
- **Related:** ADR-0179/0188/0189 (the field-group panel + rollup this family owns), ADR-0207
  (chapter 09 "Where it lands"), ADR-0310 (the lane-colour map and its drift.js twin)

## Decision

**Extract the /forecast page family — verbatim — into `web/forecast.py` (830 lines): 9 names in
one contiguous block** (app.py 7534–8311): `_where_it_lands_header` (the chapter-09 header),
`_carnac_cards`, `_FORECAST_METHOD_COLORS` (with its `#:` doc-comment block, extended by eye),
`_forecast_ruler`, `_forecast_explainer`, `_field_forecast_panel`, `_group_rollup_panel`,
`_forecast_body`, `_forecast_data`. **No descents, no stays beyond the routes** — the smallest
closure shape since mission. `app.py` **14,583 → 13,814** (wc-truth). `LAYER_ORDER` becomes
`… → mission → sra → forecast → app`; the re-export block lands between evolution and help
(e-v-o < f-o-r < h-e-l); the E501 exemption travels (8 lines need it).

**The 2-family ruling this slice adds:** `_field_forecast_panel` is served by TWO page routes —
`forecast_view` and `evm_view` (operator 2026-07-10: the ADR-0179 treatment applies to the EVM
metrics too). It MOVES with its eponymous family rather than descending or staying: ADR-0373
CF#4 (a create_app-route referrer is never a blocker — routes import downward), ADR-0351 (no
MOVER references it, so the layering forces nothing), ADR-0350 (2 families is below the
components threshold of 3+, and 2-family names belong with their pages). The evm route reaches
it through `web.app`'s re-export exactly as before; when /evm is cut, the panel is already below
it.

## The re-measure: the prefix undercounts by half, again

The queue said "forecast 391" — the four `_forecast_*` names. The behaviour-seeded closure over
`/forecast` + `/api/forecast` + the two export routes: **9 names / 778 lines** (757 ast-span
lines + the `#:` block + separators) — `_carnac_cards`, `_FORECAST_METHOD_COLORS`,
`_field_forecast_panel`, `_group_rollup_panel` and `_where_it_lands_header` carry no `_forecast`
prefix. The last is the sharpest case: the prefix census filed its 77 lines under the **where**
family ("where 235"), but its sole referrer is `forecast_view` — it is chapter 09's header and
moves here. The where family re-prices to **158** (one name, `_where_we_stand_header`). The
export routes contribute NO movers (engine tables + the shared export machinery, all
multi-family stays), exactly the mission shape.

## The oracle — 420 labels, and the grouped variant that earned its place

Rebuilt per the ADR-0372 recipe, grown 294 → **420 labels**: every parameterless GET (60, pages
AND APIs, validation-4xx bodies kept — 12×404 + 57×422 across the three surface states, all
structural rejections) · both fmts × all 27 `{fmt}` exports · the 7 `{name}` pages AND all 8
`{name}` exports in both fmts on TP4 v5 · the established variants (`/trend?target=22`, the
three `/evolution` variants, the seeded `/api/sra/ssi?iterations=300`) · `[target-set]` /
`[target-cleared]` re-rendering the FULL GET+export surface, POSTs 303-asserted. **Anchors sit
on the live critical chain by design** — target UID **22** (incomplete, 50%, finish-moving),
the ADR-0373 lesson applied at design time rather than paid for again. **NEW this slice, and
load-bearing: four `[grouped]` labels** (`/forecast?group_field=Resource`,
`/evm?group_field=Resource`, both fmts of `/export/{fmt}/field-forecast?field=Resource`) —
`_group_rollup_panel` renders ONLY when a group field is chosen (`forecast_view` line: `… if
group_field else ""`), and the field panel's deep table likewise, so without these labels two
members would have been oracle-dark by construction. Three normalizers inherited (launch token
`{hex16}.{wipe_gen}` · whoami pid · `/api/system` values, shape kept). Double-render
determinism across two separate processes: **0 flapping**, proven before any claim.

## Pre-flight probe — 9/9 render-proven, ZERO dark members

The first multi-member slice with no oracle-dark member. Span-scoped anchor mutations in place
in app.py, landed-count asserted, restores md5-verified:

| member | labels moved (of 420) |
| --- | --- |
| `_field_forecast_panel` | 8 — /forecast AND /evm in all three session states + both grouped variants (the 2-family reach, measured live) |
| `_carnac_cards`, `_FORECAST_METHOD_COLORS`, `_forecast_ruler`, `_forecast_explainer`, `_where_it_lands_header`, `_forecast_body` | 4 each — /forecast in all four render states |
| `_forecast_data` | 3 — /api/forecast in all three states |
| `_group_rollup_panel` | 1 — the grouped variant (its only render condition) |

The forecast exports moved for NO member — the export routes never call the page family (the
mission shape again). No 0-move member, so the second-stronger-anchor rule never fired.

## Proof

- **Per-region byte-identity: 9/9 IDENTICAL** — asserted inside the cut script BEFORE writing
  and re-verified from disk after; `ruff format --check` then passed with zero reformats
  (verbatim survived the formatter untouched).
- **Multiset (final tree): 54 added / 0 removed.** Additions: `forecast.py`'s preamble + import
  block and app.py's 13-line re-export block (4 comment + 9 imports). The three imports
  `ruff --fix` dropped from app.py (`CarnacSummary`, `ForecastSet`, `compute_group_rollup` —
  each mover-only) net out against forecast.py's byte-identical member lines;
  `compute_carnac_summary,` appears +1 because BOTH files now import it (a route and a mover
  each use it). **Zero code lines removed.**
- **Dropped-import sweep:** zero readers of the three dropped names through `web.app` — every
  consumer imports `engine.forecast` directly (tests/engine/test_forecast.py, ai/qa.py,
  reports/tables.py); the `from schedule_forensics.web.app import` pattern is live elsewhere,
  so the zero is measured, not vacuous.
- **420/420 routes byte-identical**, pristine vs cut, on the double-render-verified oracle.
- **Falsified in the new location: 9/9 EXACT** — every member re-mutated in `forecast.py` with
  the probe's own anchors moved exactly its pre-flight label LIST (not merely the count),
  restores md5-verified.

## The sweeps

- **Monkeypatch + attribute-read sweep** (all 29 names `forecast.py` binds, defined or
  imported): **zero hits** in both shapes — setattr-patching and `app_mod.<name>` attribute
  reads — with the standing `app_mod.non_summary` projection-memo patch found by both (1
  setattr + 1 read = the "2×" prior slices recorded).
- **Source-text sweep**: every ≥6-char string literal of all 5 app.py-source-reader test files
  (path-literal AND `__file__`/`getsource` classes) intersected against the moved text.
  11 hits, every one adjudicated: `panelkit.js` ∈ `test_axis_titles` ∩ `_forecast_body` is the
  designated positive control (a static-JS list entry, not an app.py assertion);
  `chartframe.js` assertions read **chrome.py** (repointed in phase 2); the CSS literals read
  **css files**; the rest are generic words. `_TS_CAPTION_MARK` / `data-ts-caption` /
  `drilldown.js` verified ABSENT from the moved text — the caption ledger and drill counters
  are untouched. **The first slice in which no reader's subject moved** — zero repoints needed
  (the two guard-tuple widenings are additions, not repoints).

## Verification

Six mutations, each landed-count-asserted in-script (exact-match splices that fail loudly),
each run against the WHOLE module (no `-k`), each exactly ONE named failure with the twins
green (the ran-signature rule: the summary must NAME the test), each restored from a
scratchpad copy (never `git checkout`), md5 + anchor-grep verified:

| mutation | named failure | split |
| --- | --- | ---: |
| re-export deleted from `app.py` | `…reexported_by_app…[forecast.py]` | 1 / 26 |
| deferred upward import in `_forecast_data` (in-body form) | `…imports_downward[forecast.py]` | 1 / 26 |
| `"forecast.py"` dropped from `test_bar_drill` | `…read_the_whole_view_layer[test_bar_drill.py]` | 1 / 26 |
| `"forecast.py"` dropped from `test_presentation_fixes` | `…[test_presentation_fixes.py]` | 1 / 26 |
| `"&mdash;"` sentinel planted in `forecast.py` (in-body) | `test_no_mdash_entity_sentinel_values…` | 1 / 4 |
| second `drilldown.js` include in `forecast.py` | `test_drilldown_runtime_is_loaded_globally…` | 1 / 5 |

Mutations 3–4 are the enumeration guard's **eleventh and twelfth consecutive live catches**.
Mutations 2 and 5 used the in-body form from the start — ADR-0373's defensive-overlap finding
(a NEW top-level name draws the re-export guard too) applied rather than re-derived.

## Deliberately NOT done

- **The slice-7 crafted v4/v2 SSI setup-load sequences were not rebuilt into this oracle**
  (ADR-0372's precedent, same reasoning): they exist to execute `_apply_ssi_setup`'s branch
  families, which this cut does not touch; the `[ssi-api]`/`[ssi-grid]`/`[ssi-save]` labels
  still render the ssi module's main lines, and the sequences remain named in ADR-0365/0373
  for any future slice whose closure touches that machinery.
- `CLAUDE.md`'s phase-3 + E501 prose still lags by design (the standing doc-drift sweep owns
  them); `forecast.py` DID join pyproject's per-file E501 list.
- `/api/sra/jcl` still renders 422 in every oracle state (unchanged from ADR-0373's note).

## Consequences

- Five page families remain, re-priced by the post-cut prefix census (each still owes its OWN
  closure before cutting): **what 289** · portfolio 253 · evm 239 · how 214 · **where 158**
  (the stale 235 included `_where_it_lands_header`'s 77 lines, measured out with this family).
- When **/evm** is cut, `_field_forecast_panel` is already below it in `forecast.py`; its
  closure will find the panel extracted, exactly as ADR-0373's Consequences predicted for the
  sra stays.
- The 420-label oracle (full-surface target sequences, both-fmt named exports, the grouped
  variants) is the widest yet; the `[grouped]` labels are the only execution proof for
  `_group_rollup_panel` and the field panel's table body and must survive into future oracles.
