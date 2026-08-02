# Kickoff prompt for the next session

Paste the block below verbatim to start the next session. (This file is a pointer, not a status
snapshot — `docs/STATE/HANDOFF.md` is ALWAYS the authoritative "where we are"; if any number here
disagrees with HANDOFF, HANDOFF wins. **Refresh this file whenever the queue changes** — a stale
kickoff steers a fresh session at work that is already done.)

---

Resume POLARIS (Schedule-Manipulation-Analysis-Tool). **Read `docs/STATE/HANDOFF.md` FIRST**
(auto-injected). As of last session: **v1.0.150**, highest ADR **0334**. **Both of last session's PRs are
MERGED** — #510 (Phase 2, ADR-0333) as `1e51079` and #511 (Phase 1b, ADR-0334) as `e0b0fcf`.
`git fetch --prune origin` and restart your branch from `origin/main` (nothing is in flight).
Fresh container:
`pip install -e ".[dev]"` plus `pip install playwright 'ruff==0.16.1' build` first.

**Phases 0, 1a, 1b (launcher half) and 2 are DONE.** The operator measurement Phase 1b was blocked
on ARRIVED and is banked in `docs/STATE/OPERATOR-REQUESTS.md` (OR-06), committed on its own as
`3eb317b`. **The answer was ONE PID** — the second launch produced no listener and no process at
all; it exited mute and its already-armed browser timer opened onto the OLD server. That was the
SERVER-side half of OR-06. **Do not re-collect that measurement, and do not re-open the
double-bind theory — it is measured false.**

### ⇢ DO THESE THINGS FIRST

1. `git fetch --prune origin`; confirm what merged and restart your branch fresh from `origin/main`.
   **Never amend merged commits to satisfy the stop hook** — restarting the branch is the fix.
2. **Phase 1b REMAINDER — the disk cache. Held back deliberately; ASK THE OPERATOR FIRST.**
   The approved wording is: clear on **clean shutdown + atexit, NEVER at launch** (launch-clearing
   leaves data at rest across the whole between-sessions window), plus a **size and age cap** as
   the belt for a hard kill that never cleared. `engine/cache.py` already has `clear()`; it needs a
   `prune(max_bytes, max_age)` plus wiring into `_trigger_shutdown` and `launcher.main`'s
   `finally`. **Confirm the intent before building:** clearing on every quit does discard the
   cross-session warm start, and that is a CUI-at-rest policy call the operator owns, not an
   inference. Any new cache key MUST route through `_cache_key`/`_invalidate_scope` — Law 2.
3. **Phase 3 — UI (hybrid).** The four unconverted Act III pages (`/sra`, `/risks`, `/briefing`,
   `/brief` — zero panelkit/`_panel_head`/`_shell_tools`/`sf-take`); then `DOM_PENDING`'s 7
   modules; then the DoD ledgers. **The DD-line ledger must EXCLUDE non-time-axis charts**
   (`histogram.js`, `scatter.js`, `sra_jcl.js`'s cost axis). Follow `docs/DESIGN-SYSTEM.md` and
   verify in all four themes.
4. Behind: **Phase 4 engine** (`import_notes` · the 3 falsy-zero rows · CC-01's rendering half —
   "74 sites" is an approximate grep, RE-DERIVE it · SRA-LEGACY · V3) · **Phase 5** monolith split
   2–3 (`app.py` 20.9k lines) · **Phase 6** docs/operator queue. **OR-04 stays with the operator.**
   Known intermittent: the /analysis focus→tip family — adjudicated, do NOT chase.

**Measured-false, do not re-chase:** two servers bound 8321 simultaneously · the surviving server
is itself the bug (`idle_grace=600` is by design — the bug is relaunching ONTO it) · a bind-probe
answers "is the port taken?" (false on Windows — connect-probe) · a hardened urllib opener contains
an empty `ProxyHandler` (urllib never registers a handler that installs no methods — assert
ABSENCE) · `tooltips.js` is an observer defect (it is the EXEMPLAR) · querySelectorAll CALL COUNT
measures observer cost (measure NODES RETURNED).

Standing rules (CLAUDE.md, binding): Law 1 CUI · Law 2 fidelity ("—" never 0; never weaken a test)
· ADR-0240 model/audit protocol · READ EVERYTHING, ASSUME NOTHING, VERIFY EVERYTHING. Full gate
before every commit; statics FOREGROUND first (`node --check` **per file** — a glob checks only the
first); proved-able-to-fail on every new behavioral test (**revert the CALLER, not the API**);
HANDOFF rotation + SESSION-LOG + LESSONS-LEARNED same commit; wheel + nine installers ONCE after
all code lands (bump the version BEFORE the background suite).
**NEVER `git checkout <file>` to undo a temporary test mutation** — it discards unstaged real work
in that file; `cp` from a scratchpad copy instead.
