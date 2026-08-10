# ADR-0382 — Phase 3 slice 18: the /compare family, and the oracle that stopped decaying

- **Status:** Accepted
- **Date:** 2026-08-10
- **Continues:** ADR-0350 (the kernel), ADR-0351 (the descent rule — *not* fired), ADR-0352 (the
  span-scoped pre-flight probe), ADR-0365 (closure-before-cut), ADR-0372 (the oracle recipe +
  the three normalizers), ADR-0375 (the title-stripped TP4 pool), ADR-0377 (the stage-scoped
  fingerprint; enumerate `app.routes` by method + path; a silent normalizer is a flap factory),
  ADR-0378 (sweep by bare NAME; the route-only-referrer rule; a census can be exact and still
  not be membership), ADR-0379 (the `[resloaded]` stage), ADR-0380 (mutate by offset, not
  permutation), **ADR-0381 (the instrument that did not survive the container — this ADR closes
  its open item)**
- **Related:** ADR-0208 (the "What changed" header this family owns), ADR-0298 (the chapter-10
  body), ADR-0371 (the pair scope both routes read), ADR-0104 (the session filter a variant
  exercises)

## Decision

**Two decisions, one slice.**

1. **Extract the /compare page family — verbatim — into `web/compare.py` (218 lines): TWO names
   in ONE contiguous block** (app.py 7762–7929): `_what_changed_header` and `_compare_body`.
   **No descent.** `app.py` **10,675 → 10,505** (wc-truth). `LAYER_ORDER` becomes
   `… → path → compare → app`; `compare.py` joins pyproject's per-file E501 list; `EXTRACTED`,
   `LAYER_ORDER`, `VIEW_MODULES` and both whole-view-layer guard tuples gain `"compare.py"`.
   **This exhausts the published phase-3 page-family list.**
2. **Commit the render oracle** — ADR-0381's open item — as `tests/web/oracle_corpus.py`
   (the builder), `tests/guards/render_oracle_labels.txt` (the corpus, by name) and
   `tests/guards/test_render_oracle_corpus.py` (four guards). The instrument is no longer
   re-derived from prose every container.

## The closure: exact, and exact for the right reason

| | names | ast lines |
| --- | ---: | ---: |
| prefix census (the queue's number) | 2 | 166 |
| closure over `/compare` + the export route | **2** | **166** |
| — of which **movers** | **2** | **166** |

Ratio **1.00×** on both — the third census-exact closure in phase 3, and like ADR-0381's (but
unlike ADR-0378's) nothing was hand-folded into the queue first. Every name the two members
touch resolves to an **import**: `_e` (chrome); `_metric_help_cell`, `_pair_prov_chip`,
`_panel_head`, `_shell_tools`, `_stat_cards`, `_status_stack` (components); `Schedule` (model);
`CPMResult`, `offset_to_datetime`, `diff_versions`, `detect_manipulation`,
`trend_across_versions`, `compute_net_finish_impact` (engine). Nothing to descend into, and no
shared name to adjudicate.

**The export route contributes NO movers, measured rather than assumed.** `export_compare`'s
app-level callee set is **empty**: it re-derives the signals itself (`detect_manipulation` →
`findings_table` → `_export_response`) instead of calling `_compare_body`. That is what licenses
a page-only probe anchor here — ADR-0378's trap (a page-only anchor understates an
export-feeding member) is *checked off*, not waved past. Streak: four consecutive.

`_sources_line`, `_export_bar`, `_skipped_notice`, `_focus_panel` and `_pair_versions` are
called by the **route**, not by a mover. Routes live in `create_app` and import downward, so a
route-only referrer never forces a descent (ADR-0378).

## The oracle, committed — and what committing it immediately found

ADR-0381 measured the decay (648 → 592 on a fresh container) and named the fix. Rebuilt here
from the route surface and **written down**:

| | inherited (ADR-0380) | rebuilt + committed here |
| --- | ---: | ---: |
| `[empty]` | 60 · `{200:41, 400:17, 422:2}` | **60 · `{200:41, 400:17, 422:2}`** |
| each loaded stage | 147 · `{200:124, 404:4, 422:19}` | **147 · `{200:124, 404:4, 422:19}`** |
| total | 648 | **648** |

Every stage count and every histogram bucket reproduces the inherited numbers exactly. **This
is shape identity, not proven label-for-label recovery** — the original list was never recorded,
so it cannot be diffed. Matching five stage counts and three buckets is far stronger evidence
than ADR-0381's `[empty]`-only match, but the honest claim is "same shape", and ADR-0381's
warning stands: a corpus with the same *number* and different *content* is the worst outcome.
What removes the risk permanently is not the match — it is that the list is now **in the repo**.

