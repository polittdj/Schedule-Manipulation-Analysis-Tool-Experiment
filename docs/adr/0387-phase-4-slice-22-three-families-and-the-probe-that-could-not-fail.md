# ADR-0387 — Phase 4 slice 22: three page families out, and the probe that could not fail

- **Status:** Accepted
- **Date:** 2026-08-11
- **Continues:** ADR-0350 (the kernel), ADR-0351 (the descent rule — **fired**), ADR-0352 (the
  span-scoped pre-flight probe), ADR-0365 (closure-before-cut; the named-failure rule), ADR-0372
  (the oracle recipe), ADR-0374 (a render-conditional member needs its condition IN the oracle),
  ADR-0378 (sweep by bare NAME; route-only referrers; the page-only-anchor trap), ADR-0379 (the
  oracle extended to light a family it was blind to), ADR-0382 (the oracle committed to the repo),
  ADR-0383 (phase 4's scope and its priced table), **ADR-0386 (slice 21; the exact-route seeding
  rule this slice depends on)**
- **Related:** ADR-0337 (the chapter-12 panel contract), ADR-0343 (`groups` stays fenced)

## Decision

**Extract THREE page families — verbatim — in one slice**, and **descend one shared name**:

| module | movers | ast lines | app.py span(s) |
| --- | ---: | ---: | --- |
| `web/brief.py` | `_BRIEF_XLSX_TITLE`, `_brief_body` | 48 | 6988–6991, 7316–7359 |
| `web/card.py` | `_count_bar_table`, `_card_body` | 140 | 7156–7297 (contiguous) |
| `web/scorecards.py` | `_parse_committed_date`, `_sc_status_class`, `_scorecard_export_table`, `_scorecard_panel`, `_scorecards_body` | 151 | 1206–1214, 7794–7941 |
| ↓ `web/components.py` | `_sources_line` (descent) | 14 | 1190–1203 |

`app.py` **9,936 → 9,593** (wc-truth), from 17,197 when phase 3 began. `LAYER_ORDER` becomes
`… → wbs → brief → card → scorecards → app`; all three join pyproject's per-file E501 list;
`EXTRACTED`, `LAYER_ORDER`, `VIEW_MODULES` and both whole-view-layer guard tuples gain all three.

Three families in one slice because all three are the **zero-descent set** the standing queue
names, they are adjacent in it, and 339 mover lines is an ordinary slice size (performance 326,
resources 306). The evidence below is **per family** regardless — a shared slice is not shared
proof.

## The closures — priced by referrer walk, and the walk reproduced the record

