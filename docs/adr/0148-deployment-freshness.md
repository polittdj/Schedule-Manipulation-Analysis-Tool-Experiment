# ADR-0148 — Deployment freshness: lockstep installers + static cache-busting

## Status

Accepted.

## Context

The operator reported the stuck "Loading your project(s)…" overlay was **still occurring after the
PR #284 fix merged**. A four-track investigation (code trace, embedded-wheel autopsy, live Chromium
reproduction, caching audit) found the fix itself is correct — a live BFCache reproduction showed the
`pageshow` reset restoring the overlay hidden — but it **never reached the deployment**, for two
compounding reasons:

1. **Stale embedded wheel.** All nine installers embed one shared base64 wheel. That wheel was built
   at 02:28 UTC on 2026-07-07 (the ADR-0147 regeneration); the overlay fix landed at 16:38 the same
   day and touched only `home.js` + tests — nobody regenerated the installers. The deployed tool
   serves `home.js` *from the wheel*, so a reinstall reinstalled the bug. The installer test suite
   could not catch this: it pinned only the wheel's **version string** (unchanged at 1.0.0), not its
   content.
2. **Browser-cached stale JS.** `/static` is served by Starlette `StaticFiles`, which sends
   ETag/Last-Modified but **no Cache-Control**, so browsers apply *heuristic* freshness and may serve
   a cached `home.js` without revalidation for days. Installed deployments run a **fixed port**, so
   the cache origin persists across restarts and upgrades — even a correctly upgraded server can keep
   executing the old JS in the operator's browser.

## Decision

1. **Version-busted static URLs.** `_page()` pipes the rendered HTML through `_bust_static()`, which
   rewrites every `/static/<asset>` reference to `/static/<asset>?v=<package version>`
   (`_ASSET_VERSION` from `importlib.metadata`, `"dev"` from a raw tree). A new release mints new
   URLs, so no pre-upgrade cache entry can ever satisfy them. Server-side resolution is unaffected
   (StaticFiles ignores the query).
2. **`Cache-Control: no-cache` on `/static/*`**, added in the existing `_liveness` middleware beside
   the security headers. Stored copies must revalidate (cheap 304s stay); heuristic freshness is
   disabled. Belt to the braces of (1).
3. **Wheel/source lockstep is now test-enforced.**
   `test_embedded_wheel_is_in_lockstep_with_the_source_tree` byte-compares every packaged
   `schedule_forensics/**` file inside the embedded wheel against `src/schedule_forensics/**` (both
   directions). Any PR that changes a packaged file without regenerating the wheel + installers fails
   the gate — the exact failure mode of this incident can no longer ship silently.
4. **Version bumped 1.0.0 → 1.0.1** and the wheel + all nine installers regenerated from post-fix
   source (verified: the embedded `home.js` carries the `pageshow` reset; the embedded `app.py`
   carries `_bust_static`).

## Consequences

- Every future PR touching packaged source must run
  `python -m build --wheel --outdir dist/wheel && python tools/installer/build_installers.py
  dist/wheel/schedule_forensics-*.whl` — the lockstep test makes forgetting impossible. Installer
  diffs get large (embedded base64), which is the accepted cost of one-file installers (ADR-0144).
- The operator upgrade path is now self-healing: new installer → new wheel → new `?v=` URLs → the
  browser cannot reuse any stale asset, with `no-cache` keeping all future fetches revalidated.
- One test adjusted for the query string (`test_airgap.py` strips `?…` before the extension check);
  two exact-URL assertions in `test_target_and_theme.py` updated to the busted form. Air-gap posture
  unchanged: the query is same-origin decoration; CSP and the no-external-asset guarantees hold.

## Alternatives considered

- **Hash-named assets (true content addressing).** Stronger but heavier: requires a build step for
  vendored files, contradicting the no-bundler rule. Version-query busting + no-cache achieves the
  same operator-visible guarantee here.
- **`no-store` on static.** Overkill: kills 304 efficiency for zero freshness gain over `no-cache`.
- **Comparing wheel to a freshly-built wheel in-test.** Slower (full build per test run) and adds a
  `build` dependency to the gate; byte-comparing against the source tree is equivalent for packaged
  files.
