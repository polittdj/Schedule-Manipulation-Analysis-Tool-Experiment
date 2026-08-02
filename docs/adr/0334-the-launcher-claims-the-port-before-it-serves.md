# ADR-0334 — The launcher claims the port before it serves

Status: accepted (2026-08-01)
Implements: the approved completion plan, **Phase 1b (the launcher)** — unblocked by the operator
measurement it was waiting on
Closes: the **server-side half of OR-06** ("a fresh open shows fields from previous sessions")
Builds on: ADR-0324 (the launch token), ADR-0332 (the wipe sweep), ADR-0193 (one self-stopping
icon), ADR-0315 (the Ollama lifecycle this launch path also owns)

## Context — a measurement, not a theory

Phase 1b was deliberately **blocked on one operator measurement** for two sessions, because the two
candidate mechanisms needed opposite fixes and a wrong guess would have shipped something that
changed nothing. The measurement arrived on 2026-08-01, on the deployed Windows box running
v1.0.149, and is recorded verbatim in `docs/STATE/OPERATOR-REQUESTS.md` (OR-06):

| step | LISTENING on 8321 | `pythonw` processes |
| --- | --- | --- |
| after stopping | none | none |
| after **1st** launch | 18664 | 18664 + 39740, both 19:33:17 |
| after closing **only the browser** | 18664 (survives) | 18664 + 39740, both 19:33:17 |
| after **2nd** launch | **18664** | 18664 + 39740, **still 19:33:17** |

**The second launch produced nothing** — no new listener, and no fourth process even transiently
(25 s later the process list is byte-identical). So the second launcher started, could not take the
port, and exited **mute**: uvicorn's bind failure becomes `sys.exit` into the `os.devnull` sink that
`_ensure_streams` installs for the windowless `pythonw` shortcut. Meanwhile its **browser timer was
already armed** — `main` starts it before `serve_fn` — so a window opened onto the **old server**,
carrying the previous session's loaded schedules and settings in memory.

This is the handoff's branch one, confirmed. Windows `SO_REUSEADDR` double-binding (branch two) did
not occur. It also defeats ADR-0324's launch token: same process ⇒ same token, so the client-side
guard cannot see a new launch that never happened.

**The survivor is not itself a bug.** `idle_grace` is 600 s, so a server legitimately outlives its
browser by up to ten minutes — that window is precisely when a relaunch lands on it. An earlier
attempt at the measurement showed the server gone 25 s after the browser closed; that run is
**discarded as invalid** (it contradicts the 600 s grace — Quit was evidently clicked) and is
recorded only so the contradiction is not later re-investigated as a finding.

**Consequence for OR-06.** The stale fields have a *second, deeper* cause than the localStorage one
ADR-0324/0332 fixed: **the server itself is the previous session.** No client-side sweep could ever
have fixed that half, which is why the symptom survived those two ADRs.

## Decision

**The port is claimed before anything else happens.** `launcher.claim_port(host, port)` runs before
the browser timer is armed and before uvicorn is asked to bind:

1. **Connect-probe** the port (`port_is_free`). Free ⇒ proceed.
2. Occupied ⇒ **`GET /api/whoami`** to ask who is there.
3. Not us (no answer, or an answer that is not `schedule-forensics`) ⇒ **`PortUnavailable`**. The
   tool refuses to serve rather than bind alongside a stranger.
4. Ours ⇒ **`POST /api/shutdown`**, then poll until the port frees (20 s).
5. Released ⇒ serve fresh. **Not released ⇒ `PortUnavailable`,** naming the pid.

Per the operator's "always start clean" rule a predecessor is **replaced, never reused** — the new
session starts with nothing carried over, which is the whole point.

**The browser timer is NOT moved after `serve_fn`.** `serve_fn` blocks for the life of the process,
so a timer started after it would never fire at all. The fix is ordering *within* the pre-serve
phase: claim, then arm.

**A connect-probe, never a bind-probe.** On Windows a second bind can *succeed* against a port
another process is serving (uvicorn sets `SO_REUSEADDR` and never `SO_EXCLUSIVEADDRUSE`), which
would route requests indeterminately between two servers. A testimony tool must never be in that
state, so binding is never used to answer "is this port taken?".

**`/api/whoami` is new, and it is deliberately not `/api/heartbeat`.** A probe must not refresh
`last_beat` or set `browser_seen` on the instance it is about to replace: that would extend the life
of the process being stood down, and could arm the idle watchdog on a server no browser ever
reached. The endpoint returns only `app`/`pid`/`version`/`launch_token` — no schedule content
(Law 1). The `_liveness` middleware, which refreshes the beat on *every* request, now exempts this
one path, because a launcher probing the port is not the operator being present.

**The loopback probe bypasses the system proxy.** urllib's default opener reads the machine's proxy
settings, so on a corporate-managed Windows laptop even `http://127.0.0.1:8321` can be routed
through the company proxy — the probe would be refused (a live predecessor misread as "not ours",
so the launcher refuses to start for no reason) or, far worse, sent off-machine. The launcher builds
its opener with an **empty `ProxyHandler`**, the same hardening `ai/ollama.py` already applies for
the same Law 1 reason. This was found by bandit flagging the `urlopen` line, and is the more
important half of that finding.

## Consequences

* **Nine new gates** in `tests/test_launcher_single_instance.py`, each **proved able to fail by
  reverting the CALLER and keeping the API**:
  * removing the claim from `main` fails the ordering gate with
    `assert ['browser', 'serve'] == ['claim', 'browser', 'serve']` — *the measured bug, verbatim*;
  * a failed claim opening a browser anyway fails the refusal gate;
  * dropping the `/api/whoami` middleware exemption fails with
    *"the probe refreshed the predecessor's heartbeat"*;
  * letting a stranger be shut down fails *"a stranger's port was sent a shutdown request"*;
  * reverting to a default opener fails with the environment's proxy map printed (Law 1).
* **These are not "a Linux port test".** Bind semantics differ per platform, so pinning them here
  would pin the wrong platform and prove nothing about the operator's machine. What is pinned is the
  **decision logic**, which is identical everywhere. Exactly one test touches a real socket, and it
  asserts only that a connect-probe distinguishes a listener from a free port — portable.
* An assertion written from a **wrong model of urllib** was caught and corrected rather than
  worked around: `ProxyHandler({})` installs no `<scheme>_open` methods, so
  `OpenerDirector.add_handler` never registers it — a correctly hardened opener carries **no**
  `ProxyHandler` at all. The gate therefore asserts *absence of a populated one*, and says why.
* **Not in this ADR, and deliberately so:** the disk-cache half of Phase 1b (clear on clean
  shutdown + atexit, never at launch, plus size and age caps). It is a CUI-at-rest policy decision
  with a real cross-session warm-start trade-off, and it deserves its own round rather than being
  appended to a change whose evidence is a launcher measurement. Carried forward explicitly.
