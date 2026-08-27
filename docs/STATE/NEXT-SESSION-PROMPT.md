# Kickoff prompt — next session

> Paste the block below verbatim to start the next session.

---

Resume the POLARIS² full-tool audit campaign (Schedule-Manipulation-Analysis-Tool). Read
docs/STATE/HANDOFF.md FIRST (auto-injected), then **docs/STATE/AUDIT-2026-08-27.md — the
campaign's live ledger (appended per-WP, never batch-written)**; the 2026-08-16 ledger stays the
historical row source for WP6. As of last close: **v1.0.222 · highest ADR 0440 · WP0 complete on
branch `claude/polaris2-full-tool-audit-948whg`** (draft PR open; squash-merge when CI is green —
**the planning session's "event trigger is NOT firing" claim was PARTIALLY REFUTED on
2026-08-27 (pull_request + push runs measured firing; one 08-26 push run ended
startup_failure) — verify a run appears per push, dispatch manually only if none does; WP4
root-causes the startup_failure**). Campaign decisions (operator, 2026-08-27, standing): **SOLO lead ·
fix-as-verified · BOTH folder-ask builds**. QC-1/QC-2 bind every session —
ADR-0393, pinned by `tests/test_standing_rules.py`. **git fetch origin before you branch, number an ADR,
or commit — and RE-fetch before writing the docs** (docs-only closes land often and always touch
the four state docs).

⇢ WHAT'S DONE — do not re-open. **2026-08-27 (ADR-0440, v1.0.222): WP0, the operator's live
defect on v1.0.221 is root-caused and dead.** A persisted out-of-range/garbage
`localStorage["sf.timescale.v1"]` reproduced "controls do nothing" + "renders wrong" on exactly
/path, /driving-path, /evolution with ZERO console errors (13-cell × 3-page seeded Playwright
matrix, A0-calibrated); timescale.js now sanitizes the load path (ranges clamp, enums reject,
labelDef got the months-fallback belt that kills the B2 render crash). M2
(`tests/web/test_timescale_dialog_browser.py`, 16 tests ~37s, auto-joins the browser job) is the
dialog's first behavioral coverage — 8 pins observed RED pre-fix, mutation battery red by name.
**Whether the operator's machine held that state is UNVERIFIABLE until they answer the
three-line ask in the ledger's Phase-0 section** (screenshot · console ·
`localStorage.getItem("sf.timescale.v1")`) — surface it to the operator, don't re-chase.

⇢ NEXT — **WP1: M1 `tests/web/test_ui_control_effect_census.py`** (size L): the computed
control-effect census — population harvested from the served DOM (never hand-listed), per-page
floors, any zoom/fit/pan/stepper-shaped control with no driver spec = RED. Drive with measured
effects: zoom in/out + clamps on all 5 zoom surfaces (app.js `#vizZoom`, path `#pathZoom`,
driving `#dpZoomIn/Out`, evolution `#evoZoomIn/Out`, sra_grid) · fit on all 5 · pan (/evolution)
· Size% multiplier on all 5 consumer pages (width ratio ≈ 2× at 200%) · chartframe −/＋/Reset/⤢
(one representative per layout family) · legend toggles · column drag-resize · sticky-scrollbar
sync · bar-click drills · enlarge-then-print. Mutation proof: delete a control from the spec map
→ named failure. Then WP2 (M3 steppers/autoplay clock-stepped + M5 real `#themeSelect`
click-through across all 4 themes) → WP3 (M4 SRA grid edit/paste/save) → WP4 (committed
route-coverage instrument, `SF_ROUTE_COVERAGE=1` opt-in, floor ≥139, + root-cause the CI
event-trigger outage) → WP5 (BOTH folder-ask builds — extend
`test_multi_folder_drop_browser.py`'s fake-entry machinery; the three 2026-08-21 folder-gesture
facts govern, do NOT re-derive) → WP6 (ledger highs: CPM-01 cpm.py:1316 · CPM-02
driving_slack.py:314 · MC-02 · MC-03 jcl.py:284 · MAN-01 · REC-02; parity-sensitive rows go
through the metric-parity skill, any golden shift = CONFIRMED-DEFERRED, never a silent re-pin) →
WP7 (thin dims, `ai/txlog.py` first — Law 1) → WP8 (consolidated report + roadmap by testimony
risk). Each WP ends commit-able: red-first tests → mutation proofs → full gate → ADR → state
docs → draft PR + manual dispatch.

⇢ Traps paid for, by name: **/driving-path opens on the NEWEST version and TP4 v5's corridor for
11→26 is legitimately EMPTY** — step back one version before measuring bars, or the baseline
itself reads red · **the B2-class crash fires on the tier REBUILD** — force a zoom reflow before
asserting `errors == []` or the crash channel passes vacuously · **localStorage is read at
script PARSE time** — seed via `context.add_init_script` only · **`Number("") === 0`** — guard
empty strings before clamping · **a red for the wrong reason is not a red** — calibrate every
oracle on an A0 baseline row first · byte-freeze pins trip on label/markup changes — grep pins
before landing, re-baseline in the same commit · browser-job runtime ceiling 25m (was 9m + M2's
~37s; one server+browser per module, clock-stepped autoplay, sampled chartframe drives).

⇢ Measured-false / deliberately-held — do NOT re-chase: the legal 25% Size floor look (track
120px — the dialog's own smallest choice, measured identical) · `path_evolution.js:515`'s
misattributing catch (measured unreachable with B2 fixed; reported in the ledger) ·
/driving-path's empty-corridor opening hint (UI-map candidate, WP1) · MF-05 · MC-01 parity leg ·
ADR-0417/0419 fixtures · the `citations.reattach` pin · the 6 dead E501 per-file-ignores · the
evolution 0% cell · Insufficient-Detail V05/V06 + TP2 (BLOCKED, operator-owned).
