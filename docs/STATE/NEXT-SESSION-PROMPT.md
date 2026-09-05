# Kickoff prompt — next session

> Paste the block below verbatim to start the next session.

---

Resume the POLARIS² full-tool audit campaign (Schedule-Manipulation-Analysis-Tool). Read
docs/STATE/HANDOFF.md FIRST (auto-injected), then **docs/STATE/AUDIT-2026-08-27.md — the
campaign's live ledger (appended per-WP, never batch-written)**; the 2026-08-16 ledger stays the
historical row source for the WP6b tail. As of last close: **v1.0.238 · highest ADR 0465 —
/onepager-compare SHIPPED (ADR-0465): the operator's two-list One-Pager compare, built as its own route,
page module, painter and .pptx export on the Claude Design layout (the FIFTH design page — built NEW on
the family's "Library One-Pager Timeline" artboard rather than migrated); /onepager's ADR-0446 intake,
painter and export byte-identical.** **This session's draft PR is **#639** (`claude/polaris-audit-resume-e9t5h1`
on `origin/main` @ `46a91fd2`) — read ITS checks on its FINAL head first (a red cell on a tree
byte-identical to a green head is a runner claim: compare TREE hashes before believing it); the operator
merges. Then branch FRESH from `origin/main` (`git fetch --prune origin && git checkout -B <branch>
origin/main`).** `main` is green: #1737 (the #637 squash) and #1740 (#638) both `success`. Campaign
decisions (operator, 2026-08-27, standing): SOLO lead · fix-as-verified · BOTH folder-ask builds.
QC-1/QC-2 bind every session — ADR-0393, pinned by tests/test_standing_rules.py. `git fetch origin`
before you branch, number an ADR, or commit — and RE-fetch before writing the docs. STANDING OPERATOR
ASK (2026-09-03): migrate at least ONE page per session onto the Claude Design layout — design truth
`00_REFERENCE_INTAKE/references/design_handoff_mission_ops_redesign/Mission Ops Redesign v2.dc.html`,
method ADR-0451/0456/0460/0464/0465, rules docs/DESIGN-SYSTEM.md §9; done: /volatility (04), /cei (06),
/trend (05), /forecast (09), /onepager-compare (Library One-Pager Timeline, new); **/performance (07 How we
execute) is next**; /compare (10) is a feature change (needs /integrity's ledger); the family carries
`cd-grid-2`, `cd-grid-12`, `cd-stack`, `cd-master`, `cd-note`, `cd-block`/`cd-read`; a script-CREATED
master mounts into a `#<page>Master` slot, a SERVER-rendered stepper is MOVED into it (`appendChild`, same
nodes); a page with no version cursor still wears the family (DESIGN-SYSTEM §9).

⇢ WHAT'S DONE — do not re-open. 2026-08-27..09-05 (ADR-0440..0464, v1.0.222..237, all MERGED): WP0
(timescale sanitized, scale root-caused), WP1 (M1 census), WP2 (M3 + M5), the diagonal header, WP3 (M4
SRA grid), WP4 (CI-01/02, the route-coverage instrument, cui-guard), WP5 (folder gestures), CI-03
(chartframe.js in the head), CF-01 (working days, the finish activity named), WP6 COMPLETE (the six ledger
highs CPM-01 · CPM-02 · MC-02 · MC-03 · MAN-01 · REC-02 all CONFIRMED and fixed red-first), /volatility
/cei /trend /forecast on the design. 2026-09-05 (b) (ADR-0465, v1.0.238, PR #639): **/onepager-compare** —
`reports/onepager_compare.py` (`item_key` = the ADR-0446 lane merge key + the whitespace-collapsed
casefolded name, the ONLY key the sheet carries; `compare_onepager_docs` → slipped / pulled in / start
moved / unchanged / new / removed / ambiguous, deltas `current − prior` in CALENDAR days, a rename or a
swimlane move = one removed + one new with the names seen on both sides COUNTED and said, a duplicate
name under one swimlane = a collision reported by sheet and row and compared with nothing;
`build_compare_layout` = the ADR-0446 frame + a 118-pt summary column, per row a solid current shape, a
dashed ghost for the prior, an arrow prior-finish → current-finish, `+N cal d` / `−N cal d` on the label,
NEW / REMOVED / DUPLICATE NAME tag boxes, the packer reserving all of it) · `static/onepager_compare.js`
(painter + two-slot intake; a stray drop refused) · `render_onepager_compare_pptx` (dashed `noFill`
ghosts, `triangle`-headed connectors, `flipH` pull-ins, two-run labels; `_Slide.shape(dash=)`, `arrow`,
`text_runs` added, every existing call byte-identical) · `web/onepager_compare.py` (the design rows; the
takeaway quotes only rendered cells; the three unanswered rulings stated ON the page as the current rule)
· routes · five `SessionState` fields · the LIBRARY rail · `_EXPLAINERS` · i18n ×8 × 4 · `.opc-*` CSS ·
every sweep joined with a deliberate re-baseline (M1 row · oracle labels +30 / `{200: 44, 400: 17, 422: 4}`
· DD ledger `(onepager_compare.js, 131)` · r11 sites 29 → 30 · VIEW_MODULES · assets 68 → 69 · the rail
pin). Red-first at import / 404 / no svg; 37 + 11 + 4 green; mutations 15/15 + 12/12 red by name;
four-theme census zero errors. Do NOT re-derive the compare semantics — read ADR-0465.

⇢ ASK FIRST (operator questions; do not build on the answer you assume): (a) NEW — the compare page's
three rulings, each a one-place change: does a task that changed SWIMLANE count as MOVED (keep its deltas,
tag it) or stay one REMOVED + one NEW as today (`item_key` / the ADDED–REMOVED pairing)? is there a slip
THRESHOLD below which an item reads unchanged — none today, any move of one calendar day is a change (a
constant in `_status`)? should ⤓ POWERPOINT on /onepager-compare ALSO ship the single-version slides
(prior · current · compare = three slides) or stay one (`render_onepager_compare_pptx`)? Also: does the
compare .pptx open in PowerPoint (UNVERIFIED here — LibreOffice/PowerPoint absent; ADR-0446's did). (b) on
v1.0.237+, /forecast with two or more files: do the chips and the re-homed ◀ Prev / Next ▶ / ▶ Auto-play in
the masthead strip move the drift chart, and does the pill name the version expected? (c) #635's: on
/integrity with UID 152 as the target, does the target line's working-day move read right against the
file's calendar? (d) #631's / #630's stand: the parent-folder question on `/`; /trend's chips; I-01 · T-01 ·
the residual /analysis lag. UNKNOWABLE and closed: the blank-header banner, the 08-26 incident.

⇢ NEXT — after #639 merges, branch FRESH. **WP6b** — the ledger TAIL by the same method (re-derive each
finder's line from `git show 1b833c6a:<path>`, build the refuting check, fix as verified): CPM-03/04 ·
MF-03/04/06..10 (MF-05 stays do-not-fix-blind) · MC-04..08 · IMP-02..06 · MAN-02/03 · JS-02..06 ·
TST-02/03; plus RC-02's 3 never-2xx routes (`GET /export/{fmt}/resource-drill` ·
`GET /export/{fmt}/ribbon-drill/{name}` · `POST /sra/factor-table`) and 15 never-adverse POSTs → **WP7**
(thin dims, `ai/txlog.py` first — Law 1) → **WP8** (consolidated report + roadmap by testimony risk).
PLUS the design page owed each session: **/performance (07 How we execute)** — recover artboard 07 by
EXECUTING the canvas over loopback HTTP (`npm pack react@18.3.1 react-dom@18.3.1 @babel/standalone@7.29.0`
into `pkgs/`, `support.js` patched to `./pkgs/…` AND its three `_SRI` constants blanked, seeds
`sfredux-screen=<key from the canvas's setScreen('…') calls>`, `sfredux-guided=1`,
`sfops-boot.skipNext=true`, `sfredux-theme`; `python -m http.server --bind 127.0.0.1`; screenshot
`section[data-screen-label="07 How we execute"]` in four themes), then rows over VERBATIM panels,
red-first + mutations by name, the four-theme census moved on the design's keys only. Observed, not fixed
blind (own rows): `evm.py`'s `actual_cost or 0.0` ACWP on a mixed population (an EVM parity family with an
Acumen oracle) · `path_evolution`'s pure-logic per-version critical list. CI-04 (the /driving-path
header-row equality race, #632's docs-only diff) is the remaining CI candidate: measure first, induce the
race, fix where the dependency lives — never a wider wait. Each WP ends commit-able: red-first → mutation
proofs → full gate → ADR → state docs → draft PR.

⇢ Traps paid for, by name (2026-09-05 (b) first): two charts that caption identically HASH identically —
a content-keyed freeze needs distinct content per site · a "missed" mutation is a FIXTURE question first —
put the two code paths on different rows · a counting pin must count what it NAMES (`<div class=panel`
matched `panel-head`; `<tr><td>` matched a second table; a shared class matched the table beside the SVG)
· a module-shared browser session is STATE — load unconditionally · the unit is part of the provenance at
DESIGN time (calendar days because the sheet has no calendar) · `python -m build` is NOT in the container
— `pip install build` · the installer script refuses a graft-boundary MPXJ ref; `git fetch --deepen=300`
moved it to `42d92dc9` this time — check the resolved ref · state the operator's unanswered rulings ON THE
PAGE, never assume them silently · a finder's line number is a DATE — `git show <sha-as-of-then>:path` ·
a floored FINISH must reach the float — `total_float <= LF - EF` on every task · two ends of one link
share one ruler · "guarded in two places" is a count, not a proof · an ABSENT figure at a formula's
boundary shows up as a discontinuity · a documented swap pinned by a parity test is a measurement waiting
to become exact · a finder's row can be the small half — sweep the route table with the hostile state
against a control · a test red on BOTH trees proves nothing · a fixture that lost its purpose is
re-baselined to keep its PURPOSE · `file://` is not a browser origin — serve the canvas over loopback HTTP
· a premise pin on panel ORDER fires on a re-arrangement — re-derive the order, never the assertions · the
container may have NO package installed — `pip install -e '.[dev,browser]' --retries 8 --timeout 180` and
check the exit code · the editable install's metadata goes stale after a version bump — `pip install -e .
--no-deps --no-build-isolation` · never measure a tree a battery is mutating — scratch copies,
`PYTHONPATH`, never `git checkout --` · a `.catch` that swallows a ReferenceError prints a false sentence ·
a mutation must break what the test guards, not the test's constant · a line-number-keyed pin is edited
with SAME-LINE-COUNT replacements and new code BELOW the last pin · compare TREE hashes before blaming a
squash merge · `python -m pytest` puts CWD on sys.path; CI's plain pytest does not — `from web.<module>`,
never `from tests.…` · rebuild the wheel + nine installers as the LAST step, after the final source edit ·
browser-job ceiling 25m.

⇢ Measured-false / deliberately-held — do NOT re-chase: `late_start` for a floored task stays
`LF - duration` · the S-curve & finish walk on /forecast (it is /scurve's chart) · the mock's P10–P90
window, target chip, SPREAD column and "plan to the window" line · CI-03 as a "slow first paint" (REFUTED)
· the `.catch` conflation (a UI-map row) · the `defer` attributes on resources / performance /
margin_dashboard / volatility · the change-effects table's deltas (already working days) · the legal 25%
Size floor look · `path_evolution.js:515`'s misattributing catch · /driving-path's empty-corridor hint ·
/evolution at operator scale (needs ≥2 versions) · the g-head sizing duplication · `#uiScale` is NOT dead ·
the Name-column 200px + Chromium ~53px resize floors · MF-05 · MC-01 parity leg · ADR-0417/0419 fixtures ·
the `citations.reattach` pin · the 6 dead E501 per-file-ignores · the evolution 0% cell ·
Insufficient-Detail V05/V06 + TP2 (BLOCKED, operator-owned) · the compare page's summary-column width (118
pt — a design choice, re-price only if the operator asks). CLOSED: the /mission 30-hosts-vs-9-cf-bars
question · the diagonal timeline header (ADR-0445) · the One-Pager in PowerPoint · CI-01/CI-02 (ADR-0455)
· CI-03 (ADR-0461) · CF-01 (ADR-0462) · WP6's six highs (ADR-0463) · the 2026-09-04 One-Pager compare
request (ADR-0465). OBSERVED, not fixed blind: the sticky controls bar over the sticky header at the top
scroll position; the docx/xlsx writers stamping CUI regardless of mode; `evm.py`'s ACWP none-vs-zero on
a mixed population.
