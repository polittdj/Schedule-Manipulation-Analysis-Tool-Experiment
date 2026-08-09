# ADR-0375 — Phase 3 slice 11: the /portfolio family, and the census families that dissolved

- **Status:** Accepted
- **Date:** 2026-08-09
- **Continues:** ADR-0350 (the kernel), ADR-0351 (the descent rule + per-definition byte-identity),
  ADR-0352 (the span-scoped pre-flight probe), ADR-0365 (closure-before-cut), ADR-0372 (the oracle
  recipe + the three normalizers), ADR-0373 (the live-chain aim), ADR-0374 (the chapter-header
  ruling; the misfiled-member lesson this slice found three more of)
- **Related:** ADR-0258 (one Project at a time — the rule the oracle's first shape tripped over),
  ADR-0259 (exclude/restore), ADR-0321 (OR-01 rollup titles — the family's unit coverage)

## Decision

**Three moves, one slice.** (1) The /portfolio page family — verbatim — into a NEW
`web/portfolio.py` (287 lines): `_portfolio_memory_panel`, `_portfolio_body`,
`_portfolio_version_li`, one contiguous block (app.py 7286–7542). (2–3) The two chapter headers
stranded by history into their families' EXISTING modules, per ADR-0374's header ruling applied
retroactively: `_what_could_go_wrong_header` (130 lines; sole referrer the /sra route) →
`web/sra.py` (slice 9 cut the family one day before the ruling existed), and `_how_stable_header`
(71 lines; sole referrer the /evolution route) → `web/evolution.py` (slice 3 predates it by two
days more). `app.py` **13,814 → 13,359** (wc-truth); sra.py 1,866 → 2,000; evolution.py
1,075 → 1,150. `LAYER_ORDER` becomes `… → sra → forecast → portfolio → app`; the portfolio
re-export block lands between offload and sra (o < p < s); `portfolio.py` joins pyproject's
per-file E501 list (one 102-char ledger-intro line, over-long inside app.py's exempt region).

## The re-measure: three census families dissolve at once

The queue said "what 289" was the largest remaining family. The referrer walk says **"what" is
not a family at all** — it is three chapter headers with three different sole referrers, one per
page family: `_what_drives_header` → `path_view`, `_what_changed_header` → `compare`,
`_what_could_go_wrong_header` → `sra_view`. The same walk dissolves **how 214**
(`_how_we_execute_evm_header` → `evm_view` · `_how_stable_header` → `evolution_view` ·
`_how_we_execute_header` → `performance_view`) and **where 158** (`_where_we_stand_header`'s sole
referrer is `_analysis_body` — an /analysis-family member). ADR-0374 caught ONE misfiled member;
this census carried SEVEN, filed under three phantom families whose names are question words, not
pages. The closure re-prices the queue: **analysis 356** (198 + the where header) · **evm 299**
(239 + its header) · **performance 279** (196 + its header) · **path 194** (114 + 80) ·
**compare 166** (87 + 79). The two headers whose family modules already exist moved NOW; the
other five wait for their families' own slices.

**The portfolio closure itself is census-exact** (the second after mission): prefix 253/3 =
closure 253/3. `_portfolio_body`'s sole external referrer is the `/portfolio` route (a
`create_app` closure — imports downward, stays); both helpers are body-only. **No descents**:
every external lives in components/chrome/state/engine (`estimate_resident_bytes` /
`format_bytes` stay imported by app.py too — the upload flash quotes the same estimate at lines
1737–1741, a route concern).

## The oracle — 494 labels, and the population that manufactured a false dark

Rebuilt per the ADR-0372 recipe: every parameterless GET (60, pages AND APIs, validation-4xx
bodies kept) · both fmts × all 27 parameterless `{fmt}` exports · the 7 `{name}` pages AND all
8 `{name}` exports both fmts on TP4 v5 · the established variants (`/trend?target=22`, the three
`/evolution` variants, the seeded `/api/sra/ssi?iterations=300`, the four `[grouped]` labels —
kept per ADR-0374, still the only execution proof for `_group_rollup_panel`) ·
`[target-set]`/`[target-cleared]` re-rendering the FULL surface incl. the variants (494 total —
wider than slice 10's 420 because the variants re-render in both target states). Anchors on the
live critical chain by design: target UID **22** (Network cabling, 50%, 0 float, head of the
live 22→26 chain). Three normalizers inherited.

**The first oracle shape measured a false dark.** The five TP4 snapshots carry five DISTINCT
`<Title>`s, so they grouped into five one-version Projects; ADR-0258's active population was v5
alone, and every multi-version page (/evolution, /compare, /trend, …) rendered its "load two
versions" placeholder. `_how_stable_header` probed **0 moved** — adjudicated by payload BEFORE a
stronger-anchor round: the /evolution body contained the placeholder, not a weak anchor. Fix:
the oracle uploads the snapshots with `<Title>` STRIPPED, so all five join the untitled pool as
ONE five-version population (`_portfolio_body`'s own `origin == "filename"` path). 4xx labels
133 → 88 — forty-five labels switched from placeholder to real body, widening every future
slice's oracle. Double-render determinism across two separate processes: **0 flapping — proven
twice** (before and after the population fix). *ADR-0374 said "read each member's render
condition off the route"; this slice adds: read the POPULATION the oracle's fixtures actually
form — a fixture family that groups wrong renders placeholders everywhere and calls them
byte-stable.*

## Pre-flight probe — 5/5 render-proven, zero dark members

Span-scoped anchor mutations in place in app.py (anchor count == 1 asserted, anchor line
asserted inside the member's span, restores md5- and anchor-grep-verified):

| member | labels moved (of 494) |
| --- | --- |
| `_portfolio_body`, `_portfolio_memory_panel`, `_portfolio_version_li` | 3 each — /portfolio in loaded/t-set/t-clr ([empty] renders the placeholder) |
| `_what_could_go_wrong_header` | 3 — /sra in loaded/t-set/t-clr |
| `_how_stable_header` | 12 — /evolution bare + all three variants × three states |

## Proof

- **Per-region byte-identity: 3/3 IDENTICAL** — asserted inside the cut script before writing
  and re-verified from disk after; `ruff format --check` passed with zero reformats, and region
  P was re-verified verbatim after ruff's import-sort fix touched portfolio.py's import block.
- **Multiset (final tree): 44 added / 3 removed — zero code lines removed.** Additions:
  portfolio.py's preamble + import block, app.py's 6-line re-export block (3 comment + 3
  imports), the two header re-export lines, sra.py's four widened import lines, evolution.py's
  two added import names, and 8 blanks. The 3 removals are import-shape artifacts:
  `ProjectVersion,` (re-lands in portfolio.py's single-line import), sra.py's cpm line
  (superseded by its CPMError-widened form), app.py's path_evolution line (narrowed to
  `compute_path_evolution`; `PathEvolution` lives on in evolution.py's pre-existing import).
  The moved region lines cancel exactly — verbatim.
- **Dropped-import sweep:** zero readers of `ProjectVersion` / `PathEvolution` through
  `web.app` (the one test using `PathEvolution` imports the engine directly); machinery control
  live (`from schedule_forensics.web.app import SessionState` found in multiple test files).
- **494/494 routes byte-identical**, pristine vs cut, on the double-render-verified oracle.
- **Falsified in the new locations: 5/5 EXACT** — every member re-mutated in
  portfolio.py/sra.py/evolution.py with the probe's own anchors moved exactly its pre-flight
  label LIST, restores md5-verified.

## The sweeps

- **Monkeypatch + attribute-read sweep** (all 24 names portfolio.py binds plus the names
  sra/evolution gained): **zero hits on moved names**; two adjudicated — the
  `SessionState.scope` wrap patches the CLASS object (module-boundary-invariant), and the
  standing `app_mod.non_summary` projection-memo patch is the live positive control (1 setattr
  + 1 read; its spied path is /api/dashboard through app.py's own binding — portfolio.py's
  import is outside its reach, the ADR-0365 adjudication unchanged).
- **Source-text sweep** (every ≥6-char literal of all 7 app.py-source-reader test files ∩ the
  moved text): every hit adjudicated — `panelkit.js` ∈ `test_axis_titles` ∩ `_portfolio_body`
  is the designated positive control (a static-JS list entry, not an app.py assertion);
  `test_bar_drill`'s entered/left/latest literals target volatility.js; the `&mdash;` guard is
  whole-view-layer aggregate (and now reads portfolio.py); `_TS_CAPTION_MARK` /
  `data-ts-caption` / the drilldown script tag verified ABSENT from the moved text (the
  `# drilldown.js` mention in `_how_stable_header` is a comment, not the counted tag). **Zero
  reader repoints — second consecutive slice.**

## Verification

Six mutations, each landed-count-asserted in-script (exact-match splices that fail loudly),
each run against the WHOLE module (no `-k`), each exactly ONE named failure with the twins
green, each restored from a scratchpad copy (never `git checkout`), md5 + anchor-grep verified,
each module re-run green after restore:

| mutation | named failure | split |
| --- | --- | ---: |
| re-export deleted from `app.py` | `…reexported_by_app…[portfolio.py]` | 1 / 29 |
| deferred upward import in `_portfolio_body` (in-body form) | `…imports_downward[portfolio.py]` | 1 / 29 |
| `"portfolio.py"` dropped from `test_bar_drill` | `…read_the_whole_view_layer[test_bar_drill.py]` | 1 / 29 |
| `"portfolio.py"` dropped from `test_presentation_fixes` | `…[test_presentation_fixes.py]` | 1 / 29 |
| `"&mdash;"` sentinel planted in `portfolio.py` (in-body) | `test_no_mdash_entity_sentinel_values…` | 1 / 5 |
| second `drilldown.js` include in `portfolio.py` | `test_drilldown_runtime_is_loaded_globally…` | 1 / 6 |

Mutations 3–4 are the enumeration guard's **thirteenth and fourteenth consecutive live
catches**. Mutations 2 and 5 used the in-body form from the start (ADR-0373's
defensive-overlap finding applied, not re-derived).

## Deliberately NOT done

- **The five headers whose family modules do not exist yet stay in app.py** —
  `_what_drives_header` (path), `_what_changed_header` (compare), `_how_we_execute_evm_header`
  (evm), `_how_we_execute_header` (performance), `_where_we_stand_header` (analysis). Each is
  closure-assigned to its family and moves with that family's slice; moving one now would
  invent a module its family doesn't own yet.
- **The slice-7 crafted v4/v2 SSI setup-load sequences were not rebuilt into this oracle**
  (ADR-0372/0374 precedent, same reasoning): this cut does not touch `_apply_ssi_setup`'s
  machinery; the sequences remain named in ADR-0365/0373 for any slice whose closure does.
- `groups` (315 by prefix) stays outside the phase-3 candidate list, as it has since
  ADR-0365's census — the /groups Activities feature work (ADR-0343) is queued against that
  page and cutting under queued feature churn buys conflicts, not layering.
- `CLAUDE.md`'s phase-3 + E501 prose still lag by design (the standing doc-drift sweep owns
  them); `portfolio.py` DID join pyproject's per-file E501 list.

## Consequences

- The remaining slice queue, re-priced by closure-assigned membership (each family still owes
  its OWN closure before cutting): **analysis 356** · **evm 299** · **performance 279** ·
  resources 255 (177 + `_who_is_overloaded_header` 78) · scurve 212 · path 194 ·
  compare 166 — the phantom question-word families are RETIRED as cut targets.
- The 494-label oracle (untitled-pool population, full-surface target sequences, the [grouped]
  labels) is the widest yet; **the title-strip is load-bearing** — any future oracle that
  uploads the TP4 family verbatim re-manufactures the five-project population and the
  placeholder surface with it.
- When **/evm** is cut, `_field_forecast_panel` (forecast.py, ADR-0374) AND
  `_how_we_execute_evm_header`'s move complete the page; when **/analysis** is cut, the where
  header travels with `_analysis_body`.
