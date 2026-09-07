# Kickoff prompt — next session

> Paste the block below verbatim to start the next session.

---

**PR state (2026-09-07): this session's draft PR (number in the SESSION-LOG follow-up line) carries WP8 + /wbs at v1.0.242 on `claude/polaris-audit-resume-uw726u`, branched on `main` @ `b1cd1739` (the #644 squash). Read `main`'s run #1763 for `b1cd1739` and the PR's checks on its FINAL head first (a red cell on a tree byte-identical to a green head is a runner claim: compare TREE hashes). Once merged, branch FRESH.**

Work the POLARIS² audit's plan-forward (Schedule-Manipulation-Analysis-Tool). Read docs/STATE/HANDOFF.md FIRST
(auto-injected), then **docs/STATE/AUDIT-2026-08-27-REPORT.md** — the campaign's consolidated report and repair
roadmap (WP8, ADR-0472), pinned to the tree by `tests/guards/test_audit_report_wp8.py` (every ledger row registered,
every roadmap row priced or owned, a nine-figure census recomputed by method — re-measure, never edit by hand). As
of last close: **v1.0.242 · highest ADR 0472 — THE CAMPAIGN IS CLOSED (WP0–WP8, ADR-0440..0472)**; /wbs is the EIGHTH
page on the Claude Design layout (ADR-0471). Campaign decisions (operator, 2026-08-27, standing): SOLO lead ·
fix-as-verified · BOTH folder-ask builds. QC-1/QC-2 bind every session — ADR-0393, pinned by
tests/test_standing_rules.py. `git fetch origin` before you branch, number an ADR, or commit — and RE-fetch before
writing the docs. **The container may have NO project install** (the preflight's `[ok] python` is an interpreter
check): `python3 -m pip install -e '.[dev,browser]'` (playwright 1.62 · ruff 0.16.6 · pytest 9.1 · mypy 2.3) and
`pip install build` before measuring anything; the vendored Chromium is under `/opt/pw-browsers`.

