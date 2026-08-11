# ADR-0386 — Phase 4 slice 21: the /wbs family, and the sweep that measured a stale copy of src/

- **Status:** Accepted
- **Date:** 2026-08-10
- **Continues:** ADR-0350 (the kernel), ADR-0351 (the descent rule — *not* fired), ADR-0352 (the
  span-scoped pre-flight probe), ADR-0365 (closure-before-cut; the named-failure rule), ADR-0372
  (the oracle recipe), ADR-0375 (the title-stripped TP4 pool), ADR-0377 (the stage-scoped
  fingerprint), ADR-0378 (sweep by bare NAME; route-only referrers; the page-only-anchor trap),
  ADR-0382 (the oracle committed to the repo), ADR-0383 (phase 4's scope and its priced table),
  **ADR-0384 (slice 20, and the byte-offset probe bug whose fix this slice inherits)**
- **Related:** ADR-0327 (the panel contract both pivots follow), ADR-0343 (`groups` stays fenced)

## Decision

**Extract the /wbs page family — verbatim — into `web/wbs.py` (154 lines): THREE functions in
ONE contiguous block** (app.py 7294–7407), **no descent**. `app.py` **10,046 → 9,937**
(wc-truth) — **the monolith drops below 10,000 lines for the first time**, from 17,197 when
phase 3 began. `LAYER_ORDER` becomes `… → standards → wbs → app`; `wbs.py` joins pyproject's
per-file E501 list; `EXTRACTED`, `LAYER_ORDER`, `VIEW_MODULES` and both whole-view-layer guard
tuples gain `"wbs.py"`.

## The closure — the prefix misses a member again

| | names | ast lines |
| --- | ---: | ---: |
| prefix census (`wbs`) | 2 | 107 |
| closure over all THREE routes | **3** | **110** |

`_num` — a three-line optional-number formatter — carries no `wbs` prefix at all, and it is a
member: its only referrers are inside `_wbs_body`, which a **bare-NAME sweep confirms
independently of the walk** (definition plus seven call sites, all inside `_wbs_body`'s span).
1.5× by names. After slice 20's census-exact 1.00×, this is the immediate counter-example to
reading that as licence: **the prefix is a finder, the walk is the definition** (ADR-0378).

**The export route contributes NO movers, measured — and the probe agrees.** `export_wbs`'s
app-level callee set is **empty**: it re-derives its pivots through
`reports/tables.py::wbs_breakdown_tables` rather than calling `_wbs_body` or `_wbs_data`. That
licenses a page-only probe anchor (ADR-0378's trap). This slice got a second, independent
confirmation for free: when each member was mutated, the four `[stage] GET /export/{xlsx,docx}/
wbs/…` labels **did not move**. The call-graph claim and the render claim were made by different
instruments and agree.

**Zero descent, zero shared names, zero owned constants.** Everything else resolves to an
import: `_e`, `_utility_takeaway` (chrome); `_panel_head`, `_shell_tools` (components);
`WBSGroup` (engine.metrics); `quote` (stdlib). The free-name pass finds no module-level
assignment owned by the block.

## The routes are three, and they partition cleanly

| member | route it renders through | labels moved (of 648) |
| --- | --- | --- |
| `_num`, `_wbs_body` | `GET /wbs/{name}` | **4 each** — the four loaded stages |
| `_wbs_data` | `GET /api/wbs/{name}` | **4** — the four loaded stages |
| — | `GET /export/{fmt}/wbs/{name}` | **0 movers** (re-derives) |

Probe **3/3 render-proven, ZERO dark** — twelfth consecutive slice.

## The probe needed a TYPE-AWARE marker

`_wbs_data` returns a `dict`, not a `str`. ADR-0384's marker (`(<expr>) + "MARK"`) would have
raised `TypeError` at render, turning every `/api/wbs` label into a 500 — the member would have
measured as "moves lots of labels", which is a measurement of the probe, not of the member. A
dict member gets an additive key (`{**(<expr>), "MARK": 1}`) instead. **Match the marker to the
return type, or the probe measures itself.**

## The sweep that measured a stale copy of `src/`

The four sweeps ran first over **646** Python files — against **507** in slice 20. The extra
**138** were `build/`, left behind by `python -m build` when the v1.0.192 wheel was produced one
slice earlier: a *stale copy of `src/`* carrying `standards.py` but not `wbs.py`.

No verdict changed (re-run over the clean population: 508 files, same hits, same control at 177
files), but the exposure is real in both directions — a sweep over a stale snapshot can **invent**
a reader that no longer exists, or **miss** one added since the snapshot, and it reports the same
confident "0 hits" either way. The sweep now excludes `build/`, `dist/`, `.venv`, caches — and
**states its population with its count**, because the number is the claim.

## Proof

- **The committed oracle rebuilt the inherited fingerprint** on the post-slice-20 tree: `[empty]`
  60 `{200:41,400:17,422:2}`, four loaded stages of 147 `{200:124,404:4,422:19}`, **648** total;
  determinism ×2 separate processes, **0 flapping**.
- **Per-definition byte-identity: 3/3 IDENTICAL** — in-script before the write, re-read from
  disk, and again after `ruff check --fix` + `ruff format` (region sha256 `267f40832493`;
  the formatter reported the file unchanged).
- **648/648 byte-identical**, pristine vs cut.
- **Falsified in the new location: 3/3 EXACT label lists**; every `def` asserted **absent** from
  post-cut `app.py`.
- **Multiset: 45 added / 1 removed — ZERO code lines removed.** The single removal is the
  parenthesized import member `    WBSGroup,`, re-added as `wbs.py`'s own import.

## The sweeps

- **Dropped-import sweep: ONE.** `ruff --fix` removed `WBSGroup` from `app.py` — the three movers
  were its last consumers. Adjudicated safe by an AST, alias-agnostic check: **zero** callers
  reach it through `web.app`; positive control `create_app` = 177 files.
- **Monkeypatch / setattr sweep: ZERO hits** on all 10 names `wbs.py` binds (196 setattr-style
  calls across 508 files; ADR-0378's control at `test_manifest_projection_memo.py:74`
  reproduces). No ADR-0297 trap — the three callers (`wbs_breakdown_view`, `wbs_json`,
  `export_wbs`) all stay in `app.py`.
- **Import sweep: ONE live reader, deliberately NOT repointed.**
  `tests/web/test_coverage_app_extra.py:228` does `from schedule_forensics.web.app import
  _wbs_body` and exercises the no-groups branch. The `X as X` re-export keeps it working, and
  leaving it makes it a standing live check of the re-export contract — the same call ADR-0383
  made for `test_risks.py`'s three readers.
- **Source-text sweep: 13 app.py-source readers, zero repoints.** The region carries no
  `drilldown.js`, no `"&mdash;"`, no `_TS_CAPTION_MARK` and — unlike slice 20's — no
  `panelkit.js` (the neighbouring function's include sits *outside* the span). It does carry
  `wbs.js`, and every `wbs.js` guard in the suite reads either the **static file** itself
  (`test_r11_panel_contract`, `test_dd_line_ledger`, `test_accessibility`,
  `test_categorical_bar_drill`) or the **rendered page** (`test_wbs_view`) — the two sets are
  disjoint from the 13 app.py-source readers, checked by name.

## Verification

Six mutations, each an exact-match splice landed-count-asserted in-script before the write, each
run against the WHOLE module (no `-k`), each restored from a scratchpad copy (never
`git checkout`), md5-verified, each module re-run green after restore. Mutations 3–4 are the
enumeration guard's **33rd and 34th** consecutive live catches.

| mutation | named failure | split |
| --- | --- | ---: |
| re-export deleted from `app.py` | `…reexported_by_app…[wbs.py]` | 1 / 49 |
| deferred upward import in `_wbs_body` (in-body) | `…imports_downward[wbs.py]` | 1 / 49 |
| `"wbs.py"` dropped from `test_bar_drill` | `…read_the_whole_view_layer[test_bar_drill.py]` | 1 / 49 |
| `"wbs.py"` dropped from `test_presentation_fixes` | `…[test_presentation_fixes.py]` | 1 / 49 |
| `"&mdash;"` sentinel planted in `wbs.py` (in-body) | `test_no_mdash_entity_sentinel_values…` | 1 / 5 |
| second `drilldown.js` include in `wbs.py` (in-body) | `test_drilldown_runtime_is_loaded_globally…` | 1 / 6 |

## Deliberately NOT done

- **No second slice.** `brief` (44) is the last zero-descent family and was left for slice 22.
- **`export_wbs` was not refactored to call `_wbs_body`/`_wbs_data`.** It duplicates the pivot
  derivation, which is a real (small) redundancy — converging them changes behaviour and is not
  a split.
- **`brief` and `briefing` were both re-priced but neither was cut.** See below.
- `CLAUDE.md`'s phase-3 + E501 prose still lags by design (the standing doc-drift sweep owns it;
  `wbs.py` now also joins the unpatched E501 list there); `wbs.py` DID join pyproject's.

## A census instrument note: `brief` is a PREFIX of `briefing`

Re-pricing the remaining zero-descent candidates surfaced a defect in the census harness, not in
the code: its seed matches route paths by **substring**, so seeding `brief` swallowed
`/briefing`, `/export/{fmt}/briefing` and `/api/ai/briefing` and reported one 8-name family with
three descents — two of ADR-0383's families fused. Seeded on exact route lists they separate and
reproduce that table:

| family | seeds | movers | ast lines | descents |
| --- | --- | ---: | ---: | ---: |
| `brief` | `/brief`, `/export/{fmt}/brief` | 1 | 44 | **0** |
| `briefing` | `/briefing`, `/export/{fmt}/briefing`, `/api/ai/briefing` | 4 | 194 | 3 |

`briefing`'s three are the AI-backend helpers (`_ollama_or_none`, `_openai_or_none`,
`_active_backend`), shared with `_ai_status_note` / `_settings_body` / `_polished_narrative` /
`_translate_batch`. ADR-0383's table records **4** descents for `briefing`; this walk finds 3.
Not adjudicated here — it is not this slice's family — but **`briefing` must be re-priced before
it is cut**, which is what the standing rule already says.

## A shipped-artifact finding: the MPXJ pin drifts to the build container's clone boundary

`tools/installer/build_installers.py::mpxj_ref()` bakes an **immutable** commit into all nine
installers — "the last commit that touched `tools/mpxj`" — precisely so the download URL and the
baked-in SHA-256 manifest can never disagree (ADR-0299; PR #446 review, P1).

It is computed with `git log -1 --format=%H -- tools/mpxj`. In a **shallow clone** that command
cannot see past the shallow boundary, and git reports the boundary commit as introducing every
file — so the pin silently becomes *whatever commit this container happened to clone at*. Measured
here:

| build | pin produced | did that commit touch `tools/mpxj`? |
| --- | --- | ---: |
| committed installers at `41fb122` (slice 19) | `f0634639` | **no** |
| this container, `--depth 1` at `41fb122` (slice 20, merged in #569) | `41fb122` | **no** |
| this container after `git fetch --unshallow` | **`42d92dc`** | **yes** (ADR-0232, #370) |

Nothing broke, because every candidate is a real pushed commit whose `tools/mpxj` bytes are
identical — the URL resolves and the manifest matches. But the pin has been drifting session to
session, each build re-pinning to its own clone boundary, and **slice 20 shipped that drift as an
unintended diff**. This slice's installers are built on an unshallowed clone and pin `42d92dc`,
which is what the docstring has always said they should.

The durable fix is not in this diff: `mpxj_ref()` should either refuse to run in a shallow clone
or deepen until it finds a commit that genuinely modified the path. Queued, not silently patched
here — it is installer machinery, and changing it belongs with its own falsification round.

## Consequences

- **`app.py` is below 10,000 lines.** Eleven families / ~2,008 mover lines remain outside
  `groups` by ADR-0383's table — re-priced by referrer walk at the time, never assumed.
  `brief` (44) is the last zero-descent one; then `scorecards` (151) and `card` (140), whose only
  shared names are route-only.
- **A probe's marker must match the member's return type.** A str-concat marker on a dict-returning
  member does not measure a dark member; it measures a 500.
- **A sweep's population is part of its claim.** Build artifacts are a stale copy of the tree;
  exclude them, and state the file count next to the verdict.
- **Two instruments agreeing is worth more than either alone.** The call graph said `export_wbs`
  contributes no movers; the render probe independently showed the export labels do not move.
