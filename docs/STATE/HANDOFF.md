# Handoff — 2026-08-01 (PR-8: the margin dashboard joins the one caption convention; ADR-0325; v1.0.141)

> ## STATUS (current) — **PR-8 of the approved queue BUILT AND GATED on this tree (AXIS-TITLES
> batch 3b-i per decision A1): both `margin_dashboard.js` charts captioned via the ONE shared
> helper (burn-down "Status date" × "Days (margin + contingency)" — the bars stack work-day
> margin with calendar-day contingency, so the caption asserts no single basis; erosion
> "Status date" × "Effective margin (working days)"), the two local `"status date"`
> quasi-captions retired, `y2Label` dropped (single scale verified, per A1), the in-SVG
> legends yield the helper's corner ((L+4, T+2) → (L+4, T+24)), and the page's script tag
> gains `defer` — margin_dashboard.js executes at parse time BEFORE the layout-footer
> chartframe.js, so the direct `SFChartFrame.axisTitles` call threw and NEITHER chart
> rendered (measured: 12/12 combos "no captions rendered" pre-fix; ADR-0316's blob-driven
> defer family, third member). `/margin` joined the measured visual pass with its OWN serve
> (four synthetic status-dated versions eroding 40 → 10 wd — the golden pair legitimately
> charts nothing there); the call-site census re-baselined 16 → 18 DELIBERATELY (the 16
> priors byte-identical; A1 recorded the procedure). Version 1.0.141, highest ADR ADR-0325,
> wheel + nine installers regenerated. #497 (ADR-0322–0324, v1.0.140) MERGED as `afb8e72`
> by the operator.**
> **OR-05 is now closed END-TO-END with zero code change: the operator deleted + re-uploaded
> `Jacked up Schedule 2.mpp` (blob `db7ac6ef` → `a7d2f9c6`, commits `ef3adc1`/`9ec7265`) —
> the re-saved bytes DO carry Task 11's deadline (`2026-08-14T17:00:00`), verified this
> session by a fresh MPXJ conversion byte-identical to the committed
> `jacked_up_schedule_2_with_deadline.xml` fixture (only `<CurrentDate>` differs, the
> conversion timestamp). UID 32 reads −5 d end-to-end exactly as the prior handoff predicted
> (`test_resaved_jacked2_deadline_reads_minus_five_days_end_to_end` already pinned it); the
> "tell the operator" NEXT item is overtaken by events.**
>
> ## Verification (all read from runs this session)
> Re-uploaded-oracle sweep: `test_multicalendar_cpm.py` + `test_dangling_logic.py` +
> `test_ribbon.py` + `test_elapsed_axis_regressions.py` + `test_projects/test_battery.py`
> **80 passed**. PR-8: ledger/census/margin-view/legend suites **69 passed** post-change;
> visual pass **720 caption renders measured clean** (4 themes × 3 scales × 7 pages, zero
> problems, `KNOWN_COLLISIONS` stays empty) — **proved able to fail three ways, watched:**
> the un-deferred tag failed 12/12 combos ("no captions rendered"), the OLD census against
> this tree failed (18 ≠ 16), the defer pin failed on the un-deferred page. Statics:
> ruff check clean · format clean (825 files) · mypy --strict "no issues in 117 source
> files" · bandit exit 0 · node --check clean. Installer lockstep **52 passed** after wheel
> 1.0.141 + nine installers regenerated. Full-suite result: see SESSION-LOG (recorded there
> after the run completed — a launched run is not a result).
>
> ## ⇢ NEXT
> 1. **Merge the draft PR for this round when CI is green** (branch
>    `claude/polaris-engine-correctness-resume-e52fpp`), then RESUME the approved queue
>    (`docs/STATE/PLAN-20260730.md`, decisions A1 · B1 · C1 recorded — do NOT re-ask):
>    **PR-9 rank-12 toolbar/read-me + B1 caption mechanism (M–L, may split)** → PR-10 OR-03
>    launch motion + synthesized hum (M–L).
> 2. **OR-04 operator park artifacts stay open** (`audit/VERIFICATION-REPORT-ollama-lifecycle.md`
>    §8): #1 `where ollama` · #3 the `keep_alive:0`-vs-`OLLAMA_KEEP_ALIVE=-1` probe · #5
>    runner PPID + instance count · #4 the model-identity manifest — plus the four-scenario
>    smoke script from #490's PR body on the deployed build.
> 3. Behind the queue: **batch 3c** (the four remaining PENDING modules: `sra.js`,
>    `sra_jcl.js`, `sra_ssi.js`, `volatility.js` — tornados already recorded as
>    not-axis-charts by A1), **Phase 3** (CC-01 rendering half, 74 call sites — live oracle
>    example: the eDays task's slack displays 7.88 d where MSP shows 2.63 edays; the minutes
>    beneath are exact) and **Phase 4** (P1–P6); rank 13/14.
>
> ## Still carried (unchanged identifiers, nothing lost)
> **CC-01** (H2a) — import half closed by ADR-0312, **rendering half open**, 74 call sites;
> elapsed-task slack renders /480 (7.88 d) where MSP shows 2.63 edays — metric surfaces
> deliberately KEEP /480 (the proven Acumen-parity basis; ADR-0322 residuals) · **CC-05** (H5)
> negative sub-day slack floor, oracle-gated · **V3** (H4) elapsed literals,
> `engine/msp_filters.py` · the **legacy `/sra` cross-basis defect** · **a committed SSI export
> contradicts ADR-0307's Best-Case rule** (Project5; ADR-0307 stands) · `resume` is read from
> **MSPDI only** · the forward pass still packs **completed** work from `project_start`
> (Phase 7) · ADR-0322 residuals: cross-calendar link lag on the project axis (no oracle), the
> resume-floor MFO-violation corner, lossy int LS/LF projections for off-calendar tasks (walls
> exact) · importer warnings (assumed calendar +25 %) still belong on the page via
> `Schedule.import_notes` · **ADR-0320 residuals** (Focus form drops `cf_a`/`cf_b`;
> trace-options `tier=off` keep) · ADR-0325 note: the erosion chart's "zero margin" annotation
> is data-dependent — if a future dataset parks it under the Y caption, that is ADR-0303's
> data-label-yields case, fixed in `margin_dashboard.js`, never by moving the caption.
>
> ## SRA parity — CLOSED, and the traps that stay shut
> ADR-0309 (#483/#484): det percentile **40.70 % → 6.65 %** (SSI **5.75 %**), σ **125.5 →
> 65.5** cal d (SSI **64.744**, 1.2 %), mean **+26 → +109** (SSI **+111.45**), P10/P50/P80/P90
> within **7/1/0/3** days, all five calibration seeds passing.
> - **The anchor is CONDITIONAL on stored data — never a blanket data-date floor** (ADR-0108's
>   two reverts were both unconditional floors; EVM1 UID 18 has `resume == stop`, must not move).
> - **A floor built from the STORED remaining destroys the Monte-Carlo's upside variance** —
>   it must follow `duration_overrides`. Do not "simplify" it back.
> - **Do NOT chase SSI's `Mean Date` / `Standard Deviation` cells (47322 / 107.8198)** —
>   `test_the_summary_cells_are_not_the_parity_target` pins the trap shut.
> - The SSI driving-slack goldens are **stored-date-insulated** from base-CPM changes — treat
>   ANY diff there as an implementation bug, never a re-baseline (ADR-0322 blast-radius review).
>
> ## Hypotheses KILLED — do not re-chase
> Everything in `audit/SRA-PARITY-20260729.md` §7 and the archived handoffs' lists (ADR-0307
> revert · unconditional data-date floor · ADR-0311/0313/0314/0315/0316/0317/0320/0322–0324
> items), **plus this round:** "the committed Jacked-2 lacks Task 11's deadline" — TRUE of the
> ORIGINAL upload, now FALSE: the operator's re-upload carries it (verify against blob
> `a7d2f9c6`, not memory); "margin_dashboard could reuse the parse-time script pattern" (it
> executes before the layout-footer chartframe.js — the guarded `scan()` call at its bottom was
> the tell; defer is the family fix); and "the golden pair can serve /margin's visual pass"
> (no margin-named tasks, no status-dated months — it renders NO chart there by design).
>
> ## Harness notes — the traps, one line each
> Run dev tools as `python -m <tool>` (a stale `/root/.local/bin/ruff` shadows pip's).
> **`pip install -e ".[dev]"` before the suite** (bare `PYTHONPATH=src` fails ~200 web tests).
> `pytest --timeout=N` is NOT installed — it exits 0 having run nothing. `cmd | tail; echo $?`
> reports `tail`'s status. **`pkill -f` with a pattern that appears in the killer's own shell
> command line kills the killer** (exit 144; kill by PID). CI can take ~11 min to register
> check runs. `TestClient` follows 303 and CONSUMES one-shot banners (`follow_redirects=False`).
> Parity marker: ~2m38s after the ADR-0322 perf addendum (the old "~28 min on this container"
> note is dead). Headless Chromium hides scrollbars. A remote-session resume can silently
> revert working-tree files — re-diff after every resume. `caplog` needs
> `logger="schedule_forensics.<module>"`. Playwright `bounding_box` is viewport-relative —
> assert width/height/x. **localStorage is per-ORIGIN**: a second served app instance needs
> theme/scale written AFTER landing on its origin (`test_axis_titles_visual.py`). Containers
> RESTART mid-run: statics FOREGROUND first, treat long pytest as re-runnable, reinstall pip
> after every resume. After the operator squash-merges, restart the branch with
> `git fetch --prune origin && git remote set-head origin -a && git checkout -B <branch> origin/main`.
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
