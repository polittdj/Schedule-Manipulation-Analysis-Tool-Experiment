# Handoff — 2026-07-17 (session audit: margin-risk date realignment + hardening; v1.0.65; highest ADR 0256)

> ## STATUS (current) — ADR-0256: the operator-requested ADR-0240 AUDIT of the day's work (ADR-0254 margin panel + ADR-0255 roles) ran as a 4-agent orchestrated sweep with adversarial verification + lead re-validation — outcome EXTENSIVELY CLEAN (band arithmetic re-derived exactly, CDF reads swept to bisect_right equality, roles contract proven incl. all-32-combination upload byte-compat, XSS probes negative) with ONE confirmed major, fixed: **F1 — /api/margin/risk + the margin export printed D/E/percentile DATES on the raw pure-CPM axis on progressed schedules** (months before the stored plan dates, while /sra realigned the same run). Fixed via additive `sra.stored_finish_correction` (the engine's own constant realignment, exposed; pinned vs /api/sra/ssi on a progressed fixture). Version 1.0.64 → 1.0.65.
>
> - **Minors fixed in the same PR:** single-month band polygon now renders (bar-width segment,
>   F3); MarginMonth-offsets comment corrected (F2); margin_risk_read docstring rounding caveat
>   (F4); **advisory notices now gate the role landing** (no-title / mtime-tiebreak / RAM notices
>   render only on the dashboard flash — disclosure outranks the landing; pre-F4 no-role paths
>   byte-untouched, both pinned); role-strip headings translatable (ROLES-2 partial — catalog
>   entries queued); REPO-INVENTORY stale body lines fixed (STATE-1); **.gitattributes hardening
>   (SEC-1)** — `-text` on `*.aft/*.xer/*.mpp/*.xlsx/*.docx`, `00_REFERENCE_INTAKE/**`,
>   `installer/**`, `tests/fixtures/**` so no renormalization can ever byte-rewrite the CUI
>   guard's inherited-from-main blobs or the lockstep installers (verified: dirties nothing).
> - **Recorded, NOT fixed (needs own ADR + operator approval — queued):** SEC-2 CSRF/Origin
>   protection for state-mutating POSTs; SEC-3 Host allowlist (DNS-rebinding read vector —
>   CUI-relevant on a production machine). Both touch every route; propose-then-build.
> - **State:** v1.0.65; **ADR-0256**; wheel + 9 installers in lockstep; full gate green incl.
>   `parity`; 111 affected-suite tests green incl. the two new regression pins.
> - **NEXT — the standing queue:** **#13** XER per-task calendars (still PARKED — the operator's
>   owed `.xer` files) → **SEC-2/SEC-3 hardening proposal** (design + ADR for operator approval
>   BEFORE build) → the ADR-0251 family-B option-plumbing unify PRs (golden re-validation each) →
>   the zero-margin SRA toggle (Fig 7-43 fidelity, ADR-0254 follow-up) → roles i18n catalog
>   entries (ROLES-2 residual) → deferred perf (ADR-0249 harness). Operator-side (no code): the
>   `00_REFERENCE_INTAKE/INDEX.md` §3 reorg map + the §4 root-vs-mpp `Project5_TAMPERED.mpp`
>   canonical-build decision.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
