# Handoff — 2026-08-02 (Phase 1b remainder: the disk cache empties itself on every quit; ADR-0335; v1.0.151)

> ## STATUS (current) — **Phase 1b is COMPLETE and MERGED as `e0fdf85` (#513), ADR-0335.** The
> operator answered the cache question: **CLEAR IT ON EVERY QUIT.** `main` is at **v1.0.151** and
> its committed installers embed the 1.0.151 wheel (the lockstep gate passed on the final tree).
> **All six CI checks green before merge — including `windows`** (the job that actually exercises
> the new `chmod` hardening and the unlink fallback) and both Python 3.11 and 3.13. No review
> comments were raised. Working tree clean, branch restarted from `origin/main` with `--prune`,
> **no check-ins armed** (the one-hour PR check-in was deleted on merge). Session opened by
> confirming #512 was already merged (`4691276`).
>
> The on-disk SQLite cache holds **parsed schedule content + derived metrics** and was cleared in
> exactly ONE place — `/session/wipe`. Quitting left everything parsed sitting in
> `~/.cache/schedule-forensics/cache.sqlite3` indefinitely. It now empties itself on the way out at
> four layers, it **seals** before it clears, and `prune()` bounds what a hard kill leaves.
>
> ## Three things were MEASURED, and two of them changed the design
> 1. **`PRAGMA secure_delete=ON` was implemented, measured, and REMOVED.** It zeroes every deleted
>    byte in place at ~12.5 ms/MB: **26.08 s to clear a 1 GiB cache**, which lands on the quit path
>    and **exceeds ADR-0334's 20 s handover** — a relaunch would have hit `PortUnavailable` and
>    refused to start, regressing what last session paid to fix. `clear()` now **unlinks the
>    database file**: `26.08 s → 0.12 s`, and strictly more complete (the whole file, not its
>    pages). DELETE+VACUUM is kept only as the Windows fallback. **A slow erase that gets
>    interrupted leaves more behind than a fast one that finishes.**
> 2. **An in-flight import re-populated the cache AFTER the quit cleared it — reproduced
>    end-to-end** against a real server (181 KB of `model_json` landing in a cache that had just
>    reported itself clear). uvicorn serves until requests drain. **ADR-0263's `wipe_gen` does NOT
>    cover shutdown — only `/session/wipe` bumps it.** Fixed with `ScheduleCache.seal()`, called
>    before every clear; it covers both write sites and any future one. Reads stay open.
> 3. **SIGTERM runs NO exit hook at all** (measured: exit `-15`, `finally` and `atexit` both
>    silent). uvicorn handles SIGTERM gracefully but `capture_signals` **re-raises the captured
>    signal**, killing the process before `serve()` returns; SIGINT survives only because `serve()`
>    already suppresses `KeyboardInterrupt`. So an **ASGI lifespan hook** was added — the ONLY hook
>    that covers a macOS/Linux logout or system shutdown. Starlette 1.3.1 removed `on_event`, so
>    `FastAPI(lifespan=…)` is the only route.
>
> ## Coverage, measured end-to-end per signal (cached rows before → after)
> Quit / `POST /api/shutdown` / watchdog / **SIGINT** ⇒ cleared (all four layers) · **SIGTERM** ⇒
> cleared (**lifespan only**) · **SIGKILL** ⇒ survives, by design — that is what `prune()` is for.
>
> ## Verification (all read from runs this session)
> Statics: ruff clean · format clean (452) · mypy --strict clean (117) · **bandit EXIT=0** ·
> `node --check` per file, 60/60. **Twenty-three new tests** (cache +16, upload_cache +3,
> launcher +4). **NINETEEN revert experiments, each reverting the CALLER and keeping the API**,
> proved every gate can fail — **including FOUR that initially could NOT**, every one found only
> because the revert was actually RUN: (a) the "no plaintext left" assertion is **vacuous on a
> `SECURE_DELETE` build** (Debian compiles it ON) — two audit lenses reached OPPOSITE conclusions on
> residue for exactly this reason; it now leads with **reclaimed file size** · (b) the byte-cap test
> used a 1.15 bytes/char payload and rounding landed the BUGGY code on the same answer (now 3
> bytes/char, **and it asserts the fixture's own ratio**) · (c) the "cleared even when unopenable"
> test smashed the WHOLE file, destroying the payload in its own fixture (now only the 16-byte
> header) · (d) the migration test only exercised the success path, where verifying and not
> verifying agree.
>
> **Full suite on the FINAL tree: 3299 passed, 2 skipped, 0 failed in 20m12s** — test count up by
> exactly 23 (cache +16, upload_cache +3, launcher +4) from the 3276 baseline. An earlier run on an
> intermediate tree showed two failures, both resolved and neither a defect: the installer
> **wheel-lockstep gate doing its job** (source was edited after the installers were built —
> regenerated), and `test_launch_audio_chromium::test_mute_and_volume_persist…`, which passed
> **10/10 in isolation** and clean in the final run; that run took 26m46s against a ~17–20m
> baseline because 1 GiB SQLite probes were running concurrently. **Structurally it cannot be
> ours** — it asserts browser localStorage, and the only contact point is the lifespan hook, which
> yields immediately and clears only after every assertion. Not a newly-adopted intermittent; do
> not chase without a fresh failure.
>
> ## Four correctness fixes in THIS change's own new code, all forced by the audit
> The `ALTER` migration **verified** instead of suppressing by exception type (a lost-to-a-lock ALTER
> looked identical to a harmless duplicate-column race, leaving the old schema behind while
> reporting success — a cache silently a permanent miss) · `prune()` **returned rows that had been
> rolled back** (the body is one transaction; on failure the honest count is 0) · `clear()`
> **short-circuited on `_ready`**, reporting "nothing left behind" for a corrupt database still full
> of the last session's schedules · **the age window had no upper bound**, so a backwards clock jump
> made a future-stamped row IMMORTAL, not merely late (my own comment claimed otherwise — it was
> wrong). Also `busy_timeout` now precedes the `journal_mode=WAL` switch, and the byte trim targets
> 90% of the cap so the page-bytes gate stops re-firing.
>
> ## Three more Law-1 gaps closed (found by the audit, verified by me, all defaults behaving normally)
> `VACUUM` wrote its rebuild to a **plaintext transient in `/var/tmp`** — outside the directory the
> module documents as its boundary (`temp_store_directory` now pins it inside) · the WAL could hold
> the rebuild while pre-prune pages stayed legible in the main file (`wal_checkpoint(TRUNCATE)`) ·
> the cache was created **world-readable `0644` in a `0755` dir** (now `0600`/`0700`, best-effort).
> **And a real bug in my own cap:** SQLite's `length()` on TEXT counts **characters**, but the cap
> is compared against real page bytes — so on non-ASCII activity names (EN/ES/FR/DE/PT ship with
> the tool) the belt allowed more on disk than it promised. Now `length(CAST(… AS BLOB))`.
>
> ## ⇢ NEXT — the approved plan (HANDOFF ⇢ NEXT is the queue; the plan file is GONE from disk)
> 1. **Phase 3 — UI (hybrid: keep Mission Ops, graft the Command Deck's best ideas).** The four
>    unconverted Act III pages (`/sra`, `/risks`, `/briefing`, `/brief` — zero
>    panelkit/`_panel_head`/`_shell_tools`/`sf-take`), then `DOM_PENDING`'s 7, then the DoD ledgers.
>    The DD-line ledger must EXCLUDE non-time-axis charts (`histogram.js`, `scatter.js`,
>    `sra_jcl.js` cost axis). Follow `docs/DESIGN-SYSTEM.md`; verify in all four themes.
> 2. **Phase 4 engine** (`import_notes` propagation · the 3 falsy-zero rows · CC-01's rendering
>    half — "74 sites" is an approximate grep, RE-DERIVE it · SRA-LEGACY · V3) · **Phase 5**
>    monolith split 2–3 (`app.py` is 20.9k lines) · **Phase 6** docs/operator queue. OR-04 stays
>    with the operator.
> 3. **NEW, and it is the OPERATOR's call — do not take it unilaterally.** Because a clean quit now
>    clears everything, residue from a hard kill actually survives **until the end of the next clean
>    session**, not 24 h: the age cap only ever bites at a launch, so a kill-then-relaunch-in-five-
>    minutes keeps rows the size cap alone would not evict. Closing that deterministically means
>    deleting every row not written by the CURRENT launch — which is **clear-at-launch by another
>    name**, the one thing the approved wording forbids. Flagged, not taken.
>
> ## Still carried (unchanged identifiers, nothing lost)
> **CC-01** rendering half, ~74 call sites (an approximate grep — RE-DERIVE) · **CC-05**
> oracle-blocked, do not start · **V3** elapsed literals · the **legacy `/sra` cross-basis defect**
> · **EVM2-2D** · **H6-RESID** · **CACHE-48** (the in-memory `_ANALYSIS_CACHE_MAX`, ADR-0292 —
> untouched by ADR-0335, which is the DISK cache) · **SPLIT-23** · **A0293-UI** · Project5's SSI
> export contradicts ADR-0307 (ADR-0307 stands) · `resume` is MSPDI-only · Phase 7 forward-pass
> packing · ADR-0322 residuals · importer warnings belong on the page via `Schedule.import_notes` ·
> ADR-0320/0325/0326 notes · **the /analysis focus→tip family is a measured intermittent** —
> adjudicated, do NOT chase · ADR-0332 scope note (within-session `sf-story-visited`) · ADR-0333
> scope note (`sysmon.js`'s interval still ticks while hidden; its `poll()` early-returns) ·
> **ADR-0335 scope note:** a predecessor's `finally` runs AFTER the port is released, so it can
> delete rows a successor just cached — correctness-safe (a miss recomputes), noted not engineered.
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
> ABSENCE) · **NEW — "`secure_delete=ON` is the obvious Law-1 hardening for the cache"** (MEASURED
> false: 26 s on the quit path, blows the handover, and redundant once `clear()` unlinks) ·
> **"a DELETE leaves plaintext, so the residue test is a real gate"** (false ON THIS BOX — Debian
> compiles `SECURE_DELETE` ON; assert RECLAIMED SIZE, which is portable) · **"`wipe_gen` already
> stops a late write re-populating the cache"** (false: only `/session/wipe` bumps it) ·
> **"`atexit`/`finally` cover a graceful stop"** (false for SIGTERM — only the ASGI lifespan does).
>
> ## Harness notes — the traps, one line each
> Run dev tools as `python -m <tool>`. **`pip install -e ".[dev]"` after EVERY container restart**
> (plus `playwright`, `ruff==0.16.1`, `build`). `pytest --timeout=N` is NOT installed. **Read the
> tool's own summary line** (`| tail` masks the real exit code). **`node --check a.js b.js` checks
> only the FIRST file — loop per file.** **NEVER `git checkout <file>` to undo a temporary test
> mutation — it discards UNSTAGED real work in that file; `cp` from a scratchpad copy instead.**
> **When reverting to prove able-to-fail, revert the CALLER not the API — and check the revert
> actually removed the behaviour** (a first attempt this session left the VACUUM in place, so the
> test passed and looked like a vacuous gate). **A hash-for-hash `sed` does NOT update abbreviated
> `bc18307…` digests quoted in prose — grep the prefix too.** `pkill -f` with the pattern in the
> killer's own command line kills the killer. CI can take ~11 min to register check runs.
> `TestClient` follows 303 and CONSUMES one-shot banners; **plain `TestClient(app)` does NOT run
> the lifespan — only `with TestClient(app)` does.** Parity marker ≈2m38s. Headless Chromium hides
> scrollbars. `caplog` needs `logger="schedule_forensics.<module>"`. **Playwright `bounding_box` /
> `page.screenshot(clip=…)` are VIEWPORT-relative.** **localStorage is per-ORIGIN.** Bundled
> chromium: `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`. Containers RESTART mid-run:
> statics FOREGROUND first, reinstall pip after resume. After a squash-merge:
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
