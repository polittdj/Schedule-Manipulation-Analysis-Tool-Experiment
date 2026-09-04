# Kickoff prompt — next session

> Paste the block below verbatim to start the next session.

---

Resume the POLARIS² full-tool audit campaign (Schedule-Manipulation-Analysis-Tool). Read
docs/STATE/HANDOFF.md FIRST (auto-injected), then **docs/STATE/AUDIT-2026-08-27.md — the
campaign's live ledger (appended per-WP, never batch-written)**; the 2026-08-16 ledger stays the
historical row source for WP6. As of last close: **v1.0.235 · highest ADR 0460 — WP5 SHIPPED (ADR-0459: the three folder gestures named on the dashboard; a PARENT folder that holds several project folders is ASKED about — one Project, or one per sub-folder — never guessed; server untouched; the picker path driven with a REAL directory) and /trend is the THIRD page on the Claude Design layout (ADR-0460: the page's own Play all / Step all master re-homed into a masthead cursor strip, one chip per version driving every framed chart's own stepper, the design's rows over VERBATIM panels; `vol-*` cursor vocabulary aliased onto `cd-*`). This session's draft PR is open from `claude/continue-yznv26` (branched from `origin/main` @ `f2be8a0f`; `main`'s run #1706 for the #628 merge = `success`). #630 (ADR-0457/0458, v1.0.234, the operator's evening batch) MERGED to `main` @ `19e74147` at 02:18Z; this session's PR **#631 MERGED to `main` @ `d9bac11a` at 04:55Z** (all eight checks green on the merged head); the branch is restarted on `origin/main`. Read `main`'s run **#1717** for `d9bac11a` FIRST (in progress at this record — a red there is yours to root-cause before building on it); #1714 for the #630 merge concluded `success`.**
Campaign decisions (operator, 2026-08-27, standing): **SOLO lead · fix-as-verified · BOTH folder-ask builds**.
QC-1/QC-2 bind every session — ADR-0393, pinned by `tests/test_standing_rules.py`. **git fetch origin before you
branch, number an ADR, or commit — and RE-fetch before writing the docs.** **STANDING OPERATOR ASK (2026-09-03):
migrate at least ONE page per session onto the Claude Design layout** — design truth `00_REFERENCE_INTAKE/references/
design_handoff_mission_ops_redesign/Mission Ops Redesign v2.dc.html`, method ADR-0451/ADR-0456, rules
`docs/DESIGN-SYSTEM.md` §9; done: /volatility (04), /cei (06), /trend (05 — ADR-0460); next candidates /forecast (09),
/performance (07); /compare (10) is a feature change (needs /integrity's ledger); the `vol-*` → `cd-*` alias is DONE
(third page) — the family now carries `cd-grid-12`, `cd-stack`, `cd-master`, `cd-note`; a script-created master mounts
into a `#<page>Master` slot inside `.cd-cursor` (DESIGN-SYSTEM §9).

⇢ WHAT'S DONE — do not re-open. **2026-08-27 (ADR-0440, v1.0.222, MERGED):** Timescale load path
sanitized; M2 (16 tests) is the dialog's first behavioral coverage. **2026-08-28 (ADR-0441,
v1.0.223, MERGED):** the operator's 12.3-year/2,301-activity evidence relocated the live defect to
SCALE — stale reflow column, density adaptation, fitted opening, 120 ms debounce; instruments
`test_long_span_gantt_browser.py` + `TP5_LongSpan_Synthetic.xml`. **2026-08-31 (ADR-0442,
v1.0.224, MERGED): WP1 M1 census COMPLETE** — `test_ui_control_effect_census.py` is sitewide and
computed (34 page states from the app's own route table; 65 id'd + 358 id-less controls; 8 floor
families; 17-mutation battery), the 27-row UI map is in the ledger, and its first run caught
**UI-01** (drag-resize grips 7×0px) and **UI-02** (sticky proxy raced the fetch), plus **S5**
(windowed `paintRows`: 1,623 ms → 49 ms at 2,280 rows). **2026-08-31 (ADR-0443, v1.0.225): WP2 M3
+ M5 COMPLETE** — `tests/web/test_ui_stepper_autoplay_browser.py` (59 tests) drives all 47 id'd
steppers/autoplay controls, the 138 `sf-frame` trio buttons, the three page masters and the
ADR-0275 coordinator **on a fake clock** (never wall-time sleeps), with **two oracles per control**
(label AND a DOM-shape-agnostic chart digest, itself pinned stable-and-sensitive);
`tests/web/test_ui_chrome_controls_browser.py` (8 tests) drives the REAL `#themeSelect` across
four views, `#themeToggle`, `#uiScale`, language and Task Information;
`tests/web/test_ui_language_redirect_guard.py` (10 tests) is the open-redirect pin. Five defects
fixed red-first: **M3-01** `/mission`'s wall master was never registered with the ADR-0275
coordinator (layout emits `chartframe.js` after `<main>`; the `if (window.SFPlayAll)` guard was
always false — DOM indices 20 vs 24), **M3-02** `/curves` never called `register()` at all
(`/trend` worked only by registering after a `fetch`), **M3-03** `driving_path.js` was the only
animated module of twelve ignoring `prefers-reduced-motion`, **M5-01** the wall framed 9 of 30
tiles (attach-vs-fetch race — a manual `SFChartFrame.scan()` took it 9 → 30), **M5-02** the
Language selector always dumped the operator on `/` (`/language` trusted a `Referer` the app's own
`Referrer-Policy: no-referrer` strips). The A2 reduced-motion pin, which had a hand-written
five-name population while twelve modules are animated, is now COMPUTED and fails closed. Every
`WP2:M3` census marker is discharged; driver values are module-qualified and the meta-guard
imports the sibling module to resolve them. The installer is re-downloaded from `main` once (banner must say **v1.0.228**).
**2026-09-01 (ADR-0444, v1.0.226, MERGED #620):** the timescale's EDGE bands clamped (a real defect —
NOT the operator's symptom). **2026-09-01 (ADR-0445, v1.0.227, MERGED #621): the operator's diagonal
header ROOT-CAUSED** — `hud.css`'s `[data-sf-hint]{position:relative}` out-cascaded every Gantt
band/bar/milestone's `position:absolute` since July; fixed with `:where()`, mutation-proved both ways;
ADR-0442's UI-01 `sizeGrip` was the same hijack misdiagnosed and is DELETED (grip CSS-seated, driver
proves absolute/right-edge/full-height/reachable). **2026-09-01 (ADR-0446, v1.0.228, MERGED #621): the
One-Pager** — `/onepager` (LIBRARY rail) turns a three-column Excel list into one 16:9 swimlane slide
(SVG preview) and exports the SAME slide as native PowerPoint shapes (`/export/pptx/onepager`) plus the
parsed list (`/export/{fmt}/onepager`) and a template; one layout, two painters; every parser decision
on the page by row; 43 + 13 + 4 tests.


⇢ **2026-09-02 (b) — the operator batch (ADR-0447..0451, v1.0.229).** Six reports, each MEASURED before
believed (ledger section "Operator batch"): (1) the blank-header screenshot matches the PRE-v1.0.227 hijack —
the current tree renders 3 labeled absolute tiers; the real gap was no demotion on zoom-in → the DEMOTE
ladder (`timescale.js`, Months/Weeks/Days at 30 px/day, `MAX_BANDS` 8000); (2) the bow-wave axis pins the
target/tracked months (UID 152 at +21 months was off-axis); (3) the One-Pager IS in source/wheel/installers/rail
— its rail link sits below the rail scroller's fold; (4) PERF: /analysis had 1,801,557 DOM nodes (743 gridline
+ 80 holiday divs PER ROW) → shared-background painters + row windowing → 26,926 nodes, 41.6 s → 4.7 s,
scroll 200 → 33 ms/frame; (5) field ROLES (WBS / Cost Account / Work Package → any loaded field; `POST
/fields/roles`; pickers on /groups and /wbs) and the WBS pivot now follows the session scope (it read the RAW
file); (6) /volatility in the Claude Design layout (five numbered panels, version chips, cursor-cumulative KPI;
ten tiles verbatim; census 66/66).
⇢ ASK FIRST (operator questions; NEW: (e) on /cei with ≥2 versions do the version chips beside Auto-play jump the wave, and does the "How to read this" block sit beside the CEI table? (f) githubstatus.com history for 2026-08-26 15:27–16:42 UTC — an Actions incident? plus the standing three): which VERSION banner produced the blank-header screenshot · did the
One-Pager `.pptx` open in PowerPoint · on v1.0.229 with two files, does /analysis scroll smoothly and band its
header on one row per tier. Do NOT re-chase the header without the banner.

⇢ CLOSED — the operator's header symptom (ADR-0444's open question) is ANSWERED by ADR-0445: the
three-row cascading header was the tooltip-anchor hijack, reproduced in all four themes with one file
or two and fixed at v1.0.227. Do NOT re-run ADR-0444's three diagnostics; if the operator reports a
header fault on ≥ v1.0.227 it is a NEW defect — measure rendered `y` and computed `position` first.
⇢ ONE QUESTION owed to the operator — ASK FIRST, do not build on the answer you assume: **did the
One-Pager's exported `.pptx` open cleanly in PowerPoint?** (Verified in python-pptx and LibreOffice
Impress in the build session; PowerPoint itself was never run.) If it did not, get the exact error
text and the PowerPoint version before touching `reports/pptx.py`.

