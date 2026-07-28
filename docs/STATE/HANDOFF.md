# Handoff — 2026-07-28 (the Ultracode UI redesign: 9 rounds shipped; v1.0.119)

> ## STATUS (current) — NOTHING IN FLIGHT. Branch `claude/schedule-forensics-continue-gkju7l` restarted at merged `main` `a7a06fc`, tree clean. Version **1.0.119**. Highest ADR **ADR-0303**. **#451-#471 ALL MERGED; no open PRs.**
>
> ### What this session did: the operator's design bundle became the actual UI
> The standing instruction was to redesign the UI from `00_REFERENCE_INTAKE/` **using Fable 5
> Ultracode** (ADR-0240). Nine orchestrated rounds shipped as nine merged PRs (#462-#471), each
> one: survey/plan or spec -> implement -> TWO adversarial verifiers (full gate + four-theme
> chromium fidelity) -> a lead that re-verifies every claim before ruling SHIP/HOLD.
>
> - **THE PANEL CONTRACT IS THE DELIVERABLE.** `base.css` owns the vocabulary
>   (`.panel-head` / `.sf-tools` / `.prov-chip` / `.sf-take` / `.sf-drawer` / `.is-big` /
>   `.page-kicker` / `.page-lede` / `.ctl-kpis`+`.ctl-kpi`(+`.k-edge` left-edge variant) /
>   `.sf-pill`(p-ok/p-warn/p-bad) / `.verdict-band`(+`vb-*`,`.vb-stack`) / `.finding.cite-card`)
>   and **`static/panelkit.js`** drives the three-glyph toolbar with EXACT strings
>   `▦ DATA`/`▦ HIDE DATA`, `⤓ EXCEL`, `⛶ ENLARGE`/`⛶ SHRINK`. `app.py` helpers
>   `_panel_head` / `_shell_tools` / `_prov_chip` / `_pair_prov_chip` / `_series_prov_chip` are the
>   ONLY way to emit it. **Never write a parallel vocabulary** (ADR-0298's one-convention law).
> - **PAGES CONVERTED (rounds 1-9):** home/imp · `/mission` · `/analysis` · `/evm` · `/compare` ·
>   `/integrity` · `/portfolio` (the lead's 7-rank CORE QUEUE, complete) · `/ribbon` +
>   `/scorecards` (rank 8) · `/trend` + `/curves` + `/scurve` (rank 9).
> - **REMAINING TAIL (the lead's ranked plan, verbatim):** **rank 10 — `/cei`, `/performance`,
>   `/resources`, `/forecast`** (per-visual normalization; RECOMMENDED NEXT) · rank 11 — `/path`,
>   `/driving-path`, `/evolution`, `/volatility` (missing takeaway headers + Gantt workspace
>   shells) · rank 12 — Library/Setup sweep (`/workbench`, `/groups`, `/standards`, `/margin`,
>   `/card/{name}`, `/wbs/{name}` kicker/spine placement) · rank 13 — vendored typography (local
>   IBM Plex Mono + Barlow woff2; today the stacks are name-only) · rank 14 — prototype token
>   aliases (`--cnv`/`--pn2`/`--glow`) + universal `⊞ EXPLORE` drill wiring.
>   The full rank-by-rank plan with files/risks/tests per item is in
>   `/tmp/.../tasks/w94dnscsb.output` — **if that scratch file is gone, the ranks above plus this
>   handoff are the authority**; re-derive detail from the prototype, not from memory.
>
> ### THE FIVE STANDING REQUIREMENTS — every one exists because a round shipped the defect it now prevents. Carry them into every redesign round.
> 1. **JARVIS PROBE + PROMOTION CENSUS.** `hud.css`'s broad `html[data-theme=jarvis] .panel` /
>    `body` / `button` rules silently out-rank new contract classes. Bit us THREE times (apollo
>    scanline, jarvis `--bgfx` dead token, jarvis verdict-band). Grep `hud.css` AND `sf-themes.css`
>    for competing rules, count `.panel` elements before/after (**an element that GAINS `.panel`
>    joins the fight** — round 6's trigger), and PROBE COMPUTED STYLES in real chromium. A defined
>    token is not a painting token.
> 2. **PANELKIT IS A PER-PAGE INCLUDE.** A page can wear the complete toolbar markup and be inert
>    (`/evm`, round 4). Prove the script loads **and** click ⛶ for real, reading `is-big` back.
>    `_page` cache-busts `src` to `?v=` — match a SUBSTRING, never the exact path.
> 3. **LOADED-TERMS AUDIT WITH A CONTROL.** Run every new visible string through
>    `ai.citations.introduces_loaded_terms(source="", …)` AND run `"deliberate concealed fraud"`
>    in the same session — it must return `True`. **A gate that never fires is unproven.**
> 4. **SHAPE THE PROOF TO THE PAGE'S HAZARD.** Forms → byte-diff every `<form>` vs an
>    `origin/main` worktree in two states + a live round trip (`/portfolio`). Embedded CSP JSON →
>    byte-capture (`/integrity`). Parity-relevant tables → dump the numeric content both sides and
>    diff (`/ribbon`). EVM → prove the diff contains no arithmetic.
> 5. **THE AXIS CAPTIONS ARE FINISHED — DO NOT TOUCH THEM.** ADR-0298/0301/0303, 648 renders
>    measured clean. When converting a charted page, prove the `SFChartFrame.axisTitles` call sites
>    are BYTE-IDENTICAL to `origin/main` (md5 the call + its argument lines). If a toolbar change
>    would move a caption, STOP AND REPORT — do not adjust.
>
> ### Other hard-won rules from this session
> - **A CONTRACT IS A VOCABULARY, NOT A STAMP** (round 9): count what a panel actually contains
>   before choosing panel-scope vs visual-scope controls. `/curves` = 1 chart/panel, so its
>   existing button carries `data-sf-big` (a head ⛶ would be a SECOND enlarge); `/trend` = 20
>   charts/panel, so its ⛶ stays chart-scoped (a shared `.is-big` would desync 20 labels).
> - **CHECK MERGED `main` BEFORE CALLING A PATTERN A DEFECT** (round 9): the flagged `/trend` ⤓
>   buttons were byte-for-byte the already-shipped Mission-wall precedent. "Looks wrong" and
>   "differs from what we ship" are different findings.
> - **READ THE ENGINE'S ARTIFACT, DON'T RECOMPUTE IT** (round 8): the ribbon tooltip's verdict word
>   is read off the class `_ribbon_cell_class` already assigned. A second derivation can disagree
>   with the first under exactly the inputs a testimony context will probe.
> - **WHEN A VERIFIER DIES, THE WORK IS UNVERIFIED** (round 8): the lead agent failed on exhausted
>   usage credits after two clean verifiers. The orchestrator performed the lead role itself on
>   another model rather than ship. Distinguish "the check passed" from "the check ran".
> - **⚠️ BUILD TRAP:** `python -m build --wheel` writes to `dist/`, but
>   `tools/installer/build_installers.py` defaults to **`dist/wheel/*.whl`** — it will silently
>   embed a STALE wheel. Always `python -m build --wheel --outdir dist/wheel`, then
>   `python tools/installer/build_installers.py`, and RUN IT IN THE BACKGROUND (a 120s foreground
>   timeout truncates it and leaves tier3 a version behind).
> - **⚠️ HARNESS TRAPS:** never `wait_until="networkidle"` (heartbeat 3s / sysmon 2s — never
>   settles); never pipe a long run through `| tail` (buffers to EOF); never `pkill -f <pattern>`
>   where the pattern is in your own command line; `pgrep -c pytest` MISSES `python -m pytest`
>   (use `pgrep -af "python -m pytest"`); **"themes only change colour" is FALSE** — apollo is
>   IBM Plex Mono, so geometry differs per theme and must be measured per theme.
> - **A page with no chart is not a missing caption** — `/resources` needs a resource picked and
>   `/margin` needs tasks named "margin"; with the golden fixtures both correctly show a no-data
>   note. Flagging it sends the next session chasing a bug that does not exist.
>
> ### Also still open (pre-redesign backlog)
> **AXIS-TITLES batch 3b** — `PENDING` is at **5** (`margin_dashboard`, `sra`, `sra_jcl`,
> `sra_ssi`, `volatility`); `sra`/`margin_dashboard` can use `y2Label` (ADR-0302); expect the
> batch-3a collision family (X caption vs inline value labels at the plot's bottom-right) and fix
> it with the `labelFits`-refuses-the-band pattern from `trend.js`, **not** a placement change.
> Derive every caption from the RENDERING CODE (ADR-0301 — the spec's table was wrong for 6 of 8
> modules). Then CRISPNESS 11px floor ONLY. Then GUIDED-MODE (5) + VOICE-DECISION (4), parked on
> the operator. Also: monolith split phases 2-3; a DOM caption mechanism for the 13 `NO_SVG_AXES`
> visuals; `_ANALYSIS_CACHE_MAX = 48` (ADR-0292); the `.mpp` probe UI (ADR-0293).
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
