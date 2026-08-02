# Handoff — 2026-08-02b (a launch clears only what a killed run left behind; ADR-0336; v1.0.152)

> ## STATUS (current) — **the operator's open cache question is ANSWERED and IMPLEMENTED.** They
> chose the **dirty-flag clear**, and ADR-0336 lands it: a write **claims** the on-disk cache for
> the running process, a clear **releases** it, and a launch that still finds someone else's claim
> knows the previous run never reached a clear — a hard kill — and empties the cache before doing
> anything else. A launch after a clean quit finds no marker and clears nothing, so ADR-0335's
> approved "**never clear at launch**" wording stays true as written. Session opened by confirming
> **#514 was already merged** (`e1c81cf`, `origin/main`'s tip) and restarting the branch from it.
>
> ## What the hole actually was (and why the 24 h cap did not close it)
> `prune()`'s age cap is only ever evaluated **at a launch**. Once clearing-on-quit became the rule
> that produced a consequence nobody chose: kill a session hard → relaunch five minutes later →
> every row is inside both caps, so the constructor's prune evicts **nothing** → the residue is
> carried through that entire next session, and the first thing to remove it is the *clean quit
> that ends it*. "A day at most" was in practice "until the end of the next clean session".
>
> ## The design, and the three things that were deliberately NOT done
> One `meta` row (`key='run'`) holding a **per-process token**. Claimed inside the SAME transaction
> as the content row it vouches for (no unclaimed window, no second write-path transaction), once
> per run, not per write.
> 1. **Not the pid.** Pids are reused and the portable liveness probe does not exist: `os.kill(pid,
>    0)` asks a question on POSIX but on Windows **terminates the target**. Only equality is ever
>    needed, so a token carries no platform behaviour at all.
> 2. **Not keyed on `seal()`.** `clear()` has two callers with different intent — the quit (sealed)
>    and `/session/wipe` (not sealed, session continues) — and BOTH must release: after a wipe the
>    session keeps working and its next write **re-claims**, so a kill after the wipe is caught
>    exactly as a kill before it. Keying on `_sealed` would have meant trusting each of ADR-0335's
>    four shutdown layers to seal first; keying on the operation trusts nothing.
> 3. **Not clear-at-launch.** A cache with rows but NO marker (an older build's) still takes the
>    prune path untouched — pinned by its own test, which is the guard against this quietly
>    degenerating into the thing the operator ruled out.
>
> ## Verification (every number read from a run this session)
> **SIX reverts, each reverting the CALLER**, and every new gate proved able to fail: R1 never
> launch-clears → 2 fail · R2 clears at EVERY launch → 2 fail · R3 drops the identity comparison →
> 1 fails · R4 drops the `_claimed` reset → 1 fails · R5 `clear()` stops releasing → 2 fail · R6
> writes never claim → 2 fail. **R5 caught a VACUOUS gate**: the clean-quit test passed against a
> build that never released anything, because `clear()` **unlinks the database file**, so the
> marker goes with it either way. The explicit `DELETE` earns its place only on the **Windows
> fallback** path (an open reader refuses the unlink → tables emptied in place), where the marker
> would be the one row to survive its own session. The test now forces that path **and asserts the
> file still exists**, so it cannot drift back to proving nothing. `tests/engine/test_cache.py`
> 22 → 27; cache-adjacent modules (launcher, upload_cache, vertical_integration, analysis_cache_lru,
> session_consistency) 67 passed.
>
> ## Scope note (accepted, not overlooked)
> Two concurrent processes sharing one `$SF_CACHE_DIR` read each other's marker as a dead run and
> clear. The cost is a re-parse, never a wrong number (Law 2); ADR-0334's port claim already makes
> two live servers abnormal; and it is the same trade ADR-0335's scope note takes for a
> predecessor's `finally`. **No caller changed** — `web/app.py` and `launcher.py` are untouched
> except for the SIGKILL row of the exit-census table, which now points at the marker.
>
> ## ⇢ NEXT — the approved plan (HANDOFF ⇢ NEXT is the queue)
> 1. **Phase 3 — UI (hybrid: keep Mission Ops, graft the Command Deck's best ideas).** THE HEAD OF
>    THE QUEUE. The four unconverted Act III pages — **re-measured this session off rendered HTML,
>    not grep**: `/sra` (13 panels), `/risks` (8), `/brief` (8), `/briefing` (1), all with **zero**
>    `panel-head` / `sf-tools` / `sf-take` / `prov-chip` / panelkit. Then `DOM_PENDING`'s 7 modules,
>    then the DoD ledgers (the DD-line ledger must EXCLUDE non-time-axis charts: `histogram.js`,
>    `scatter.js`, `sra_jcl.js`'s cost axis). Follow `docs/DESIGN-SYSTEM.md`; verify in all four
>    themes; one page shell per PR; never touch `engine/` for a UI change.
>    **Measured and worth keeping:** `/driving-path`'s zeros are its EMPTY STATE (no target UID
>    entered), not an unconverted page — `/path` is the populated variant and is converted.
> 2. **Phase 4 engine** (`import_notes` propagation · the 3 falsy-zero rows · CC-01's rendering
>    half — "74 sites" is an approximate grep, RE-DERIVE it · SRA-LEGACY · V3) · **Phase 5**
>    monolith split 2–3 (`app.py` ~20.9k lines) · **Phase 6** docs/operator queue. OR-04 stays with
>    the operator.
>
> ## Still carried (unchanged identifiers, nothing lost)
> **CC-01** rendering half, ~74 call sites (an approximate grep — RE-DERIVE) · **CC-05**
> oracle-blocked, do not start · **V3** elapsed literals · the **legacy `/sra` cross-basis defect**
> · **EVM2-2D** · **H6-RESID** · **CACHE-48** (the in-memory `_ANALYSIS_CACHE_MAX`, ADR-0292 — the
> DISK cache is ADR-0335/0336, untouched by it) · **SPLIT-23** · **A0293-UI** · Project5's SSI
> export contradicts ADR-0307 (ADR-0307 stands) · `resume` is MSPDI-only · Phase 7 forward-pass
> packing · ADR-0322 residuals · importer warnings belong on the page via `Schedule.import_notes` ·
> ADR-0320/0325/0326 notes · **the /analysis focus→tip family is a measured intermittent** —
> adjudicated, do NOT chase · ADR-0332 scope note (within-session `sf-story-visited`) · ADR-0333
> scope note (`sysmon.js`'s interval still ticks while hidden; its `poll()` early-returns) ·
> ADR-0335 scope note (a predecessor's `finally` runs AFTER the port is released, so it can delete
> rows a successor just cached — correctness-safe, noted not engineered).
>
> ## Hypotheses KILLED — do not re-chase
> Everything in `audit/SRA-PARITY-20260729.md` §7 and the archived lists, **plus:** the caption/halo
> set; "listing the fields to reset is maintainable"; a blanket `sf-` localStorage sweep;
> "`tooltips.js` is one of the observer defects" (it is the EXEMPLAR); "querySelectorAll CALL COUNT
> measures observer cost" (measure NODES RETURNED); "a shared observer helper module is the clean
> fix" (ADR-0316 load-order); "`sysmon.js` is an unfixed idle pump" (the cost was the SERVER loop);
> "two servers bound 8321 simultaneously" (MEASURED false) · "the surviving server is itself the
> bug" (false: `idle_grace=600` is by design) · "a bind-probe answers 'is the port taken?'" (false
> on Windows — connect-probe) · "a hardened opener contains an empty ProxyHandler" (false — assert
> ABSENCE) · "`secure_delete=ON` is the obvious Law-1 cache hardening" (MEASURED false: 26 s on the
> quit path, blows ADR-0334's 20 s handover) · "a bare DELETE leaves plaintext so a residue test is
> a real gate" (false on Debian — `SECURE_DELETE` is compiled ON; assert RECLAIMED SIZE) ·
> "`wipe_gen` stops a late write re-populating the cache" (only `/session/wipe` bumps it) ·
> "`atexit`/`finally` cover a graceful stop" (false for SIGTERM — only the ASGI lifespan does) ·
> **NEW — "a pid identifies the run that holds the cache"** (false: reused, and `os.kill(pid, 0)`
> TERMINATES on Windows) · **NEW — "asserting a clean quit leaves no claim is a real gate"** (false
> on the unlink path, which destroys the marker with the file — force the Windows FALLBACK).
>
> ## Harness notes — the traps, one line each
> Run dev tools as `python -m <tool>`. **`pip install -e ".[dev]"` after EVERY container restart**
> (plus `playwright`, `ruff==0.16.1`, `build`). `pytest --timeout=N` is NOT installed. **Read the
> tool's own summary line** (`| tail` masks the real exit code). **`node --check a.js b.js` checks
> only the FIRST file — loop per file.** **NEVER `git checkout <file>` to undo a temporary test
> mutation — `cp` from a scratchpad copy instead.** **When reverting to prove able-to-fail, revert
> the CALLER not the API — and check the revert actually removed the behaviour.** **A `-k` filter
> can silently DESELECT the very test the revert targets — run the whole module** (hit this
> session: R1 looked like a 1-test failure until the file was run whole). **A hash-for-hash `sed`
> does NOT update abbreviated `bc18307…` digests quoted in prose — grep the prefix too.** `pkill -f`
> with the pattern in the killer's own command line kills the killer. CI can take ~11 min to
> register check runs. `TestClient` follows 303 and CONSUMES one-shot banners; **plain
> `TestClient(app)` does NOT run the lifespan — only `with TestClient(app)` does.** Parity marker
> ≈2m38s. Headless Chromium hides scrollbars. `caplog` needs `logger="schedule_forensics.<module>"`.
> **Playwright `bounding_box` / `page.screenshot(clip=…)` are VIEWPORT-relative.** **localStorage is
> per-ORIGIN.** Bundled chromium: `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`. Containers
> RESTART mid-run: statics FOREGROUND first, reinstall pip after resume. After a squash-merge:
> `git fetch --prune origin && git remote set-head origin -a && git checkout -B <branch>
> origin/main` — **NEVER amend the merged commits.** **Version-bump sequencing:** bump BEFORE the
> suite. Never sleep in a sync-Playwright route handler. Never `from tests.web...` in a test.
> **A parse-time-rendering JS module + a later chartframe.js = first-paint crash** (ADR-0316).
> **A stray `*/` makes CSS error-recovery swallow the NEXT rule silently.** **`cd` in a Bash call
> persists across calls — use absolute paths.**
>
> **Standing rule:** do not put a test result in prose unless the number appeared in output you
> read that turn. **A launched run is not a result, and a piped exit code is not the command's.**

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
