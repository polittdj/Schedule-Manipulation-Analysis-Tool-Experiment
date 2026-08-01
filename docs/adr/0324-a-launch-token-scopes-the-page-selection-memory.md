# 0324 — A launch token scopes the browser's page-selection memory to the server session (OR-06)

Date: 2026-07-31
Status: accepted

## Context

Operator bug (OR-06): a fresh open of the deployed tool showed fields populated from
PREVIOUS sessions — e.g. a Target UID from a project never loaded — even after
wipe-then-Quit. Mechanism (verified): ADR-0186's per-page selection memory keeps
`sf-qs:<path>` (query strings incl. `?target=…`) and `sf-ui:<path>` (control values) in
browser **localStorage**, which by design outlives the server process and the session
wipe; nothing ever invalidated those layers, so the next launch replayed them.

## Decision

The server serves a **launch token** on every page (`<meta name=sf-launch>`), composed
of a per-process nonce (`secrets.token_hex`, minted at import — fresh every launch) and
`SessionState.wipe_gen` (bumps on every `/session/wipe`). `persist.js` compares it with
the token it last stored **before the query-string replay runs**; on a mismatch it
removes every `sf-qs:*` / `sf-ui:*` key plus the per-page column-picker keys, then
stores the new token. Within one launch (and between wipes) the token is stable, so
ADR-0186's within-session page memory is byte-identical to before; global preferences
(theme, UI scale, Timescale) are page-independent keys and are never touched. No token
served (an old server) → the guard is a no-op, fail-open. No visual change (a meta tag
plus storage hygiene), so the design-system checklist is trivially satisfied.

Both invalidation triggers the operator named are covered by one comparison: Quit +
relaunch rotates the nonce; wipe rotates the generation.

## Residuals (from the adversarial review; documented, not chased)

- **Browser session-restore** can reopen a tab on a stale deep URL (`?target=…`); the
  guard clears the stored layers, but layer 1 then legitimately saves the CURRENT URL's
  query — that is "the user opened this URL", indistinguishable from typing it. The
  operator's reported flow (fresh open of the tool's root) is fully covered.
- **A tab left open across a wipe** keeps its in-memory control state and re-records it
  on the next interaction in that tab — it is an active session view, not stale storage.

## Verification

`tests/web/test_launch_invalidation.py`: token on every page and stable across
requests; `/session/wipe` rotates it; persist.js guard-ordering contract (guard before
the replay layer); and a real-browser (bundled Chromium) proof of BOTH halves — stale
token clears `sf-qs:`/`sf-ui:`/column keys while the theme pref survives, and
same-token memory survives a reload. Proved able to fail: all four failed on the
pre-fix tree (the browser test with the operator's exact stale-Target-UID shape).
ADR-0186's own page-memory suite passes unchanged.
