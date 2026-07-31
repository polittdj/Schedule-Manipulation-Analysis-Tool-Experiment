# Handoff — 2026-07-31 (the /evolution exports honor the page state; ADR-0320; v1.0.138)

> ## STATUS (current) — **PR-6 of the approved queue BUILT AND FULLY GATED on this tree: the /evolution exports honor the banner's promise (trace options + focus), state their applied scope, and the page's forms stop dropping state. Version 1.0.138, highest ADR ADR-0320, wheel + nine installers regenerated. #494 (ADR-0319) MERGED as `b3e4286` by the operator.**
> `app.py` only, per the plan's PR-6 row: the ⤓ bar now carries the LIVE query string
> (`_evolution_state_qs`, urlencode, defaults emit nothing — bare path byte-identical);
> `export_evolution` gained the SAME Query params as `/api/evolution`, resolves the focus with
> the page's exact URL-first/session-fallback rule, and routes through `_optioned_versions`;
> headings state the APPLIED scope on two carriers (TableSet-title suffix → the Word H0; a
> prepended "Applied scope" sheet → the workbook, since xlsx never renders a TableSet title) —
> and a chosen `tier` is DISCLOSED as not applied (gated by `_EVO_TIER_SELECT` membership,
> which is also the injection gate) because the tier stepper never filters these tables. The
> drop-nothing rule (`_keep_hidden`): the Focus form keeps `ignore_*`, the what-if picker keeps
> `target`/`tier`/`ignore_*`, the clear-focus link keeps tier+options while emitting the
> explicit empty `target=`. `_trace_option_names` is now the ONE source the banner and the
> export headings both read. **Load-bearing finding (ADR-0320):** the session target is a
> POPULATION scope (`SessionState.scope()` truncates every version to the target's driving
> subtree inside `_solvable_versions`) while `?target=` is a VIEW focus on the full population
> — the page renders those states differently and the export now MIRRORS the page in both;
> they are not equivalent and must never be pinned as such.
>
> ## Verification (all read from runs this session)
> New `tests/web/test_evolution_export_options.py`: **14 passed** (bar qs live + bare default;
> pure-logic dates replace stored `2025-01-2x` under `ignore_leveling`; URL focus + session
> mirror; scope sheet + docx H0 suffix, absent by default; tier disclosed not applied; forms +
> clear link carry state; explicit-default URLs byte-identical). **Proved able to fail:**
> `app.py` stashed → **9 failed / 5 passed** (the five are the deliberate non-regression pins)
> → popped. Neighbors (evolution view · family-B unify · path options · coverage app + extra ·
> mission ×2 · coverage misc + new file): **127 passed**. Statics read: ruff 0.16.1 clean ·
> format clean (816 files) · mypy --strict "no issues in 117 source files" · bandit exit 0 ·
> node --check clean. Export-vs-page strictness parity read: non-int `ignore_*` → 422 on BOTH;
> garbage `target` / `tier=critical` → 200 on both. **One freeze pin re-baselined per its own
> prescribed path** (ADR-0320 named in the table): the r11 what-if-picker form pin — the
> drop-nothing hidden input carrying the fixture's RESOLVED session focus grew it 803 → 847;
> old md5 `25dd…` → new `3b6af0bf…`, computed from a live fixture-identical render; the two
> untouched `/evolution` form pins (802/743) prove nothing else moved. Full suite on this
> tree: **3157 passed, 1 skipped, 1 failed (837 s)** — the failure is `test_float_tip_dismiss`
> (ADR-0314's browser suite, `/analysis` page this diff never touches) timing out its 4 s
> tip-SHOW wait under full-suite load only: **18/18 rerun alone** and **54/54 in a 3× parallel
> probe on the PRISTINE stashed tree** (all read). Load-dependent, pre-existing, CI
> arbitrates; if CI reproduces it, its timing posture gets its own fix — never a weakened
> contract.
>
> ## ⇢ NEXT
> 1. **Merge #PR-6 when CI is green** (draft PR from `claude/polaris-schedule-planning-resume-8oosjw`),
>    then the queue (`docs/STATE/PLAN-20260730.md`, decisions A1 · B1 · C1 recorded — do NOT
>    re-ask): **PR-7 OR-01 roll-up titles (M)** → PR-8 AXIS-TITLES 3b-i `margin_dashboard` per
>    A1 (M) → PR-9 rank-12 toolbar/read-me + B1 caption mechanism (M–L) → PR-10 OR-03 launch
>    motion + synthesized hum (M–L). margin.js's vocabulary conversion stays a later round.
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
> **NEW:** this session's container RESTARTED repeatedly mid-run — every background process
> (gates, workflows) dies with it and pip installs vanish: re-diff the tree AND reinstall
> deps after every resume, run the statics FOREGROUND first so their results are locked in,
> and treat the long pytest as re-runnable rather than assume it survived.
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
