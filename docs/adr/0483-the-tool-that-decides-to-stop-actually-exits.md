# ADR-0483 — The tool that decides to stop actually exits

* **Status:** Accepted (2026-09-10)
* **Unit:** OR-13 (operator report) — "I still can't open the program when I close the browser
  without quitting", still true on v1.0.252, after ADR-0482 shipped

## Context

**ADR-0482 is not the culprit and is not wrong.** A real-Chromium run on a clean single cycle
measures `POST /api/heartbeat → 200`, `POST /api/closing` sent on unload, and the server stopping
5 s after the close. The *decision* to stop is correct, prompt, and proven. The defect is one
layer below it, in the **exit**.

```
uvicorn 0.52.4 — Config(..., timeout_graceful_shutdown: int | None = None)
web/app.py serve(): uvicorn.Config(app, host=host, port=port, log_level=log_level)   # never set
```

`Server.shutdown` passes that value straight to `asyncio.wait_for`, where **`None` means wait
forever**. `_wait_tasks_to_complete` then spins `while self.server_state.connections` with no
bound. A connection whose peer has stopped draining its socket never leaves that set, so the
drain never ends: the listening socket is already closed, the process is still alive, and the
port is still unbindable. The 600 s idle rule never worked either, for the same reason — a
server survived ~18 h. **The bug was never in the detection.**

### The one-line fix was not shipped on that argument, and the argument turned out to be false

OR-13 recorded the proposed fix together with the reason it looked safe: `active_requests > 0`
already blocks the watchdog from requesting a stop while real work is in flight, so by the time
`should_exit` is set there should be no legitimate long response to cut off. It also flagged that
reasoning as the same species that had died four times on measurement that day, and required a
red-first reproduction before a line was written.

**It was right to.** Measurement refuted it: in the reproduction below the watchdog fires — the
listening socket closes — with **megabytes still queued** to the wedged peer. Starlette's
`BaseHTTPMiddleware` runs the `finally` when *dispatch returns*, which is **before** the response
body finishes streaming, so `active_requests` is already back to `0` while the response is still
being written. The counter never protected a streaming response and never could. What actually
protects a live download is the browser's own heartbeat, which keeps the watchdog from firing at
all. The fix is the same one line; the justification for it is not the one that was written down.

### The reproduction, including the five shapes that did not reproduce

A stop was requested against a real `serve()` in a real subprocess, with a real abandoned socket
left behind. **Five plausible shapes of "the browser went away" all stopped cleanly in ~6 s:** an
idle keep-alive; a half-closed socket after a completed small response; an unread small response;
a truncated request; and a truncated POST whose body never finished arriving. None of them wedges
anything, because a small response fits in the kernel buffers and completes.

What reproduces is a peer that **stops draining bytes the server is still writing** — a tiny
receive window with pipelined requests for a large vendored asset, with and without a FIN:

| | exits? | listening socket | port re-bindable |
|---|---|---|---|
| current build, wedged peer | **no**, at the deadline | closed | **no** |
| current build, wedged peer + FIN | **no**, at the deadline | closed | **no** |
| with a bounded drain | yes, 12.3 s | — | — |
| clean close, either build | yes, ~6 s | — | — |

That last column is the operator's sentence in a measurement: the tool decided to stop, closed its
listener, kept its port, and could not be relaunched onto it.

**One correction to OR-13's reading of its own evidence.** OR-13 reads the operator's `Listen` row
as proof the process was "STILL serving" *during* the hang. It cannot have been: `Server.shutdown`
closes the listening socket **before** it waits, and in every reproduction here the listener is
closed while the process hangs. That capture was taken before the fuse burned. The observation was
real, the inference from it was wrong, and the diagnosis it was attached to is nonetheless correct
— which is exactly the shape QC-2 warns about. A second failure in which the watchdog never fires
at all was hypothesised and **searched for** (a request pinning `active_requests` forever); the
truncated-POST shape refutes it, and no such path was found.

