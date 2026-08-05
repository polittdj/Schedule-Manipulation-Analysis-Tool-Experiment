# Handoff — 2026-08-05 (phase 3 slice 3: the evolution family + the pre-flight coverage check; ADR-0352; v1.0.167)

> ## STATUS (current) — **branch pushed, draft PR open.** ADR-0352, **v1.0.167**.
> ADR-0351 (slice 2, driving) **MERGED as `d0ca992`** (PR #541); ADR-0350 merged as `0674dd9`
> (#540). Slice 3 extracts the **/evolution page family → `web/evolution.py` (1,075 lines)**,
> `app.py` **19,139 → 18,128** (−1,011). Running total this session: **20,192 → 18,128**.
> Wheel + nine installers rebuilt at **v1.0.167**.
>
> ## THE PREFIX HEURISTIC UNDER-REACHED — THE CLOSURE DEFINES THE FAMILY
> Seeding only `_evolution_*` left `_trace_option_names` pulled by `_optioned_versions` and
> `_keep_hidden` pulled by `_trace_options_form` — helpers that would have STAYED in `app.py`.
> Seeding the trace-options pair too gives **16 names / 991 lines where every external referrer
> is `create_app`** (a route: stays put, imports downward). **The prefix finds a family; the
> closure defines it.**
>
> ## THE PRE-FLIGHT COVERAGE CHECK — RUN BEFORE CUTTING, AND IT PAID TWICE
> ADR-0351's rule, applied for the first time BEFORE the cut. Mutating each member **scoped to
> its own AST line span** and re-rendering gives a per-member map: `_evolution_body` 1 route ·
> `_completed_on_path_panel` 1 · `_whatif_added_rows` 4 · `_optioned_versions` (bytes change
> under `ignore_constraints=1`) · **`_counterfactual_panel` (107 ln) 0** ·
> **`_render_counterfactual` (179 ln) 0**. So the render diff IS meaningful here (unlike slice
> 2) — but for MOST of the slice, not all. Both facts measured, 286 uncovered lines named.
> **The first probe was INVALID and flattered the result:** it picked `class=sf-take` — a
> GENERIC class — and `str.replace()`d it file-wide, so 24 routes moved and the member looked
> well covered. **A file-wide substitution measures the ANCHOR, not the FUNCTION.** Span-scoped,
> the same member moves 0.
> **Oracle extended** with three `/evolution` query-param variants (`?target=1`,
> `?ignore_constraints=1&ignore_leveling=1`, `?target=1&cf_a=0&cf_b=1&tier=critical`) — a real
> gain: `_optioned_versions` went from unrendered to rendered. `cf_a`/`cf_b` still do not fire
> the counterfactual under the golden pair (same corpus limit as driving).
>
> ## PROOF
> Verbatim: 58 added (preamble + re-exports), **1 removed** (`urllib.parse` narrowed by
> `ruff --fix` once `urlencode`'s last consumer moved). **Per-definition byte-identity 16/16** —
> the load-bearing evidence for the two members nothing renders. **66/66 routes byte-identical**,
> tree md5-verified across the run.
>
> ## BOTH TRAPS AGAIN — AND LAST SLICE'S WIDENED SWEEP EARNED ITS KEEP
> **The SILENT monkeypatch fired for real:** `test_coverage_app_extra` patched
> `appmod.compute_path_evolution` then called `_evolution_data`. `app.py` **still binds** that
> name for its own callers, so the patch SUCCEEDS and does NOTHING once the callee moves. Now
> patches `evomod` — and reverting that one word turns the test RED, which is what proves the
> fix is load-bearing. **A second, subtler one:** `test_session_consistency` did
> `real = app_module.compute_cpm` merely to capture the real callable, then patched
> `state_module`; `ruff --fix` deleted `compute_cpm` from `app.py` entirely, so the READ raised
> `AttributeError`. It now reads from the module it patches. **ADR-0351's widened sweep (every
> name the new module BINDS, imported OR defined) found both** — the imports-only version would
> have missed the silent one. **A THIRD/FOURTH site surfaced only in the FULL SUITE:**
> `tests/perf/test_perf_regression.py` reads `app_module.compute_cpm` twice for the same reason.
> **A READ is a coupling too, and no `setattr` sweep sees it.** New standing sweep: parse `app.py`
> for the names it still binds, then flag any `app_module.<name>`/`appmod.<name>` in `tests/`
> naming something absent — repo-wide it found exactly these and nothing else. **ADR-0350's enumeration guard fired for the SECOND consecutive
> slice**, naming `evolution.py` and both guard files. Two for two.
>
> ## Verification
> Four mutations, each verified-mutated and restored from a scratchpad copy: dropped re-export →
> contract names `_evolution_body`; `evolution.py` removed from the whole-layer guard →
> enumeration test fails; **`evomod` → `appmod` revert → the coverage test fails**, proving the
> patch target matters rather than coincidentally passing; **deferred** upward import in
> `_delta_words` → layering guard fails.
>
> ## Next
> **Eleven page families remain:** `integrity` 402 · `margin` 379 · `trend` 348 · `ssi` 335 ·
> `mission` 304 · `how` 290 · `sra` 264 · `what` 257 · `where` 235 · `portfolio` 231 · `evm` 208 ·
> `forecast` 204. **Per-slice checklist, now four items:** (1) seed the closure by BEHAVIOUR not
> prefix; (2) add the module to `LAYER_ORDER` + `VIEW_MODULES` (the contract test fails until you
> do); (3) sweep monkeypatches over EVERY name the new module BINDS, imported or defined;
> (4) run the **span-scoped** pre-flight coverage probe BEFORE quoting a render diff.
> Then: **a fixture that fires a driving corridor AND /evolution's counterfactual** (one fixture
> may close both named gaps) · the three pages with no `page-lede` (`/briefing`, `/path`,
> `/compare`) · `/groups` "Activities" counting summary rows (ADR-0343) · the nine installers vs
> `-c constraints/known-good.txt` (62 lockstep tests, own unit) · Phase 6 docs.
> **Reserved for Fable 5 Max (ADR-0240), do NOT start on Opus:** **SRA-LEGACY** · ADR-0348's
> **`tod + per_day == 1440`** residual · **V3** (`engine/msp_filters.py`).
> **Operator only:** license selection · branch-protection contexts · intake re-upload ·
> proprietary-tool reruns · OR-04.
>
> ## Carried forward
> The `/analysis` focus→tip family is **load-sensitive** — passes in isolation, PASSED ON CI while
> failing locally, and a DIFFERENT member fails each run. Do NOT chase. Do NOT re-derive CC-01's
> "74 call sites". `pydantic>=2` is NOT a safe floor (2.6 is); `fastapi>=0.110` is an AIR-GAP
> VIOLATION (0.110.2 is the floor). **Run `ruff check .` — the WHOLE tree**, as **`python -m
> ruff`**. Never `git checkout <file>` to undo a mutation — `cp` from a scratchpad copy. The
> render oracle needs launch-token/pid normalization and `/api/system` excluded. **After mutating,
> assert the ORIGINAL anchor is ABSENT from the re-read file** (a suffix leaves it as a substring;
> a single-occurrence replace leaves the others). **The fast checks do NOT substitute for the full
> suite on a code-moving refactor** — slice 2's `__file__`-based guard was invisible to every
> cheaper check.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
