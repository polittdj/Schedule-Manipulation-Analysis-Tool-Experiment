# Handoff — 2026-08-01b (PR-9a: one caption convention per medium — B1 shipped; ADR-0326; v1.0.142)

> ## STATUS (current) — **PR-9a BUILT AND GATED on this tree (decision B1, split out of PR-9
> per the plan's "may split"; the rank-12 toolbar/read-me sweep is now PR-9b): DOM visuals
> caption natively in `.ch-at`'s new DOM sibling voice (`.ch-atd` — same token/case, `color`
> for `fill`). Mechanism 1: `workbench.js` builds a native `<table><caption>` on BOTH its
> tables (ribbon "Selected metrics × schedule version"; drill "Activities behind {metric} —
> one row per activity"). Mechanism 2: `gantt.js`'s shared `buildTierScale` renders ONE
> caption-slot row above the tiers whenever the served page carries `data-ts-caption`
> (`app.py::_TS_CAPTION_MARK`) — four one-line server opt-ins label all four Gantt-family
> consumers (/path · /evolution · /driving-path · /sra's SSI grid, all "Schedule dates")
> with ZERO consumer-module edits; /mission's tile and /analysis stay deliberately
> unmarked. The ledger gained the B1 executable detectors: `DOM_TABLE_CAPTIONED` ·
> `TIMESCALE_CAPTIONED` · `DOM_PENDING` (7 left) partition `NO_SVG_AXES` with `gantt.js`
> named as the slot primitive; `DOM_PENDING` reaching empty closes ADR-0298's deferral.
> ADR-0311's recorded `/workbench` blocker is CLEARED (tables are ⤓-only per DESIGN-SYSTEM
> §3:78, already shipped — its remaining owed work is read-me + ▦/⛶ in PR-9b).
> `gantt.js`'s PAGE_SCRIPTS freeze re-baselined DELIBERATELY (`2a4ccb61… → 9fa3a692…`,
> named in the ADR; a MutationObserver alternative was rejected as a timing-races class).
> DESIGN-SYSTEM §4 states the per-medium rule. Version 1.0.142, highest ADR ADR-0326,
> wheel + nine installers regenerated. Earlier today: PR-8 (#498, ADR-0325, v1.0.141)
> MERGED as `469cef0` by the operator; OR-05 verified closed end-to-end (the re-uploaded
> Jacked-2 carries Task 11's deadline; −5 d live).**
>
> ## Verification (all read from runs this session)
> `test_dom_captions.py` (new): server pins + REAL-chromium proof — the slot renders on all
> four opted-in pages (token 11px, uppercase, its box ENDS above the first tier band),
> workbench's ribbon caption renders in the same voice, and /analysis renders NO slot
> (leak guard). **Proved able to fail, watched:** a dropped marker failed the server pin AND
> the ledger count; the pre-slot gantt.js failed the ledger detector; the slot assertion
> itself failed three real ways during development (/path and /driving-path draw NO
> timescale without a target/trace — the fixture sets target 143 and traces 142 → 143;
> 26 → 143 is critical-but-not-driving and embeds nothing). Neighbor sweep (timescale,
> gantt×6, workbench, driving, path, sra, evolution, colresize, accessibility):
> **403 passed**. Caption suites post-format: **59 passed**. Statics: ruff check clean ·
> format clean (828 files — the formatter caught ONE reflow in app.py, the known
> read-the-summary-line trap) · mypy --strict "no issues in 117 source files" · bandit
> exit 0 · node --check clean (gantt/workbench/timescale). Installer lockstep **52 passed**
> after wheel 1.0.142 + nine installers. Full-suite result: see SESSION-LOG (recorded after
> the run completed — a launched run is not a result).
>
> ## ⇢ NEXT
> 1. **Merge the draft PR for this round when CI is green** (branch
>    `claude/polaris-engine-correctness-resume-e52fpp`), then:
> 2. **PR-9b — the rank-12 toolbar/read-me sweep** (the six Library/Setup pages;
>    `docs/STATE/PLAN-20260730.md` PR-9 row's first half): per page one `panelkit.js`
>    include + `_panel_head`/`_shell_tools` (⤓ only where a real export exists — dead ⤓ is
>    a defect class; tables ⤓-only per §3:78; ▦ needs a `.sf-drawer`) + read-me
>    `<p class=muted>` after `<p class=sf-take>` (canonical app.py:8559-8566 area — re-grep,
>    app.py moved). /margin unblocked by ADR-0325; /workbench unblocked by ADR-0326.
> 3. Then **PR-10 OR-03 launch motion + synthesized hum** (plan row 10, decisions recorded).
> 4. **OR-04 operator park artifacts stay open** (`audit/VERIFICATION-REPORT-ollama-lifecycle.md`
>    §8): #1 `where ollama` · #3 keep_alive probe · #5 runner PPID · #4 model-identity
>    manifest — plus #490's four-scenario smoke on the deployed build.
> 5. Behind the queue: SVG batch 3c (sra/sra_jcl/sra_ssi/volatility; tornados recorded
>    not-axis-charts per A1) · the 7-module `DOM_PENDING` ledger · Phase 3 (CC-01 rendering
>    half, 74 sites) · Phase 4 (P1–P6) · rank 13/14.
>
> ## Still carried (unchanged identifiers, nothing lost)
> **CC-01** (H2a) rendering half open, 74 call sites (eDays slack renders 7.88 d where MSP
> shows 2.63 edays; metric surfaces deliberately KEEP /480) · **CC-05** (H5) negative sub-day
> slack floor, oracle-gated · **V3** (H4) elapsed literals, `engine/msp_filters.py` · the
> **legacy `/sra` cross-basis defect** · **Project5's SSI export contradicts ADR-0307's
> Best-Case rule** (ADR-0307 stands) · `resume` is MSPDI-only · Phase 7: the forward pass
> packs completed work from `project_start` · ADR-0322 residuals (cross-calendar lag ·
> resume-floor MFO corner · lossy int LS/LF for off-calendar tasks) · importer warnings
> belong on the page via `Schedule.import_notes` · ADR-0320 residuals (Focus form drops
> `cf_a`/`cf_b`; trace-options `tier=off`) · ADR-0325 note: the erosion "zero margin"
> annotation is data-dependent (data yields, never the caption) · ADR-0326 notes: /mission's
> path-evolution tile deliberately unmarked; a marked page's caption applies to every
> tier-scale on it by design (same schedule-date axis).
>
> ## SRA parity — CLOSED, and the traps that stay shut
> ADR-0309: det percentile **40.70 % → 6.65 %** (SSI **5.75 %**), σ **125.5 → 65.5** cal d
> (SSI **64.744**), mean **+26 → +109** (SSI **+111.45**), P10/P50/P80/P90 within **7/1/0/3**
> days, five calibration seeds passing.
> - **The anchor is CONDITIONAL on stored data — never a blanket data-date floor** (EVM1
>   UID 18 has `resume == stop`, must not move).
> - **A floor from the STORED remaining destroys the upside variance** — follow
>   `duration_overrides`; do not "simplify" it back.
> - **Do NOT chase SSI's Mean/StdDev cells (47322 / 107.8198)** — pinned shut.
> - The SSI driving-slack goldens are **stored-date-insulated** from base-CPM changes — any
>   diff there is an implementation bug, never a re-baseline.
>
> ## Hypotheses KILLED — do not re-chase
> Everything in `audit/SRA-PARITY-20260729.md` §7 and the archived lists (ADR-0307 revert ·
> unconditional floor · ADR-0311→0325 items), **plus this round:** "26 → 143 can seed a
> driving-path trace" (critical-together ≠ driving; the server embeds nothing — use
> 142 → 143); "/path and /driving-path chart without a target/trace" (they render picker
> notes and NO timescale — a slot assertion there is vacuous); "the timescale slot can ride
> a MutationObserver instead of the frozen builder" (rejected: rebuild races on /evolution's
> frames and the dialog's repaints for zero gain); and "an overlay caption can sit in the
> tier header" (every band row is occupied — the slot is its OWN row by construction).
>
> ## Harness notes — the traps, one line each
> Run dev tools as `python -m <tool>` (a stale `/root/.local/bin/ruff` shadows pip's).
> **`pip install -e ".[dev]"` before the suite** (bare `PYTHONPATH=src` fails ~200 web tests).
> `pytest --timeout=N` is NOT installed — it exits 0 having run nothing. `cmd | tail; echo $?`
> reports `tail`'s status — **read the tool's own summary line** (bit AGAIN this session:
> "1 file would be reformatted" behind a clean-looking pipe). **`pkill -f` with a pattern in
> the killer's own command line kills the killer** (kill by PID). CI can take ~11 min to
> register check runs. `TestClient` follows 303 and CONSUMES one-shot banners
> (`follow_redirects=False`). Parity marker ≈2m38s (ADR-0322 perf addendum). Headless
> Chromium hides scrollbars. A remote-session resume can silently revert working-tree
> files — re-diff after every resume. `caplog` needs `logger="schedule_forensics.<module>"`.
> Playwright `bounding_box` is viewport-relative. **localStorage is per-ORIGIN** (second
> served app instance: write theme/scale AFTER landing on its origin). Containers RESTART
> mid-run: statics FOREGROUND first, long pytest re-runnable, reinstall pip after every
> resume. After a squash-merge: `git fetch --prune origin && git remote set-head origin -a
> && git checkout -B <branch> origin/main`.
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
