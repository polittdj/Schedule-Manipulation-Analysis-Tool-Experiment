# Handoff — 2026-07-21c (DCMA milestone scope — Acumen parity; v1.0.87; highest ADR 0277)

> ## STATUS (current) — operator delivered a real Acumen-vs-Program dataset (Large Test File / File2: `.mpp` + `.afw` + comparison workbooks) and asked to root-cause why our DCMA metrics differ from Acumen Fuse, test, and fix. **Deep forensic root-cause done** (converted `.mpp`→MSPDI via MPXJ, ran our engine, **set-differenced our offender lists against Acumen's actual flagged-ID lists**). **Shipped the one verified, parity-safe fix: a configurable DCMA milestone scope (ADR-0277).** Highest ADR **0277**.
>
> - **Verified root cause (milestones).** Excluding zero-duration milestones makes our offender SET
>   match Acumen EXACTLY on **Hard Constraints** (1→0) and **Negative Float** (41→35), and covers the
>   milestone share of High Float / Logic / SS-FF. Coherent rule: **work checks** (Logic 01, SS/FF 04,
>   Hard 05, High float 06, Neg float 07) omit milestones; **completion checks** (Missed 11, BEI 14)
>   KEEP them (a missed milestone is a real missed deliverable — excluding OVERSHOOTS Acumen, confirmed).
> - **Implementation:** `compute_dcma14(..., exclude_milestones=False)` + `audit_schedule` forward it;
>   `SessionState.dcma_exclude_milestones` (default off), added to `_scope_signature` ONLY when on (so
>   the default cache-key shape is unchanged, analysis re-keys on toggle → never a stale audit); a
>   checkbox on the `/analysis` DCMA panel POSTs `/dcma/scope`. **Default off = byte-identical to before,
>   P2/P5 goldens untouched** (verified default==exclude on P2/P5). Tests: `test_dcma14.py` (3 new) +
>   `test_dcma_scope.py` (toggle seam). Full local gate green. v1.0.86 → **1.0.87**, wheel + 9 installers.
> - **Root-caused but NOT shipped (documented in ADR-0277 + `scratchpad/acumen_parity/FINDINGS.md`):**
>   (a) **CPLI** 1.0 vs 0.97/0.59 — we use recomputed CPM float (≈0); Acumen uses STORED float. Stored
>   float nails File 1 (0.97 exact) but File 2 (0.59) needs Acumen's stored-schedule critical-path
>   length (our pure-logic CPM schedules a chain to 2025 the stored file puts in 2028) → a real engine
>   change. (b) A fixed **~24 non-milestone tasks** Acumen omits from EVERY check, structurally
>   indistinguishable in the `.mpp` (NOT resource/calendar/type/WBS/work/cost/create-date; operator
>   confirmed NO Acumen filter) — still UNEXPLAINED. (c) **BEI** 0.51 vs 0.52/0.53 (small). (d) the
>   ribbon-vs-detail counting basis for Logic/SS-FF/Lags/Invalid-Forecast (Acumen's own display
>   truncation; our diffs used the authoritative ribbon count).
> - **Sandbox preserved:** `scratchpad/acumen_parity/` (converted `file1.xml`/`file2.xml`, all
>   set-diff/verification scripts, `FINDINGS.md`). The 20 MB MSPDI + `.mpp` are NOT committed.
> - **State:** v1.0.87; **ADR-0277** highest; wheel + 9 installers lockstep. Branch
>   `claude/conditional-branching-contingency-bi6g00` (from merged main). This session's PR carries the
>   DCMA milestone scope.
> - **NEXT (operator to steer):** the CPLI stored-float / stored-CPL change (own PR, both files); the
>   24-task mystery (needs the operator's insight — maybe the `.afw` selection state, or a schedule
>   detail); BEI. Also still OWED: ADR-0261 PowerShell crash log + large dataset; ADR-0258 Claude-Design
>   portfolio prompt. Interactive-legend rollout (ADR-0276) is DONE.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
