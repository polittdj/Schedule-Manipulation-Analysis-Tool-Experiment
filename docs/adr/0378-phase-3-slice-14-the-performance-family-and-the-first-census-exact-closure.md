# ADR-0378 — Phase 3 slice 14: the /performance family, and the first census-exact closure

- **Status:** Accepted
- **Date:** 2026-08-09
- **Continues:** ADR-0350 (the kernel), ADR-0351 (the descent rule — *not* fired this slice),
  ADR-0352 (the span-scoped pre-flight probe), ADR-0365 (closure-before-cut), ADR-0372 (the
  oracle recipe + the three normalizers), ADR-0373 (the stronger-anchor round), ADR-0374 (the
  render-condition rule), ADR-0375 (the title-stripped TP4 pool), ADR-0377 (the 88/69
  stage-scoped fingerprint this slice re-used as a self-check)
- **Related:** ADR-0205 (the chapter-07 "How we execute" header), ADR-0261 P3 (the per-version
  memo `_perf_version_block` owns), ADR-0291 (the projection-memo spies), ADR-0298 (the panel
  contract the page's fourteen tiles wear)

## Decision

**Extract the /performance page family — verbatim — into `web/performance.py` (383 lines): four
names in one contiguous block** (app.py 10761–11092): `_perf_version_block`,
`_performance_data`, `_how_we_execute_header`, `_performance_body`. **No descent rides this
slice** — the first multi-member slice since ADR-0364 to need none. `app.py` **11,735 → 11,403**
(wc-truth). `LAYER_ORDER` becomes `… → analysis → evm → performance → app`; the re-export block
lands immediately above portfolio's (isort: `performance` < `portfolio`); `performance.py` joins
pyproject's per-file E501 list (the fourteen chart-mount tiles and their viz-hint one-liners are
HTML f-strings, over-long inside app.py's exempt region — verbatim outranks re-wrapping);
`EXTRACTED`, `LAYER_ORDER`, `VIEW_MODULES` and both whole-view-layer guard tuples gain
`"performance.py"`.

## The re-measure: census-EXACT, for the first time in phase 3

Every prior slice's behaviour-seeded closure ran *larger* than its prefix census — 1.15× at the
mildest (ADR-0377), 3.6× at the widest (ADR-0376). This one lands on the nose:

| | names | ast lines |
| --- | ---: | ---: |
| prefix census (the queue's number) | 4 | 326 |
| closure over `/performance` + `/export/{fmt}/performance` | **4** | **326** |

Ratio **1.00×**. The reason is structural, not luck: this family's members all carry the family
prefix (`_performance_*` / `_perf_*`) *except* `_how_we_execute_header`, which the queue had
already counted by hand after ADR-0375's ruling-lag finding. A census that has already absorbed
the ruling can be exact — but only the referrer walk can *prove* it, and the walk is still what
assigns membership.

**No descent, adjudicated.** The walk surfaced exactly one shared name, `_sources_line` (14
lines, referred to by `_scorecards_body` and seven other routes). It is **not** a mover's
dependency: the four movers reference **no** other app.py-defined name at all — `_sources_line`
enters the closure only through `performance_view`'s own body (app.py:3203), and routes live in
`create_app`, which imports downward and stays. A route-only referrer never forces a descent.

**The export route SHARES a mover — the first time in six slices.** ADR-0372/0373/0374/0375/0376
/0377 all recorded "the export route contributes NO movers". Here `export_performance` builds its
five tables from `_performance_data`, so both export formats are part of the family's
render-proven surface. The streak is broken by behaviour, not by a rule change.

The only imports `app.py` drops are the whole `performance_summary` block — `activity_flow`,
`duration_ratio`, `to_go_snapshot`, `work_to_go_census`, `workoff_burden` (zero uses outside the
moved region) — re-landing verbatim in `performance.py`.

## The oracle — 498 labels, and the recipe reproduced from its own fingerprint

Rebuilt from the ADR-0372 recipe with the ADR-0375 title-stripped TP4 pool (five snapshots,
`<Title>` stripped, asserted stripped before any render; the untitled-pool assertion re-checked
on `/evolution` and `/compare` before the first measured body). Surface unchanged from ADR-0377:
60 parameterless GETs (enumerated by **method + path**, so `/openapi.json` is counted) · both
fmts × 27 parameterless `{fmt}` exports · the 7 `{name}` pages AND all 8 `{name}` exports both
fmts on TP4 v5 · the established variants (`/trend?target=22`, the three ADR-0352 `/evolution`
shapes aimed at UID 22, the seeded `/api/sra/ssi?iterations=300`, the four `[grouped]` labels) —
146 × three target states + the all-60 `[empty]` stage = **498**. Target UID **22**, POSTs
303-asserted. Three normalizers inherited, each made **LOUD** (a `raise` on a zero-match), which
is ADR-0377's flap-factory lesson applied at design time rather than paid for again.

**ADR-0377's fingerprint did its job as a harness self-check.** The first build of this oracle
read `404:38` per loaded stage against the recipe's `404:4`. Adjudicated by payload before
anything was tweaked, in two findings: (1) the valid export formats are **xlsx and docx**, not
csv — `_bad_format` returns 404 with `"format must be xlsx or docx"`, so a csv surface 404s 34
labels' worth; (2) the `{name}` key is the session key, which **drops the `.xml`**
(`TP4_DataCenter_v5`, not `TP4_DataCenter_v5.xml`). With both corrected the harness reproduces
ADR-0377's histogram exactly — `[empty]` {200:41, 400:17, 422:2}, each loaded stage {200:123,
404:4, 422:19}, 4xx **88 all-stages / 69 loaded-stages** — which is what licenses calling it the
same instrument. Double-render determinism across two separate processes: **0 flapping**.

## Pre-flight probe — 4/4 render-proven, ZERO dark members (fifth consecutive slice)

Span-scoped anchor mutations in place in app.py: anchor count asserted `== 1` in-file, anchor
line asserted **inside** the member's own AST span, value-level markers only (so nothing raises —
the label list is a render measurement, not a crash signature). Restores md5- and
anchor-grep-verified.

