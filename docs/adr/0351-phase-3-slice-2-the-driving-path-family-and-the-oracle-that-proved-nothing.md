# ADR-0351 — Phase 3 slice 2: the driving-path family, and the oracle that proved nothing

- **Status:** Accepted
- **Date:** 2026-08-05
- **Continues:** ADR-0350 (phase 3 slice 1 — the shared kernel), which had to land first
- **Related:** ADR-0297 (phase 1, the monkeypatch trap), ADR-0349 (phase 2, the source-text trap),
  ADR-0011 (driving-slack tiers), ADR-0251 (the counterfactual banner)

## Context

With the shared kernel out (ADR-0350), the per-page slices are finally clean. `driving`'s AST
transitive closure fell from **15 names / 870 lines** to **9 names / 793 lines**, and seven of
those nine are the page's own.

## Decision

**Extract the driving-path family — verbatim — into `web/driving.py` (842 lines):**
`_driving_data`, `_driving_path_body`, `_driving_tiers_panel`, `_driving_tier_trend`,
`_driving_path_gantt`, plus the two helpers nothing else references (`_task_iso_dates`,
`_corridor_chips`). `app.py` **19,944 → 19,139** (−805). First per-PAGE module.

**Two 2-family names DESCEND into `components.py` in the same commit.** ADR-0350 said
`_task_name_across` and `_EVO_TIER_LABEL` would "stay in `app.py` until both owners have moved;
the last slice of a pair collects them." **That was wrong, and the layering test proves it:**
`driving.py` needs both, so leaving them in `app.py` would force a page module to import
*upward* — a cycle. The correct rule is the one the layering makes unavoidable:

> A symbol needed by an extracted module must live **at or below** that module's layer. The
> **first** slice of a pair forces the descent, not the last.

