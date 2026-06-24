# ADR-0120 — Auto-shutdown idle grace: 10 seconds → 10 minutes

- Status: accepted
- Date: 2026-06-24
- Supersedes/relates: ADR-0022 (desktop icon + auto-shutdown on browser close — the original
  `idle_grace` = 10s), ADR-0032 (in-flight requests hold the watchdog so a long import is not
  mistaken for an absent operator)

## Context

The desktop launcher builds the app with `auto_shutdown=True`; a daemon watchdog stops the server
once a browser has connected and then gone quiet for `idle_grace` seconds (the pure, tested
`_is_idle(browser_seen, idle_seconds, grace)`). Every open page beats `POST /api/heartbeat` every
**3 seconds** (`static/heartbeat.js`); when the last window closes the beats stop, the watchdog
fires, and the whole tool turns off. ADR-0022 set `idle_grace = 10s` so closing the window stopped
the server almost immediately.

Ten seconds is too aggressive in normal use:

- **Backgrounded/minimized tabs throttle timers.** Modern browsers clamp `setInterval` in a
  hidden or background tab (often to ~once per minute, sometimes more). With a 10s grace, simply
  minimizing the tool or switching to another window long enough for one beat to be throttled past
  10s makes the watchdog shut down a **still-open** session. ADR-0032 fixed the *server-busy* false
  positive (in-flight work holds the watchdog), but not the *quiet-but-open* one.
- **Brief navigation away / sleep.** Stepping away for a moment, or letting the laptop sleep, kills
  the session and forces a relaunch.

Operator request: give the tool **10 minutes** of idle time before it times out once opened.

## Decision

`create_app`'s `idle_grace` default changes **10.0 → 600.0** (10 minutes). The watchdog, the 3s
heartbeat, the in-flight-request hold (ADR-0032), and the pure `_is_idle` decision are otherwise
unchanged; the launcher and `serve()` inherit the new default (neither passes `idle_grace`
explicitly). The in-page **Quit** control and `POST /api/shutdown` still stop the server
immediately — the grace only governs the *passive* browser-gone timeout.

## Consequences

- A backgrounded/minimized tab with throttled heartbeats, a brief navigation away, or a short
  sleep no longer shuts the tool down; the operator returns to the same session for up to 10
  minutes. Closing the window still turns the tool off — now ~10 minutes later instead of ~10s,
  or instantly via Quit.
- No data-sovereignty change: the server is still loopback-only, std-lib I/O, air-gap CSP intact;
  this only lengthens how long an *idle local* process lingers before self-terminating.
- Tests: `test_default_idle_grace_is_ten_minutes` pins the 600s default (launcher mode included)
  and that an explicit override still wins; the existing watchdog/`_is_idle` tests (which inject a
  tiny grace) are unchanged.