## Decision

**Bound the drain: `SHUTDOWN_DRAIN_TIMEOUT = 5`, passed to `uvicorn.Config`.**

**The bound is set by the launcher, not by taste.** `launcher._HANDOVER_TIMEOUT` is 20 s — how long
a replacement launch waits for a stood-down predecessor to release the port before giving up,
*invisibly*, under `pythonw` with stderr going to `nul`. That is the operator's "I double-click and
nothing happens". The whole stop must fit inside it with room to spare:

```
CLOSE_GRACE (5) + watchdog poll (2) + drain (5) = ~12 s measured, ~8 s of margin
```

`tests/web/test_exit_is_bounded.py::test_the_drain_budget_fits_inside_the_handover_budget` pins
that **arithmetic**, not the constant, so raising any of the three re-opens the question.

`int`, not `float`: that is uvicorn's annotation for the field. The parameter exists and is used in
`Server.shutdown` at the declared floor (`uvicorn==0.29.0`, verified by installing the floor and
introspecting it, not from memory), so `constraints/floor.txt` needs no change.

**What was rejected:** `force_exit`, or killing the process from the watchdog. Both skip the ASGI
lifespan shutdown, and that is the hook that seals and clears the on-disk CUI cache on SIGTERM
(ADR-0335). A Law-1 clear must not be traded for promptness. The bounded drain keeps the whole
graceful path — uvicorn cancels the stragglers on timeout and the lifespan shutdown still runs.

## Consequences

* Once the tool decides to stop it exits, worst case ~12 s, whatever the peer does with its socket.
* The port is released inside the handover budget, so the desktop icon's relaunch stops depending
  on a race it silently loses.
* Nothing legitimate is cut short: a drain only starts once a stop has been *requested* — Quit, a
  replacement launch standing this one down, or the browser gone for `CLOSE_GRACE` (or 600 s idle).
* The 600 s idle rule now works for the first time. It was never a timing problem.

## Residual, measured and stated rather than papered away

A response genuinely in flight to a **live** peer at the moment of a Quit is cut at 5 s. Nothing in
the app streams for that long to a browser that is still there and still beating — an export is
served from memory — but the guarantee now rests on the heartbeat rather than on `active_requests`,
and that is a weaker place than the code's comments used to claim it rested.

Not covered: a peer that drains *slowly but continuously* (a live browser on a saturated link) is
indistinguishable, at this layer, from one that has stopped. It is cut at 5 s like any other.

## How it was proven

Red first, and the red arm is **inside the test**. `test_exit_is_bounded.py` runs the pre-ADR-0483
configuration (`timeout_graceful_shutdown=None`) against the same wedge and **requires it to hang**
before it will trust the green arm. If the wedge fails to bite on some other machine — a different
kernel, a larger socket buffer — that control exits early and the test **fails** instead of handing
back a green that proves nothing. That is the defect class this repo repeats, wired shut.

Then an **8-mutation battery in an isolated worktree with its own venv, 8/8 RED by name**, the
harness refusing any mutation whose replacement equals its anchor (ADR-0482's lesson):

| mutation | caught by |
|---|---|
| drop the `Config` argument | the two behavioural tests, and the fast unit belt |
| `SHUTDOWN_DRAIN_TIMEOUT = None` | both behavioural tests |
| drain grows to 20 s | the budget arithmetic |
| `CLOSE_GRACE` grows to 14 s | the budget arithmetic |
| `_HANDOVER_TIMEOUT` shrinks to 6 s | the budget arithmetic + the close-path test |
| **the wedge is given a wide receive window** | the red arm — instrument neutered, test fails |
| **the wedge asks for one small response** | the red arm — instrument neutered, test fails |

The last two are the ones worth keeping: they mutate the *instrument* rather than the subject, and
they are what makes "the control hung" mean something.
