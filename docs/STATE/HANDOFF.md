# Handoff — 2026-07-23b (validated multi-project performance fixes; byte-identical numbers; v1.0.91; highest ADR 0282)

> ## STATUS (current) — implemented the four **sandbox-validated** performance fixes from the
> 2026-07-23 audit-validation session (ADR-0281). **Every number is byte-identical** — this is a
> speed/robustness change only (Law 2). Version **1.0.91**. Highest ADR **0282** (a *proposed* open
> question, no code). Branch `claude/multi-project-perf-fixes-khihxv` (fresh from `origin/main` at
> `f551b01`).
>
> - **Tests committed FIRST (fail on main), then the fixes turned them green** — op-count/equality
>   pins per ADR-0249: `tests/web/test_dashboard_perf_contract.py` (dashboard builds 0 full analyses;
>   warm-served past the LRU cap; single-flight; 1×/1× deps; **golden payload SHA-256**; wipe/epoch
>   guards; xfail cross-project leak) + `tests/web/test_upload_dedup_scaling.py` (O(M) dedup).
> - **A′ dashboard card tier:** new `_DashCore` (the 3 card fields projected, ~1 KiB, no citation
>   pins) + `SessionState.dash_cores` (plain dict, epoch-keyed like `cpms`, cleared on wipe) +
>   `dashboard_core_for` (3 tiers: resident core → project a full analysis → compute only audit +
>   zero-float band off the solve). `_dashboard_data` reads the core. **No more LRU thrash past N=48.**
> - **B single-flight:** 64 striped locks + `_stripe_for`; `analysis_for` / `cpm_scoped_for` take the
>   stripe OUTSIDE `_lock` and re-derive `ck`/`gen`/`parity` inside it, compute once, store under the
>   `wipe_gen` guard. Exceptions propagate to every waiter; unrelated keys stay concurrent.
> - **C compute deps once:** `recommend(precomputed_audit=, precomputed_compliance=)`,
>   `build_narrative(precomputed_findings=)`; `_compute_analysis` computes audit + compliance once and
>   threads them (3×/3×/2× → 1×/1×/1×). **Deliberate pin:** parity mode still derives findings from the
>   DEFAULT audit (byte-identical) — the "should findings follow the parity audit?" question is filed
>   as **ADR-0282** for the operator, NOT changed here.
> - **D linear dedup:** `/upload` builds a `(hash, folder)→first-key` index once per batch; O(1)
>   lookup, first-loaded-wins, folder-context rules preserved.
> - **Gate:** full `pytest` green (2624 passed, 1 xfail = the Fix-E leak) once the wheel + 9 installers
>   were regenerated to 1.0.91 (installer lockstep green); `-m parity` 44 green; ruff/mypy-strict/bandit
>   clean on all changed files; `node --check` clean. (Pre-existing `ruff format` drift on `docs/*.md`
>   from a newer local ruff formatting embedded code blocks — NOT touched, not mine.)
> - **NEXT — deferred follow-ups in order (separate PRs; do NOT fold together):** **Fix E** —
>   active-population scoping of `_render_target_control` + `_endpoint_banner` (real cross-project UID
>   leak; un-xfail test 7; decide with operator whether the target dropdown should list other projects'
>   milestones at all). Then: lazy status-UID payload trim (486 KB → ~40 KB @ 50 versions); home.js
>   bounded-concurrency pre-read; manifest-projection memo; instrument-then-byte-budget the
>   `cpms`/`summaries` tiers; MPP capability probe; importer profiling; `web/app.py` monolith split
>   (never with a behavior fix). And **ADR-0282**: settle the parity-findings source with the operator.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
