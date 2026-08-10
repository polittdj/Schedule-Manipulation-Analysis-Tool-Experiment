# ADR-0379 — Phase 3 slice 15: the /resources family, and the oracle that was blind to it

- **Status:** Accepted
- **Date:** 2026-08-09
- **Continues:** ADR-0350 (the kernel), ADR-0351 (the descent rule — *not* fired this slice),
  ADR-0352 (the span-scoped pre-flight probe), ADR-0365 (closure-before-cut), ADR-0372 (the
  oracle recipe + the three normalizers), ADR-0374 (**the render-condition rule — this slice is
  its sharpest case yet**), ADR-0375 (the title-stripped TP4 pool), ADR-0377 (the stage-scoped
  fingerprint), ADR-0378 (sweep by bare NAME; the route-only-referrer rule)
- **Related:** ADR-0206 (the chapter-08 "Who is overloaded" header), ADR-0297 (the phase-1
  patch-the-module-that-CALLS trap, fired again here), ADR-0298 (the panel contract the page's
  three panels wear)

## Decision

**Extract the /resources page family — verbatim — into `web/resources.py` (362 lines): four
names in one contiguous block** (app.py 9807–10118): `_resource_loading_json`,
`_resources_explainer`, `_who_is_overloaded_header`, `_resources_body`. **No descent.**
`app.py` **11,403 → 11,095** (wc-truth). `LAYER_ORDER` becomes `… → evm → performance →
resources → app`; the re-export block lands immediately below portfolio's (isort: `portfolio` <
`resources` < `sra`); `resources.py` joins pyproject's per-file E501 list (the histogram/roster
panel copy and the explainer's `<p>` text are HTML string literals, already over-long inside
app.py's exempt region — verbatim outranks re-wrapping); `EXTRACTED`, `LAYER_ORDER`,
`VIEW_MODULES` and both whole-view-layer guard tuples gain `"resources.py"`.

## The closure: census-exact again, and a fifth name that stays

