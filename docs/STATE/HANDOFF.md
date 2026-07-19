# Handoff — 2026-07-19a (ADR-0270: correlation matrix + eigenvalue feasibility — #331 item 2, Opus Ultracode; v1.0.75; highest ADR 0270)

> ## STATUS (current) — operator said "do all you can without my files, continue with Opus Ultracode", so the #331 phase continues: shipped a costed-MSPDI import-path JCL test (#408, merged), then built the correlation MATRIX + eigenvalue feasibility feature (ADR-0270) end-to-end via a design workflow + independently-verified numerics. Version 1.0.74 → 1.0.75 (wheel + 9 installers in lockstep). Design authored by a 3-proposal × adversarial-pressure-test × synthesis Workflow; every hand-computed constant re-verified by the lead against a std-lib prototype before implementing.
>
> - **Engine:** new pure-std-lib leaf `engine/correlation.py` (no numpy, no sra/jcl import —
>   no cycle). `CorrelationSpec` (pairwise pairs + shared-driver GROUPS, Hulett) →
>   `build_matrix` → cyclic **Jacobi** eigen (with the MANDATORY zero-off-diagonal skip guard —
>   a mixed correlated/independent matrix would else ZeroDivisionError; pinned by a mixed test)
>   → feasibility (min-eigenvalue PSD test) → **spectral-clipping** repair (clip to +ε floor,
>   reconstruct, renormalize diagonal — a congruence, PD-preserving by Sylvester inertia;
>   chosen over Higham for auditability, raw min-eig + Frobenius distance surfaced so never
>   silent) → **robust_cholesky** (zero-pivot→zero column, used on BOTH paths so a feasible ρ=1
>   all-ones block samples as a zero column, not a crash). `prepare_correlation` order is
>   load-bearing (None/`<2`-uncertain/identity → scalar fallback).
> - **Shared sampler (the freeze discipline):** extracted the duplicated per-iteration duration
>   draw from compute_sra_ssi + compute_jcl into ONE `_iteration_duration_overrides(rng, config,
>   uids, three, prepared)` — landed as a PROVEN no-op refactor FIRST (78 freeze tests
>   byte-identical) before the matrix branch. `prepared is None` → the exact scalar statements,
>   byte-frozen (incl. the pert-uses-triangular-when-r>0 quirk + point-mass-no-draw). `prepared`
>   set → multivariate copula x=Lz, a DISTINCT mode (N idiosyncratic, no common draw), OVERRIDES
>   the scalar correlation; both engines call the identical helper so ssi==jcl finish marginal
>   holds under a matrix too (pinned). SSIResult/JCLResult gain 4 default-valued provenance
>   fields (applied/repaired/min_eigenvalue/frobenius_distance), inert to the finish-cdf pin.
> - **Web:** SessionState sra_corr_pairs/sra_corr_groups; POST /sra/correlation-matrix
>   (add-pair/add-group/clear, ρ∈[-1,1] negatives allowed, unknown/summary uids dropped,
>   SEC-2-gated); `_correlation_spec(st)` threads correlation_matrix into all 5 SRAConfig
>   builders; a `/sra` editor panel (lists pairs/groups, clear) + a post-run `#corrBadge`
>   feasibility badge fed from provenance ("feasible (min eig …)" / "infeasible input repaired
>   … Frobenius …") rendered by both sra_ssi.js and sra_jcl.js; i18n +6 terms ×4 langs.
> - **Verified:** tests/engine/test_correlation.py (14 hand-computed pins: 2×2 {0.4,1.6} +
>   Cholesky [[1,0],[0.6,0.8]]; infeasible ρ=-0.6 {-0.2,1.6,1.6}; clip→exact E(-0.5) +
>   Frobenius √0.06; both zero-pivot singular cases; the mixed-matrix skip guard) +
>   test_sra_ssi.py matrix cases (widen, distinct-from-scalar, repair provenance, <2 fallback)
>   + test_jcl.py ssi==jcl-under-matrix + tests/web/test_correlation_web.py (8). 801+ engine/web
>   tests green; mypy clean (116 files). **Browser verification of the panel still OWED this
>   session** (run before final ship if not yet done — see NEXT).
> - **Still OWED by the operator:** PowerShell crash log + real large dataset (ADR-0261
>   on-machine re-validation); Claude-Design prompt (Portfolio US-map/site drill, ADR-0258).
>   #13 XER per-task calendars PARKED.
> - **State:** v1.0.75; **ADR-0270** highest; wheel + 9 installers in lockstep. Branch
>   `claude/handoff-continuation-vistlu`. This session already MERGED #407 (docs) + #408
>   (costed-MSPDI test). Correlation feature committed but PR not yet opened at this snapshot.
> - **NEXT:** open the correlation PR, get CI green, merge. Then the remaining #331 items,
>   none needing operator files: the **STAT/GAO scorecard gap audit** (#12 — likely
>   confirm-complete, scorecards already ship all 11 STAT + 10 GAO checks), **Latin Hypercube
>   sampling** (Hulett #11), and the **risk-critical Gantt tint** (Hulett #12). The 3 OWED
>   operator inputs still block ADR-0261/0258.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
