# ADR-0275 — "Play all" coordinator: manual chart control halts the master animation

Status: accepted (2026-07-19)

## Context

Operator bug report (Mission Control): "there is an issue with the play/stop functionality on the
charts when you enlarge them. I hit stop, and it continued to play."

The animated charts (trend / margin / curves version-steppers, plus the bow-wave, S-curve, drift,
path-evolution and quality-trend steppers) each carry a per-chart `‹ Prev / ▶ Play / Next ›` control
with its **own** timer, AND every page that tiles them has a **master "Play all"** — `mission.js` on
the Mission wall, the `#sfPlayAll` control on the Trends page — that steps every chart *in lockstep*
by **programmatically clicking each chart's Next button** on a 1.6 s timer.

The defect: a per-chart `stop()` cleared only **that chart's own** timer. While the master was
running it kept clicking the chart's Next, so the chart kept advancing even though its own button
read "▶ Play" (its own timer was off) — the screenshot symptom exactly. Enlarging a chart made it
worse: the operator focuses on the one enlarged chart, the master control is scrolled out of view, so
hitting the chart's Stop looked like it simply didn't work. There was no coupling between an
individual chart's controls and the master, so manual control was impossible while "Play all" ran.

## Decision

A tiny shared **coordinator** in `chartframe.js` (loaded on every page, before the chart scripts):

- `window.SFPlayAll` with `register(stopFn)` (idempotent) and `stopAll()` (fans out to every
  registered master, one failure never blocking the rest).
- Each page master **registers its `stop()`**: `mission.js` (the wall master) and `trend.js`'s
  `#sfPlayAll` (the Trends-page master).
- A single **capture-phase** `document` click listener: on a **TRUSTED** click
  (`event.isTrusted === true`) whose target is inside any per-chart animation control
  (`.sf-frame-play/next/prev` plus the dedicated `#autoPlay/#scurvePlay/#driftPlay/#evoPlay/#qualPlay`
  and their `#next*/#prev*` step buttons), it calls `SFPlayAll.stopAll()` **before** the control's own
  handler runs. So the moment the operator touches a chart by hand, the auto-play-all halts and their
  manual Stop/Prev/Next behaves as expected.

The **`isTrusted` guard is load-bearing**: the master itself advances charts via
`element.click()`, which dispatches a synthetic event with `isTrusted === false`, so the master's own
stepping never trips the listener and never stops itself. Real user clicks are `isTrusted === true`.
Capture phase ensures the master is stopped before the control acts, so there is no one-frame race.

This is additive and air-gap-safe (no new dependency, no external asset); no chart's rendering or the
engine is touched. New animated charts join the coordinator by adding their control id to the
selector (documented inline).

## Consequences

- "Stop" (and Prev/Next) on any chart now reliably halts the motion the operator sees, enlarged or
  not — the reported bug is fixed for **every** animated chart on **every** page in one shared place,
  not per chart.
- Touching one chart stops the whole lockstep "Play all" (all charts) rather than pausing just one.
  This matches the operator's mental model on a lockstep wall ("I want the animation to stop") and is
  the intended, least-surprising behavior; a genuine per-chart pause-while-others-run is not a goal.
- Verified by a Node harness (`tests/web/js/playall_harness.mjs`, run by
  `tests/web/test_playall_js.py`): the coordinator stops registered masters on a trusted control
  click, does **not** on a programmatic (untrusted) click, ignores trusted clicks off any control,
  and `stopAll()` fans out to each distinct master exactly once (idempotent registration).

## Verification pointers

`chartframe.js` (the coordinator + capture listener), `mission.js` / `trend.js` (master
registration). Harness assertions cover the trusted-vs-programmatic distinction that is the crux of
the fix. The pre-existing per-chart `stop()`/timer logic and the masters' own stepping are unchanged.
