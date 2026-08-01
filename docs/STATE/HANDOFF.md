# Handoff — 2026-08-01i (Phase 0: the caption halo + a pixel-measuring visual pass; ADR-0331; v1.0.147)

> ## STATUS (current) — **Phase 0 of the approved completion plan BUILT AND GATED on this tree
> (ADR-0331).** Batch 3c-ii MERGED as `02decef` (#507). An ADR-0240 audit of it returned one
> adversarially-verified finding: **an axis caption over chart ink is illegible** — 1.05–1.54:1
> against `.ch-bar` `#3d8ec4` in the four themes, where the same caption measures 3.07–5.52:1
> against the canvas. **Convention-wide, not a 3c-ii bug:** the pass now reports ink beneath
> **792 of 1008** caption renders. ADR-0303's "the DATA yields" cannot apply — on a histogram the
> data IS the plot — so the fix is a **halo**: `.ch-at{paint-order:stroke fill;stroke:
> var(--sf-ch-canvas);…}`, one CSS rule, **placement unmoved**, **no JS touched** (all 28 frozen
> call-site digests byte-identical by construction). The halo colour is a token because the canvas
> is NOT uniform — `--sf-ch-canvas` defaults to `var(--panel)`, `.ssi-svg` sets `#fff`, `.res-svg`
> and `.evo-gantt svg` set `var(--gantt-canvas)`. **The measured pass now reads PIXELS:** the probe
> sweeps non-text ink and requires the halo's computed style across the matrix (cheap, broad), and
> the degenerate single-bin case screenshots each caption and measures the modal colour of its own
> box against the 3.0 floor (sharp) — PNG decoded with **stdlib zlib**, since Pillow is not and will
> not become a dependency. Version **1.0.147**, highest ADR **ADR-0331**, wheel + nine installers
> regenerated ONCE after the code landed.
>
> ## Verification (all read from runs this session)
> Visual pass (10 route-cells × 4 themes × 3 scales + the degenerate case): **2 passed in 106.6 s**,
> 1008 caption renders, 792 inked, zero collisions, KNOWN_COLLISIONS still EMPTY. Census + freeze +
> neighbours: **94 passed, 2 skipped**. **Proved able to fail, watched:** with the halo stashed the
> pixel test reports `rgb(61,142,195)` — the bar fill — at **1.17:1** (predicted 1.166), while the
> one caption with no bar behind it still reads 3.07:1, so the check DISCRIMINATES; restored, all
> read 3.06:1. Statics foreground: ruff "All checks passed!" · format clean (836) · mypy --strict
> clean (117) · node --check clean. Full-suite result: see SESSION-LOG (recorded after the run
> completed — a launched run is not a result).
>
> ## ⇢ NEXT — the approved plan (`/root/.claude/plans/merry-juggling-owl.md`; operator-approved)
> Order: **perf + session first**, then UI (hybrid), then engine. Phase 0 is this round.
> 1. **Phase 1 — "always start clean."** ROOT CAUSE VERIFIED: the deployed install pins
>    `$AppPort = 8321`, `launcher.py` has no instance detection, the old process survives
>    (`idle_grace=600` and `_liveness` refreshes `last_beat` on EVERY request), and the browser
>    timer starts BEFORE the bind and is non-daemon — so a relaunch opens onto the OLD process and
>    its OLD SessionState, which also defeats ADR-0324 (same process ⇒ same launch token).
>    **RED-TEAM CORRECTIONS, must be honoured:** (a) on **Windows** `SO_REUSEADDR` may let the
>    second bind SUCCEED (two listeners, indeterminate routing) — so build an explicit
>    single-instance PROBE, not a bind-error reporter, and confirm on the deployed box first;
>    (b) "move the browser timer after serve_fn" is WRONG — `serve_fn` blocks for process life;
>    (c) `POST /session/wipe` misses **35** declared fields incl. **`dcma_acumen_parity`** (a
>    metric-mode flag — Law-2 relevant); the reflection test needs MUST_RESET / PRESERVED /
>    EXCLUDED buckets (`_lock` never compares equal); (d) clear the disk cache on **clean
>    shutdown**, NOT at launch (launch-clearing leaves data at rest over the risky window and
>    throws away a 9× warm start); (e) a blanket `sf-`/`sf.` localStorage sweep would un-mute the
>    ADR-0328 boot hum and reset theme/scale/hints — split session state from preferences.
> 2. **Phase 2 — performance.** Idle pumps are exactly TWO: `sysmon.js` (2 s) and `heartbeat.js`
>    (3 s). **Do NOT pause the heartbeat** — `idle_grace=600` would shut the tool down after 10
>    minutes minimized and lose the session (data loss introduced by a perf item). The nine/eleven
>    `setInterval(…,1600)` steppers are **Play-gated**, not idle — real crash-prevention work, but
>    misfiled as idle-loop. Lead the observer fix with the **records-based** rewrite
>    (`tooltips.js:71-79`, walk `addedNodes`), scoping second.
> 3. **Phase 3 — UI (hybrid).** Four unconverted Act III pages (`/sra`, `/risks`, `/briefing`,
>    `/brief`: zero panelkit/`_panel_head`/`_shell_tools`/`sf-take`), `DOM_PENDING` (7), then the
>    DoD ledgers. **DD-line ledger must exclude non-time-axis charts** (`histogram.js`,
>    `scatter.js`, `sra_jcl.js` cost axis) — record them as exemptions.
> 4. Behind: Phase 4 engine (import_notes · falsy-zero · CC-01 · SRA-LEGACY · V3), Phase 5
>    monolith split 2–3, Phase 6 docs/operator queue (OR-04 collection still with the operator).
>
> ## Still carried (unchanged identifiers, nothing lost)
> **CC-01** (H2a) rendering half open, ~74 call sites (an approximate grep — RE-DERIVE, never
> inherit) · **CC-05** oracle-blocked, do not start · **V3** elapsed literals
> (`engine/msp_filters.py`) · the **legacy `/sra` cross-basis defect** · **EVM2-2D** and
> **H6-RESID** (both fell out of the handoff chain — re-adopted by the plan) · **CACHE-48** ·
> **SPLIT-23** · **A0293-UI** · Project5's SSI export contradicts ADR-0307 (ADR-0307 stands) ·
> `resume` is MSPDI-only · Phase 7 forward-pass packing · ADR-0322 residuals · importer warnings
> belong on the page via `Schedule.import_notes` · ADR-0320 residuals · ADR-0325/0326 notes ·
> **the /analysis focus→tip family is a measured intermittent** — adjudicated, do NOT chase.
>
> ## Hypotheses KILLED — do not re-chase
> Everything in `audit/SRA-PARITY-20260729.md` §7 and the archived lists, **plus this round:**
> "the caption can move out of the ink" (ADR-0298/0303 placement is frozen and the data cannot
> yield when the data IS the plot — the halo is the answer); "a blanket white halo" (two of the
> three chart families are not on white — read the CSS); "ink-present ⇒ halo-required is a
> sufficient test" (its antecedent is true on 79 % of renders — measure pixels).
>
> ## Harness notes — the traps, one line each
> Run dev tools as `python -m <tool>`. **`pip install -e ".[dev]"` before the suite.**
> `pytest --timeout=N` is NOT installed. **Read the tool's own summary line.** `pkill -f` with the
> pattern in the killer's own command line kills the killer. CI can take ~11 min to register check
> runs. `TestClient` follows 303 and CONSUMES one-shot banners. Parity marker ≈2m38s. Headless
> Chromium hides scrollbars. `caplog` needs `logger="schedule_forensics.<module>"`. **Playwright
> `bounding_box` and `page.screenshot(clip=…)` are VIEWPORT-relative — a caption below the fold
> needs `handle.screenshot()`, which scrolls itself.** **localStorage is per-ORIGIN** (the visual
> pass spans THREE origins). Containers RESTART mid-run: statics FOREGROUND first, reinstall pip
> after every resume. After a squash-merge: `git fetch --prune origin && git remote set-head origin
> -a && git checkout -B <branch> origin/main`. **Version-bump sequencing:** bump BEFORE the suite.
> Never sleep in a sync-Playwright route handler. Never `from tests.web...` in a test.
> **A parse-time-rendering JS module + a later chartframe.js = first-paint crash** (ADR-0316).
> **An on-demand panel needs a strict per-host wait AND a caption floor.** **A stray `*/` makes CSS
> error-recovery swallow the NEXT rule silently — only a computed-style read catches it.**
> **`cd` in a Bash call persists across calls — use absolute paths.**
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
