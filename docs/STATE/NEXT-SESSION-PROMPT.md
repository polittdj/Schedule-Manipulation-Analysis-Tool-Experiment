# Kickoff prompt — next session

> Paste the block below verbatim to start the next session.

---

Resume the POLARIS² full-tool audit campaign (Schedule-Manipulation-Analysis-Tool). Read
docs/STATE/HANDOFF.md FIRST (auto-injected), then **docs/STATE/AUDIT-2026-08-27.md — the
campaign's live ledger (appended per-WP, never batch-written)**; the 2026-08-16 ledger stays the
historical row source for WP6. As of last close: **v1.0.223 · highest ADR 0441 · WP0 + its
operator-evidence addendum complete on branch `claude/polaris2-full-tool-audit-948whg`** (WP0/PR
#615 squash-merged @ `2fbde95e`; the ADR-0441 addendum PR follows it — verify a pull_request CI
run appears per push, dispatch manually only if none does; WP4 root-causes the 08-26
`startup_failure`). Campaign decisions (operator, 2026-08-27, standing): **SOLO lead ·
fix-as-verified · BOTH folder-ask builds**. QC-1/QC-2 bind every session —
ADR-0393, pinned by `tests/test_standing_rules.py`. **git fetch origin before you branch, number
an ADR, or commit — and RE-fetch before writing the docs.**

⇢ WHAT'S DONE — do not re-open. **2026-08-27 (ADR-0440, v1.0.222, MERGED):** the Timescale
config load path is sanitized; M2 (16 tests) is the dialog's first behavioral coverage.
**2026-08-28 (ADR-0441, v1.0.223): the operator ANSWERED the three-line ask** — clean default
storage → **A-row REFUTED for their machine** (sanitizer stands as hardening); their 12.3-year,
2,301-activity IPMR relocated the live defect to SCALE, reproduced and fixed red-first:
`reflow()` re-pins the timeline column (was stale at attach-time width — 1,918 bars painted in a
969px track inside a 40,104px column, pane 24,206px into dead space) · density adaptation
(`MIN_BAND_PX=14`, months promote to quarters fitted, return on zoom-in — was 165 bands/0
labeled/5.9px) · whole-schedule opens FITTED above 16 pages (ADR-0438's zoomed+seat preserved
below — the 3× first try broke it, the seat module is the boundary-setter) · 120 ms slider
debounce (was 5,692 ms synchronous per input event). Instruments:
`tests/web/test_long_span_gantt_browser.py` + `TP5_LongSpan_Synthetic.xml` (provenance-pinned).
**No further reply owed to the operator on the ask; after the addendum PR merges they
re-download the installer once (v1.0.223).**

⇢ NEXT — **WP1: full M1 `tests/web/test_ui_control_effect_census.py`** (size L): extend the
reduced census (12 tests, three pages) to the computed sitewide census — population harvested
from the served DOM, per-page floors, unknown zoom/fit/pan/stepper control with no driver spec =
RED; all 5 zoom surfaces (`#vizZoom`, `#pathZoom`, `#dpZoomIn/Out`, `#evoZoomIn/Out`, sra_grid) ·
fit on all 5 · Size% multiplier on 5 consumer pages · chartframe −/＋/Reset/⤢ per layout family ·
legend toggles · column drag-resize · sticky-scrollbar sync · bar-click drills ·
enlarge-then-print. **Plus the S5 deferral now queued here (priced M): windowed `paintRows` on
/path** (one-shot fitted rebuild still 1,417 ms at 2,280 rows; drive with TP5 or the scratch
scale generator). Then WP2 (M3 steppers/autoplay clock-stepped + M5 real `#themeSelect` across 4
themes) → WP3 (M4 SRA grid edit/paste/save) → WP4 (route-coverage instrument,
`SF_ROUTE_COVERAGE=1`, floor ≥139, + the CI `startup_failure` root-cause) → WP5 (BOTH folder
builds — the three 2026-08-21 folder-gesture facts govern, do NOT re-derive) → WP6 (ledger
highs: CPM-01 cpm.py:1316 · CPM-02 driving_slack.py:314 · MC-02 · MC-03 jcl.py:284 · MAN-01 ·
REC-02; parity-sensitive rows through the metric-parity skill; any golden shift =
CONFIRMED-DEFERRED, never a silent re-pin) → WP7 (thin dims, `ai/txlog.py` first — Law 1) → WP8
(consolidated report + roadmap by testimony risk). Each WP ends commit-able: red-first →
mutation proofs → full gate → ADR → state docs → draft PR.

⇢ Traps paid for, by name: **a reproduction matrix must include the reporter's data SHAPE**
(span/row count) — 13 cells of hostile state missed a clean-storage 12-year schedule ·
**measure POSITION, not just presence** — after Fit everything was painted at rect left
−24,205px · **scroll the grid into view before counting visible marks** — a KPI block filling
the viewport reads as bars_visible=0 · **a fix applied to one of two rebuild paths is a bug
scheduled for the other** (render vs reflow; SFColResize g-head sizing) · **anchor thresholds on
the pathological case with ~2× headroom from any measured-good case** — the neighbour suite's
red is the boundary-setter · **a mutation-restore must assert exactly what the mutation
changed** · /driving-path opens on the NEWEST version (TP4 v5's corridor for 11→26 is EMPTY —
step back before measuring) · localStorage is read at script PARSE time (`add_init_script` only)
· byte-freeze pins trip on label/markup changes — grep pins, re-baseline same commit ·
browser-job ceiling 25m (M2 ~37s + long-span ~16s on top of 9m).

⇢ Measured-false / deliberately-held — do NOT re-chase: the legal 25% Size floor look ·
`path_evolution.js:515`'s misattributing catch (unreachable with B2 fixed) · /driving-path's
empty-corridor hint (WP1 UI-map candidate) · /evolution at operator scale (their session loads
ONE file; needs ≥2 versions — revisit only on their next multi-version load) · the g-head sizing
duplication (colresize attach + path reflow — extract only if a third caller appears) · MF-05 ·
MC-01 parity leg · ADR-0417/0419 fixtures · the `citations.reattach` pin · the 6 dead E501
per-file-ignores · the evolution 0% cell · Insufficient-Detail V05/V06 + TP2 (BLOCKED,
operator-owned).
