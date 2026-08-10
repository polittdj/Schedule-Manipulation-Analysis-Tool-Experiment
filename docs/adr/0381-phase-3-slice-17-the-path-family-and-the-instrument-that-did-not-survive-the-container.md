# ADR-0381 — Phase 3 slice 17: the /path family, and the instrument that did not survive the container

- **Status:** Accepted
- **Date:** 2026-08-10
- **Continues:** ADR-0350 (the kernel), ADR-0351 (the descent rule — *not* fired), ADR-0352 (the
  span-scoped pre-flight probe), ADR-0365 (closure-before-cut), ADR-0372 (the oracle recipe +
  the three normalizers), ADR-0375 (the title-stripped TP4 pool), ADR-0377 (the stage-scoped
  fingerprint; enumerate `app.routes` by method + path), ADR-0378 (sweep by bare NAME; the
  route-only-referrer rule; a census can be exact and still not be membership), ADR-0379
  (the `[resloaded]` stage; extend, never re-base), ADR-0380 (mutate by offset, not permutation;
  a census miss is a warning about the oracle too)
- **Related:** ADR-0297 (patch the module that CALLS — *not* fired here), ADR-0199 (the
  "What drives the date" header this family owns)

## Decision

**Extract the /path page family — verbatim — into `web/path.py` (240 lines): TWO names in ONE
contiguous block** (app.py 6972–7167): `_what_drives_header` and `_path_body`. **No descent.**
`app.py` **10,871 → 10,675** (wc-truth). `LAYER_ORDER` becomes `… → resources → scurve → path`;
the re-export block sorts below `offload`'s (isort: `offload` < `path` < `performance`);
`path.py` joins pyproject's per-file E501 list; `EXTRACTED`, `LAYER_ORDER`, `VIEW_MODULES` and
both whole-view-layer guard tuples gain `"path.py"`.

## The closure: exact, and exact for the right reason

| | names | ast lines |
| --- | ---: | ---: |
| prefix census (the queue's number) | 2 | 194 |
| closure over `/path` + the export route | **2** | **194** |
| — of which **movers** | **2** | **194** |

Ratio **1.00×** on both. This is the second census-exact closure in phase 3, and unlike slice
14's (ADR-0378 — exact only because a prior ADR's ruling had already been hand-folded into the
queue) **nothing was folded in beforehand**: the walk was run cold and landed on the census.

The exactness is a *measurement*, not an assumption. The walk resolves every name each member
touches to its origin, and every one of them is an **import** from a module the split already
cut — `_e` (chrome); `_mdY`, `_panel_head`, `_shell_tools`, `_stat_cards`, `_status_stack`,
`_user_tip` (components); `_Analysis` (state); `Schedule` (model); `non_summary`,
`offset_to_datetime` (engine). There is no shared name to adjudicate and nothing to descend
into. The prefix remains a finder and the walk remains the definition (ADR-0378) — this family
simply had an author who kept it whole.

**The export route contributes NO movers.** `/export/{fmt}/path/{name}` is the *driving-path*
trace export despite its URL: it builds from `_driving_data` (`web.driving`),
`_optioned_versions` (`web.evolution`) and `driving_table` (`reports.tables`). The page's own
grid is client-side over `/api/driving`, which belongs to the driving family. The
export-contributes-no-movers streak, broken at five by ADR-0378 and resumed by ADR-0379, now
stands at **three consecutive**.

**A harness bug was caught before it produced a false finding.** The origin resolver first
reported `analysis` as a name `_what_drives_header` shares with `create_app` — because it
checked the nested-scope table *before* the local one, and `analysis` is the member's own
**parameter**. A parameter shadows an outer binding; ordering the checks the other way removed
the phantom. *Had it stood, the slice would have opened with a shared name that does not exist.*

## The headline: the instrument did not survive the container

Every slice since ADR-0372 has inherited an oracle described in prose and **built in the
scratchpad** — which a fresh container does not have. This session rebuilt it from the route
surface, and the rebuild is only *partly* faithful:

