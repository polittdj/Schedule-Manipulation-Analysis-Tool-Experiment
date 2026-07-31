# Handoff — 2026-07-31 (the /resources period labels yield to the measured caption; ADR-0319; v1.0.137)

> ## STATUS (current) — **PR-5 of the approved queue SHIPPED: the last measured caption collision on a shipped chart page is CLOSED, and `/resources` joined the four-theme visual pass. Version 1.0.137, highest ADR ADR-0319, wheel + nine installers regenerated. #493 (ADR-0318) MERGED as `e29a155` by the operator.**
> The debt round 10 recorded: after the `defer` made the histogram paint on load, the visual
> pass measured the X caption "Period (month commencing)" parked over the last 40°-rotated
> period tick labels in 8 of 12 theme × scale combos (console@1 ~36×2 px per label; apollo@1
> ~40×4 px — the mono font's wider glyphs). Shipped per ADR-0303's law, applied where the
> collision is caused: `resources.js` now runs a **measured yield** after the SVG lands in the
> DOM — it reads the X caption's LIVE box (`text.ch-at[text-anchor=end]`) and removes any
> rotated period label within 2 px of it. The caption never moves (standing requirement 5);
> apollo's wider corner reserves itself by construction; a hidden/unmeasurable box skips the
> yield rather than shredding the labels; the yielded bucket keeps its full tooltip (the label
> is presentation, the bar is the data). Tick-cadence thinning was rejected (degrades every
> label to protect one corner). Freeze bookkeeping per each pin's own prescribed path: the
> 16-site census untouched (the yield sits BELOW the call site — line 243 and every digest
> unchanged); the r10 whole-file `resources.js` digest refreshed deliberately with ADR-0319
> named, while its load-bearing pins (call-site block digest + both caption strings) prove the
> `axisTitles` call byte-identical.
>
> ## Verification (all read from runs this session)
> `tests/web/test_axis_titles_visual.py` now walks SIX pages (`/resources` added per the file's
> own protocol note, which now records the closure): the 12-combo measured pass is green.
> Focused suites (visual pass + r10 resources contract + r11 census + axis-titles ledger):
> **80 passed, 1 skipped**. **Proved able to fail:** src stashed → the visual pass reports the
> original collisions ("overlaps 2027-08 by 20x2px", "overlaps 2027-09 by 43x2px") and exits 1
> (read) → popped. `ruff` (0.16.1, CI-matched) + format + `mypy --strict` (117 files) +
> `bandit` exit 0 + `node --check` clean; wheel + nine installers regenerated. **Full suite on
> THIS tree (read): 3144 passed, 1 skipped, exit 0, in 886 s** (browser-marked tests included).
>
> ## ⇢ NEXT
> 1. **The approved queue** (`docs/STATE/PLAN-20260730.md` — decisions A1 · B1 · C1 recorded;
>    do NOT re-ask): **PR-6 `/evolution` exports honor trace options (M)** → PR-7 OR-01
>    roll-up titles (M) → PR-8 AXIS-TITLES 3b-i `margin_dashboard` per A1 (M) → PR-9 rank-12
>    toolbar/read-me + B1 caption mechanism (M–L) → PR-10 OR-03 launch motion + synthesized
>    hum (M–L). margin.js's vocabulary conversion stays a later round (the trends pin names it
>    as the only legacy carrier).
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
> guard"** (ADR-0313 — it emits no `<f>`; the CSV sibling was the real vector); **"OR-02 is in
> the hint/tooltip layer"** (ADR-0314 — the callout is app.js's DCMA float tip); **an image-name
> sweep of the model runner** (ADR-0315 — `llama-server` is llama.cpp's generic binary, the tool's
> own OpenAI-compat backend runs one; pid-rooted tree-kill instead, exclusion pinned by test);
> **asserting** that a per-request `keep_alive:0` overrides `OLLAMA_KEEP_ALIVE=-1` (UNVERIFIED,
> audit F-13 — park #3 decides; never state it in either direction); **a runtime guard on
> `performance.js:472`** (ADR-0316 — `defer` makes it unreachable and every digest pin would
> re-baseline for nothing); and **asserting a fixed-overlay toggle via `bounding_box` Y** —
> viewport-relative and scroll-polluted by the click's own `scrollIntoView`; assert the
> scroll-invariant size axes instead (ADR-0317).
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
> **NEW:** Playwright `bounding_box` is viewport-relative — a click that scrolls (its own
> `scrollIntoView`) shifts Y for free; measured-box assertions use width/height/x.
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
