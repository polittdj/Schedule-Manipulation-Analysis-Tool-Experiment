# ADR-0384 — Phase 4 slice 20: the /standards family, and the sweep the byte offsets broke

- **Status:** Accepted
- **Date:** 2026-08-10
- **Continues:** ADR-0350 (the kernel), ADR-0351 (the descent rule — *not* fired), ADR-0352 (the
  span-scoped pre-flight probe), ADR-0365 (closure-before-cut; the named-failure rule), ADR-0372
  (the oracle recipe + the three normalizers), ADR-0375 (the title-stripped TP4 pool), ADR-0377
  (the stage-scoped fingerprint), ADR-0378 (sweep by bare NAME; the route-only-referrer rule; a
  census can be exact and still not be membership), ADR-0382 (the oracle committed to the repo),
  **ADR-0383 (which scoped phase 4 and ranked `standards` first among the zero-descent families)**
- **Related:** ADR-0327 (the panel contract these three sections follow), ADR-0238 (the SEM family
  validated against the Fuse exports), ADR-0343 (the /groups feature work that fences `groups` out)

## Decision

**Extract the /standards page family — verbatim — into `web/standards.py` (227 lines): FOUR
functions in ONE contiguous block** (app.py 8764–8930), **no descent**. `app.py` **10,215 →
10,046** (wc-truth). `LAYER_ORDER` becomes `… → risks → standards → app`; `standards.py` joins
pyproject's per-file E501 list; `EXTRACTED`, `LAYER_ORDER`, `VIEW_MODULES` and both
whole-view-layer guard tuples gain `"standards.py"`.

## The closure — census-exact, for the second time in the split

| | names | ast lines |
| --- | ---: | ---: |
| prefix census (`standards`) | 4 | 161 |
| closure over `GET /standards` | **4** | **161** |
| — of which **movers** | **4** | **161** |

**1.00×** — the prefix and the walk agree exactly, as they did once before (ADR-0378, slice 14).
That is a coincidence of this family's naming, not a licence to price the next one by prefix:
ADR-0383's own family ran 2.27× its prefix, and the walk is what says which of the two you are
looking at. **A census can be exact and still not be membership** (standing trap 1) — the walk
assigns membership, and here it happens to agree.

**The family has no export route at all.** `standards` is the first slice whose seed surface is a
single page GET: the route census finds one `/standards` route and zero `/api` or `/export`
siblings, and a whole-tree grep for the four names returns nothing outside `app.py`. The page's
⤓ EXCEL points at the *analysis* workbook (`/export/xlsx/analysis/{key}`), which `export_analysis`
serves without calling a member. So ADR-0378's trap — a page-only probe anchor understates a
member that feeds an export — is **checked off by measurement, not waved past**: there is no
export to understate. Sixth consecutive slice whose export surface contributes no movers.

**Zero descent, zero shared names, and — measured — zero owned constants.** Every other name the
four members touch resolves to an *import*: `_e`, `_utility_takeaway` (chrome);
`_ANALYSIS_XLSX_TITLE`, `_panel_head`, `_prov_chip`, `_shell_tools`, `_status_class` (components);
`SessionState`, `_Analysis` (state); `metric_doc` (help); `AuditCheck` (engine.dcma_audit);
`CheckStatus`, `MetricResult` and eight `compute_*` families (engine.metrics); `Schedule` (model);
`Sequence`, `quote` (stdlib). ADR-0383's free-name pass — the one that caught four stranded
constants there — ran here and found **no module-level assignment owned by the block**. A pass
that finds nothing is worth running: that is how you know the block owns nothing.

## Pre-flight probe — 4/4 render-proven, ZERO dark (eleventh consecutive)

Span-scoped: every `return` expression inside the member's own AST span marked additively, the
count asserted before the write, each anchor line asserted inside the span.

| member | labels moved (of 648) |
| --- | --- |
| `_standards_value_cell` (4 anchors) · `_standards_rows` · `_standards_section` · `_standards_body` | **4 each** — `/standards` at all four loaded stages |

`[empty] GET /standards` correctly does **not** move: with no schedules the route returns its
"Load a schedule to see the DCMA-14, NASA/Acumen-Fuse, and Schedule Execution Metrics scorecards"
placeholder and calls no member.

## The instrument bug this slice paid for: `col_offset` is a BYTE offset

The probe's first run planted its markers by character-indexing `ast` column offsets. `ast`
reports `col_offset` in **UTF-8 bytes**, and this region carries `—`, `·`, `⤓` and `⛶` — so every
edit on a line with non-ASCII before the column landed several columns early. It produced
`) + "SFPROBE1"   if m.unit == "count":` — a `SyntaxError` at import, which is the *cheap*
failure. On a different line shape the same skew lands inside a string literal and the probe
measures a member it silently corrupted. The fix is to splice on `bytes` and re-`ast.parse` the
result before writing: **a probe that does not parse is not a measurement.**

## Proof

- **The oracle imported clean on a second cold container.** ADR-0382's committed corpus rebuilt
  the inherited fingerprint with no reconstruction: `[empty]` 60 `{200:41,400:17,422:2}`, four
  loaded stages of 147 `{200:124,404:4,422:19}`, **648** total. Determinism ×2 separate processes:
  **0 flapping**. Second consecutive cold-start success.
- **Per-definition byte-identity: 4/4 IDENTICAL** — asserted in-script before the write, re-read
  from disk after, and a third time after `ruff check --fix` + `ruff format` (region sha256
  `39f910ab432c`, unchanged across all three; `ruff format` reported the file unchanged).
