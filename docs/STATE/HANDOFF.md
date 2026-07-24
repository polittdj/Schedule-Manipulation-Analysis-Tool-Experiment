# Handoff — 2026-07-24c (ADR-0282 resolved as Option A: findings/narrative/briefing follow the parity audit; v1.0.94; highest ADR 0285)

> ## STATUS (current) — resolved the last queued open question. The operator chose **Option A** for
> ADR-0282, shipped as **ADR-0285**: when Acumen-parity mode is ON, the findings, narrative, risk
> matrix and executive briefing all derive from the **parity** audit, so every surface agrees with the
> ribbon. Version **1.0.94**. Highest ADR **0285**. Branch `claude/smat-tool-continuation-uskbh7`
> (restarted fresh from `origin/main` at `17431a6` after PR #431 / ADR-0284 squash-merged).
>
> - **What changed:** a single `acumen_parity` flag threaded through every findings-derived surface —
>   `recommend(..., acumen_parity=)` (sources `_dcma_findings` from the parity audit),
>   `build_narrative(..., acumen_parity=)` (its fallback `recommend`), `build_briefing(...,
>   acumen_parity=)` (BOTH the audit driving `dcma_fails`/**verdict** and its `recommend`), and the web
>   call sites `/risks`, `/export/*/risks`, `/briefing`, `/export/*/briefing`, `/api/ai/briefing`,
>   `_the_briefing_header`. This also closed a real gap: the `/briefing` header was parity-aware while
>   its BODY was not.
> - **The ADR-0281 pin is gone:** `_compute_analysis` now passes its parity-aware audit as
>   `precomputed_audit` in BOTH modes, so parity mode dropped from **2×/1×/1× to 1×/1×/1×** audit /
>   compliance / recommend (a free perf win alongside the behaviour fix).
> - **Default is byte-identical** (verified on the 2,126-task golden: `recommend(sch)` ==
>   `recommend(sch, acumen_parity=False)`, same for `build_narrative`). **Baseline compliance is
>   mode-independent** (one Acumen-validated definition), so only DCMA-check findings move.
> - **No golden re-pin was needed.** A read-only survey confirmed there are NO stored findings/
>   narrative/briefing/risk-matrix goldens (all inline + default-mode), and the `ai.citations`
>   re-verification tests are literal-fixture / mode-independent — so ADR-0282's feared citation re-pin
>   did not materialize. The parity dashboard SHA is audit-only and unaffected.
> - **Tests:** new `test_acumen_parity_findings_follow_the_parity_audit` (a no-baseline past-date task
>   is a DCMA-09 CONCERN in default, absent under parity; default byte-identical); rewrote the two pins
>   that encoded the OLD behaviour — `test_cold_analysis_parity_mode_computes_each_dependency_once`
>   (now `(1,1,1)` / flags `[True]`) and `test_findings_and_narrative_follow_the_active_audit_per_mode`.
>   Refreshed the module docstring (points 4 and 7). Docs: ADR-0285, ADR-0282 marked resolved,
>   `docs/ACUMEN-PARITY-MODE.md` notes the toggle applies end-to-end.
> - **Gate:** full suite **2627 passed** at the pre-version-bump checkpoint (only the expected wheel
>   lockstep failed, then fixed by regenerating); ruff / ruff format / mypy-strict / bandit /
>   `node --check` clean; installer+packaging 21 green at 1.0.94. **Re-run the FULL gate before the
>   squash-merge.**
> - **NEXT — the queue is clear; remaining backlog is the deferred perf work** (separate PRs, never
>   folded with a behavior fix): lazy status-UID payload trim (486 KB → ~40 KB @ 50 versions); home.js
>   bounded-concurrency pre-read; manifest-projection memo; instrument-then-byte-budget the
>   `cpms`/`summaries`/`dash_cores` tiers; MPP capability probe; importer profiling; the `web/app.py`
>   monolith split. Also still OWED by the operator: the ADR-0261 PowerShell crash log; the
>   Claude-Design portfolio prompt. Consider committing the newer `20260708` `.aft` + refreshing
>   `test_aft_formula_audit.py`.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
