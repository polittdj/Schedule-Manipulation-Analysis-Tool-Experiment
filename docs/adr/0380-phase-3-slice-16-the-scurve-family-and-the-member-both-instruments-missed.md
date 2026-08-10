# ADR-0380 — Phase 3 slice 16: the /scurve family, and the member BOTH instruments missed

- **Status:** Accepted
- **Date:** 2026-08-10
- **Continues:** ADR-0350 (the kernel), ADR-0351 (the descent rule — *not* fired this slice),
  ADR-0352 (the span-scoped pre-flight probe), ADR-0365 (closure-before-cut), ADR-0372 (the
  oracle recipe + the three normalizers), ADR-0373 (**the stronger-anchor round — fired here**),
  ADR-0374 (the render-condition rule), ADR-0375 (the title-stripped TP4 pool), ADR-0377 (the
  stage-scoped fingerprint), ADR-0378 (sweep by bare NAME; the route-only-referrer rule),
  ADR-0379 (extend the oracle, never re-base it; prefer a parser to a regex)
- **Related:** ADR-0297 (the phase-1 patch-the-module-that-CALLS trap — *not* fired here),
  ADR-0104 (the session-wide filter the `[grouped]` labels exercise)

## Decision

**Extract the /scurve page family — verbatim — into `web/scurve.py` (283 lines): SEVEN names in
TWO contiguous blocks** (app.py 8324–8530 and 9016–9040): `_scurve_filter_fields`,
`_pair_criteria`, `_scurve_status_point`, `_scurve_interpretation`, `_scurve_header`,
`_scurve_body`, `_scurve_data`. **No descent.** `app.py` **11,095 → 10,871** (wc-truth).
`LAYER_ORDER` becomes `… → performance → resources → scurve → app`; the re-export block lands
immediately below resources' (isort: `resources` < `scurve` < `sra`); `scurve.py` joins
pyproject's per-file E501 list (two interpretation strings were already over-long inside app.py's
exempt region — verbatim outranks re-wrapping); `EXTRACTED`, `LAYER_ORDER`, `VIEW_MODULES` and
both whole-view-layer guard tuples gain `"scurve.py"`.

## The closure: the census misses a member, and it is the interesting one

