# Handoff — 2026-07-30 (the import anchor enforced; ADR-0312; v1.0.130)

> ## STATUS (current) — **Phase 2 item 3 (external H2c) shipped as ADR-0312. #486 (rank 12 takeaways, ADR-0311) is OPEN and green, awaiting the operator.**
> ADR-0312 implements ADR-0310's **decision 5**: the offset ↔ datetime precondition is now **enforced
> at the importer boundary** — normalise or reject, never merely warn. **No committed figure moves**
> (asserted, not assumed: all 21 committed schedules are already inside the supported domain).
> Version **1.0.130**, wheel + nine installers regenerated. Highest ADR **ADR-0312**.
> Evidence: `audit/SRA-ROOTCAUSE-20260730.md` · `audit/EXTERNAL-RECONCILIATION-20260730.md`.
>
> ## What ADR-0312 shipped
> - **`importers/_common.anchored_project_start(start, calendar, *, source)`** — one shared helper,
>   called by MSPDI, XER **and** the tool's own JSON format so the three cannot drift.
>   Inside the domain (`start_tod + working_minutes_per_day <= 1440`) the start comes back
>   **byte-identical with no note**. Outside it, the start is normalised to the calendar's
>   **modelled shift start**; when even that cannot fit a working day the file is **rejected**.
> - **`modelled_shift_start(calendar)`** = earliest `day_segments` start, else **0**. Midnight is
>   not a guess — `Calendar.intraday_worked_minutes` ALREADY models a segment-free calendar as one
>   contiguous block from midnight, so the fallback reads an existing contract. `Calendar` still has
>   **no shift-start field** and ADR-0310's decision to not add one stands.
> - **`Schedule.import_notes: tuple[str, ...]`** — operator-visible statements of *how the importer
>   interpreted the file*, never its contents (same CUI contract as `ImporterError`). Rendered in the
>   **Working-calendar panel** as a `notice warn`, and round-tripped through Save `.json`.
> - **`units.MINUTES_PER_CALENDAR_DAY = 1440`** — the wall-clock axis gets a name, so ADR-0310
>   decision 4 ("no hard-coded minutes-per-day") has something to point at.
>
> ## The measurement that justifies it (24 h calendar, Monday 08:00 start, 12-day offset sweep)
> | | renders on a **non-working** date | breaks `datetime_to_offset(offset_to_datetime(k)) == k` |
> |---|---:|---:|
> | as imported (08:00) | **26** | **156** |
> | after normalisation (00:00) | **0** | **0** |
>
> The **second column is why a display-only helper cannot close this** — the engine was converting an
> offset to an instant and back and getting a different number. That is exactly ADR-0310's split:
> CC-01 is rendering, this was import. **CC-01 is still open and unchanged (74 call sites).**
>
> ## Two things to know before touching this again
> - **The first draft of the operator note was WRONG and the probe caught it.** It said "the date each
>   activity is scheduled on is unaffected". False — the rendered calendar date moves (that is the
>   point). What is invariant is the **working day**: `offset_to_datetime`'s whole-day term is a
>   function of the offset and calendar, never of the anchor's time of day. Pinned by
>   `test_normalisation_keeps_every_activity_on_the_same_working_day`.
> - **The inclusive boundary is a KNOWN residual, deliberately left to CC-01.**
>   `start_tod + per_day == 1440` is inside the declared domain, and an exact-multiple offset renders
>   at the END of the working day — 00:00 of the following calendar date, possibly a weekend. It
>   cannot be normalised away (a 24 h calendar has no in-domain start that avoids it). Recorded in
>   ADR-0312 §"What this does NOT fix" so item 6 inherits it.
>
> ## Coverage checked, and the gap it exposed
> All **54** `offset_to_datetime` call sites in `src/` pass a schedule's own **project** calendar
> (read, not assumed), so enforcing the `(project_start, project_calendar)` pair covers the whole
> rendering direction. **But per-task calendars are a reachable out-of-domain pairing this ADR does
> NOT touch:** `00_REFERENCE_INTAKE/mpp/Hard_File_updated4 24 hour calendar.mpp` (converted and
> parsed this round) has a Standard 8 h *project* calendar — in domain — plus per-task `24 Hours`
> (uid 10, 1440 min/day, 7-day week) and `Standard+Sat.` (uid 12, 930), both assigned to tasks.
> `driving_slack` measures stored dates against a task's own calendar using the PROJECT anchor
> (`_stored_offset(ps, when, cal)`), i.e. `start_tod 480 + per_day 1440`. It only ever runs the
> MEASUREMENT direction, so it renders no non-working dates — but it is outside the declared domain
> and nothing enforces it there. That belongs to ADR-0118's per-task model, not the project anchor.
> **Not merely argued — pinned:** `tests/parity/test_ssi_hardfile_24h_uid155.py` reproduces 100 SSI
> Directional-Path rows cell-for-cell across the 8 h and 24 h snapshots of that same schedule (the
> pair whose driving slack differs 32 d vs 18 d *because* of the per-task calendar) and is green.
>
> ## `SCHEMA_VERSION` 2.8.0 → **2.9.0**, covering TWO adds
> `Schedule.import_notes` (ADR-0312) **and, retroactively, `Task.resume`** (ADR-0309, #483). That
> one shipped with the freeze test's field set updated but the version left at 2.8.0 — the guard
> asserts a literal equality, so **it cannot see an add that was registered but not versioned**. If
> you add a model field, bump the version in the same commit; the test will not remind you.
>
> ## ⇢ NEXT — #486 first, then rank 12's remainder
> **#486 is open, draft, all six checks green, `mergeable_state: clean`, zero review comments.** After
> it merges: `git fetch --prune origin && git remote set-head origin -a && git checkout -B
> claude/smat-hardened-review-pwxm33 origin/main`.
>
> **Phase 2 is now items 1, 2, 3 and 4 DONE.** The only Phase 2 remainder is **item 5** — V1/V2, the
> tri-state SRA magnitude parser (`missing | valid | invalid(reason)`) with an operator-visible error,
> bounded length, non-finite/overflow rejection, spreadsheet-formula-injection guard on export, and a
> cap on the uncapped `/sra/ssi/load` upload. **That is unblocked, ordinary work.**
>
> ## ⇢ RANK 12 REMAINDER — BLOCKED, do NOT invent the answers
> Three operator decisions, unchanged:
> 1. **AXIS-TITLES `PENDING`** — `/margin`'s toolbar needs `margin_dashboard.js` captioned (batch 3b).
> 2. **`NO_SVG_AXES` DOM caption mechanism** — `/workbench`'s `workbench.js`; ADR-0298 records this as
>    *"a separate design decision, deliberately not invented here."*
> 3. **`data-noprint`** — still **zero CSS rules anywhere**, across ten already-merged contract pages.
>
> Everything else in rank 12 is done (ADR-0311 + #486: kickers, segues, nav entries, all six takeaway
> h1s + context lines, all six Setup rail takeaways). Then rank 13 (vendored typography) and rank 14.
>
> ## Still carried (unchanged identifiers, nothing lost)
> **CC-01** (H2a) `offset_to_datetime` non-working dates, 74 call sites — **import half now closed by
> ADR-0312, rendering half open** · **CC-05** (H5) negative sub-day slack floor, oracle-gated ·
> **V1/V2** (H3) SRA magnitude needs an operator-visible error · **V3** (H4) elapsed literals —
> `engine/msp_filters.py` is the sole violator of a convention the repo already follows eight times,
> so it is a conformance fix, but the saved-filter **population still moves** and the evaluator
> versioning + migration report still gate it · the **legacy `/sra` cross-basis defect**
> (`_build_result` reads a full-duration deterministic against a remaining-duration sample, no
> realignment; reaches `/api/sra`, the SRA report, `sra_conclusions`, and
> `scorecards.reserve_recommendation`, whose dates sit on a different axis from `/api/margin/risk`) ·
> **a committed SSI export contradicts ADR-0307's Best-Case rule** (Project5 `SRA Sensitivity
> Analysis.xlsx` shows the pre-0307 ratios; ADR-0307 stands for the artifact we match — stored
> Best/Worst wins, the table+rule is the operator-entered fallback) · `resume` is read from **MSPDI
> only**, the XER path has no equivalent · the forward pass still packs **completed** work from
> `project_start` (724 tasks, median −1458 d vs stored actuals; does not move the focus or project
> finish — Phase 7) · several existing importer warnings (notably the **assumed** calendar, which
> overstates every duration-in-days figure by 25 % when a 10-hour calendar fails to resolve) belong on
> the page via `import_notes` and have not migrated.
>
> ## SRA parity — CLOSED, and the traps that stay shut
> ADR-0309 (#483/#484) closed it against SSI's own committed export: det percentile **40.70 % →
> 6.65 %** (SSI **5.75 %**), σ **125.5 → 65.5** cal d (SSI **64.744**, 1.2 %), mean **+26 → +109**
> (SSI **+111.45**), P10/P50/P80/P90 within **7/1/0/3** days, all five calibration seeds passing.
> - **The anchor is CONDITIONAL on stored data — MS Project's own `<Resume>` — never a blanket
>   data-date floor.** ADR-0108's two reverts were both unconditional floors; EVM1 UID 18 has
>   `resume == stop` and must not move.
> - **A floor built from the STORED remaining silently destroys the Monte-Carlo's upside variance**
>   (`det_pctile = 100 %`, σ 20.3). It must follow `duration_overrides`. The wrong version improved
>   3 of 6 headline metrics. Do not "simplify" it back.
> - **Do NOT chase SSI's `Mean Date` / `Standard Deviation` cells (47322 / 107.8198)** — computed over
>   the 245 DISTINCT dates with `Occurrences` dropped. The target is the occurrence-weighted
>   histogram. `test_the_summary_cells_are_not_the_parity_target` pins the trap shut.
>
> ## Hypotheses KILLED — do not re-chase
> Everything in `audit/SRA-PARITY-20260729.md` §7 (impact days as calendar not working days ·
> `std_cal_days` as a 7/5 fudge · `mean_delta_days` overstating · float absorption · V2 as the cause
> of the screenshot), **plus**: reverting ADR-0307's Best-Case rule (it moves the mean closer while
> leaving σ wrong — the exact error cancellation Law 2 forbids), an **unconditional** data-date floor
> (ADR-0108's two reverts; ADR-0309 supersedes), and "the four Setup pages have no chapter kicker"
> (ADR-0311 — the probe regexed `CHAPTER \d+ ·`, which cannot match an empty-number kicker).
>
> ## Harness notes
> Run dev tools as `python -m <tool>` (a stale `/root/.local/bin/ruff` shadows pip's; the tell is a
> **793** file-count mismatch). **`pip install -e ".[dev]"` before running the suite** — with a bare
> `PYTHONPATH=src` the package has no distribution metadata and ~200 web tests fail with
> `PackageNotFoundError`, which is setup contamination and not a product verdict (an external audit
> hit the identical 211-failed/828-error pattern and correctly discounted it). **`--timeout` is not
> installed** — passing it makes pytest exit **0** having run nothing, which reads as a pass in a
> background task's exit code. Converting the reference `.mpp` needs a writable `TMPDIR` (~9 s), and
> **2000 SRA iterations ≈ 90 s**, so the oracle test costs ~2 min. Full `pytest -q` ≈ 15 m;
> `pytest -m parity` ≈ 40 s — run parity first. Regenerate the wheel with `--outdir dist/wheel` (the
> default silently embeds a STALE wheel) and only ONCE after all code lands.
>
> **Standing rule, from this session's own failure:** do not put a test result in prose unless the
> number appeared in output you read that turn. **A launched run is not a result.**

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
