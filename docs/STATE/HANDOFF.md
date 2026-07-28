# Handoff — 2026-07-28b (round 10 shipped; the toolbar that fired but did nothing; ADR-0304; v1.0.120)

> ## STATUS (current) — Round 10 COMPLETE, merged as #473 + #474. Version **1.0.120**, wheel + nine installers regenerated. Highest ADR **ADR-0304**. Tail rank 10 done; **next is rank 11 — `/path`, `/driving-path`, `/evolution`, `/volatility`.**
>
> ### What shipped
> `/cei`, `/performance`, `/resources` and `/forecast` now wear the panel contract — the rank-10
> per-visual normalization. Four surveys + a cross-cutting audit, four serialized implementers,
> two adversarial verifiers and a lead, every claim re-verified by the orchestrator.
> **Gate green: `2919 passed, 1 skipped`; ruff / ruff-format / mypy-strict / bandit / node clean.**
> Law 2 held — a numeric-token diff of **14 rendered states** against the round-9 baseline
> `a7a06fc` resolved to **0 schedule figures changed** (the single differing token was `11015`,
> the `&#11015;` ⇩ glyph of a deliberately deleted duplicate anchor). All **16** `axisTitles` call
> sites md5-identical to baseline; 648 caption renders, clean.
>
> ### ⚠️ THE ROUND'S CENTRAL LESSON (ADR-0304) — verify the EFFECT, not the MECHANISM
> **Standing requirement 2 passed on a control that does nothing.** It said *"click ⛶ for real,
> reading `is-big` back"* — and that assertion succeeds perfectly while the panel never moves:
> ```css
> .is-big{grid-column:1/-1}      /* base.css:557 — the ONLY rule for the class */
> ```
> `grid-column` binds only on a **grid item**. Measured, all four themes, box before vs after a
> real click: `/cei` 8/8 no-ops, `/resources` 12/12, `/forecast` 23/23, `/evm` 20/20 — `panelW
> 1308->1308, panelH 745->745`. **REQUIREMENT 2 IS AMENDED: measure `getBoundingClientRect()`
> before and after; an unchanged box is a failing control even when the class and label are
> perfect.** Every check this project has had that passed while the feature was broken shares that
> shape — it asserted the machinery ran, not that anything visibly happened.
>
> ### ⚠️ AND THE ATTRIBUTION WAS WRONG THE FIRST TIME — mine, not an agent's
> The no-op was first written up (in a PR body and twice to the operator) as *"round 10 shipped 43
> dead buttons"*. **False.** `.is-big` is byte-identical at `a7a06fc`, which already had **43
> `_shell_tools` call sites** across `_analysis_body` / `_evm_body` / `_scurve_body` /
> `_portfolio_body` / `_ribbon_body` / `_compare_body` and ~20 more, and measures the same no-op on
> the untouched baseline (`/scurve` 2/2, `/portfolio` 2/2, `/integrity` 4/4, `/evm` 4/4). It is a
> **pre-existing property of the merged contract** across ~9 pages; round 10 replicated the merged
> convention onto four more. **A finding can be REAL AS AN OBSERVATION and WRONG AS AN
> ATTRIBUTION, and each implies a different fix.** The CSS reading was right; skipping the baseline
> check was not. Round 9's rule — *check merged `main` before calling a pattern a defect* — exists
> for exactly this, and it was not applied.
>
> ### Fixed this round
> - **`/performance` ⛶ made the chart WORSE.** The page already had the correct **matched pair**
>   (`.mosaic .tile.tile-expanded{grid-column:1/-1}` + `.tile-expanded .chart-host{height:74vh}`,
>   app.css:636-637, wired by mission.js). The round stamped `.is-big` on instead — width half
>   only — so the tile widened 546->1108px, the width-proportional svg doubled (516x266 ->
>   1078x556), the host stayed clamped at 340px, and ~40% of the chart including the whole X axis
>   fell below a scroll fold. Fix: `.mosaic .tile.is-big .chart-host{height:74vh}` — the sibling's
>   own rule, toggled-state only, so no default caption moves.
> - **A forensic export control must never disagree with the visual it sits on.** `/performance`'s
>   per-tile ⤓ pinned `?file=` at render time while the stepper re-binds G1-G5 with no reload, so
>   after one step the button beside a chart exported a DIFFERENT version. `setVersion` now
>   re-points every `#perfGrid [data-export]`; both stepped URLs verified live (200 / `PK`).
> - **The `/forecast` drift table mislabelled four columns** — 5 `<th>` vs 6 `<td>`, so the
>   as-scheduled date read under "Completion rate". Pre-existing, changes no number, wrong on a
>   testimony page. Header restored; the test now asserts it **structurally** (`<th> == <td> + 1`).
>
> ### OPEN — decision-ready, each with a measurement, none silent
> 1. **`/resources` X-caption collision.** The round's one-word `defer` genuinely fixed a blank
>    chart (`svg children 0 -> 62`) — and thereby made a previously INVISIBLE defect visible:
>    `Period (month commencing)` sits over the last rotated month ticks in **8 of 12 theme x scale
>    combos** (console@1 ~36x2px, apollo@1 ~40x4px). Per requirement 5 `resources.js` was **NOT**
>    adjusted (md5 unchanged). Remedy is ADR-0303's — move the **label**, then add `/resources` to
>    the caption gate's `PAGES`.
> 2. **`/performance` `SFChartFrame` first-paint race** — pre-existing on both trees; `quadRatio`
>    and `quadBeiCp` render **nothing** until the stepper is touched. `defer` was tried and
>    reverted: it works (`quadRatio 0->24`, `quadBeiCp 0->23`, G1-G5 byte-identical) but surfaces
>    a caption collision (`To-go finishes ÷ baseline remaining` over `1.0 = as planned`, 50-64 x
>    8-9px, all 4 themes x 3 scales) that must be closed in the same change. **Operator decision.**
> 3. **`.is-big` global redefinition** — making ⛶ paint on block-layout pages touches ~9 merged
>    pages, and any rule that grows chart hosts **moves captions on `/scurve`, `/curves`,
>    `/trend`**, which requirement 5 forbids without a decision. **Operator decision.**
>
> ### THE FIVE STANDING REQUIREMENTS (2 is amended — carry all five into every round)
> 1. **JARVIS PROBE + PROMOTION CENSUS.** `hud.css`'s broad `html[data-theme=jarvis] .panel` /
>    `body` / `button` rules out-rank new contract classes. An element that GAINS `.panel` joins
>    the fight. Grep `hud.css` AND `sf-themes.css`, count `.panel` before/after, PROBE COMPUTED
>    STYLES in real chromium. A defined token is not a painting token. *(Round 10: 5 routes x 4
>    themes, `.panel` 5->5 / 7->7 / 8->8 / 8->8 / 18->18, zero promotions.)*
> 2. **PANELKIT IS A PER-PAGE INCLUDE — AND THE CONTROL MUST MOVE SOMETHING (ADR-0304).** Prove
>    the script loads, click for real, **and measure that the rendered box changed**. A class
>    read-back is not a proof. `_page` cache-busts `src` to `?v=` — match a SUBSTRING.
> 3. **LOADED-TERMS AUDIT WITH A CONTROL.** Run every new visible string through
>    `ai.citations.introduces_loaded_terms(source="", …)` AND run `"deliberate concealed fraud"` in
>    the same session — it must return `True`. A gate that never fires is unproven. *(Round 10:
>    control True; 56 strictly-new strings, harvested by diffing renders rather than retyped, 0
>    flagged.)*
> 4. **SHAPE THE PROOF TO THE PAGE'S OWN HAZARD.** Forms → byte-diff every `<form>`; embedded CSP
>    JSON → byte-capture; parity-relevant tables → dump the numeric content both sides and diff.
> 5. **THE AXIS CAPTIONS ARE FINISHED — DO NOT TOUCH THEM.** ADR-0298/0301/0303. md5 every
>    `axisTitles` call site against baseline. If a change would move a caption, STOP AND REPORT.
>
> ### Other rules that earned their place
> - **A CONTRACT IS A VOCABULARY, NOT A STAMP** — count what a panel CONTAINS before choosing
>   panel-scope vs visual-scope, and **reuse the page's existing mechanism** rather than shadowing
>   it with a second one that implements half of it (the `/performance` ⛶ failure, exactly).
> - **CHECK MERGED `main` BEFORE CALLING A PATTERN A DEFECT** — and before calling it a regression.
> - **READ THE ENGINE'S ARTIFACT, DON'T RECOMPUTE IT.**
> - **A MID-ROUND MERGE COSTS THE VERIFICATION.** #473 was merged with 7 of 12 agents done, which
>   (a) shipped `/cei` + `/performance` + `/resources` unverified, (b) left `main` red on the
>   ADR-0148 guard, (c) shipped a title claiming `/forecast` that was not in the diff, and (d)
>   **moved `origin/main` so both verifiers' Law-2 "before" comparison went blind** — the baseline
>   had to be re-pinned to `a7a06fc` by hand. If a round must be merged early, re-pin the baseline
>   explicitly.
> - **⚠️ MODEL AVAILABILITY IS A REAL FAILURE MODE.** The round's first launch died instantly —
>   all 8 agents returned *"out of usage credits"* for Fable 5 (the same failure recorded against
>   round 8). Relaunched on the strongest AVAILABLE model per ADR-0240's own clause. **Restore
>   Fable 5 credits before the next round**, and never hard-pin a workflow to one model without a
>   fallback.
> - **⚠️ BUILD TRAP:** `python -m build --wheel` writes to `dist/`, but
>   `tools/installer/build_installers.py` defaults to **`dist/wheel/*.whl`** and will silently
>   embed a STALE wheel. Always `--outdir dist/wheel`, then regenerate, and RUN IT IN THE
>   BACKGROUND (a 120s foreground timeout truncates it).
> - **⚠️ HARNESS TRAPS:** never `wait_until="networkidle"` (heartbeat 3s / sysmon 2s never
>   settles); never pipe a long run through `| tail`; never `pkill -f <pattern>` matching your own
>   command line; `pgrep -c pytest` MISSES `python -m pytest`; **"themes only change colour" is
>   FALSE** — apollo is IBM Plex Mono, so geometry differs per theme.
> - **A page with no chart is not a missing caption** — but check WHY it has no chart before
>   writing that down. `/resources` was excluded on exactly that reasoning and the reasoning was
>   wrong (a JS load-order bug, not absent data).
>
> ### Remaining redesign tail
> **rank 11 — `/path`, `/driving-path`, `/evolution`, `/volatility`** (missing takeaway headers +
> Gantt workspace shells) · rank 12 — Library/Setup sweep (`/workbench`, `/groups`, `/standards`,
> `/margin`, `/card/{name}`, `/wbs/{name}`) · rank 13 — vendored typography (local IBM Plex Mono +
> Barlow woff2; today the stacks are name-only) · rank 14 — prototype token aliases
> (`--cnv`/`--pn2`/`--glow`) + universal `⊞ EXPLORE` drill wiring.
>
> ### Also still open (pre-redesign backlog)
> **AXIS-TITLES batch 3b** — `PENDING` at **5** (`margin_dashboard`, `sra`, `sra_jcl`, `sra_ssi`,
> `volatility`); `sra`/`margin_dashboard` can use `y2Label` (ADR-0302); expect the batch-3a
> collision family and fix it with the `labelFits`-refuses-the-band pattern from `trend.js`, not a
> placement change. Derive every caption from the RENDERING CODE (ADR-0301). Then CRISPNESS 11px
> floor ONLY. Then GUIDED-MODE (5) + VOICE-DECISION (4), parked on the operator. Also: monolith
> split phases 2-3; a DOM caption mechanism for the 13 `NO_SVG_AXES` visuals; `_ANALYSIS_CACHE_MAX
> = 48` (ADR-0292); the `.mpp` probe UI (ADR-0293).
>
> ### DEPLOY (operator has no local clone)
> Download `installer/install-tier2.ps1` from the GitHub web UI and run
> `powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\install-tier2.ps1"`.
> One file; it fetches + SHA-256-verifies the `.mpp` converter from a pinned immutable commit on
> `main`. An existing converter is never destroyed — not by a re-run, a failed download, a
> self-referential `SF_MPXJ_HOME`, a junction, or a symlink; a drive root no longer aborts the
> install (all executed on Windows in CI, ADR-0300). Offline: Code -> Download ZIP, run from
> inside the extracted folder.




# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
