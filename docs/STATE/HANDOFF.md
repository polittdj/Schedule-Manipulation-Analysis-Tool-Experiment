# Handoff — 2026-07-30 (a number the operator never typed; ADR-0313; v1.0.131)

> ## STATUS (current) — **PHASE 2 IS COMPLETE.** Item 5 (V1/V2 / external H3) shipped as ADR-0313; #486 (ADR-0311 rank 12 + ADR-0312 import anchor) MERGED as `dcb891e`.
> ADR-0313 closes the **last Phase 2 item**. The SRA magnitude parser is now **tri-state**
> (absent / valid / invalid-with-a-reason), an unreadable entry is **refused and reported** instead
> of becoming a locked zero, and the server + `sra_risk.js` are pinned to **one shared grammar** by a
> case table both read. Version **1.0.131**, wheel + nine installers regenerated. Highest ADR
> **ADR-0313**. Evidence: `audit/SRA-ROOTCAUSE-20260730.md` · `audit/EXTERNAL-RECONCILIATION-20260730.md`.
>
> ## The defect, measured (`avg_rem = 10.0`)
> | input | `(days, pct, dl, pl)` | |
> |---|---|---|
> | *absent* days + valid `50` | `(5.0, 50.0, False, True)` | correct — 50 % of 10 d **derives** 5 d |
> | **garbage** days + valid `50` | **`(0.0, 50.0, True, True)`** | SSI sees **0 d**, legacy sees **50 %** |
> | valid `7` + **garbage** pct | **`(7.0, 0.0, True, True)`** | mirror image |
> | garbage + garbage | `(0.0, 0.0, True, True)` | both zeroed |
>
> Rows 1 vs 2 are the point: an invalid entry did not merely "read as zero", it **suppressed the
> derivation that is the function's whole purpose**, leaving one risk row whose two magnitudes
> describe **two different events** — with a 303 redirect and no message. ChatGPT's H3 "additive vs
> legacy disagree" is **TRUE but only for the MIXED input**; garbage-in-both zeroes both, so the
> general phrasing overstates it. **Gemini's "missing defaults" stays a harness error** (5 required
> positional args, both call sites pass 5) — do not act on it.
>
> ## The finding no audit had: the two implementations ALREADY disagreed
> `sra_risk.js`'s header claims *"the server mirrors this exact math."* **False.** JS `parseFloat`
> takes a numeric PREFIX and Python `float()` accepts PEP-515 underscores, so:
> `"1.2.3"` → **1.2** client / `ValueError` server · `"5 days"` → **5** / reject ·
> `"12,5"` → **12** / reject · `"1_000"` → 1 / **1000.0**. One grammar
> (`^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$`, stricter than BOTH) now governs both sides, pinned by
> **`tests/web/js/magnitude_cases.json`** — read by the Python test AND the node harness, so adding a
> case exercises both. **Proved able to fail:** reverting `num()` to `parseFloat` makes the harness
> exit **1** with 16 failures; restoring it exits **0**.
>
> ## Also shipped
> - **A length bound (32 chars), not a magnitude ceiling** — makes the overflow class unreachable
>   (`float("1"*400)` is `inf`) without deciding how many days is too many. Deliberately not decided.
> - **An invalid field is never locked** — the client-supplied `*_locked` flag must not pin a value
>   the server refused to read.
> - **The Excel importer keeps its own promise** (*"a missing figure is skipped and reported, never
>   guessed"* — true for EMPTY, false for MALFORMED). Malformed rows are counted **separately** from
>   `skipped`; "unreadable" and "incomplete" send the operator to different fixes.
> - **A failure no longer renders in the success style.** Every `sra_import_msg` went out as
>   `notice ok` + `role=status`, including "not imported". `sra_import_is_error` now selects
>   `notice warn` + `role=alert` (announced immediately, not politely).
> - **`/sra/ssi/load` is bounded and reports** — it did an unbounded `setup.file.read()` then
>   redirected in TOTAL SILENCE on bad JSON. Own cap `_MAX_SETUP_BYTES` = 8 MB, not the 500 MB `.mpp`
>   bound its two siblings use, which here would be a cap in name only.
>
> ## Formula injection — the plan named the WRONG writer
> - **`reports/xlsx.py` is NOT a vector.** Every string is `t="inlineStr"` inside `<is><t>` and no
>   `<f>` element is ever emitted (verified by unzipping a rendered workbook), so Excel shows `=1+1`
>   as text. A test now pins the **absence** of a guard so nobody cargo-cults one on and prefixes a
>   visible apostrophe onto legitimate exhibit text.
> - **`exhibits/csvout.py` IS a vector** and now defuses `= + - @ \t \r` — on **text only**, so a real
>   `-5` float stays the number −5. These CSVs carry **task names straight from the schedule file**:
>   content the tool did not author and, in a delay claim, content an opposing party may have written.
>
> ## ⇢ NEXT — Phase 2 is done, so the UI queue is finally unblocked
> **⇢ TAKE RANK 12's REMAINDER / RANK 13 NEXT**, subject to the three operator decisions below. The
> UI queue has now been displaced by **seven** consecutive out-of-band correctness rounds
> (ADR-0306→0313). Every deferral was individually justified; the pattern is not.
>
> ## ⇢ BLOCKED on operator decisions — do NOT invent answers
> 1. **AXIS-TITLES `PENDING`** — `/margin`'s toolbar needs `margin_dashboard.js` captioned (batch 3b).
> 2. **`NO_SVG_AXES` DOM caption mechanism** — `/workbench`'s `workbench.js`; ADR-0298 records it as
>    *"a separate design decision, deliberately not invented here."*
> 3. **`data-noprint`** — still **zero CSS rules anywhere**, across ten already-merged contract pages.
>
> Everything else in rank 12 is done (ADR-0311 + #486). Then rank 13 (vendored typography) and 14.
> Behind the UI queue: **Phase 3** (CC-01, 74 call sites, Fable-5-Max deep dive; V3 elapsed literals —
> a conformance fix per ADR-0310 but still saved-filter-population-moving) and **Phase 4** (P1–P6,
> measured but unremediated).
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
>
> **Standing rule, from this session's own failures:** do not put a test result in prose unless the
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
