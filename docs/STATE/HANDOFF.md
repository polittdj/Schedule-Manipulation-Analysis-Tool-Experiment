# Handoff — 2026-07-21d (DCMA milestone scope — ground-truth CORRECTION; v1.0.88; highest ADR 0278)

> ## STATUS (current) — the operator committed the **ground-truth workbooks** (`00_REFERENCE_INTAKE/acumen_v8.11.0/Large Test File[2] Acumen DCMA 14 Point vs Program Results.xlsx` — Acumen's ACTUAL per-check flagged-task lists, + the `.afw` + the `.mpp` under `mpp/`). A **UID-level** re-verification (join: Acumen `Id`==our `unique_id`, `Description`==`name`, exact) **overturned part of ADR-0277** and is shipped as **ADR-0278**. Highest ADR **0278**.
>
> - **What the ground truth proved (File 1, on the committed `Large Test File.mpp`, 2126 tasks):**
>   milestone-exclusion is **UID-EXACT** for Hard (05: 1→0) and Negative Float (07: 41→35) on File 1
>   — every extra we drop is a milestone Acumen omits (File 2: 0 FN, small non-milestone residual =
>   the Acumen-side exclusion class) — and **safe** for SS-FF (04) and Logic (01). But **HARMFUL for
>   High Float (06): Acumen's 814 detail INCLUDES 7 milestones** with high stored float; excluding
>   them = 7 false negatives (under-report). ADR-0277 wrongly excluded 06.
> - **Shipped (ADR-0278):** narrowed `exclude_milestones` scope from {01,04,05,06,07} → **{01,04,05,07}**
>   (High Float 06 now KEEPS milestones — uses full incomplete population under both scopes). Engine
>   `dcma14.py` (06 → `incomplete`/`n_inc`), test updated (06 retains its milestone), the `/analysis`
>   toggle label corrected. Default **off** still byte-identical; **P2/P5 untouched**. v1.0.87 →
>   **1.0.88**, wheel + 9 installers. Re-verified UID-level: Hard=0 exact, NegFloat=35 exact, HighFloat=898 (0 FN).
> - **Two residuals RESOLVED as Acumen-side (not our bug), documented in ADR-0278:** (a) the **~24-task**
>   class Acumen omits from EVERY check (Resources 866 vs our 890, same 24 in High Float) is
>   **structurally indistinguishable in the `.mpp`**; the **`.afw`** (gzip→.NET) exposes a per-activity
>   **`Excluded`** field + a **`FilterActivityTypeLevelOfEffort`** filter ⇒ an Acumen workspace-side
>   exclusion/LOE classification — our engine is CORRECT to flag them. (b) **Ribbon vs detail** is
>   Acumen's own over-count (operator-confirmed in the sheet notes: Logic 8→5, SS-FF 93→73, Lags 8→5).
> - **Still open (need operator's Acumen-side input / bigger change):** **Logic 01** — Acumen flags 5
>   fully-linked tasks under a *different definition* than our missing-pred-OR-succ (we flag 2 others);
>   needs the operator's Acumen Logic metric setting. **CPLI** stored-float/stored-CPL (File 2 0.59
>   needs Acumen's stored critical-path length — real engine change). **BEI** 0.51 vs 0.52/0.53.
> - **Sandbox:** `scratchpad/acumen_parity/` (`FINDINGS2_GROUNDTRUTH.md` + all set-diff scripts +
>   converted `file1.xml`/`file1_committed.xml`/`file2.xml` + decompressed `.afw`). Big binaries NOT committed.
> - **State:** v1.0.88; **ADR-0278** highest (corrects 0277); wheel + 9 installers lockstep. Branch
>   `claude/conditional-branching-contingency-bi6g00` (fresh from merged main after #424). This session's
>   PR carries the ground-truth correction.
> - **NEXT (operator to steer):** confirm the Acumen-side config for the 24-task `Excluded`/LOE set and
>   the Logic definition; then CPLI stored-float/CPL; BEI. Also still OWED: ADR-0261 PowerShell crash
>   log + large dataset; ADR-0258 Claude-Design portfolio prompt. Interactive-legend rollout DONE.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