`LAYER_ORDER` becomes `state → chrome → components → driving → app`. `driving.py` takes the E501
exemption (it carries the page's HTML f-strings), exactly as `chrome.py` and `components.py` did.

## The oracle proved nothing, and only falsification revealed it

The render diff reported **60/60 byte-identical**. Then the mandatory sensitivity check: one
character changed inside a moved `driving.py` function moved **0 of 60** hashes.

**The 60/60 was vacuous for this cut.** The harness loaded the single-version example schedule,
and `/driving-path`'s tier/corridor/gantt panels only render across multiple versions. Reloading
with the Project2/Project5 golden pair (63 routes, deterministic) did not help either: still
**0 of 63**. The repo had already written down why — `tests/web/test_page_memory.py` says the
corridor panel "only renders when a real driving corridor exists across versions (**which the
golden pair doesn't produce**)".

So **no fixture in the corpus can render this family's deep panels.** The honest consequence is
that the render diff, which dominated the evidence in ADR-0349 and ADR-0350, is *not* the oracle
here. It still earns its place — it proves the 63 routes that DO render are unchanged, including
`/driving-path`'s shell — but it must not be quoted as proof of the moved code.

**What is proved instead**, and it is stated as narrowly as it deserves:

- **Per-definition byte-identity.** Each of the nine moved definitions was extracted from the
  pre-move `app.py` and from its new module by AST and compared byte-for-byte: **9/9 identical**
  (`_driving_tiers_panel` 8,000 bytes, `_driving_tier_trend` 4,443, …). For code no fixture can
  execute, this is the strongest available statement, and it is a direct measurement rather than
  an inference from the file-level multiset.
- **File-level verbatim.** Non-blank multiset over `app.py + driving.py + components.py`: 47
  lines added (entirely the new module's preamble, the re-export block, and one `PathTier`
  import), **zero removed**.
- **Coverage, stated plainly.** Five of the seven moved driving names have direct unit-test
  coverage. **`_driving_tiers_panel` and `_driving_tier_trend` have none**, and neither does
  `_task_name_across` or `_EVO_TIER_LABEL`. Their only guard is `test_page_memory`'s source-text
  check, which is why that guard's repointing (below) mattered more than it looked.

**A fixture that produces a real driving corridor is now a named gap** — worth its own unit,
because until one exists this family cannot be refactored with behavioural evidence again.

## Both traps fired — one of each kind, in the same commit

- **Phase 1's (monkeypatch).** `test_coverage_app_extra` patches three names on `web.app` before
  calling `_driving_path_body`. One (`compute_driving_path_evolution`) failed **loudly** with
  `AttributeError` because `app.py` no longer binds it. The other two are the dangerous shape:
  `_driving_path_gantt` and `_corridor_chips` **are still re-exported by `app.py`**, so
  `setattr(appmod, …)` would have *succeeded and done nothing* while `_driving_path_body`
  resolved them through `driving.py` — the test would have quietly asserted against the real
  renderers. All three now patch `drvmod`.
  A first sweep for this missed them, because it compared against the names `driving.py`
  *imports*; these are names it *defines*. **The sweep has to cover every name the new module
  binds, imported or defined** — that is now how it is written.
- **Phase 2's (source text).** `test_page_memory` read `app.py` for `dpFind`/`dpBarDates`. Those
  moved. Direction: this guard's subject is the driving-path markup, so it **follows** the
  subject to `driving.py` — unlike the two whole-view-layer guards, which **widen**. Getting that
  backwards would have left the one untestable panel guarded by nothing at all.
- **Phase 2's, a THIRD time — and the sweep could not have found it.**
  `test_gantt_find_coverage` pins the corridor's Find control (`id=dpFind`, "UID or name") by
  reading **`Path(app_module.__file__)`** — the module *object*, not a literal `"app.py"`. The
  standing sweep is `grep -rln 'app\.py' tests/`, which never listed this file. It survived the
  targeted pre-cut sweep, the repointing of three sibling guards, and every fast check, and was
  caught only by the **full suite**. The sweep is therefore incomplete as written: it must also
  cover `__file__`-based and `inspect.getsource`-based reads. A repo-wide check for those found
  exactly one other module-source read (`test_installers`, whose subject —
  `@app.post("/api/shutdown")` — correctly stayed in `app.py`).
- **ADR-0350's enumeration guard worked.** Adding `driving.py` to `VIEW_MODULES` made
  `test_whole_view_layer_guards_actually_read_the_whole_view_layer` fail immediately and name
  both files to widen. That is the guard doing on its first real outing exactly what it was
  written for. It does **not** cover the `__file__` class above — that guard's claim is
  "this markup exists", not "nowhere in the view layer", so it is a follow-the-subject case.

## Verification

Four mutations, each verified-mutated by re-reading the file and restored from a scratchpad copy:
re-export of `_driving_data` dropped → contract names it; a **deferred** upward import inside
`_corridor_chips` → layering guard fails; `dpFind` removed from `driving.py` → repointed
page-memory guard fails; plus the enumeration guard's live failure above.

**Two falsifications were themselves wrong first, both flattering.** They are recorded because
each looked exactly like "this guard cannot fail":

1. `dpFind` removed from `driving.py` — the first attempt replaced only the **first** of two
   occurrences, so the guard stayed green. **Count the anchor; replace all of them.**
2. `id=dpFind` → `id=dpFindZ` for the `test_gantt_find_coverage` guard — all occurrences
   replaced this time, and the guard *still* passed. The assertion is `"id=dpFind" in src`, and
   `id=dpFind` is a **substring of** `id=dpFindZ`. **A suffixed mutation does not remove a
   substring anchor.** The working mutation was a same-length non-superstring (`id=dpQind`).

The general rule both cases point at: after mutating, assert the ORIGINAL anchor is absent from
the re-read file — do not assume a substitution removed what it was aimed at.

## Consequences

- Twelve page families remain (`evolution` 429, `integrity` 402, `margin` 379, …). Each must add
  its module to `LAYER_ORDER` and `VIEW_MODULES`; the contract test says so by failing.
- Every future slice must run the monkeypatch sweep over **all** names the new module binds, and
  must check whether its family is renderable by any fixture *before* quoting a render diff.
