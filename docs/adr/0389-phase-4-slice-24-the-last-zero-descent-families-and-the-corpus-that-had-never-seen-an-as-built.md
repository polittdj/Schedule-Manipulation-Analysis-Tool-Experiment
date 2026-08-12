# ADR-0389 — Phase 4 slice 24: the last four zero-descent families, and the corpus that had never rendered an as-built

- **Status:** Accepted
- **Date:** 2026-08-12
- **Continues:** ADR-0350 (the kernel), ADR-0351 (**the descent rule — re-read here, and the
  reading matters**), ADR-0352 (the span-scoped pre-flight probe), ADR-0365 (closure-before-cut;
  the named-failure rule), ADR-0372 (the oracle recipe), ADR-0374 (a render-conditional member
  needs its condition IN the oracle), ADR-0378 (sweep by bare NAME; route-only referrers),
  ADR-0379 (the oracle extended with a POOL to light a family it was blind to), ADR-0382 (the
  oracle committed), ADR-0386 (exact-route seeding; a spy that asserts ZERO must be forced),
  ADR-0387 (prove an instrument can FAIL before believing it), **ADR-0388 (a priced table is a
  snapshot — re-walked here, and it held)**
- **Related:** ADR-0297 (the monkeypatch trap), ADR-0343 (`groups` stays fenced), ADR-0375
  (`strip_title` or the pool becomes one-version Projects)

## Decision

**Extract the four remaining ZERO-DESCENT page families — verbatim, in one slice** — and **extend
the render oracle with a seventh stage** so the one dark member is measured rather than assumed.

| module | movers | ast lines | app.py span(s) |
| --- | --- | ---: | --- |
| `web/curves.py` | `_curves_header`, `_curves_body`, `_curves_data` | 131 | 6995–7129 |
| `web/ribbon.py` | `_RIBBON_WARN_FRACTION`, `_RIBBON_ZERO_TOLERANCE`, `_RIBBON_PCT5`, `_RIBBON_FLOAT_EXTRAS`, `_ribbon_cell_class`, `_RIBBON_CLS_VERDICT`, `_ribbon_cell_title`, `_can_we_trust_header`, `_ribbon_body` | 243 | 7157–7309, 7381–7487 |
| `web/workbench.py` | `_workbench_body` | 67 | 7312–7378 |
| `web/volatility.py` | `_volatility_data`, `_volatility_body` | 192 | 8491–8684 |

`app.py` **9,125 → 8,482** (wc-truth), from 17,197 when phase 3 began. `LAYER_ORDER` becomes
`… → cei → curves → ribbon → workbench → volatility → app`; all four join pyproject's per-file
E501 list, `EXTRACTED`, `LAYER_ORDER`, `VIEW_MODULES` and both whole-view-layer guard tuples.

**This empties the zero-descent set.** Outside `groups` (fenced, ADR-0343), `settings` is the only
page family left in `app.py`.

## The walk was rebuilt and made to reproduce the record before it was allowed to extend it

ADR-0388's instruction was to re-walk rather than read the table, so the referrer walk was rebuilt
from scratch and pointed at the **pre-slice-23 tree**, where ADR-0388's two shipped modules pin
the expected values exactly — names, line counts **and** spans:

```
OK  briefing   (['_BRIEFING_XLSX_TITLE','_briefing_body','_briefing_table_html',
                '_cite_tag','_the_briefing_header'], 198)
OK  cei        (['_cei_body','_cei_data','_stack_not_measured','_work_piling_header'], 262)
CONTROL PASSED
```

It was then shown able to FAIL, twice and in two different ways — the same control pointed at the
**post**-slice-23 tree (the names are gone: `([], 0)`), and with ADR-0388's own defect #1
re-injected (`ast.walk` over `create_app` with no stop-set, which attributes every name used
anywhere inside it to one unit). Both print `([], 0)` and both exit 1. **The failure mode ADR-0388
paid for reproduces on demand**, which is what makes the instrument's agreement worth anything.

Re-priced on the current tree, **ADR-0388's table reproduces exactly** — the first time in this
phase a carried-forward table has survived a re-walk unchanged:

| family | movers | ast lines | descent candidates |
| --- | ---: | ---: | --- |
| `groups` *(fenced)* | 8 | 430 | 0 |
| `settings` | 7 | 347 | 3 |
| `ribbon` | 9 | 243 | 0 |
| `volatility` | 2 | 192 | 0 |
| `curves` | 3 | 131 | 0 |
| `workbench` | 1 | 67 | 0 |

The four cut here are **fully disjoint**: no name is claimed by two families, and no mover of one
references a mover of another — measured, not assumed, which is what makes a four-family slice no
riskier than a one-family slice.

## THE FINDING — `settings`' three "descents" are CANDIDATES, and none of them is forced

