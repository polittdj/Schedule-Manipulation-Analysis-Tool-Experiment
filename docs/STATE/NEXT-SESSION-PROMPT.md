# Kickoff prompt for the next session

Paste the block below verbatim to start the next session. (This file is a pointer, not a status
snapshot — `docs/STATE/HANDOFF.md` is ALWAYS the authoritative "where we are"; if any number here
disagrees with HANDOFF, HANDOFF wins. **Refresh this file whenever the queue changes** — a stale
kickoff steers a fresh session at work that is already done.)

---

Resume POLARIS (Schedule-Manipulation-Analysis-Tool). **Read `docs/STATE/HANDOFF.md` FIRST**
(auto-injected). As of last session: **v1.0.154**, highest ADR **0338**. **Three PRs merged —
#515 (ADR-0336) `1bcf01a`, #516 (ADR-0337) `400f51d`, #517 (ADR-0338) `1835839`** — all with six
CI checks green and no review comments. `git fetch --prune origin` and restart your branch from
`origin/main` — **nothing is in flight**. Fresh container: `pip install -e ".[dev]"` plus
`pip install playwright 'ruff==0.16.1' build`.

**Phases 0, 1a, 1b and 2 are DONE, and the cache question is CLOSED.** The operator chose the
dirty-flag clear (ADR-0336): a write claims the disk cache, a clear releases it, and a launch that
finds a foreign claim empties it — so hard-kill residue leaves at the very next launch, while a
launch after a clean quit still clears nothing. **Do not re-open any of it.**

### ⇢ DO THIS FIRST — Phase 3 UI: `/sra` is the last unconverted Act III route

`/briefing`, `/brief` (ADR-0337) and `/risks` (ADR-0338) are converted and merged. **`/sra` is all
that is left of the four**, and it is the whole of the next UI unit:

* **15 panels** (measured off rendered HTML — the long-carried "13" was WRONG), ≈550 lines across
  `_sra_body` (146) · `_sra_report_blocks` (295) · `_sra_explainers` (66) · `_sra_overrides_table`
  (42). It already has a `page-takeaway` h1; it has **zero** heads/tools/⛶/takes/chips/panelkit.
* The pattern to copy is in the merged PRs: `_panel_head` + `_shell_tools(export_title=…)` + a
  provenance chip + one `.sf-take` per panel, `data-export` to an EXISTING endpoint, and
  `panelkit.js` included **exactly once**.
* **Extend `tests/web/test_act3_panel_contract.py` and `tests/web/test_act3_themes_chromium.py`** —
  they are already the Act III census and grow a row per conversion; `/sra` is the last route
  outside them. Measure the before-census on the pristine tree (`cp` to scratchpad,
  `git show HEAD:… >`, re-render, `cp` back) — **never `git checkout`**.
* Then `DOM_PENDING`'s 7 modules, then the DoD ledgers. **The DD-line ledger must EXCLUDE
  non-time-axis charts** (`histogram.js`, `scatter.js`, `sra_jcl.js`'s cost axis). Follow
  `docs/DESIGN-SYSTEM.md`, **verify in all four themes**, never touch `engine/` for a UI change,
  one page per PR.

Behind: **Phase 4 engine** (`import_notes` propagation · the 3 falsy-zero rows · CC-01's rendering
half — "74 sites" is an approximate grep, **RE-DERIVE it** · SRA-LEGACY · V3) · **Phase 5** monolith
split 2–3 (`app.py` ~21k lines) · **Phase 6** docs/operator queue. **OR-04 stays with the operator.**

### ⇢ The three gate-shapes that keep proving vacuous — check for these BY NAME

Every one of the last three PRs shipped an assertion that could not fail, and every one was found
only by RUNNING the revert:

1. **The code under test destroys its own evidence.** "A clean quit leaves no claim behind" passed
   against a build that never released anything, because `clear()` **unlinks the database file** —
   the marker dies with it either way. The assertion only bites on the Windows FALLBACK path.
   *Ask which of the two implementations your fixture actually exercises.*
2. **A rendered-appearance assertion nobody has made fail.** The four-theme computed-style probe
   passed first try; it took two deliberate CSS reverts (jarvis hiding the tool strip, apollo
   rendering the chip transparent) to show it discriminated. *A style test's failure mode is
   silence.*
3. **A per-route rule tested on one route.** Dropping `/risks`'s takeaway h1 failed NOTHING — the
   takeaway test hard-coded `/brief`. *A loop over `pages.items()` is coverage; a hard-coded key is
   coverage for one key.* Writing the missing gate then exposed a real Law-2 defect in the new
   headline, which quoted a SUM the page never rendered.

**Measured-false, do not re-chase:** two servers bound 8321 simultaneously · the surviving server is
itself the bug (`idle_grace=600` is by design) · a bind-probe answers "is the port taken?" (false on
Windows — connect-probe) · a hardened urllib opener contains an empty `ProxyHandler` (assert
**ABSENCE**) · `tooltips.js` is an observer defect (it is the EXEMPLAR) · querySelectorAll CALL
COUNT measures observer cost (measure **NODES RETURNED**) · `secure_delete=ON` is the obvious Law-1
cache hardening (26 s on the quit path, blows ADR-0334's 20 s handover) · a bare DELETE leaves
plaintext so a residue test is a real gate (false on Debian — assert **RECLAIMED SIZE**) ·
`wipe_gen` stops a late write re-populating the cache (only `/session/wipe` bumps it) ·
`atexit`/`finally` cover a graceful stop (false for SIGTERM — only the ASGI lifespan does) ·
**a pid identifies the run holding the cache** (reused, and `os.kill(pid, 0)` **TERMINATES** on
Windows) · **`/driving-path` is a fifth unconverted page** (that is its EMPTY STATE; `/path` is the
populated, already-converted variant) · **counting `<div class=panel` finds every panel** (it misses
the QUOTED `class="panel …"` form). Known intermittent: the /analysis focus→tip family —
adjudicated, do **NOT** chase.

Standing rules (CLAUDE.md, binding): Law 1 CUI · Law 2 fidelity ("—" never 0; never weaken a test)
· ADR-0240 model/audit protocol · READ EVERYTHING, ASSUME NOTHING, VERIFY EVERYTHING. Full gate
before every commit; statics FOREGROUND first (`node --check` **per file** — a glob checks only the
first); proved-able-to-fail on every new behavioral test (**revert the CALLER, not the API — then
confirm the revert actually removed the behaviour**, and make sure the fixture can discriminate at
all — **run the WHOLE module; a `-k` filter can silently deselect the very test you are targeting**);
HANDOFF rotation + SESSION-LOG + LESSONS-LEARNED same commit; wheel + nine installers ONCE after all
code lands (bump the version BEFORE the background suite).
**NEVER `git checkout <file>` to undo a temporary test mutation** — it discards unstaged real work
in that file; `cp` from a scratchpad copy instead. **`pkill -f <pat>` kills the killer** when the
pattern appears in its own command line. **pytest stdout redirected to a FILE is block-buffered** —
the dot count lags badly and is not a stall. **The `/risks` page title is `Risks & Opportunities`
in source (NOT `&amp;`)** — an Edit that assumes the entity will not match.