| | names | ast lines |
| --- | ---: | ---: |
| prefix census (the queue's number) | 6 | 212 |
| closure over `/scurve` + `/api/scurve` + the export route | 13 | 250 |
| — of which **movers** | **7** | **222** |

Ratio **1.05× on lines, 1.17× on names**. The extra name is **`_pair_criteria`** — the cf/cv
validator that turns the S-curve's own per-chart filter into `(field, value)` criteria. It is
reachable only from `/api/scurve`, carries no `_scurve` prefix, and no prefix sweep can ever
find it. It sits physically *inside* the family's block, between `_scurve_filter_fields` and
`_scurve_status_point` — the author put it there; only the walk says so.

**No descent, adjudicated by referrer.** The walk surfaced six shared names, every one pinned to
`app.py`:

| name | pinned by |
| --- | --- |
| `_parse_uid` (9) | routes of /driving, /evolution, /margin, /sra, /trend + `_parse_uid_list` |
| `_parse_uid_list` (13) | `_drill_uid_set` and `_import_risk_register` — **non-route** referrers |
| `_parse_track_uids` (3) | `cei_json` / `cei_view` — routes of ANOTHER family |
| `_MAX_TRACK_UIDS` (1) | only `_parse_track_uids`, which stays (cohesion) |
| `_CF_QUERY`, `_CV_QUERY` (1 each) | route-signature defaults — see below |

**`_CF_QUERY` / `_CV_QUERY` stay, on zero precedent.** They are FastAPI `Query` singletons whose
only purpose is to be default values in `scurve_json`'s signature, and they are referenced by no
mover — only by the route. Across **220 names** already extracted over **fifteen** slices, **not
one** route-signature default has ever lived in an extracted module (checked mechanically, not by
memory). Moving them would have bought two lines and invented a coupling pattern the split has
never used. Route plumbing stays with the routes; presentation moves.

**The export route contributes NO movers** — `export_scurve` builds its table straight from
`compute_s_curve`. The streak ADR-0378 broke at five and ADR-0379 resumed now stands at **two
consecutive**.

## The headline: the census's blind spot and the oracle's were the SAME member

`_pair_criteria` is missing from the prefix census because it lacks the prefix. It was *also*
invisible to the inherited 644-label oracle — for an unrelated reason: **no inherited label ever
supplies `cf`/`cv`**, so the member returns an empty criteria list on every one of the 648
renders and does no work. Two independent instruments, two independent causes, **one member**.

That is not a coincidence, and it is the lesson: both blindnesses have the same root — the member
is off the obvious path. *The name a finder cannot see is disproportionately likely to be the
name the instrument cannot exercise, so a census miss is a warning about the ORACLE too.* Had the
walk not found it, nothing downstream would have complained: it would have been cut (or left
behind) with a clean 648/648 byte-identity and a silent dark reading.

**The oracle was extended, not re-based** (ADR-0379's rule). One label was added —
`[scurve-filter] /api/scurve?cf&cv`, seeded from the first populated group field and asserted to
change the payload *before* being recorded — taking the corpus **644 → 648**. The inherited 644
are untouched and byte-comparable, so ADR-0377's fingerprint stays checkable as a subset, and it
reproduced **exactly** on the pristine tree before anything was cut:

| stage | n | histogram |
| --- | ---: | --- |
| `[empty]` | 60 | `{200:41, 400:17, 422:2}` |
| `[loaded]` / `[target]` / `[cleared]` / `[resloaded]` | 146 each | `{200:123, 404:4, 422:19}` |

4xx **69 loaded-stages · 88 inherited-all · 111 all-five** — reproduced on the nose, including
the `404:4` that ADR-0379 had to repair. The extension moves each loaded stage to 147 labels and
`200:124`; **the 4xx fingerprint is unchanged**, which is what proves the extension is purely
additive. Double-render determinism across two separate processes: **0 flapping**, at both 644
and 648.

## Pre-flight probe — 7/7 render-proven, ZERO dark members (seventh consecutive slice)

Span-scoped anchor mutations: anchor count asserted `== 1` in-file, anchor line asserted
**inside** the member's own AST span, value-level markers only, restores md5-verified.

| member | labels moved (of 648) |
| --- | --- |
| `_scurve_filter_fields` | **4** — `/scurve`, all four loaded stages |
| `_pair_criteria` | **4** — `[scurve-filter] /api/scurve`, all four (the new label ONLY) |
| `_scurve_status_point` | **4** — `/scurve`, all four |
| `_scurve_interpretation` | **4** — `/scurve`, all four |
| `_scurve_header` | **4** — `/scurve`, all four |
| `_scurve_body` | **4** — `/scurve`, all four |
| `_scurve_data` | **8** — `/api/scurve` **and** `[scurve-filter]`, all four |

`_pair_criteria`'s entire proven reach is the label this slice added. Without the extension it
reads 0/648 — a dark member with a clean bill of health.

### The stronger-anchor round: a PERMUTATION has fixed points

`_scurve_status_point` first read **3/4**: `[target] /scurve` did not move. Adjudicated by payload
before anything was touched — under the target scope the page renders **100% finished against
100% planned**, and the first anchor was a *swap* of `(actual, planned)`. A permutation applied to
equal values is the identity, so the label was invariant to that mutation for reasons that were
arithmetic, not reach. Re-run with an **additive** marker (`actual + 11.0`), the member reads
**4/4**.

*Prefer an offset to a permutation.* A swap/reorder mutation reads dark exactly where the values
coincide — which is precisely where a scoped or fully-progressed population puts them. This is
ADR-0373's stronger-anchor round, fired for a new reason (arithmetic invariance rather than a
weak anchor), and it generalises: **the mutation must have no fixed points on the data the oracle
renders.**

## Proof

- **Per-region byte-identity: IDENTICAL** — asserted in-script before the write, from disk after,
  and a third time after `ruff --fix` dropped app.py's now-unused `SCurve` import
  (`sha256 4811f34f46cb…` on both sides); `ruff format --check` reported zero reformats over 943
  files at cut time (944 at the final gate).
- **648/648 byte-identical**, pristine vs cut; the full fingerprint held on the cut tree.
- **Falsified in the new location: 7/7 EXACT label lists** — every member re-mutated in
  `scurve.py` with the probe's own anchors, moving exactly its pre-flight list; every anchor
  additionally asserted **absent** from post-cut `app.py`; restores md5-verified.

## The sweeps

- **Dropped-import sweep (by bare NAME, ADR-0378): one name, `SCurve` — 0 readers** anywhere in
  `src/` or `tests/` outside the engine module that defines it and the new module that uses it.
  The positive control confirms the sweep can see the name where it does exist.
- **Monkeypatch + attribute sweep (AST, alias-agnostic, ADR-0379): ZERO hits** on the 19 names
  `scurve.py` binds. The sweep finds **192** `setattr` calls across `tests/` and reproduces
  ADR-0378's control (`compute_activity_makeup`, patched across wrapped lines at
  `test_manifest_projection_memo.py:74`). The alias census again makes the bare-name case:
  `appmod` 18 · `app_module` 15 · `app_mod` 3. **No ADR-0297 trap this slice** — the family's
  engine entry point `compute_s_curve` is called by the ROUTES, which stay in `app.py`, and every
  test that touches it imports it straight from `schedule_forensics.engine.s_curve`.
