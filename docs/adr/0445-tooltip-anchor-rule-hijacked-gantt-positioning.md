# ADR-0445 — The tooltip anchor rule silently re-positioned every Gantt band, bar and milestone; the operator's "diagonal timeline header" was this, not ADR-0444

- **Status:** Accepted
- **Date:** 2026-09-01
- **Version:** 1.0.227 (shipped: `static/hud.css` one line; `static/colresize.js` `sizeGrip` removed; `static/app.css` one comment)
- **Supersedes / extends:** ADR-0444 (which fixed a real but DIFFERENT header defect and whose
  test could not see this one), ADR-0286 (the `data-sf-hint` callout system whose anchor rule is
  the cause), ADR-0441 (the long-span header work, whose measurements were all width-based).

## Context

The operator reported `/path`'s timeline header "still screwed up" with two IPMR versions open,
and after ADR-0444 shipped: "the fix did not fix the problem." Their screenshot showed the year
labels descending **diagonally** — `2017` on row one, `2018` a row lower and further right,
`2019` another row down — with everything past the third row cut off and the rest of the header
empty, while the bars beneath spanned the full column.

ADR-0444 had found and fixed an unclamped-edge-band defect in the same component, measured it,
mutation-proved it, and shipped it — but its own reproduction never showed a diagonal, and the ADR
said so ("UNVERIFIED as their fix"). The reason it never showed one is the lesson of this ADR.

## What was actually wrong

Every `.g-band`, `.gantt-bar` and `.g-ms` is created with a `title=` (its hover text).
`tooltips.js` promotes any non-empty `title` to `data-sf-hint` at load so the styled callout
renders (ADR-0286). `hud.css` then anchors that callout with

```css
[data-sf-hint]{position:relative}
```

An attribute selector has the same specificity as a class selector, and `hud.css` loads after
`app.css`. So on every element that carried a tooltip, this rule **won** over
`.g-band{position:absolute}`, `.gantt-bar{position:absolute}` and `.g-ms{position:absolute}`.

Measured on the operator's shape (2,301 activities, 12.3 years, two files, 1920×1080), computed
`position` after load:

| element | on page | carrying `data-sf-hint` | `position: relative` |
| --- | --- | --- | --- |
| `.g-band` (header bands) | 62 | 60 | **60** |
| `.gantt-bar` | 73 | 73 | **73** |
| `.g-ms` (milestones) | 11 | 11 | **11** |

The two bands that stayed `absolute` were the two with an **empty label** — no title, nothing to
promote, no override. That is the cascade's own fingerprint, and the engine confirmed it directly:
`CSS.getMatchedStylesForNode` on a broken band lists `.g-band … position: absolute` followed by
`[data-sf-hint] … position: relative`.

A `position:relative` band is a block element in normal flow: it paints on its own line, shifted
right by its inline `left`. Ten year bands in a tier therefore paint on ten rows, each 18px lower
and one year further right — the diagonal — and the header's fixed height clips everything after
the third. Rendered tops measured `[18, 36, 54, 72, 90, …]` for what should be one row. Bars and
diamonds were flipped too but survived by accident: a track holds one child, so block flow puts it
at `y=0` regardless. On pages where a track holds a bar **and** an envelope (`.g-envelope` is the
same shape), the envelope stacks under the bar.

This has been in the tree since 2026-07-11 (`47899b23`), in every theme, at every span, with one
file or two. The operator only *noticed* it with two files open; it was never conditional on that.

## Why nothing caught it for seven weeks — the real finding

**Every measurement of the header ever taken read either the bands' inline `style.left`/`width`
or their rendered `width`.** Both are byte-identical between a working and a broken header —
positioning mode changes `y`, and only `y`. ADR-0441's density work measured band widths and label
counts; ADR-0444's test read `style.left`/`style.width`; the WP1 census drivers measured bar width
under zoom. All of them passed on a header that had been diagonal the entire time. The oracle was
not merely weak, it was **structurally incapable of refuting the claim** — QC-1's exact failure
class — and this session's first fix inherited the same blind spot and shipped green.

The kickoff prompt has carried "`tooltips.js` moves `title=` at load" as a *census-signature* trap
since WP1. Its positioning side-effect was never suspected, because the trap was written from the
symptom that was noticed (attribute text moving), not the mechanism (promotion changes the
cascade).

## Decision

**Drop the anchor selector to zero specificity:**

```css
:where([data-sf-hint]){position:relative}
```

`:where()` contributes no specificity, so ANY explicit `position` rule — every `.g-band`,
`.gantt-bar`, `.g-ms`, `.g-envelope`, and any future positioned element that grows a tooltip —
beats it regardless of source order, while a static host (heading, button, hint-dot) still gets
its bubble anchor exactly as before. An already-positioned element is a perfectly good containing
block for the `::after` bubble; forcing it to `relative` was never needed. One line, no
enumeration, fails closed for the next case. Alternatives rejected: raising the specificity of each
victim class (an enumeration that fails open for the next one), and teaching `tooltips.js` to skip
positioned elements (a `getComputedStyle` per titled node at load, hundreds on a large grid, for a
problem that is a CSS cascade problem). `:where()` is supported by every Chromium the tool targets.