ADR-0388 corrected *which* three names `settings` carries. It did not ask the next question, and
the answer changes what slice 25 has to do.

ADR-0351 states the rule the layering makes unavoidable:

> A symbol needed by an extracted module must live **at or below** that module's layer.

A name can satisfy that in **two** ways: descend into `components.py`, **or move into the family
module itself** — `app.py` is the TOP layer and imports downward, so anything left behind in
`app.py` still reaches it through the `X as X` re-export. Only a referrer in **another extracted
module** can force the first option, because that module cannot import sideways or up.

Measured, with a positive control:

| candidate | blocking referrer | where that referrer lives | forced? |
| --- | --- | --- | --- |
| `_ollama_or_none` | `_active_backend` | `app.py`, module level | **no** |
| `_openai_or_none` | `_active_backend` | `app.py`, module level | **no** |
| `_second_backend` | `_ask_response` | `app.py`, nested in `create_app` | **no** |

An AST scan over all 28 extracted view modules finds **zero** references to any of the three
(positive control: `_e`, the same scan, **26** modules — so the scan is not blind). ADR-0378's
own precedent already ruled this way for `_sources_line`: shared, but never by a mover that had to
leave, so it stayed.

**So the walk's "descents" column counts candidates, not verdicts**, and it is now labelled that
way. `settings` is very likely a single-module cut with **zero forced descents** — but that is
slice 25's measurement to make, not this ADR's claim to bank.

## The oracle grew a seventh stage, because the corpus had never rendered an as-built

The probe scored **14/15** with `_RIBBON_FLOAT_EXTRAS` **dark**. Its branch is a Law-2 guard
(audit NEW-1): when a schedule has no incomplete activities, Avg/Max Float are a placeholder
`0.0`, and the ribbon must show `—` rather than a fabricated mean.

Measured rather than guessed: **every** MSPDI fixture in the tree (16) and the one XER carry at
least one activity under 100% complete. The condition was not merely unreached — **the corpus had
never rendered a fully-progressed schedule at all**, which is an ordinary forensic input and a gap
wider than this one member.

`[allcomplete]` is built the way `strip_title` already is — a **byte transform of an existing
fixture, not a new file**: every `<PercentComplete>` in `TP1_Library_Progressed` is rewritten to
100, and the transform **asserts its own landed count against the `<Task>` count**, because a
fixture with one task missing the element would leave that task incomplete and the branch dark
again, silently. `TP1` is used because it is the one authored snapshot the corpus does not
otherwise load, so the stage adds a session key rather than shadowing one.

Corpus **800 → 948**; the pinned label list was regenerated in this commit. The new stage renders
the full 148-label surface with the same status histogram as every other loaded stage. With it in
place `_RIBBON_FLOAT_EXTRAS` moves **exactly one label — `[allcomplete] GET /ribbon` — and
nothing else**, which is ADR-0388's honesty test met as a *measurement of which labels*, not a
count: remove the stage and the member goes dark again (battery mutation M5).

## Proof

- **Probe 15/15 render-proven, ZERO dark** (fifteenth consecutive slice). Every function member
  moves 6 labels (one per loaded stage) with 6 marker hits; `_RIBBON_FLOAT_EXTRAS` moves 1.
  Control `_page` **263/263**. Four members are **byte-difference only** — a float threshold and
  two sets of attribute names cannot carry a string marker — and are reported as such rather than
  counted as two instruments agreeing when only one ran.
- **Fingerprint (scope: all seven stages):** `[empty]` 60 `{200:41,400:17,422:2}`, six loaded
  stages of 148 `{200:125,404:4,422:19}`, **948** total.
- **948/948 byte-identical**, pristine vs cut — and the `diff -r` itself shown to fail (a one-byte
  append to a single `.bin` returns exit 1; restored, exit 0). Determinism ×2 separate processes
  on **both** trees: **0 flapping**, and the second pair reproduces byte-identity independently.
- **Per-definition byte-identity 15/15 IDENTICAL**, re-read from disk *after* `ruff check --fix` +
  `ruff format`, every moved definition asserted **absent** from the post-cut `app.py` (0 leaks).
- **Multiset: 101 added / 2 removed — ZERO code lines removed.** Both removals are dropped-import
  fragments (`CheckStatus,` from a multi-name list, and the `MonthCurves` half of a two-name
  import whose surviving half is re-added as a one-name line).
- **Battery 6/6 caught BY NAME**, each an exact-match splice with a landed-count assert before the
  write, each restored from a scratchpad copy and **md5-verified**, the selection re-run GREEN
  after every restore.
- `mypy --strict` clean over **148** source files; `ruff check .` clean whole-tree.
- The corpus was re-rendered **after** the battery and is byte-identical to the pre-battery cut
  render, so nothing the battery touched leaked into the measured tree.

