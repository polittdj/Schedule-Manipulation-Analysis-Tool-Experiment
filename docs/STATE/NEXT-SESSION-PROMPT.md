# Kickoff prompt — next session

> Paste the block below verbatim to start the next session.

---

Resume the POLARIS² full-tool audit campaign (Schedule-Manipulation-Analysis-Tool). Read
docs/STATE/HANDOFF.md FIRST (auto-injected), then **docs/STATE/AUDIT-2026-08-27.md — the
campaign's live ledger (appended per-WP, never batch-written)**; the 2026-08-16 ledger stays the
historical row source for WP6. As of last close: **v1.0.226 · highest ADR 0444 · WP0, its
addendum, WP1 AND WP2 complete, plus an operator-reported header fix (ADR-0444) on top** (WP0/PR #615 @ `2fbde95e`, addendum PR #616 @ `d56ad3f9`, WP1/PR
#617 @ `286046d5`, WP2/PR #618 @ `0e07d213` — ALL MERGED, so branch fresh from `origin/main` and
do not look for an open PR; verify a pull_request CI run appears per push, dispatch manually only
if none does; WP4 root-causes the 08-26 `startup_failure`). Campaign decisions (operator,
2026-08-27, standing): **SOLO lead · fix-as-verified · BOTH folder-ask builds**. QC-1/QC-2 bind
every session — ADR-0393, pinned by `tests/test_standing_rules.py`. **git fetch origin before you
branch, number an ADR, or commit — and RE-fetch before writing the docs.**

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
imports the sibling module to resolve them. After the WP2 PR merges the operator re-downloads the
installer once (banner must say **v1.0.225**).

⇢ OPEN QUESTION owed to the operator (ADR-0444) — ASK BEFORE RE-CHASING. They reported "the time
line headers are still screwed up" with a screenshot of /path on their 2,301-activity / 12.3-year
IPMR, two files open. A REAL defect was found and fixed there (tierBands clamped `left` but took the
width from the UNCLAMPED left and never clamped `right` — the 2017 band overlapped 2018 by 34px and
the last band ran 57px past the header). **But their exact symptom — a THREE-row header with
cascading year labels — was NOT reproduced**: every repro at their row count, span, file count and
six viewport widths (1100→2560) produced a sound TWO-row header with zero pageerrors, because
`effectiveStack` promotes Months→Quarters at that span and dedupes. ADR-0444 is therefore UNVERIFIED
as their fix. Get these three from the machine showing the fault, both files open, BEFORE probing
further: (1) the version banner — are they on >=1.0.225, or a build predating ADR-0441's header work?
(2) `localStorage.getItem("sf.timescale.v1")` — the persisted tier config that decides the row count.
(3) a dump of `.g-scale-tiered .g-tier` (class + computed `top`) and the first few `.g-band`
label/left pairs — the one thing a screenshot cannot give.

⇢ NEXT — **WP3: M4 the SRA grid** — edit / paste-from-Excel / save round-trip (UI-map row 27, the
last queued row). Then **WP4** (committed route-coverage instrument, `SF_ROUTE_COVERAGE=1`, floor
≥139, + the 08-26 CI `startup_failure` root-cause — the outage claim is PARTIALLY REFUTED, event
triggers do fire; note `installer-smoke.yml` has NO workflow_dispatch, a fix candidate) → **WP5**
(BOTH folder-ask builds — the three 2026-08-21 folder-gesture facts govern, do NOT re-derive) →
**WP6** (ledger highs: CPM-01 `cpm.py:1316` · CPM-02 `driving_slack.py:314` · MC-02 · MC-03
`jcl.py:284` · MAN-01 · REC-02; parity-sensitive rows through the metric-parity skill; any golden
shift = CONFIRMED-DEFERRED, never a silent re-pin) → **WP7** (thin dims, `ai/txlog.py` first —
Law 1) → **WP8** (consolidated report + roadmap by testimony risk). Each WP ends commit-able:
red-first → mutation proofs → full gate → ADR → state docs → draft PR.

⇢ Traps paid for, by name: **a background waiter that greps for its own command line never exits** — `until ! pgrep -f "pytest …"; do sleep; done` matches the waiter's OWN `bash -c` line, so four of them span for hours after the suite ended; match on a pidfile or a sentinel in the output file instead · **re-applying a fix needs the suite RE-RUN** — WP2's first push was RED because a re-apply restored only HALF of chartframe.js and the "59/59 green" being quoted described a tree that no longer existed; a green from memory is testimony, not evidence · **a byte-pin pre-flight grep must search the PIN SHAPE, not your filenames** (four pins fired that hash whole files / index call sites by line, so they never name a file on the hash's line — re-baseline deliberately and verify the CAPTION hashes are identical first) · **rebuild the wheel + nine installers as the LAST step**, after the final source edit (a late whitespace change drifted the embedded wheel) · **a declared dependency floor can be made false by your own change** (`playwright>=1.44` vs `page.clock`, which needs 1.45 — measured from both wheels; the ADR-0346 fastapi shape) · **`git checkout --` is NOT a mutation restore** — it reverts to HEAD and
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
question — settled by measurement in WP2 and re-pinned 30/30.
