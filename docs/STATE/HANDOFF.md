# Handoff — 2026-08-01g (batch 3c-i: sra + volatility join the caption convention; ADR-0329; v1.0.145)

> ## STATUS (current) — **Batch 3c-i BUILT AND GATED on this tree (the AXIS-TITLES queue's
> remaining-four, first half; ADR-0329): `sra.js`'s CDF + histogram and `volatility.js`'s
> churn / flow / area / dwell all caption via the ONE shared helper (18 → 24 call sites, a
> DELIBERATE re-baseline, prior 18 entries byte-untouched).** Two hand-rolled quasi-captions
> RETIRED into the helper (flow's "joined ↑ / left ↓…" annotation; dwell's centred "versions
> on the critical path"). Every collision closed where caused (ADR-0303, data yields): the CDF
> det-finish label moved out of the Y-caption band (padT+24); rotated date/version ticks yield
> to the X caption via the ADR-0319 LIVE-box remove (local `yieldTicksToCaption` per module,
> 2px margin, apollo mono covered); dwell count labels statically clamped out of BOTH bands.
> **Recorded NOT-axis-charts (decision A1, in the ADR):** sra's two tornados · volatility's
> gauge, heatmap, two leaderboards, strips, ribbon; sra_ssi's 5×5s are natively-labeled HTML
> tables (other medium). **`/volatility` joined the ADR-0316 `defer` family** — the measured
> pass caught volatility.js (parse-time renderer, loads before chartframe.js) throwing
> `SFChartFrame is not defined` on the new call: one word in app.py, guard rejected per the
> recorded precedent. `/sra` + `/volatility` joined the visual PAGES matrix (sra self-runs
> /api/sra ≈1.4 s on the goldens; volatility charts from its blob). PAGE_SCRIPTS volatility
> digest deliberately re-baselined (0d38b34e… → 67a62558…). **3c-ii deliberately split, not
> skipped:** `sra_jcl.js` + `sra_ssi.js` stay in PENDING — their charts render only on a Run
> click, so the visual harness must learn to click first. Earlier this session: **PR-10 (#503,
> OR-03, ADR-0328) and #504 (session close + the OR-04 collection kit) both MERGED** by the
> operator. Version **1.0.145**, highest ADR **ADR-0329**, wheel + nine installers regenerated
> ONCE after the code landed (bump BEFORE suite, the recorded sequencing).**
>
> ## Verification (all read from runs this session)
> Census + freeze suites: **54 passed** (module classification · 24-site count+uniqueness ·
> the load-bearing file+digest equality · PAGE_SCRIPTS). The MEASURED visual pass
> (9 pages × 4 themes × 3 scales, caption-vs-every-sibling-text, ≥2px both axes): **1 passed
> in 86 s**, zero collisions, KNOWN_COLLISIONS still EMPTY. Neighbor suites (sra view /
> ssi-web / grid / zero-margin / file-select · bar-drill · accessibility): **99 passed**.
> Installer lockstep vs the fresh 1.0.145 wheel: **52 passed**. **Proved able to fail,
> watched:** the three ledgers FAIL on the stashed pre-change tree (census unclassified ·
> 24 ≠ 18 · volatility byte-freeze), and the visual pass itself was watched failing LIVE on
> the pre-`defer` tree ("no captions rendered" × every /volatility cell — the failure that
> exposed the defer find). Statics foreground: ruff "All checks passed!" · format clean (835
> files) · mypy --strict "no issues in 117 source files" · bandit exit 0 · node --check clean.
> Full-suite result: see SESSION-LOG (recorded after the run completed — a launched run is
> not a result).
>
> ## ⇢ NEXT
> 1. **Merge the draft PR for this round when CI is green** (branch
>    `claude/polaris-pr10-or03-motion-uzgvc0`), then:
> 2. **Batch 3c-ii** — `sra_jcl.js` + `sra_ssi.js`: teach the visual harness to CLICK their
>    Run buttons (both fetch and render on demand), then caption the football (its corner
>    quadrant %-labels sit exactly in BOTH caption corners — they must yield), the cost
>    S-curve, and the SSI S-curve + histogram; the FICSM strip is a labeled bar strip →
>    recorded not-axis-chart. PENDING → empty closes AXIS-TITLES for good.
> 3. **The OR-04 ball stays with the operator:** run
>    `audit/operator-artifacts/collect-ollama-artifacts.ps1` on the deployed box (after one
>    Ask-the-AI question), review, commit outputs + `smoke-results.md` (A–D verdicts).
> 4. Behind: the 7-module `DOM_PENDING` ledger · Phase 3 (CC-01 rendering half, 74 sites,
>    Fable 5 Max) · Phase 4 (P1–P6) · rank 13/14 · OR-03 residuals parked in ADR-0328
>    (operator's-ear hum acceptance; ogg fallback HELD).
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
> - The 3c-i captions touch NO engine number: JS presentation + one script-tag attribute only.
>
> ## Hypotheses KILLED — do not re-chase
> Everything in `audit/SRA-PARITY-20260729.md` §7 and the archived lists (ADR-0307 revert ·
> unconditional floor · ADR-0311→0328 items), **plus this round:** "the four PENDING modules
> can ship as one measured batch" (jcl/ssi render only on Run clicks — unmeasurable captions
> until the harness clicks; split recorded, not skipped); "volatility.js can call the helper
> bare like the fetch-rendered modules" (it draws at PARSE time before chartframe.js loads —
> the ADR-0316 defer family, third member); "tornados/gauges/leaderboards need captions"
> (no axis scale to name — decision A1, recorded in ADR-0329).
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
> viewport-relative. **localStorage is per-ORIGIN.** Containers RESTART mid-run: statics
> FOREGROUND first, long pytest re-runnable, reinstall pip after every resume. After a
> squash-merge: `git fetch --prune origin && git remote set-head origin -a &&
> git checkout -B <branch> origin/main`. **Version-bump sequencing:** bump pyproject BEFORE
> the full background suite — bump, rebuild wheel+installers, THEN launch. Module-scoped
> chromium suites: a completing upload needs bytes no earlier test loaded (dedup redirects
> home). Never sleep in a sync-Playwright route handler — park the route, resolve from the
> test body. Never `from tests.web...` in a test (CI ModuleNotFoundError) — pin by text.
> **A parse-time-rendering JS module + a later chartframe.js = first-paint crash** — the
> ADR-0316 defer family; check the page's script ORDER before calling any SFChartFrame API.
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
