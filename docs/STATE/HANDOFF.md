# Handoff — 2026-07-30 (#487 merged and verified; the three gating decisions are briefed; ADR-0313; v1.0.131)

> ## STATUS (current) — **#487 MERGED as `c937ad9` and verified end-to-end. No code changed this session; the three operator decisions are now BRIEFED (`docs/STATE/DECISION-BRIEFS-20260730.md`) and awaiting answers.**
> Version stays **1.0.131**, highest ADR **ADR-0313**, `main` at **`c937ad9`**. Post-merge CI on
> `main@c937ad9` is fully green (CI run 30553471610: `test (3.11)` incl. coverage + parity gates,
> `test (3.13)`, `browser (measured-box proof)`, `check`; installer-smoke run 30553471322: `linux`,
> `windows`).
>
> ## The owed full-suite figure — READ AND CLOSED
> The previous handoff owed a full-suite figure from a run actually read. Done, twice over, both
> posted on #487:
> - The previous session's own pre-bump run: `4 failed, 3062 passed, 24 skipped in 799.10s` — all
>   four failures the ADR-0148 lockstep gate firing on the stale embedded wheel from before the
>   1.0.131 bump; re-run green as a 60-test subset at 1.0.131 (posted 12:49Z, before merge).
> - **The committed tree, one run, no subset carve-out:** `python -m pytest -q` on `main@c937ad9` →
>   **`3067 passed, 24 skipped, 1 warning in 853.99s`**, exit **0** read from the file the command
>   itself wrote (`; echo $? > file`), **zero** `FAILED`/`ERROR` lines as the independent second
>   check. The 24 skips are the playwright-gated ones (runtime stays stdlib-only).
>
> ## ⇢ NEXT — the three decisions are briefed; the queue is waiting on answers
> **`docs/STATE/DECISION-BRIEFS-20260730.md`** carries, for each decision, the verified state,
> options with tradeoffs, a recommendation, and the sub-questions to confirm. Summary:
> **(A) AXIS-TITLES batch 3b scope** — recommended: `margin_dashboard.js` first (smallest slice
> that unblocks ADR-0311's `/margin` toolbar), rest as 3c, with the Cartesian-only triage recorded
> in the batch ADR. **(B) `NO_SVG_AXES` DOM caption mechanism** — recommended: native `<caption>`
> on data tables + one label slot in the shared SFGantt timescale header (covers 4 modules at a
> stroke), with an ADR recording "one convention per medium" and a new ledger detector.
> **(C) `data-noprint`** — recommended: the one-line `[data-noprint]{display:none!important}` in
> base.css's A5 print block, as its own small PR with print-preview verification.
>
> **Four research findings that change the picture** (each verified against the file):
> 1. **ADR-0076 already records the print mechanism** — "a `@media print` stylesheet (base.css)",
>    pinned by `tests/web/test_accessibility.py:102-109` asserting the rules live IN base.css. A
>    separate `print.css` would contradict a recorded decision AND an existing test.
> 2. **DESIGN-SYSTEM §3:78 "Tables get `⤓ EXCEL` only"** shrinks what rank 12 owes on
>    `/workbench`: nearly all 13 `NO_SVG_AXES` entries render tables/grids, and `/workbench`
>    already ships its Excel exports (`app.py:13259-13260`, `workbench.js:179`) — the owed work is
>    ▦ DATA / ⛶ ENLARGE / read-me line, not the full triple.
> 3. **ADR-0302's `y2Label` prediction does not survive the code**: `sra.js`'s CDF is single-axis
>    (`sra.js:50-57`) and `margin_dashboard`'s burn-down is one scale carrying two named units
>    (`:157/:162`) — no second scale exists in either.
> 4. **`volatility.js` is byte-frozen WHOLE** (`PAGE_SCRIPTS`,
>    `tests/web/test_r11_panel_contract.py:436-444`), so batch 3b re-baselines more than the
>    16-site `axisTitles` census; line-neutral editing cannot work when ADDING call sites — the
>    re-baseline must be deliberate and named.
>
> **Not gated on the decisions** (available to any session meanwhile): OR-01/OR-02/OR-03 in
> `docs/STATE/OPERATOR-REQUESTS.md` (OR-02 — the DCMA-11 call-out that covers the left nav and
> will not dismiss — is a **bug**); `/analysis/{name}` panel 5's two ⛶ (one inert); `/evolution`'s
> target-blind `⬇ Excel / ⬇ Word` bar under a banner promising otherwise; the `/resources`
> X-caption collision; the `/performance` first-paint race. Then rank 13 (vendored typography) and
> 14 behind rank 12. Behind the UI queue: **Phase 3** (CC-01, 74 call sites, Fable-5-Max deep
> dive; V3 elapsed literals) and **Phase 4** (P1–P6, measured but unremediated).
>
> ## Still carried (unchanged identifiers, nothing lost)
> **CC-01** (H2a) — import half closed by ADR-0312, **rendering half open**, 74 call sites; its two
> named residuals are ADR-0312's inclusive boundary (`start_tod + per_day == 1440` renders an
> exact-multiple offset at 00:00 of the FOLLOWING date) and `Calendar` still having no shift-start
> field · **CC-05** (H5) negative sub-day slack floor, oracle-gated · **V3** (H4) elapsed literals,
> `engine/msp_filters.py` the sole violator of a convention the repo already follows eight times ·
> the **legacy `/sra` cross-basis defect** (`_build_result` reads a full-duration deterministic
> against a remaining-duration sample, no realignment; reaches `/api/sra`, the SRA report,
> `sra_conclusions`, and `scorecards.reserve_recommendation`, whose dates sit on a different axis
> from `/api/margin/risk`) · **a committed SSI export contradicts ADR-0307's Best-Case rule**
> (Project5 shows the pre-0307 ratios; ADR-0307 stands for the artifact we match — stored Best/Worst
> wins, the table+rule is the operator-entered fallback) · `resume` is read from **MSPDI only** ·
> the forward pass still packs **completed** work from `project_start` (724 tasks, median −1458 d vs
> stored actuals; does not move the focus or project finish — Phase 7) · **per-task calendars are an
> out-of-domain pairing ADR-0312 does not reach** (`driving_slack` measures stored dates against a
> task's own calendar using the PROJECT anchor; measurement direction only, and the 24 h SSI golden
> is green) · several importer warnings (notably the **assumed** calendar, which overstates every
> duration-in-days figure by 25 % when a 10-hour calendar fails to resolve) belong on the page via
> `Schedule.import_notes` and have not migrated.
>
> ## SRA parity — CLOSED, and the traps that stay shut
> ADR-0309 (#483/#484): det percentile **40.70 % → 6.65 %** (SSI **5.75 %**), σ **125.5 → 65.5** cal d
> (SSI **64.744**, 1.2 %), mean **+26 → +109** (SSI **+111.45**), P10/P50/P80/P90 within
> **7/1/0/3** days, all five calibration seeds passing.
> - **The anchor is CONDITIONAL on stored data — MS Project's own `<Resume>` — never a blanket
>   data-date floor.** ADR-0108's two reverts were both unconditional floors; EVM1 UID 18 has
>   `resume == stop` and must not move.
> - **A floor built from the STORED remaining destroys the Monte-Carlo's upside variance**
>   (`det_pctile = 100 %`, σ 20.3). It must follow `duration_overrides`. The wrong version improved
>   3 of 6 headline metrics. Do not "simplify" it back.
> - **Do NOT chase SSI's `Mean Date` / `Standard Deviation` cells (47322 / 107.8198)** — computed over
>   the 245 DISTINCT dates with `Occurrences` dropped. `test_the_summary_cells_are_not_the_parity_target`
>   pins the trap shut.
>
> ## Hypotheses KILLED — do not re-chase
> Everything in `audit/SRA-PARITY-20260729.md` §7, **plus**: reverting ADR-0307's Best-Case rule (it
> moves the mean closer while leaving σ wrong — the exact error cancellation Law 2 forbids); an
> **unconditional** data-date floor (ADR-0108's two reverts, superseded by ADR-0309); "the four Setup
> pages have no chapter kicker" (ADR-0311 — the probe regexed `CHAPTER \d+ ·`, which cannot match an
> empty-number kicker); and **"the xlsx writer needs a formula-injection guard"** (ADR-0313 — it emits
> no `<f>`; the CSV sibling was the real vector).
>
> ## Harness notes — three exit-code traps now, all the same shape
> Run dev tools as `python -m <tool>` (a stale `/root/.local/bin/ruff` shadows pip's; the tell is a
> **793** file-count mismatch). **`pip install -e ".[dev]"` before running the suite** — a bare
> `PYTHONPATH=src` gives `PackageNotFoundError` on ~200 web tests (an external audit hit the identical
> 211-failed/828-error pattern and correctly discounted it).
> 1. **`pytest --timeout=N` is NOT installed** — passing it makes pytest exit **0** having run nothing.
> 2. **`cmd | tail; echo $?` reports `tail`'s status, not `cmd`'s.** This is how the node harness was
>    reported green while exiting 1. Redirect to a file and check the exit code directly.
> 3. **CI took ~11 minutes to register check runs** on one push — `total_count: 0` means "not yet",
>    never "passed".
> **`TestClient` follows a 303 by default**, and that render CONSUMES a one-shot banner — use
> `follow_redirects=False` when asserting on `sra_import_msg`. Converting the reference `.mpp` needs a
> writable `TMPDIR` (~9 s); **2000 SRA iterations ≈ 90 s**. Full `pytest -q` ≈ 14 m;
> `pytest -m parity` ≈ 40 s — run parity first. Regenerate the wheel with `--outdir dist/wheel` (the
> default silently embeds a STALE wheel) and only ONCE after all code lands.
> **New this session:** a remote-session resume KILLS in-flight background work — the Workflow
> journal + `resumeFromRunId` recovered 5 of 6 agents' results without re-running them; and a
> handoff written before a round's last actions records **intent, not outcome** — this handoff's
> "drive #487 to green" and "the figure is owed" were BOTH already done (merged 14:47Z; figure
> posted 12:49Z) when the next session started. Check the live system before redoing "owed" items.
>
> **Standing rule, from this project's own failures:** do not put a test result in prose unless the
> number appeared in output you read that turn. **A launched run is not a result, and a piped exit
> code is not the command's.**

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
