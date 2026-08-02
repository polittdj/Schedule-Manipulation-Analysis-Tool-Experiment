# Kickoff prompt for the next session

Paste the block below verbatim to start the next session. (This file is a pointer, not a status
snapshot — `docs/STATE/HANDOFF.md` is ALWAYS the authoritative "where we are"; if any number here
disagrees with HANDOFF, HANDOFF wins. **Refresh this file whenever the queue changes** — a stale
kickoff steers a fresh session at work that is already done.)

---

Resume POLARIS (Schedule-Manipulation-Analysis-Tool). **Read `docs/STATE/HANDOFF.md` FIRST**
(auto-injected). As of last session: **v1.0.151**, highest ADR **0335**. **PR #513 (Phase 1b
remainder, ADR-0335) is MERGED** as `e0fdf85`, all six checks green including `windows`.
`git fetch --prune origin` and restart your branch from `origin/main` — **nothing is in flight**.
Fresh container: `pip install -e ".[dev]"` plus `pip install playwright 'ruff==0.16.1' build`.

**Phases 0, 1a, 1b (BOTH halves) and 2 are DONE.** The disk cache now empties itself on every quit
(the operator's decision), seals before it clears, and `prune()` bounds what a hard kill leaves.
**Do not re-open any of it** — see the measured-false list below.

### ⇢ DO THESE THINGS FIRST

1. `git fetch --prune origin`; confirm `origin/main` is at `e0fdf85` or later and restart your
   branch fresh from it. **Never amend merged commits to satisfy the stop hook** — restarting the
   branch is the fix.
2. **Phase 3 — UI (hybrid: keep Mission Ops, graft the Command Deck's best ideas).** This is the
   head of the queue. The four unconverted Act III pages (`/sra`, `/risks`, `/briefing`, `/brief` —
   zero panelkit/`_panel_head`/`_shell_tools`/`sf-take`); then `DOM_PENDING`'s 7 modules; then the
   DoD ledgers. **The DD-line ledger must EXCLUDE non-time-axis charts** (`histogram.js`,
   `scatter.js`, `sra_jcl.js`'s cost axis). Follow `docs/DESIGN-SYSTEM.md` and **verify in all four
   themes**. Never touch `engine/` for a UI change; one page shell per PR, never big-bang.
3. Behind: **Phase 4 engine** (`import_notes` propagation · the 3 falsy-zero rows · CC-01's
   rendering half — "74 sites" is an approximate grep, **RE-DERIVE it** · SRA-LEGACY · V3) ·
   **Phase 5** monolith split 2–3 (`app.py` ~20.9k lines) · **Phase 6** docs/operator queue.
   **OR-04 stays with the operator.**

### ⇢ OPEN — the operator's call, do NOT take it unilaterally

Because a clean quit now clears everything, hard-kill residue actually survives **until the end of
the next clean session**, not the 24 h the age cap implies: the age cap only ever bites at a launch,
so a kill-then-relaunch-in-five-minutes keeps rows the size cap alone will not evict. Closing that
deterministically means deleting every row **not written by the current launch** — which is
**clear-at-launch by another name**, the one thing the approved wording forbids. Ask before acting.

**Measured-false, do not re-chase:** two servers bound 8321 simultaneously · the surviving server is
itself the bug (`idle_grace=600` is by design — the bug is relaunching ONTO it) · a bind-probe
answers "is the port taken?" (false on Windows — connect-probe) · a hardened urllib opener contains
an empty `ProxyHandler` (assert **ABSENCE**) · `tooltips.js` is an observer defect (it is the
EXEMPLAR) · querySelectorAll CALL COUNT measures observer cost (measure **NODES RETURNED**) ·
**`secure_delete=ON` is the obvious Law-1 hardening for the cache** (26 s on the quit path, blows
ADR-0334's 20 s handover, and redundant once `clear()` unlinks) · **a bare DELETE leaves plaintext,
so a residue test is a real gate** (false on this box — Debian compiles `SECURE_DELETE` ON; assert
**RECLAIMED SIZE**, which is portable) · **`wipe_gen` stops a late write re-populating the cache**
(false: only `/session/wipe` bumps it) · **`atexit`/`finally` cover a graceful stop** (false for
SIGTERM — only the ASGI lifespan does). Known intermittent: the /analysis focus→tip family —
adjudicated, do **NOT** chase.

Standing rules (CLAUDE.md, binding): Law 1 CUI · Law 2 fidelity ("—" never 0; never weaken a test)
· ADR-0240 model/audit protocol · READ EVERYTHING, ASSUME NOTHING, VERIFY EVERYTHING. Full gate
before every commit; statics FOREGROUND first (`node --check` **per file** — a glob checks only the
first); proved-able-to-fail on every new behavioral test (**revert the CALLER, not the API — then
confirm the revert actually removed the behaviour**, and make sure the fixture can discriminate at
all); HANDOFF rotation + SESSION-LOG + LESSONS-LEARNED same commit; wheel + nine installers ONCE
after all code lands (bump the version BEFORE the background suite).
**NEVER `git checkout <file>` to undo a temporary test mutation** — it discards unstaged real work
in that file; `cp` from a scratchpad copy instead. **`pkill -f <pat>` kills the killer** when the
pattern appears in its own command line.
