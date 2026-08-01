# Kickoff prompt for the next session

Paste the block below verbatim to start the next session. (This file is a pointer, not a status
snapshot — `docs/STATE/HANDOFF.md` is ALWAYS the authoritative "where we are"; if any number here
disagrees with HANDOFF, HANDOFF wins. **Refresh this file whenever the queue changes** — a stale
kickoff steers a fresh session at work that is already done.)

---

Resume POLARIS (Schedule-Manipulation-Analysis-Tool). **Read `docs/STATE/HANDOFF.md` FIRST**
(auto-injected). As of last session: **v1.0.148**, highest ADR **0332**. Three merges landed:
**#507** (batch 3c-ii, ADR-0330 — AXIS-TITLES complete) as `02decef`, **#508** (Phase 0, ADR-0331 —
the caption halo + a pixel-measuring visual pass) as `5c829e4`, and **#509** (Phase 1a, ADR-0332 —
a wipe resets by reflection). Verify with `git fetch --prune origin` and restart your branch from
`origin/main`. Fresh container: `pip install -e ".[dev]"` plus
`pip install playwright 'ruff==0.16.1' build` first.

**We are executing an operator-APPROVED completion plan** (`/root/.claude/plans/merry-juggling-owl.md`
— if that path is gone, HANDOFF ⇢ NEXT carries the same queue). Order: **perf + session first**,
then UI (hybrid: keep Mission Ops, graft the Command Deck's best ideas), then engine. Phases 0 and
1a are done.

### ⇢ DO THESE THINGS FIRST

1. `git fetch --prune origin`; confirm #509 is merged and restart your branch fresh from
   `origin/main`. **Never amend merged commits to satisfy the stop hook** — restarting the branch
   is the fix (they are published history; rewriting them breaks the CUI guard's
   `inherited_from_main` rule).
2. **Phase 1b — the launcher. CHECK FOR THE OPERATOR'S MEASUREMENT BEFORE BUILDING.** The
   operator was asked to run, on the DEPLOYED box: launch → close ONLY the browser →
   `netstat -ano | findstr :8321` → relaunch → re-check. **One PID or two?**
   * **One** ⇒ the second launch died mute (uvicorn `sys.exit()` into `os.devnull` under
     `pythonw`) and the non-daemon browser timer — started BEFORE the bind — opened onto the
     surviving old process with its old `SessionState`. That also defeats ADR-0324 (same process
     ⇒ same launch token).
   * **Two** ⇒ Windows `SO_REUSEADDR` let a second server bind the same port (uvicorn never sets
     `SO_EXCLUSIVEADDRUSE`), so routing is indeterminate — and a bind-error reporter would fix
     nothing.
   Either way the fix is an **explicit single-instance probe before serving** (`GET /api/heartbeat`
   or a new `/api/whoami`), then — per "always start clean" — `POST /api/shutdown` the old
   instance, wait for the port, and start fresh; if it will not release, **fail visibly** instead
   of opening a browser onto an unknown session. **Do NOT "move the browser timer after
   `serve_fn`" — `serve_fn` blocks for process life**; bind (or probe) first, then start the timer.
   A Linux-only port test pins the WRONG platform — write it as an explicit POSIX-behaviour test
   plus a probe-logic unit test that runs everywhere. Also in 1b: clear the on-disk cache on
   **clean shutdown + atexit, never at launch** (launch-clearing leaves data at rest over the
   between-sessions window and throws away a 9× warm start), plus a size and age cap.
   **If the measurement has not arrived, say so and do Phase 2 instead — do not guess.**
3. **Phase 2 — performance.** The idle pumps are exactly TWO: `sysmon.js` (2 s) and
   `heartbeat.js` (3 s). **Do NOT pause the heartbeat** — `idle_grace=600` would shut the tool
   down after 10 minutes minimized and LOSE the session (data loss introduced by a perf item).
   Lead the observer fix with the **records-based** rewrite (`tooltips.js:71-79`, walk
   `addedNodes`) and rAF/debounce; scoping to `<main>` is the secondary belt and needs an
   assertion that no `.panel`/`.chart`/`.tile-head` renders outside it. The `setInterval(…,1600)`
   steppers are **Play-gated, not idle** (11 modules / 12 sites, incl. `margin.js` and
   `driving_path.js`) — real crash-prevention work, wrong bucket. Windows telemetry spawns two
   PowerShell probes every 5 s from launch to quit — measurable only on the operator's box.
   **Any new cache MUST key through `_cache_key`/`_invalidate_scope`** (filter + target scoped) or
   it serves a differently-scoped number — Law 2, not a perf detail. Extend
   `tests/perf/test_perf_regression.py`; no absolute wall-clock gates in CI.
4. Behind: **Phase 3 UI** (the four unconverted Act III pages `/sra`, `/risks`, `/briefing`,
   `/brief` — zero panelkit/`_panel_head`/`_shell_tools`/`sf-take`; then `DOM_PENDING`'s 7
   modules; the DD-line ledger must EXCLUDE non-time-axis charts) · **Phase 4 engine**
   (`import_notes` propagation · the 3 falsy-zero rows · CC-01's rendering half — the "74 sites"
   is an approximate grep, RE-DERIVE it · SRA-LEGACY · V3) · **Phase 5** monolith split 2–3
   (`app.py` is 20.9k lines, 2.8k LARGER than ADR-0297 left it) · **Phase 6** docs/operator queue.
   **The OR-04 ball stays with the operator** (run
   `audit/operator-artifacts/collect-ollama-artifacts.ps1` on the deployed box after one
   Ask-the-AI question; commit outputs + `smoke-results.md`). Known intermittent: the /analysis
   focus→tip family — adjudicated, do NOT chase as a regression.

Standing rules (CLAUDE.md, binding): Law 1 CUI · Law 2 fidelity ("—" never 0; never weaken a
test; a fast wrong number is worthless) · ADR-0240 model/audit protocol · READ EVERYTHING,
ASSUME NOTHING, VERIFY EVERYTHING. Full gate before every commit; statics FOREGROUND first;
proved-able-to-fail on every new behavioral test (**revert the CALLER, not the API** — reverting
both turns a behavioural failure into an ImportError, which proves nothing); HANDOFF rotation +
SESSION-LOG + LESSONS-LEARNED same commit; wheel + nine installers ONCE after all code lands
(bump the version BEFORE launching the full background suite, or its installer-lockstep tests
red-herring against the stale wheel).
