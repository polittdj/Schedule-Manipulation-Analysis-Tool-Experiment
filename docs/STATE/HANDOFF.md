# Handoff — 2026-08-02c (Phase 3 UI: chapter 12 joins the panel contract; ADR-0337; v1.0.153)

> ## STATUS (current) — **TWO merges this session.** #515 (ADR-0336, the dirty-flag cache clear the
> operator chose) merged as **`1bcf01a`**, all six checks green including `windows`, no review
> comments. This branch then carries **ADR-0337 — Phase 3's FIRST UI conversion: chapter 12
> (`/briefing` + `/brief`) joins the Mission Ops panel contract.** Session opened by confirming
> #514 was already merged (`e1c81cf`).
>
> ## Two measurements that changed what got built
> 1. **`/driving-path` is NOT an unconverted page.** It reads as all-zeros only because the probe
>    caught its EMPTY STATE (no target UID entered); `/path` is the populated variant and already
>    carries the contract. A source grep would have put it in the queue.
> 2. **A `<div class=panel[ >]` regex silently misses the QUOTED form** (`<div class="panel
>    brief-doc">`), so the first census called `/briefing` a 1-panel page when it renders **4**.
>    Every count below is the both-spellings total, measured on BOTH trees — the converted one and
>    the pristine tree at `1bcf01a`, restored from a scratchpad copy and put back (never
>    `git checkout`).
>
> ## Chapter 12, before → after (panel counts UNCHANGED — the conversion decorates, never mints)
> `/briefing` 4 panels: heads/tools/⛶/takes/chips **0,0,0,0,0 → 1,1,1,1,1**, panelkit 0 → 1 ·
> `/brief` 8 panels: **0,0,0,0,0 → 7,7,7,1,7**, panelkit 0 → 1, and it gained the **takeaway h1 it
> never had** (`page-takeaway` 0 → 1). A minted `.panel` would silently enrol in jarvis's broad
> `.panel` rules, so the census pins the count.
>
> ## Why chapter 12 and not `/sra` (sized before choosing)
> `/sra` alone is `_sra_body` 146 + `_sra_report_blocks` 295 + `_sra_explainers` 66 +
> `_sra_overrides_table` 42 ≈ **550 lines** — not one reviewable PR. Chapter 12 is ≈180 lines across
> two pages that are ONE chapter (same nav entry, `/brief` is `/briefing`'s sub-page). **Chapter 11
> (`/sra` + `/risks`, ≈755 lines) is next, as its own PR.**
>
> ## The one that would have rotted silently
> `ai_polish.js` does `node.innerHTML = d.html` over the WHOLE of `#briefingBody`, and that HTML
> comes from `/api/ai/briefing` re-rendering `_briefing_body`. So the provenance chip is a
> **parameter**, not something the function builds: a chip it could not build for itself would
> vanish the moment a local model was active — no error, no layout change, just a briefing wearing
> no provenance, in the one configuration the suite never exercises by default. Both call sites now
> pass `_series_prov_chip(schedules)` (the SERIES chip: both pages are built from every solvable
> version at once), and a test drives the endpoint with a stub backend to prove it. **The toolbar
> was never at risk — panelkit.js binds ONE delegated listener on `document`, so buttons arriving
> via innerHTML keep working. Checked, not assumed.**
>
> ## Verification (every number read from a run this session)
> **ADR-0336: SIX reverts** (R1 never launch-clears → 2 fail · R2 clears at EVERY launch → 2 · R3
> drops the identity comparison → 1 · R4 drops the `_claimed` reset → 1 · R5 `clear()` stops
> releasing → 2 · R6 writes never claim → 2). **R5 caught a VACUOUS gate** — the clean-quit test
> passed against a build that never released anything, because `clear()` UNLINKS the database file
> so the marker dies with it either way; the explicit `DELETE` only matters on the **Windows
> fallback** path, which the test now forces (and asserts `db.exists()` so it cannot drift back).
> **ADR-0337: EIGHT reverts, all of the CALLER** — V1 the AI path drops the chip · V2 `/brief`
> loses panelkit.js · V3 a heading skips `_panel_head` · V4 the panel export is removed · V5 the
> takeaway is dropped · V6 the conversion mints a panel · V7 the shared status bars grow a head ·
> V8 the wrap alters heading TEXT. **Plus TWO CSS reverts to prove the four-theme browser probe can
> fail at all** (jarvis hiding the tool strip; apollo rendering the chip transparent) — a theme
> assertion that cannot fail is worth nothing.
> ADR-0336 full suite: **3304 passed, 2 skipped, 0 failed in 27m14s** (3299 baseline + 5).
> Chapter-12 modules: contract 8, chromium 4, affected existing modules **91 passed**.
>
> ## Scope deliberately NOT widened (pinned by a test)
> The **Ask panel** is global chrome `_page` adds everywhere; the two `.panel.status-stack` bars on
> `/briefing` come from `_status_stack`, which several chapter headers share (`/sra` among them).
> Converting either here would be a cross-cutting change wearing a chapter-12 label, and would hand
> ⤓ EXCEL to panels whose data no workbook carries. ▦ DATA is refused on both routes: these panels
> ARE prose and tables, so the glyph would be inert.
>
> ## ⇢ NEXT — the queue
> 1. **Phase 3 continues: chapter 11 (`/sra` + `/risks`)**, its own PR. Then `DOM_PENDING`'s 7
>    modules, then the DoD ledgers — **the DD-line ledger must EXCLUDE non-time-axis charts**
>    (`histogram.js`, `scatter.js`, `sra_jcl.js`'s cost axis). Follow `docs/DESIGN-SYSTEM.md`;
>    verify in all four themes; never touch `engine/` for a UI change.
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
> adjudicated, do NOT chase · ADR-0332 scope note · ADR-0333 scope note (`sysmon.js`'s interval
> still ticks while hidden) · ADR-0335 scope note (a predecessor's `finally` runs AFTER the port is
> released) · **ADR-0336 scope note:** two concurrent processes sharing one `$SF_CACHE_DIR` read
> each other's marker as a dead run and clear — correctness-safe (a re-parse), accepted not
> engineered · **ADR-0337 scope note:** the Ask panel and the shared `_status_stack` bars stay bare.
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
> force the Windows FALLBACK) · **NEW — "`/driving-path` is a fifth unconverted page"** (false: that
> is its EMPTY STATE; `/path` is the populated, already-converted variant) · **NEW — "counting
> `<div class=panel` finds every panel"** (false: it misses the QUOTED `class="panel …"` form, which
> under-counted `/briefing` by three).
>
> ## Harness notes — the traps, one line each
> Run dev tools as `python -m <tool>`. **`pip install -e ".[dev]"` after EVERY container restart**
> (plus `playwright`, `ruff==0.16.1`, `build`). `pytest --timeout=N` is NOT installed. **Read the
> tool's own summary line** (`| tail` masks the real exit code). **`node --check a.js b.js` checks
> only the FIRST file — loop per file.** **NEVER `git checkout <file>` to undo a temporary
> mutation — `cp` from a scratchpad copy** (used twice this session, for app.py and app.css).
> **When reverting to prove able-to-fail, revert the CALLER — and check the revert actually removed
> the behaviour.** **A `-k` filter can silently DESELECT the very test the revert targets — run the
> whole module** (hit this session). **A theme/computed-style assertion needs its own CSS revert to
> prove it can fail.** **pytest stdout to a FILE is block-buffered — the dot count lags badly; do
> not read it as a stall.** **A hash-for-hash `sed` does NOT update abbreviated digests quoted in
> prose — grep the prefix too.** `pkill -f` with the pattern in the killer's own command line kills
> the killer. CI can take ~11 min to register check runs; `test (3.13)` ran ~30 min. `TestClient`
> follows 303 and CONSUMES one-shot banners; **plain `TestClient(app)` does NOT run the lifespan —
> only `with TestClient(app)` does.** Parity marker ≈2m38s. Headless Chromium hides scrollbars.
> `caplog` needs `logger="schedule_forensics.<module>"`. **Playwright `bounding_box` /
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
