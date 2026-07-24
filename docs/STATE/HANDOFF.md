# Handoff — 2026-07-17 (SEC-2/SEC-3 hardening: loopback Host allowlist + Origin gate; v1.0.66; highest ADR 0257)

> ## STATUS (current) — ADR-0257: the audit's two deferred security findings are CLOSED, operator-approved before build ("Approve both"). ONE middleware extension, checked before any route: (SEC-3) a non-loopback Host is refused 421 — the DNS-rebinding read vector (CUI-relevant on a production machine) dies at the attacker's-hostname-in-Host artifact; (SEC-2) a POST bearing a present non-loopback/null Origin is refused 403 — modern browsers always attach Origin cross-site, so hostile forms die with ZERO token plumbing and zero UI change. Absent Origin passes (curl/TestClient/legacy same-origin posts); reads stay ungated (browser SOP + the strict CSP). Disclosed: the `testserver` TestClient host exception; the pre-2020 no-Origin-browser residual. Version 1.0.65 → 1.0.66 (wheel + 9 installers in lockstep).
>
> - **Verified.** `tests/web/test_host_origin_guard.py` (6): foreign-Host 421 carrying the
>   security headers; loopback Hosts any port; empty Host refused; cross-origin/null-Origin
>   POSTs 403 with session state proven untouched; loopback + absent Origins mutate normally;
>   reads ungated. Full suite green under the guard (TestClient rides the disclosed
>   `testserver` allowance; no existing test sends Origin).
> - **State:** v1.0.66; **ADR-0257**; wheel + 9 installers in lockstep; full gate green incl.
>   `parity`.
> - **NEXT — the standing queue:** **#13** XER per-task calendars (still PARKED — the operator's
>   owed `.xer` files) → the ADR-0251 family-B option-plumbing unify PRs (forward toggles to
>   /api/evolution; full-trace export basis; drill field columns — golden re-validation each) →
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
