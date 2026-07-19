# Handoff — 2026-07-19d (ADR-0273: probabilistic branching — #331 Hulett #8, Opus Ultracode; v1.0.79; highest ADR 0273)

> ## STATUS (current) — operator said "do all you can without my files, continue with Opus Ultracode"; the #331 phase continues at Hulett #8: **probabilistic branching** — a discrete failure that inserts *rework* into the SSI Monte-Carlo in p% of iterations → the **bi-modal** finish distribution (a spike at "no failure" + a shifted lump when the rework happens) the deterministic plan hides (ADR-0273). v1.0.78 → 1.0.79. Unlike a risk (adds days to an EXISTING task), a branch is a NEW node on a chosen FS tie, so it participates in **merge bias** (only moves the finish when it drives). The core augmentation mechanism was **verified against the real compute_cpm BEFORE any code** (`scratchpad/branch_verify.py`).
>
> - **Engine (`sra.py`, additive — Law 2 clean):** `ProbabilisticBranch` spec (id, name,
>   probability, after_uid, before_uid, 3-point low/ml/high minutes). `_augment_with_branches`
>   inserts each fragnet ONCE: replaces the FS tie `after→before` with `after --FS0--> F
>   --FS(lag)--> before`, F a new leaf with **0 placeholder duration** (so F-at-0 == base,
>   byte-frozen; verified). `compute_sra_ssi` gains `branches`; F's ml=0 → point-mass 0 in the
>   anchor + no-fire iterations; `_branch_draws` fires + samples the fragnet on streams DISJOINT
>   from duration/risk draws; a fired iteration overrides F to a `_sample_triangular` 3-point draw.
>   `SSIResult.branches: tuple[SSIBranchStat,...]=()` (fired fraction, mean rework days, mean finish
>   Δ, applied/inert), appended last → inert to the finish-cdf + ssi==jcl pins. SSI-only (not
>   JCL/OAT/legacy). Inert branch (FS tie absent) disclosed, never silent.
> - **Web:** `SessionState.sra_branches`/`_seq`; `POST /sra/branch` (add/remove/clear; days→minutes;
>   distinct non-summary endpoints); `_schedule_branches(st)` threads `branches=` into all 5 SSI
>   `compute_sra_ssi` sites; a collapsible **"Probabilistic branches"** editor on `/sra` (form +
>   list + explainer of the merge-bias distinction); `_ssi_data` echoes per-branch stats +
>   `sra_ssi.js` renders a "Probabilistic-branch outcomes" table; the bi-modal finish shows in the
>   existing S-curve. Save/Load persists branches; wipe clears them; i18n +2 terms ×4 langs.
> - **Verified:** `tests/engine/test_sra_branching.py` (8: freeze, bi-modal split, certain-shift,
>   off-path no-op + overtake = merge bias, inert disclosure, determinism, zero-prob ignore);
>   `tests/web/test_sra_ssi_web.py` (+4: editor render, add→listed→bimodal payload, inert, clear).
>   **End-to-end through the web** on Project5 driving tie 131→142: fired ~40%, mean rework ~23 d
>   (=(10+20+40)/3), finish shifted by that amount (bi-modal). Full local gate green (ruff, format,
>   mypy 116, bandit, node, pytest). v1.0.78 → **1.0.79**, wheel + 9 installers in lockstep.
> - **Standing rule (from #412):** update `docs/STATE/LESSONS-LEARNED.md` DAILY — first-class state.
> - **Still OWED by the operator:** PowerShell crash log + real large dataset (ADR-0261
>   on-machine re-validation); Claude-Design prompt (Portfolio US-map/site drill, ADR-0258).
>   #13 XER per-task calendars PARKED.
> - **State:** v1.0.79; **ADR-0273** highest; wheel + 9 installers in lockstep. Branch
>   `claude/handoff-continuation-vistlu` (restarted from main after #414 merged). This session
>   merged #411 (LHS) + #414 (Gantt tint); the branching PR is the open PR at this snapshot.
> - **NEXT (file-free):** Hulett **#9 conditional branching** (Alt-A/Alt-B contingency switching —
>   builds on #8's augmentation; a larger design) is the last non-deferred Hulett item (#13
>   resource-leveled iterations is deferred/out-of-scope). Then re-read #331 for anything else, or
>   the 3 OWED operator inputs (ADR-0261/0258). Keep the daily LESSONS-LEARNED entry.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
