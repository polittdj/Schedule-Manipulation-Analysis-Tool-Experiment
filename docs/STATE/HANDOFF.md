# Handoff — 2026-08-01k (Phase 2: observers read records, telemetry probes on demand; ADR-0333; v1.0.149)

> ## STATUS (current) — **Phase 2 BUILT AND GATED on this tree (ADR-0333).** Phase 1a MERGED as
> `8e1f319` (#509). **Phase 1b was NOT started: the operator's measurement has not arrived.**
> Checked `docs/STATE/OPERATOR-REQUESTS.md`, `audit/operator-artifacts/` (drop zone holds only its
> README + the Ollama collector), every untracked path, and the git log since 2026-07-30 — no
> netstat capture anywhere. Per the standing instruction, Phase 2 was done instead and **the
> launcher was not guessed at**.
>
> Phase 2 found and fixed **two measured defects**, and recorded that the idle-pump half was
> already correct so it is not re-chased: the client pumps are exactly `sysmon.js` (2 s) and
> `heartbeat.js` (3 s), the heartbeat is UNTOUCHED (pausing it loses the session), and
> `sysmon.js`'s `poll()` already early-returns while `document.hidden`.
>
> **(1) Three document-wide `MutationObserver`s re-scanned the whole page per inserted node.**
> `vizhints.js` re-ran a full-document heading sweep and re-tested every heading against a
> **114-entry** catalog (a heading matching nothing is never marked, so it is re-scanned forever);
> `gantt.js` ran three full-document attach passes; `chartframe.js` re-ran `applyZoom()` per
> mutation, forcing synchronous layout on every `.cf-zoom-box`. Two of them **re-arm themselves
> with their own writes** — `stickyScrollbar` appends its proxy bar to `<body>`, `attachColumnMovers`
> appends a grip `<span>` to every header cell — a 2× echo measured on `/curves` (20 inserts drove
> **80** `table.gantt-grid` sweeps, not 40). `tooltips.js` (ADR-0286) was ALREADY correct and is
> the exemplar, not a defect — the prior handoff's "tooltips.js:71-79" pointer names the model to
> copy. Fixed records-based + one flush per frame, plus `eachMatch(root, sel, fn)` in `gantt.js`
> which tests `root.matches(sel)` BEFORE walking it — the correctness half, since `querySelectorAll`
> returns only DESCENDANTS and the inserted node may BE the pane.
>
> **(2) `web/system.py::_slow_loop` was `while True` — launch-to-quit telemetry.** The first
> `/api/system` request started it and it then spawned two subprocesses (on Windows two `powershell`
> children) **every 5 s until the process exited**, whether or not anyone was looking; `sysmon.js`'s
> `document.hidden` skip is client-side and cannot reach a server loop. This is the operator's
> reported "two PowerShell probes every 5 s from launch to quit", now ROOT-CAUSED. Fixed:
> `snapshot()` stamps a demand clock + sets an Event; the loop parks on that Event after
> `_IDLE_AFTER` (30 s) with zero subprocesses, and wakes straight into a probe. **No value is
> fabricated** — an unavailable field stays `None` → "—" (Law 2). Version **1.0.149**, highest ADR
> **ADR-0333**.
>
> ## Verification (all read from runs this session)
> **The metric is nodes SCANNED, not calls made** — scoping a query does not reduce the call count
> (it can raise it slightly); it collapses what each call walks. Measured in the bundled chromium,
> `/analysis/Project5`, 30 insertions one per frame: heading sweep **1,275 → 84** nodes;
> `table.gantt-grid` **62 → 0**; gantt panes **31 → 0** (1,368 → 84, ~16×), each heading walked
> costing up to 114 substring compares on top. **No wall-clock is asserted anywhere** — the storm
> is rAF-bound and elapsed time is flat (887 ms both), so a timing gate would assert nothing and
> flake on CI.
> Eight new gates, **all proved able to fail by reverting the CALLER and keeping the API**, watched:
> reverting `vizhints.js`'s callback → *"observer ignores what was actually inserted"* and
> *1,211 walked, bound 162*; `gantt.js`'s → *62 gantt-grid nodes for 30 unrelated insertions*;
> `chartframe.js`'s → the coalesce contract; dropping `eachMatch`'s root test → the root contract;
> deleting the park block → ***"46 extra probes after the idle window"***; un-arming `snapshot()`
> → *"must release a parked probe thread"*. `tests/perf/` **17 passed**. The 10 tests pinning the
> three edited modules: **152 passed, 1 failed** — the byte-freeze pin on `gantt.js`, re-baselined
> DELIBERATELY (see below). Statics foreground: ruff "All checks passed!" · format clean (451) ·
> mypy --strict clean (117) · bandit EXIT=0 · `node --check` clean on all **60** JS files
> (per-file — `node --check a.js b.js` silently checks only the first). **Full suite on the FINAL
> tree: 3265 passed, 2 skipped, 0 failed in 18m53s** — test count up by exactly 9 (the 7 new perf
> contracts + the 2 browser gates); the carried /analysis focus→tip intermittent passed this run
> and stays adjudicated either way.
>
> **`gantt.js` digest re-baselined** in `tests/web/test_r11_panel_contract.py`
> (`9fa3a69…` → `d313413…`), following that file's own convention. The pin guards chart geometry;
> verified inapplicable — the diff is confined to the three attachers + the boot IIFE, `gantt.js`
> has **zero** `axisTitles` call sites (the census test asserts this independently and stayed
> green), and `buildTierScale`/`paintGrid`/`gridLines`/`timeTiers` are untouched.
>
> ## ⇢ NEXT — the approved plan (HANDOFF ⇢ NEXT is the queue; the plan file is GONE from disk)
> 1. **Phase 1b — the launcher. STILL BLOCKED ON THE ONE OPERATOR MEASUREMENT.** On the deployed
>    box: launch, close ONLY the browser, then `netstat -ano | findstr :8321` — **one PID or two?**
>    — then relaunch and re-check. One ⇒ the second launch died mute (uvicorn `sys.exit` into
>    `os.devnull` under `pythonw`) and the non-daemon browser timer — started BEFORE the bind —
>    opened onto the surviving old process and its old `SessionState` (which also defeats
>    ADR-0324's launch token). TWO ⇒ Windows `SO_REUSEADDR` let a second server bind the same port
>    (uvicorn never sets `SO_EXCLUSIVEADDRUSE`), routing indeterminate — a bind-error reporter
>    would fix nothing. Either way the fix is an explicit single-instance PROBE before serving,
>    then per "always start clean" `POST /api/shutdown` the old instance, wait for the port, start
>    fresh; if it will not release, **FAIL VISIBLY** rather than open a browser onto an unknown
>    session. **Do NOT "move the browser timer after `serve_fn`" — `serve_fn` blocks for process
>    life.** A Linux-only port test pins the WRONG platform. Also: clear the on-disk cache on clean
>    shutdown + atexit, **NEVER at launch**, plus a size and age cap. **If it still has not
>    arrived, say so and take Phase 3 — do not guess.**
> 2. **Phase 3 — UI (hybrid: keep Mission Ops, graft the Command Deck's best ideas).** The four
>    unconverted Act III pages (`/sra`, `/risks`, `/briefing`, `/brief` — zero
>    panelkit/`_panel_head`/`_shell_tools`/`sf-take`), then `DOM_PENDING`'s 7, then the DoD
>    ledgers. The DD-line ledger must EXCLUDE non-time-axis charts (`histogram.js`, `scatter.js`,
>    `sra_jcl.js` cost axis).
> 3. **Phase 4 engine** (`import_notes` propagation · the 3 falsy-zero rows · CC-01's rendering
>    half — "74 sites" is an approximate grep, RE-DERIVE it · SRA-LEGACY · V3) · **Phase 5**
>    monolith split 2–3 (`app.py` is 20.9k lines, 2.8k LARGER than ADR-0297 left it) · **Phase 6**
>    docs/operator queue. The OR-04 collection run stays with the operator.
>
> ## Still carried (unchanged identifiers, nothing lost)
> **CC-01** rendering half, ~74 call sites (an approximate grep — RE-DERIVE) · **CC-05**
> oracle-blocked, do not start · **V3** elapsed literals · the **legacy `/sra` cross-basis defect**
> · **EVM2-2D** · **H6-RESID** · **CACHE-48** · **SPLIT-23** · **A0293-UI** · Project5's SSI export
> contradicts ADR-0307 (ADR-0307 stands) · `resume` is MSPDI-only · Phase 7 forward-pass packing ·
> ADR-0322 residuals · importer warnings belong on the page via `Schedule.import_notes` ·
> ADR-0320/0325/0326 notes · **the /analysis focus→tip family is a measured intermittent** —
> adjudicated, do NOT chase · **ADR-0332 scope note:** a within-session `sf-story-visited` still
> records the current chapter's route (filename included) — deliberate, only cross-session
> persistence was the exposure · **ADR-0333 scope note:** `sysmon.js`'s 2 s `setInterval` still
> ticks while hidden (its `poll()` early-returns, so it costs a no-op callback) — deliberately not
> cleared; `translate.js` / `legend_toggle.js` were already records-based / lazily scoped.
>
> ## Hypotheses KILLED — do not re-chase
> Everything in `audit/SRA-PARITY-20260729.md` §7 and the archived lists, **plus:** "the caption can
> move out of the ink" (placement frozen — halo); "a blanket white halo" (two of three chart
> families are not on white); "ink-present ⇒ halo-required is a sufficient test" (true on 79 % of
> renders — measure pixels); "listing the fields to reset is maintainable" (it fell 27 behind —
> reset by reflection); "a blanket `sf-`/`sf.` localStorage sweep" (un-mutes the boot hum, resets
> theme); **NEW — "`tooltips.js` is one of the observer defects"** (it was already correct; it is
> the EXEMPLAR); **"querySelectorAll CALL COUNT measures observer cost"** (scoping holds calls flat
> or raises them — measure NODES RETURNED); **"a shared observer helper module is the clean fix"**
> (ADR-0316 load-order risk on the pages emitting `gantt.js`; keep each module self-contained);
> **"`sysmon.js` is an unfixed idle pump"** (it already skips while `document.hidden` — the cost
> was the SERVER loop).
>
> ## Harness notes — the traps, one line each
> Run dev tools as `python -m <tool>`. **`pip install -e ".[dev]"` after EVERY container restart**
> (plus `playwright`, `ruff==0.16.1`, `build`). `pytest --timeout=N` is NOT installed. **Read the
> tool's own summary line** (`| tail` masks the real exit code). **`node --check a.js b.js` checks
> only the FIRST file — loop per file.** `pkill -f` with the pattern in the killer's own command
> line kills the killer. CI can take ~11 min to register check runs. `TestClient` follows 303 and
> CONSUMES one-shot banners. Parity marker ≈2m38s. Headless Chromium hides scrollbars. `caplog`
> needs `logger="schedule_forensics.<module>"`. **Playwright `bounding_box` and
> `page.screenshot(clip=…)` are VIEWPORT-relative.** **localStorage is per-ORIGIN.** Bundled
> chromium is at `/opt/pw-browsers/chromium-1194/chrome-linux/chrome` — a bare `launch()` dies.
> Containers RESTART mid-run: statics FOREGROUND first, reinstall pip after resume. After a
> squash-merge: `git fetch --prune origin && git remote set-head origin -a && git checkout -B
> <branch> origin/main` — **NEVER amend the merged commits to satisfy the stop hook.**
> **Version-bump sequencing:** bump BEFORE the suite. Never sleep in a sync-Playwright route
> handler. Never `from tests.web...` in a test. **A parse-time-rendering JS module + a later
> chartframe.js = first-paint crash** (ADR-0316). **A stray `*/` makes CSS error-recovery swallow
> the NEXT rule silently.** **`cd` in a Bash call persists across calls — use absolute paths.**
> **When reverting to prove able-to-fail, revert the CALLER not the API** — reverting both turns a
> behavioural failure into an ImportError, which proves nothing.
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
