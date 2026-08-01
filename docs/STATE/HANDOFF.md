# Handoff — 2026-08-01e (PR-10: OR-03 launch motion + the synthesized Boot Audio Hum; ADR-0328; v1.0.144)

> ## STATUS (current) — **PR-10 BUILT AND GATED on this tree (OR-03, PLAN-20260730 row 10 —
> decisions executed as recorded, none re-asked): the Launch Sequence gains CSS-only orbiting
> craft dots around the (untouched) spinner and a SYNTHESIZED WebAudio Boot Audio Hum — no
> asset ships anywhere.** New `static/launch_audio.js` (shuffled-pitch-bag swell scheduler over
> an 8-pitch A-rooted set + a detuned two-oscillator bed; generative ⇒ no loop point ⇒ no seam;
> every gain move is a linearRamp; `FADE_CAP_MS = 200`). home.js primes the context in exactly
> the four genuine gesture handlers (pick / folder / example-submit / drop — deliberately NOT
> `input.onchange`), starts the hum with the overlay, stops it on every error path, and on the
> fetch path FADES (≤200 ms) **before** `window.location` navigates; all through one guarded
> `hum()` helper so audio can never block a load. `/example` stays a native form navigation —
> its hum ends at unload, recorded not hidden (ADR-0328). Visible mute + volume on
> `.load-card`, persisted `sf-hum-mute`/`sf-hum-vol` (theme.js house pattern), audible-at-
> low-gain default (slider 40/100, squared curve, ceiling 0.32; WCAG 1.4.2 = a control, not
> silence; volume-move unmutes). Motion: `.load-orbit` + three `.orbit-dot`s
> (--accent/--ok/--warn; radii 56/42/61 px via `--orbit-r`; 2.8/4.6/6.7 s; transform-only
> keyframes; zero JS) with its OWN `@media (prefers-reduced-motion: reduce){.orbit-dot{
> animation:none}}` line BESIDE the pinned `.load-spinner{animation:none}` literal (unchanged).
> The pinned `_AUTOPLAY_JS` list untouched; `launch_audio.js` triaged into the axis-census
> EXEMPT bucket; PAGE_SCRIPTS digests + 18 axis call sites hold as-is. DESIGN-SYSTEM gains
> **§8 Audio** + a DoD bullet (§7 numbering intact). Version 1.0.144, highest ADR ADR-0328,
> wheel + nine installers regenerated ONCE after the code landed (bump BEFORE suite, the
> recorded sequencing).**
>
> ## Verification (all read from runs this session)
> `test_launch_sequence.py` (8 content: card markup incl. controls INSIDE the card ·
> transform-only keyframes · token-only orbit colors · zero-JS motion · the two reduced-motion
> lines side by side · assetless synthesis (static tree globbed for audio extensions) ·
> shuffled-bag/lookahead/jitter markers · prime-count == 4 with BOTH onchange handlers
> regex-excluded · `hum('fade')` indexed BEFORE `window.location` · ≥3 `hum('stop')` ·
> `_AUTOPLAY_JS` pin equality · DESIGN-SYSTEM §8 pin) + `test_launch_audio_chromium.py`
> (6 behavioral, REAL chromium: zero AudioContexts after page load AND during a held
> programmatic-change load (silent by design, which then completes) · one context per gesture,
> hum state RUNNING across a held POST, an orbit dot's computed transform measurably different
> between two 300 ms samples, then the release lands /analysis · `fadeOut(99999)` resolves
> <1.5 s proving the 200 ms cap, closed ⇒ a new gesture builds context #2 · mute set DURING a
> load survives the navigation + reload, volume persists, volume-move unmutes · card geometry
> in 4 themes × 2 viewports with scrollbars VISIBLE: orbit + both controls inside the card,
> controls non-overlapping). **Proved able to fail, watched: 13 of 14 FAIL on the stashed
> pre-change tree; the one both-tree pass is the `_AUTOPLAY_JS` pin equality (invariant
> guard). Post-change: 14 passed.** Six nearest existing suites (header_and_loading · landing ·
> home_shell · axis_titles · accessibility · static_cache): **70 passed, 1 skipped** (the
> standing INCIDENTAL_SVG path.js skip). Statics foreground: ruff check "All checks passed!" ·
> format clean (833 files) · mypy --strict "no issues in 117 source files" · bandit exit 0 ·
> node --check clean on every static JS. Installer lockstep vs the fresh 1.0.144 wheel:
> **52 passed**. Full-suite result: see SESSION-LOG (recorded after the run completed — a
> launched run is not a result).
>
> ## ⇢ NEXT
> 1. **Merge the draft PR for this round when CI is green** (branch
>    `claude/polaris-pr10-or03-motion-uzgvc0`), then:
> 2. **OR-04 operator park artifacts** (`audit/VERIFICATION-REPORT-ollama-lifecycle.md` §8):
>    #1 `where ollama` · #3 keep_alive probe · #5 runner PPID · #4 model-identity manifest —
>    plus #490's four-scenario smoke on the deployed build.
> 3. Behind the queue: SVG batch 3c (sra/sra_jcl/sra_ssi/volatility; tornados recorded
>    not-axis-charts per A1) · the 7-module `DOM_PENDING` ledger · Phase 3 (CC-01 rendering
>    half, 74 sites) · Phase 4 (P1–P6) · rank 13/14.
> 4. OR-03 residuals if ever wanted (ADR-0328): operator's-ear acceptance on the deployed
>    build (the vendored-ogg fallback stays HELD if the synthesis grates); /example → fetch
>    path if its at-unload cut ever matters; cross-page audio is out of scope by the
>    navigation boundary.
> 5. ADR-0327 residuals unchanged: a `/export/{fmt}/standards` workbook would let §2/§3 join
>    the ⤓ set; analysis-workbook makeup/status/constraint sheets would let /card's pivots
>    join. `data-noprint` (C1) shipped as PR-4.
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
> container; the no-target /analysis render is byte-identical across the round's trees) —
> an OR-02-adjacent hardening item, mechanism undetermined. Adjudicated: do NOT chase as a
> regression.
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
> unconditional floor · ADR-0311→0327 items), **plus this round:** "the hum needs an audio
> asset or a seam-mixed loop" (synthesis has no loop point — the seam requirement is satisfied
> by construction, and the ogg fallback stays HELD, not shipped); "`input.onchange` can prime
> the AudioContext" (excluded by decision AND asserted — a programmatic change runs a silent
> load); "the orbit needs JS or a new stepper entry" (transform-only CSS; `_AUTOPLAY_JS` is a
> pin, not a place for audio).
>
> ## Harness notes — the traps, one line each
> Run dev tools as `python -m <tool>` (a stale `/root/.local/bin/ruff` shadows pip's).
> **`pip install -e ".[dev]"` before the suite** (bare `PYTHONPATH=src` fails ~200 web tests).
> `pytest --timeout=N` is NOT installed — it exits 0 having run nothing. `cmd | tail; echo $?`
> reports `tail`'s status — **read the tool's own summary line** (the formatter reflowed one
> test file again this session). **`pkill -f` with a pattern in the killer's own command
> line kills the killer** (kill by PID). CI can take ~11 min to register check runs.
> `TestClient` follows 303 and CONSUMES one-shot banners (`follow_redirects=False`). Parity
> marker ≈2m38s (ADR-0322 perf addendum). Headless Chromium hides scrollbars
> (`ignore_default_args=["--hide-scrollbars"]` shows them). A remote-session resume can
> silently revert working-tree files — re-diff after every resume. `caplog` needs
> `logger="schedule_forensics.<module>"`. Playwright `bounding_box` is viewport-relative.
> **localStorage is per-ORIGIN** (second served app instance: write theme/scale AFTER landing
> on its origin). Containers RESTART mid-run: statics FOREGROUND first, long pytest
> re-runnable, reinstall pip after every resume. After a squash-merge: `git fetch --prune
> origin && git remote set-head origin -a && git checkout -B <branch> origin/main`.
> **Version-bump sequencing:** bump pyproject BEFORE the full background suite starts (the
> installer-lockstep tests in THAT run red-herring against a not-yet-rebuilt wheel) — bump,
> rebuild wheel+installers, THEN launch. **NEW (this round):** in a MODULE-scoped chromium
> suite, a test that lets its upload COMPLETE must use bytes no earlier test loaded — the
> byte-identical dedup (ADR-0259) redirects home, not /analysis (first run failed exactly so).
> **Never sleep inside a sync-Playwright route handler** (it runs on the event loop and
> freezes the page's own waits) — park the route object and resolve it from the test body.
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
