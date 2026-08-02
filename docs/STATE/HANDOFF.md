# Handoff — 2026-08-02d (Phase 3 UI: /risks joins the panel contract; ADR-0338; v1.0.154)

> ## STATUS (current) — **THREE PRs this session, two already merged.** #515 (ADR-0336, the
> dirty-flag cache clear the operator chose) merged as **`1bcf01a`**; #516 (ADR-0337, chapter 12 —
> `/briefing` + `/brief`) merged as **`400f51d`**, both with all six CI checks green and no review
> comments. This branch carries **ADR-0338 — `/risks` joins the panel contract**, the second Phase-3
> UI conversion. Session opened by confirming #514 was already merged (`e1c81cf`).
>
> ## `/sra` is the LAST unconverted Act III route — and it is bigger than the estimate said
> Measured this session off rendered HTML: **`/sra` renders 15 panels** (not the 13 the earlier
> estimate assumed) across ≈550 lines in four helpers (`_sra_body` 146 · `_sra_report_blocks` 295 ·
> `_sra_explainers` 66 · `_sra_overrides_table` 42). Chapter 11 as a whole would have been a
> ~755-line diff, so `/risks` was taken alone and **`/sra` gets its own PR — it is the whole of the
> next UI unit.**
>
> ## `/risks`, before → after (panel count UNCHANGED at 8)
> heads/tools/⛶/takes/chips **0,0,0,0,0 → 7,7,7,7,7**, panelkit 0 → 1, and it gained the
> **takeaway h1 it never had** (`page-takeaway` 0 → 1). The 8th panel is the global Ask panel and
> stays bare, as on chapter 12.
>
> ## Three decisions worth carrying
> 1. **The chip is the PAIR chip.** `/risks` computes `recommend(current, prior, …)` — most findings
>    describe the current version, but the CHANGE findings come from the pair, so a single-file chip
>    would under-describe exactly the findings that motivated loading a second version. It uses the
>    **real version indices** (`len(solv)-1 → len(solv)`), not `_series_prov_chip`'s positional
>    `1→2`, because the pair is the last two solvable versions rather than the first and last.
> 2. **The empty returns are untouched.** `_risk_matrix([]) == ""` and `_risk_ranking([]) == ""` are
>    pinned by `test_risks.py`; a head strip over no matrix would be a box announcing nothing.
>    `_risks_section` DOES always render, so its take is worded to hold at **zero** — a take written
>    only for the populated case leaves a clean schedule wearing a headline that reads as a defect.
> 3. **The Act III census module was renamed** `test_ch12_*` → `test_act3_*` (both the contract and
>    the chromium module). A file called "ch12" asserting on a chapter-11 route is a name that lies;
>    it now grows a row per conversion PR, with `/sra` the last route outside it.
>
> ## The two gaps the reverts found — neither visible by reading the tests
> - **W4: dropping `/risks`'s takeaway h1 failed NOTHING.** The takeaway test read `/brief` only, so
>   a per-route rule had no per-route assertion. **A per-route DoD rule needs a per-route gate.**
> - **Writing that gate then exposed a real Law-2 defect in my own headline:** it quoted
>   `len(findings)`, a SUM of three separately-rendered counts that appeared nowhere else on the
>   page — which `_utility_takeaway`'s own contract forbids. Fixed in the RENDER (the lead take now
>   states the total), then pinned by W5.
>
> ## Verification (every number read from a run this session)
> **ADR-0336: 6 reverts** — R5 caught a VACUOUS gate (the clean-quit test passed against a build
> that never released anything, because `clear()` UNLINKS the file; the explicit `DELETE` only bites
> on the **Windows fallback**, which the test now forces). Full suite **3304 passed, 2 skipped**.
> **ADR-0337: 8 caller-reverts + 2 CSS reverts** (jarvis hiding the tool strip; apollo rendering the
> chip transparent) — the four-theme probe passed first try, which proves nothing on its own. Full
> suite **3316 passed, 2 skipped** (3304 + 12).
> **ADR-0338: 5 caller-reverts** — W1 the view stops passing the chip · W2 `/risks` loses panelkit ·
> W3 the panel export is dropped · W4 the takeaway h1 is dropped · W5 the take stops stating the
> total. Contract module 8 → 9 tests, chromium 4 → 6; risks-adjacent modules **74 passed**.
>
> ## ⇢ NEXT — the queue
> 1. **Phase 3: `/sra` — 15 panels, ≈550 lines, its own PR.** The last unconverted Act III route.
>    Then `DOM_PENDING`'s 7 modules, then the DoD ledgers — **the DD-line ledger must EXCLUDE
>    non-time-axis charts** (`histogram.js`, `scatter.js`, `sra_jcl.js`'s cost axis). Follow
>    `docs/DESIGN-SYSTEM.md`; verify in all four themes; never touch `engine/` for a UI change.
> 2. **Phase 4 engine** (`import_notes` propagation · the 3 falsy-zero rows · CC-01's rendering
>    half — "74 sites" is an approximate grep, RE-DERIVE it · SRA-LEGACY · V3) · **Phase 5**
>    monolith split 2–3 (`app.py` ~21k lines) · **Phase 6** docs/operator queue. OR-04 stays with
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
> adjudicated, do NOT chase · ADR-0332/0333 scope notes · ADR-0335 scope note (a predecessor's
> `finally` runs AFTER the port is released) · **ADR-0336 scope note:** two concurrent processes
> sharing one `$SF_CACHE_DIR` read each other's marker as a dead run and clear — correctness-safe
> (a re-parse), accepted not engineered · **ADR-0337/0338 scope note:** the Ask panel and the shared
> `_status_stack` bars stay bare, pinned by a test.
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
> quit path) · "a bare DELETE leaves plaintext so a residue test is a real gate" (false on Debian —
> assert RECLAIMED SIZE) · "`wipe_gen` stops a late write re-populating the cache" (only
> `/session/wipe` bumps it) · "`atexit`/`finally` cover a graceful stop" (false for SIGTERM) ·
> "a pid identifies the run that holds the cache" (false: reused, and `os.kill(pid, 0)` TERMINATES
> on Windows) · "asserting a clean quit leaves no claim is a real gate" (false on the unlink path —
> force the Windows FALLBACK) · "`/driving-path` is a fifth unconverted page" (false: that is its
> EMPTY STATE; `/path` is the populated, already-converted variant) · "counting `<div class=panel`
> finds every panel" (false: it misses the QUOTED `class="panel …"` form) · **NEW — "a DoD rule
> tested on one route is tested"** (false: dropping `/risks`'s takeaway h1 failed nothing until it
> got its OWN gate) · **NEW — "`/sra` is 13 panels"** (measured: **15**).
>
> ## Harness notes — the traps, one line each
> Run dev tools as `python -m <tool>`. **`pip install -e ".[dev]"` after EVERY container restart**
> (plus `playwright`, `ruff==0.16.1`, `build`). `pytest --timeout=N` is NOT installed. **Read the
> tool's own summary line** (`| tail` masks the real exit code). **`node --check a.js b.js` checks
> only the FIRST file — loop per file.** **NEVER `git checkout <file>` to undo a temporary
> mutation — `cp` from a scratchpad copy** (used repeatedly this session, for app.py and app.css).
> **When reverting to prove able-to-fail, revert the CALLER — and check the revert actually removed
> the behaviour.** **A `-k` filter can silently DESELECT the very test the revert targets — run the
> whole module.** **A theme/computed-style assertion needs its own CSS revert to prove it can
> fail.** **pytest stdout to a FILE is block-buffered — the dot count lags badly; not a stall.**
> **The /risks page title is `Risks & Opportunities` in source (NOT `&amp;`) — an Edit that assumes
> the entity will not match.** **A hash-for-hash `sed` does NOT update abbreviated digests quoted in
> prose — grep the prefix too.** `pkill -f` with the pattern in the killer's own command line kills
> the killer. CI can take ~11 min to register check runs; `test (3.11)`/`(3.13)` run ~30 min.
> `TestClient` follows 303 and CONSUMES one-shot banners; **plain `TestClient(app)` does NOT run the
> lifespan — only `with TestClient(app)` does.** Parity marker ≈2m38s. Headless Chromium hides
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
