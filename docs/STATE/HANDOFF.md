# Handoff — 2026-07-21e (Acumen-parity CPLI stored-float; v1.0.89; highest ADR 0279)

> ## STATUS (current) — after the milestone-scope correction (ADR-0278, PR #425 merged), continued the Acumen-parity work using the operator's committed ground-truth. **Root-caused and shipped CPLI (DCMA-13) parity as a configurable option (ADR-0279).** Highest ADR **0279**.
>
> - **CPLI ground truth (Acumen "Ribbon Analysis" sheet in the committed Quick-Add-Metrics workbook):**
>   File 1 **0.97**, File 2 **0.59**. Ours was **1.00** for both. Root cause: we compute CPLI from the
>   recomputed pure-logic CPM (min float ~0 → 1.0); Acumen uses the file's **stored, progress-aware
>   Total Slack** AND the **stored project finish** for the remaining length. Our pure-logic CPM
>   collapses File 2's finish to ~2025 (78-day remaining) vs the stored ~2028 (~1053 d), so the two
>   stored inputs are **inseparable** (stored float + recomputed length gives File 2 a nonsense −4.55).
> - **Shipped (ADR-0279):** `compute_dcma14(..., cpli_stored_float=False)` + `audit_schedule` forward
>   it; `_cpli` gains the stored mode (project float = `min effective_total_float` over `non_summary`;
>   length = `max stored finish − status`). **Re-verified EXACT: File 1 0.9698≈0.97, File 2 0.5863≈0.59.**
>   `SessionState.dcma_cpli_stored_float` (default off), `_scope_signature` `C=1` only when on, a 2nd
>   checkbox on the `/analysis` DCMA form → `/dcma/scope` (composes with milestone `M=1`). **Default off
>   byte-identical; P2/P5 CPLI stays 1.0 even ENABLED** (their min stored slack is +1 d vs a long length
>   → rounds to 1.00). Tests: `test_dcma14.py` (+2), `test_dcma_scope.py` (+1). v1.0.88 → **1.0.89**,
>   wheel + 9 installers.
> - **Acumen parity status now:** Hard (05) & Negative Float (07) UID-exact via milestone scope (ADR-0278);
>   **CPLI (13) exact via stored-float (ADR-0279)**; High Float (06) keeps milestones (correct). Two
>   Acumen-parity toggles on `/analysis` (milestone scope + stored-float CPLI), both default-off.
> - **Still open (need operator's Acumen-side input):** **Logic 01** — Acumen's own exports disagree
>   (ribbon 0 vs 8 vs detail 5); it flags 5 fully-linked tasks under a *different definition* than our
>   missing-pred-OR-succ. Needs the operator's Acumen Logic metric setting. The **~24-task** `Excluded`/
>   LOE population (Acumen workspace-side, ADR-0278) — confirm in Acumen. **BEI** 0.52/0.53 vs our 0.51.
> - **Sandbox:** `scratchpad/acumen_parity/` (`FINDINGS2_GROUNDTRUTH.md` + set-diff/CPLI scripts +
>   converted `file1.xml`/`file2.xml` + decompressed `.afw`). Big binaries NOT committed.
> - **State:** v1.0.89; **ADR-0279** highest; wheel + 9 installers lockstep. Branch
>   `claude/conditional-branching-contingency-bi6g00` (fresh from merged main after #425). This session's
>   PR carries the CPLI stored-float option.
> - **NEXT (operator to steer):** confirm the Acumen-side Logic definition + the 24-task `Excluded`/LOE
>   set; BEI. Also still OWED: ADR-0261 PowerShell crash log + large dataset; ADR-0258 Claude-Design
>   portfolio prompt. Interactive-legend rollout DONE.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
