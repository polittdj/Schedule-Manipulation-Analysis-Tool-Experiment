# ADR-0388 — Phase 4 slice 23: /briefing + /cei, and the three descents that were not there

- **Status:** Accepted
- **Date:** 2026-08-12
- **Continues:** ADR-0350 (the kernel), ADR-0351 (the descent rule), ADR-0352 (the span-scoped
  pre-flight probe), ADR-0365 (closure-before-cut; the named-failure rule), ADR-0372 (the oracle
  recipe), ADR-0374 (a render-conditional member needs its condition IN the oracle), ADR-0378
  (sweep by bare NAME; route-only referrers; the page-only-anchor trap), ADR-0379 (the oracle
  extended with a POOL to light a family it was blind to — the direct precedent for `[ceidark]`),
  ADR-0382 (the oracle committed), ADR-0383 (phase 4's scope and its priced table — **corrected
  here**), ADR-0386 (exact-route seeding), **ADR-0387 (prove an instrument can FAIL before
  believing it — applied twice in this slice, and it fired both times)**
- **Related:** ADR-0337 (the chapter-12 panel contract), ADR-0343 (`groups` stays fenced),
  ADR-0375 (`strip_title` or the pool becomes one-version Projects)

## Decision

**Extract TWO page families — verbatim — with ZERO descents**, and **extend the render oracle
with a sixth stage** so the one genuinely dark member is measured rather than assumed.

| module | movers | ast lines | app.py span(s) |
| --- | --- | ---: | --- |
| `web/briefing.py` | `_BRIEFING_XLSX_TITLE`, `_cite_tag`, `_briefing_table_html`, `_the_briefing_header`, `_briefing_body` | 198 | 6981–6988 (with its `#:` block), 9037–9236 |
| `web/cei.py` | `_stack_not_measured`, `_work_piling_header`, `_cei_body`, `_cei_data` | 262 | 7153–7374, 7710–7753 |

`app.py` **9,593 → 9,125** (wc-truth), from 17,197 when phase 3 began. `LAYER_ORDER` becomes
`… → scorecards → briefing → cei → app`; both join pyproject's per-file E501 list, `EXTRACTED`,
`LAYER_ORDER`, `VIEW_MODULES` and both whole-view-layer guard tuples.

## THE FINDING — "the zero-descent set is EXHAUSTED" is measured FALSE

The standing queue opened this slice with a flat statement: *all eight remaining families outside
`groups` carry descents*, `briefing` first at **3** (`_ollama_or_none`, `_openai_or_none`,
`_active_backend`). Re-walked from scratch — because ADR-0387's own instruction was to re-price
every family and never to trust the table — the count is **zero**, and six of the eight families
carry none:

| family | movers | ast lines | descents |
| --- | ---: | ---: | --- |
| `groups` *(fenced, ADR-0343)* | 8 | 430 | 0 |
| `settings` | 7 | 347 | **3** — `_ollama_or_none`, `_openai_or_none`, `_second_backend` |
| `cei` | 4 | 262 | 0 |
| `ribbon` | 9 | 243 | 0 |
| `briefing` | 5 | 198 | 0 |
| `volatility` | 2 | 192 | 0 |
| `curves` | 3 | 131 | 0 |
| `workbench` | 1 | 67 | 0 |

The record's trio decomposes into two different errors, and neither is exotic:

* `_ollama_or_none` and `_openai_or_none` are needed by `_ai_status_note` and `_settings_body` —
  both **`settings`** movers. They were attributed to the wrong family.
* `_active_backend` is reached from the **`/api/ai/briefing` ROUTE** and from nothing else in the
  family. **A route-only referrer never forces a descent** — routes live in `create_app` and
  import downward — which is ADR-0378's rule, restated by ADR-0387, applied here to the very
  family whose price it had been inflating.

Even `settings`' real trio is not the trio the record named: `_active_backend` is out and
`_second_backend` (reached from the nested `_ask_response` helper) is in. **A priced table decays
in a way a re-walk does not**, and the correction is cheap only if the walk is rebuilt rather
than read.

