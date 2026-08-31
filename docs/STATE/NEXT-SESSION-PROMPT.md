# Kickoff prompt — next session

> Paste the block below verbatim to start the next session.

---

Resume the POLARIS² full-tool audit campaign (Schedule-Manipulation-Analysis-Tool). Read
docs/STATE/HANDOFF.md FIRST (auto-injected), then **docs/STATE/AUDIT-2026-08-27.md — the
campaign's live ledger (appended per-WP, never batch-written)**; the 2026-08-16 ledger stays the
historical row source for WP6. As of last close: **v1.0.224 · highest ADR 0442 · WP0, its
addendum, AND WP1 complete** (WP0/PR #615 @ `2fbde95e`, addendum PR #616 @ `d56ad3f9`; WP1 on
branch `claude/polaris2-audit-wp1-gkhubc` — check whether its draft PR has merged before
branching; verify a pull_request CI run appears per push, dispatch manually only if none does;
WP4 root-causes the 08-26 `startup_failure`). Campaign decisions (operator, 2026-08-27,
standing): **SOLO lead · fix-as-verified · BOTH folder-ask builds**. QC-1/QC-2 bind every
session — ADR-0393, pinned by `tests/test_standing_rules.py`. **git fetch origin before you
branch, number an ADR, or commit — and RE-fetch before writing the docs.**

⇢ WHAT'S DONE — do not re-open. **2026-08-27 (ADR-0440, v1.0.222, MERGED):** Timescale load
path sanitized; M2 (16 tests) is the dialog's first behavioral coverage. **2026-08-28
(ADR-0441, v1.0.223, MERGED):** the operator's 12.3-year/2,301-activity evidence relocated the
live defect to SCALE — stale reflow column, density adaptation, fitted opening, 120 ms
debounce; instruments `test_long_span_gantt_browser.py` + `TP5_LongSpan_Synthetic.xml`.
**2026-08-31 (ADR-0442, v1.0.224): WP1 full M1 census is COMPLETE** —
`tests/web/test_ui_control_effect_census.py` is sitewide and computed (34 page states from the
app's own route table; 65 id'd + 358 id-less in-family controls; 8 floor families; zero
pageerrors pinned; 17-mutation battery red by name), the 27-row UI map with per-row status is
in the ledger's WP1 section, and the census's FIRST RUN caught two dead control families,
fixed red-first: **UI-01** drag-resize grips were 7×0px (Chromium ignores top/bottom/%-height
on abs-pos children of table cells → `sizeGrip` measured geometry) and **UI-02** the sticky
proxy scrollbar tracked content only by attach-vs-fetch race (→ childList adoption). **S5 is
CLOSED**: windowed `paintRows` (slice ±40 at ≥400 rows, flat only; full-paint escapes pinned
for groups/links/Find/beforeprint) — 2,280-row one-shot rebuild **1,623 ms → 49 ms**, DOM
104,728 → 19,066; instruments `tests/web/scale_schedule.py` (deterministic row-scale
generator) + `tests/web/test_path_row_windowing_browser.py` (5 tests). After the WP1 PR merges
the operator re-downloads the installer once (banner must say **v1.0.224**).

⇢ NEXT — **WP2: M3 + M5** (the census carries explicit deferral markers naming every control):
M3 clock-stepped drivers for the 47 census'd steppers/autoplay controls + the 138 sf-frame
trio buttons (`#dpNext`/`#dpPlay` · `#prevEvo/#nextEvo/#evoPlay` · cei `#prevSnap/#nextSnap/
#autoPlay` · scurve · volatility `#volPrev/Next/Play` · performance `#perfPrev/Next/Play` ·
forecast drift · qual · masters `#sfPlayAll/#sfStepAll/#missionPlay/#missionStep`) — drive the
clock, not wall-time sleeps; M5 the real `#themeSelect` across 4 themes (every four-theme test
bypasses it with `setAttribute`) · language · taskinfo dblclick · the /mission
30-hosts-vs-9-cf-bars design question (floor-pinned, decide don't drift). Then WP3 (M4 SRA
grid edit/paste-from-Excel/save round-trip) → WP4 (route-coverage instrument,
`SF_ROUTE_COVERAGE=1`, floor ≥139, + the CI `startup_failure` root-cause) → WP5 (BOTH folder
builds — the three 2026-08-21 folder-gesture facts govern, do NOT re-derive) → WP6 (ledger
highs: CPM-01 cpm.py:1316 · CPM-02 driving_slack.py:314 · MC-02 · MC-03 jcl.py:284 · MAN-01 ·
REC-02; parity-sensitive rows through the metric-parity skill; any golden shift =
CONFIRMED-DEFERRED, never a silent re-pin) → WP7 (thin dims, `ai/txlog.py` first — Law 1) →
WP8 (consolidated report + roadmap by testimony risk). Each WP ends commit-able: red-first →
mutation proofs → full gate → ADR → state docs → draft PR.

⇢ Traps paid for, by name: **a control-census signature is id+class ONLY** — schedule names
("Fit-Out"), prose ("dis-play", "s-pan") and tooltip attrs false-positive; `tooltips.js` moves
`title=` at load; `pan` needs `(?!d)` · **a passing byte-pin over a dead feature certifies the
corpse** — the resize grips were 7×0px and the sticky proxy raced for months under green pins
claiming "Chromium-verified" · **`tbody.innerHTML=""` clamps scrollTop to 0 BEFORE your slice
math runs** — capture, compute from the capture, restore · **never pipe a mutation battery
through `head`** — SIGPIPE kills it mid-mutation; diff the tree after every restore chain ·
**a test that needs a lucky wait is measuring a race, not a feature** (sticky passed at
1500/700 ms, failed at 1200/600 ms — remove the race) · **scroll the grid into view before
hit-testing** (`elementFromPoint` below the fold hits the wrong element — third appearance) ·
CSS floors out-floor JS clamps (Name 200px, Chromium min-content ~53px) — assert the styled
width AND a sane range · /driving-path opens on the NEWEST version (TP4 v5's corridor for
11→26 is EMPTY — step back before measuring) · localStorage is read at script PARSE time
(`add_init_script` only) · byte-freeze pins trip — grep pins, re-baseline same commit
(PAGE_SCRIPTS: path.js AND gantt.js this round) · anchor thresholds on the pathological case
with ~2× headroom; the neighbour suite's red is the boundary-setter · browser-job ceiling 25m
(census ~2:30 + windowing ~18s + M2 ~37s + long-span ~16s on top of ~9m).

⇢ Measured-false / deliberately-held — do NOT re-chase: the legal 25% Size floor look ·
`path_evolution.js:515`'s misattributing catch (unreachable with B2 fixed) · /driving-path's
empty-corridor hint (now a UI-map row) · /evolution at operator scale (their session loads ONE
file; needs ≥2 versions — revisit only on their next multi-version load) · the g-head sizing
duplication (colresize attach + path reflow — extract only if a third caller appears) ·
/mission's 21 unframed async tiles (WP2:M5 design question — floor-pinned 30/9, not a blind
fix) · the Name-column 200px + Chromium ~53px resize floors (documented working behavior) ·
MF-05 · MC-01 parity leg · ADR-0417/0419 fixtures · the `citations.reattach` pin · the 6 dead
E501 per-file-ignores · the evolution 0% cell · Insufficient-Detail V05/V06 + TP2 (BLOCKED,
operator-owned).
