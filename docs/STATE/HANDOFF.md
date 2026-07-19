# Handoff — 2026-07-19b (ADR-0271: Latin Hypercube sampling — #331 Hulett #11, Opus Ultracode; v1.0.77; highest ADR 0271)

> ## STATUS (current) — operator said "do all you can without my files, continue with Opus Ultracode", so the #331 phase continues at Hulett #11: added a **Latin Hypercube (LHS) variance-reduction sampler** as a distinct opt-in mode on the SRA/JCL Monte-Carlo (ADR-0271), designed via a design Workflow whose load-bearing numerics were re-verified by the lead against a std-lib prototype (`scratchpad/lhs_verify.py`) BEFORE implementing. Version 1.0.76 → 1.0.77 (wheel + 9 installers in lockstep). Default sampler stays **"mc"** — the byte-frozen Monte-Carlo path is untouched.
>
> - **Engine (`sra.py`, no new module — LHS is a sampling MODE of the existing shared sampler):**
>   `_phi_inv` (std-lib probit via `NormalDist().inv_cdf`, input clamped to [1e-12, 1−1e-12] →
>   finite ±7.03 at the edges); `LatinHypercubePlan` + `_lhs_plan` (one stratified [0,1) column
>   per dimension on a DEDICATED disjoint RNG stream `_lhs_seed(seed)` — one draw per stratum,
>   Fisher-Yates shuffle per column, `centered` = midpoints); `_build_lhs_plan` (column count
>   EXACTLY matches the branch's per-iteration draw count: matrix N, scalar 1+D, independent D;
>   None when off or all-point-mass); `_lhs_overrides` (the three correlation branches, plan
>   columns replace the RNG draws in the EXACT current draw order, copula composition unchanged —
>   LHS-then-Cholesky under a matrix; probit for scalar common+idiosyncratic; stratified uniform
>   used directly as the copula uniform when r=0). `_iteration_duration_overrides` gains kw-only
>   `plan`/`iteration`; **`plan is None` (default) runs the exact MC statements byte-for-byte**.
>   `SRAConfig` +`sampling="mc"` +`lhs_centered=False`; SSIResult/JCLResult +`sampling` (default
>   "mc", appended last, inert to the finish-cdf pin). Both engines build the plan from identical
>   uids/three/prepared → **ssi==jcl finish marginal holds under LHS** for all 3 branches (pinned).
>   `pert` under LHS falls back to triangular (no std-lib PERT inverse — documented quirk).
> - **Web:** SessionState `sra_sampling`/`sra_lhs_centered` thread through POST /sra/ssi-run-config
>   into ALL 5 SSI/JCL SRAConfig builders (NOT the legacy compute_sra path); a Monte-Carlo /
>   Latin Hypercube radio + Centered checkbox + a plain-language explainer on `/sra`; run payloads
>   (`_ssi_data`/`_jcl_data`/`/api/sra`) echo `sampling`; Save/Load setup persists both; i18n
>   +"Centered" ×4 langs (method names stay untranslated). CSP-safe, no JS change.
> - **Verified:** `tests/engine/test_lhs.py` (27: freeze mc==default, stratification random+centered,
>   disjoint seed stream, Φ⁻¹ finiteness+round-trip, **>5× (≈45×) variance reduction vs MC**,
>   lhs≠mc but in-support, determinism, all-point-mass fallback, matrix widening, **ssi==jcl under
>   LHS × triangular/pert × r=0/0.3 × centered, + matrix**); `tests/web/test_sra_ssi_web.py` +3
>   (radio renders, MC pre-checked, sampling persists+echoes). Engine+web SRA suites green; ruff +
>   mypy (116 files) + bandit clean.
> - **Still OWED by the operator:** PowerShell crash log + real large dataset (ADR-0261
>   on-machine re-validation); Claude-Design prompt (Portfolio US-map/site drill, ADR-0258).
>   #13 XER per-task calendars PARKED.
> - **State:** v1.0.77; **ADR-0271** highest; wheel + 9 installers in lockstep. Branch
>   `claude/handoff-continuation-vistlu`. Prior session merged #407 + #408 + #409 + #410 (the #12
>   scorecard fix). LHS is the open PR at this snapshot.
> - **NEXT (all file-free, one gated PR each):** **risk-critical Gantt tint** (Hulett #12) — tint
>   the SSI grid Gantt bars by criticality index from the last MC run; a separate gated PR. The 3
>   OWED operator inputs still block ADR-0261/0258.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
