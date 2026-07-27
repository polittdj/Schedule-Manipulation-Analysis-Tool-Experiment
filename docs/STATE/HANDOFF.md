# Handoff — 2026-07-27j (AXIS-TITLES batch 2: PENDING 11 -> 7; a ledger entry that was never a chart; ADR-0301 addendum; v1.0.107)

> ## STATUS (current) — ADR-0301 + batch-2 addendum. Version **1.0.107**. Highest ADR **ADR-0301**. `main` at `8990c49` (batch 2 on the branch, PR open).
> Branch `claude/schedule-forensics-continue-gkju7l`. #451-#455 all merged before this.
>
> - **AXIS-TITLES batch 2: `PENDING` 11 -> 7** (`drift`, `margin_dashboard`, `sra`, `sra_jcl`,
>   `sra_ssi`, `trend`, `volatility` remain). Captioned `margin`, `trend_drill`, `wbs` — and
>   **removed `path.js`, which was never a chart.**
> - **⚠️ `path.js` WAS MIS-PARKED IN `PENDING`, on a claim in ADR-0298** ("the regex missed
>   `path.js` and `resources.js`, which do draw SVG axes"). Half right: `resources.js` does;
>   **`path.js` does not.** Its timeline is a **DOM table** (`tbody`, `.path-track` divs,
>   `rowIndex` arithmetic); its ONLY SVG is a 2-element overlay (`.pv-link`) drawing a dependency
>   connector between rows. No chart root, no plot rect, no ticks. So "11 to caption" overstated
>   the work by one — the exact thing the ledger exists to prevent.
> - **A CLEVERER REGEX WAS TRIED AND REJECTED ON EVIDENCE — do not retry it.** "An `<svg>` root
>   AND a plot rect" was written and run against every module before adoption: it mis-classified
>   **five** (`performance`, `margin_dashboard` name geometry `L/R/T/B` not `padL`; `resources`,
>   `sra_jcl`, `sra_ssi` build through a local `svg()` factory not `svgEl("svg")`) **and still
>   called `path.js` a chart.** Every module names its geometry differently. The exception is
>   explicit instead: **`INCIDENTAL_SVG`** names the entry + reason, and
>   `test_the_incidental_svg_exception_cannot_rot` closes three ways it could become a dumping
>   ground. All four mutations bite.
> - **⚠️ SPEC WRONG AGAIN — now 6 of 8 checked modules.** `trend_drill.js`: spec says "SCHEDULE
>   VERSION x METRIC VALUE"; the code draws **one bar per quality metric** against a locked count
>   of **offending activities** (the version is the animation frame, not the X axis). `wbs.js`:
>   spec says "PERCENT COMPLETE (%)"; the left axis is **SPI(t)**, a ratio against a 1.0 on-plan
>   reference. `margin.js` is the one the spec got right. **Derive every caption from the
>   rendering code (ADR-0301).**
> - **A GAP NAMED, NOT INVENTED — secondary axes.** `wbs.js` is a combo chart (SPI(t) bars left,
>   earned schedule right); `axisTitles` draws exactly one X and one Y, so the right axis stays
>   uncaptioned. Captioning the primary pair is strictly better than two unlabelled axes and says
>   nothing false. **`sra.js` and `margin_dashboard.js` will want the same affordance** — it is a
>   change to the shared convention (ADR-0298) and needs its own decision.
> - **Version 1.0.106 -> 1.0.107**, wheel rebuilt, nine installers regenerated (ADR-0148 lockstep).
>   **The MPXJ pin held at `749bf07c`** (on `main`), confirming last batch's fix is stable rather
>   than a one-off.
> - **Gate:** axis guard 26 passed + 1 documented skip (`path.js`); ruff / ruff format /
>   mypy --strict / bandit clean; `node --check` on all static JS; installer suite green.
> - **NEXT: AXIS-TITLES batch 3** — 7 left, and they are the HARD ones. Several are **multi-chart
>   modules** needing per-chart captions, not one call: `sra.js` (4 charts), `volatility.js` (10
>   visuals, 7 plot rects), `trend.js` (1,183 lines, 5 svg roots), `margin_dashboard.js` (2 charts
>   + a strip), `sra_jcl.js` / `sra_ssi.js` (football scatter + S-curve + non-axis strips/matrices).
>   `trend` + `volatility` need the per-metric Y caption (spec §3.1: `metric.label + " (" +
>   metric.unit + ")"`; **a metric with no unit is a catalogue gap to REPORT, not a caption to
>   invent**). `drift.js` additionally needs a `padT` nudge (its Y anchor lands 7px above the first
>   method-name row). **Decide the secondary-axis affordance before `sra`/`margin_dashboard`.**
>   Then **CRISPNESS 11px floor ONLY** (`--sf-fs-axis-title` is the seam; its §2.1 claim that
>   `sf-themes.css` "was never committed" is FALSE). Then GUIDED-MODE (5) + VOICE-DECISION (4),
>   parked on the operator. Also open: monolith split phases 2-3; a DOM caption mechanism for the
>   13 `NO_SVG_AXES` visuals; `_ANALYSIS_CACHE_MAX = 48` (ADR-0292); the .mpp probe UI (ADR-0293).
> - **STILL OWED:** the four-theme visual pass (console / daylight / apollo / jarvis at 90-125%),
>   outstanding since 2026-07-27b and now covering **thirteen** captioned modules. **A headless
>   browser IS usable here** (verified, not assumed): `pip install playwright`, then launch with
>   `executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome"` — the pip driver wants
>   build 1228 and the image ships 1194, so a bare `launch()` fails with "Executable doesn't
>   exist". **The browser is verified; the pass is not.** CSP: use `page.evaluate` /
>   `eval_on_selector`, never `wait_for_function`.
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