### M7 — the mutation scored against the oracle, not against pytest

A markup edit inside a moved definition is exactly what the unit tests do **not** pin (ADR-0388
measured this; it reproduces). Its anchor had to be chosen, not guessed: the first candidate
(`Schedule Quality Ribbon`) appears **4×** in `ribbon.py` — an anchor that collides is not
span-scoped (ADR-0377) — and the obvious unique alternatives (`>Missing Logic<`, `>Merge
Hotspot<`) are asserted by 11 and 2 test files respectively, which would have made the mutation
score for the wrong reason. `>Click any metric cell<` is unique in the file and pinned by **no**
test. Result: unit selection **exit 0** (the unit tests genuinely do not pin it), oracle **6
differing labels** — which **matches the probe's independent per-member count for `_ribbon_body`
exactly**, two instruments agreeing on a number neither was told.

## The sweeps (population: **517** `.py` files; `build/`, `dist/`, `.venv`, caches excluded)

`build/` is a stale copy of `src/` and is excluded; the count is stated because a sweep's
population is part of its claim (ADR-0386). 513 before this slice's four new modules.

- **Dropped-import sweep: TWO.** `ruff --fix` removed `CheckStatus` and `MonthCurves` from
  `app.py` — the movers were their last consumers. Adjudicated by an AST, alias-agnostic check:
  **zero** callers reach either through `web.app`; positive control `create_app` = **184** files.
- **Monkeypatch / setattr sweep over the names the new modules BIND** (ADR-0387: the moved names
  are the wrong population) — 38 bound names, **196** setattr-style calls, **1 hit**:
  `tests/web/test_manifest_projection_memo.py:74` patches `app_mod.compute_activity_makeup`.
  **Adjudicated NOT the ADR-0297 trap, by forcing the non-zero case** — the test asserts
  `(scope.n, makeup.n, ns.n) == (0, 0, 0)`, and a spy that asserts ZERO cannot be checked by
  running it (ADR-0386). Patching `app_mod.compute_activity_makeup` and driving a **cold**
  `/api/dashboard` reaches it **3×** (warm: 0×), so the patch target is still live: the dashboard
  caller stayed in `app.py`, and `ribbon.py`'s own call sits in `_can_we_trust_header`, which is
  not on that path. Empty-sweep control: sweeping two known-patched names that did **not** move
  (`_ollama_or_none`, `_active_backend`) returns **17** hits.
- **Import sweep: ONE live reader** must keep working through the re-export —
  `tests/web/test_volatility.py:15` (`_volatility_data`). Green.
- **Source-text sweep: 47 files** reference `app.py` by path or name; **zero repoints** — both
  whole-view-layer guards were widened to read all four new modules, which mutation M4 proves.

## Deliberately NOT done

- **`settings` was not cut**, and its three candidate descents were not resolved. The finding
  above says what slice 25 should test; it does not do slice 25's measurement.
- **`_active_backend` / `_ollama_or_none` / `_openai_or_none` / `_second_backend` were not moved
  or descended.** Nothing this slice extracts needs them.
- **The `[allcomplete]` stage renders the full 148-label surface**, not a `/ribbon`-only subset —
  every other stage does, and the guard machinery assumes it.
- **The two mis-ordered `LESSONS-LEARNED` Part VIII entries were only half fixed.** ADR-0388's
  entry was moved to the top of Part VIII where the standing rule puts it; the older 2026-08-10(e)
  straggler is left where it is and added to the doc-drift queue rather than silently reshuffled.
- **`mpxj_ref()`'s shallow-clone hardening is still queued, not silently patched.** The trap was
  pre-empted this time — `git fetch --unshallow` before building, and the nine installers pin
  `42d92dc` as they must — but the build still prints the ref and trusts the operator.

## Consequences

- **A rule can be right, written down, and still under-applied.** ADR-0351's descent rule permits
  two remedies; three ADRs of "descent counts" recorded only one of them. The column is now
  labelled *candidates*, because a count that reads as a verdict will be spent as one.
- **When a member is dark, ask what the corpus has never rendered — not what this member needs.**
  The answer here was an entire *class* of input (a fully-progressed as-built), not one branch.
- **An oracle stage can be a byte transform of an existing fixture.** No new file, no CUI surface,
  and the transform asserts its own landed count so it cannot half-apply in silence.
- **Choosing a mutation's anchor is part of the mutation.** A colliding anchor is not span-scoped,
  and a *unique* anchor that some unit test happens to assert makes the mutation score for the
  wrong reason — which would have reported the opposite of what M7 exists to measure.
- **A zero-asserting spy is only adjudicated by forcing the non-zero case.** "The caller stayed in
  `app.py`" is an argument; 3 cold / 0 warm is a measurement.
