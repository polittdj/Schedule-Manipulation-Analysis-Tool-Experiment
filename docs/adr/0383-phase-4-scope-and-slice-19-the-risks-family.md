# ADR-0383 — Phase 4 scope, and slice 19: the /risks family, off a list that said it was empty

- **Status:** Accepted
- **Date:** 2026-08-10
- **Continues:** ADR-0350 (the kernel), ADR-0351 (the descent rule — *not* fired), ADR-0352 (the
  span-scoped pre-flight probe), ADR-0365 (closure-before-cut), ADR-0372 (the oracle recipe +
  the three normalizers), ADR-0375 (the title-stripped TP4 pool), ADR-0377 (the stage-scoped
  fingerprint; anchor asserted inside the member's own span), ADR-0378 (sweep by bare NAME; the
  route-only-referrer rule; a census can be exact and still not be membership), ADR-0380 (mutate
  by offset, not permutation), **ADR-0382 (which declared the phase-3 page-family list exhausted
  and asked for exactly the fresh census this ADR performs)**
- **Related:** ADR-0338 (the panel contract these panels follow), ADR-0282 (Option A: findings
  follow the parity audit), ADR-0343 (the /groups feature work that fences `groups` out)

## Decision

**Two decisions, one slice.**

1. **Scope phase 4 by measurement, not by memory.** A fresh structural census of the post-cut
   `app.py` plus a referrer walk over every route establishes that the *published list* was
   exhausted while the *file* was not: **fourteen** page families remain, worth **2,709 mover
   lines** (2,279 excluding `groups`, which stays fenced while ADR-0343 feature work is queued
   against it). Phase 4 is those families, priced below and taken zero-descent-first.
2. **Extract the /risks page family — verbatim — into `web/risks.py` (349 lines): EIGHT
   functions and FOUR constants in ONE contiguous block** (app.py 7458–7759), **no descent**.
   `app.py` **10,505 → 10,215** (wc-truth). `LAYER_ORDER` becomes `… → compare → risks → app`;
   `risks.py` joins pyproject's per-file E501 list; `EXTRACTED`, `LAYER_ORDER`, `VIEW_MODULES`
   and both whole-view-layer guard tuples gain `"risks.py"`.

## The scoping census — what "exhausted" actually meant

`app.py` at 10,505 lines, by structure:

| | names | ast lines |
| --- | ---: | ---: |
| module-level imports | — | 585 |
| module-level functions | 106 | 3,806 |
| module-level classes | 2 | 53 |
| module-level assignments | 35 | 105 |
| `create_app` (lines 1294–6796) — **135 routes**, 153 direct nested defs | 1 | 5,503 |

So the routes are **52%** of the file and the module-level helpers **36%**. ADR-0382's claim was
that the *published* page-family list was exhausted, and that was true. The inference a reader
could have drawn — that the page families were gone — is not: a referrer walk seeded on every
route's full surface (page + `/api` + `/export`) finds fourteen of them.

| family | routes | movers | mover lines | route-only shared | descent? |
| --- | ---: | ---: | ---: | ---: | ---: |
| `groups` *(fenced, ADR-0343)* | 2 | 8 | 430 | 0 | 0 |
| `settings` | 4 | 5 | 318 | 1 | 3 |
| **`risks`** | **2** | **8** | **275** | **0** | **0** |
| `cei` | 3 | 4 | 262 | 2 | 2 |
| `ribbon` | 3 | 4 | 234 | 0 | 1 |
| `briefing` | 3 | 4 | 194 | 0 | 4 |
| `volatility` | 2 | 2 | 192 | 0 | 1 |
| `standards` | 1 | 4 | 161 | 0 | 0 |
| `scorecards` | 3 | 5 | 151 | 1 | 0 |
| `card` | 1 | 2 | 140 | 1 | 0 |
| `curves` | 3 | 3 | 131 | 0 | 1 |
| `wbs` | 3 | 3 | 110 | 0 | 0 |
| `workbench` | 5 | 1 | 67 | 0 | 1 |
| `brief` | 2 | 1 | 44 | 0 | 0 |

"route-only shared" is a name reached from the family whose only outside referrers are *routes*
— never a descent (ADR-0378). "descent?" counts names an outside **mover** also calls; those are
the adjudications a slice has to price. `risks` is the largest family with **both** columns zero,
which is why it is slice 19 and not `settings` (318 lines but three descents into the AI-backend
helpers) or `cei` (262 with `_sources_line` shared with `_scorecards_body`).

## The closure: 2.27× the prefix, and four constants the walk could not see