The walk was rebuilt from scratch in this container and independently reproduced ADR-0386's
re-priced table (`brief` 1/44/0, `briefing` 4/194/**3** — not ADR-0383's 4), which is what
licensed trusting it on the three families it had not seen.

| family | prefix census | referrer walk | ratio |
| --- | ---: | ---: | ---: |
| `brief` | 4 names / 234 lines (`brief` matches `briefing`) | **1 / 44** | — |
| `card` | 1 / 128 | **2 / 140** | 2.0× by names |
| `scorecards` | 3 / 139 (`scorecard`) | **5 / 151** | 1.7× by names |

**The prefix misses a member in two of the three.** `_count_bar_table` carries no `card` token;
`_sc_status_class` and `_parse_committed_date` carry no `scorecard` token — and
`_parse_committed_date` lived **6,500 lines away** at 1206. A bare-NAME sweep confirms each
independently of the walk. And in the other direction, a `brief` *name* census sweeps in all
three `briefing` names: **the prefix is a finder in both directions and the walk is the
definition** (ADR-0378, ADR-0386).

**Two names were reached but are NOT members**, both adjudicated by *who* refers to them:
`_unschedulable_panel` (the `/card` route calls it, and so does `/analysis`) and — before the
descent — `_sources_line`. A route-only referrer never blocks a move, but neither does it make
the name that family's to carry; both were left where the call graph put them.

## The descent: a route-only referrer does not block, but a MOVER does

`_sources_line` is called by `_scorecards_body` **and** by eight other page routes. That
combination has exactly two legal resolutions, and the difference is not stylistic:

* move it into `scorecards.py` — legal (routes live in `create_app` and import downward), but it
  buries a generic provenance line inside one page's module; or
* **descend it into `components.py`** — the shared kernel every view module may import.

It descended. `scorecards.py` could not have imported it from `app.py`: that is an UPWARD import
and closes a cycle, which is the whole acyclicity argument `LAYER_ORDER` exists to pin. This is
the same shape ADR-0351 (`_task_name_across`), ADR-0376 (`_target_panel`) and ADR-0377
(`_metric_scorecard_table`) each resolved the same way, and it lands beside the provenance
cluster (`_prov_chip` / `_pair_prov_chip` / `_series_prov_chip`) it belongs to.

## THE FINDING — a probe that could not have reported anything but zero

The first probe scored `_brief_body` **oracle-dark**. It is not: `/brief` renders its body at all
four loaded stages, and the marker sat in an always-emitted header line.

The harness compared `manifest.json`'s **values**. `oracle_corpus._iter_out` names each body file
`sha256(LABEL)[:16] + ".bin"` — **derived from the label, not the content** — so `manifest[label]`
is a constant across every run of every tree. The diff could not have reported a difference for
any member, including one that changed every byte of every page. It reported "0 moved" with the
confidence of a measurement.

This is the repo's single most-repeated defect class — a green check that could never fail — and
it appeared *inside the instrument built to detect exactly that*. Two things now stand between it
and a repeat:

1. **The probe compares BODY BYTES**, read from the `.bin` files (which is what the corpus's own
   documented usage, `diff -r`, always did).
2. **A positive control runs BEFORE any finding is trusted**, and the harness *aborts* if it
   reports zero. A second, independent check asserts the marker TEXT actually reached a rendered
   body — byte-difference and marker-presence are different instruments, and agreement beats
   either alone.

The generalisation is sharper than "add a control": **the first draft of an instrument is not
evidence until it has been shown to fail.** A probe whose failure mode is silence — reporting
"nothing moved" — cannot be sanity-checked by reading its output, because its broken output and
its most interesting finding are the same string.

## The oracle was extended to light a genuinely dark member

`_parse_committed_date` really was dark, and for a structural reason: `scorecards_buffer_json`
**requires** `committed`, so the bare `/api/scorecards/buffer` label is a 422 that returns before
the parser's live path runs. Following ADR-0374's rule and ADR-0379's precedent, one variant was
added to the corpus:

```
("[buffer-committed] GET /api/scorecards/buffer",
 "/api/scorecards/buffer?committed=2026-07-17&iterations=100")
```

The date is the TP4 pool's own deterministic finish, which is what makes the render
non-degenerate — committed confidence **0.49** with non-zero P70/P80 reserves, where any date
past the finish returns the trivial 1.0 / 0.0. `iterations=100` is the route's own floor and the
Monte-Carlo is seeded. The corpus goes **648 → 652** (one label per loaded stage; `[empty]` is
unchanged because variants are loaded-stage only), and the pinned label list was regenerated in
this commit. With it, `_parse_committed_date` moves exactly those four labels **and nothing else**
— so the variant is proven load-bearing: remove it and the member goes dark again, which is
mutation 7 of the battery.

## The export routes split three ways, measured — not assumed

ADR-0378's trap says a page-only probe anchor understates a member that feeds an export. All
three families were anchored per member rather than per page, and they do not behave alike:

| family | export route | movers it contributes |
| --- | --- | --- |
| `brief` | `export_brief` | **none** — renders via `ai.brief.brief_blocks` (docx) / straight off `brief.sections` (xlsx) |
| `card` | *(no export route)* | — |
| `scorecards` | `export_scorecards` | **`_scorecard_export_table`** — 8 labels |

`scorecards` is the first family since ADR-0378 whose export shares the page's surface. A
page-only anchor would have measured that member at **zero** and called it dark. For `brief` the
call-graph claim and the render claim were made by different instruments and agree.

*(A drafting note worth keeping: this ADR's own source file first claimed `export_brief`
re-derives through `reports/brief_tables.py`. Reading the route showed it does not — the module
does not exist in that path. The claim was corrected before it landed. A plausible module name is
not a measurement either.)*

## Proof

- **Probe 9/9 render-proven, ZERO dark** (thirteenth consecutive slice) — `_brief_body` 4 ·
  `_card_body` 4 · `_count_bar_table` 4 · `_sc_status_class` 4 · `_scorecard_panel` 4 ·
  `_scorecards_body` 4 · `_scorecard_export_table` **8** · `_parse_committed_date` **4 (after the
  variant; 0 before)** · `_sources_line` 4.
- **Fingerprint (scope: all five stages):** `[empty]` 60 `{200:41,400:17,422:2}`, four loaded
  stages of 148 `{200:125,404:4,422:19}`, **652** total. Determinism ×2 separate processes on
  **both** trees: **0 flapping**.
- **652/652 byte-identical**, pristine vs cut.
- **Per-definition byte-identity 10/10 IDENTICAL**, verified by a separate script that re-reads
  both trees from disk *after* `ruff check --fix` + `ruff format`, and every `def` asserted
  **absent** from the post-cut `app.py`.
- **Multiset: 152 added / 5 removed — ZERO code lines removed.** The five are the two
  dropped-import members (`DiagnosticBrief`, `Scorecard`) and the three `#:` comment lines
  deliberately rewritten (below).
- **Battery 7/7 caught BY NAME**, each an exact-match splice with a landed-count assert before the
  write, each run against the WHOLE module, each restored from a scratchpad copy and md5-verified,
  each module re-run green after restore. Mutations 3–4 are the enumeration guard's **35th and
  36th** consecutive live catches.
- `mypy --strict` clean over 142 source files; `ruff check .` clean over the whole tree.

## The sweeps (population: **511** `.py` files; `build/`, `dist/`, `.venv`, caches excluded)

- **Dropped-import sweep: TWO.** `ruff --fix` removed `DiagnosticBrief` and `Scorecard` from
  `app.py` — the movers were their last consumers. Both adjudicated by an AST, alias-agnostic
  check: **zero** callers reach either through `web.app`; positive control `create_app` = 177
  files.
- **Monkeypatch / setattr sweep, run TWICE — and the second run is the one that found something.**
  Over the 10 **moved** names: **ZERO** hits (196 setattr-style calls across 511 files); no
  ADR-0297 trap, since every caller of every moved name is a route and routes stay in `app.py`.
  But the moved names are the wrong population on their own: the ADR-0297 trap fires on the names a
  new module **binds**, because a spy aimed at `app_mod.X` stops reaching code that now resolves `X`
  through `card.py`. Re-swept over all 43 bound names, and **`card.py` binds `non_summary`**, which
  `tests/web/test_manifest_projection_memo.py:77` patches as `app_mod.non_summary`.
  **Adjudicated NOT a new trap, and measured rather than argued:** that spy's subject is
  `_dashboard_data`, which stays in `app.py` and therefore still resolves `non_summary` from
  `app.py`'s globals; `_card_body`'s copy moved, but the test only renders `/api/dashboard` and
  never `/card`. The measurement matters because the test asserts `(0, 0, 0)` on a **warm**
  dashboard — an assertion a *dead* spy would satisfy just as well. Installing the spies and making
  a **cold** call returns `scope=24, makeup=6, non_summary=12`, so the patch target is still live
  and the zero-assertion still means something. (Sibling name `compute_activity_makeup` is slice
  12's standing ADR-0291 adjudication, unchanged.)
- **Import sweep: ZERO live readers** import a moved name from `web.app`. Unlike slices 19–21
  there was no standing live check to preserve, because no test ever imported one of these ten.
- **Source-text sweep: 9 test files** reference `app.py` by path or name; **zero repoints**. The
  moved regions carry `panelkit.js`, `drilldown.js`, `scorecards.js`, `sf-drill`, `sfDrillMount`
  and `&mdash;`. Every guard for each was classified by name: all read either the STATIC file or
  the RENDERED page, except the two `&mdash;` source-text readers —
  `test_presentation_fixes.py` (widened here, and mutation 5 proves it) and
  `test_forecast_views.py`, whose `&mdash;` assertion is against a rendered page and whose
  `read_text` reads `drift.js`, not `app.py`. `test_axis_titles.py` reads `app.py`'s text for
  `_TS_CAPTION_MARK`, which no moved region carries and whose serving routes stay put.

## The one non-verbatim byte: a `#:` block that documented a PAIR

`_BRIEF_XLSX_TITLE` sat under a `#:` doc-comment covering **both** chapter-12 export titles, whose
first sentence is *"Both name a REAL endpoint…"*. The constant's own bytes moved verbatim; the
comment was **split**, because once one constant leaves, "Both" is false in `app.py` and absent
from `brief.py`. Each file now carries the half that is true of it, and each says where the other
half went. This is the standing "constants carry `#:` blocks the ast span does not see" trap in a
sharper form: **a shared doc-comment is not a movable unit, and leaving it intact would have left
a false statement behind** (Law 2's spirit, applied to prose).

## Deliberately NOT done

- **`briefing` was not cut**, though it is adjacent and its 4 names / 194 lines are priced. It
  carries **3** real descents (`_ollama_or_none`, `_openai_or_none`, `_active_backend` — the
  AI-backend helpers shared with `_ai_status_note` / `_settings_body` / `_polished_narrative` /
  `_translate_batch`) and deserves its own slice.
- **`export_scorecards` was not converged with the page.** It calls `_scorecard_export_table`
  already; nothing here changes behaviour.
- **`mpxj_ref()`'s shallow-clone hardening is still queued**, not silently patched (ADR-0386). This
  container was `git fetch --unshallow`'d before building, so the nine installers pin `42d92dc` —
  the commit that genuinely last touched `tools/mpxj` — rather than a clone boundary.
- `CLAUDE.md`'s phase-3 + E501 prose still lags by design (the standing doc-drift sweep owns it);
  `brief.py`, `card.py` and `scorecards.py` join `wbs.py` on the unpatched list there. All three
  DID join pyproject's.

## Consequences

- **A probe's diff must compare CONTENT, and must prove it can fail before it is believed.** An
  instrument whose broken output is indistinguishable from its most interesting finding needs a
  positive control that aborts, not a reading.
- **A descent is forced by a MOVER, not by sharing.** Route-only referrers never block; a mover
  that calls a shared name means the name must already live below, or go there.
- **The monkeypatch sweep's population is the names the new module BINDS, not the names it
  MOVES.** Over the moved names this slice was clean; over the bound names it was not. And a
  spy that asserts ZERO cannot be checked by running it — force the non-zero case.
- **An export route's relationship to its page is per-family and must be measured.** Three
  families in one slice produced three different answers.
- **Extending the oracle is part of the method, not a deviation** — when a member is dark because
  the corpus lacks its render condition, the condition is what is missing.
- Eight families remain outside `groups` by ADR-0383's table, all carrying descents. `briefing`
  (194, 3 descents) is next by size; `settings` (318) and `cei` (262) also carry real ones.
  **Re-price every one by referrer walk before cutting.**
