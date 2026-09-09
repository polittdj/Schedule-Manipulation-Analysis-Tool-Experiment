# ADR-0482 — Closing the browser stops the tool in seconds, not in ten minutes

* **Status:** Accepted (2026-09-09)
* **Unit:** OR-12 (operator report) — "if the user accidentally closes the browser without
  hitting Wipe and Quit, the program should close by itself and reopen cleanly next time"

## Context

**The operator's report, and what was actually measured.** Closing the browser window without
using *Wipe and Quit* leaves the tool running. It is not a hang and not a leak — it is the
documented design working as specified, and the specification was wrong for the case:

* `web/app.py`'s `idle_grace` is **600 s**. The watchdog stops the server when no heartbeat has
  arrived for that long.
* `static/heartbeat.js` sent **nothing on unload**. There was no `pagehide` handler at all.

So *"I closed the window"* and *"I walked away from my desk"* were the **same event** to the
server, and both waited the full ten minutes. For that whole window the Python process stays
up and — because `launcher.main` only stops the Ollama manager on the way out — so does the
local model, holding several GB of VRAM for a program the operator believes they closed.

**The repo already knew.** `launcher.py`'s own comment, verbatim: *"The survivor is not a bug
in itself: `idle_grace` is 600s, so a server legitimately outlives its browser by up to ten
minutes. That ten-minute window is exactly when a relaunch lands on it."* ADR-0334 built the
whole port-handover mechanism to **survive** that window rather than close it. This ADR closes
it; the handover stays as the backstop it was always meant to be.

**One thing the report assumed that is not true, and is worth recording:** skipping *Wipe and
Quit* does **not** leave CUI on disk. `_trigger_shutdown` seals and clears the cache on every
graceful path, watchdog included (ADR-0335). What the operator loses by closing the window is
promptness, not data sovereignty.

## Decision

**`pagehide` arms a short fuse. It does not mean "stop".**

That distinction is the entire design, and it is forced by the app's shape: this is **35
server-rendered routes**, so *every link click is a real page unload*. A `pagehide` handler
that shut the server down would kill the tool the first time the operator clicked anything.

* `heartbeat.js` beacons `POST /api/closing` on `pagehide`, via `navigator.sendBeacon` — the
  only send guaranteed to survive unload. CSP already permits it (`connect-src 'self'`).
* The server records `app.state.closing_at`. **A heartbeat clears it.** A navigation loads the
  next page, which beats *immediately* on load before scheduling its interval, so the fuse it
  just armed is cancelled within about a second.
* `_shutdown_due` stops the tool by **either** route: the unchanged 600 s idle rule, **or** a
  fuse that has burned past `CLOSE_GRACE` with no beat since. `browser_seen` still gates both.
* `CLOSE_GRACE = 5.0` **must** exceed `HEARTBEAT_INTERVAL = 3.0`, and that is a constraint, not
  a preference: a fuse shorter than the gap between beats would expire during an ordinary
  navigation. A test asserts the inequality, and another reads the `3000` literal back out of
  `heartbeat.js` so the vendored JS and the Python constant cannot drift apart unnoticed.

**Two deliberate exclusions:**

* **Not `visibilitychange`.** It fires on a tab switch or a minimise, where the page is alive.
  Arming the fuse there would leave its cancellation to a *background* tab's beats, which
  browsers throttle.
* **Not on `event.persisted`.** That is the back/forward cache: the page is frozen and coming
  back. Beaconing there would stop the tool behind a Back button.

**What was rejected:** simply lowering `idle_grace`. The 600 s grace is load-bearing — an
operator reading a long report without clicking must not be shut down under them. Lowering it
trades this defect for a worse one.

## Consequences

* Closing the last window stops the server, and with it Ollama, in ~5–7 s instead of ~600 s.
* **Reopening is cleaner as a side effect.** ADR-0334's handover exists because a relaunch
  landed on a 10-minute survivor; that window now closes in seconds, so the handover is rarely
  reached. It is unchanged and still correct — this reduces reliance on it, it does not
  replace it.
* The walked-away case is **untouched**: no close signal means the 600 s rule, exactly as
  before.
* In-flight requests still hold the watchdog off (`active_requests > 0`), so a long import is
  never killed by a stray unload.

## Residual, measured and stated rather than papered over

A close beacon that arrives **late** — after the next page has already beaten — re-arms the
fuse on a live session. The following beat (≤3 s) clears it, and `CLOSE_GRACE` is 5 s, so the
beat wins with 2 s of margin. The case this does **not** cover is a session whose only
remaining page is a *throttled background tab* beating slower than the fuse burns; there the
tool could stop while a hidden tab is still open. The blast radius is bounded — the operator
relaunches and ADR-0334's handover applies — and it is strictly better than the ten-minute
hang it replaces, but it is a real edge and it is recorded here rather than claimed away.

## How it was proven

Red first: the Python module failed at collection (`_shutdown_due`, `CLOSE_GRACE`,
`HEARTBEAT_INTERVAL` did not exist), and the node harness failed on exactly the three
new-behaviour assertions while its other five passed against the old code — which is what
proves the instrument works before it is trusted.

Then a **14-mutation battery, 14/14 RED by name**. Two came back green first time and **both
were findings about the checks, not passes**:

* One mutation had `old == new` — a no-op that proves nothing while reading as a pass. The
  harness now refuses any mutation whose replacement is identical to its anchor.
* `test_the_probe_endpoint_never_arms_or_disarms_the_fuse` compared the post-probe fuse value
  to a "before" value **read out of the same state the mutation corrupts**. A mutation clearing
  the fuse on every request made both sides `None` and the equality held. An oracle derived
  from the thing under test cannot judge it (QC-1). Re-aimed at an absolute anchor: the fuse
  must be armed *at all*, and only then must it be unchanged.
