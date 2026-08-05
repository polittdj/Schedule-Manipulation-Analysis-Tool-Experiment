# ADR-0352 — Phase 3 slice 3: the evolution family, and the pre-flight coverage check

- **Status:** Accepted
- **Date:** 2026-08-05
- **Continues:** ADR-0350 (the shared kernel), ADR-0351 (driving — the first per-page module)
- **Related:** ADR-0297 (the monkeypatch trap), ADR-0349 (the source-text trap), ADR-0011,
  ADR-0201, ADR-0320

## Decision

**Extract the /evolution page family — verbatim — into `web/evolution.py` (1,075 lines):** the
page body, the completed-on-path and counterfactual panels, `_render_counterfactual`, the
evolution/tier data builders, and the shared trace-options controls. `app.py` **19,139 →
18,128** (−1,011). `LAYER_ORDER` becomes `state → chrome → components → driving → evolution →
app`.

**The prefix heuristic under-reached, and the closure said so.** Seeding only `_evolution_*`
left `_trace_option_names` pulled by `_optioned_versions` and `_keep_hidden` pulled by
`_trace_options_form` — two helpers that would have stayed in `app.py`. Seeding the
trace-options pair as well gives **16 names / 991 lines in which every external referrer is
`create_app`** — a route, which stays put and imports downward. The prefix is a convenience for
*finding* a family; the closure is what *defines* it.

## The pre-flight coverage check — new, and it is the point of this ADR

ADR-0351 ended with a rule: *check whether the family is renderable by any fixture BEFORE
quoting a render diff.* This is the first slice to run that check **before cutting**, and it
paid twice.

Mutating each member inside `app.py` — **scoped to that member's own line span** — and
re-rendering gives a per-member coverage map:

| member | routes moved |
| --- | ---: |
| `_evolution_body` | 1 (`/evolution`) |
| `_completed_on_path_panel` | 1 |
| `_whatif_added_rows` | 4 |
| `_optioned_versions` | (page bytes change under `ignore_constraints=1`) |
| **`_counterfactual_panel`** (107 ln) | **0** |
| **`_render_counterfactual`** (179 ln) | **0** |

So the render diff *is* meaningful here — unlike ADR-0351's family, where it was worth nothing —
but it is meaningful for **most** of the slice, not all of it. Both facts are now measured rather
than assumed, and the 286 uncovered lines are named.

**The first version of that probe was invalid, and the failure mode is worth recording.** It
picked `class=sf-take` as `_render_counterfactual`'s anchor and `str.replace()`d it across the
whole file — `sf-take` is a *generic* class, so 24 routes moved and the member looked
well-covered. **A file-wide substitution measures the anchor, not the function.** The corrected
probe replaces only within the member's AST line span, and the same member then moves **0**.

**The oracle was also extended** with three `/evolution` query-param variants
(`?target=1`, `?ignore_constraints=1&ignore_leveling=1`, `?target=1&cf_a=0&cf_b=1&tier=critical`),
because a bare `/evolution` leaves `_optioned_versions` and the counterfactual gate unrendered.
That is a real coverage gain: `_optioned_versions` moved from unrendered to rendered. `cf_a`/`cf_b`
still do not fire the counterfactual under the golden pair — the same corpus limitation ADR-0351
recorded for driving.

## Proof

- **Verbatim.** Non-blank multiset: 58 added (the new module's preamble + the re-export block),
  **1 removed** — `from urllib.parse import quote, urlencode, urlparse, urlsplit`, which `ruff
  --fix` narrowed because `urlencode`'s last consumer moved.
- **Per-definition byte-identity vs the pre-move source: 16/16 identical.** This is the load-bearing
  evidence for `_counterfactual_panel` and `_render_counterfactual`, which no fixture renders.
- **66/66 routes byte-identical** on the extended oracle, tree md5-verified across the run.

## Both traps, again — and the sweep that was widened last time earned it

- **The silent monkeypatch fired for real.** `test_coverage_app_extra` patched
  `appmod.compute_path_evolution` and then called `_evolution_data`. `app.py` **still binds**
  `compute_path_evolution` for its own callers, so the patch succeeds and does nothing once the
  callee moves. It now patches `evomod` — and reverting that single word turns the test red,
  which is what proves the fix is load-bearing rather than incidental.
- **A second, subtler one.** `test_session_consistency` did `real = app_module.compute_cpm` purely
  to capture the real callable, then patched `state_module`. `ruff --fix` removed `compute_cpm`
  from `app.py` entirely once its last consumer moved, so the *read* raised `AttributeError`. It
  now reads from the module it patches, which is what it should always have done.
- **ADR-0351's widened sweep found both**, because it covers every name the new module BINDS —
  imported or defined. The narrow version (imports only) would have missed
  `compute_path_evolution`'s silent case exactly as it missed driving's.
- **A THIRD and FOURTH site of the read-coupling, found only by the full suite.**
  `tests/perf/test_perf_regression.py` does `real_cpm = app_module.compute_cpm` twice, for the
  same reason `test_session_consistency` did — capture the real callable, patch `state_module`.
  Neither the monkeypatch sweep nor any fast check sees this: it is an attribute **read**, not a
  `setattr`, and it is only reachable at test runtime. **A new standing sweep** now covers it —
  parse `app.py` for every name it still binds, then flag any `app_module.<name>` / `appmod.<name>`
  access in `tests/` naming something absent. Run repo-wide, it found exactly these two plus the
  already-fixed one, and nothing else.
- **ADR-0350's enumeration guard fired for the second consecutive slice**, naming `evolution.py`
  and both guard files. Two for two on real cuts.

## Verification

Four mutations, each verified-mutated and restored from a scratchpad copy: dropped re-export →
contract names `_evolution_body`; `evolution.py` removed from the whole-layer guard →
enumeration test fails; **the `evomod` → `appmod` revert** → the coverage test fails, proving the
patch target matters; a **deferred** upward import inside `_delta_words` → layering guard fails.

## Consequences

- Eleven page families remain. Each must: seed the closure by **behaviour, not prefix**; add its
  module to `LAYER_ORDER`/`VIEW_MODULES`; sweep monkeypatches over every bound name; and run the
  **span-scoped** pre-flight coverage probe before quoting a render diff.
- The named gap from ADR-0351 stands and now covers two families: no fixture produces a driving
  corridor, and none fires `/evolution`'s counterfactual. One fixture may close both.
