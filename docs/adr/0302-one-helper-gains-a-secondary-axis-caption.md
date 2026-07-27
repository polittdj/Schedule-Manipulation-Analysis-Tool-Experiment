# ADR-0302 — The one caption helper gains an optional secondary-axis label

- **Status:** Accepted
- **Date:** 2026-07-27
- **Extends:** ADR-0298 (one shared helper, one type token, the ledger)
- **Related:** ADR-0301 (captions come from the rendering code), ADR-0195 (design system —
  one convention, phased integration), ADR-0192 (never a false statement about our own output)
- **Decided by:** the operator, asked directly during AXIS-TITLES batch 2 close-out

## Context

`SFChartFrame.axisTitles` draws exactly one X caption and one Y caption. That is the whole
convention ADR-0298 promoted, and it is sufficient for a single-scale chart.

**It is not sufficient for a combo chart.** `wbs.js` plots SPI(t) as bars against a **left** axis
(a ratio, against the 1.0 on-plan reference line) and earned schedule as a line against a
**right** axis (working days). Batch 2 could name only the left one. That leaves a reader looking
at two sets of gridlines with one of them anonymous — on a tool whose output is meant to be read
in testimony, an unidentified scale is a question the chart invites and cannot answer.
`sra.js` and `margin_dashboard.js` are the same shape and are still `PENDING`.

Batch 2 deliberately did **not** invent a fix mid-batch: adding a second caption mechanism locally
is exactly the fragmentation ADR-0298 exists to prevent, and changing the shared helper is a
convention decision. It was recorded as a gap and put to the operator, who chose to extend the
helper.

## Decision

**One optional third label, `y2Label`, inside the same helper.**

```js
if (opts.y2Label) caption(svg, geom.R - 4, geom.T + 9, opts.y2Label, "end");
```

- **Placement mirrors the Y caption** to the plot's top-**right**, end-anchored. The Y caption is
  at `(L + 4, T + 9)`; the secondary sits at `(R - 4, T + 9)` on the same baseline.
- **The three captions occupy three different corners by construction** — X at the bottom-right
  `(R, B - 4)`, Y at the top-left, Y2 at the top-right. A secondary caption that collided with the
  X caption would be worse than no caption, so the harness asserts three distinct anchors and that
  Y2 shares the Y baseline rather than the X one.
- **Horizontal, never rotated**, like the other two. Rotation was the second convention ADR-0298
  retired and it is not coming back through a side door.
- **Absent unless asked for.** Omitting `y2Label` emits nothing, so every pre-existing caller is
  byte-for-byte unaffected — asserted directly by the harness rather than assumed.
- **No new styling surface.** `y2Label` goes through the same `caption()` node builder and the same
  `.ch-at` class, so size, colour and case still come from `--sf-fs-axis-title` alone. The queued
  CRISPNESS 11px floor still moves **one value**.

**This preserves "one convention" rather than breaking it.** ADR-0298's rule is one
*implementation*, one *token*, one *placement law* — not "exactly two labels". A chart with two
scales can now name both, through the same helper, with no chart drawing anything itself.

### On captions naming their own axis

`wbs.js` now passes `"SPI(t) (ratio, left axis)"` and
`"Earned schedule (working days, right axis)"`. The axis names are part of the caption text rather
than implied by position, because on a two-scale chart the reader's actual question is *which
gridlines do I read this against* — and position alone answers that only if you already know the
convention.

## Consequences

- `wbs.js` is the first caller; both its scales are now identified. `sra.js` and
  `margin_dashboard.js` can use it when their batch lands.
- **The affordance was mutation-verified — four mutants, each caught** (file backups, ADR-0298):
  the secondary caption moved onto the X caption's corner; emitted unconditionally (which would
  silently add a caption to every existing caller); left-anchored instead of right; and a numeric
  `font-size` planted in the caption block. The harness catches the first three, and the
  block-level no-numeric-type assertion catches the fourth.
- **Behaviour is executed, not pinned** (ADR-0289): the node harness drives the real helper against
  a DOM stub for placement, anchoring, the `.ch-at` hook, non-rotation, three-distinct-corners, and
  backward compatibility.
- **Version 1.0.107 → 1.0.108**, wheel rebuilt and all nine installers regenerated — `chartframe.js`
  and `wbs.js` are packaged, so ADR-0148's lockstep rule applies.
- **Not done here, on purpose:** nothing else was captioned. This ADR is the affordance and its
  first caller; the remaining `PENDING` modules stay a batch-3 problem, so the convention change is
  reviewable on its own rather than buried in seven modules of caption text.
- **Still owed, unchanged:** the four-theme visual pass. The secondary caption is the one placement
  most worth eyeballing, because it is the newest and sits where a legend or a value readout often
  lives — `cei.js` draws its CEI figure near that corner, though it passes no `y2Label`.