| | inherited (ADR-0380) | rebuilt here |
| --- | ---: | ---: |
| `[empty]` | 60 · `{200:41, 400:17, 422:2}` | **60 · `{200:41, 400:17, 422:2}`** ✅ |
| each loaded stage | 147 · `{200:124, 404:4, 422:19}` | 133 · `{200:111, **404:4**, 422:18}` |
| total labels | 648 | **592** |

**Everything the route surface determines reproduced exactly** — the `[empty]` stage on the
nose, the 60 parameterless GETs (`/openapi.json` among them, ADR-0377), and the `404:4` per
loaded stage that ADR-0379 had to repair. What did **not** reproduce is the ~14 hand-authored
variant labels per loaded stage (the three `/evolution` variants, `[ssi-api]`/`[ssi-grid]`/
`[ssi-save]`, the `[grouped]` pair, and others): **the ADRs name some of them in prose but never
record their URLs**, and prose is not a build recipe.

So the corpus this slice's claims rest on is **592 labels, and every number below carries that
scope** (ADR-0377's rule: a fingerprint is only as good as its stated scope). It is *not* the
648 — writing 648 would have been a number, not a measurement.

The lesson generalises past this slice: **an instrument that lives only in the scratchpad is
re-derived, not inherited, and it silently gets weaker every time.** Nine slices have each
rebuilt this oracle from the same prose; each rebuild can only recover what the prose pins.
The mechanical core is self-healing because it is derived from `app.routes`; the hand-authored
variants are not, and they are exactly the labels that were added to reach code the mechanical
core could not. *The parts of an oracle that were added because they were hard to reach are the
parts most likely to be lost.* Committing the harness (or at minimum its label list) is now the
open item — see Consequences.

Two normalizer notes, both inherited and both re-earned: the launch token fired on **150**
bodies per run, and `/api/system`'s live host telemetry is normalized by VALUE with the shape
kept. Every normalizer **raises on a zero match** (ADR-0377) — a silent one is a flap factory.
Double-render determinism across **two separate processes: 0 flapping** at 592.

**One family-specific extension, purely additive.** `export_path` declares `target: int =
Query(...)` — *required* — so the inherited `/export/{fmt}/path/{name}` label is a 422 that never
renders the export's body. Two labels were added (`[path-export]`, both formats, `?target=22`)
so the family's export route is exercised for real. The inherited labels are untouched and
byte-comparable, which is what proves the extension additive.

## Pre-flight probe — 2/2 render-proven, ZERO dark members (eighth consecutive slice)

Span-scoped anchor mutations: anchor count asserted `== 1` in-file, anchor line asserted
**inside** the member's own AST span, **additive** value markers only (ADR-0380 — a permutation
has fixed points), restores md5-verified.

| member | labels moved (of 592) |
| --- | --- |
| `_what_drives_header` | **4** — `/path` at all four loaded stages |
| `_path_body` | **4** — `/path` at all four loaded stages |

`[empty] GET /path` correctly does **not** move for either: with no schedules the route returns
its "Load a schedule" placeholder and calls neither member. That is the render condition
(ADR-0374) reading back exactly as the route states it.

## Proof

- **Per-region byte-identity: IDENTICAL** — asserted in-script before the write, re-read from
  disk after, and a third time after `ruff --fix` re-sorted the re-export block
  (`sha256 d85a3c7698e8…` on both sides). `ruff format --check`: **945 files, zero reformats**.
- **592/592 byte-identical**, pristine vs cut; the full fingerprint held on the cut tree.
- **Falsified in the new location: 2/2 EXACT label lists** — each member re-mutated in `path.py`
  with the probe's own anchors, moving exactly its pre-flight list; each anchor additionally
  asserted **absent** from post-cut `app.py`; restores md5-verified.
- **Multiset: 44 added / 0 removed — ZERO member code lines removed.** Every added line is
  `path.py`'s own header/imports plus the two re-exports.

## The sweeps

- **Dropped-import sweep (bare NAME, ADR-0378): zero dropped imports.** app.py's module-level
  import set went 443 → 445 (the two re-exports); `ruff --fix` removed nothing, because every
  name the moved code used is still used elsewhere in `app.py`. The set difference is
  positive-controlled, so "none" is a measurement.
