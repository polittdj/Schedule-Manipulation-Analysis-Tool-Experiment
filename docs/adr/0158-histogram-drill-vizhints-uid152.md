# ADR-0158 — histogram click-drill, universal visual explainers, Large_Test_File SSI parity

## Status

Accepted. The fourth 2026-07-08 operator work order.

## Decisions

1. **Total-float histogram click-drill.** The analysis page's float histogram takes the LEFT
   half of its panel; clicking any band (including empty ones — a full-height hit strip per
   band) lists that band's activities on the RIGHT with UID + Name + Total float by default, a
   Gantt-style Columns dropdown (every standard field plus the file's mapped custom fields),
   and an "Excel (this selection)" export. `/export/{fmt}/float-band/{name}?band=i&cols=…`
   serves exactly the on-screen selection; `_FLOAT_HIST_BANDS` mirrors the client BUCKETS by
   index (a sync comment marks both sides). Fractional floats between 0 and 1 now land in the
   "1–5" band (they previously fell through to "> 44" — a real binning bug fixed on both
   sides).
2. **Every visual explains itself, on every page.** `static/vizhints.js` carries a ~65-entry
   catalog — per visual: WHAT is shown, an EXAMPLE reading, HOW TO READ it, and PM USE — and
   decorates every matching `<h2>/<h3>` with the shared `data-sf-hint` hover callout
   (keyboard-focusable, pre-line, 480px). Substring matching survives dynamic headings; a
   MutationObserver catches headings that charts add after their fetch; Mission Control tiles
   keep their richer server-side hints (already-hinted headings are skipped).
3. **Large_Test_File UID-152 SSI parity (closes needs-list A-4).** The operator's delivered
   SSI Directional Path export for `Large_Test_File.mpp` ("USA OTB Master IMS", 2,126 tasks,
   progressed + resource-leveled) is pinned as the `ssi_uid152` golden: the engine reproduces
   the 76-task Path-01 membership AND every driving-slack value UID-for-UID with ZERO
   mismatches on the first run — SSI parity now holds at real-world scale, on a leveled file,
   from a committed 680 KB gzipped MSPDI fixture (`test_ssi_driving_slack_uid152_exact`).
4. **The export's Drag column is provenance-only, deliberately NOT gated.** Decoded structure:
   SSI reports 0 for milestones and for tasks whose stored window overlaps another on-path
   task, and a uniform 0.5 d for every serial task. That 0.5 is the near-path slack under an
   SSI measurement convention the engine computes as 1.0 d (the nearest parallel branch hangs
   on a noon milestone). Forcing the engine to 0.5 without understanding that convention would
   be curve-fitting (Law 2), and the uid67 drag gate (20/20) stays authoritative for the drag
   semantics we HAVE validated. Open question recorded on the operator needs list: SSI's
   drag/slack definition doc, or a second simple-file drag export, to resolve the half-day
   convention.

## Consequences

- Live-verified in Chromium (13 checks, zero console errors): half-width split, band click →
  task list, Columns add/remove, selection Excel download, explainers on /analysis /trend
  /ribbon /integrity /curves with the four-part format.
- Parity surface grows to two independent SSI oracles (small unleveled + large leveled);
  driving-slack semantics are unchanged — the new golden pins existing behavior.