Two rendered-geometry tests now pin the contract from both sides
(`tests/web/test_long_span_gantt_browser.py`):

- `test_header_bands_bars_and_milestones_stay_absolutely_positioned` — every band in a tier paints
  on ONE rendered row; the header does not overflow by a row; the computed position of every band,
  bar and milestone is `absolute`. The overflow bound is "less than one tier row (18px)" because the
  gold data-date line deliberately overhangs the header by 2px to join the track gridlines.
- `test_the_hint_anchor_still_positions_static_hosts_after_the_downgrade` — the 200+ static hint
  hosts on the page are still `position:relative`, so the fix did not trade a broken header for
  broken tooltips sitewide (which `test_tooltips.py`, byte pins on the CSS text, could never see).

## Proof (QC-1)

- **Red first, by name, on the standard single-file fixture:** `g-tier-yr: its 10 bands paint on
  10 different rows (tops [18, 36, 54, 72, 90]…)`.
- **Mutation, both directions:** restoring the plain `[data-sf-hint]` selector → the staircase
  assertion fires by name; deleting the anchor rule entirely → `206 of 215 tooltip hosts are
  position:static`. Each test catches the reversion the other cannot.
- **Reproduced in all four themes** before the fix (console / daylight / apollo / jarvis, distinct
  rendered tops = 13 per tier).
- **Neighbour veto:** tooltip / HUD / axis-title / panel-contract suites 147 passed; census +
  timescale dialog + row windowing green (numbers in the SESSION-LOG entry).
- The full-suite number for the shipped tree is recorded in the SESSION-LOG entry, AFTER the run,
  from a tree verified identical to the pushed sha.

## The second layer: ADR-0442's UI-01 was a misdiagnosis of the same hijack

Dropping the anchor's specificity turned the WP1 column drag-resize driver RED (`(54, 54)` — the
column no longer widened; twice on the fixed tree, green on the reverted tree). The grip
(`.col-rsz`) carries `title="Drag to resize column"`, so it was the same victim: seven weeks of
`position:relative` under a rule that says `absolute`. ADR-0442 measured it at "7×0px at the
cell's static position, LEFT edge", diagnosed *"Chromium does not honor top/right/bottom on an
absolutely-positioned child of a table cell"*, and wrote `sizeGrip` — a JS patch that stamps an
inline `height` and a `left` computed **for a relative box** onto the grip. That is exactly what a
`position:relative` empty `<div>` looks like; the Chromium quirk was never the cause.

With the grip genuinely absolute, `sizeGrip`'s inline `left: 0.5px` plus the CSS `right:0` and
`width:7px` over-constrained the box; `left` wins, and the grip was pinned to the **left** edge
(`gripRect [1, 0, 7, 59]`) where the pointer hit a page control instead. Stripping the inline
styles and measuring again: `[47, 0, 7, 58]` — right edge, full height, **CSS alone seats it
correctly**. So `sizeGrip` is deleted, not kept "just in case": a geometry patch on top of a
correct CSS placement is a second thing to go wrong, and it had already gone wrong once. The
CSS comment above `.col-rsz` that repeated the refuted quirk is corrected in place.

The WP1 driver only ever asserted that a drag widened the column — true even with the grip on the
wrong edge, which it was the whole time (pre-fix it sat at `x=7`, not `x=47`). It now also
asserts the grip is `absolute`, flush with the cell's right edge, full height, and that
`elementFromPoint` at its centre returns the grip. Mutation: reintroducing an inline `left` →
`grip is not flush with the cell's right edge: right: 47`.

**Observed, deliberately not fixed here:** with the grid scrolled to the top, the page's own
sticky controls bar (`#pathControls.sf-freeze-bar`, `z-index: 6`) overlays the sticky header row
(`thead z 3`, frozen cells `z 4`) — the topmost element under a correctly-seated grip at that
scroll position is a filter button in the bar. The WP1 driver's `scrollBy(0, -40)` only worked
because the mis-seated grip poked out from beneath it. The driver now scrolls the grid to the
viewport centre and proves reachability. Whether the bar should sit above the header at all is
a cross-page z-order design question (it is what makes the controls "frozen"); logged in the
ledger as a do-not-fix-blind row, not changed.

## What ADR-0444 was, in hindsight

A real defect (edge bands drawn a full unit wide, overlapping at the left and bleeding past the
right), correctly measured, correctly fixed, and correctly labelled UNVERIFIED as the operator's
symptom. It stays. What it was NOT was a fix for what the operator saw, and its test — like every
header test before it — could not have told anyone that. This ADR is the correction, and the
lesson is recorded so the next width-based oracle is recognised for what it is.

## Consequences

- The operator re-downloads once; the banner must read **v1.0.227**. Their header will band
  across the track on one row per tier for the first time since July.
- `/sra` and every other page drawing bars-plus-envelopes in one track renders the envelope on
  the bar again rather than under it.
- Standing rule, added to the kickoff: **a positioning claim is measured by rendered `y` and
  computed `position`, never by inline styles or widths.**
