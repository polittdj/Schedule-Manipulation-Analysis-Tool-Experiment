# ADR-0452 — The configured tier count survives "whole project"; the promotion floor follows a one-glyph label

- **Status:** Accepted — 2026-09-02 (operator report on v1.0.229, /path, View entire project)
- **Version:** 1.0.230
- **Shipped:** `static/timescale.js` (`effectiveStack`: a PROMOTED tier that collides with the tier below is pushed one rung coarser, dropped only when nothing coarser exists; `effectiveTier`: the promotion floor is the configured label's `fitPx` when it declares one; `m_letter` fitPx 8, `m_num` fitPx 11), `tests/web/test_timescale_zoom_ladder_browser.py` (+2, both observed RED pre-fix)

## Context

"I should be seeing three tiers and I am only seeing two." Screenshot: v1.0.229, `/path`, View entire
project, 12.3-year IMS, dialog set to Three tiers Years / Quarters / Months; rendered Years / Quarters.
Cause: at that width months are ~5 px, so the bottom tier promoted to Quarters, collided with the
configured middle Quarters tier, and ADR-0441's rule dropped the duplicate — deliberately, as "MS
Project's zoomed-out two-tier stack". The operator, who lives in MS Project, disagrees: Project keeps
the configured row count. Their second ask — "abbreviate the months … J, F, M … or 1-12" — already
existed in the Label menu (`m_letter`, `m_num`) but was useless at density: the 14-px promotion floor
ignored the label, so a 10-px month was promoted whatever the operator picked.

## Decisions

1. **Promote-collision pushes the upper tier COARSER** (`COARSER`), exactly as ADR-0447 already did for
   demote-collisions. Y/Q/M fitted to a 12-year page becomes **Years / Half Years / Quarters** — three
   rows. A row is dropped only when no coarser unit exists above the tier below (two tiers both at
   Years — a track too narrow for 14-px quarters), or when the operator CONFIGURED a tier finer than
   the one below it. Supersedes ADR-0441's drop rule; ADR-0441's promotion itself is unchanged.
2. **The promotion floor follows the configured label.** A label def may declare `fitPx`, the width
   its glyphs legibly fit; the configured tier promotes only below THAT floor (`m_letter` 8 px,
   `m_num` 11 px), and every rung after the first promotion uses the generic 14 px again (the label
   has reset to the unit's default). So "J F M" holds months down to 8 px and "1..12" to 11 px.
3. Not added: new label styles — both requested styles already existed; the defect was the floor.

## Consequences

- Rendered proof at the operator's width (1600 px): three rows, each strictly coarser than the one
  below, all labeled. At 1440 px the fitted /path track cannot hold 14-px quarters and renders two rows
  (Years / Half Years) — stated in the test, not hidden.
- Synthetic-axis proof through `SFTimescale.tiers()`: at 10 px/month the default label promotes to 8
  quarters; `m_letter` keeps 24 months reading J F M; `m_num` at 12 px keeps 24 months reading 1 2 3.
- Ladder, long-span and dialog suites green (30 tests). The header is one element per page, so the
  extra row costs one tier of divs, never a per-row multiplier (ADR-0449).