## The walk was made to reproduce the record before it was allowed to correct it

An instrument that disagrees with the record is worth nothing until it has been shown to agree
with the parts of the record that are known-good. Rebuilt here, the walk was pointed at the
**pre-slice-22 tree** and required to reproduce ADR-0387's three shipped modules exactly — names,
line counts **and spans**:

```
OK  brief:      (2, 48)   spans [(6988,6991),(7316,7359)]
OK  card:       (2, 140)  spans [(7156,7167),(7170,7297)]
OK  scorecards: (5, 151)  spans [(1206,1214),(7794,7796),(7799,7804),(7807,7863),(7866,7941)]
CONTROL PASSED
```

It failed that control **twice** first, and both failures were real defects in the instrument:

1. `ast.walk(create_app)` yields `create_app` **itself**, so treating it as a nested helper
   attributed every name used anywhere inside it to one unit that is never in the allowed set.
   Every family priced at **zero members** — a uniform, plausible, completely wrong answer.
2. The `card` seed used `GET /card`; the route is `GET /card/{name}`, so the family had **no
   seed routes** and, again, zero members.

Both failure modes print as a small tidy number. Neither would have been visible without a
control that names an expected value.

*(One expectation in the control was mis-transcribed by the author, not wrong in the walk:
ADR-0387's **closure** table records `brief` as `1/44` — the function only — while its
**decision** table and the shipped `brief.py` carry the constant too, at `2/48`. The shipped
module is the record that matters; the control was corrected to it.)*

## The oracle grew a sixth stage, because one member was dark for want of a CONDITION

The span-scoped probe scored **8/9** render-proven with `_stack_not_measured` **dark**. It is not
unreachable: it is the Law-2 panel `_work_piling_header` renders **instead of** a stacked bar when
`/cei` has no scored CEI month — "not measured", never a bar of zeroes. Every pool the corpus
loaded (TP4 ×5, the resource goldens) carries a scored month, so the branch never ran and the
member's byte-identity claim would have rested on nothing.

Measured rather than guessed: of every 2-combination of the available MSPDI fixtures, exactly
three produce `cei_period=None`, all from the `jacked_up_schedule_*` pair. A query-string variant
could not have reached it — the condition is a property of the loaded POPULATION, not of a URL —
so this needed a stage, which is ADR-0379's precedent exactly. `[ceidark]` uploads
`jacked_up_schedule_1` + `jacked_up_schedule_2` with `strip_title=True` (intact, they become two
one-version Projects and `/cei` serves its placeholder — the ADR-0375 trap).

Corpus **652 → 800** (`[empty]` 60 + five loaded stages of 148); the pinned label list was
regenerated in this commit. With the stage in place `_stack_not_measured` moves **exactly the two
`[ceidark] /cei` labels and nothing else**, so the stage is **provably load-bearing** rather than
coverage theatre — remove it and the member goes dark again, which is battery mutation 5.

## The probe had to be repaired before it certified anything — again

The positive control ran first and **aborted the run**: `_page` — which wraps every HTML page in
the application — moved **zero** labels. The probe was not measuring `_page`'s dark­ness; the
marker injector handled `str` and `dict` returns and `_page` returns an **`HTMLResponse`**, so it
fell through untouched. **A probe's marker must match the RETURN TYPE** (ADR-0386) — named in the
standing trap list, and still the first thing that broke.

Repaired (append to `Response.body`, re-stamp `content-length` or TestClient truncates), the
control moves **224 labels with 224 marker hits** and the run proceeds. The same ADR-0387 pairing
is kept throughout: byte-difference and marker-presence are independent instruments and they
agree on all nine members.

## Both exports contribute NOTHING, and two instruments say so independently

ADR-0387's rule is that an export's relationship to its page is per-family and must be measured.
Here both come back empty, and the two measurements are of different kinds:

