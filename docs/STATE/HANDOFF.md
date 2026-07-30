# Handoff — 2026-07-30 (OR-02 closed under audit: the callout dismisses and never covers the nav; ADR-0314; v1.0.132)

> ## STATUS (current) — **OR-02 (the DCMA-11 callout bug) is FIXED, Ultracode-audited, and pinned by measured-box tests. Version 1.0.132, highest ADR ADR-0314, wheel + nine installers regenerated.**
> The operator's one sentence hid THREE defects, all measured before fixing (`app.js`, the DCMA
> overview float tip): a FOCUS-shown tip had **no reachable dismissal** (Escape/pointer-away/
> alt-tab all stuck); the nav clamp tested `position === "fixed"` only, so **daylight's sticky
> bar was never avoided** (hit-checked overlap at three sizes); and — the audit's find — the tips
> are **BORN visible** (no inline `display:none` at creation while `.dcma-tip-float` CSS computes
> visible), so every render stacked all 16 over the nav at (0,0), masked only on loads whose
> Gantt auto-scroll fired the scroll-hide. That last one is almost certainly the operator's
> literal *"it returns after I switch pages."*
>
> ## The audit earned its keep — two blockers my own probes could not see
> Ultracode (ADR-0240): 4 dimension reviewers + adversarial verifiers, 12 findings, every one
> lead-re-verified executably. The blockers: (1) the first fix compared the header box against
> `window.innerWidth`, which **includes a classic scrollbar** — a full-width bar then classifies
> as a RAIL and the tip lands off-screen at a **9px sliver**. Headless Chromium HIDES scrollbars
> (all my probes were green); re-measured with `--hide-scrollbars` disabled: real. The shipped
> classifier uses `document.documentElement.clientWidth`. (2) the born-visible stack above.
> Also folded in: overflow **hidden** not auto (a scrollbar on a `pointer-events:none` element is
> a control no input can operate — ADR-0304's own law), an 8px pointermove travel threshold (a
> desk bump must not kill a keyboard-opened tip — ADR-0286's posture), `mark()` hides a different
> previously tracked tip, tip ids + `aria-describedby` (the overview's `role=tooltip` was
> orphaned), and three test-hardening findings.
>
> ## Verification (all read from runs this session)
> `tests/web/test_float_tip_dismiss.py`: **19 passed** (dismissal by Escape/pointer/blur on the
> operator's own DCMA-11 row · tips born hidden via an INSERTION-TIME MutationObserver — post-load
> inspection cannot tell "born hidden" from "scroll-masked" · a 4-theme × 4-viewport measured-box
> sweep incl. the 600×700 burger header, counting only cells that actually measured a tip).
> **Proved able to fail:** on unfixed code the dismissal test, born-hidden test, and daylight cell
> fail (3 failed, 8.31s, read); fixed code 19 passed in 131s. All 136 existing app.js-content
> tests green. Local vendored-chromium posture (CI's browser job deliberately runs only the r11
> contract file). Full-suite figure for THIS tree: owed by the next gate run — do not quote one.
>
> ## ⇢ NEXT
> 1. **The three operator decisions stay OPEN and briefed** — `docs/STATE/DECISION-BRIEFS-20260730.md`
>    (A: batch 3b scope · B: NO_SVG_AXES caption mechanism · C: `data-noprint`). Asked twice,
>    unanswered twice — ask from the briefs, do NOT re-research, do NOT invent answers.
> 2. **Un-gated queue:** OR-01 (roll-up titles), OR-03 (Launch Sequence motion + ≥1-min hum),
>    `/analysis` panel 5's two ⛶, `/evolution`'s target-blind export bar, `/resources` X-caption
>    collision, `/performance` first-paint race. Then rank 13/14 behind rank 12's gated remainder.
> 3. Behind the UI queue: **Phase 3** (CC-01 rendering half, 74 call sites, Fable-5-Max deep dive;
>    V3 elapsed literals) and **Phase 4** (P1–P6, measured but unremediated).
>
> ## Still carried (unchanged identifiers, nothing lost)
> **CC-01** (H2a) — import half closed by ADR-0312, **rendering half open**, 74 call sites; its two
> named residuals are ADR-0312's inclusive boundary (`start_tod + per_day == 1440` renders an
> exact-multiple offset at 00:00 of the FOLLOWING date) and `Calendar` still having no shift-start
> field · **CC-05** (H5) negative sub-day slack floor, oracle-gated · **V3** (H4) elapsed literals,
> `engine/msp_filters.py` the sole violator of a convention the repo already follows eight times ·
> the **legacy `/sra` cross-basis defect** (`_build_result` reads a full-duration deterministic
> against a remaining-duration sample, no realignment; reaches `/api/sra`, the SRA report,
> `sra_conclusions`, and `scorecards.reserve_recommendation`) · **a committed SSI export contradicts
> ADR-0307's Best-Case rule** (Project5 shows the pre-0307 ratios; ADR-0307 stands for the artifact
> we match) · `resume` is read from **MSPDI only** · the forward pass still packs **completed** work
> from `project_start` (724 tasks, median −1458 d vs stored actuals; Phase 7) · **per-task calendars
> are an out-of-domain pairing ADR-0312 does not reach** · several importer warnings (notably the
> **assumed** calendar, +25 % on duration-days when a 10-hour calendar fails to resolve) belong on
> the page via `Schedule.import_notes` and have not migrated.
>
> ## SRA parity — CLOSED, and the traps that stay shut
> ADR-0309 (#483/#484): det percentile **40.70 % → 6.65 %** (SSI **5.75 %**), σ **125.5 → 65.5** cal d
> (SSI **64.744**, 1.2 %), mean **+26 → +109** (SSI **+111.45**), P10/P50/P80/P90 within
> **7/1/0/3** days, all five calibration seeds passing.
> - **The anchor is CONDITIONAL on stored data — MS Project's own `<Resume>` — never a blanket
>   data-date floor.** ADR-0108's two reverts were both unconditional floors; EVM1 UID 18 has
>   `resume == stop` and must not move.
> - **A floor built from the STORED remaining destroys the Monte-Carlo's upside variance**
>   (`det_pctile = 100 %`, σ 20.3). It must follow `duration_overrides`. Do not "simplify" it back.
> - **Do NOT chase SSI's `Mean Date` / `Standard Deviation` cells (47322 / 107.8198)** — computed
>   over the 245 DISTINCT dates with `Occurrences` dropped.
>   `test_the_summary_cells_are_not_the_parity_target` pins the trap shut.
>
> ## Hypotheses KILLED — do not re-chase
> Everything in `audit/SRA-PARITY-20260729.md` §7, **plus**: reverting ADR-0307's Best-Case rule;
> an **unconditional** data-date floor (ADR-0108's two reverts, superseded by ADR-0309); "the four
> Setup pages have no chapter kicker" (ADR-0311); **"the xlsx writer needs a formula-injection
> guard"** (ADR-0313 — it emits no `<f>`; the CSV sibling was the real vector); and **"OR-02 is in
> the hint/tooltip layer"** (the intake notes guessed `hints.js`/`vizhints.js` — the callout is
> app.js's DCMA float tip; measured, ADR-0314).
>
> ## Harness notes — the traps, one line each
> Run dev tools as `python -m <tool>` (a stale `/root/.local/bin/ruff` shadows pip's).
> **`pip install -e ".[dev]"` before the suite** (bare `PYTHONPATH=src` fails ~200 web tests).
> `pytest --timeout=N` is NOT installed — it exits 0 having run nothing. `cmd | tail; echo $?`
> reports `tail`'s status. CI can take ~11 min to register check runs (`total_count: 0` = "not
> yet"). `TestClient` follows 303 and CONSUMES one-shot banners (`follow_redirects=False`).
> Full `pytest -q` ≈ 14 m; `pytest -m parity` ≈ 40 s. Wheel: `--outdir dist/wheel`, ONCE, after
> all code lands. **NEW: headless Chromium hides scrollbars** — any geometry that depends on
> viewport width MUST also be probed with `ignore_default_args=["--hide-scrollbars"]`; a
> classic-scrollbar browser (the operator's Windows default) is ~15px narrower than headless
> thinks. **A remote-session resume can silently revert / flip uncommitted working-tree files** —
> diff the tree against your last known state after every resume before trusting it.
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
