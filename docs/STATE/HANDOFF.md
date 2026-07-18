# Handoff — 2026-07-18d (family-B basis unification ADR-0265: stepper/export/drill share one counterfactual basis; v1.0.71; highest ADR 0265)

> ## STATUS (current) — the automated build cycle continues: PR #400 (SEC-2/SEC-3, ADR-0264, v1.0.70) squash-merged at CI green; branch restarted; the queue's next item shipped — **ADR-0265 family-B basis unification** (the behavior work ADR-0251 queued). Version 1.0.70 → 1.0.71 (wheel + 9 installers in lockstep).
>
> - **ADR-0265 (one basis per counterfactual page):** (1) `/api/evolution` accepts the trace
>   options and applies `_optioned_versions`; `/evolution` embeds `data-ignore-*` attrs and
>   path_evolution.js forwards them — the stepper now reads the SAME re-solved network as
>   the panels (the /mission wall embeds nothing → stored basis, byte-identical). (2)
>   `/export/{fmt}/path/{name}` gains `basis` (default `stored` byte-identical, pinned);
>   /driving-path's link passes `basis=resolve` so the full-trace Excel mirrors the
>   re-solved tiers (workbook title carries the counterfactual marker; the /path page stays
>   family A). (3) the tiers drill + its Excel drop the solve-dependent columns
>   (Start/Finish/Total float/Critical — stored-basis figures) while options are active,
>   screen + server-side; input columns always remain. Banner/caption/docstrings updated to
>   the unified truth; the ADR-0251 divergence pin re-targeted.
> - **Verified:** tests/web/test_family_b_unify.py (8) + the updated test_path_options pin;
>   adjacent suites (evolution/driving-path/tiers-drill/exports/mission) green;
>   browser-verified in Chromium (live stepper fetch carries the option; drill note; export
>   link basis; zero console errors). Family-A byte-identity pinned (stored default +
>   basis=resolve no-op equality); parity untouched.
> - **Still OWED by the operator:** PowerShell crash log + the real large dataset (ADR-0261
>   on-machine re-validation); the Claude-Design prompt (Portfolio US-map, ADR-0258).
> - **State:** v1.0.71; **ADR-0265** highest; wheel + 9 installers in lockstep; branch
>   `claude/handoff-review-validation-ikldbf` (restarted from the #400 squash; draft PR).
> - **NEXT:** zero-margin SRA toggle (Fig 7-43 fidelity, ADR-0254 follow-up, via the
>   existing three-point surface) → roles i18n catalog; #13 XER per-task calendars stays
>   PARKED; operator-blocked items resume on their inputs.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
