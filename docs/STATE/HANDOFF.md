# Handoff — 2026-08-01c (PR-9b: the Library pages wear the panel toolbar; ADR-0327; v1.0.143)

> ## STATUS (current) — **PR-9b BUILT AND GATED on this tree (the rank-12 toolbar/read-me
> sweep — PLAN-20260730 PR-9 row's first half; PR-8 #498 and PR-9a #499 both MERGED by the
> operator before this round): the six Library/Setup pages (/margin · /workbench · /standards
> · /groups · /card/{name} · /wbs/{name}) each carry ONE panelkit.js include +
> `_panel_head`/`_shell_tools` per data visual + a muted read-me per visual (ADR-0327).
> ⤓ EXCEL wired ONLY where an existing export covers what the panel draws: /margin's three
> data panels → the ONE margin workbook; /standards §1 → the analysis workbook's DCMA sheet;
> /wbs both pivots → the WBS workbook (its two sheets ARE the pivots). ⤓ REFUSED with
> reasons recorded AND asserted: margin risk panel (live Zero-margin toggle vs static
> data-export — the r10 defect class), workbench head strip (its labeled Excel/Word links
> already are the §3:78 ⤓ — a glyph would duplicate one URL in one panel), standards §2/§3
> (NO export carries the Fuse/SEM families — recorded residual), /groups page-wide
> (URL-preview scope ≠ applied scope every export reads), /card page-wide (KPI set is no
> sheet; pivots 1-of-4 covered). NO ▦ anywhere (every panel's numbers are visible tables on
> the same page — home-shell precedent; no .sf-drawer invented). ⛶ on every data visual;
> forms/notices/empty states get NOTHING, and /groups + /wbs gate the include on a control
> actually in the assembled body (r11 dead-promise law). `_panel_head` gained `h2_attrs` so
> /margin's data-no-i18n headings survive. NO JS files touched — all PAGE_SCRIPTS freezes
> and the 16-site axisTitles census hold as-is. Version 1.0.143, highest ADR ADR-0327,
> wheel + nine installers regenerated ONCE after the code landed.**
>
> ## Verification (all read from runs this session)
> `test_r12_library_toolbar.py` (new, r11-style): include exactly-once + empty-state absence
> · ⤓ liveness with per-page COUNT pins (3/0/1/0/0/2 — no vacuous pass) · per-panel glyph
> anatomy incl. every refusal paired with a presence assertion · read-mes (the four NEW ones
> by content) · promotion census 7/2/5/5/3/3 · loaded-terms gate with its control · REAL
> chromium: ⛶ measurably lifts the /margin burn-down and /card pivots panels into the fixed
> overlay and Escape restores the box. **Proved able to fail, watched: 12 of 14 tests FAIL
> on the pre-change tree (git stash); the two both-tree passes are the invariant guards
> (clean empty states; census equal pre/post — the no-new-panels cross-check).** Post-change:
> **14 passed**. Six-page existing suites: **70 passed**. Neighbor sweep (r11 contract, DOM
> captions, portfolio panelkit, integrity shell): **36 passed**. Statics foreground: ruff
> check "All checks passed!" · format clean (829 files — the formatter reflowed BOTH edited
> files first, the known read-the-summary-line trap) · mypy --strict "no issues in 117
> source files" · bandit exit 0 · node --check clean. Full-suite + installer-lockstep
> results: see SESSION-LOG (recorded after the runs completed — a launched run is not a
> result).
>
> ## ⇢ NEXT
> 1. **Merge the draft PR for this round when CI is green** (branch
>    `claude/polaris-pr-9b-toolbar-ns95de`), then:
> 2. **PR-10 — OR-03 launch motion + synthesized hum** (plan row 10, decisions recorded;
>    WebAudio synthesis, no asset; motion CSS-only; the pinned `_AUTOPLAY_JS` list stays
>    untouched; tests per the plan row).
> 3. **OR-04 operator park artifacts stay open** (`audit/VERIFICATION-REPORT-ollama-lifecycle.md`
>    §8): #1 `where ollama` · #3 keep_alive probe · #5 runner PPID · #4 model-identity
>    manifest — plus #490's four-scenario smoke on the deployed build.
> 4. Behind the queue: SVG batch 3c (sra/sra_jcl/sra_ssi/volatility; tornados recorded
>    not-axis-charts per A1) · the 7-module `DOM_PENDING` ledger · Phase 3 (CC-01 rendering
>    half, 74 sites) · Phase 4 (P1–P6) · rank 13/14.
> 5. ADR-0327 residuals if ever wanted: a `/export/{fmt}/standards` workbook would let
>    §2/§3 join the ⤓ set; analysis-workbook makeup/status/constraint sheets would let
>    /card's pivots join. `data-noprint` (C1) ships as its own PR-4.
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
> · **test_float_tip_dismiss is a measured intermittent** (≈half of isolated runs fail
> the 4 s focus→tip wait on this container; /analysis bytes identical to main modulo the
> launch token) — an OR-02-adjacent hardening item, mechanism undetermined.
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
> unconditional floor · ADR-0311→0326 items), **plus this round:** "the six pages need new
> export endpoints to satisfy the toolbar" (the sweep wires EXISTING exports only; new
> endpoints are the recorded residual, not this round's scope); "tables take big=False"
> (no shipped table panel omits ⛶ — the sole big=False is the /analysis scatter whose chart
> script supplies its own); "the no-filter /groups Active-scope panel takes the toolbar"
> (it is a status NOTICE — branch 1 with criteria is the data visual); and "census pins can
> be written from the post-change render alone" (they must be verified EQUAL on the stashed
> pre-change tree, or the test cannot catch panel minting).
>
> ## Harness notes — the traps, one line each
> Run dev tools as `python -m <tool>` (a stale `/root/.local/bin/ruff` shadows pip's).
> **`pip install -e ".[dev]"` before the suite** (bare `PYTHONPATH=src` fails ~200 web tests).
> `pytest --timeout=N` is NOT installed — it exits 0 having run nothing. `cmd | tail; echo $?`
> reports `tail`'s status — **read the tool's own summary line** (the formatter reflowed BOTH
> edited files again this session). **`pkill -f` with a pattern in the killer's own command
> line kills the killer** (kill by PID). CI can take ~11 min to register check runs.
> `TestClient` follows 303 and CONSUMES one-shot banners (`follow_redirects=False`). Parity
> marker ≈2m38s (ADR-0322 perf addendum). Headless Chromium hides scrollbars. A remote-session
> resume can silently revert working-tree files — re-diff after every resume. `caplog` needs
> `logger="schedule_forensics.<module>"`. Playwright `bounding_box` is viewport-relative.
> **localStorage is per-ORIGIN** (second served app instance: write theme/scale AFTER landing
> on its origin). Containers RESTART mid-run: statics FOREGROUND first, long pytest
> re-runnable, reinstall pip after every resume. After a squash-merge: `git fetch --prune
> origin && git remote set-head origin -a && git checkout -B <branch> origin/main`.
> **Version-bump sequencing:** bump pyproject BEFORE the full background suite starts and the
> installer-lockstep tests in THAT run red-herring against the not-yet-rebuilt wheel — bump,
> rebuild wheel+installers, THEN launch the suite (or re-run tests/installer after).
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
