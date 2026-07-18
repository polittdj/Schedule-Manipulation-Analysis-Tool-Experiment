# Handoff — 2026-07-18b (full handoff-verification audit + remediation ADR-0262/0263: /mission tile degrade, epoch pairing, wipe finality, upload locking, summary-margin overlay; v1.0.69; highest ADR 0263)

> ## STATUS (current) — operator-directed verify-everything session: a ten-agent Ultracode audit (ADR-0240 protocol, lead re-verified every major finding) checked EVERY ADR-0261/handoff claim against code + executed tests. The record held: P1 signatures/keys/residency, P2 tier, P3 memo + census-oracle equality, P5 bounds, latency-gate determinism, version/installer lockstep, parity (44 green), AFT pinning live — all CONFIRMED. The audit's confirmed defects were reproduced (failing tests first), fixed, hardened, and browser-verified; NEXT #1 (/mission tile degrade) shipped in the same PR. Version 1.0.68 → 1.0.69 (wheel + 9 installers in lockstep).
>
> - **ADR-0262 (/mission + CEI guards):** cross-version tiles degrade server-side below their
>   OWN API's population threshold (CEI = 2 loaded; Evolution/Quality = 2 analyzable) — no
>   chart host ⇒ scripts early-return ⇒ zero console 4xx (Chromium-proven, 4 themes); the
>   /cei + /api/cei + /export cei guards now count st.ordered() (ADR-0258 residual: they
>   gated on the whole-session dict and 422'd on multi-project 1-version populations).
>   Correction: /api/scurve was never an offender (works with 1 version). i18n ×4 for the
>   two degrade notes; degraded tiles use .chart-note so chartframe adds no dead toolbar.
> - **ADR-0263 (audit remediation):** (1) mixed-epoch pairing made UNREPRESENTABLE —
>   _Analysis.scoped + cpm_scoped_for return the (scoped, cpm) pair from ONE lock window;
>   ten call sites swapped (the P3-memo poisoning this closes was the audit's one REFUTED
>   ADR-0261 sub-claim). (2) wipe finality: wipe_gen + _scope_gen store guards; the on-disk
>   clear + SRA/AI resets now run INSIDE the wipe's lock; disk puts run under the lock —
>   "nothing survives the reset" now holds against in-flight computes. (3) /upload +
>   /example D18 locking (short windows; mid-upload wipe aborts LOUDLY). (4) Portfolio
>   summary margin now honors the ADR-0230 confirmed-margin overlay (dashboard precedence;
>   skip-disk like scoped versions; /margin/confirm clears the summaries tier). (5)
>   _clean_key strips control chars (\x1f epoch-key collision). (6) new gates: P2 per-EPOCH
>   solve counts, OAT cap disclosure (was uncovered), six deterministic race regressions
>   (test_session_consistency.py). (7) AFT drift guard audits EVERY committed .aft (the
>   newer v8.11.0 snapshot was unaudited; verified near-identical first); __version__ now
>   derives from distribution metadata (was hand-pinned "0.0.0" for 68 releases).
> - **Deliberately NOT done (recorded in ADR-0263):** bounding cpms/summaries epoch growth
>   (an LRU would thrash the population pass on large portfolios; revisit on profiling
>   evidence); epoch-key reuse for scope-unchanged versions (missed reuse, never wrong);
>   the polished cache's scoped-object anchor (safe; wording drift only).
> - **Still OWED by the operator:** PowerShell crash log + the real large dataset (ADR-0261
>   on-machine re-validation); the Claude-Design prompt (Portfolio US-map, ADR-0258).
> - **State:** v1.0.69; **ADR-0263** highest; wheel + 9 installers in lockstep; branch
>   `claude/handoff-review-validation-ikldbf` (draft PR).
> - **NEXT:** SEC-2/SEC-3 hardening (CSRF/Origin + Host allowlist — design + ADR) → ADR-0251
>   family-B unify → zero-margin SRA toggle → roles i18n catalog; #13 XER per-task calendars
>   stays PARKED; the two operator-blocked items above resume when their inputs arrive.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
