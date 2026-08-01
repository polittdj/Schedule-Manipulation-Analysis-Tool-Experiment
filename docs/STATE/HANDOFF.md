# Handoff — 2026-08-01h (batch 3c-ii: the on-demand SRA panels captioned — AXIS-TITLES COMPLETE; ADR-0330; v1.0.146)

> ## STATUS (current) — **Batch 3c-ii BUILT AND GATED on this tree (ADR-0330): `sra_jcl.js`'s
> football + cost S-curve and `sra_ssi.js`'s S-curve + histogram caption via the ONE shared
> helper (24 → 28 call sites, a DELIBERATE re-baseline, prior 24 entries byte-untouched), and
> the SVG `PENDING` ledger is EMPTY — the recorded AXIS-TITLES completion signal.** The
> football's two corner quadrant %-labels sat EXACTLY in both caption corners; both clamp
> statically out of the bands (`mt+10 → mt+24`, `H−mb−6 → H−mb−20` — the ADR-0303 yield, the
> dwell-precedent static mechanism; live-box remove REJECTED, it would delete a
> by-construction-colliding data label). **The measured pass learned to CLICK, on a serve that
> can chart:** the survey found the 3c-i prerequisite understated — the golden pair carries no
> budgeted cost, so `/sra` there renders NO `#jclRun` (the honest-SCL gate) and no
> `sra_jcl.js` tag at all, and with no Best/Worst spread the SSI S-curve degenerates to ONE
> point. `served_sra` (the `served_margin` precedent) loads a synthetic 4-task cost-loaded
> schedule + `st.sra_bcwc` spread; the new `/sra+run` cell clicks BOTH Run buttons with a
> strict never-suppressed per-panel caption wait + a MIN_CAPTIONS=12 floor (a dead clicked
> panel cannot hide behind the page's self-run captions). The plain `/sra` golden cell stays
> exactly what ADR-0329 measured. FICSM strip + the 5×5 matrices: recorded not-axis-charts
> (decision A1 / ADR-0326's other medium). Neither module is in PAGE_SCRIPTS — no byte-freeze
> digest moved. Caption contrast on `.ssi-svg`'s hardcoded WHITE canvas measured in all four
> themes (console 3.07:1 the slimmest — recorded in the ADR as the first thing a future theme
> would break). Version **1.0.146**, highest ADR **ADR-0330**, wheel + nine installers
> regenerated ONCE after the code landed (bump BEFORE suite, the recorded sequencing).
>
> ## Verification (all read from runs this session)
> Census + freeze suites: **52 passed, 2 skipped** (one skip IS the emptied PENDING's empty
> parametrize; the other the standing path.js INCIDENTAL_SVG skip). The MEASURED visual pass
> (10 pages × 4 themes × 3 scales, caption-vs-every-sibling-text, ≥2px both axes): **1 passed
> in 103.7 s**, zero collisions, KNOWN_COLLISIONS still EMPTY; a 12-combo pre-probe of the
> clicked cell alone: **144 caption renders, zero problems**. Neighbor suites (sra view /
> ssi-web / jcl-web / grid / zero-margin / file-select / chart-callouts / bar-drill /
> accessibility): **122 passed**. **Proved able to fail, watched:** the visual pass dies on
> the strict wait on the pre-caption tree (`TimeoutError: waiting for locator("#ssiCharts
> text.ch-at")`), the census reports both modules unclassified, the freeze counts 24 ≠ 28.
> Statics foreground: ruff "All checks passed!" · format clean (835 files) · mypy --strict
> "no issues in 117 source files" · bandit exit 0 · node --check clean. An ADR-0240
> multi-lens audit (4 finders + adversarial verifiers) ran on the diff; lead-validated
> outcome in SESSION-LOG. Full-suite + installer-lockstep results: see SESSION-LOG (recorded
> after the run completed — a launched run is not a result).
>
> ## ⇢ NEXT
> 1. **Merge the draft PR for this round when CI is green** (branch
>    `claude/polaris-batch-3c-ii-captions-3szmiw`), then:
> 2. **The OR-04 ball stays with the operator:** run
>    `audit/operator-artifacts/collect-ollama-artifacts.ps1` on the deployed box (after one
>    Ask-the-AI question), review, commit outputs + `smoke-results.md` (A–D verdicts).
> 3. **The DOM medium's caption ledger is now the only caption work left:** `DOM_PENDING`
>    (7 modules — drilldown, driving_tiers, findings_drill, ribbon_drill, scorecards,
>    sra_risk, whatif) under ADR-0326's B1 mechanisms, batch-at-a-time like the SVG one.
> 4. Behind: Phase 3 (CC-01 rendering half, 74 sites, Fable 5 Max) · Phase 4 (P1–P6) ·
>    rank 13/14 · OR-03 residuals parked in ADR-0328 (operator's-ear hum acceptance; ogg
>    fallback HELD).
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
> annotation is data-dependent · ADR-0326 notes: /mission's path-evolution tile deliberately
> unmarked; a marked page's caption applies to every tier-scale on it by design.
> · **the /analysis focus→tip family is a measured intermittent** (dismiss AND scroll
> siblings; ≈half of isolated runs fail the 4 s wait on this container) — adjudicated, do NOT
> chase as a regression.
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
> - The 3c-ii captions touch NO engine number: JS presentation + test files only (app.py
>   untouched this round).
> - **The golden pair's cost-LESSNESS is load-bearing** (the JCL honest-requirement gate,
>   pinned by test_jcl_web.py) — never "fix" it by cost-loading the goldens; the clicked
>   visual cell has its own synthetic serve (`served_sra`) for exactly this reason.
>
> ## Hypotheses KILLED — do not re-chase
> Everything in `audit/SRA-PARITY-20260729.md` §7 and the archived lists (ADR-0307 revert ·
> unconditional floor · ADR-0311→0329 items), **plus this round:** "clicking the Run buttons
> on the golden serve is enough for 3c-ii" (the golden pair renders NO #jclRun — the JCL
> panel is cost-gated closed — and its SSI S-curve is a 1-point degenerate; the clicked cell
> NEEDS its own cost-loaded, spread-bearing serve); "the football's corner labels can yield
> via the ADR-0319 live-box REMOVE" (they collide by construction — removal would delete the
> data label every render; the static band-clamp is the recorded mechanism).
>
> ## Harness notes — the traps, one line each
> Run dev tools as `python -m <tool>` (a stale `/root/.local/bin/ruff` shadows pip's).
> **`pip install -e ".[dev]"` before the suite** (bare `PYTHONPATH=src` fails ~200 web tests).
> `pytest --timeout=N` is NOT installed — it exits 0 having run nothing. **Read the tool's own
> summary line** (`cmd | tail; echo $?` reports `tail`'s status). **`pkill -f` with a pattern
> in the killer's own command line kills the killer** (kill by PID). CI can take ~11 min to
> register check runs. `TestClient` follows 303 and CONSUMES one-shot banners
> (`follow_redirects=False`). Parity marker ≈2m38s. Headless Chromium hides scrollbars
> (`ignore_default_args=["--hide-scrollbars"]`). Re-diff after every remote resume. `caplog`
> needs `logger="schedule_forensics.<module>"`. Playwright `bounding_box` is
> viewport-relative. **localStorage is per-ORIGIN** (the visual pass now spans THREE origins —
> land on the target origin before writing theme/scale). Containers RESTART mid-run: statics
> FOREGROUND first, long pytest re-runnable, reinstall pip after every resume. After a
> squash-merge: `git fetch --prune origin && git remote set-head origin -a &&
> git checkout -B <branch> origin/main`. **Version-bump sequencing:** bump pyproject BEFORE
> the full background suite — bump, rebuild wheel+installers, THEN launch. Module-scoped
> chromium suites: a completing upload needs bytes no earlier test loaded (dedup redirects
> home). Never sleep in a sync-Playwright route handler — park the route, resolve from the
> test body. Never `from tests.web...` in a test (CI ModuleNotFoundError) — pin by text.
> **A parse-time-rendering JS module + a later chartframe.js = first-paint crash** — the
> ADR-0316 defer family; check the page's script ORDER before calling any SFChartFrame API.
> **An on-demand panel needs a strict per-host wait AND a caption floor in the visual pass** —
> "some captions rendered" cannot see a dead clicked panel behind a self-running chart.
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
