# Handoff — 2026-07-18c (SEC-2/SEC-3 hardening ADR-0264: Host allowlist + Origin gate; v1.0.70; highest ADR 0264)

> ## STATUS (current) — the automated build cycle continues: PR #399 (audit + remediation, ADR-0262/0263, v1.0.69) squash-merged after CI green; branch restarted from main; the standing queue's next item shipped — **ADR-0264 SEC-2/SEC-3 hardening** (closing the ADR-0256 recorded findings). Version 1.0.69 → 1.0.70 (wheel + 9 installers in lockstep).
>
> - **ADR-0264:** one check pair in the `_liveness` middleware, before any route logic —
>   SEC-3 Host allowlist ({127.0.0.1, localhost, ::1, testserver} — the DNS-rebinding CUI
>   read path is closed; `testserver` is TestClient's single-label, publicly-unresolvable
>   default, no rebinding surface) + SEC-2 Origin gate on POST/PUT/PATCH/DELETE (a present
>   foreign/`null` Origin = the cross-site signature → 403 and provably no state change; an
>   ABSENT Origin = non-browser local client → passes; reads never gated — browsers omit
>   Origin on same-origin GET navigations). Rejections carry the full security-header set.
>   Authorization: the operator's standing 2026-07-18 automated-build directive, recorded in
>   the ADR (ADR-0256 had asked for explicit sign-off; the change is small + revertible).
> - **Verified:** tests/web/test_sec_hardening.py (6 — foreign/empty Host on pages/POSTs/
>   static; all loopback host forms; foreign/null-Origin POST refused + state unchanged;
>   loopback/absent-Origin POSTs work; reads ungated); full web suite 919 green unchanged;
>   real-Chromium end-to-end (upload → mission → 4 themes) ALL SCENES CLEAN under the gates.
> - **Known residuals (recorded in ADR-0264):** GET /cei?target=… query side effect
>   (ADR-0061 design; Origin can't cover GETs); the CSP 'unsafe-inline' script follow-up.
> - **Still OWED by the operator:** PowerShell crash log + the real large dataset (ADR-0261
>   on-machine re-validation); the Claude-Design prompt (Portfolio US-map, ADR-0258).
> - **State:** v1.0.70; **ADR-0264** highest; wheel + 9 installers in lockstep; branch
>   `claude/handoff-review-validation-ikldbf` (restarted from the #399 squash; draft PR).
> - **NEXT:** ADR-0251 family-B unify (forward options to /api/evolution; decide the
>   driving-path full-trace basis vs goldens; option-solve or hide the drill's added
>   columns) → zero-margin SRA toggle (Fig 7-43, ADR-0254 follow-up) → roles i18n catalog;
>   #13 XER per-task calendars stays PARKED; operator-blocked items resume on their inputs.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