| | names | ast lines |
| --- | ---: | ---: |
| prefix census (`risks`) | 2 | 121 |
| closure over `/risks` + the export route | **8** | **275** |
| — of which **movers** | **8** | **275** |

**2.27× by lines, 4.0× by names.** The matrix, the ranking, the finding card, its quantified
read, the band classifier and the working-days formatter carry no `risks` prefix at all —
`_risk_matrix`, `_risk_ranking`, `_finding_card`, `_finding_quant`, `_risk_band`, `_wd`. A queue
built on the prefix would have priced this family at 121 lines and cut less than half of it.

**A closure computed over `def`s alone strands the constants the block owns.** The walk's graph
is functions calling functions, so `_IMPACT_LABELS`, `_LIKELIHOOD_LABELS`, `_RISKS_EXPORT` and
`_RISKS_XLSX_TITLE` — four module-level assignments physically inside the block and read only by
it — are invisible to it. They were caught by the separate free-name pass, which classifies
every name the movers reference as import / constant / app-level function / app-level
*assignment*, and by extending the region by eye (`_RISKS_EXPORT` sits under a three-line `#:`
doc-comment block the AST span does not include). Left behind they would have produced a
`NameError` at first render, not an import error — the cheap failure, but only by luck.

Everything else resolves to an **import**: `_e`, `_expandable_more` (chrome); `_panel_head`,
`_shell_tools` (components); `Schedule` (model); `Category`, `Finding`, `SEVERITY_ORDER`,
`Severity` (engine.recommendations); `Narrative` (ai.citations); `quote` (stdlib). Nothing to
descend into, nothing to adjudicate.

**The export route contributes NO movers, measured.** `export_risks`'s app-level callee set is
empty: it re-derives its own findings (`recommend` → `findings_table` → `_export_response`)
rather than calling `_risks_body`. That is what licenses a page-only probe anchor here —
ADR-0378's trap is checked off, not waved past. Streak: five consecutive.

## Pre-flight probe — 8/8 render-proven, ZERO dark (tenth consecutive slice)

Span-scoped: anchor count asserted `== 1` in-file (five for `_risk_band`, one each elsewhere),
each anchor line asserted **inside** the member's own AST span, **additive** markers only,
restores md5-verified.

| member | labels moved (of 648) |
| --- | --- |
| `_risk_band` · `_wd` · `_finding_quant` · `_finding_card` | **4 each** — `/risks` at all four loaded stages |
| `_risk_matrix` · `_risk_ranking` · `_risks_section` · `_risks_body` | **4 each** — same four |

`[empty] GET /risks` correctly does **not** move: with no schedules the route returns its "Load a
schedule to see risks, issues & opportunities" placeholder and calls no member. `_wd` — the
3-line formatter, the likeliest dark member in the family — fires, so the TP4 findings do carry
quantified float/exposure fields and no stronger-anchor round (ADR-0373) was needed.

## Proof

- **The oracle survived the container.** ADR-0382's committed corpus rebuilt the inherited
  fingerprint on a cold clone with no reconstruction: `[empty]` 60 `{200:41,400:17,422:2}` and
  four loaded stages of 147 `{200:124,404:4,422:19}`, 648 total. Determinism ×2 separate
  processes: **0 flapping**.
- **Per-region byte-identity: IDENTICAL** — asserted in-script before the write, re-read from
  disk after, and a third time after `ruff --fix` + `ruff format` (sha256 `154962d7e95b`,
  unchanged across all three).
- **648/648 byte-identical**, pristine vs cut; the full fingerprint held on the cut tree.
- **Falsified in the new location: 8/8 EXACT label lists** — each member re-mutated inside
  `risks.py` with the probe's own anchors moved exactly its pre-flight list; every anchor
  additionally asserted **absent** from post-cut `app.py` (the code moved, it was not copied).
- **Multiset: 59 added / 0 removed — ZERO code lines removed.** Every added line is `risks.py`'s
  docstring, its import block and the twelve re-exports plus their ADR comment.

## The sweeps — and a sweep that reported ZERO and was wrong, again

- **Dropped-import sweep: THREE dropped.** `ruff --fix` removed `SEVERITY_ORDER`, `Category` and
  `Finding` from `app.py` — the eight movers were app.py's last consumers of all three.
  Adjudicated safe by an AST, alias-agnostic check: **zero** callers reach any of them through
  `web.app` (neither `from schedule_forensics.web.app import <name>` nor `<alias>.<name>` on a
  module bound to `web.app`), while a positive control (`create_app`, 177 files) proves the
  sweep runs. No re-export is owed: the three are *imports* in `risks.py`, not names it defines.
