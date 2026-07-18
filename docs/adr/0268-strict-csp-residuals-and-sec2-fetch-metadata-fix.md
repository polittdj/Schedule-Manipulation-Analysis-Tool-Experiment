# ADR-0268 — strict script-src CSP, four recorded residuals, and a SEC-2 correction (browser-surfaced)

## Status

Accepted. Clears the standing "smaller recorded residuals" list (the queue had no unblocked
feature work left) — and, in the course of browser-verifying the CSP change, surfaced and
fixed a **serious latent bug in the already-merged ADR-0264 SEC-2 gate** that would have made
every POST form in the deployed tool fail. Operator authorization: the standing 2026-07-18
automated-build directive (residuals were explicitly offered as "if directed"; the SEC-2
correctness fix is not optional once found — a broken security gate that bricks the UI must
not ship).

## Decisions

### 1. Strict `script-src 'self'` (the long-tracked CSP follow-up)

`'unsafe-inline'` was in `script-src` only because page chrome used inline `on*=` handlers
and inline `window.SF_*=` boot scripts. Both are eliminated:

- **Handlers → delegation.** New always-loaded `web/static/chrome.js` delegates every former
  inline handler from `document`, keyed by `data-sf-*` attributes: `data-sf-autosubmit`
  (submit the owning form on change), `data-sf-navselect` (navigate to the option value),
  `data-sf-nexturl-submit` (stamp the current page into `next_url`, then submit — the banner
  Project switcher, which needs an explicit return under `Referrer-Policy: no-referrer`),
  `data-sf-confirm` (a `confirm()` gate on submit — Wipe), and `#sfQuitLink` (→ `sfQuit()`).
  Document-level delegation covers AJAX-rendered chrome automatically.
- **Boot payloads → JSON blocks.** Each `window.SF_*=` inline script becomes a
  non-executable `<script type="application/json">` block its consumer parses by id
  (`sfI18nBoot`, `sfScurveFields`, `sfRibbonDrillData`, `sfRemainDays`, `sfFieldHelp`),
  each still `<`-escaped so imported file text can't close the block.

`script-src` tightens to `'self'` — an injected inline `<script>` or `on*=` handler can no
longer execute even if markup escaping ever failed (defense in depth for a tool that renders
opposing-party file content). `style-src` keeps `'unsafe-inline'` (the Gantt's legitimate
inline px widths — inline styles execute no code; remote styles stay forbidden).

### 2. SEC-2 correction — Fetch Metadata over Origin (browser-surfaced MAJOR)

Verifying the strict CSP in a real browser drove the **first real-browser POST *form*
navigation** the suite has ever exercised (the ADR-0264 browser probe used only `fetch`
POSTs, which carry a real Origin) — and it was **refused (403)**. Root cause: the app sends
`Referrer-Policy: no-referrer` (ADR-0150), under which Chromium sends `Origin: null` on
same-origin form-submission navigations; the ADR-0264 Origin-only gate read `null` as the
cross-site signature. **Every** POST form in the deployed tool (Wipe, Target, Language,
Project-select, Margin-confirm, filters, SRA…) would have failed live.

The gate now uses **`Sec-Fetch-Site`** as the primary discriminator (`_csrf_safe`): a
browser-set forbidden header a cross-site page cannot forge, and — unlike Origin — *not*
nulled by `no-referrer`. `same-origin` (the tool's own forms/fetches) and `none` (a
user-initiated top-level navigation — address bar/bookmark, not a CSRF vector) pass;
`cross-site`/`same-site`/`cross-origin` are refused. When the header is absent (non-browser
client, or a pre-Fetch-Metadata browser) it falls back to the ADR-0264 Origin check
(absent-Origin and loopback pass; foreign/null refused). This is the OWASP-recommended Fetch
Metadata Resource Isolation Policy — strictly more correct than the Origin-only gate on every
case, and it *fixes* the null-Origin same-origin form-POST that ADR-0264 broke.

### 3. Four recorded residuals

- **`GET /cei?target=…` side effect removed.** Focusing a target now POSTs `/target` (the
  Focus form; the SEC-2 gate can't cover a GET anyway, and a GET must not mutate state — the
  ADR-0061 residual). `uids` stays a display-only GET param.
- **`/export/{fmt}/mission` degrades** below two versions to a valid workbook carrying a
  one-row explanatory note (mirroring the ADR-0262 on-screen wall degrade), never a raw 422
  the browser saves as a broken document.
- **`/export/{fmt}/margin?zero_margin=1`** exports the Fig 7-43 zero-margin sufficiency
  snapshot (ADR-0266) — the same curve the panel toggle shows; the "Curve basis" row names it.
- The CSP-comment follow-up itself (item 1) is the fourth.

## Consequences

- New: `tests/web/test_csp_strict_scripts.py` (strict CSP, no inline handlers on 17 page
  families, every inline script is a JSON block, chrome.js delegation, boot payloads reach
  consumers); `tests/web/test_residuals_268.py` (the three residuals); `test_sec_hardening.py`
  gains the Sec-Fetch-Site cases incl. the null-Origin-same-origin regression. Existing pins
  that referenced the old markup (`window.SF_*`, `location.href=this.value`, GET `/cei?target`)
  re-targeted; the SRA-derive JS harness stubs the JSON block.
- Browser-verified (Chromium): **zero CSP violations** across ten heavy pages; the delegated
  language POST form applies (page renders in Spanish — also a live confirmation of ADR-0267);
  the Wipe confirm dialog fires. This is the verification that caught the SEC-2 bug.
- No engine math touched; parity untouched. Version 1.0.72 → 1.0.73; wheel + 9 installers in
  lockstep.
