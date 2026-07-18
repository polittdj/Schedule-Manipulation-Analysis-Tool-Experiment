# ADR-0264 — SEC-2/SEC-3 hardening: Host allowlist + Origin gate on state-mutating requests

## Status

Accepted. Closes the SEC-2/SEC-3 items recorded in ADR-0256 ("own ADR + operator approval
required"). Authorization: the operator's standing session directive of 2026-07-18 (execute
the full handoff queue autonomously as an automated build cycle, answering design questions
in favor of fidelity and safety) — recorded here explicitly since ADR-0256 asked for the
operator's sign-off; the change is small, fail-safe, and trivially revertible if the
operator wants a different posture.

## Context

The tool binds 127.0.0.1 only, but loopback binding alone leaves two classic browser-borne
vectors (ADR-0256's audit findings):

- **SEC-3 — DNS rebinding (a CUI READ path).** A malicious page on an attacker domain whose
  DNS re-resolves to 127.0.0.1 lets that page issue requests the browser considers
  same-origin *to the attacker's domain* — reaching the local tool with the ATTACKER'S name
  in the `Host` header. On a production machine the responses are real schedule content
  (real CUI).
- **SEC-2 — CSRF (a state WRITE path).** State-mutating POSTs carried no cross-site
  protection: a cross-site form POST could silently change operator-set parameters
  (fail-soft validation limits the blast radius, but the surface was real).

## Decision

One check pair in the existing `_liveness` middleware (every request, before any route
logic; rejections carry the full security-header set):

- **Host allowlist (SEC-3).** The `Host` header's hostname (port ignored, IPv6 brackets
  handled, RFC-lowercased) must be in `{127.0.0.1, localhost, ::1, testserver}` — else
  `400 {"error": "invalid host header"}`. A rebinding page cannot forge a loopback Host (the
  browser fills Host from the URL's attacker domain), so the read path is closed.
  `testserver` is Starlette TestClient's default base host: a single-label name public DNS
  cannot resolve, so admitting it adds no rebinding surface while keeping the 2400-test
  suite untouched.
- **Origin gate on unsafe methods (SEC-2).** For POST/PUT/PATCH/DELETE, a present `Origin`
  must be an http(s) loopback origin — else `403 {"error": "cross-site request refused"}`
  (this catches `null` too, the sandboxed-iframe signature). Browsers attach `Origin` to
  every cross-site POST, forms included, so this is exactly the CSRF discriminator. An
  ABSENT Origin passes: that is a non-browser local client (curl, tests, launcher probes),
  which is not the CSRF vector. Reads are never Origin-gated — browsers omit the header on
  same-origin GET navigations, so gating reads would break normal use without adding safety
  (SOP + the strict CSP govern the read side).

## Known residuals (recorded, unchanged)

- `GET /cei?target=…` sets the session target from a query parameter (ADR-0061 design) — a
  GET side effect the Origin gate cannot cover. Low impact (fail-soft, a display target,
  no data exfiltration) and pre-existing; a future change would move it to POST.
- The CSP's `'unsafe-inline'` script allowance (two inline handlers) remains the tracked
  follow-up it already was.

## Consequences

- `tests/web/test_sec_hardening.py`: foreign/empty Host refused on pages, POSTs, and static
  (with security headers on the rejection); all loopback host forms + `testserver` served;
  foreign/`null`-Origin POST refused **and provably changes nothing**; loopback-Origin and
  absent-Origin POSTs work; reads never gated.
- Full web suite (919 tests) green unchanged; real-Chromium end-to-end (upload → mission →
  themes) stays clean — the browser's own same-origin POSTs pass the gate live.
- No engine change, no number moved; version 1.0.69 → 1.0.70; wheel + 9 installers in
  lockstep.
