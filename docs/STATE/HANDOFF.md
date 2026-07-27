# Handoff — 2026-07-27i (AXIS-TITLES batch 1: PENDING 16 -> 11; the spec's caption table is not a source; ADR-0301; v1.0.106)

> ## STATUS (current) — NOTHING IN FLIGHT. ADR-0301 merged. Version **1.0.106**. Highest ADR **ADR-0301**. `main` at `a941a4a`.
> Branch `claude/schedule-forensics-continue-gkju7l`, restarted from merged `main`, tree clean.
> **#451, #452, #453 and #454 all merged. No open PRs.** All five checks green on #454 —
> and the windows leg is the one that mattered: it re-downloaded the converter and
> **SHA-256-verified 24 jars against the NEW pin**, which is the empirical proof that moving the
> pin off orphaned history is safe. Both ADR-0300 link shapes and both mutations ran in that
> same job.
>
> - **AXIS-TITLES batch 1 done: `PENDING` 16 -> 11.** Captioned `histogram`, `curves`, `scurve`,
>   `cei`, `resources` via `SFChartFrame.axisTitles`. Guard mutation-proved three ways (deleted
>   call · one-label caption · captioned module parked back in PENDING).
> - **⚠️ THE BIG ONE — DO NOT TRANSCRIBE THE SPEC'S §3 CAPTION TABLE. It is wrong for four of the
>   modules I checked**, and a caption is an assertion about what the reader is looking at:
>   `curves.js` plots **activity counts**, not "CUMULATIVE VALUE ($M)"; `resources.js` plots **work
>   booked in working days** over a **runtime-chosen** day/week/month bucket, not "DEMAND (FTE)" over
>   "WEEK (COMMENCING)"; `cei.js` has **no secondary axis** (the CEI figure is a text callout);
>   `drift.js` plots **forecast dates x three forecast methods**, not "SCHEDULE VERSION x SLIP
>   AGAINST BASELINE". **Derive every caption from the rendering code (ADR-0301).**
> - **⚠️ AND DO NOT FOLLOW THE SPEC'S §5 BATCH TABLE.** It was never revised after ADR-0298's
>   correction #4, so its batch 1 is **4/5 DOM visuals** the SVG helper cannot serve. **Batches
>   follow the `PENDING` ledger**, which is executable and current.
> - **Two captions are COMPUTED, not constant, because the axis itself changes:** `cei.js` follows
>   the Running-totals toggle (`top = totals ? cumTop : data.max_count`) and `resources.js` names the
>   bucket actually rendered (`UNIT`). A constant string would be false in one of the two states.
> - **`histogram.js` carried a THIRD local caption convention** (`cap.textContent`, hard-coded 11px)
>   beyond the two batch 0 retired — now shared, and it gains a Y caption it never had. **The
>   `SECOND_CONVENTION` regex cannot be completed**: widening it to `cap.textContent` fires on
>   `a11y.js` and `trend_drill.js`. The property that converges is **the ledger reaching empty**,
>   not the regex.
> - **`drift.js` is deliberately still PENDING**, reasons recorded in the ledger itself: its
>   captions need a decision (above), and its Y anchor (`T + 9`) lands **7px above** its first
>   method-name row (`padT + 14`), so it needs a `padT` nudge — a layout change, out of scope for a
>   caption batch.
> - **⚠️ INCIDENTAL BUT IMPORTANT — the MPXJ download pin was on ORPHANED history.** `mpxj_ref()`
>   pins the last commit touching `tools/mpxj`. The pin shipped in **v1.0.105 (`1f10729`) is NOT an
>   ancestor of `main`** — it survives only on an unmerged branch, so the operator's converter
>   download depended on that branch continuing to exist. Regenerating moved it to **`749bf07c`, a
>   squash-merge commit ON `main`**, bytes verified byte-identical to the tree. **A squash-merge
>   gives the same content a NEW SHA, so a pin captured pre-merge is orphaned the moment the branch
>   goes.** Re-check `mpxj_ref()` against `main` whenever `tools/mpxj` changes.
> - **Version 1.0.105 -> 1.0.106; wheel rebuilt, all nine installers regenerated** (ADR-0148
>   lockstep — the static JS is packaged). Verified by watching the lockstep test fail first, then
>   pass.
> - **Gate:** ruff / ruff format / mypy --strict / bandit clean; `node --check` on all static JS;
>   axis guard 29 green; installer suite 52 green; the three dashboard payload golden SHAs
>   unchanged (a caption cannot move a payload hash); `grep -rn "rotate(-90"` empty.
> - **NEXT: AXIS-TITLES batch 2** — take the next ~5 off `PENDING` (11 left: `drift`, `margin`,
>   `margin_dashboard`, `path`, `sra`, `sra_jcl`, `sra_ssi`, `trend`, `trend_drill`, `volatility`,
>   `wbs`). **Read each chart's rendering code and derive its caption; the spec's table is a
>   suggestion, not a source.** `trend.js` + `volatility.js` need the per-metric Y caption
>   (spec §3.1: `metric.label + " (" + metric.unit + ")"`; a metric with no unit is a
>   **catalogue gap to report**, not a caption to invent). `trend_drill.js` has a `cap.textContent`
>   subtitle that is NOT an axis caption — leave it. Then **CRISPNESS 11px floor ONLY**
>   (`--sf-fs-axis-title` is the seam; its §2.1 claim that `sf-themes.css` "was never committed" is
>   FALSE). Then GUIDED-MODE (5) + VOICE-DECISION (4), parked on the operator. Also open: monolith
>   split phases 2-3; a DOM caption mechanism for the 11 `NO_SVG_AXES` visuals; `_ANALYSIS_CACHE_MAX
>   = 48` (ADR-0292); the .mpp probe UI (ADR-0293).
> - **STILL OWED:** the four-theme visual pass (console / daylight / apollo / jarvis at 90-125%),
>   outstanding since 2026-07-27b and now covering ten captioned modules. **A headless browser IS
>   usable in this container** (verified 2026-07-27h, not assumed): `pip install playwright`, then
>   launch with an explicit
>   `executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome"` — the pip driver expects
>   build 1228 and the image ships 1194, so a bare `launch()` fails with "Executable doesn't exist".
>   `PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers` is already set. **The browser is verified; the pass
>   is not.** CSP note: use `page.evaluate` / `eval_on_selector`, never `wait_for_function`
>   (`script-src 'self'` blocks string-eval — the air-gap working).
> - **DEPLOY NOTE (operator has no local clone):** download `installer/install-tier2.ps1` from the
>   GitHub web UI and run
>   `powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\install-tier2.ps1"`.
>   One file; it fetches + SHA-256-verifies the `.mpp` converter from a pinned immutable commit
>   (now on `main`). An existing converter is never destroyed — not by a re-run, a failed download,
>   a self-referential `SF_MPXJ_HOME`, a junction, or a symlink; and a drive root no longer aborts
>   the install. All executed on Windows in CI (ADR-0300). Offline: Code -> Download ZIP, run from
>   inside the extracted folder.


# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