- **648/648 byte-identical**, pristine vs cut; the full fingerprint held on the cut tree.
- **Falsified in the new location: 4/4 EXACT label lists** — each member re-mutated inside
  `standards.py` with the probe's own anchors moved exactly its pre-flight list; every `def`
  additionally asserted **absent** from post-cut `app.py` (the code moved, it was not copied).
- **Multiset: 60 added / 2 removed — ZERO code lines removed.** The two removals are
  *import-line rewrites*, both from the dropped-import set:
  `from …dcma_audit import AuditCheck, Citation` → `… import Citation`, and the parenthesized
  member `    metric_doc,`. Every added line is `standards.py`'s docstring, its import block and
  the four re-exports plus their ADR comment.

## The sweeps — nine dropped imports, the largest set yet

- **Dropped-import sweep: NINE dropped.** `ruff --fix` removed `AuditCheck`, `metric_doc` and
  the seven `compute_*` names (`compute_bri`, `compute_cei`, `compute_completion_performance`,
  `compute_fei`, `compute_float_ratio`, `compute_hmi`, `compute_sem`) from `app.py` — the four
  movers were app.py's last consumers of all nine. Adjudicated safe by an AST, alias-agnostic
  check: **zero** callers reach any of them through `web.app` (neither
  `from schedule_forensics.web.app import <name>` nor `<alias>.<name>` on a module bound to
  `web.app`), with a positive control (`create_app`, 177 files) proving the sweep runs. No
  re-export is owed: the nine are *imports* in `standards.py`, not names it defines.
  `compute_evm_indices` is **not** in the set — `export_evm` still reads it in `app.py`, which is
  exactly the shared-import shape ADR-0377 recorded.
- **ADR-0383's parenthesized-import lesson held.** One of the nine (`    metric_doc,`) came out of
  a parenthesized block, the shape a `^-from`/`^-import` diff regex cannot see. The sweep compared
  the two trees' import **sets** by AST from the start and caught it.
- **Monkeypatch / setattr sweep (AST, alias-agnostic): ZERO hits** on all 29 names `standards.py`
  binds. 196 setattr-style calls across 507 files; ADR-0378's control
  (`compute_activity_makeup` at `test_manifest_projection_memo.py:74`) reproduces. No ADR-0297
  trap — the caller `standards_view` stays in `app.py`.
- **Import sweep: ZERO readers, ZERO repoints.** No test imports any of the four names from
  `web.app`; the bare-NAME sweep (trap 4) finds them only at their definitions and app.py's
  re-export line.
- **Source-text sweep: 13 app.py-source readers, zero repoints.** The region carries no
  `drilldown.js`, no `"&mdash;"` and no `_TS_CAPTION_MARK`. It *does* carry two `panelkit.js`
  occurrences — one prose mention in `_standards_section`'s docstring and one real `<script src>`
  in `_standards_body` — and app.py's count falls 19 → 17 accordingly; every `panelkit` guard in
  the suite asserts over the **rendered page**, not app.py's source, so none is affected. The
  arithmetic is stated because an unexplained count is an unshipped one.

## Verification

Six mutations, each an exact-match splice landed-count-asserted in-script before the write, each
run against the WHOLE module (no `-k`), each restored from a scratchpad copy (never
`git checkout`), md5-verified, each module re-run green after restore. Mutations 3–4 are the enumeration guard's **31st and
32nd** consecutive live catches.

| mutation | named failure | split |
| --- | --- | ---: |
| re-export deleted from `app.py` | `…reexported_by_app…[standards.py]` | 1 / 47 |
| deferred upward import in `_standards_body` (in-body) | `…imports_downward[standards.py]` | 1 / 47 |
| `"standards.py"` dropped from `test_bar_drill` | `…read_the_whole_view_layer[test_bar_drill.py]` | 1 / 47 |
| `"standards.py"` dropped from `test_presentation_fixes` | `…[test_presentation_fixes.py]` | 1 / 47 |
| `"&mdash;"` sentinel planted in `standards.py` (in-body) | `test_no_mdash_entity_sentinel_values…` | 1 / 5 |
| second `drilldown.js` include in `standards.py` (in-body) | `test_drilldown_runtime_is_loaded_globally…` | 1 / 6 |

## Deliberately NOT done

- **No second slice.** `wbs` (110) and `brief` (44) are the remaining zero-descent families and
  were left for slice 21 — one family per slice with the full instrument is what has kept every
  slice byte-identical.
- **`export_analysis` was not re-pointed at the family.** The /standards ⤓ deliberately serves the
  *analysis* workbook (ADR-0327 records why: a ⤓ with no covering endpoint is a defect class);
  giving the page its own export is a feature, not a split.
- `CLAUDE.md`'s phase-3 + E501 prose still lags by design (the standing doc-drift sweep owns it;
  `standards.py` now also joins the unpatched E501 list there); `standards.py` DID join
  pyproject's.

## Consequences

- **Twelve families / 2,118 mover lines remain** outside `groups` by ADR-0383's table — re-priced
  by referrer walk at the time, never assumed. The zero-descent set is down to `wbs` (110) and
  `brief` (44), plus `scorecards` (151) and `card` (140) whose only shared names are route-only.
- **`ast` column offsets are BYTE offsets.** Any harness that edits source by `(lineno, col)` must
  splice on bytes and re-parse before writing. This is now a standing trap.
- **A free-name pass that finds nothing is still evidence.** ADR-0383 added the pass because four
  constants hid from the call graph; running it here and reporting the empty result is what
  distinguishes "this block owns no constants" from "nobody looked."