| | names | ast lines |
| --- | ---: | ---: |
| prefix census (the queue's number) | 4 | 306 |
| closure over `/resources` + both export routes | 5 | 308 |
| — of which **movers** | **4** | **306** |

Ratio **1.00×** on the movers — the second consecutive census-exact closure, and again only
because the queue had already absorbed a prior ruling by hand. The walk still assigns membership.

**The walk found a route the prefix never would.** Seeding by behaviour surfaced a *third*
entry point, `export_resource_drill` (`/export/{fmt}/resource-drill`), which no `_resource*`
prefix sweep reaches — the click-through Excel export behind one loading bar.

**No descent, adjudicated.** That third route is the only reason the closure exceeds the census:
it pulls in `_cell` (2 lines). `_cell` is referred to by six other export routes, by
`_import_risk_register` and `_import_task_risk` — and by **no mover**. A route-only referrer
never forces a descent (ADR-0378): routes live in `create_app`, which imports downward and stays.

**The export-contributes-no-movers streak RESUMES.** ADR-0378 broke it at five because
`export_performance` read the page's own data builder. Here both export routes build their
tables straight from `compute_resource_loading`, so this family's proven surface is the page
alone — and the probe anchors are page anchors by evidence, not by habit.

## The headline: the inherited oracle was STRUCTURALLY BLIND to this family

The first pre-flight probe returned **0 labels moved for all four movers** — a clean sweep of
"dark members" that would have made the slice unverifiable. It was not a product finding and not
a probe defect. Adjudicated by payload before anything was changed:

- `/resources` renders 19,040 bytes at every loaded stage, carrying **none** of the four anchors.
- The five-snapshot TP4 pool contains **zero** `<Assignment>`, **zero** `<Resource>` and **zero**
  `<Work>` elements. `_who_is_overloaded_header` returns `""` when `not rl.resources`, and
  `_resources_body` takes its no-loading branch. All four movers short-circuit **by design**.

The TP4 pool — the population every slice since ADR-0372 has rendered — **cannot exercise this
family at all**. ADR-0374's rule ("a render-conditional member needs its condition IN the
oracle") and ADR-0375's ("the fixture population is a render condition") are the same rule, and
this is their sharpest case: not one conditional member, but an entire family invisible to the
instrument.

**The oracle was extended, not reinterpreted.** A fifth stage `[resloaded]` was added: the
`project2_5` goldens (Project2 + Project5 — 164/165 assignments over 33 resources) uploaded into
the live session, with the render **condition asserted before the stage is measured** (five
markers required present, a `raise` otherwise). The inherited 498 labels are untouched, so
ADR-0377's published fingerprint stays checkable as a subset — and it reproduces exactly:

| stage | n | histogram |
| --- | ---: | --- |
| `[empty]` | 60 | `{200:41, 400:17, 422:2}` |
| `[loaded]` / `[target]` / `[cleared]` | 146 each | `{200:123, 404:4, 422:19}` |
| **`[resloaded]` (new)** | 146 | `{200:123, 404:4, 422:19}` |

4xx **69 loaded-stages** (unchanged) · **88 inherited all-stages** · **111** over all five
stages. Total **644 labels**. Double-render determinism across two separate processes: **0
flapping**. *An oracle that cannot render a family is not a weak oracle for that family — it is a
blind one, and it reports blindness as innocence.*

The harness self-check earned its keep twice more before any claim: the first build read
`404:6` per loaded stage against the recipe's `404:4`, and the payload diff named the cause —
two `[grouped]` labels pointed at routes that do not exist (`{"detail":"Not Found"}` from
`/dashboard` and `/activities`). Re-pointed at real filter-sensitive pages (`/scorecards`,
`/resources`), the histogram matched on the nose.

## Pre-flight probe — 4/4 render-proven, ZERO dark members (sixth consecutive slice)

Span-scoped anchor mutations in app.py: anchor count asserted `== 1` in-file, anchor line
asserted **inside** the member's own AST span, value-level markers only. Restores md5-verified.

| member | labels moved (of 644) |
| --- | --- |
| `_resource_loading_json` | **2** — `/resources` and `[grouped-resources] /resources`, `[resloaded]` |
| `_resources_explainer` | **2** — same two |
| `_who_is_overloaded_header` | **2** — same two |
| `_resources_body` | **2** — same two |

Every moved label sits in the new stage: on the inherited 498 all four are, and remain,
invisible. The 2-label reach is the honest measurement of a page-only family whose page appears
twice in the surface (bare, and under the session-wide filter).

## Proof

- **Per-region byte-identity: IDENTICAL** — asserted in-script before the write, from disk
  after, and a third time after `ruff --fix` dropped app.py's two now-unused imports
  (`sha256 ab1eb5e7…` on both sides); `ruff format --check` reported zero reformats over 941
  files.
- **Multiset (final tree): 54 added / 0 removed — ZERO code lines removed.** The two dropped
  imports (`ResourceLoading`, `bucket_key`) re-land inside `resources.py`'s parenthesized
  import, so every member line cancels verbatim. Measured on a quiescent tree, md5-verified
  first, with the `/proc`-based quiescence check ADR-0378 rewrote.
- **Dropped-import sweep (by bare NAME, ADR-0378): two names, adjudicated.** `bucket_key` — 0
  readers. `ResourceLoading` — 2 hits in `tests/web/test_r10_resources_contract.py`, both
  importing it **straight from `schedule_forensics.engine.resources`**, never through `web.app`;
  harmless.
- **644/644 byte-identical**, pristine vs cut; the fingerprint held on the cut tree.
- **Falsified in the new location: 4/4 EXACT label lists** — every member re-mutated in
  `resources.py` with the probe's own anchors moved exactly its pre-flight list; all four anchors
  additionally asserted **absent** from post-cut `app.py`; restores md5-verified.

## The sweeps

- **Monkeypatch + attribute sweep over all 18 names `resources.py` binds: ONE hit** —
  `tests/web/test_r10_resources_contract.py:274` patching `app_mod.compute_resource_loading` to
  substitute a clean engine result, then rendering `/resources`. That is the **ADR-0297 phase-1
  trap** live: the page's call now lives in `resources.py`, so an `app.py` patch would no longer
  reach it. Repointed to `web.resources` (and the docstring's "app.py is the module whose code
  calls the helper" corrected), then **proven load-bearing**: reverting the target to `web.app`
  fails exactly `test_takes_read_as_prose_when_nothing_is_over_allocated`; restored from a
  scratchpad copy, md5-verified.
- **Source-text sweep** (every ≥6-char literal of all 5 app.py-source-reader test files ∩ the
  moved text): every hit adjudicated — `panelkit.js` / `static` / `latest` / `status` /
  `/analysis/` / `<` / `&mdash;` all appear in the **staying** app.py too and belong to the
  two whole-view-layer guards, which this commit widens. `_TS_CAPTION_MARK`, `data-ts-caption`,
  `drilldown.js`, `_LAYOUT` and `mission.js` verified **absent** from the moved text. Zero
  source-text repoints; one monkeypatch repoint (above).

## Verification

Six mutations, each an exact-match splice landed-count-asserted in-script, each run against the
WHOLE module (no `-k`), each exactly ONE named failure, each restored from a scratchpad copy
(never `git checkout`), md5-verified, module re-run green after restore:

| mutation | named failure | split |
| --- | --- | ---: |
| re-export deleted from `app.py` | `…reexported_by_app…[resources.py]` | 1 / 36 |
| deferred upward import in `_resources_body` (in-body) | `…imports_downward[resources.py]` | 1 / 36 |
| `"resources.py"` dropped from `test_bar_drill` | `…read_the_whole_view_layer[test_bar_drill.py]` | 1 / 36 |
| `"resources.py"` dropped from `test_presentation_fixes` | `…[test_presentation_fixes.py]` | 1 / 36 |
| `"&mdash;"` sentinel planted in `resources.py` (in-body) | `test_no_mdash_entity_sentinel_values…` | 1 / 4 |
| second `drilldown.js` include in `resources.py` (in-body) | `test_drilldown_runtime_is_loaded_globally…` | 1 / 5 |

Mutations 3–4 are the enumeration guard's **twenty-first and twenty-second consecutive live
catches**. A **seventh** mutation proved the spy repoint load-bearing (above).

## The trap this slice paid for

### A positive control that cannot see the pattern it certifies

ADR-0378 ruled: sweep by bare NAME, and a positive control proves the sweep RUNS, not that its
PATTERN is right. This slice hit the *next* layer of that same lesson. The monkeypatch sweep was
written as a line regex — `setattr([A-Za-z_.]*, *["']<name>["']` — and run with ADR-0378's own
`compute_activity_makeup` as the positive control. **The control returned 0.**

The cause: `monkeypatch.setattr(` calls **wrap across lines**, so the module and the attribute
name sit on the line *after* the one the regex anchors on. A single-line regex cannot see them,
whatever alias it is aimed at. Had the control been omitted — or had it been chosen as a name
that happens to be patched on one line — the sweep would have reported "no hits" on a family
whose one real spy is the ADR-0297 trap, and the cut would have shipped it broken.

Replaced with an **AST sweep** over every test file: every `setattr(X, "name", …)` /
`monkeypatch.setattr(X, "name", …)` call recorded regardless of alias, wrapping or spelling. It
finds 188 such calls across `tests/`, reproduces the control, and returns the one real hit.

The same sweep prints the alias census, which is the quantitative case for ADR-0378's rule:
`mpp_mpxj` 23 · `launcher` 18 · **`appmod` 18** · **`app_module` 15** · `state_module` 9 ·
`state_mod` 6 · **`app_mod` 3**. Three different aliases for `web.app` alone, and the repo's
"dominant idiom" is only the third most common. *A control proves the sweep runs; only a control
that exercises the sweep's own weakness proves the pattern. Prefer a parser to a regex whenever
the thing being matched is syntax.*

## Deliberately NOT done

- **The `[resloaded]` stage does not replace the TP4 pool.** Keeping the inherited 498 byte-for-
  byte comparable is what lets ADR-0377's fingerprint act as a self-check; a swapped population
  would have silently re-based every future slice's reference.
- **`_cell` was NOT descended into `components.py`.** Shared, but by routes and importers — never
  by a mover. When the /activities-drill families are cut, their own closures will make that call.
- **The slice-7 crafted v4/v2 SSI setup-load sequences were not rebuilt into this oracle**
  (unbroken precedent since ADR-0372): this cut does not touch `_apply_ssi_setup`'s machinery.
- `groups` (430 by prefix) stays outside the phase-3 candidate list while ADR-0343 feature work
  is queued against it.
- `CLAUDE.md`'s phase-3 + E501 prose still lag by design (the standing doc-drift sweep owns them
  — `resources.py` now also joins the unpatched E501 list there); `resources.py` DID join
  pyproject's per-file E501 list.

## Consequences

- The remaining slice queue, by the post-cut prefix census (wc-truth; each family still owes its
  OWN closure before cutting; membership named because the prefix sweep is a finder, not the
  definition): **scurve 212** · **path 194** (incl. `_what_drives_header` 80) · **compare 166**
  (incl. `_what_changed_header` 79).
- **The oracle is now 644 labels and can render resource-loaded pages.** Every future slice
  inherits the `[resloaded]` stage; the fingerprint to reproduce is `[empty]` `{200:41,400:17,
  422:2}` · four loaded stages `{200:123,404:4,422:19}` each · 4xx **69 loaded / 88 inherited /
  111 all-five**.
- **A dark reading is a claim about the instrument first.** Four dark members on one page family
  was the signal that the population, not the code, was wrong. Before recording a member as dark,
  prove the oracle *can* render it.
- **Prefer a parser to a regex when matching syntax** — and pick the positive control to
  exercise the sweep's weakness, not merely its existence.
