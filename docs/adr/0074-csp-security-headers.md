# ADR-0074 — Enforce the air-gap in the browser: Content-Security-Policy + security headers

Date: 2026-06-18 · Status: accepted

## Context

External audit item A7. The tool set **no security headers**. Law 1 (no remote assets, nothing
leaves the machine) was enforced only by a *test* (`tests/web/test_airgap.py` scans served bodies).
A Content-Security-Policy enforces the same guarantee **in every user's browser at runtime** — a far
stronger control, and a perfect fit for the CUI threat model (the operator analyzes opposing-party
schedule files). The audit flagged that a strict `script-src 'self'` would break two inline handlers
(`onclick="return sfQuit()"`, the wipe-session `onsubmit="return confirm(...)"`) and ~20 inline
`style=` attributes (the Gantt's px widths), and recommended shipping a **permissive-inline CSP
first** (immediate value, zero breakage), tightening later.

## Decision

Add security headers to **every** response via the existing `http` middleware (`create_app`):

* **`Content-Security-Policy`:** `default-src 'self'; object-src 'none'; base-uri 'self';
  frame-ancestors 'none'; connect-src 'self'; img-src 'self' data:; form-action 'self';
  style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'`. The air-gap-critical
  directives (`default-src`/`connect-src`/`img-src` = `'self'`) mean the page can never pull or
  beacon to a remote host — no CDN, no webfont, no exfil `fetch`. `'unsafe-inline'` for style/script
  permits the existing inline `style=` and the two inline handlers, but **still forbids any remote
  script/style**, so the no-remote-asset guarantee holds.
* **`X-Content-Type-Options: nosniff`**, **`Referrer-Policy: no-referrer`**, **`X-Frame-Options:
  DENY`** — free hardening (no MIME-sniffing, no referrer leakage, no framing).

Headers are applied with `setdefault`, so a route that sets its own value is never clobbered. Tightening
to a strict `script-src 'self'` (after moving the two inline handlers to `addEventListener`) is a
tracked follow-up.

## Scope / safety

No engine/CPM/metric change → **parity 10/10**. The headers strengthen — never weaken — the air-gap;
`test_airgap.py` still passes (no remote asset slips through) and a new case asserts the CSP +
nosniff/referrer/frame headers ride every page and static asset. Verified the in-page Quit, the
wipe-session confirm, the theme toggle, charts, uploads, and `fetch`-based panels all still work
under the policy (inline handlers + same-origin `connect-src`). Full gate green;
ruff/format/mypy/bandit clean.
