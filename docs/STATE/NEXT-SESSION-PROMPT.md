# Kickoff prompt — next session

> Paste the block below verbatim to start the next session.

---

Resume the POLARIS² full-tool audit campaign (Schedule-Manipulation-Analysis-Tool). Read
docs/STATE/HANDOFF.md FIRST (auto-injected), then **docs/STATE/AUDIT-2026-08-27.md — the
campaign's live ledger (appended per-WP, never batch-written)**; the 2026-08-16 ledger stays the
historical row source for WP6. As of last close: **v1.0.233 · highest ADR 0456 (WP4 COMPLETE — ADR-0455: the
08-26 CI `startup_failure` root-caused GitHub-side and the "triggers not firing" claim REFUTED, the route-coverage
instrument COMMITTED (`tools/route_coverage.py`, `SF_ROUTE_COVERAGE=1`, population 148 over the 139 floor, the gap
BY NAME in the ledger), Law 1's blocklist running in CI (`cui-guard`), `installer-smoke.yml` dispatchable; ADR-0456:
/cei on the Claude Design layout) · WP0, its addendum, WP1, WP2, WP3 AND WP4 complete; the header root cause
(ADR-0445), the One-Pager (ADR-0446), the OPERATOR BATCH (ADR-0447..0453) and WP3 (ADR-0454, #626) ALL MERGED;
WP4 + /cei MERGED as #628 → `main` @ `0f098cce` (2026-09-03 22:54Z) — branch fresh from `origin/main` for WP5 and
open a NEW draft PR; read `main`'s run #1706 for that merge commit FIRST (in progress at close — a red there is
yours to root-cause before building on it).**
Campaign decisions (operator, 2026-08-27, standing): **SOLO lead · fix-as-verified · BOTH folder-ask builds**.
QC-1/QC-2 bind every session — ADR-0393, pinned by `tests/test_standing_rules.py`. **git fetch origin before you
branch, number an ADR, or commit — and RE-fetch before writing the docs.** **STANDING OPERATOR ASK (2026-09-03):
migrate at least ONE page per session onto the Claude Design layout** — design truth `00_REFERENCE_INTAKE/references/
design_handoff_mission_ops_redesign/Mission Ops Redesign v2.dc.html`, method ADR-0451/ADR-0456, rules
`docs/DESIGN-SYSTEM.md` §9; done: /volatility (04), /cei (06); next candidates /trend (05), /forecast (09),
/performance (07); /compare (10) is a feature change (needs /integrity's ledger); alias `vol-*` → `cd-*` with the
third page.

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

⇢ NEXT — **FIRST: the operator's 2026-09-03 evening batch (ledger section "Operator answers + new batch"; measure before believing, red-first tests that FAIL on the defect and PASS on the fix, mutation-proved, ADR per fix):** **I-01** /integrity "not picking up the same findings it once did; not working correctly" — highest severity (testimony surface); instrument = a DIFFERENTIAL run of the SAME inputs (golden pair, TP4 corpus, the operator's IPMR files if present) through this tree vs `git worktree` checkouts at v1.0.221 (`dfa09ac`) and v1.0.229 (`cc21cb5`), diffing detector rows by name; suspects (REFUTE, don't believe): ADR-0450 scope/field-roles narrowing the detector population, ADR-0421/0422 raw-vs-scoped pairing, ADR-0371 pair truncation, ADR-0424 all-N pairing · **T-01** the Timescale "two tiers" setting does not take effect — drive the dialog (M2 module) to show=2 on /analysis and /path across zooms and count RENDERED tier rows by computed position; suspects: the ADR-0441/0452/0453 promotion ladder overriding `show`, a string `show` the ADR-0440 sanitizer rejects, "View entire project" re-applying its tier set · **(c)** /analysis residual lag — frame times at TP5 scale (2,280 rows, two files) before any change; the ADR-0449 residue names the sticky cells of ~130 materialized rows. ASK the operator for I-01's exact finding + file pair and T-01's page + zoom, but run the differential first. CLOSED by the operator: the One-Pager opened in PowerPoint (ADR-0446). UNKNOWABLE: the blank-header banner; the 08-26 incident. THEN **WP5** (BOTH folder-ask builds — the three 2026-08-21 folder-gesture facts govern, do NOT
re-derive) → **WP6** (ledger highs: CPM-01 `cpm.py:1316` · CPM-02 `driving_slack.py:314` · MC-02 · MC-03
`jcl.py:284` · MAN-01 · REC-02; parity-sensitive rows through the metric-parity skill; any golden shift =
CONFIRMED-DEFERRED, never a silent re-pin; RC-02's never-reached / never-adverse endpoints are WP6/WP7 rows) →
**WP7** (thin dims, `ai/txlog.py` first — Law 1) → **WP8** (consolidated report + roadmap by testimony risk).
Plus ONE design page per session. Each WP ends commit-able: red-first → mutation proofs → full gate → ADR →
state docs → draft PR.

⇢ Traps paid for, by name: **a run's CONCLUSION is the measurement — `cancelled`, `startup_failure`, and a red merge commit under a green PR head all happened this week; read the merge commit's run** · **put event-to-run latency in a table before carrying an outage forward** · **`spec_from_file_location` + `dataclass` + `from __future__ import annotations` needs `sys.modules[spec.name] = module` BEFORE `exec_module`** · **resolve a route template BEFORE dispatch — a `Mount` rewrites the scope it handles** · **`page.count("<div class=panel")` counts `panel-head` — parser census only** · **the design canvas needs three seeds (`sfredux-screen`, `sfops-boot.skipNext`, `sfredux-guided`) and the section's bounding box is identical under an overlay — look at the picture** · **every CDN is egress-blocked, the npm registry is not (`npm pack`)** · **`git reset --soft <base>` stages exactly `base..HEAD` for the hook; aim `origin/main` at the base or a push to main exempts its own blobs** · **the build container may have NO package installed — `pip install -e '.[dev,browser]'` before the first test** · **`tooltips.js` moves `title=` to `data-sf-hint` at load — every NEW oracle reads either** (WP3 met WP1's trap again) · **a badInput number input reports `""`; once a blank CLEARS, an unparseable keystroke is a silent delete unless refused at the cell** · **an empty pending map never POSTs ("Nothing to save.") — a driver that waits for the request hangs** · **`/root/.local/bin/ruff` 0.15.8 shadows `/usr/local/bin/ruff` 0.16.5 — run the absolute path** · **prove each half of a two-sided fix with its OWN revert** (original route / original JS) · **a positioning claim is measured by RENDERED `y` and COMPUTED `position`, never by inline styles or widths** — ADR-0444's test and every header oracle before it read inline `left`/`width` and stayed green on a diagonal header for seven weeks; positioning mode changes `y` and only `y` · **a global `[attr]{position:relative}` hijacks every positioned element that gains the attribute** — hud.css's tooltip anchor flipped every Gantt band/bar/milestone to relative once tooltips.js promoted their `title=`; use `:where([attr])` for any global rule that sets `position` · **ask the engine which rule won** (`CSS.getMatchedStylesForNode` via CDP) before reading stylesheets by eye · **partial failures with a clean discriminator ARE the diagnosis** (the two unbroken bands had empty labels) · **the One-Pager (ADR-0446, `/onepager`) is ONE layout, TWO painters — `reports/onepager.py` computes every coordinate in slide points; `static/onepager.js` and `reports/pptx.py` only paint; never compute geometry in a painter** · **it is UNVERIFIED in PowerPoint itself** (python-pptx + LibreOffice Impress renders were viewed; the operator's first open settles it — ask) · **`TestClient` follows a 303** (`follow_redirects=False`) · **`python -m pytest` puts CWD on `sys.path`; CI's plain `pytest` does not — never `from tests.…`, always `from web.<module>`, and check `pytest --collect-only -q` before pushing** · **`panelkit.js` is a per-page include** · **the DD ledger's `TIME_RE` wants the singular `month`** · **compute fixture serials, never type them** · **a fix that weakens a rule needs a test on what the rule was FOR** (the static-host anchor test) · **a workaround written against a hijacked state becomes the bug once the hijack is fixed** — ADR-0442's `sizeGrip` (UI-01) was a patch for this same defect misdiagnosed as a Chromium table-cell quirk; it is DELETED and UI-01's diagnosis is corrected in ADR-0445 (the grip had sat on the WRONG edge under a green test that only checked the drag's effect) · **a file with two identical anchors turns a slice-edit into a silent no-op** (`colresize.js` has two `ths.forEach`; delete by brace-matching, verify by grep count) · **the sticky controls bar (`#pathControls` z6) overlays the sticky header (z3/4) at the top scroll position** — OBSERVED in the ledger, a cross-page z-order design question, not fixed blind; drivers scroll the grid to viewport centre and prove `elementFromPoint` reachability · **a background waiter that greps for its own command line never exits** — `until ! pgrep -f "pytest …"; do sleep; done` matches the waiter's OWN `bash -c` line, so four of them span for hours after the suite ended; match on a pidfile or a sentinel in the output file instead · **re-applying a fix needs the suite RE-RUN** — WP2's first push was RED because a re-apply restored only HALF of chartframe.js and the "59/59 green" being quoted described a tree that no longer existed; a green from memory is testimony, not evidence · **a byte-pin pre-flight grep must search the PIN SHAPE, not your filenames** (four pins fired that hash whole files / index call sites by line, so they never name a file on the hash's line — re-baseline deliberately and verify the CAPTION hashes are identical first) · **rebuild the wheel + nine installers as the LAST step**, after the final source edit (a late whitespace change drifted the embedded wheel) · **a declared dependency floor can be made false by your own change** (`playwright>=1.44` vs `page.clock`, which needs 1.45 — measured from both wheels; the ADR-0346 fastapi shape) · **`git checkout --` is NOT a mutation restore** — it reverts to HEAD and
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
