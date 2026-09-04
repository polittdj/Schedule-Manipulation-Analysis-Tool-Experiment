# Kickoff prompt — next session

> Paste the block below verbatim to start the next session.

---

Resume the POLARIS² full-tool audit campaign (Schedule-Manipulation-Analysis-Tool). Read
docs/STATE/HANDOFF.md FIRST (auto-injected), then **docs/STATE/AUDIT-2026-08-27.md — the
campaign's live ledger (appended per-WP, never batch-written)**; the 2026-08-16 ledger stays the
historical row source for WP6. As of last close: **v1.0.236 · highest ADR 0462 — CI-03 ROOT-CAUSED
and FIXED (ADR-0461: every fetch-driven chart module draws inside its fetch callback and
`chartframe.js` — the only `SFChartFrame` — was emitted AFTER `</main>`; the parser yields while it
downloads a sync script, so the callback could run first, throw, and the module's `.catch` printed
"Failed to load the … data." with zero captions; the tag now sits at the end of the layout HEAD, five
premise pins re-derived, the sweep's zero-caption line carries its diagnosis) and the operator's
counterfactual report FIXED (ADR-0462: /integrity printed a calendar-date subtraction as "working
day(s)"; both deltas are now the CPM's working-minute move over the calendar's day, the project-finish
ACTIVITY is named, the target line carries its own move, and one line says the two finishes are
different activities).** This session's draft PR **#635** is open from `claude/polaris-audit-resume-xqte7c`
(branched from `origin/main` @ `66364af7`, the #634 docs merge; `main`'s run **#1724** for `66364af7`
concluded `success` at 13:29Z). Read #635's own checks on its CURRENT head FIRST (every docs push
restarts its run — the concurrency group cancels the previous one); #1721 for the #633 merge
concluded `success` in full; #632 was closed unmerged. Campaign decisions (operator, 2026-08-27,
standing): SOLO lead · fix-as-verified · BOTH folder-ask builds. QC-1/QC-2 bind every session —
ADR-0393, pinned by `tests/test_standing_rules.py`. git fetch origin before you branch, number an
ADR, or commit — and RE-fetch before writing the docs. STANDING OPERATOR ASK (2026-09-03): migrate at
least ONE page per session onto the Claude Design layout — design truth `00_REFERENCE_INTAKE/references/
design_handoff_mission_ops_redesign/Mission Ops Redesign v2.dc.html`, method ADR-0451/ADR-0456/ADR-0460,
rules `docs/DESIGN-SYSTEM.md` §9; done: /volatility (04), /cei (06), /trend (05); **the 2026-09-04 (d)
session did NOT migrate a page** (the operator's live report took the slot) — /forecast (09) is owed
first, then /performance (07); /compare (10) is a feature change (needs /integrity's ledger); the family
carries `cd-grid-12`, `cd-stack`, `cd-master`, `cd-note`; a script-created master mounts into a
`#<page>Master` slot inside `.cd-cursor` (DESIGN-SYSTEM §9).

⇢ WHAT'S DONE — do not re-open. 2026-08-27 (ADR-0440, v1.0.222, MERGED): Timescale load path
sanitized; M2 (16 tests). 2026-08-28 (ADR-0441, v1.0.223, MERGED): the operator's 12.3-year evidence
relocated the live defect to SCALE. 2026-08-31 (ADR-0442, v1.0.224, MERGED): WP1 M1 census COMPLETE
(`test_ui_control_effect_census.py`, sitewide and computed). 2026-08-31 (ADR-0443, v1.0.225): WP2 M3 +
M5 COMPLETE (59 + 8 + 10 tests; five defects fixed red-first; the A2 reduced-motion pin computed).
2026-09-01 (ADR-0444, v1.0.226, MERGED #620): the timescale's EDGE bands clamped. 2026-09-01
(ADR-0445, v1.0.227, MERGED #621): the diagonal header ROOT-CAUSED (`hud.css`'s
`[data-sf-hint]{position:relative}`; `:where()`); UI-01's `sizeGrip` DELETED. 2026-09-01 (ADR-0446,
v1.0.228, MERGED #621): the One-Pager (`/onepager`, SVG preview + native PowerPoint shapes).
2026-09-02 (b) (ADR-0447..0451, v1.0.229): the six-item operator batch (demote ladder · bow-wave
target pin · /analysis DOM budget + windowing · field ROLES · /volatility on the design). 2026-09-03
(ADR-0454, v1.0.232, MERGED #626): WP3 · M4 COMPLETE (the SRA grid driven with a REAL clipboard; six
silent defects fixed). 2026-09-03 (docs #627): the intake manifest regenerated after the operator's six
web uploads (a web upload bypasses the pre-commit guard). 2026-09-03 (c) (ADR-0455 + ADR-0456,
v1.0.233, MERGED #628): WP4 COMPLETE (CI-01 GitHub-side · CI-02 REFUTED · the route-coverage instrument
· `cui-guard` CI job · every workflow dispatchable) + /cei on the design. 2026-09-03 (e) (ADR-0457 +
ADR-0458, v1.0.234, MERGED #630): I-01 root-caused to session POPULATION (page names it) · T-01
measured working · /analysis re-aim incremental. 2026-09-04 (ADR-0459 + ADR-0460, v1.0.235, MERGED
#631): WP5 SHIPPED (the three folder gestures named; a PARENT folder is ASKED about) + /trend on the
design (`vol-*` aliased onto `cd-*`). **2026-09-04 (d) (ADR-0461 + ADR-0462, v1.0.236, this PR):
CI-03 CLOSED — R1 (asset held 1.5 s) blanked /cei /curves /forecast /scurve /trend while the four
`defer`red pages survived; R2 (NO delay, 6 CPU hogs + CDP 8×, fresh browser, 12 cold loads × 3
routes) reproduced `Failed to load the forecast-drift data.` 1/36 with the first caption never later
than 2,494 ms (the 5-s wait never bit — slow paint REFUTED); FIX one moved line in `web/chrome.py`;
`test_chartframe_load_order_browser.py` (8) red 8/8 pristine → green; sleep-neutralised mutation red
by name. CF-01 CLOSED — engine `7 == 5` + `AttributeError: finish_uid` red → green; page 3 pins red on a
pristine scratch copy → green; one data pin re-baselined 7 → 5 with the reason.** Do NOT re-run R1/R2,
do NOT widen the sweep's timeout, do NOT add per-module `SFChartFrame` guards (the head placement is
the fix), and do NOT re-derive the counterfactual unit by hand — run the engine.

⇢ ASK FIRST (operator questions; do not build on the answer you assume): (a) NEW — on v1.0.236,
/integrity with the same pair and UID 152 as the target: the first line names the network's last
activity and the target line carries its own working-day move — does the count read right against the
file's calendar (five-day or seven-day)? (b) #631's: on `/`, pick a PARENT folder holding two project
folders — does the question appear and do both answers land as promised; on /trend with ≥2 files do the
chips move every chart and the drill together? (c) #630's stand: I-01 (which finding, which two files,
folders or Titles) · T-01 (page, zoom, screenshot) · (c) is the residual /analysis lag gone. UNKNOWABLE
and closed: the blank-header banner, the 08-26 incident.

⇢ NEXT — branch FRESH from `origin/main` once this PR merges (`git fetch --prune origin && git
checkout -B <branch> origin/main`); open a NEW draft PR. **WP6** (ledger highs: CPM-01 `cpm.py:1316`
· CPM-02 `driving_slack.py:314` · MC-02 · MC-03 `jcl.py:284` · MAN-01 · REC-02; parity-sensitive rows
through the metric-parity skill; any golden shift = CONFIRMED-DEFERRED, never a silent re-pin; RC-02's
never-reached / never-adverse endpoints are WP6/WP7 rows) → **WP7** (thin dims, `ai/txlog.py` first —
Law 1) → **WP8** (consolidated report + roadmap by testimony risk). PLUS the design page owed from this
session: /forecast (09 Where it lands) — recover artboard 09 by EXECUTING the canvas (npm-pack
React/Babel; `support.js` patched local; seeds `sfredux-screen`, `sfredux-guided`,
`sfops-boot.skipNext`; view four themes), re-home `drift.js`'s own Prev/Next/Play into a `#forecastMaster`
slot, rows over VERBATIM panels, red-first + mutations by name, four-theme census moved on the design's
keys only. CI-04 (the /driving-path header-row equality race, #632's docs-only diff) is the remaining
CI candidate: measure first, induce the race, fix where the dependency lives — never a wider wait.
Each WP ends commit-able: red-first → mutation proofs → full gate → ADR → state docs → draft PR.

⇢ Traps paid for, by name (2026-09-04 (d) first): a wait whose failure reads the same as "not yet"
reports nothing — make the zero case name what it saw · fix the class where the dependency LIVES (one
layout line) rather than the consumer where it bites (`defer` ×4, eleven still exposed) · a `.catch`
that swallows a `ReferenceError` prints a false sentence and no oracle sees it — read the page's own
text · a probe that shows no effect must first prove its intervention landed (every static URL carries
`?v=<version>`; a route glob needs a trailing `*`) · a premise pin that fires is re-derived, never
deleted · a mutation must break what the test guards, not the test's constant (`SLOW_MS = 0` zeroed
the threshold too) · a number's UNIT is part of its provenance — compare units across one page's panels
· two dates that look like a contradiction are two subjects — name them · a pip log's last line can
look green while the install died on a read timeout — check the exit code (`--retries 8 --timeout
180`) · `cd` inside one Bash call moves the shell's cwd for every later call · the lessons log's order
(newest first) is a rule · a mutation that SURVIVES is a claim about the FIXTURE before it is a claim
about the code · a real `webkitdirectory` FileList arrives in filesystem-traversal order — sort by name
· a line-number-keyed pin is edited with SAME-LINE-COUNT replacements and new code BELOW the last pin ·
a byte-frozen page script changes only by a dated re-baseline · an intake screenshot's FILE NAME is
testimony — execute the canvas · two sessions in flight: number ADRs after the in-flight PR's, hold the
version / installers / docs rotation to the end · `build` is NOT in the dev extras (`pip install build`)
· a differential that comes back IDENTICAL is the finding · the page's own sentences on a testimony
surface are the defect even when the banners disclose the state · frame times measured while a battery
runs are noise · isolate native cost by SUBTRACTION in the live page · a `bounding_box()` pointer can
sit below the viewport — assert `scrollTop` moved · `pkill -f <pattern>` kills the shell that runs it
— sentinel files, never process greps · a run's CONCLUSION is the measurement — read the merge
commit's run · compare TREE hashes before blaming a squash merge, and never spend a `main` re-run while
a push is imminent · `spec_from_file_location` + `dataclass` + `from __future__ import annotations`
needs `sys.modules[spec.name] = module` BEFORE `exec_module` · resolve a route template BEFORE dispatch
· every CDN is egress-blocked, the npm registry is not (`npm pack`) · `git reset --soft <base>` stages
exactly `base..HEAD` for the hook · the build container may have NO package installed — `pip install
-e '.[dev,browser]'` before the first test · `tooltips.js` moves `title=` to `data-sf-hint` at load ·
`/root/.local/bin/ruff` shadows the pinned ruff — run `python -m ruff` · prove each half of a two-sided
fix with its OWN revert · a positioning claim is measured by RENDERED `y` and COMPUTED `position` ·
`:where([attr])` for any global rule that sets `position` · `python -m pytest` puts CWD on `sys.path`;
CI's plain `pytest` does not — never `from tests.…`, always `from web.<module>`, and check `pytest
--collect-only -q` before pushing · `git checkout --` is NOT a mutation restore — restore from a `cp`
of the WORKING TREE · a guard with a hand-written population fails OPEN · never pipe a mutation battery
through `head` · the installer build refuses a shallow clone (`git fetch --deepen=300` first; the
2026-09-04 (d) deepen resolved the true MPXJ last touch `42d92dc9`) · rebuild the wheel + nine
installers as the LAST step, after the final source edit · browser-job ceiling 25m.

⇢ Measured-false / deliberately-held — do NOT re-chase: CI-03 as a "slow first paint" (REFUTED by
R2: max first caption 2,494 ms at 8× throttle) · the `.catch` conflation ("Failed to load" for a render
throw) — a UI-map row, byte-frozen scripts, not this queue · the `defer` attributes on resources /
performance / margin_dashboard / volatility (kept: byte-pinned, harmless) · `legend_toggle.js` and the
rest of the post-`</main>` group (no page module calls `SFLegend`; measured by grep) · the change-effects
table's deltas (already working days; pins +7 / +1 / +2 / +9 / +3 hold) · the legal 25% Size floor look
· `path_evolution.js:515`'s misattributing catch · /driving-path's empty-corridor hint · /evolution at
operator scale (needs ≥2 versions) · the g-head sizing duplication · `#uiScale` is NOT dead · the
Name-column 200px + Chromium ~53px resize floors · MF-05 · MC-01 parity leg · ADR-0417/0419 fixtures ·
the citations.reattach pin · the 6 dead E501 per-file-ignores · the evolution 0% cell ·
Insufficient-Detail V05/V06 + TP2 (BLOCKED, operator-owned). CLOSED: the /mission 30-hosts-vs-9-cf-bars
question · the diagonal timeline header (ADR-0445; a report on ≥ v1.0.227 is a NEW defect) · the
One-Pager in PowerPoint (opened) · CI-01/CI-02 (ADR-0455) · CI-03 (ADR-0461). OBSERVED, not fixed
blind: the sticky controls bar over the sticky header at the top scroll position; the docx/xlsx
writers stamping CUI regardless of mode.