- **Monkeypatch / setattr sweep (AST, alias-agnostic): ZERO hits** on both moved names. The
  sweep finds **192** `setattr` calls across `tests/` and reproduces ADR-0378's control
  (`compute_activity_makeup`). **No ADR-0297 trap this slice** — the caller is `path_view`,
  which stays in `app.py`, so a patch of `app_mod._path_body` would still rebind the global the
  caller reads. Nothing to repoint, and nothing that *needed* repointing.
- **Source-text sweep, widened.** `test_gantt_find_coverage.py` carries a comment from ADR-0351
  warning that a guard reaching source via `app_module.__file__` was invisible to a
  `grep -rln 'app\.py' tests/` sweep. The first pass here had that same blind spot; re-run with
  **three detectors** (path literal · `__file__` · `getsource`) it finds **203** readers and
  **zero** literals that both live in the moved region and are asserted by a reader.
  **Zero source-text repoints.** The four first-pass candidates were adjudicated false: three
  read the *rendered page* (`client.get("/path").text`) and one reads `static/path.js` — plus
  `"app.py"` itself, which matched only because this ADR's own module docstring names it.

## Verification

Six mutations, each an exact-match splice landed-count-asserted in-script, each run against the
WHOLE module (no `-k`), each exactly ONE named failure, each restored from a scratchpad copy
(never `git checkout`), md5-verified.

| mutation | named failure | split |
| --- | --- | ---: |
| re-export deleted from `app.py` | `…reexported_by_app…[path.py]` | 1 / 40 |
| deferred upward import in `_path_body` (in-body) | `…imports_downward[path.py]` | 1 / 40 |
| `"path.py"` dropped from `test_bar_drill` | `…read_the_whole_view_layer[test_bar_drill.py]` | 1 / 40 |
| `"path.py"` dropped from `test_presentation_fixes` | `…[test_presentation_fixes.py]` | 1 / 40 |
| `"&mdash;"` sentinel planted in `path.py` (in-body) | `test_no_mdash_entity_sentinel_values…` | 1 / 4 |
| second `drilldown.js` include in `path.py` (in-body) | `test_drilldown_runtime_is_loaded_globally…` | 1 / 5 |

Mutations 3–4 are the enumeration guard's **twenty-fifth and twenty-sixth consecutive live
catches**.

## Deliberately NOT done

- **The oracle was not padded back to 648.** The missing variants are not recoverable from the
  ADRs, and inventing replacements would have produced a corpus with the same *number* and
  different *content* — the worst of both worlds, since every future slice compares against it.
- **`export_path` was not renamed or moved**, despite its URL naming this page. It serves the
  driving family; renaming it is a route change, not a split.
- `groups` (430 by prefix) stays outside the phase-3 candidate list while ADR-0343 feature work
  is queued against it.
- `CLAUDE.md`'s phase-3 + E501 prose still lag by design (the standing doc-drift sweep owns
  them — `path.py` now also joins the unpatched E501 list there); `path.py` DID join pyproject's.

## Consequences

- The remaining slice queue, by the post-cut prefix census (wc-truth; each family still owes its
  OWN closure before cutting): **compare 166** (incl. `_what_changed_header` 79). After that the
  phase-3 page-family list as published is exhausted.
- **Commit the oracle harness, or accept a slowly-blinding instrument.** This is the first slice
  to measure the decay instead of inheriting it. The mechanical core is re-derivable from
  `app.routes` and healed itself; the hand-authored variants did not, and they were precisely
  the labels earlier slices added to reach code the mechanical core could not. Either the label
  list lands in the repo (a fixture, not prose) or every future slice silently re-derives a
  slightly smaller oracle and reports the shortfall as byte-identity.
- **A fingerprint carries its scope or it is decoration** (ADR-0377, sharpened): the number to
  reproduce is now `[empty]` 60 `{200:41,400:17,422:2}` — the part the route surface determines,
  which is the part that actually survives a rebuild.
- **Check the shadowing order in any origin resolver.** A parameter that shares a name with an
  outer binding will read as a shared name, and a phantom shared name costs a descent argument.