⇢ **2026-09-03 (ADR-0454, v1.0.232): WP3 · M4 COMPLETE** — `tests/web/test_sra_grid_edit_browser.py` (17
drivers) drives the SRA grid with a REAL clipboard (`navigator.clipboard.writeText` + Ctrl+V under the
clipboard permissions; Excel-shaped CRLF/tab payloads) and two oracles (the status line; a grid digest
carrying each input's live value, pinned stable across reload/servers and sensitive). Six silent defects
found on v1.0.231 and fixed red-first: **M4-01** Refresh / post-run reload wiped unsaved edits (pending
now survives `load()`; `beforeunload` guard = **M4-06**) · **M4-02** a blank was ignored and the old value
returned (a blank now CLEARS — factor only; a blanked range side re-derives from the ranking) · **M4-03**
pasted junk vanished / a 7 clamped silently (`POST /sra/grid` returns `rejected` + `clamped` by
uid/field/value/reason; the grid reads them back — ADR-0313's rule on the grid) · **M4-04** the save
confirmation was overwritten by the reload · **M4-05** `badInput` (`e`) queued as `""` — refused at the
cell. Mutation: original-JS + fixed-route → exactly the six JS-side drivers red, blank-clear green.
The UI map has NO queued rows left. **MERGED #626** (all seven checks green; the browser job's first
attempt failed one `/forecast` caption cell on a page the diff never touched and passed on the single
re-run — `rerun_failed_jobs` is refused while sibling jobs still run; wait for the run to complete).

⇢ **2026-09-03 (docs, #627):** the operator's SIX web-UI intake uploads (255 files) broke `main`'s intake-manifest
guard; the regenerated manifest rides #627. **A web upload bypasses the pre-commit CUI guard** (four `.docx` +
a Save-format `house_build.json` copy landed under `00_REFERENCE_INTAKE/src/`) — a CI-side blocklist run over
the push diff is a WP4 candidate alongside the route-coverage instrument. `main`'s runs for those pushes were
CANCELLED by the next push: never assume a `main` commit was measured green — check its run's conclusion.

⇢ **2026-09-03 (c) — WP4 COMPLETE (ADR-0455, v1.0.233) + /cei on the design (ADR-0456).** CI-01: run #1656 (the
#612 merge) was created 247 s after the push, died in 4 s with 0 billable ms and four jobs never left `queued`;
`ci.yml` byte-identical to the green runs either side; the NEXT push's run took 21 min to appear and cancelled the
16:22 manual dispatch — a GitHub-side anomaly, NOT a repo fault (incident attribution UNVERIFIABLE: status page
egress-blocked — operator ask (f)). CI-02 REFUTED: 50/50 `main` commits since 08-01 have a push run, 48 within 4 s.
RC-01: `tools/route_coverage.py` + the opt-in conftest plugin + 11 guards (passive recorder on
`FastAPI.build_middleware_stack`, templates resolved BEFORE dispatch, three buckets). RC-02: the gap BY NAME is in
the ledger — a work queue for WP6/WP7, not a floor. HOOK-03: `tools/ci_cui_guard.sh` runs THE hook over
`base..HEAD` as the `cui-guard` job (PR = gate; push to main = warning under `00_REFERENCE_INTAKE/`, error
elsewhere; self-test stages a probe `.mpp`). WF-01: every workflow dispatchable, guarded. /cei: cursor strip with
one chip per snapshot driving the stepper's own `render()`, the two ADR-0268 forms byte-exact as the options row,
the `1.1fr .9fr` row (CEI panel verbatim · "How to read this" from the page's explainer), `.cd-*` family; red-first
5/3, 160 TestClient green, four-theme render census moved on the chip keys only. **Do NOT re-chase the 08-26
outage, and do NOT re-derive the route population by hand — run the instrument.**

⇢ **2026-09-03 (e) — the evening batch, MEASURED (ADR-0457 + ADR-0458, v1.0.234).** I-01: the SAME inputs (golden
trio, Project2→5, all ten TP4 pairs) through `/integrity` and `detect_manipulation` on worktrees at v1.0.221 / v1.0.229 /
this tree → detector rows IDENTICAL by name; the page empties on STATE — a second Project (two folders, or loose files
with different document Titles) or a reduce filter on an unmapped role name — and its sentences were wrong for both
("load two versions" with two loaded; "no findings" over an empty population). Fixed red-first: the page names its
Project population (holds k of N · other Projects · switch form back to /integrity) and its in-scope counts; an empty
side reads "nothing to compare". T-01: Show = Two tiers rendered EXACTLY two absolute rows on /analysis, /path,
/driving-path, /evolution, /sra across zooms, Fit and reload — NOT reproduced, two M2 pins, ask for page + zoom +
screenshot. (c): root-caused by SUBTRACTION in the live page (links off → p50 67 → 17 ms): the re-aim repainted the whole
window and re-created a table-sized link overlay holding every relationship; now incremental, survivor-copied sticky
offsets, spacers re-trued to the rendered pitch, one reused overlay drawing window-visible links; residue = ~700–800
sticky cells (a separate frozen pane is the priced next candidate). **Do NOT re-run the differential or re-drive the
dialog without a NEW operator report naming the finding/file pair or the page/zoom.**

⇢ **2026-09-04 — WP5 SHIPPED (ADR-0459) + /trend on the design (ADR-0460), v1.0.235 — this session's PR.** WP5: (A) `choose one
folder…`, a `.dz-how` legend (Ctrl/⌘/Shift-click for several FILES · one folder per pick · select the folders together and DROP
them for several Projects · a parent folder that holds several project folders asks), hover hints, the 2026-08-21 phrases kept;
(B) `home.js` `ingest()` → `subfolderPlan()` (ONE root, ≥2 schedule-bearing immediate sub-folders) → the served hidden `#dzAsk`
`role=dialog` shell filled with `textContent` (sub-folders BY NAME — a real FileList arrives in filesystem order) → *N Projects,
one per sub-folder* (`reroot()` drops the parent segment; 2-segment rels stay the parent's, and the box says so) / *One Project* /
Cancel; server untouched; multi-root drops never ask; a single dropped parent asks. `test_folder_ask.py` (6) +
`test_folder_ask_browser.py` (7 — Playwright 1.62 uploads a REAL directory), red-first, four mutations red by name, four-theme
render clean. /trend: artboard 05 recovered by EXECUTING the canvas (npm-pack React/Babel; `screenshots-v2/05-screen.png` is
CHAPTER 11 — never trust that file); the master mounts into `#trendMaster` (no `.panel` shell, no ◂ Back — named omission); chips
click every framed chart's Next + `#qualNext` until it shows that version (each stepper publishes `data-frame`; the cursor follows
the FIRST framed chart); Focus form = `.cd-options`; `.cd-grid-12` (version table | signals) · charts full width · `.cd-grid-2`
(quality drill | `.cd-stack` of the quality sentences + "How to read this" = `_EXPLAINERS["Trend"]`) · margin full width.
`volatility.js`'s r11 byte-freeze re-baselined DELIBERATELY; six same-line-count edits above the axis-caption line pins
(`[483, 587, 712, 830, 920]` / `[224]` / `[110]` unchanged). `test_trend_design_layout.py` (5) + `test_trend_design_browser.py`
(3 — incl. a synthetic two-version margin corpus: TP4 has NO margin task, so the burndown renders no stepper there and the margin
mutation was GREEN until that corpus existed), red-first, five mutations red by name; 254 TestClient + census rows + 38 M3 drivers +
the caption sweep green; four-theme census moved on chips / order / the master's shell only. **Do NOT re-run the folder-gesture
measurements or re-recover artboard 05; do NOT add a master step-back without an operator ask.**

⇢ NEXT — **branch FRESH from `origin/main` @ `d9bac11a` or later; open a NEW draft PR.** THEN **WP6** (ledger highs: CPM-01 `cpm.py:1316` · CPM-02 `driving_slack.py:314` · MC-02 · MC-03
`jcl.py:284` · MAN-01 · REC-02; parity-sensitive rows through the metric-parity skill; any golden shift =
CONFIRMED-DEFERRED, never a silent re-pin; RC-02's never-reached / never-adverse endpoints are WP6/WP7 rows) →
**WP7** (thin dims, `ai/txlog.py` first — Law 1) → **WP8** (consolidated report + roadmap by testimony risk).
Plus ONE design page per session. Each WP ends commit-able: red-first → mutation proofs → full gate → ADR →
state docs → draft PR.

⇢ Traps paid for, by name: **a mutation that SURVIVES is a claim about the FIXTURE before it is a claim about the code — check the fixture reaches the line (TP4 renders no margin burndown)** · **a real `webkitdirectory` FileList arrives in filesystem-traversal order — sort by name** · **a line-number-keyed pin is edited with SAME-LINE-COUNT replacements and new code BELOW the last pin; assert the pin lines in the patch** · **a byte-frozen page script (r11 `PAGE_SCRIPTS`) changes only by a dated re-baseline** · **an intake screenshot's FILE NAME is testimony — execute the canvas** · **two sessions in flight: number ADRs after the in-flight PR's, hold the version / installers / docs rotation to the end, plan the re-merge + rebuild** · **`build` is NOT in the dev extras (`pip install build`**a differential that comes back IDENTICAL is the finding — it earns the right to call the engine innocent** · **the page's own sentences on a testimony surface are the defect even when the banners disclose the state** · **frame times measured while a battery runs are noise (p95 250 vs 83 on the same tree) — quiet box, and say so** · **isolate native cost by SUBTRACTION in the live page (links off · stub · strip); the profile's `(program)` names nothing** · **a `bounding_box()` pointer can sit below the viewport — assert `scrollTop` moved before believing 16.7 ms** · **`pkill -f <pattern>` kills the shell that runs it (exit 144) — sentinel files, never process greps** · **an estimate baked in before the table is connected survives until something re-measures it (18 vs 16.18 px rows)** · **a slice oracle needs the whole population — take the order from the page's JSON and guard it against the opening window** · **ask whether a change belongs in the byte-pinned file at all before re-baselining its pin (`gantt.js` reverted; `freezeLike` copies from a survivor)** · **a run's CONCLUSION is the measurement — `cancelled`, `startup_failure`, and a red merge commit under a green PR head all happened this week; read the merge commit's run** · **put event-to-run latency in a table before carrying an outage forward** · **`spec_from_file_location` + `dataclass` + `from __future__ import annotations` needs `sys.modules[spec.name] = module` BEFORE `exec_module`** · **resolve a route template BEFORE dispatch — a `Mount` rewrites the scope it handles** · **`page.count("<div class=panel")` counts `panel-head` — parser census only** · **the design canvas needs three seeds (`sfredux-screen`, `sfops-boot.skipNext`, `sfredux-guided`) and the section's bounding box is identical under an overlay — look at the picture** · **every CDN is egress-blocked, the npm registry is not (`npm pack`)** · **`git reset --soft <base>` stages exactly `base..HEAD` for the hook; aim `origin/main` at the base or a push to main exempts its own blobs** · **the build container may have NO package installed — `pip install -e '.[dev,browser]'` before the first test** · **`tooltips.js` moves `title=` to `data-sf-hint` at load — every NEW oracle reads either** (WP3 met WP1's trap again) · **a badInput number input reports `""`; once a blank CLEARS, an unparseable keystroke is a silent delete unless refused at the cell** · **an empty pending map never POSTs ("Nothing to save.") — a driver that waits for the request hangs** · **`/root/.local/bin/ruff` 0.15.8 shadows `/usr/local/bin/ruff` 0.16.5 — run the absolute path** · **prove each half of a two-sided fix with its OWN revert** (original route / original JS) · **a positioning claim is measured by RENDERED `y` and COMPUTED `position`, never by inline styles or widths** — ADR-0444's test and every header oracle before it read inline `left`/`width` and stayed green on a diagonal header for seven weeks; positioning mode changes `y` and only `y` · **a global `[attr]{position:relative}` hijacks every positioned element that gains the attribute** — hud.css's tooltip anchor flipped every Gantt band/bar/milestone to relative once tooltips.js promoted their `title=`; use `:where([attr])` for any global rule that sets `position` · **ask the engine which rule won** (`CSS.getMatchedStylesForNode` via CDP) before reading stylesheets by eye · **partial failures with a clean discriminator ARE the diagnosis** (the two unbroken bands had empty labels) · **the One-Pager (ADR-0446, `/onepager`) is ONE layout, TWO painters — `reports/onepager.py` computes every coordinate in slide points; `static/onepager.js` and `reports/pptx.py` only paint; never compute geometry in a painter** · **it is UNVERIFIED in PowerPoint itself** (python-pptx + LibreOffice Impress renders were viewed; the operator's first open settles it — ask) · **`TestClient` follows a 303** (`follow_redirects=False`) · **`python -m pytest` puts CWD on `sys.path`; CI's plain `pytest` does not — never `from tests.…`, always `from web.<module>`, and check `pytest --collect-only -q` before pushing** · **`panelkit.js` is a per-page include** · **the DD ledger's `TIME_RE` wants the singular `month`** · **compute fixture serials, never type them** · **a fix that weakens a rule needs a test on what the rule was FOR** (the static-host anchor test) · **a workaround written against a hijacked state becomes the bug once the hijack is fixed** — ADR-0442's `sizeGrip` (UI-01) was a patch for this same defect misdiagnosed as a Chromium table-cell quirk; it is DELETED and UI-01's diagnosis is corrected in ADR-0445 (the grip had sat on the WRONG edge under a green test that only checked the drag's effect) · **a file with two identical anchors turns a slice-edit into a silent no-op** (`colresize.js` has two `ths.forEach`; delete by brace-matching, verify by grep count) · **the sticky controls bar (`#pathControls` z6) overlays the sticky header (z3/4) at the top scroll position** — OBSERVED in the ledger, a cross-page z-order design question, not fixed blind; drivers scroll the grid to viewport centre and prove `elementFromPoint` reachability · **a background waiter that greps for its own command line never exits** — `until ! pgrep -f "pytest …"; do sleep; done` matches the waiter's OWN `bash -c` line, so four of them span for hours after the suite ended; match on a pidfile or a sentinel in the output file instead · **re-applying a fix needs the suite RE-RUN** — WP2's first push was RED because a re-apply restored only HALF of chartframe.js and the "59/59 green" being quoted described a tree that no longer existed; a green from memory is testimony, not evidence · **a byte-pin pre-flight grep must search the PIN SHAPE, not your filenames** (four pins fired that hash whole files / index call sites by line, so they never name a file on the hash's line — re-baseline deliberately and verify the CAPTION hashes are identical first) · **rebuild the wheel + nine installers as the LAST step**, after the final source edit (a late whitespace change drifted the embedded wheel) · **a declared dependency floor can be made false by your own change** (`playwright>=1.44` vs `page.clock`, which needs 1.45 — measured from both wheels; the ADR-0346 fastapi shape) · **`git checkout --` is NOT a mutation restore** — it reverts to HEAD and
silently deleted three of WP2's own fixes mid-battery, then let one mutation "pass" while measuring
unfixed code; restore from a `cp` of the WORKING TREE and diff the tree after every chain · **a
wrong oracle looks exactly like a defect** — an SVG-only chart digest reported three false "chart
did not move" rows because `/evolution`, `/driving-path` and `/trend`'s quality drill paint HTML
tables; pin the oracle stable-AND-sensitive per family before believing anything built on it ·
**measuring `document.body` to test a page zoom calls a working control dead** (body is full-bleed
at every zoom; `#uiScale` was nearly written up) · **a probe's own wait can invent a finding** —
`page.url` read after `wait_for_load_state` but before the navigation began; use
`expect_navigation` · **the server session outlives a browser context** (a language set in one step
translated a later step's page — restore in `finally`) · **a defensive `if` around a load-order
dependency hides the failure it was meant to survive** · **a guard with a hand-written population
fails OPEN** (the A2 five-name list; ADR-0439's lesson, now paid for twice) · a control-census
signature is id+class ONLY — schedule names ("Fit-Out"), prose ("dis-play", "s-pan") and tooltip
attrs false-positive; tooltips.js moves title= at load; pan needs `(?!d)` · a passing byte-pin over
a dead feature certifies the corpse · `tbody.innerHTML=""` clamps scrollTop to 0 BEFORE your slice
math runs — capture, compute, restore · never pipe a mutation battery through `head` — SIGPIPE
kills it mid-mutation · a test that needs a lucky wait is measuring a race · scroll the grid into
view before hit-testing · CSS floors out-floor JS clamps (Name 200px, Chromium min-content ~53px) ·
/driving-path opens on the NEWEST version (TP4 v5's corridor for 11→26 is EMPTY — step back before
measuring) · localStorage is read at script PARSE time (add_init_script only) · byte-freeze pins
trip — grep pins, re-baseline same commit · anchor thresholds on the pathological case with ~2×
headroom · **the installer build refuses a shallow clone** (`mpxj_ref` resolves to the graft
boundary) — `git fetch --deepen=300` first · browser-job ceiling 25m (census ~2:36 + M3 ~1:52 +
M5 ~30s + windowing ~18s + M2 ~37s + long-span ~16s on top of ~9m).

⇢ Measured-false / deliberately-held — do NOT re-chase: the legal 25% Size floor look ·
`path_evolution.js:515`'s misattributing catch (unreachable with B2 fixed) · /driving-path's
empty-corridor hint (a UI-map row) · /evolution at operator scale (their session loads ONE file;
needs ≥2 versions — revisit only on their next multi-version load) · the g-head sizing duplication
(extract only if a third caller appears) · **`#uiScale` is NOT dead** (measured on a heading's box
it scales 212 → 371 px) · the Name-column 200px + Chromium ~53px resize floors (documented working
behavior) · MF-05 · MC-01 parity leg · ADR-0417/0419 fixtures · the citations.reattach pin · the 6
dead E501 per-file-ignores · the evolution 0% cell · Insufficient-Detail V05/V06 + TP2 (BLOCKED,
operator-owned). **CLOSED, no longer a deferral:** the /mission 30-hosts-vs-9-cf-bars design
question — settled by measurement in WP2 and re-pinned 30/30. **CLOSED (ADR-0445):** the diagonal timeline header — re-chase only on a
report from ≥ v1.0.227, which would be a NEW defect. **OBSERVED, not fixed blind:** the sticky controls
bar over the sticky header at the top scroll position; the docx/xlsx writers stamping CUI regardless of
mode (the One-Pager slide follows `_cui_marking`).
