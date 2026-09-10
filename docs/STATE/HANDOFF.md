# Handoff — 2026-09-10 (OR-13 CLOSED (ADR-0483): the tool that decides to stop actually exits; v1.0.253)

STATUS (current) — `main` @ **`b13dbd61`** (#663, ADR-0483 / OR-13, **v1.0.253**), **MERGED and tree-verified**: `git rev-parse` reads `609e146fe4ec91ac89a98f46d581a64afb8c5ac6` for BOTH the squash and the PR head `51a45639`, so the squash carries exactly the tree the eight green checks ran on. `main`'s own run for the squash is **1827 (`34532629609`)**. Branch `claude/blissful-clarke-tyggug` restarted on `origin/main` with `--prune` + `remote set-head` + `checkout -B`; the squash was never amended. **#662 merged first** (`9922e276`, docs-only) and its squash conflicted with this branch — which already carried the same two docs commits — and was merge-resolved to this branch's side, **proven**: `9922e276^{tree}` == `abf372cf^{tree}`, and the merged tree equalled the pre-merge tree. One unit, **engine untouched**, red-first, mutation-tested **8/8 by name**. Highest ADR **0483**. QC-1/QC-2 bind every session — ADR-0393.

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
