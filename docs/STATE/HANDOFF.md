# Handoff — 2026-09-09 (b) (OR-12 CLOSED (ADR-0482): closing the browser stops the tool in seconds, not in ten minutes; v1.0.252)

STATUS (current) — `main` @ **`f8d639f7`** (#660, the docs-only record of #659's merge, tree-verified `c89dda54…`). Branch `claude/polaris-audit-plan-forward-41qww9`, restarted on it. One unit, **engine untouched**, red-first, mutation-tested **14/14 by name**. Highest ADR **0482**. Version **1.0.252** (wheel + nine installers rebuilt AFTER the last source edit; full suite started after THAT). QC-1/QC-2 bind every session — ADR-0393.

## OR-12 — the operator closed the window and the program kept running

**The report:** close the browser without *Wipe and Quit* and the tool does not stop. **Measured, and it was the spec working as written:** `idle_grace` is **600 s** and `static/heartbeat.js` sent **nothing** on unload — so "I closed the window" and "I walked away" were the SAME event and both waited ten minutes, with Ollama holding its VRAM the whole time. `launcher.py`'s own comment already said so: *"a server legitimately outlives its browser by up to ten minutes. That ten-minute window is exactly when a relaunch lands on it."* ADR-0334 built the port handover to SURVIVE that window; this closes it.

**`pagehide` arms a short fuse; it does NOT mean stop** — forced by the app's shape: **35 server-rendered routes, so every link click is a real page unload**. `heartbeat.js` beacons `POST /api/closing` via `sendBeacon` (the only send that survives unload; CSP `connect-src 'self'` already allows it); the server records `closing_at`; **a heartbeat clears it**, and the next page beats immediately on load, so a navigation cancels the fuse it just armed within ~1 s. `_shutdown_due` stops on EITHER the unchanged 600 s idle rule OR a fuse burned past `CLOSE_GRACE = 5.0`. **`CLOSE_GRACE > HEARTBEAT_INTERVAL = 3.0` is a CONSTRAINT, not a preference** — a fuse shorter than the beat gap expires during an ordinary navigation. Two exclusions, both deliberate: **not `visibilitychange`** (fires on a tab switch, and cancellation would then ride on a THROTTLED background tab) and **not on `event.persisted`** (bfcache — beaconing there stops the tool behind a Back button). **Rejected:** just lowering `idle_grace` — it is load-bearing for the operator reading a long report without clicking.

**Two of the operator's premises were false and are corrected in the ADR:** skipping Wipe-and-Quit does NOT leave CUI on disk (`_trigger_shutdown` seals+clears on every path, watchdog included — ADR-0335); and the Desktop icon launches **`pythonw.exe`** (`template.ps1:460`), which opens no console, so there is no PowerShell window to close from the icon.

## Traps this session paid for, by name

* **2 of 14 mutations came back GREEN and BOTH were findings about the checks.** (a) One mutation had `old == new` — a no-op that reads exactly like a pass; the sandbox harness now REFUSES any mutation whose replacement equals its anchor. (b) Worse species: `test_the_probe_endpoint_never_arms_or_disarms_the_fuse` compared the post-probe value to a "before" value **read out of the same state the mutation corrupts** — clearing the fuse on every request made both sides `None` and the equality held. **An oracle derived from the thing under test cannot judge it** (QC-1). Re-aimed at an ABSOLUTE anchor: armed *at all* first, unchanged second.
* **The red proved the instrument before the instrument was trusted:** the node harness failed on exactly the 3 new-behaviour assertions while its other 5 passed against the OLD code.

## Registered residual (measured, not taken)

A close beacon arriving LATE re-arms the fuse on a live session; the next beat (≤3 s) clears it and the fuse is 5 s, so the beat wins with 2 s margin. **Not covered:** a session whose only remaining page is a THROTTLED background tab beating slower than the fuse burns — the tool could stop with a hidden tab open. Bounded (relaunch + ADR-0334 handover) and strictly better than the ten-minute hang, but real.

## Next — campaign queue

**R-56** (add UID 385, seven heads, both `pc == 0`) · R-49 · R-46 · R-47 · R-52 · R-50 · R-57/58/59 · then R-03 · R-04 · R-09 · R-13 · R-18 · R-21 · R-22 · R-32 · R-39. Other residuals: `/settings` horizontal overflow (its own UI unit; NOT the hint bubble, that is closed) · OR-11b (measure the 48-fact cap on a real 32-file workbook first) · OR-11d (`_AskRecord` exports an unanswered ask without its reason) · the working-minute axis cannot carry a recorded instant on a day boundary · the hint bubble still widens the document while OPEN. **PLUS the design page, owed and still not delivered: `/scorecards` (`setScreen('sk')`)**, 21 artboards remaining (report §6).

**Review cover is still absent** — Codex quota EXHAUSTED on #655, #656, #657, #659 AND #660. Five consecutive PRs with no automated review performed; the mutation battery and the full gate are all this repo gets.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
