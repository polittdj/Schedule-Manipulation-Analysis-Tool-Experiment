# Handoff — 2026-07-18f (ADR-0268: strict script-src CSP + 4 residuals + a browser-surfaced SEC-2 correction; v1.0.73; highest ADR 0268)

> ## STATUS (current) — with the standing queue empty, cleared the recorded residuals in one PR (ADR-0268) — and the browser verification of the CSP change SURFACED A SERIOUS LATENT BUG in the already-merged ADR-0264 SEC-2 gate (every POST form was refused live) and fixed it. Version 1.0.72 → 1.0.73 (wheel + 9 installers in lockstep).
>
> - **Strict CSP:** `script-src 'self'` (dropped 'unsafe-inline'). Every inline handler →
>   delegated in the new `chrome.js` via `data-sf-*` attrs (autosubmit / navselect /
>   nexturl-submit / confirm / sfQuitLink); every `window.SF_*=` boot script → a
>   non-executable `<script type="application/json">` block its consumer parses by id
>   (sfI18nBoot/sfScurveFields/sfRibbonDrillData/sfRemainDays/sfFieldHelp). style-src keeps
>   'unsafe-inline' (Gantt px widths). Defense in depth: injected inline JS can't execute.
> - **SEC-2 CORRECTION (browser-surfaced MAJOR):** the ADR-0264 Origin-only gate refused
>   EVERY real-browser POST *form* navigation — `Referrer-Policy: no-referrer` makes Chromium
>   send `Origin: null` on those, read as cross-site. The #400 probe only did fetch POSTs
>   (real Origin), so it never caught it. Gate now uses `Sec-Fetch-Site` (primary; a
>   forbidden header no-referrer doesn't null, unforgeable cross-site) — same-origin/none
>   pass, cross-site/same-site/cross-origin refused — with the Origin check as the
>   absent-header fallback (OWASP Fetch-Metadata pattern). Proven live: the language POST
>   form now applies (page renders in Spanish — also confirms ADR-0267).
> - **Residuals cleared:** GET /cei?target side effect → POST /target (uids stays a display
>   GET); /export mission degrades to a valid note workbook <2 versions (not a 422);
>   /export margin?zero_margin=1 exports the Fig 7-43 snapshot (ADR-0266).
> - **Verified:** test_csp_strict_scripts.py + test_residuals_268.py + expanded
>   test_sec_hardening.py (Sec-Fetch-Site cases incl. the null-Origin-same-origin
>   regression); re-targeted old-markup pins + the SRA-derive JS harness; Chromium sweep of
>   10 pages ZERO CSP violations, forms work, Wipe confirm fires. Parity untouched.
> - **Still OWED by the operator (all remaining work):** PowerShell crash log + real large
>   dataset (ADR-0261 on-machine re-validation; five-large-file stress); Claude-Design prompt
>   (Portfolio US-map/site drill, ADR-0258). #13 XER per-task calendars PARKED.
> - **State:** v1.0.73; **ADR-0268** highest; wheel + 9 installers in lockstep; branch
>   `claude/handoff-review-validation-ikldbf` (restarted from the #402 squash; draft PR).
> - **NEXT:** babysit the open PR to merge; then WAIT on operator inputs — the residual list
>   is now empty too. The 2026-07-18 cycle: #399→#400→#401→#402→this PR.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