| member | labels moved (of 498) |
| --- | --- |
| `_perf_version_block` | **9** — `/performance` AND both fmt exports, all three session states |
| `_performance_data` | **9** — same nine |
| `_how_we_execute_header` | 3 — `/performance` × three states |
| `_performance_body` | 3 — `/performance` × three states |

**Two anchors were deliberately re-cut after a weaker first reading**, ADR-0373's stronger-anchor
round applied to a *non-zero* move rather than a 0-move: `_performance_data` first anchored on
`data["version"]`, which reaches the page blob and the **docx** body but **not** the xlsx body
(the TableSet title is not xlsx sheet content), and so measured 6; re-anchored on a quad row
value it measures 9. `_perf_version_block` first anchored on `status_month` (page blob only, 3);
re-anchored on the DRM `points` list — which the G5 export table renders from — it measures 9.
*A probe anchor that lands in one output channel understates a member whose reach spans three;
when a member feeds an export, anchor it on something the export's own tables render.*

## Proof

- **Per-region byte-identity: IDENTICAL** — asserted in-script before the write, from disk after,
  and a third time after `ruff --fix` dropped app.py's five mover-only imports (`sha256
  cc6c99e4…` on both sides); `ruff format --check` reported zero reformats over 939 files.
- **Multiset (final tree): 51 added / 0 removed — ZERO code lines removed.** Cleaner than
  ADR-0377's single import-shape artifact: the dropped `performance_summary` block is
  parenthesized on both sides, so every member line cancels verbatim. Measured on the quiescent
  tree, md5-verified first (ADR-0376's reverse trap). The quiescence check itself had to be
  rewritten — see the trap below.
- **Dropped-import sweep: FOUR readers, in two files — and the first sweep MISSED them.** The
  sweep was written as a regex over the alias `app_mod` (the repo's dominant idiom); both readers
  spell it `app_module`, so the sweep reported zero with its positive control live (182 test files
  import from `web.app`) and looked exactly like a clean result. The full suite caught it —
  `AttributeError: module 'schedule_forensics.web.app' has no attribute 'work_to_go_census'`. The
  corrected sweep is **alias-agnostic** (grep each dropped NAME across `tests/`, no module
  qualifier) and finds exactly 4 references, all to `work_to_go_census`, in
  `tests/perf/test_perf_regression.py` and `tests/web/test_session_consistency.py`; the other four
  dropped names have zero readers. See "The traps this slice paid for" below.
- **498/498 routes byte-identical**, pristine vs cut, on the double-render-verified oracle; the
  88/69 fingerprint held on the cut tree.
- **Falsified in the new locations: 4/4 EXACT label lists** — every member re-mutated in
  `performance.py` with the probe's own anchors moved exactly its pre-flight list; all four
  anchors additionally asserted **absent** from post-cut `app.py`; restores md5-verified.

## The sweeps

- **Monkeypatch + attribute-read sweep** (all 27 names `performance.py` binds, defined or
  imported, including the two function-local deferred imports): **one hit —
  `compute_activity_makeup`**, the ADR-0291 projection-memo spy, which is slice 12's standing
  adjudication rather than a new one. Re-verified post-cut by running the module green (5
  passed): the spy patches `app_mod.compute_activity_makeup` and exercises `/api/dashboard`; the
  module never renders `/performance` (literal count of "performance" in the file: 0), so
  `performance.py`'s own binding is outside the patch's reach by design. `non_summary` is **not**
  bound by `performance.py`, so that half of the adjudication does not grow.
- **Source-text sweep** (every ≥6-char literal of all 5 app.py-source-reader test files ∩ the
  moved text): every hit adjudicated — `panelkit.js` / `performance.js` / `<` / `&mdash;`
  belong to the two whole-view-layer guards, which this commit widens; `mission.js` appears in
  the moved text **only inside `_performance_body`'s docstring** (prose explaining that
  mission.js is *not* on this route) and `test_axis_titles` uses it as a member of `EXEMPT`, a
  ledger of static JS **filenames** checked against `static/*.js`, never an app.py source
  assertion; `"BEI (throughput)"` in `test_presentation_fixes` is a `_stat_cards` CALL ARGUMENT
  (ADR-0377's adjudication, unchanged); `latest` / `static` / `metrics` / `status` /
  `schedule_forensics` are generic words. `_TS_CAPTION_MARK`, `data-ts-caption`, `drilldown.js`
  and `_LAYOUT` verified **absent** from the moved text. **Zero SOURCE-TEXT reader repoints** —
  but the zero-repoint streak itself ENDS at four: two monkeypatch spies had to be repointed (the
  dropped-import finding above), so this slice repoints two readers.

## Verification

Six mutations, each an exact-match splice landed-count-asserted in-script, each run against the
WHOLE module (no `-k`), each exactly ONE named failure with the twins green, each restored from a
scratchpad copy (never `git checkout`), md5-verified, each module re-run green after restore:

| mutation | named failure | split |
| --- | --- | ---: |
| re-export deleted from `app.py` | `…reexported_by_app…[performance.py]` | 1 / 35 |
| deferred upward import in `_performance_body` (in-body) | `…imports_downward[performance.py]` | 1 / 35 |
| `"performance.py"` dropped from `test_bar_drill` | `…read_the_whole_view_layer[test_bar_drill.py]` | 1 / 35 |
| `"performance.py"` dropped from `test_presentation_fixes` | `…[test_presentation_fixes.py]` | 1 / 35 |
| `"&mdash;"` sentinel planted in `performance.py` (in-body) | `test_no_mdash_entity_sentinel_values…` | 1 / 5 |
| second `drilldown.js` include in `performance.py` (in-body) | `test_drilldown_runtime_is_loaded_globally…` | 1 / 6 |

Mutations 3–4 are the enumeration guard's **nineteenth and twentieth consecutive live catches**.

A **seventh** mutation was added after the suite exposed the sweep miss: reverting both repointed
spies' patch target from `perf_module` back to `app_module` fails exactly the two tests that claim
to measure the P3 memo (`…memoised_per_epoch`, `…across_an_epoch_flip`), proving the repoint is
load-bearing rather than a rename that passes either way.

## The traps this slice paid for

### 1. A sweep written against ONE alias is not a sweep

`ruff --fix` correctly dropped five now-unused `performance_summary` imports from `app.py`. The
dropped-import sweep asked "who reads these through `web.app`?" as a regex over `app_mod.<name>` /
`setattr(app_mod, "<name>")` / `web.app.<name>` — every spelling the repo's dominant idiom uses.
Two tests alias the module `app_module` instead, and both patch `app_module.work_to_go_census` to
spy on the P3 memo. The sweep returned **zero readers with its positive control live**, which is
indistinguishable from a genuinely clean result, and the cut shipped into the suite with two
broken tests.

Two lessons, and the second is the sharper one:

- **Sweep by NAME, not by qualified expression.** A dropped import can be read through any alias,
  a `getattr`, or a re-export; only the bare name is invariant. The corrected sweep greps
  `\b<name>\b` across `tests/` and adjudicates each hit.
- **A positive control proves the sweep RUNS; it does not prove the sweep's PATTERN is right.**
  The 182-file control was live and truthful the whole time. ADR-0353's "an empty sweep is
  evidence only with a positive control" is necessary, not sufficient — the control must exercise
  the same pattern the sweep depends on, or it only proves grep works.

The two spies were repointed to `web/performance.py` — the module whose code actually calls
`work_to_go_census` (the ADR-0297 phase-1 trap, recurring). Each repoint was then **proven
load-bearing**: reverting the patch target to `app_module` fails both tests, so neither passes
vacuously; restored from scratchpad copies, never `git checkout`.

### 2. A quiescence check that matched its own shell

The multiset diff is guarded by "never MEASURE a tree a battery is mutating" (ADR-0376). The
guard was implemented as `pgrep -f pytest` — and it fired on a quiescent tree, because the
shell running the check carries the heredoc (containing the word `pytest`) **in its own argv**.
The `[p]ytest` bracket trick fails identically for the same reason. Adjudicated by reading the
matched process's command line (it was the check itself), then reimplemented by scanning `/proc`
for processes whose `cmdline[0]` contains `python` **and** which are not this pid. *A
self-referential guard is worse than no guard: it cries wolf on a clean tree, and the natural
"fix" is to delete it.* The measurement was only taken after the corrected check passed.

## Deliberately NOT done

- **The slice-7 crafted v4/v2 SSI setup-load sequences were not rebuilt into this oracle**
  (ADR-0372/0374/0375/0376/0377 precedent, same reasoning): this cut does not touch
  `_apply_ssi_setup`'s machinery.
- **`_sources_line` was NOT descended into `components.py`.** It is shared, but by *routes* and
  by `_scorecards_body` — never by a mover. Descending it would move a stayer's dependency for
  no layering reason; when the /scorecards family is eventually cut, its own closure will make
  that call on evidence.
- `groups` (430 by prefix, `_saved_*` included) stays outside the phase-3 candidate list while
  ADR-0343 feature work is queued against it.
- `CLAUDE.md`'s phase-3 + E501 prose still lag by design (the standing doc-drift sweep owns them
  — `performance.py` now also joins the unpatched E501 list there); `performance.py` DID join
  pyproject's per-file E501 list.

## Consequences

- The remaining slice queue, by the post-cut prefix census (wc-truth; each family still owes its
  OWN closure before cutting; membership named because the prefix sweep is a finder, not the
  definition): **resources 306** (`_resources_body` 157 + `_resources_explainer` 20 +
  `_resource_loading_json` 51 + `_who_is_overloaded_header` 78) · **scurve 212** · **path 194**
  (incl. `_what_drives_header` 80) · **compare 166** (incl. `_what_changed_header` 79).
- **A census can be exact — and that is still not membership.** The 1.00× ratio is the first, and
  it arrived only because a prior ADR's ruling had already been folded into the queue by hand.
  The closure remains the definition; the census remains a finder that happened to agree.
- **The export-contributes-no-movers streak is over at five.** A family whose export route reads
  the page's own data builder puts both export formats inside the family's proven surface — and
  makes the probe anchor choice matter more, since page-only anchors understate such a member.
- The oracle's published fingerprint (498 labels; 88 all-stages / 69 loaded-stages; per-stage
  histograms) is now demonstrably strong enough to **re-derive the recipe from scratch**: two
  harness errors were caught by it before a single byte-identity claim was made.
- **The dropped-import sweep's shape is now fixed for every future slice: by bare NAME across
  `tests/`, never by a module-qualified regex.** The 498-label oracle could not have caught this
  class — the two spies are unit tests, not routes — so the sweep is the only instrument that
  covers it, and it must not be aimed by guessing the caller's alias.
