# ADR-0257 — loopback Host allowlist + cross-origin mutation gate (audit SEC-2/SEC-3)

## Status

Accepted. The propose-then-build follow-up to ADR-0256's two deferred security findings;
the design was put to the operator and approved ("Approve both") before build.

## Context

The 2026-07-17 audit recorded two pre-existing surface gaps in the loopback web app:

- **SEC-3 (DNS rebinding):** the app answered requests bearing ANY Host header. A malicious
  page rebinding its domain to 127.0.0.1 could have the operator's browser READ responses —
  schedule content, which on a production machine is real CUI — bypassing same-origin
  protections (the browser treats the attacker's domain as the origin).
- **SEC-2 (CSRF):** the 26 state-mutating POST routes carried no cross-site protection; a
  hostile page could silently change operator-set analysis parameters (margin band rates,
  thresholds, role, AI settings…). Probes showed fail-soft validation limits the blast
  radius, but the surface was real.

## Decision

**One middleware extension** (inside the existing liveness/security-headers middleware, so it
runs before any route and its rejections still carry the CSP/nosniff headers):

1. **Host allowlist** — a request whose ``Host`` is not a loopback host (any port) is
   refused with **421** before any route runs. "Loopback" is decided by the SAME predicate the
   bind API validates its host with (``net_guard.is_loopback_host`` — all of 127.0.0.0/8,
   ``localhost``, ``ip6-localhost``, ``::1``), so a host accepted at startup can never produce
   a server that 421s itself (refined per the Codex review on the PR — the first cut's narrower
   literal set would have broken a legitimate ``serve(host="127.0.0.2")`` bind; the Origin gate
   shares the predicate for the same reason). The
   rebinding attack's defining artifact is the attacker's hostname in Host; refusing it kills
   the read vector outright. Disclosed exception: ``testserver`` (starlette TestClient's fixed
   host) — dev/test-only, unforgeable cross-site from a browser, and the deployed server binds
   127.0.0.1. An empty/absent Host is refused.
2. **Origin gate on mutations** — a **POST** whose ``Origin`` header is present and not a
   loopback origin (or is ``null``) is refused with **403**. Modern browsers always attach
   Origin to cross-site POSTs, so hostile forms/fetches die here with **zero token plumbing**
   through the app's forms and zero UI change. An absent Origin passes (curl, TestClient, the
   tool's own legacy same-origin form posts). Reads stay ungated — cross-origin response
   reading is the browser's job (SOP), backed by the strict CSP.

**Disclosed residuals:** pre-2020 browsers that omitted Origin on cross-site POSTs are not
covered by the gate (they are also increasingly unable to browse the modern web); non-browser
local processes can always talk to a loopback server — that is the OS trust boundary, not a
web one.

## Consequences

- `web/app.py`: `_ALLOWED_HOSTS` + `_host_allowed` + `_origin_allows_mutation` + the two
  checks at the top of the middleware. No route, form, or JS change; behavior for every
  legitimate client is byte-identical (the full suite runs unchanged under TestClient's
  ``testserver`` Host and absent Origin).
- `tests/web/test_host_origin_guard.py`: foreign-Host 421 with security headers on the
  rejection; loopback Hosts on any port pass; empty Host refused; cross-origin/null-Origin
  POSTs 403 with session state proven untouched; loopback + absent Origins mutate normally;
  reads ungated by Origin.
- v1.0.65 → v1.0.66 (wheel + 9 installers in lockstep).