| family | export route | movers it contributes |
| --- | --- | --- |
| `briefing` | `export_briefing` | **none** |
| `cei` | `export_cei` | **none** |

The call graph says no mover is referenced by either export route; the probe says no member moves
any `/export/` label. Unlike `scorecards` in ADR-0387 — whose `_scorecard_export_table` moved 8
export labels — these two pages and their workbooks share no app-level surface.

## Proof

- **Probe 9/9 render-proven, ZERO dark** (fourteenth consecutive slice) — `_BRIEFING_XLSX_TITLE`
  5 · `_cite_tag` 5 · `_briefing_table_html` 5 · `_the_briefing_header` 5 · `_briefing_body` 5 ·
  `_work_piling_header` 10 · `_cei_body` 10 · `_cei_data` 5 · `_stack_not_measured` **2 (after
  the stage; 0 before)**. Control `_page` 224/224.
- **Fingerprint (scope: all six stages):** `[empty]` 60 `{200:41,400:17,422:2}`, five loaded
  stages of 148 `{200:125,404:4,422:19}`, **800** total.
- **800/800 byte-identical**, pristine vs cut — and the `diff -r` was itself shown to fail (a
  one-byte perturbation of a single `.bin` returns exit 1). Determinism ×2 separate processes on
  **both** trees: **0 flapping**; the second pair reproduces byte-identity independently.
- **Per-definition byte-identity 9/9 IDENTICAL**, re-read from disk *after* `ruff check --fix` +
  `ruff format`, every moved definition asserted **absent** from the post-cut `app.py` (0 leaks).
- **Multiset: 95 added / 7 removed — ZERO code lines removed.** The seven are four import-list
  entries (`BriefingSection`, `ExecutiveBriefing`, `audit_schedule`, and the `BowWave` half of a
  two-name import) and three deliberately rewritten comment lines.
- **Battery 7/7 caught**, each an exact-match splice with a landed-count assert before the write,
  each restored from a scratchpad copy and **md5-verified**, each selection re-run GREEN after
  restore. Round 1 scored 4/7 by name; the three misses were diagnostic and are recorded below.
- `mypy --strict` clean over **144** source files; `ruff check .` clean whole-tree.
- The corpus was re-rendered **after** the battery finished and is still 800/800 identical, so
  nothing the battery touched leaked into the measured tree.

### The three battery mutations that did not score on the first pose

Kept because what they measured is more useful than a clean 7/7 would have been:

* **M1** made `briefing.py` import `web.app` at module scope. That is a *real* cycle, so pytest
  died at **collection** (exit 2) and the layering guard never ran. Louder than a named failure,
  but not the guard firing — and "pytest exit ≠ a failing test" is this repo's own rule. Re-posed
  under `TYPE_CHECKING`, the statement is still there for the AST guard and no longer detonates:
  `test_the_view_layer_only_ever_imports_downward[briefing.py]`, caught by name. **That is also
  the more realistic smuggling route for an upward import.**
* **M6/M7** edited markup inside a moved definition and **no unit test noticed**. That is a true
  measurement about the unit tests — they do not pin those strings — not a harness bug. For a
  verbatim move the instrument that pins markup is the **oracle**, so they were re-scored against
  it: 2 and 5 differing labels respectively. Those counts **match the probe's independent
  per-member measurements exactly** (`_stack_not_measured` 2, `_briefing_table_html` 5), which is
  two instruments agreeing on a number neither was told.

## The sweeps (population: **513** `.py` files; `build/`, `dist/`, `.venv`, caches excluded)

- **Dropped-import sweep: TWO.** `ruff --fix` removed `BowWave` and `Citation` from `app.py` —
  the movers were their last consumers. Both adjudicated by an AST, alias-agnostic check: **zero**
  callers reach either through `web.app`; positive control `create_app` = **177** files.
