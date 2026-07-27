# Handoff — 2026-07-27k (the caption helper gains a secondary-axis label; ADR-0302; v1.0.108)

> ## STATUS (current) — ADR-0302. Version **1.0.108**. Highest ADR **ADR-0302**. `main` at `56dcaa6` (this work on the branch, PR open).
> Branch `claude/schedule-forensics-continue-gkju7l`. #451-#457 all merged before this.
>
> - **`SFChartFrame.axisTitles` now takes an OPTIONAL `y2Label`** for a combo chart's secondary
>   (right) axis. **The operator was asked and chose this** over "primary axes only, permanently"
>   and over deferring it — batch 2 had recorded it as a gap rather than inventing a fix mid-batch.
> - **Placement mirrors the Y caption to the plot's top-RIGHT**, end-anchored, same baseline:
>   `caption(svg, geom.R - 4, geom.T + 9, opts.y2Label, "end")`. The three captions occupy three
>   different corners **by construction** — X bottom-right `(R, B-4)`, Y top-left `(L+4, T+9)`,
>   Y2 top-right. Horizontal, never rotated.
> - **This PRESERVES ADR-0298's "one convention", it does not break it.** The rule is one
>   *implementation*, one *token*, one *placement law* — not "exactly two labels". Y2 goes through
>   the same `caption()` builder and the same `.ch-at` class, so the queued **CRISPNESS 11px floor
>   still moves ONE value**.
> - **Omitting `y2Label` emits nothing**, so every pre-existing caller is unaffected — asserted in
>   the harness, not assumed.
> - **`wbs.js` is the first caller**: SPI(t) (ratio, left axis) + earned schedule (working days,
>   right axis). Its captions **name their own axis**, because on a two-scale chart the reader's
>   real question is *which gridlines do I read this against*.
> - **Mutation-verified — four mutants, each caught:** Y2 moved onto the X caption's corner · Y2
>   emitted unconditionally (would silently add a caption to every existing caller) · Y2
>   left-anchored · a numeric `font-size` planted in the caption block.
> - **`PENDING` is UNCHANGED at 7** (`drift`, `margin_dashboard`, `sra`, `sra_jcl`, `sra_ssi`,
>   `trend`, `volatility`). Nothing new was captioned on purpose: the convention change is
>   reviewable on its own rather than buried in seven modules of caption text.
> - **Version 1.0.107 -> 1.0.108**, wheel rebuilt, nine installers regenerated (ADR-0148 lockstep —
>   `chartframe.js` + `wbs.js` are packaged). ⚠️ **Run the regeneration in the BACKGROUND**: at the
>   120s foreground timeout it gets killed mid-write and leaves tier3 a version behind tier1/tier2
>   (`test_shared_body_is_identical_across_tiers_no_drift[ps1]` catches it — that happened in batch 2).
> - **NEXT: AXIS-TITLES batch 3** — the 7 remaining, and they are the hard ones, mostly **multi-chart
>   modules needing per-chart captions, not one call**: `sra.js` (4 charts), `volatility.js` (10
>   visuals, 7 plot rects), `trend.js` (1,183 lines, 5 svg roots), `margin_dashboard.js` (2 charts +
>   a strip), `sra_jcl.js` / `sra_ssi.js` (football scatter + S-curve + non-axis strips/matrices).
>   `sra` and `margin_dashboard` can now use **`y2Label`**. `trend` + `volatility` need the
>   per-metric Y caption (`metric.label + " (" + metric.unit + ")"`; **a metric with no unit is a
>   catalogue gap to REPORT, not a caption to invent**). `drift.js` also needs a `padT` nudge (its Y
>   anchor lands 7px above the first method-name row). **Derive every caption from the rendering
>   code (ADR-0301) — the spec's table has been wrong for 6 of 8 modules checked.**
>   Then **CRISPNESS 11px floor ONLY**. Then GUIDED-MODE (5) + VOICE-DECISION (4), parked on the
>   operator. Also open: monolith split phases 2-3; a DOM caption mechanism for the 13
>   `NO_SVG_AXES` visuals; `_ANALYSIS_CACHE_MAX = 48` (ADR-0292); the .mpp probe UI (ADR-0293).
> - **STILL OWED:** the four-theme visual pass (console / daylight / apollo / jarvis at 90-125%),
>   outstanding since 2026-07-27b, now covering thirteen captioned modules **plus the new secondary
>   caption — which is the placement most worth eyeballing**, being newest and sitting where a
>   legend or value readout often lives (`cei.js` draws its CEI figure near that corner, though it
>   passes no `y2Label`). **A headless browser IS usable here** (verified, not assumed):
>   `pip install playwright`, then `executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome"`
>   — the pip driver wants build 1228 and the image ships 1194, so a bare `launch()` fails with
>   "Executable doesn't exist". **The browser is verified; the pass is not.** CSP: use
>   `page.evaluate` / `eval_on_selector`, never `wait_for_function`.
> - **DEPLOY NOTE (operator has no local clone):** download `installer/install-tier2.ps1` from the
>   GitHub web UI and run
>   `powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\install-tier2.ps1"`.
>   One file; it fetches + SHA-256-verifies the `.mpp` converter from a pinned immutable commit on
>   `main`. An existing converter is never destroyed — not by a re-run, a failed download, a
>   self-referential `SF_MPXJ_HOME`, a junction, or a symlink; and a drive root no longer aborts the
>   install. All executed on Windows in CI (ADR-0300). Offline: Code -> Download ZIP, run from
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
