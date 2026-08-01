# ADR-0333 — Observers read records, and telemetry probes only on demand

Status: accepted (2026-08-01)
Implements: the approved completion plan, **Phase 2 (performance)**
Builds on: ADR-0286 (`tooltips.js` — the records-based observer this generalises), ADR-0249 /
ADR-0261 / ADR-0263 (the perf regression harness and its epoch-keyed caches), ADR-0147 (the
telemetry module), ADR-0180 / ADR-0187 (the shared Gantt primitives)

## Context

Phase 2 was scoped by the prior session to two things: the idle pumps, and the observer storm.
The idle-pump half was already correct and is recorded here so it is not re-chased — the client
pumps are exactly two, `sysmon.js` (2 s) and `heartbeat.js` (3 s); **the heartbeat must never be
paused** (`idle_grace=600` would shut the tool down after ten minutes minimized and lose the
session), and `sysmon.js` already skips its fetch while `document.hidden`. The
`setInterval(…, 1600)` steppers across 11 modules are **Play-gated, not idle** — the wrong bucket.

That left two real defects, both measured before anything was changed.

### 1. Three document-wide `MutationObserver`s re-scanned the whole page per inserted node

`vizhints.js`, `gantt.js` and `chartframe.js` each observed `{childList: true, subtree: true}` and
then **ignored the records**, re-running their pass from `document` (or over the whole host):

* `vizhints.js` ran `document.querySelectorAll(".panel h2, … main h3")` and re-tested every
  returned heading against a **114-entry** catalog — for every insertion, forever, because a
  heading that matches no entry is never marked and so is re-scanned every time;
* `gantt.js` ran three full-document passes (`attachStickyScrollbars`, `attachColumnMovers`,
  `attachColumnDrag`);
* `chartframe.js` re-ran `applyZoom()` per mutation, which re-walks every `<svg>` in the host and
  **forces synchronous layout** on every `.cf-zoom-box` (`offsetWidth`/`offsetHeight`).

Worse, two of them **re-arm themselves with their own writes**: `stickyScrollbar` appends its proxy
bar to `<body>` and `attachColumnMovers` appends a grip `<span>` to every header cell, each of which
is itself a `childList` mutation. Measured on `/curves`, 20 insertions drove **80** `table.gantt-grid`
sweeps, not 40 — a 2× echo on top of the per-insertion cost.

`tooltips.js` (ADR-0286) was already correct and is the exemplar this generalises.

### 2. The telemetry probe thread ran launch-to-quit regardless of demand

`web/system.py::_slow_loop` was `while True`. The first `/api/system` request started it, and it
then spawned two subprocesses — on Windows, two `powershell` children — **every five seconds until
the process exited**, whether or not anyone was looking. `sysmon.js`'s `document.hidden` skip stops
the *fetch*, but it is client-side and cannot reach a server loop, so a minimized tool kept paying
for telemetry that could not be seen. This is the "two PowerShell probes every 5 s from launch to
quit" the operator reported, now root-caused.

## Decision

**Observers read their records, flush once per frame, and test the root itself.**

Each of the three callbacks now collects the `addedNodes` that are elements, coalesces them, and
runs one pass per animation frame over that batch — never from `document` again. Because
`querySelectorAll` returns only *descendants* and the node handed to us may **be** the pane, grid or
heading, `gantt.js` gained `eachMatch(root, sel, fn)`, which tests `root.matches(sel)` before
walking it; the three attachers all route through it. This is the correctness half of the change,
not an optimisation: without it an async-built Gantt inserted as a bare `.gantt-scroll` would
silently lose its scrollbar. The attachers remain idempotent per pane/cell, so a re-inserted node is
never decorated twice, and the self-echo becomes a no-op — a grip `<span>`'s own record carries no
table. `chartframe.js` keeps its host-wide pass (zoom is inherently host-wide) but coalesces it to
one call per frame; only the frame's final state is observable, so that is equivalence, not a trade.

Two things were **verified rather than assumed** before settling this shape. First, the batch keeps
only ELEMENT `addedNodes`, which would drop a heading re-titled *in place* (a text-node mutation the
old full-document rescan happened to catch). Every candidate was checked: `trend.js:41`,
`scorecards.js:38`, `resources.js:98` and `a11y.js:23` all set `textContent` on a **detached**
element and append it afterwards, so the observer always sees an element insertion — there is no
in-place retitle in the tool, and a text-node fallback would have cost a `<main>`-wide query per
text insertion for nothing. Second, `resources.js:97` appends a **bare `<h3>`** straight into its
drill container: precisely the case a descendants-only scoped walk would silently drop, and the
concrete reason `eachMatch`/`decorate` test the root itself.

