# ADR-0461 — `chartframe.js` is emitted in the layout HEAD: the fetch-callback load-order race behind CI-03 (three "no captions rendered" strikes), and the caption sweep now names its mechanism

- **Status:** Accepted — 2026-09-04 (CI-03's root-cause PR, recommended first in the kickoff; the operator's order)
- **Version:** 1.0.236
- **Extends:** ADR-0316 (round 10: `defer` on `resources.js` / `performance.js` — the parse-time form of this defect), ADR-0340 / ADR-0342 (the DOM helpers' head-loaded home), ADR-0298 (the one axis-caption helper), ADR-0443 (M3-01: `SFPlayAll` defined after `<main>`), ADR-0418 (browser tests execute on a runner)
- **Shipped:** `web/chrome.py` (`_LAYOUT`: the `chartframe.js` tag moves from after `</main>` to the end of the head script group, after `tooltips.js`), `tests/web/test_chartframe_load_order_browser.py` (NEW: 1 layout pin · 6 per-route pins · 1 real-Chromium slow-asset proof with a teeth check), `tests/web/test_axis_titles_visual.py` (a zero-caption cell reports its diagnosis), five re-derived premise pins (`test_axis_titles.py`, `test_dd_line_ledger.py`, `test_r10_performance_contract.py`, `test_r10_resources_contract.py`, `test_margin_dashboard_view.py`), `docs/DESIGN-SYSTEM.md` §4

## Context

`tests/web/test_axis_titles_visual.py::test_captions_survive_every_theme_and_scale` failed three
times in 48 hours on three pages no diff touched — `console@0.9 /forecast` (#626, first attempt),
`console@0.9 /curves` (#629, a docs-only diff), `console@0.9 /cei` (`main`'s own run #1717 for the
#631 squash, tree byte-identical to the green PR head) — every time with the same words, **"no
captions rendered"**, every time in the sweep's FIRST cell, and never twice on one commit. The
ledger's working hypothesis (row CI-03) was a slow first paint outrunning the sweep's suppressed
5-second wait; the kickoff's instruction was to measure what that wait waits for before touching it.

**What the measurement found instead.** Every fetch-driven chart module (`cei.js`, `curves.js`,
`drift.js`, `scurve.js`, `trend.js`, `sra.js`, …) is a synchronous script inside `<main>` that
issues `fetch("/api/…")` at parse time and calls `SFChartFrame.axisTitles` inside its `.then`.
`chartframe.js` — the only definition of `window.SFChartFrame` — was emitted AFTER `</main>`. The
HTML parser yields to the event loop while it waits for a synchronous external script to download,
so a fetch callback CAN run before `chartframe.js` has executed; when it does, `render()` throws
`SFChartFrame is not defined`, the module's own `.catch` swallows the error and prints
**"Failed to load the … data."** (a false sentence: the data loaded, the render threw), and the
page never renders a caption. The project had already met the parse-time form of this defect twice
and fixed it per module with `defer` (ADR-0316: `resources.js`, `performance.js`; later
`margin_dashboard.js`, `volatility.js`); every callback-time consumer stayed exposed, and the
census in this session counted eleven of them.

| Probe (2026-09-04, this container, 4 vCPU) | Result |
| --- | --- |
| **R1 — deterministic.** `chartframe.js` held 1.5 s by route interception; fresh context per page; console@0.9 | /cei · /curves · /forecast · /scurve · /trend: **0 captions**, each printing its "Failed to load …" line, `pageerror` EMPTY (the `.catch` swallowed it); /volatility · /resources · /performance (deferred): captions rendered |
| **R1 baseline** (no delay) | every page captioned; the `/api/*` response arrived 0–100 ms after the script's — the window exists on a quiet box and is small |
| **R2 — stochastic, NO artificial delay.** 6 CPU-hog processes + CDP `setCPUThrottlingRate` 8×, a FRESH browser per iteration, 12 cold loads × 3 routes on the pristine tree | **1 / 36 loads** read `Failed to load the forecast-drift data.` with 0 captions — /forecast, the page #626 struck on; time-to-first-caption elsewhere 1.0–2.5 s (max 2,494 ms) |
| CI's own timing (#1717 browser job) | the sweep ran in the job's first minute (schedules loaded 04:57:19, the test step started 04:56:45): a cold browser, a cold server, the first cell — the widest window |

R2 refutes the slow-paint hypothesis on its own terms: even at 8× throttle under six hogs the
first caption arrived inside 2.5 s, half the 5-second wait. The strikes were the race.

## Decisions

1. **The helper precedes every consumer.** `_LAYOUT` emits `chartframe.js` at the end of the
   head script group (after `tooltips.js`), before `<main>`. A synchronous body script — and any
   callback it schedules — can no longer run before `window.SFChartFrame` (and `window.SFPlayAll`,
   defined in the same file) exists. `chartframe.js` needs nothing from the body at parse time:
   its `boot()` already defers `scan()` and the late-chart observer to `DOMContentLoaded`, and its
   one document-level listener registers on `document`. No per-module guard, no `whenReady`
   wrapper on eleven modules (byte-frozen and line-pinned scripts), no wider timeout.
2. **The `defer` attributes stay.** They are part of four pages' byte-pinned contracts and are
   harmless; what their tests pin now is the property the first paint actually depends on —
   the helper before `<main>` — with the history recorded in each docstring.
3. **Five premise pins re-derived, not deleted.** Each asserted `</main>` before
   `chartframe.js` as the reason for something (why the DOM caption helper and the data-date
   marker live in `gantt.js`, why `defer` was required) and each said "re-derive, do not just
   delete". Re-derived: the DOM helpers keep their home in `gantt.js` **by filing** (table / Gantt
   primitives, ADR-0340 / ADR-0342), no longer by necessity; the head order `gantt.js` →
   `chartframe.js` is the new pinned fact. `docs/DESIGN-SYSTEM.md` §4 says the same.
4. **The sweep names its mechanism.** A zero-caption cell now reports `readyState`, whether
   `SFChartFrame` existed, the chart hosts / svgs present, every "Failed to load …" sentence on
   the page and every page error. Run against the PRE-fix layout with a slow `chartframe.js`, the
   three struck cells read `failed=['Failed to load the bow-wave data.']` (and the curve / drift
   twins) — the diagnosis the three CI strikes never carried. The 5-second wait is unchanged and
   still suppressed, for the reason now written beside it: so the cell reaches the probe and is
   reported with its diagnosis rather than aborting the sweep as a bare timeout.
5. **A regression pin that can fail.** `test_chartframe_load_order_browser.py`: the layout's head
   contains the tag (1); each fetch-driven route serves the helper before `<main>` (6); and in
   real Chromium, with an ASGI middleware holding `/static/chartframe.js` for 2.5 s while every
   `/api/…` answers at once, all six routes caption with no "Failed to load" text and no page
   error — the delay itself asserted to have happened (a middleware that stops sleeping reddens
   the proof by name).

## Verification

- **Red first, on the pristine tree:** the new module 8 failed / 0 passed — the browser proof
  listing all six routes at `captions=0` with their "Failed to load" sentences.
- **Green after:** 8 passed; the six pinning modules 143 passed / 3 env-skipped, including the
  real-browser first-paint proofs for /performance and /resources under the moved script.
- **Mutations:** the layout reverted → the module red 8/8 (the red-first run IS this mutation);
  the middleware's sleep neutralised with the 2.5-s constant intact → the teeth assertion red by
  name (`chartframe.js was not delayed`); the enriched sweep against the pristine layout →
  `failed=[…]` on every struck cell.
- Statics: ruff / format / mypy --strict clean on every touched file.

## Deliberately NOT done

- **The `.catch` sentences are not reworded.** "Failed to load the bow-wave data." conflates a
  fetch failure with a render exception; with the race closed the conflation can no longer print
  a false sentence on load, and splitting it touches byte-frozen / line-pinned page scripts. A UI
  map row, not this PR.
- **`legend_toggle.js` and the rest of the post-`</main>` group stay where they are.** No page
  module calls `SFLegend` (the toggle works by document-level delegation), and no other post-main
  global is consumed by a body script — measured by grep, not assumed.
- **The `_pending` stub pattern (ADR-0443, `mission.js` / `curves.js` / `trend.js`) stays.** It
  now never activates (the coordinator exists first) and is harmless either way.
- **CI-04** (the /driving-path header-row equality race on #632's docs-only diff) is a different
  oracle and is not diagnosed here.

## Consequences

CI-03 is CLOSED in the ledger with its cause named. A first-load "Failed to load …" on a slow
machine — the same race an operator could hit — is closed for every fetch-driven page at once.
The M3-01 class ("`if (window.SFPlayAll)` was always false") cannot recur for `SFChartFrame` or
`SFPlayAll`. The next zero-caption cell, if one ever appears, will say what it saw.
