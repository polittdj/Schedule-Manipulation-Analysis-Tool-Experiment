# 0316 — The second blob-driven module gets the same `defer` (/performance first paint)

Date: 2026-07-30
Status: accepted

## Context

`/performance` executed `performance.js` synchronously at parse time: the module reads its
embedded `#perfData` blob (no fetch) and its IIFE ends with `step(cursor)` — an immediate full
render. `quad()` ends in an unguarded `SFChartFrame.axisTitles(...)` call, but `chartframe.js`
is emitted by `_LAYOUT` **after** `</main>`, i.e. after the body's script tag in document
order. First paint therefore threw `SFChartFrame is not defined`, `renderQuads()` aborted, and
the three portfolio quad tiles (`quadHmiCei`, `quadRatio`, `quadBeiCp`) stayed empty until the
operator's first Prev/Next/Play click re-rendered — the page recovered on any interaction,
which is exactly why the defect survived casual use.

This is byte-for-byte the round-10 `/resources` defect (`test_r10_resources_contract.py`'s
"first-paint regression this round fixes"): `resources.js` was the other module that drew
synchronously ahead of the layout's `chartframe.js`, fixed then with a one-word `defer`.
A cross-check of every other `SFChartFrame.axisTitles` caller shows them all drawing inside a
`fetch().then()` — the race is unique to the two blob-driven modules, and `/performance` was
the one still un-deferred.

## Decision

Add `defer` to the `/performance` script tag (`web/app.py`) — nothing else. A deferred script
executes after parsing completes and after every synchronous script (`chartframe.js` included),
so the ordering is guaranteed by the platform, exactly as on `/resources`.

**Deliberately NOT added: a runtime guard around `performance.js:472`.** The repo pins its
chart modules hard (whole-file digests on `resources.js`/`volatility.js`, the byte-pinned quad
caption block in the r10 contract, and the 16-site `axisTitles` call-site census) — editing the
call site would force a census re-baseline for a guard the `defer` makes unreachable. The
house precedent (`/resources`) shipped `defer`-only with the JS byte-identical; this follows it.

## Verification

Two tests in `tests/web/test_r10_performance_contract.py`, mirroring the `/resources` twins:
the TestClient pin (`<script defer src="/static/performance.js"` present AND `</main>` really
precedes `chartframe.js` — the reason `defer` is required), and a real-chromium first-paint
test (fresh load, zero interaction: no `pageerror`, all three quad hosts painted). Proved able
to fail on the un-deferred tree: both fail (the chromium one reads
`['SFChartFrame is not defined']`).

## Consequences

First paint on `/performance` now renders all fourteen tiles including the quads, with a clean
console, before any interaction. `performance.js` is untouched (every digest pin stands). The
`defer` idiom is now uniform across both blob-driven modules; any future blob-driven page
should copy it from birth.
