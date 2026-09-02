# ADR-0449 — The Gantt DOM budget: gridlines and holidays as shared backgrounds, row windowing on /analysis

- **Status:** Accepted — 2026-09-02 (operator item 4 of six — "the program is running like shit")
- **Version:** 1.0.229
- **Shipped:** `static/gantt.js` (`sharedRule` / `cssColorOf` / `svgUrl`, `paintGrid` as one shared background rule, coalesced sticky-scrollbar measures), `static/timescale.js` (`decorateCell` holiday layer as one shared background), `static/app.js` (both inline gridline loops routed through `paintGrid`; row windowing ported from ADR-0442's `paintRows`; index-math link anchors for off-window rows; Find/print force a full paint), `tests/web/test_gantt_row_dom_budget_browser.py` (3), `tests/web/test_analysis_row_windowing_browser.py` (3)

## Context — measured, on the operator's scale (2,125 rows, 12.3 years, one file; two files for the server side)

| what | pre-fix | after painters | after windowing |
|---|---|---|---|
| server TTFB, every route | 0–0.9 s (fine) | — | — |
| /analysis DOM nodes | **1,801,557** (1,578,875 `.g-grid` + 170,927 `.g-nonwork-holiday`) | 51,756 | 26,926 |
| /analysis wall to interactive | 41.6 s (63.6 s in a second run) | 8.4 s | 4.7 s |
| long-task time / longest | 36,904 ms / 24,111 ms | 4,648 / 2,504 | 834 / 308 |
| zoom-step synchronous rebuild | 26,386 ms | 1,749 ms | (windowed body) |
| page-scroll frame p50 / p95 | 200 / 317 ms (5 fps) | 117 / 400 | 33 / 83 ms |
| /path (already windowed, ADR-0442) scroll p50 | 17 ms | 17 | 17 |

Every other page measured 17 ms/frame and ≤ 3 s wall; the server was never the lag. Root cause: every
timeline track appended one `<div>` per gridline (743/row once ADR-0447's Weeks tier existed; 213/row
before) and one per holiday (80/row) — the count scaled with rows × zoom. The CPU profile after the
painter fix showed the residue was NATIVE (layout + 12,750 `position:sticky` frozen cells + a 34,000-px
table), not script.

## Decisions

1. **Gridlines = ONE shared background per gridline set.** `paintGrid` builds one SVG data URI (a 1-px rect
   per line, stretched to row height) per `lines` array — cached on the array, every caller passes the same
   array to every row of a render — and applies it through a generated class in a bounded `<style>`
   (`RULE_CAP` 24) so the URI exists once per render, not in 2,000 inline styles. Colours are RESOLVED from
   the `.g-grid` theme rules at paint time (an SVG cannot read custom properties) and cached for the page's
   life — each probe was a ~100 ms layout flush (1,158 ms of a 3.4 s rebuild before the cache).
2. **Holidays = ONE shared background layer per (calendar, axis span, colour)**, keyed by CONTENT (a
   per-axis-object memo re-minted on every zoom, because every rebuild mints a new axis).
3. **Sticky-scrollbar observer callbacks coalesce to one measure+place per frame** (`measure()` reads
   `scrollWidth`, a forced layout; a rebuild fired it several times).
4. **/analysis row windowing** (ADR-0442's `paintRows`, ported): at ≥ 400 rows the tbody carries the viewport
   slice ± 40 rows between two spacer rows; a scroll re-aims it; Find and print force a full paint; a short
   tail (≤ 20 rows) is painted outright. **Links stay on**: off-window endpoints are anchored by index math
   on the same axis, so long connectors still cross the viewport (a documented approximation — the far
   row's y uses the mean pitch).
5. `WINDOW_MIN_ROWS` 400 sits above the largest full-paint suite (TP5, 121) and below the operator (2,000+).

## Consequences

- Fixed 11 nodes per row (was 834). The remaining cost at operator scale is the ~130 materialized rows'
  sticky cells; a class-based freeze (per-column rules instead of per-cell inline styles) is the next
  candidate and was NOT done blind.
- The whole-tree pins that hash `gantt.js`/`volatility.js` were re-baselined deliberately (ADR-0451 also
  touches `volatility.js`); the axis-caption call-site hashes did not move.
- Two traps paid for: a colour probe that forces layout is a per-call cost proportional to the DOM, and a
  memo keyed on an object that every rebuild recreates is not a memo.
