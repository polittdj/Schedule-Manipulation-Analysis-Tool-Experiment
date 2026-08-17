# ADR-0416 — JS-01: the Acumen-parity toggle was a dead control; it is now live, and JS-free

**Status:** Accepted · **Date:** 2026-08-17 · **Closes:** JS-01 (audit 2026-08-16, critical) ·
**Extends:** ADR-0268 (event delegation) · **Ships:** `web/analysis.py`, `static/chrome.js`

## Context

The DCMA panel on `/analysis` offers **Acumen Fuse parity mode** — the toggle that switches the
14 DCMA checks between the pure-logic/forensic read and the Acumen-parity read. The two
disagree on real progressed schedules; the panel's own explainer says so at length. It was
rendered as:

```html
<input type=checkbox name=parity value=1 onchange="this.form.submit()">
```

inside a `<form action="/dcma/scope">` **with no submit button**.

The app serves `Content-Security-Policy: … script-src 'self'` — no `'unsafe-inline'`, by design,
because that CSP is how Law 1's air-gap is enforced in the browser at runtime. Inline event
handlers are therefore refused, and with no submit button the form had no other way to fire.

## The measurement

Verified in real Chromium against the app on loopback, not inferred from the CSP text:

| observation | result |
| --- | --- |
| checkbox state before click | checked (parity ON) |
| URL after clicking | **unchanged** |
| page state after clicking | **unchanged** |
| server state on reload | **unchanged** |
| browser console | *"Refused to execute inline event handler because it violates the following Content Security Policy directive: `script-src 'self'`"* |

The operator could not switch DCMA views at all. On a forensic tool where that toggle changes
reported numbers in a testimony deliverable, a visible control that silently does nothing is
worse than an absent one: it reports a state the tool is not in.

## The cause, which the repo had already solved

ADR-0268 built `chrome.js` **for exactly this**, and says so in its own header: *"The strict CSP
(`script-src 'self'`) forbids inline event handlers, so every interactive bit of server-rendered
chrome is delegated here instead"* — including `data-sf-autosubmit`, described as covering *"the
classic `onchange="this.form.submit()"`"* controls.

Its selector was `select[data-sf-autosubmit]`. A **checkbox** is not a `<select>`, so it fell
through the mechanism built to catch it, and the author reached for the inline handler the
mechanism exists to replace.

## Decision

- **Widen the delegation** from `select[data-sf-autosubmit]` to `[data-sf-autosubmit]` — any
  element. One word, and the mechanism now covers what its own docstring always claimed.
- **Delegate the control**: the checkbox carries `data-sf-autosubmit` instead of `onchange`.
- **Add a real submit button** to the form. This is the part that is not merely a port: the
  toggle must work with **no JavaScript at all**. JS-01 happened because the control's only path
  to the server was a script that turned out not to run; restoring that single point of failure
  in a new costume would be repeating it. Belt (delegation, one click) and braces (a button that
  needs nothing).

## Verification (QC-1)

- **Red first, by name:** 4 of 7 new tests failed on the shipped tree.
- **The same browser probe that condemned it now clears it**: parity toggles ON → OFF, the
  server agrees on reload, and the console logs **zero** CSP violations.
- **Census, not anecdote.** `tests/web/test_no_inline_event_handlers.py` scans the whole view
  layer's source for *any* `on*=` attribute (not just `onchange` — a guard that names only the
  attribute that broke is a guard waiting for the next one) and re-checks the served `/analysis`
  HTML, because source and served HTML have disagreed in this repo before. The sweep confirmed
  this was the **only** inline handler in the view layer — a single site, not a class.
- Blast radius: 41 passed across the DCMA-scope, panel-contract, analysis-cache and
  single-compute suites; `node --check` clean on the vendored JS.

## The lesson

**A control the CSP kills is invisible to every test that reads markup.** The parity checkbox
was almost certainly "verified" by confirming the input renders with the right name and state —
which it did, perfectly, while doing nothing. Only executing the page in a browser could tell
the difference. This is the render-verify rule stated for interactivity: for a *control*, the
evidence is that clicking it changes something, never that it appears.