- **Monkeypatch / setattr sweep over the names the new modules BIND** (ADR-0387: the moved names
  are the wrong population) — 26 bound names, **197** setattr-style calls across the population,
  **2 hits**, both `audit_schedule` at `tests/ai/test_briefing.py:230-231`. **Adjudicated NOT the
  ADR-0297 trap:** the patch targets are `schedule_forensics.ai.briefing` and
  `engine.recommendations`, and the subject `build_briefing` resolves the name from `ai.briefing`'s
  globals — a different module from the new `web.briefing`, which the test never imports. The
  basename collision (`ai/briefing.py` vs `web/briefing.py`) is real and worth knowing; the patch
  targets are fully qualified and unaffected. Note also that this test asserts `calls == ["audit"]`
  — a **non-zero** assertion — so a dead spy fails loudly rather than passing quietly, and no
  forcing was needed.
- **Import sweep: FOUR live readers** import a moved name from `web.app` and must keep working
  through the re-export — `test_cei_views.py` and `test_r10_cei_contract.py` (`_cei_body`),
  `test_coverage_app.py` (`_briefing_table_html`), `test_coverage_app_extra.py` (`_briefing_body`).
  All four modules run green.
- **Source-text sweep: 37 files** reference `app.py` by path or name; **zero repoints** — both
  whole-view-layer guards were widened to read `briefing.py` and `cei.py`, which mutation 4 proves.

## The two `#:` notes this slice made false

ADR-0387 split a doc-comment that documented BOTH chapter-12 export titles and left each half
beside its constant — with `brief.py`'s half saying the twin *"stays in `app.py` until the
/briefing family is cut."* This slice cuts it, so that sentence and the matching one in the
migrated block were both rewritten to say where the other half now lives. `app.py`'s slice-22
import comment ("`briefing`, whose four names and three AI-backend descents stay in this file")
was rewritten for the same reason and for a second one: it was **wrong on both counts**.

**A doc-comment that names a future is a doc-comment with an expiry date.** Both halves were
found by grepping the moved names, not by remembering.

## Deliberately NOT done

- **`settings` was not cut.** It is the only remaining family with real descents (3), and it
  deserves the slice where they get resolved rather than being tacked onto a two-family cut.
- **`_active_backend` was not descended.** Nothing requires it: no mover reaches it.
- **The `[ceidark]` stage renders the full 148-label surface**, not a `/cei`-only subset. Every
  other stage does, the guard machinery assumes it, and a stage that renders a special-case subset
  would be a second kind of stage to reason about for one member's benefit.
- **`mpxj_ref()`'s shallow-clone hardening is still queued, not silently patched.** The trap fired
  exactly as documented: this container is a `--depth 1` clone and `git log -1 -- tools/mpxj`
  returned `3a925b0`, the CLONE BOUNDARY. `git fetch --unshallow` first, and the nine installers
  pin `42d92dc` as they must. The build still has no guard against this — it prints the ref and
  trusts the operator to have unshallowed.
- `CLAUDE.md`'s phase-3 + E501 prose is refreshed here for the module list, but the wider
  doc-drift sweep (PARITY-REPORT, FINAL-REPORT) remains queued.

## Consequences

- **A priced table is a snapshot, not a measurement, and it decays silently.** ADR-0383's has now
  been wrong about `briefing` twice — first the count, now the whole premise. Re-walk, and make
  the walk reproduce something known before believing it about something unknown.
- **A route-only referrer never forces a descent** — restated because it is the rule that had been
  mis-priced, and the mis-pricing survived three ADRs.
- **A control that names an expected VALUE beats one that names a direction.** "Zero members" and
  "no seed routes" both print as plausible output; only `expected (2, 140)` catches them.
- **When a member is dark for want of a render condition, the condition is what is missing** —
  and the extension is only honest if the member then moves exactly the labels the condition
  added, which is a claim to test, not to assert.
- **A mutation that does not score can be the most informative one in the battery.** Two of this
  slice's told us the unit tests do not pin page markup — true, worth knowing, and the reason the
  oracle exists.
