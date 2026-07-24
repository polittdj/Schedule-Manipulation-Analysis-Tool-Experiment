# Handoff — 2026-07-24 (Acumen-parity DCMA-09 scoped to Baseline Duration > 0; UID-exact on File2; v1.0.92; highest ADR 0283)

> ## STATUS (current) — root-caused the operator's "why does POLnRIS's DCMA-14 differ from Acumen
> Fuse?" question against the fresh **Large Test File2** (2,124 activities, DD 2025-03-10) + its Acumen
> ribbon/detail exports, and shipped the one genuine residual as **ADR-0283**. Version **1.0.92**.
> Highest ADR **0283**. Branch `claude/smat-tool-continuation-uskbh7` (from `origin/main` at `df68be7`).
>
> - **Primary finding (no bug): the operator's screenshot was DEFAULT (pure-logic) mode.** The engine
>   reproduces every screenshot value **byte-for-byte** in default mode (Logic 3, SS/FF 98, High Float
>   717, Neg Float 123, Resources 864/919, Missed 1221/1357, CPLI 1.0, BEI 0.51, Invalid 182). With
>   **Acumen-parity mode ON** it already matched Acumen's ribbon on **12/14** checks and Acumen's
>   *detail* (distinct activities) on the SS/FF + Lags counts the ribbon over-counts by counting links.
> - **The one real residual: DCMA-09 Invalid Dates** (parity 182 vs Acumen detail 173 = 170 forecast +
>   3 actual). Set-differencing: we caught ALL 173, plus **9 extra**, every one with **no baseline
>   duration** (8 milestones + 1 completed task with a future actual). The NASA `.aft` shows the
>   `9. Invalid Forecast/Actual Dates` metrics carry the SAME `PrimaryFilter` as the other work checks
>   — **`Baseline Duration > 0`** — which ADR-0280 applied everywhere EXCEPT DCMA-09.
> - **Fix (ADR-0283, parity-only):** `compute_dcma14` scopes the DCMA-09 loop + population to
>   `ap_tasks` (the baselined population) when `acumen_parity=True`; default (`ap_tasks is tasks`) is
>   **byte-identical** (still 182). Parity → **173, UID-exact vs Acumen detail** (0 FP, 0 miss). Each
>   date condition self-excludes the wrong completion state, so the single combined loop == Acumen's
>   two separately-filtered metrics. Test `test_acumen_parity_invalid_dates_scoped_to_baselined_population`
>   (fails on pre-fix engine `{1,2,3}`, passes after `{1}`). Docs: `docs/ACUMEN-PARITY-MODE.md` (new
>   check-9 row + example 6). Wheel + 9 installers regenerated to 1.0.92 (lockstep green).
> - **Gate:** `test_dcma14.py` 26 green; `-m parity` 44 green; installer/packaging 21 green. (Run the
>   FULL gate — ruff/format/mypy/bandit/pytest cov/node — before the squash-merge.)
> - **NEXT — still-open, separate PRs (do NOT fold):** **ADR-0282** — decide findings/narrative source
>   under parity; File2 IS the "two audits disagree on a finding-driving check" case the operator asked
>   for (default vs parity differ on High Float/Neg Float/Resources/Missed/CPLI/BEI). Recommend Option A
>   (findings follow parity when parity is on) — needs operator sign-off + fresh parity-variant goldens.
>   **Fix E** — cross-project UID leak in `_render_target_control` + `_endpoint_banner` (xfail test 7
>   ready to un-xfail; sub-question: should the target dropdown list other projects' milestones at all).
>   Then the deferred perf backlog (lazy status-UID trim, home.js pre-read, monolith split, …).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