- **The first run of that sweep reported ZERO — and was wrong.** It was a line-prefix regex over
  the diff (`^-from` / `^-import`), and every one of the three drops came out of a
  *parenthesized* import block, so the removed lines read `-    Category,` and matched nothing.
  The error surfaced only because an independent AST pass compared the two trees' import **sets**
  and found the names gone. ADR-0378's lesson was "sweep by bare NAME, not a module-qualified
  regex"; this is the same lesson one level up — the *shape* of a sweep can be wrong even when
  its pattern is right, and a diff is the wrong surface for a question about imports.
- **Monkeypatch / setattr sweep (AST, alias-agnostic): ZERO hits** on all twelve moved names.
  196 setattr-style calls found across 498 files; ADR-0378's control (`compute_activity_makeup`
  at `test_manifest_projection_memo.py:74`) reproduces. **No ADR-0297 trap** — the caller
  `risks_view` stays in `app.py`, so patching `app_mod._risks_body` still rebinds the global the
  caller reads.
- **Import sweep: three live readers, zero repoints.** `tests/web/test_risks.py:83` imports
  `_finding_quant`, `_risk_matrix` and `_risk_ranking` from `web.app`; the `X as X` re-export
  keeps them working, and leaving them un-repointed makes them a standing live check of the
  re-export contract.
- **Source-text sweep: five genuine view-source readers, zero repoints.** The risks region
  carries no `_TS_CAPTION_MARK`, so `test_axis_titles.py`'s app.py-reading guard is unaffected;
  `test_gantt_find_coverage.py` reads `driving.py`. The two whole-view-layer guards gain
  `"risks.py"` as a *registration*, which the contract test forces.

## Verification

Six mutations, each an exact-match splice landed-count-asserted in-script, each run against the
WHOLE module (no `-k`), each restored from a scratchpad copy (never `git checkout`), md5-verified,
each module re-run green after restore. Mutations 3–4 are the enumeration guard's twenty-ninth
and thirtieth consecutive live catches.

| mutation | named failure | split |
| --- | --- | ---: |
| re-export deleted from `app.py` | `…reexported_by_app…[risks.py]` | 1 / 45 |
| deferred upward import in `_risks_body` (in-body) | `…imports_downward[risks.py]` | 1 / 45 |
| `"risks.py"` dropped from `test_bar_drill` | `…read_the_whole_view_layer[test_bar_drill.py]` | 1 / 45 |
| `"risks.py"` dropped from `test_presentation_fixes` | `…[test_presentation_fixes.py]` | 1 / 45 |
| `"&mdash;"` sentinel planted in `risks.py` (in-body) | `test_no_mdash_entity_sentinel_values…` | 1 / 5 |
| second `drilldown.js` include in `risks.py` (in-body) | `test_drilldown_runtime_is_loaded_globally…` | 1 / 6 |

## Deliberately NOT done

- **No second slice.** The census names thirteen more families; taking one per slice with the
  full instrument is what has kept every slice byte-identical, and a scoping ADR that also
  cut two families would have priced neither properly.
- **`export_risks` was not refactored to call `_risks_body`.** It duplicates the findings
  derivation, which is a real (small) redundancy — but converging them changes behaviour and is
  not a split.
- **`groups` (430 mover lines) stays outside the candidate list** while ADR-0343 feature work is
  queued against it — unchanged from phase 3.
- `CLAUDE.md`'s phase-3 + E501 prose still lags by design (the standing doc-drift sweep owns it;
  `risks.py` now also joins the unpatched E501 list there); `risks.py` DID join pyproject's.

## Consequences

- **Phase 4 exists, and it is priced.** Thirteen families / 2,279 mover lines remain outside
  `groups`. The zero-descent set — `standards` (161), `wbs` (110), `brief` (44), plus
  `scorecards` (151) and `card` (140) whose only shared names are route-only — is the natural
  order for the next slices; `settings`, `briefing` and `cei` carry real descents and should be
  priced again when their turn comes, not assumed from this table.
- **A queue is a record of what was noticed, not of what exists.** "The published list is
  exhausted" was true and was still the wrong stopping signal. Re-derive the population from the
  code before concluding a phase is over.
- **Extend the closure to module-level assignments.** The function-call graph cannot see the
  constants a block owns; the free-name pass is what catches them, and the `#:` doc-comment
  block above a constant is outside its AST span (standing trap 21).
- **The oracle's maintenance contract held its first cold-start test.** ADR-0382 committed the
  corpus one session before a fresh container needed it, and it rebuilt with no prose
  archaeology. That is the whole return on writing an instrument down.
