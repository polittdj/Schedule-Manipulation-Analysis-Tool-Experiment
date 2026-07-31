# Handoff — 2026-07-31 (roll-up titles state the aggregation rule; ADR-0321; v1.0.139)

> ## STATUS (current) — **PR-7 of the approved queue BUILT AND FULLY GATED on this tree: OR-01 roll-up titles — every Portfolio ledger heading states the rule it applied (latest vs average), the NEW "Avg DCMA-14 passes — all included versions" column is the view-layer mean of the engine's own per-version pass counts, and the per-file surfaces (home manifest · dashboard cards · /card) name Site/Company · data date · computed finish · effective margin · DCMA-14 per file. Version 1.0.139, highest ADR ADR-0321, wheel + nine installers regenerated. #495 (ADR-0320) MERGED as `aef69db` by the operator.**
> Per the plan's PR-7 row: `_portfolio_body`'s three headline headings gained "— latest
> version" (Latest data date already stated its rule) and the ONE aggregate column arrived —
> "Avg DCMA-14 passes — included, solvable versions", VIEW-LAYER arithmetic only (mean of
> `VersionSummary.dcma_pass` over exactly that pool via the cached `summary_for` tier; never
> `analysis_for`), cell `<mean:.1f> of 14 · N versions` with N the pool size so a solvability
> drop is visible in the figure, empty pool → the "—" literal (ADR-0219 M2), never 0.0. The
> takeaway discloses BOTH bases. Home manifest rows gained the five per-file columns —
> dates/margin from the summary tier, the DCMA cell from the PARITY-AWARE card tier so one
> page never shows two verdicts for one file; `/api/dashboard` cards gained exactly `site` +
> `margin_days` (dashboard.js renders them; unsolvable cards degrade as before with both
> null); `/card` gained the same two KPI cards; `/margin/confirm` now clears `st.dash_cards`
> beside `st.summaries` (the memo bakes `margin_days`; without it the cards served a stale
> pre-confirm margin — live-reproduced). New headings entered `_TERMS` in all four languages
> (plus "Latest data date" / "Effective margin" / invariant "DCMA-14"). **The three
> `/api/dashboard` golden SHAs were DELIBERATELY re-baselined via their own `_dashboard_sha`
> path (ADR-0321 named at the pins): the only delta is the two added keys, proved at row
> level by the new test's full key-set + engine-verbatim value pins.** ADR-0240 review round
> (four-lens adversarial fan-out + per-finding refutation) ran on the draft diff; every
> confirmed finding is fixed in this tree, and the parity-blind summary tier + the unscoped
> manifest Activities cell are recorded residuals in ADR-0321.
>
> ## Verification (all read from runs this session)
> New `tests/web/test_portfolio_rollup_titles.py`: **15 passed** (non-degeneracy guard —
> distinct 5/9/5 pass counts AND a nonzero 2.0 d engine margin; heading-row pin; takeaway
> bases; the average equals the mean of ENGINE pass counts; mixed-solvability pool disclosed
> in the cell — 4 included, "· 3 versions"; "—" when nothing solves; exclusion shifts mean
> AND stated N, reversibly; home-manifest fields engine-verbatim + unsolvable keeps "—" never
> "0 pass"; manifest DCMA cell EQUALS the same-page health cards; margin-confirm reaches the
> cards immediately; card key-set + value pins; dashboard.js stat pins; /card label+value
> adjacent; i18n completeness). **Proved able to fail:** `src/` stashed → **13 failed / 2
> passed** (the passers are the engine-oracle fixture guard and the em-dash non-regression
> pin) → popped — the margin-confirm regression test FAILS on main, catching the live stale-
> memo defect. Golden re-pins + memo + status-trim: **23 passed**. Neighbors (portfolio
> shell/panelkit · home shell · landing · card view · i18n · coverage app ×2 · project scope
> · global filter · presentation fixes · cache tiers · drill ×2 · axis titles): **169 passed,
> 1 skipped** (known INCIDENTAL_SVG). Statics read: ruff 0.16.1 check clean · format clean ·
> mypy --strict "no issues in 117 source files" · bandit exit 0 · node --check clean. Full
> suite on the final tree (post-review-fixes, post-regeneration): **3173 passed, 1 skipped,
> 0 failed (1190 s)** — installers in lockstep, no flake. An
> earlier pre-review-fix full run read 4 failed / 3165 passed / 1 skipped (1305 s) — the four
> were the installer-lockstep tests on then-stale artifacts, and `test_float_tip_dismiss`
> (ADR-0320's load-dependent flake) did NOT fail that run.
>
> ## ⇢ NEXT
> 1. **Merge PR-7 when CI is green** (draft PR from `claude/polaris-pr7-or01-rollup-5lc2ba`),
>    then the queue (`docs/STATE/PLAN-20260730.md`, decisions A1 · B1 · C1 recorded — do NOT
>    re-ask): **PR-8 AXIS-TITLES 3b-i `margin_dashboard` per A1 (M)** → PR-9 rank-12
>    toolbar/read-me + B1 caption mechanism (M–L) → PR-10 OR-03 launch motion + synthesized
>    hum (M–L). margin.js's vocabulary conversion stays a later round.
> 2. **OR-04 operator park artifacts stay open** (`audit/VERIFICATION-REPORT-ollama-lifecycle.md`
>    §8): #1 `where ollama` · #3 the `keep_alive:0`-vs-`OLLAMA_KEEP_ALIVE=-1` probe (severity
>    fork) · #5 runner PPID + instance count · #4 the model-identity manifest — plus the
>    four-scenario smoke script from #490's PR body on the deployed build (≥ v1.0.133).
> 3. Behind the queue: **Phase 3** (CC-01 rendering half, 74 call sites, Fable-5-Max deep dive;
>    V3 elapsed literals) and **Phase 4** (P1–P6, measured but unremediated); rank 13/14.
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
> the page via `Schedule.import_notes` and have not migrated · **ADR-0320 residuals, recorded not
> chased:** the Focus form still drops `cf_a`/`cf_b` (the what-if pair resets to its default on
> refocus), and the trace-options form's pre-existing `tier=off` keep stays.
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
> guard"** (ADR-0313 — it emits no `<f>`; the CSV sibling was the real vector); **"OR-02 is in
> the hint/tooltip layer"** (ADR-0314 — the callout is app.js's DCMA float tip); **an image-name
> sweep of the model runner** (ADR-0315 — `llama-server` is llama.cpp's generic binary, the tool's
> own OpenAI-compat backend runs one; pid-rooted tree-kill instead, exclusion pinned by test);
> **asserting** that a per-request `keep_alive:0` overrides `OLLAMA_KEEP_ALIVE=-1` (UNVERIFIED,
> audit F-13 — park #3 decides; never state it in either direction); **a runtime guard on
> `performance.js:472`** (ADR-0316 — `defer` makes it unreachable and every digest pin would
> re-baseline for nothing); **asserting a fixed-overlay toggle via `bounding_box` Y** —
> viewport-relative and scroll-polluted by the click's own `scrollIntoView`; assert the
> scroll-invariant size axes instead (ADR-0317); and **"the session target and `?target=` are
> equivalent for /evolution exports"** (ADR-0320 — the session target truncates the POPULATION
> via `SessionState.scope()`; `?target=` is a view focus; the export mirrors the page in both
> states, it never equates them).
>
> ## Harness notes — the traps, one line each
> Run dev tools as `python -m <tool>` (a stale `/root/.local/bin/ruff` shadows pip's).
> **`pip install -e ".[dev]"` before the suite** (bare `PYTHONPATH=src` fails ~200 web tests).
> `pytest --timeout=N` is NOT installed — it exits 0 having run nothing. `cmd | tail; echo $?`
> reports `tail`'s status. CI can take ~11 min to register check runs (`total_count: 0` = "not
> yet"). `TestClient` follows 303 and CONSUMES one-shot banners (`follow_redirects=False`).
> Full `pytest -q` ≈ 14 m; `pytest -m parity` ≈ 40 s. Wheel: `--outdir dist/wheel`, ONCE, after
> all code lands. **Headless Chromium hides scrollbars** — any geometry that depends on viewport
> width MUST also be probed with `ignore_default_args=["--hide-scrollbars"]`. **A remote-session
> resume can silently revert / flip uncommitted working-tree files** — diff the tree after every
> resume. `caplog` here needs `logger="schedule_forensics.<module>"` (the redaction layer stops
> propagation), and the autouse `SF_CACHE_DIR` fixture isolates the Ollama engagement marker per
> test for free. A foreground wait on a background run: `tail --pid=<pid> -f /dev/null` (no
> sleep, no polling); target the real `python -m pytest` pid, not the wrapper shell.
> Playwright `bounding_box` is viewport-relative — a click that scrolls (its own
> `scrollIntoView`) shifts Y for free; measured-box assertions use width/height/x.
> This queue's containers RESTART repeatedly mid-run — every background process (gates,
> workflows) dies with it and pip installs vanish: re-diff the tree AND reinstall deps after
> every resume, run the statics FOREGROUND first so their results are locked in, and treat the
> long pytest as re-runnable rather than assume it survived.
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
