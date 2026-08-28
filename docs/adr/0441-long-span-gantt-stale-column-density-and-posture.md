# ADR-0441 — Operator evidence re-aimed the live-defect chase: the reflow path leaves the timeline column pinned at its attach-time width, the header degrades instead of promoting units on long spans, and a decade-scale whole-schedule view opens 38 pages wide

- **Status:** Accepted
- **Date:** 2026-08-28
- **Context:** POLARIS² campaign WP0 addendum (docs/STATE/AUDIT-2026-08-27.md, Phase-0). The
  operator answered the ADR-0440 three-line ask WITH evidence, which refuted the A-row for their
  machine and handed the chase a better lead: their real schedule spans 2017–2029 (~4,500
  calendar days, 2,301 activities) — a scale axis the TP4-era suite never exercised.
- **Extends/relates:** ADR-0440 (the load-path sanitizer stands as real hardening; it was not the
  operator's defect) · ADR-0438 (whole-schedule posture; its zoomed-and-seated opening is
  preserved below 16 pages) · the SFColResize fixed-layout change (whose g-head sizing this
  completes on the reflow path) · ADR-0187 (edge-extend, unchanged).

## The operator's evidence, and what it refuted

`localStorage.getItem("sf.timescale.v1")` on their machine returned a **byte-clean default
config** (`size:100, show:3`, stock tiers), `sf-ui:/path` returned `null`, and their console had
no errors. So the CONFIRMED-PLAUSIBLE-ROOT-CAUSE claim of ADR-0440 is **REFUTED for their
machine** — the mechanism was real and stays fixed, but their live defect was elsewhere. Their
two screenshots located it: a 12.3-year IPMR on /path.

## Three defects, reproduced at their scale before any fix (QC-1)

A synthetic look-alike (2,280 tasks, 2017–2029, data date 2026-01-16) measured, pre-fix:

| finding | measurement |
| --- | --- |
| **A — the reflow path leaves the timeline COLUMN pinned at its attach-time width.** `SFColResize.attach` sizes the `.g-head` th fresh per attach — but attach runs only from `render()`; the Zoom slider and Fit go through `reflow()`, which swaps a new scale into the th while the th's inline `width/minWidth/maxWidth` survive. | After Fit: every one of 1,918 bars + 362 milestones painted inside a 969px track — positioned inside a **40,104px column**, with the pane still scrolled **24,206px** right from the data-date seat. Track rect left: **−24,205px**. The screen shows dead space: "renders wrong" and "controls do nothing" in one mechanism. A fresh Trace full-renders (re-attach) and looks fine — which is exactly the operator's experience: traces displayed, then zoom/Fit appeared dead. |
| **B — the timescale header degrades instead of adapting.** `tierBands` shrinks LABELS (full → narrow → empty) but never promotes UNITS the way MS Project does zoomed out. | Fitted 12.3y in 969px: months tier = **165 bands, 0 labeled, 5.9px average** — the operator's picket fence ("should be showing Years, Quarters, and Months and it is not"); quarters at 17.6px barely legible. 165 month gridlines × 2,280 rows also put **427,795 nodes** in the DOM. |
| **C — the whole-schedule posture opens at the slider default regardless of span** (`fitFill = posture !== "whole"`, ADR-0438's "opens zoomed"). | No-target /path opened a **40,104px** track (~38 pages); with the seat at the data date, the visible slice held ~0–2 marks — the operator's first screenshot. Each slider input event synchronously rebuilt the grid: **5,692 ms per event** (a drag fires dozens). |

## Decision

Four changes, all presentation-layer (`engine/` untouched):

1. **A:** `path.js reflow()` re-pins the `.g-head` th (`width/minWidth/maxWidth = axis.width`)
   on every reflow, mirroring what attach does — the column now follows the axis, and the pane's
   scroll clamps back into content when the track shrinks.
2. **B:** `timescale.js` gains density adaptation (`effectiveTier`/`effectiveStack`): a tier
   whose bands would average under `MIN_BAND_PX = 14` promotes up the ladder
   (hours→days→weeks→months→quarters→halfyears→years; thirds→months) **for rendering only** —
   CFG keeps the operator's configured units and zoom-in restores them; a tier that promotes
   into its neighbour's unit is dropped (Years/Quarters/Months renders as Years/Quarters — the
   MS Project zoomed-out stack). `gridBoundaries` uses the same stack, so body gridlines match
   the header (fitted DOM fell to 176,829 nodes).
