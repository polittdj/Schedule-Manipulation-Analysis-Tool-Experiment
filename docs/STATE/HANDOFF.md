# Handoff — 2026-07-31 (the base CPM honors per-task calendars; ADR-0324; v1.0.140)

> ## STATUS (current) — **OR-05 + OR-06 BUILT AND GATED on this tree (operator-directed
> engine-correctness deep dive, pre-empting the PR-8/9/10 queue): the base CPM now honors
> per-task calendars (ADR-0322 — the elapsed branch generalized: eDays = the 24/7 calendar),
> a violated MSO/MFO pin reports MS Project's negative slack, Open Start / Open Finish
> dangling checks landed per the Bible (ADR-0323), and a server launch token now scopes the
> browser's ADR-0186 page-selection memory (ADR-0324 — the operator's stale-Target-UID bug).
> Version 1.0.140, highest ADR ADR-0324, wheel + nine installers regenerated. #496
> (ADR-0321, v1.0.139) MERGED as `ffa5009` by the operator — the prior handoff's "merge
> PR-7" line is satisfied.**
> The oracle: `00_REFERENCE_INTAKE/mpp/Jacked Up Schedule 1.mpp`, `Jacked up Schedule 2.mpp`
> and the 6-slide `Politte Schedule Tool.pptx` (operator-committed, non-CUI), READ IN FULL —
> every slide, every task/link/calendar field, plus MS Project's own stored values (slack in
> tenths of a minute). Pre-change variances measured on the real engine: computed finish
> 10/28 vs MSP 10/07 (the 24-Hours task burned as 15 project days across the September
> void), the 24h task wrongly critical (TF 0 vs stored 36 900 min = 76.88 d), eDays slack
> collapsed by cap-space math (vs stored 3 780 min = 2.63 edays), the violated MFO milestone
> placid at 0 vs stored −2 400, and the dangling pair invisible to every logic check.
> Post-change: **recomputed float == stored Total Slack EXACTLY, task by task, on both
> files**; finishes 10/07 / 10/09; critical sets match MSP; wall instants ride
> `TaskTiming.*_wall` (project-axis ints stay canonical). **PowerPoint-vs-file divergence,
> verified and documented (NOT chased): the committed Jacked-2 .mpp does not contain Task
> 11's deadline** (MPXJ reads MPP14 deadlines fine — positive controls Hard_File UID 155 /
> Large-Test UID 157; the .mpp's last save 09:23 EDT predates the pptx's final edit
> 10:29 EDT). The tool's +13 d is the slide's own stated no-deadline outcome; if the
> operator re-saves the .mpp with the deadline, the pipeline already flows it (pinned).
>
> ## Verification (all read from runs this session)
> New `tests/engine/test_multicalendar_cpm.py` **17 passed** (exact-minute float table,
> stored==recomputed sweeps both files, wall instants through the void, free floats,
> critical sets, off-calendar chaining, offset-0 start-role, fast-path sentinel, deadline
> pipeline) — **proved able to fail: 14 failed / 5 passed pre-change** (the five passers are
> deliberate regression pins). New `tests/engine/test_dangling_logic.py` + oracle + ribbon +
> logic-panel neighbors **47 passed**. OR-06 `tests/web/test_launch_invalidation.py` (incl.
> a real-Chromium proof seeding the operator's exact stale-Target-UID shape) + the ADR-0186
> page-memory suite **12 passed** — **proved able to fail: 4 failed pre-fix**. Mid-build
> engine sweep **831 passed / 1 failed** → the one failure (TP3 ribbon neg-float 3→4) was
> ADJUDICATED against FUSE-VALIDATION.md's own "to reconcile" note and deliberately
> re-pinned (ADR-0322 §Verification), as was QC-D2's elapsed-chain pin {1:0}→{1:1440}
> (oracle: the eDays task's stored 3 780 for the same shape). Statics read this session:
> ruff 0.16.1 check clean · format clean (822 files) · mypy --strict "no issues in 117
> source files" · bandit exit 0 · node --check clean. Installer lockstep **52 passed** after
> wheel 1.0.140 + nine installers regenerated. Full-suite result: see SESSION-LOG (the run
> completed after this section was drafted; its numbers are recorded there — a launched run
> is not a result).
>
> ## ⇢ NEXT
> 1. **Merge the draft PR for this round when CI is green** (branch
>    `claude/polaris-engine-correctness-5y3ge1`), then RESUME the approved queue
>    (`docs/STATE/PLAN-20260730.md`, decisions A1 · B1 · C1 recorded — do NOT re-ask):
>    **PR-8 AXIS-TITLES 3b-i `margin_dashboard` per A1 (M)** → PR-9 rank-12 toolbar/read-me
>    + B1 caption mechanism (M–L) → PR-10 OR-03 launch motion + synthesized hum (M–L).
> 2. **Tell the operator about the Jacked-2 deadline divergence** (OPERATOR-REQUESTS OR-05
>    outcome note): re-saving the .mpp with the deadline makes Task 11 read −5 d end-to-end.
> 3. **OR-04 operator park artifacts stay open** (`audit/VERIFICATION-REPORT-ollama-lifecycle.md`
>    §8): #1 `where ollama` · #3 the `keep_alive:0`-vs-`OLLAMA_KEEP_ALIVE=-1` probe · #5
>    runner PPID + instance count · #4 the model-identity manifest — plus the four-scenario
>    smoke script from #490's PR body on the deployed build.
> 4. Behind the queue: **Phase 3** (CC-01 rendering half, 74 call sites — now WITH a live
>    oracle example: the eDays task's slack displays 7.88 d where MSP shows 2.63 edays; the
>    minutes beneath are exact) and **Phase 4** (P1–P6); rank 13/14.
>
> ## Still carried (unchanged identifiers, nothing lost)
> **CC-01** (H2a) — import half closed by ADR-0312, **rendering half open**, 74 call sites; new
> named example from this round: elapsed-task slack renders /480 (7.88 d) where MSP shows
> 2.63 edays — metric surfaces deliberately KEEP /480 (the proven Acumen-parity basis; ADR-0322
> residuals) · **CC-05** (H5) negative sub-day slack floor, oracle-gated · **V3** (H4) elapsed
> literals, `engine/msp_filters.py` · the **legacy `/sra` cross-basis defect** · **a committed
> SSI export contradicts ADR-0307's Best-Case rule** (Project5; ADR-0307 stands) · `resume` is
> read from **MSPDI only** · the forward pass still packs **completed** work from
> `project_start` (Phase 7) · ~~per-task calendars out-of-domain~~ **CLOSED by ADR-0322** —
> new residuals recorded there instead: cross-calendar link lag on the project axis (no
> oracle), the resume-floor MFO-violation corner, lossy int LS/LF projections for
> off-calendar tasks (walls exact) · importer warnings (assumed calendar +25 %) still belong
> on the page via `Schedule.import_notes` · **ADR-0320 residuals** (Focus form drops
> `cf_a`/`cf_b`; trace-options `tier=off` keep).
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
> - NEW (ADR-0322 blast-radius review, verified): the SSI driving-slack goldens are
>   **stored-date-insulated** from base-CPM changes — treat ANY diff there as an
>   implementation bug, never a re-baseline.
>
> ## Hypotheses KILLED — do not re-chase
> Everything in `audit/SRA-PARITY-20260729.md` §7 and the prior handoff's list (ADR-0307
> revert · unconditional data-date floor · ADR-0311/0313/0314/0315/0316/0317/0320 items),
> **plus this round:** "the Jacked-2 slide's −5 d for Task 11 means the engine must produce
> −5 d on the committed file" (the deadline is NOT in the saved bytes — proven via MPXJ
> positive controls + save-vs-edit timestamps; 13 d is correct for the file as saved);
> "cap-space slack is safe for elapsed tasks" (it under-measures across non-working gaps —
> the stored 3 780 disproves it); "a violated MFO's TF is 0 because LS−ES is 0" (MSP stores
> the violation: −2 400, now reproduced); and "per-task calendars can stay disclosure-only"
> (the 24h-task finish error was three weeks of project finish).
>
> ## Harness notes — the traps, one line each
> Run dev tools as `python -m <tool>` (a stale `/root/.local/bin/ruff` shadows pip's).
> **`pip install -e ".[dev]"` before the suite** (bare `PYTHONPATH=src` fails ~200 web tests).
> `pytest --timeout=N` is NOT installed — it exits 0 having run nothing. `cmd | tail; echo $?`
> reports `tail`'s status. **`pkill -f` with a pattern that appears in the killer's own shell
> command line kills the killer** (bit this session — exit 144; kill by PID). CI can take
> ~11 min to register check runs. `TestClient` follows 303 and CONSUMES one-shot banners
> (`follow_redirects=False`). On THIS container the parity marker alone ran ~28 min (SRA
> Monte-Carlo, single-core) — the handoff's old "≈40 s" does not hold here; foreground wait =
> `tail --pid=<real pytest pid> -f /dev/null`. Headless Chromium hides scrollbars. A
> remote-session resume can silently revert working-tree files — re-diff after every resume.
> `caplog` needs `logger="schedule_forensics.<module>"`. Playwright `bounding_box` is
> viewport-relative — assert width/height/x. Containers RESTART mid-run: statics FOREGROUND
> first, treat long pytest as re-runnable, reinstall pip after every resume.
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
