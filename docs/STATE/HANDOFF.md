# Handoff — 2026-09-10 (OR-13 CLOSED (ADR-0483): the tool that decides to stop actually exits; v1.0.253)

STATUS (current) — `main` @ **`26d821e3`** (#666). **The OR-13 arc is FULLY MERGED — four PRs, every squash tree-verified against its head**: #663 `b13dbd61`/`51a45639` (`609e146f…`) · #664 `902088b0`/`931c0e0e` (`95b7039e…`) · #665 `b195c7d3`/`1098bcf7` (`52c1d084…`) · #666 `26d821e3`/`dfa7bb6c` (`9b244aff…`). No squash was ever amended. `main`'s runs **1827 SUCCESS**, **1829 SUCCESS**, **1833** (`34551102503`, #666). **OR-13 CLOSED** — ADR-0483, **v1.0.253**, engine untouched, red-first, mutation-tested **8/8 by name**, 8/8 green on the PR and green on `main` itself. Highest ADR **0483**. Branch restarted on `origin/main`, clean, no PR open.

**NEW, registered 2026-09-11:** `test_driving_path_whole_schedule_browser.py:104` is **width-racy** — it went red on #667 (docs-only, `src`/`tests` byte-identical to `main`) while `main`'s run 1833 passed on the same code two minutes earlier. The assertion compares the rendered `thead` inner_text of two separately-rendered pages, so it is width-sensitive, and both captures wait on ROWS (`#pathBody tr[data-uid]`), never on the timescale. **Not a flake — a race with a mechanism.** Its own unit; do NOT fix it by widening a wait. Details in SESSION-LOG.

**THE NEXT UNIT IS `/scorecards`, and the operator chose a FRESH SESSION for it** (2026-09-11, at 64% context here): 21 artboards with four-theme render-verify does not fit the headroom left, and a design unit split across a handoff loses coherence at the seam. See `NEXT-SESSION-PROMPT.md`.

## OR-13 — the tool decided to stop and then could not exit

**Root cause, confirmed by measurement rather than adopted from the handoff.** `uvicorn.Config` defaults `timeout_graceful_shutdown` to `None`; `Server.shutdown` hands that to `asyncio.wait_for`, where `None` means **wait forever**. A peer that stops draining bytes the server is still writing never leaves `server_state.connections`, so the drain never ends — listener already closed, process alive, **port unbindable**. That last one is the operator's sentence, measured: `port_rebindable=False`. Fix is `SHUTDOWN_DRAIN_TIMEOUT = 5` on the Config, bounded by `launcher._HANDOVER_TIMEOUT` (20 s), not by taste: `CLOSE_GRACE 5 + watchdog poll 2 + drain 5 = ~12 s`, ~8 s of margin, and the **arithmetic** is pinned, not the constant.

**The kickoff's own safety argument was refuted, and the fix shipped anyway.** OR-13 said a short value looked safe because `active_requests > 0` blocks the watchdog while real work is in flight. **False, and now measured:** Starlette's `BaseHTTPMiddleware` runs the `finally` when *dispatch returns*, which is before the response body finishes streaming — the watchdog fires with megabytes still queued. The counter never protected a streaming response. The heartbeat does. Same one line, different reason; the code comments that claimed otherwise are corrected.

**Five plausible repro shapes stopped cleanly in ~6 s and proved nothing:** idle keep-alive · half-closed after a small response · unread small response · truncated request · truncated POST. Only a peer that stops draining a *large* in-flight write wedges it (tiny receive window + pipelined requests for a real vendored asset). A second failure mode — a request pinning `active_requests` forever, which would explain the operator's `Listen` row — was hypothesised, searched for, and **refuted**; that capture was simply taken before the fuse burned. OR-13's observation was right, one inference from it was wrong, the diagnosis was right anyway.

## Traps this session paid for, by name

* **The red arm lives INSIDE the test.** `test_exit_is_bounded.py` runs the pre-fix configuration against the same wedge and requires it to HANG before trusting the green arm. On a machine with bigger socket buffers the wedge would not bite — and the control exits early and the test **fails**, instead of returning a green that measured nothing.
* **Two of the eight mutations target the instrument, not the subject** (wide receive window · one small response). Those are the ones that make "the control hung" mean anything; a battery that only mutates the subject cannot tell a working oracle from a lucky one.
* **The shallow clone lies about the MPXJ pin, generously.** `+60` → `f021b5e6`, `+200` → `1df4d4a1`, `+400` → `42d92dc9`. Each intermediate answer is a graft boundary that *looks* like a real commit. Deepened to a full clone (760 commits, `shallow=false`) and confirmed `42d92dc9…` is stable — only then is `build_installers.py` allowed to run without `SF_MPXJ_REF`.

## Next — campaign queue

**R-56** (add UID 385, seven heads, both `pc == 0`) · R-49 · R-46 · R-47 · R-52 · R-50 · R-57/58/59 · then R-03 · R-04 · R-09 · R-13 · R-18 · R-21 · R-22 · R-32 · R-39. Other residuals: ADR-0483's own (a live-peer response is cut at 5 s; a slow-but-live drain is indistinguishable from a dead one at this layer) · `/settings` horizontal overflow (its own UI unit; NOT the hint bubble, that is closed) · OR-11b (measure the 48-fact cap on a real 32-file workbook first) · OR-11d · the working-minute axis cannot carry a recorded instant on a day boundary · the hint bubble still widens the document while OPEN. **PLUS the design page, owed four sessions running and still not delivered: `/scorecards` (`setScreen('sk')`)**, 21 artboards remaining (report §6).

**Review cover is still absent** — Codex quota EXHAUSTED on #655, #656, #657, #659, #660 AND #661. Six consecutive merges with no automated review performed; the mutation battery and the full gate are all this repo gets.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