3. **C:** a fresh whole-schedule payload opens **fitted when its zoomed track would exceed
   SIXTEEN pages**; anything shorter keeps ADR-0438's zoomed-and-seated opening. The first
   threshold tried (3×) broke the measured, operator-approved seat contract on a ~2.5-year
   (7.5-page) schedule — `test_path_whole_schedule_browser` caught it, and the boundary was
   re-anchored on the pathological case with ~2× headroom on both sides (7.5 stays zoomed,
   38 fits).
4. **D:** the /path zoom slider input is debounced (120 ms trailing) so a drag coalesces into
   one rebuild. Handler cost per event at 2,280 rows: **5,692 ms → 0 ms**; Fit one-shot
   5,580 ms → 1,417 ms (see "not done" for the remainder).

## Verification (QC-1)

- New fixture `tests/fixtures/test_projects/TP5_LongSpan_Synthetic.xml` (121 tasks, 2017–2029;
  the SPAN is the payload — the defects reproduce at any row count; parameters in the banner;
  added to the provenance pin list).
- New suite `tests/web/test_long_span_gantt_browser.py` (5 tests): all four fix-side tests
  observed RED pre-fix by name (th 26,200px vs fitted scale 489px · whole view opened 26,200px
  in a 1,440px window · months tier 108 bands/0 labeled/4.5px · 6 slider events = 6 rebuilds),
  plus the PASS-side months-return pin.
- **Mutation battery, red by name:** A: th re-pin removed → its test alone red · B:
  `MIN_BAND_PX=0` → picket-fence test red · C: whole-fit flag never set → opens-fitted red
  (re-proven after the threshold change) · D: debounce reverted → burst test red · E:
  `MIN_BAND_PX=100000` (over-promotion) → months-return pin red — the PASS side has teeth.
- **End-to-end at operator scale (2,280 rows):** opens fitted at 969px with labeled year bands ·
  slider event handler 0 ms · Fit 1,417 ms · /driving-path's ADR-0438 whole-schedule grid opens
  fitted through the same path · regression sweep over the affected neighbourhood (whole-schedule
  seat, timescale unit tests, gantt shading harness, M1 census, M2 dialog, DD-line, axis titles)
  green.

## Consequences

- The operator's reported experience on a decade-scale schedule is repaired end to end: the
  whole view opens showing the whole schedule; zoom/Fit visibly respond; the header reads
  Years/Quarters fitted and Years/Quarters/Months as you zoom in — number-true at every density.
- The Timescale dialog's configured units are never rewritten by the adaptation; it is
  presentation-only and reversible by zooming.

## Deliberately NOT done

- **Row virtualization / windowed painting.** The one-shot fitted rebuild still costs ~1.4 s at
  2,280 rows (bars + per-row gridline divs). Priced M — a windowed `paintRows` that renders only
  the viewport slice ± overscan — queued in the WP1 ledger section; the debounce makes the
  current cost a once-per-gesture payment rather than a per-event one.
- **A promotion floor knob in the Timescale dialog.** `MIN_BAND_PX = 14` is a constant; making
  it configurable is UI surface with no operator ask behind it.
- **The `.g-head` sizing duplication** between `colresize.js` (attach) and `path.js` (reflow)
  stands — extracting a shared helper touches every Gantt's attach path for a two-line gain;
  reconsider if a third caller appears.
