# Handoff — 2026-08-01f (PR-10 MERGED; the OR-04 collection kit banked; ADR-0328; v1.0.144)

> ## STATUS (current) — **PR-10 (#503, OR-03 launch motion + the synthesized Boot Audio Hum,
> ADR-0328, v1.0.144) MERGED by the operator as `839c659`** — CI fully green on the merged head
> (all six checks; the one CI-only failure, a `from tests.web...` import that resolves locally
> but not on the runner, was fixed by pinning `_AUTOPLAY_JS` by TEXT). **This round then banked
> the OR-04 §8 park list as a turnkey collection kit** (PR #504, docs/tests/tooling only — no
> runtime code, no version change): `audit/operator-artifacts/` is now a real folder holding
> the deposit-contract README (the six §8 slots by filename + the four-scenario ADR-0315 smoke
> A–D brought in-repo from #490's PR body + the review-before-commit / no-schedule-content
> note) and `collect-ollama-artifacts.ps1` — ONE command on the deployed Windows box that runs
> probes §8-1/2/3/5 (+4's manifest search) read-only and loopback-only, never invoking
> `ollama list`/`ollama run` (the audit's DON'T), writing outputs beside itself for a web-UI
> commit. The audit's human gate is unchanged: NO lifecycle implementation until the operator
> deposits the artifacts — the kit only makes the gate one command wide. Highest ADR stays
> **ADR-0328**; version stays **1.0.144** (nothing packaged changed; wheel + installers NOT
> rebuilt, correctly).
>
> ## Verification (all read from runs this session)
> `tests/test_operator_kit.py` (new, 6 tests): kit exists where the audit points (two-sided
> contract check against §8's own text) · README names all six deposit slots + the A–D smoke +
> the commit-safety note · the collector's CODE lines never invoke `ollama list`/`ollama run`
> (prose-comment-safe check) · loopback-only (every URL in the script starts
> `http://127.0.0.1`) · read-only (no taskkill/Stop-Process/Start-Process/Remove-Item/
> Stop-Service) · each §8 probe present (where.exe · /api/ps · keep_alive=0 + /api/generate ·
> the F-18 sha · Win32_Process llama-server.exe · instance count · the 10 s wait). **Proved
> able to fail, watched: all 6 FAIL with the kit stashed; 6 passed restored.** Guards suite
> with it: **74 passed**. state-docs guard **4 passed**. Statics: ruff "All checks passed!" ·
> format clean · mypy --strict "no issues in 117 source files". Prior rounds' full-suite +
> CI-green record: see SESSION-LOG 2026-08-01e entries.
>
> ## ⇢ NEXT
> 1. **Merge the draft PR #504** (session close + the OR-04 kit; docs/tests/tooling only) when
>    CI is green.
> 2. **The OR-04 ball is with the operator:** on the deployed box, run
>    `audit/operator-artifacts/collect-ollama-artifacts.ps1` right after one Ask-the-AI
>    question, review the outputs, commit them to the same folder via the web UI (plus
>    `smoke-results.md` for the A–D verdicts). Those artifacts settle F-12/F-13/F-15/F-16/
>    F-17/F-18 and re-open the lifecycle work if anything contradicts ADR-0315's shipped fix.
> 3. Behind the gate: SVG batch 3c (sra/sra_jcl/sra_ssi/volatility; tornados recorded
>    not-axis-charts per A1) · the 7-module `DOM_PENDING` ledger · Phase 3 (CC-01 rendering
>    half, 74 sites, Fable 5 Max) · Phase 4 (P1–P6) · rank 13/14.
> 4. OR-03 residuals stay parked in ADR-0328: operator's-ear acceptance of the hum on the
>    deployed build (vendored-ogg fallback HELD) · /example → fetch path only if its at-unload
>    cut ever matters · cross-page audio out of scope by the navigation boundary.
> 5. ADR-0327 residuals unchanged (a /export standards workbook; analysis-workbook makeup/
>    status/constraint sheets for /card's pivots).
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
> annotation is data-dependent (data yields, never the caption) · ADR-0326 notes: /mission's
> path-evolution tile deliberately unmarked; a marked page's caption applies to every
> tier-scale on it by design (same schedule-date axis).
> · **the /analysis focus→tip family is a measured intermittent** (test_float_tip_dismiss
> AND its scroll sibling; ≈half of isolated runs fail the 4 s focus→tip wait on this
> container; byte-identical no-target /analysis render across trees) — an OR-02-adjacent
> hardening item, mechanism undetermined. Adjudicated: do NOT chase as a regression.
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
>
> ## Hypotheses KILLED — do not re-chase
> Everything in `audit/SRA-PARITY-20260729.md` §7 and the archived lists (ADR-0307 revert ·
> unconditional floor · ADR-0311→0328 items — incl. this round's: an audio asset / seam-mixed
> loop; onchange priming; a JS orbit), **plus this round:** "the §8 park list has an in-repo
> implementation half" (it does NOT — every §8 item runs on the operator's deployed box; the
> in-repo share was exactly the collection kit + smoke doc, now done) and "`from tests.web...`
> imports are fine in tests" (local-only sys.path luck; pin cross-module invariants by TEXT).
>
> ## Harness notes — the traps, one line each
> Run dev tools as `python -m <tool>` (a stale `/root/.local/bin/ruff` shadows pip's).
> **`pip install -e ".[dev]"` before the suite** (bare `PYTHONPATH=src` fails ~200 web tests).
> `pytest --timeout=N` is NOT installed — it exits 0 having run nothing. `cmd | tail; echo $?`
> reports `tail`'s status — **read the tool's own summary line**. **`pkill -f` with a pattern
> in the killer's own command line kills the killer** (kill by PID). CI can take ~11 min to
> register check runs. `TestClient` follows 303 and CONSUMES one-shot banners
> (`follow_redirects=False`). Parity marker ≈2m38s (ADR-0322 perf addendum). Headless Chromium
> hides scrollbars (`ignore_default_args=["--hide-scrollbars"]` shows them). A remote-session
> resume can silently revert working-tree files — re-diff after every resume. `caplog` needs
> `logger="schedule_forensics.<module>"`. Playwright `bounding_box` is viewport-relative.
> **localStorage is per-ORIGIN** (second served app instance: write theme/scale AFTER landing
> on its origin). Containers RESTART mid-run: statics FOREGROUND first, long pytest
> re-runnable, reinstall pip after every resume. After a squash-merge: `git fetch --prune
> origin && git remote set-head origin -a && git checkout -B <branch> origin/main`.
> **Version-bump sequencing:** bump pyproject BEFORE the full background suite starts — bump,
> rebuild wheel+installers, THEN launch. In a MODULE-scoped chromium suite, a completing
> upload must use bytes no earlier test loaded (byte-identical dedup redirects home). **Never
> sleep inside a sync-Playwright route handler** (event-loop freeze) — park the route object,
> resolve it from the test body. **Never `from tests.web...` in a test** — importable locally,
> ModuleNotFoundError on CI; pin by text.
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