Committing it forced three findings that prose had been hiding:

1. **Six of twelve hand-authored variants were decoration.** Drafted from the ADRs' prose
   (`/evolution?view=tiers`, `/resources?field=Status`, `/path?target=22`, `/api/sra/grid`,
   `/sra/ssi/save`, …), they rendered **byte-identical to their bare label**: FastAPI ignores an
   undeclared query parameter, so the URL reached no new code while inflating the count. Rewritten
   against the actual route **signatures** (`tier`, `ignore_constraints`/`ignore_leveling`,
   `cf_a`/`cf_b`, `bucket`, `uids`, `iterations`/`distribution`, `target`), all ten are distinct.
   *A variant that reaches no new code is worse than a missing one — it keeps the label count
   looking healthy while the coverage is gone.* Guarded now.
2. **The launch-token normalizer had been pinning one of TWO spellings.** The recipe describes
   `{hex16}.{wipe_gen}`; the page carries it as `<meta name=sf-launch content="…">` and
   `/api/whoami` carries it as a `"launch_token"` JSON key. Rebuilt against the page surface
   alone it left **five labels flapping** — one `/api/whoami` per stage — adjudicated by payload
   diff before the harness was touched, exactly as the standing rule requires.
3. **`[empty]` deliberately excludes the `{name}` labels.** With no schedules loaded every
   `{name}` URL 404s about the same missing file, which measures the fixture pool rather than
   the code. Written down in the builder so the next rebuild cannot "helpfully" add them.

The four committed guards, each **proven able to fail** (mutate → the named test fails →
restore → green): the label list is pinned; the `[empty]` fingerprint is pinned; no variant may
be decoration; every must-fire normalizer still fires.

## Pre-flight probe — 2/2 render-proven, ZERO dark members (ninth consecutive slice)

Span-scoped: anchor count asserted `== 1` in-file, anchor line asserted **inside** the member's
own AST span, **additive** markers only (ADR-0380), restores md5-verified.

| member | labels moved (of 648) |
| --- | --- |
| `_what_changed_header` | **4** — `/compare` at all four loaded stages |
| `_compare_body` | **4** — `/compare` at all four loaded stages |

`[empty] GET /compare` correctly does **not** move: with fewer than two schedules the route
returns its "Load at least two versions to compare" placeholder and calls neither member. The
render condition reads back exactly as the route states it (ADR-0374).

## Proof

- **Per-region byte-identity: IDENTICAL** — asserted in-script before the write, re-read from
  disk after, and a third time after `ruff --fix` + `ruff format` (sha256 `b667721aebe1…` /
  `ea823b325325…`, unchanged across all three).
- **648/648 byte-identical**, pristine vs cut; the full fingerprint held on the cut tree.
- **Falsified in the new location: 2/2 EXACT label lists** — each member re-mutated inside
  `compare.py` with the probe's own anchors moved exactly its pre-flight list; each anchor
  additionally asserted **absent** from post-cut `app.py` (the code moved, it was not copied).
- **Multiset: 49 added / 1 removed — ZERO member code lines removed.** Every added line is
  `compare.py`'s header/imports plus the two re-exports; the single removal is an import name,
  below.

## The sweeps — and the first slice where the dropped-import sweep found drops

- **Dropped-import sweep (bare NAME, ADR-0378): THREE dropped**, ending the zero-drop run.
  `ruff --fix` removed `compute_net_finish_impact`, `diff_versions` and `trend_across_versions`
  from `app.py`, because the two moved members were their only consumers *in app.py*. Adjudicated
  safe by an AST, alias-agnostic check: **zero** callers reach any of the three through
  `web.app` — neither `from schedule_forensics.web.app import <name>` nor `<alias>.<name>` on a
  module bound to `web.app` — while a positive control (`create_app`, 184 files) proves the
  sweep runs. Every real consumer imports from the engine directly. The contract test does not
  require a re-export here: the three are *imports* in `compare.py`, not names it defines.
- **Monkeypatch / setattr sweep (AST, alias-agnostic): ZERO hits** on both moved names. 193
  setattr-style calls found across 362 test files; ADR-0378's control (`compute_activity_makeup`
  at `test_manifest_projection_memo.py:74`) reproduces. **No ADR-0297 trap** — the caller
  `compare` stays in `app.py`, so patching `app_mod._compare_body` would still rebind the global
  the caller reads.
