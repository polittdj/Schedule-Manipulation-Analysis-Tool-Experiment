# Handoff — 2026-07-23 (Acumen parity mode from the .aft — solves ALL DCMA parity; v1.0.90; highest ADR 0280)

> ## STATUS (current) — the operator supplied the **NASA Acumen metric library** (`NASA_Metrics_Complete_20260708.aft`, newer than the committed 20260423). Reading it verbatim **solved every remaining parity issue** and revealed my milestone toggle was a proxy. **Shipped ONE "Acumen parity mode" (ADR-0280) that reproduces Acumen UID-exact on all checks; supersedes 0277/0278, folds in 0279.** Highest ADR **0280**.
>
> - **The unifying rule (from the `.aft` `<PrimaryFilter>`):** every DCMA work metric filters on
>   **`Baseline Duration > 0`, truncated to WHOLE DAYS** (a sub-day baseline reads as 0) and sets
>   **`IncludeMilestone = 1`** (Acumen KEEPS milestones — the ones I excluded just have baseline dur 0;
>   milestone-ness was a coincidental proxy). Plus: **Resources** = `Baseline Cost = 0 AND Baseline
>   Work = 0` (NOT "no resource name" — this is the "24-task mystery": those have no baseline duration);
>   **float compared in whole days**; **BEI** two-term denominator; **CPLI** stored (ADR-0279).
> - **Verified UID-EXACT on BOTH files:** Hard 05, SS/FF 04, High Float 06, Neg Float 07, Resources 10,
>   Missed 11 all Id-exact; BEI 0.52/0.53; CPLI 0.97/0.59; Logic = Acumen **ribbon** (0/2; File-1
>   detail-of-5 is Acumen's own inconsistency). **P2/P5 golden byte-identical** (no sub-day baselines).
> - **Shipped (ADR-0280):** `compute_dcma14(..., acumen_parity=False)` + `audit_schedule` forward one
>   flag; retired `exclude_milestones`/`cpli_stored_float`. New `Task.baseline_work_minutes` (+importer
>   `<Baseline><Work>`). `SessionState.dcma_acumen_parity` (default off), `_scope_signature` `A=1`, ONE
>   `/analysis` checkbox + an example-driven explanation panel. Docs: `docs/ACUMEN-PARITY-MODE.md`
>   (the two views, real-world examples, when-to-use). Tests: `test_dcma14.py` (6 parity tests) +
>   `test_dcma_scope.py` (single toggle). Default off = byte-identical (golden green). v1.0.89 →
>   **1.0.90**, wheel + 9 installers.
> - **Retracted:** the ADR-0278 `.afw` `Excluded`/LOE hypothesis for the 24 tasks was WRONG — the real
>   discriminator is `Baseline Duration > 0` in the schedule.
> - **Sandbox:** `scratchpad/acumen_parity/FINDINGS2_GROUNDTRUTH.md` (the full `.aft` solution +
>   set-diff/verification scripts). The `.aft` lives in `00_REFERENCE_INTAKE/` (20260423 committed;
>   the 20260708 the operator uploaded is newer — NOT re-committed here).
> - **State:** v1.0.90; **ADR-0280** highest (supersedes 0277/0278, folds 0279); wheel + 9 installers
>   lockstep. Branch `claude/conditional-branching-contingency-bi6g00` (fresh from merged main after #426).
> - **NEXT (operator to steer):** operator has a **followup prompt queued** (said "tell me when ready").
>   Still OWED by operator: ADR-0261 PowerShell crash log + large dataset (they don't have it yet); the
>   Claude-Design portfolio prompt (not ready yet). Consider committing the 20260708 `.aft` + refreshing
>   `test_aft_formula_audit.py` to the newer library. Interactive-legend rollout DONE.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