- **Source-text sweep:** six tests read a Python view module by path; exactly one literal in the
  moved text is absent from post-cut `app.py` — `'scurve.js'` at `test_dd_line_ledger.py:74`.
  **Adjudicated false:** that is an entry in the DD-line ledger keyed by `(static JS module,
  line)`, naming `static/scurve.js`; it matched only because the moved HTML contains
  `<script src="/static/scurve.js">`. **Zero source-text repoints.**

## Verification

Six mutations, each an exact-match splice landed-count-asserted in-script, each run against the
WHOLE module (no `-k`), each exactly ONE named failure, each restored from a scratchpad copy
(never `git checkout`), md5-verified.

| mutation | named failure | split |
| --- | --- | ---: |
| re-export deleted from `app.py` | `…reexported_by_app…[scurve.py]` | 1 / 39 |
| deferred upward import in `_scurve_body` (in-body) | `…imports_downward[scurve.py]` | 1 / 39 |
| `"scurve.py"` dropped from `test_bar_drill` | `…read_the_whole_view_layer[test_bar_drill.py]` | 1 / 39 |
| `"scurve.py"` dropped from `test_presentation_fixes` | `…[test_presentation_fixes.py]` | 1 / 39 |
| `"&mdash;"` sentinel planted in `scurve.py` (in-body) | `test_no_mdash_entity_sentinel_values…` | 1 / 5 |
| second `drilldown.js` include in `scurve.py` (in-body) | `test_drilldown_runtime_is_loaded_globally…` | 1 / 6 |

Mutations 3–4 are the enumeration guard's **twenty-third and twenty-fourth consecutive live
catches**.

## Deliberately NOT done

- **`_CF_QUERY` / `_CV_QUERY` were NOT moved** (above): route-signature plumbing, zero precedent.
- **The `[scurve-filter]` label does not replace anything.** Keeping the inherited 644
  byte-comparable is what let ADR-0377's fingerprint act as a self-check on a corpus this slice
  also grew.
- **`_parse_track_uids` was NOT descended into a shared module.** It is shared with /cei; when
  that family is cut, its own closure will make the call.
- `groups` (430 by prefix) stays outside the phase-3 candidate list while ADR-0343 feature work
  is queued against it.
- `CLAUDE.md`'s phase-3 + E501 prose still lag by design (the standing doc-drift sweep owns them
  — `scurve.py` now also joins the unpatched E501 list there); `scurve.py` DID join pyproject's.

## Consequences

- The remaining slice queue, by the post-cut prefix census (wc-truth; each family still owes its
  OWN closure before cutting; membership named because the prefix sweep is a finder, not the
  definition): **path 194** (incl. `_what_drives_header` 80) · **compare 166** (incl.
  `_what_changed_header` 79).
- **The oracle is now 648 labels.** Every future slice inherits `[scurve-filter]`; the 4xx
  fingerprint to reproduce is unchanged at **69 loaded / 88 inherited / 111 all-five**, with
  `[empty]` 60 `{200:41,400:17,422:2}` and four loaded stages of 147 `{200:124,404:4,422:19}`.
- **A census miss is a warning about the oracle, not just the queue.** The name a finder cannot
  see is the name an instrument is most likely unable to exercise — both follow from the member
  being off the obvious path. Check the second instrument whenever the first one misses.
- **Mutate by offset, not by permutation.** A swap has fixed points, and a scoped or
  fully-progressed population is exactly where the values coincide.
