# Handoff — 2026-07-17 (F3c-fuller: expected-margin panel — Fig 5-30 editable band + SRA percentile spread; v1.0.63; highest ADR 0254)

> ## STATUS (current) — ADR-0254: the operator's VERBATIM F3c spec delivered — the "parameterized expected-margin panel — tier-a Fig 5-30 editable band + tier-b SRA percentile spread" (Thursday directive). ADR-0253's rate param was the narrower first cut; this is the full two-tier panel, designed by a Fable 5 Max deep dive and adversarially verified (4-agent workflow, quotes + code claims) before build. Includes a VERIFIED doc-truth citation correction to the 50%-consumed threshold. Version 1.0.62 → 1.0.63 (wheel + 9 installers in lockstep). Full gate green incl. `parity`.
>
> - **Tier-a — Fig 5-30 editable band** (`engine/margin_guideline.py`, pure + additive). Figure 5-30
>   (SMH §5.5.11.2, printed p.120) is a three-row TABLE of per-phase margin rate ranges, each
>   explicitly "Varies" → operator-editable with cited defaults ((30,60)/(60,75)/(30,84) wd/yr at the
>   disclosed 1-month=30-wd Gold-Rule convention; row 3's three verbatim alternatives quoted beside
>   the inputs). The stepped band (`edge(t) = Σ rate × overlap_days(phase ∩ [t,launch])/365`, the
>   Fig 7-32 "stepped burndowns that mimic the margin guidelines" form) overlays the burn-down once
>   the operator enters the four phase dates (never derived; fail-soft setters; cleared on wipe);
>   below-band months get a hollow-diamond guideline-deviation marker (§7.3.3.1.6 Thresholds quote);
>   verdicts suppressed on a mixed wd-basis (the erosion-fit refusal). `POST /margin/band`.
> - **Tier-b — SRA percentile sufficiency** (§7.3.3.2.3's stochastic tracking). `margin_risk_read`
>   consumes the EXISTING sra step-CDF — covered percentile = CDF(D), pinned equal to the engine's own
>   `deterministic_percentile`; the margin window [E, D] is computed EXACTLY on the run's all-ML axis
>   by the additive `sra.deterministic_margin_bounds` (pinned == compute_sra_ssi's anchor). Verdicts
>   classify against operator-editable Watch/Corrective percentiles (70/50 prefilled AS the handbook's
>   EXAMPLE values). `GET /api/margin/risk` — button-triggered, seeded-deterministic, offload-guarded,
>   every parameter echoed. Fail-soft: no schedule / raised run / degenerate point-mass / no margin
>   each disclose honestly, never a fabricated verdict. Disclosed caveat: margin rides in-network at
>   plan (Fig 7-43's curves are zero-margin) — the zero-margin toggle is a documented follow-up.
> - **Doc-truth citation correction (adversarially verified against the PDF).** "The corrective
>   action threshold is set where the margin is 50% consumed" lives in **§7.3.3.2.3** (printed p.324),
>   **example-framed** ("In this example case, the P/p has chosen…") — NOT §7.3.3.1.6 as ADR-0230
>   recorded (its own Thresholds paragraph is deliberately non-numeric). Flag behavior unchanged; the
>   takeaway/burn-down/JS copy now cite §7.3.3.2.3 as the handbook's example threshold. Also fixed:
>   the burn-down requirement-line tooltip now states the operator-set rate (was hardcoded 30).
> - **Export.** Three new margin-export tables: the per-status-date band read (or "not configured"),
>   the band parameters (dates/rates/verbatim rows/conversion), and the seeded SRA sufficiency read
>   with full provenance — byte-identical to the panel by determinism.
> - **Verified.** `tests/engine/test_margin_guideline.py` (hand-computed band values incl. the
>   67.3/118.4 CR sum, the two Law-2 equivalence pins, CDF breakpoint semantics, degenerate paths) +
>   `tests/web/test_margin_band_and_risk.py` (verbatim rows render, POST persists/fail-soft/clear,
>   band JSON gating + month classification, degenerate disclosure + determinism + provenance echo,
>   the corrected citation, export statements) + the additive-offsets pin. 4-theme Chromium check
>   green — both new visuals, zero console errors (incl. a genuinely light daylight render and a
>   legend-wrap fix for the 7-item burn-down legend).
> - **State:** v1.0.63; **ADR-0254**; wheel + 9 installers regenerated in lockstep; full gate green
>   (ruff / ruff format --check / mypy --strict 113 files / bandit exit 0 / node --check / full
>   pytest incl. `parity`).
> - **NEXT — the standing queue:** **#13** XER per-task calendars (still PARKED — needs the operator's
>   owed `.xer` files) → **roles front-end (v4 F4)** — NO committed spec exists (searched all docs +
>   the Thursday directive): the next session should propose a role list + Law-2-safe behavior for
>   operator approval before building. Then: the ADR-0251 family-B option-plumbing unify PRs; the
>   zero-margin SRA toggle (Fig 7-43 fidelity, via the existing three-point surface); deferred perf
>   (ADR-0249 harness). Operator-side (no code): the `00_REFERENCE_INTAKE/INDEX.md` §3 reorg map +
>   the §4 root-vs-mpp `Project5_TAMPERED.mpp` canonical-build decision.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
