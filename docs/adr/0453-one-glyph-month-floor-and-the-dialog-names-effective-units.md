# ADR-0453 — A one-glyph month survives 7 px, and the Timescale dialog SAYS what each tier renders as

- **Status:** Accepted — 2026-09-02 (operator report on v1.0.230, /path, View entire project, Bottom = Months / "J, F, M")
- **Version:** 1.0.231
- **Shipped:** `static/timescale.js` (`m_letter.fitPx` 8 → 7; label-aware band blanking; `effectiveNote` under the dialog preview; `effectiveStack` rows remember their configured tier), `static/gantt.js` (`g-band-glyph` class), `static/app.css` (`.g-band-glyph`, `.ts-effective`), `tests/web/test_timescale_zoom_ladder_browser.py` (+2, both observed RED pre-fix)

## Context — two reports, both reproduced before a line changed

1. **"The bottom tier should show months and it shows Quarters and it won't change."** On the
   operator's 12.3-year IMS the fitted track is ~1,090 px, so a month is **7.4 px**. ADR-0452's
   one-glyph floor was 8 px, so the tier still promoted; and independently the band painter blanked
   ANY label under 9 px (`if (w < 9) label = ""`), so even an un-promoted 7.4-px month would have
   painted empty. Two thresholds, both set for words, fighting an explicit one-glyph configuration.
   Sandbox at 9 px/month rendered the letters (94 of 108 labeled — the 14 blanks were the sub-9-px
   bands); at 7.4 px the synthetic-axis probe promoted 24 months to 8 quarters.
2. **"Reset to default does not work."** Measured: it works — the Label select snapped from "J, F,
   M" to "Jan, Feb" and OK persisted `m_short`. But at whole-project zoom the default and the
   operator's configuration promote to the SAME three rows (Years / Half Years / Quarters), so the
   preview was pixel-identical before and after, and nothing in the dialog said what had promoted or
   why. A control whose effect is invisible reads as broken. The defect is the silence, not the button.

## Decisions

1. **`fitPx` 7 for the letter label** (9-px glyph font; "M" at 9 px is ~7 px) and **blanking follows
   the label**: a band is blanked below `fitPx − 1` when the label declares one, else below 9 px as
   before. Glyph bands carry `g-band-glyph` (font-size 9 px, no padding) so they survive the width.
   `m_num` stays at 11 px (two digits).
2. **The preview explains itself.** `effectiveNote` renders one line under the dialog preview:
   "At this zoom → Top: Years · Middle: Half Years — Quarters pushed coarser … · Bottom: Quarters —
   Months promoted (months are 6.5 px here; this label needs 7 px — zoom in, raise Size, or pick a
   shorter label)". It re-computes from the DRAFT config on every edit, so Reset visibly changes it
   even when the bands do not. `effectiveStack` rows now carry `src`, the configured tier they came
   from, so a dropped row is named ("dropped — nothing coarser than Years at this zoom").
3. Not changed: Reset still only resets the draft (OK applies), matching MS Project's dialog.

## Consequences

- Synthetic proof: `m_letter` at 7.4 px/month keeps 24 months labelled J F M (RED pre-fix: 8
  quarters). Rendered at 1920 px on TP5 (fitted, 6.5 px/month) the bottom tier is still promoted —
  the note says so with the numbers; the operator's 7.4-px track clears the new floor.
- Dialog test: the `.ts-effective` line exists, names "Bottom", and after Reset names Months and the
  word "promoted" — the operator sees the reset AND the reason the bands look the same.
- Legibility at 7 px is the floor of the tool's own judgment (a 9-px sans glyph), not a published
  threshold; the note tells the operator the number so they can raise Size instead of guessing.
