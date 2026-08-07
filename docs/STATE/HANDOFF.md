# Handoff — 2026-08-07 (triple session: full read-only audit · FX fixture verdicts · intake guard re-greened; no new ADR; v1.0.176)

> ## STATUS (current) — **pushed, draft PR open** on `claude/schedule-tool-audit-hhjbtp`
> (branched fresh from `main` cac9bea after #552 squash-merged at 19:46Z). **Docs + one
> test pin only — NO shipped code changed** (no version bump, no installer rebuild; still
> ADR-0365, **v1.0.176**, SCHEMA 2.11.0). This commit re-greens `main`: the operator's
> 2026-08-07 16:39Z web upload (16 FX files + `FX.afw`, commits 9ba7203/cac9bea) landed
> AFTER slice 7's manifest regeneration, so `tests/guards/test_intake_manifest.py` was
> RED on main (4 tests). Fixed by regeneration: **416 → 433 tracked files, mismatches
> stay 99**, CLAUDE.md count updated, and the `.mpp` census pin moved 22 → **28** (the
> six FX conversions, all verified genuine OLE2; pin mutation-proven able to fail).
>
> ## What else this session produced (evidence OUTSIDE the repo, delivered to operator)
> 1. **Full adversarial read-only audit at cac9bea** (per the operator's ChatGPT audit
> spec; evidence package in the session workspace, 10 deliverables + harnesses, repo
> untouched). Headlines: statics + suite green except the intake guard (now fixed);
> "UniversalProjectReader rejects Project2.mpp" REFUTED (28/28 .mpp read by both readers
> — the old failure was the broken host Java loader); "dashboard recomputes per project"
> REFUTED empirically at HEAD (warm / = 0 solves; upload precomputes); REAL findings:
> `/briefing` does 4 uncached CPM solves + a duplicate DCMA audit on EVERY request
> (build_briefing rebuilt by 4 callers; ~0.56 s with two 9 MB files) · sub-day
> counterfactual effects render "no effect" (`round()` at change_effects.py:117-123,
> exactly-half-day drops via banker's; NO fractional-day test exists) · `_baselined`
> (dcma14.py:84-85) excludes ALL milestones from the parity population — CLAUDE.md says
> "milestones kept", and Fuse's NASA-lib Missing Logic COUNTS the TP4 milestone UID 26
> (parity 0 vs Fuse 1; ordinary matches) · /integrity omits the change-effects panel
> silently on unmeasurable targets; skipped changes disclosed count-only · FX-06's
> baseline finding names UID 131 but shows NO magnitude/old-new dates · ~150 MB RSS
> retained per loaded 9 MB .mpp, no per-file unload · Negative Float has NO formula in
> the AFT (prose only) — sub-day semantics ORACLE-GATED · 3 web tests call GET /target
> where only POST exists (silently not exercising focus).
> 2. **FX fixture verdicts (operator had already run Fuse — exports committed).**
> FX-01: Fuse Days Late EXCLUDES milestones (8 unchanged). FX-02: CLAMPED at zero (4,
> not −2). FX-05: Missing Preds +1 as predicted but Missing Logic +3 (two dropped links
> open THREE ends — 142/131/141; SMAT matches Fuse UID-exactly 5→8). FX-03/FX-04:
> **MS Project silently REVERTED both duration cuts on XML import** (Duration re-derived
> from stale stored dates) — their .mpp/Fuse numbers oracle the UNCHANGED schedules;
> operator re-export needed. SMAT-side positive controls ran on the authored XMLs and
> PASSED EXACTLY (+10 wd / +15 wd; /integrity renders "restore UID 17 … +10 wd").
> FX-06 trap PASSED: finish frozen AND a HIGH DECM-29I401a baseline finding.
>
> ## Next
> Phase 3 monolith split resumes at **mission 304** (stale census — RE-MEASURE the
> closure first; expect sra ~700+ over its "264"). NEW queue items from the audit
> (P0 first): sub-day effect display (keep minutes; "<1 wd" label; F1/F7) · parity
> milestone-population decision (F5 — re-pin against the ADR-0280 Large-Test oracles
> BEFORE changing; doc contradicts code either way) · /briefing memoisation (P1) ·
> integrity disclosure (target-unavailable banner, skipped identities, baseline-finding
> magnitude; F2/F4). Then the standing queue: stored-SRA-fields MSPDI fixture ·
> driving-corridor fixture · three page-lede-less pages · /groups Activities (ADR-0343)
> · installers vs known-good constraints · P80/P90 recurring-exception residual · Phase 6
> docs. **Operator:** re-convert FX-03/04 (verify UID17=5d/UID131=1w BEFORE save; F9;
> finish must move) + re-run Fuse · one Acumen run on a crafted sub-day-negative-float
> schedule closes the O1 oracle gap · license · branch-protection · proprietary reruns ·
> OR-04 · July mpp/ re-export decision.
>
> ## Carried forward
> ADR-0353..0365 closed — do not re-open. Highest ADR stays 0365 (this session: docs +
> one test pin, no ADR-worthy decision). MS Project XML import DERIVES Duration from
> stored dates — a duration-only fixture whose stored dates disagree gets silently
> un-edited on .mpp conversion; future duration fixtures must carry recalc-consistent
> stored dates. SMAT floors predecessor-less unstarted tasks at stored start
> (cpm.py `_stored_date_bounds`) — an unmoored task does NOT slide to the data date;
> FX-05's isolated rows {+0, −29} with joint 0 are the canonical non-additivity exhibit.
> Parity evidence is three-tiered (runtime external oracle / transcription / engine-
> pinned) — never report it as uniform equivalence. The strongest external-oracle parity
> tests skip without Java — check whether CI installs a JDK. A number written mid-session
> is not a measurement (wc decides). `grep -c` exits 1 on zero — chain with `;`. Full
> suite > 10-min foreground — background `python -u`, read the tail. The /analysis
> focus→tip family is load-sensitive — do NOT chase.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