- **Source-text sweep, three detectors, and a filter that had to be sharpened.** The first pass
  called 178 files "source-text readers" because nearly every test uses `__file__` to locate
  fixtures, and produced 665 "candidates" — common words like `project` and `critical` that
  happen to appear in the moved text. Re-run requiring an actual view-source idiom
  (`getsource` · `<module>.__file__` · `with_name("*.py")` · a literal `"app.py"` · `web/"*.py"`)
  **beside** a real `read_text`/`read_bytes`/`getsource` call, it finds **6** genuine readers —
  including `test_gantt_find_coverage.py`, the file whose own comment documents this blind spot.
  Their nine ≥12-char candidate literals are all `"schedule_forensics"` used as a **path
  segment**, not an assertion about source. **Zero source-text repoints.**

## Verification

Six mutations, each an exact-match splice landed-count-asserted in-script, each run against the
WHOLE module (no `-k`), each exactly ONE named failure, each restored from a scratchpad copy
(never `git checkout`), md5-verified, each module re-run green after restore.

| mutation | named failure | split |
| --- | --- | ---: |
| re-export deleted from `app.py` | `…reexported_by_app…[compare.py]` | 1 / 42 |
| deferred upward import in `_compare_body` (in-body) | `…imports_downward[compare.py]` | 1 / 42 |
| `"compare.py"` dropped from `test_bar_drill` | `…read_the_whole_view_layer[test_bar_drill.py]` | 1 / 42 |
| `"compare.py"` dropped from `test_presentation_fixes` | `…[test_presentation_fixes.py]` | 1 / 42 |
| `"&mdash;"` sentinel planted in `compare.py` (in-body) | `test_no_mdash_entity_sentinel_values…` | 1 / 4 |
| second `drilldown.js` include in `compare.py` (in-body) | `test_drilldown_runtime_is_loaded_globally…` | 1 / 5 |

Mutations 3–4 are the enumeration guard's **twenty-seventh and twenty-eighth consecutive live
catches**. Four further mutations proved the new oracle guards (above), for **ten** falsification
runs this slice.

A harness bug was caught before it produced a false finding, again: the mutation runner read
pytest's `FAILED …` lines with `split(" ")[0]`, which is the literal word `FAILED`, so the first
falsification reported NOT PROVEN against a guard that had failed correctly. *A parser that
cannot name the failing test cannot enforce the named-failure rule* (standing trap 32) — the
rule's own instrument needs the same scepticism as the code under it.

## Deliberately NOT done

- **The corpus was not padded, and the shape match was not claimed as recovery.** 648 = 648 is
  reported as shape identity with the reason it cannot be more.
- **`export_compare` was not refactored to call `_compare_body`.** It duplicates the signal
  derivation, which is a real (small) redundancy — but converging them changes behaviour and is
  not a split.
- `groups` (430 by prefix) stays outside the phase-3 candidate list while ADR-0343 feature work
  is queued against it.
- `CLAUDE.md`'s phase-3 + E501 prose still lag by design (the standing doc-drift sweep owns
  them — `compare.py` now also joins the unpatched E501 list there); `compare.py` DID join
  pyproject's.

## Consequences

- **The published phase-3 page-family list is exhausted.** `app.py` is 10,505 lines, down from
  16,685 when phase 3 began (ADR-0372). What remains in it is routes (`create_app`), the
  remaining shared helpers, and `groups`. The next monolith decision is a *scoping* decision,
  not another slice off a known list — take a fresh prefix census against the post-cut file and
  price the candidates by referrer walk before committing to a phase 4.
- **The oracle is now a repo asset with a maintenance contract.** Adding a route changes the
  label list and the pin test says so; regenerate it in the same commit with
  `python tests/web/oracle_corpus.py --labels > tests/guards/render_oracle_labels.txt`. The
  numbers a future slice inherits are `[empty]` 60 `{200:41,400:17,422:2}` and four loaded
  stages of 147 `{200:124,404:4,422:19}` — **and, for the first time, the labels themselves.**
- **A hand-authored oracle label must be checked against the route SIGNATURE.** Prose names a
  variant; only the signature says whether the parameter exists. Half of a prose-derived variant
  set was inert, and nothing would have reported it.
- **Ending a zero-finding streak is a result.** Sixteen slices reported "0 dropped imports"; the
  seventeenth found three, because this family was the last app.py consumer of three engine
  functions. A streak is a property of the code met so far, not evidence the sweep is redundant.
