# ADR-0329 — AXIS-TITLES batch 3c-i: sra.js + volatility.js join the caption convention

Status: accepted (2026-08-01)
Implements: the AXIS-TITLES ledger (ADR-0298 → 0303 → 0325), PLAN-20260730 decision A1's
carried sub-answers (tornados recorded as not-axis-charts; deliberate md5 re-baseline is the
accepted procedure), the batch 3c "remaining four PENDING modules" queue item — first half
Builds on: ADR-0303 (the caption stays fixed, the DATA yields), ADR-0319 (the live-box yield
mechanism), ADR-0316 (the blob-driven-module `defer` family), ADR-0326 (one convention per
medium)

## Context

Four modules remained in the `PENDING` ledger: `sra.js`, `sra_jcl.js`, `sra_ssi.js`,
`volatility.js`. Each was surveyed fresh on this tree (the ADR-0311 lesson). The survey found
three kinds of visuals mixed inside the four modules: real X/Y axis charts that belong under
the shared helper, tornado/strip/grid forms with no axis scale to name (decision A1's recorded
call), and two modules whose charts render only after a Run button click — which matters
because the measured visual pass is the batch's acceptance, and an unclickable chart is an
unmeasured caption.

## Decision

**Batch 3c ships in two halves.** This half (3c-i) captions the two modules whose charts render
without a click; `sra_jcl.js` + `sra_ssi.js` stay in `PENDING` for 3c-ii, whose visual pass
must first learn to click Run (deliberately split, not skipped — the ledger keeps them listed).

1. **Six charts join the shared helper** (`SFChartFrame.axisTitles`, 18 → 24 call sites, a
   DELIBERATE re-baseline with the prior 18 entries byte-untouched):
   * `sra.js` #sraCdf — x "Finish date", y "Cumulative probability".
   * `sra.js` #sraHist — x "Finish date", y "Simulated finishes".
   * `volatility.js` churn — x "Schedule version", y "Path carried over".
   * `volatility.js` flow — x "Schedule version", y "Joined ↑ / left ↓" (the local
     "joined ↑ / left ↓ vs the prior version" annotation RETIRED into it, the 3b-i pattern).
   * `volatility.js` area — x "Schedule version", y "Activities on path" (the
     "green = carried over · red = newly joined" line is a LEGEND, kept).
   * `volatility.js` dwell — x "Versions on path" (the hand-rolled centred
     "versions on the critical path" caption RETIRED into it), y "Activities".

2. **Recorded NOT-axis-charts (decision A1) — no call, deliberately:** the two `sra.js`
   tornados (#sraSens, #sraRisk: a centre axis with name-labelled rows has no X/Y scale to
   name) and `volatility.js`'s gauge, membership heatmap, tenure/jumper leaderboards, timeline
   strips, and transition ribbon (gauges, grids and labeled strips likewise). `sra_ssi.js`'s
   5×5 matrices are HTML tables that already carry native axis labels — a different medium
   entirely (ADR-0326).

3. **Every collision closed where it is caused — the data yields (ADR-0303):**
   * The CDF's "deterministic finish — P<n>" label moves from `padT+10` to `padT+24`, out of
     the Y caption's band (it still tags its full-height dashed marker).
   * Rotated date/version ticks yield to the X caption via the ADR-0319 LIVE-box mechanism
     (a local `yieldTicksToCaption` in each module, mirroring resources.js: measure the
     caption's real rendered box after layout, remove any tick biting it with a 2px margin —
     apollo's wider mono glyphs covered per-theme, the caption never moves).
   * The dwell count labels clamp statically out of BOTH caption bands
     (`max(raw, padT+24)` then cap at `H-padB-20`), keeping their bar's x.

4. **`/volatility` joins the ADR-0316 `defer` family.** The measured pass caught it live:
   `volatility.js` draws synchronously at parse time and loads BEFORE chartframe.js on its
   page, so the new helper call threw `SFChartFrame is not defined` and killed the whole
   render — the exact `/performance` (PR-2) defect class. Fix per the recorded precedent: one
   word, `defer` on the script tag (a call-site guard stays rejected, ADR-0316's reasoning).

5. **`/sra` + `/volatility` join the measured visual PAGES matrix.** `/sra` self-runs its
   simulation on load (`/api/sra` ≈ 1.4 s on the golden pair, auto screening defaults) so its
   captions render for real; `/volatility` charts from its embedded blob (2 golden versions
   suffice). `volatility.js`'s PAGE_SCRIPTS byte-freeze is deliberately re-baselined
   (`0d38b34e…` → `67a62558…`, the gantt.js/ADR-0326 procedure).

## Consequences

* `PENDING` is down to `sra_jcl.js` + `sra_ssi.js` (3c-ii); reaching empty stays the
  AXIS-TITLES completion signal. 3c-ii's prerequisite is a click-driving serve in the visual
  harness (both panels render only on their Run buttons).
* The AXIS_CALL_SITES freeze now pins 24 sites; the count check and docstrings moved 18 → 24
  in the same change (test renamed accordingly — a rename, not a weakening; the load-bearing
  file+digest equality is unchanged in form).
* The flow chart's "vs the prior version" phrasing lives in the panel's read-me/tooltips, not
  the caption — captions name scales, prose explains semantics.
* A third member joins the ADR-0316 defer family; if a fourth blob-driven module ever appears,
  the lesson is standing: parse-time rendering + late chartframe = first-paint crash.

## Verification (all read from runs this session)

Census + freeze suites (`test_axis_titles.py` + `test_r11_panel_contract.py`): **54 passed**
post-change. The measured visual pass (`test_axis_titles_visual.py`, 9 pages × 4 themes × 3
scales, caption-vs-every-sibling-text collision detection): **1 passed in 86 s** with zero
collisions and KNOWN_COLLISIONS still empty. Neighbor suites (sra view/ssi-web/grid/zero-margin/
file-select, bar-drill, accessibility): **99 passed**. **Proved able to fail, watched:** the
three ledgers FAIL on the stashed pre-change tree (census unclassified ×2, call-site count
24 ≠ 18, volatility byte-freeze mismatch), and the visual pass itself was watched failing live
on the pre-`defer` tree ("no captions rendered" in every /volatility cell) — the failure that
exposed finding 4. Full-suite + installer-lockstep results: SESSION-LOG.