The modules stay **self-contained** rather than sharing a new helper module. ADR-0316 (a
parse-time-rendering module loading before `chartframe.js` crashed first paint) is the precedent:
`gantt.js` is emitted on pages a shared helper would have to be ordered ahead of, and the idiom is
~10 lines. `tooltips.js` and `translate.js` already each roll their own.

**Telemetry probes only while something is asking.** `snapshot()` stamps a monotonic demand clock
and sets an Event; `_slow_loop` checks `probing_wanted()` and, once no snapshot has been requested
for `_IDLE_AFTER` (30 s), clears the Event and **parks** on it — zero subprocesses, zero CPU — until
the next request wakes it. Waking `continue`s straight into a probe, so the first poll after an idle
spell refreshes within one probe instead of waiting out a cadence tick. The dock polls every 2 s
while visible, so a real viewer re-arms demand ~15× inside the window; only nobody-is-watching parks
it. **No value is ever fabricated** — a field the platform cannot provide stays `None` and renders
"—" (Law 2); the only change is that a field may briefly carry its last *real* reading after an idle
spell, which the next poll (≤ 2 s later) replaces.

## Measurement

The metric is **nodes scanned, not calls made**, and the distinction is the whole point: scoping a
query to the inserted node does not reduce the *number* of `querySelectorAll` calls (it can raise it
slightly, since each batched root gets its own now-trivial query) — it collapses what each call has
to walk. Measured in the bundled chromium on `/analysis/Project5`, 30 insertions one per frame:

| selector (nodes returned during the storm) | before | after |
| --- | ---: | ---: |
| `.panel h2, .panel h3, .chart h3, .tile-head h3, main h2, main h3` | **1,275** | **84** |
| `table.gantt-grid` | **62** | **0** |
| `#grid, .gantt-scroll, .path-view, .sra-grid-scroll` | **31** | **0** |

1,368 → 84 nodes walked, ~16×; and each heading walked costs up to 114 substring comparisons on top.
On `/curves` the `table.gantt-grid` echo fell from 80 sweeps to 40 (the 2× self-trigger is gone) and
the `applyZoom` passes halved.

**No wall-clock assertion is made anywhere.** The synthetic storm is rAF-bound — 30 paced frames
dominate it — so elapsed time is flat before and after (887 ms both). The saving is work volume,
which is what bites on the operator's real 2,000-row grids and slower hardware. An absolute timing
gate here would assert nothing and flake on CI.

## Consequences

* Eight new gates, **all proved able to fail by reverting the CALLER and keeping the API** (reverting
  both turns a behavioural failure into an `ImportError`, which proves nothing):
  * `tests/perf/test_perf_regression.py` — source contracts that run on CI, which has no browser:
    records-based + frame-coalesced for both body observers, `eachMatch` tests the root, the
    chartframe reapply is coalesced. Reverting `vizhints.js`'s callback alone fails with
    *"observer ignores what was actually inserted"*.
  * `tests/perf/test_observer_storm.py` (new) — the browser measurement, skipped without the bundled
    chromium like `test_axis_titles_visual.py`. The bound is **relative** (`3 × (insertions +
    headings)`), so it distinguishes the implementations without pinning a count. Reverting
    `vizhints.js`'s callback fails with *1,211 walked, bound 162*; reverting `gantt.js`'s fails with
    *62 gantt-grid nodes walked for 30 unrelated insertions*.
  * three telemetry gates: a deterministic park decision, the arm-on-`snapshot()` contract, and a
    behavioural run of the real `_slow_loop` with compressed cadence. Deleting the park block fails
    with *"the probe thread kept spawning while nobody was asking: 46 extra probes"*.
* **`gantt.js` needs a deliberate digest re-baseline** in `tests/web/test_r11_panel_contract.py`
  (`9fa3a69…` → `d313413…`), following that file's own convention. The pin guards chart geometry
  ("a caption / axis / tick can move with it"); verified inapplicable here — the diff is confined to
  the three attachers and the boot IIFE, `gantt.js` contains **zero** `axisTitles` call sites (the
  census test asserts this independently and stayed green), and `buildTierScale` / `paintGrid` /
  `gridLines` / `timeTiers` are untouched.
* Deferring a pass by one frame means a hidden background tab may not run it until it is shown
  (rAF is throttled there). That is correct for all three: hints matter on hover, sticky scrollbars
  and zoom matter when visible.
* Deliberately **not** changed: the heartbeat (pausing it loses the session), `sysmon.js`'s interval
  (its `poll()` already early-returns while hidden; clearing the timer would save a no-op callback),
  the Play-gated steppers, and `translate.js` / `legend_toggle.js` (already records-based / lazily
  scoped).
