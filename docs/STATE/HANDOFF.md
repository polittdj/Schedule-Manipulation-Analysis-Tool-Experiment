# Handoff — 2026-07-18e (zero-margin SRA toggle ADR-0266 + roles i18n catalog ADR-0267 — the standing queue's last unblocked items; v1.0.72; highest ADR 0267)

> ## STATUS (current) — the automated build cycle: PR #401 (family-B unification, ADR-0265, v1.0.71) squash-merged at CI green; branch restarted; the LAST two unblocked queue items shipped together — **ADR-0266 zero-margin SRA toggle** (Fig 7-43 fidelity) + **ADR-0267 roles i18n catalog** (ROLES-2 completion). Version 1.0.71 → 1.0.72 (wheel + 9 installers in lockstep). **The standing queue is now EMPTY of unblocked work** — everything remaining waits on operator inputs or is PARKED.
>
> - **ADR-0266:** `/api/margin/risk?zero_margin=1` (checkbox by the panel's Run button) runs
>   the seeded SRA with every margin activity's three-point at (0,0,0) — the handbook's
>   "Current Plan, Zero Margin, With Risks" curve via the existing three-point surface,
>   exactly as ADR-0254 queued. [E, D], thresholds, margin-set precedence, seed unchanged;
>   payload + provenance + export name the curve basis. Seed-independent proof: a fixture
>   whose ONLY uncertainty is the margin task collapses to a degenerate distribution landing
>   exactly on E (margin provably removed from the sampling). Browser-verified live (note:
>   Playwright wait_for_function was refused by our own CSP — the air-gap working).
> - **ADR-0267:** the full role-strip vocabulary ×4 languages (~46 _TERMS entries): roles,
>   taglines, combined "Start here — {role}" headings (single text nodes), missing card
>   titles, all 24 why-lines, tooltips (translate.js walks title attrs). Product/standard
>   names stay untranslated by convention; the picker prose stays on the AI fallback.
> - **Still OWED by the operator (the only remaining work):** the PowerShell crash log + the
>   real large dataset (ADR-0261 on-machine re-validation; five-large-file stress); the
>   Claude-Design prompt (Portfolio US-map/site drill, ADR-0258). #13 XER per-task calendars
>   stays PARKED. Smaller recorded residuals if idle: CSP 'unsafe-inline' script tightening
>   (ADR-0264 note), GET /cei?target side effect, /export/{fmt}/mission <2-version 422,
>   margin-export zero-margin snapshot (ADR-0266 note).
> - **State:** v1.0.72; **ADR-0267** highest; wheel + 9 installers in lockstep; branch
>   `claude/handoff-review-validation-ikldbf` (restarted from the #401 squash; draft PR).
> - **NEXT:** babysit the open PR to merge; then WAIT on operator inputs (or pick up the
>   residuals above if directed). The 2026-07-18 automated cycle shipped: #399 (audit +
>   ADR-0262/0263) → #400 (ADR-0264) → #401 (ADR-0265) → this PR (ADR-0266/0267).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