⇢ WHAT'S DONE — do not re-open. WP0–WP7 as recorded in the ledger; **WP8** (ADR-0472): the report's 78 register rows ·
43 roadmap rows in testimony-tier order (T1 a cited figure could be WRONG · T2 misread · T3 the record · T4 controls and
rendering · T5 process · T6 organizational) · the census with methods · the closures made by re-measurement: the `176
round(` figure retired (AST calls 325 outside `engine/metrics`, 45 inside) · ADR-0466's expression-string waits EMPTY
(0 of 15) · ADR-0451's /volatility four themes (a DOM census) · ADR-0470's /card artboard EXECUTED (`setScreen('ic')`) ·
TEST-01 and ENG-DEAD-01 (grep) · DOC-01 FIXED (FINAL-REPORT's headline tempered, `test_docs` pin) · **UI-03** NEW and
ATTRIBUTED (every page scrolls sideways at 1440: the hidden `[data-sf-hint]::after` box on right-aligned Reset-view
buttons; priced S, R-20, NOT fixed blind). **/wbs** (ADR-0471): the artboard executed (`setScreen('wr')`), the
masthead-first order, the navigation strip (`_version_chips` DESCENDED into `components.py` with `route` / `cursor_id` /
`noun`; /card byte-identical), the picker in the options position; not ported: the row click (R-22), the bars/colour,
the footnote wording (the mock says duration-weighted, the engine counts), the Continue footer. Do NOT re-derive any of
it — read the two ADRs and the report.

⇢ ASK FIRST (operator questions; do not build on the answer you assume — the report's §5 names the rows each decides):
(a) TX-03 — keep the model dropdown's catalog probe firing BEFORE the acknowledgment, or gate it too? (R-12) (b) IMP-05 —
on a P6 XER should HMI/BEI keep reading the PLANNED dates as the baseline, or read N/A until a baseline project is
exported? A Fuse export on an XER settles the parity leg (R-02). (c) the /onepager-compare rulings (swimlane move ·
threshold · one vs three slides) — and does its .pptx open in PowerPoint? (R-31) (d) #635's /integrity with UID 152 —
does the working-day move read right? (R-30) (e) /forecast's chips with two files; the parent-folder question on `/`;
/trend's chips; T-01 (which page, which zoom, a screenshot) · I-01 (which finding, which two files) · the /analysis lag
(R-23 · R-24 · R-29). UNKNOWABLE and closed: the blank-header banner, the 08-26 incident (R-43).

⇢ NEXT — once the PR is merged, branch FRESH (`git fetch --prune origin && git checkout -B <branch> origin/main`).
Work the report's §3 in order, one row per unit of work, each commit-able (red-first → mutation proofs by name → the
full gate → an ADR → the state docs → a draft PR): **R-01 FIRST** — `evm.py`'s ACWP `actual_cost or 0.0` on a mixed
cost-loaded population: a two-task fixture with one `actual_cost=None`, a red test that CPI/TCPI read NA-or-disclosed
(an `actuals_missing_count`, JCL's ADR-0463 shape), the Fuse EVM export the parity leg; then **R-03** (dcma14's two
parity-mode roundings — build the ±0.5 d / 44.5 d fixture, ASK for the Acumen run, never flip blind) · **R-04** (classify
the 325 `round()` sites by exposure with the census script; render /sra and /jcl on a half-day fixture) · **R-09** (the
`.catch` conflation — a browser test that stubs `SFChartFrame.axisTitles` to throw, then a shared helper across the 13
modules) · **R-13** · **R-18** (NUM-01, UNVERIFIED — grep PARITY-REPORT for tolerance-accepted families) · **R-20** (UI-03:
render the tooltip box only on hover/focus; pin `scrollingElement.scrollWidth <= innerWidth` across the census's 34 page
states, red-first) · **R-21** · **R-22** · **R-32** (CI-04) · **R-39**. PLUS the design page owed each session:
**/standards** (Control Standards and Execution Indices, `setScreen('sd')`) or **/scorecards** (`'sk'`) — the recipe:
`npm pack react@18.3.1 react-dom@18.3.1 @babel/standalone@7.29.0`, patch `support.js` to the local files with the SRI
constants blanked, `python -m http.server --bind 127.0.0.1`, seed `sfredux-screen` / `sfredux-guided=1` /
`sfops-boot.skipNext=true` / `sfredux-theme`, screenshot `section[data-screen-label]` in four themes, DOM-census it
BEFORE writing a line; measure the pristine page (Tier-1 renders + a four-theme census incl. `scrollingElement.scrollWidth`),
write the layout tests red-first, keep every panel verbatim, mutation battery on scratch copies under `PYTHONPATH`.
/compare (10) stays a feature (M-L). Each unit ends commit-able; the wheel + nine installers rebuild as the LAST step.

⇢ Traps paid for, by name (2026-09-07 first): a figure without a method is a rumour — pin the method with the number ·
a census instrument that names the literal it censuses self-matches — exclude its own file · the family regex belongs
on id/class VALUES, never raw markup (`<span` matches `pan(?!d)`) · element boxes cannot see a pseudo-element — measure
`document.scrollingElement.scrollWidth` · the preflight's `[ok] python` is an interpreter check · a shared helper
descends when a second extracted module refers to it; prove the first caller unchanged by render diff · a single-card
artboard's migration is the ORDER · a snapshot worktree's lockstep pin fails by construction after an installer rebuild —
map the `F` onto `--collect-only` · the Library/Control screens boot with the canvas's own keys · `git fetch --deepen=300`
may leave the clone shallow and the installer build still succeeds · `str(exc)` is not a sanitizer · a boundary rule is a
census · garbage that parses to a default is a fabricated figure · old-style `git merge-tree` prefixes every line —
`--write-tree` · merge on the DESIGNATED branch, offer the fast-forward · a page's `.panel` count includes the chrome's
Ask panel · Excel truncates a sheet name to 31 characters · `ls` a test path before filtering its run · `"&mdash;"` is
never a VALUE sentinel · a mutation must LAND before its verdict counts · a module-level name in an extracted page
module needs the `X as X` re-export in `web.app` · `python -m pytest` puts CWD on sys.path; CI's plain pytest does not —
`from web.<module>` · rebuild the wheel + nine installers as the LAST step · browser-job ceiling 25m · compare TREE
hashes before blaming a squash merge · never measure a tree a battery is mutating.

⇢ Measured-false / deliberately-held — do NOT re-chase (the report's HELD and CLOSED rows carry each measurement):
`late_start` for a floored task stays `LF − duration` · the S-curve & finish walk on /forecast · the mock's P10–P90
window / target chip / SPREAD column · CI-03 as a "slow first paint" (REFUTED) · the `defer` attributes · the
change-effects deltas · the legal 25 % Size floor (R-26) · `path_evolution.js:515`'s catch (R-09's named instance) ·
/driving-path's empty-corridor hint (R-26) · /evolution at operator scale (R-27) · the g-head sizing duplication ·
`#uiScale` is NOT dead · the Name-column floors (R-26) · MF-05 · MC-01 parity leg · ADR-0417/0419 fixtures · the
`citations.reattach` pin · the 6 dead E501s · the evolution 0 % cell (R-08) · Insufficient-Detail V05/V06 + TP2 (BLOCKED,
operator-owned) · the compare page's 118-pt summary column · the artboard's ⑥ EVM ledger and ⑦ SPI(t)-by-WBS on
/performance · MF-07/09/10 and MC-08 (R-06, unverifiable as filed) · IMP-04 (R-07) · JS-02 as a leak · IMP-02's tolerated
gaps · `/margin/confirm`'s all-unknown tick list as a deliberate "no margin" · the pre-consent catalog probe as a defect
(R-12 — ask, do not gate blind) · the WBS mock's footnote wording (R-11) · the 176 (R-38, retired).
