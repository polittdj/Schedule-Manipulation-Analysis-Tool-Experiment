# 0314 — A help callout must be dismissable and must never cover the nav (OR-02)

Date: 2026-07-30
Status: accepted

## Context

Operator report (2026-07-28, `docs/STATE/OPERATOR-REQUESTS.md` OR-02): *"I keep getting this weird
call-out that covers the menu bar on the left side of the screen that I can't get to go away unless
I switch to another page but then it will return. It is the DCMA 11 — Missed Activities call-out."*

The callout is the DCMA-overview float tip (`.dcma-tip-float`): `position:fixed` on `<body>` at
z-index 10000 (so the chart frame's overflow cannot clip it — ADR-0286 lineage), and
`pointer-events:none` (so it never steals hover). Those two properties are also the whole bug
surface: it paints over everything, and it can never receive its own `mouseleave` — every hide has
to be driven from somewhere else.

A 2026-07-27 round had already fixed one strand (scroll-hide + the zero-rect anchor guard,
`tests/web/test_float_tip_scroll.py`). OR-02 arrived AFTER that fix, so the report was re-measured
from scratch rather than assumed to be the same bug. It was not — it was three more, one of which
only an audit of the first fix attempt surfaced.

## The defects, measured (probes, Chromium)

**1. A focus-shown tip had no reachable dismissal.** The rows are `tabindex=0`; a click or a tap
focuses one and shows the tip instantly. The only hide paths were the row's `mouseleave` (pointer
was never over the row — never fires), its `blur` (focus stays put — never fires), and any scroll.
Of six dismissals a real operator would try: **Escape STUCK, moving the mouse away STUCK,
alt-tab STUCK**; only click-elsewhere, scroll, and row-removal cleared it. "I can't get it to go
away" was literally true for the three things an operator tries first.

**2. The placement clamp did not know daylight's header is an overlay.** It asked for
`getComputedStyle(header).position === "fixed"` — true for console/apollo/jarvis (a 236px fixed
left rail at ≥761px), but daylight's full-width top bar is `position:sticky`, so daylight was never
avoided. With hit-target-checked hovers, the callout overlapped the daylight header at 1280×520,
1280×800 and 1440×600, while no fixed-rail view overlapped at any probed size.

**3. The tips are BORN visible (the audit's find — very likely the original symptom).**
`.dcma-tip-float` CSS computes visible (it opts out of the base `.dcma-tip` hover-gating with
`opacity:1; visibility:visible`), and `dcmaPanel` created each tip with **no inline
`display:none`** — so on every render, all 16 tips painted stacked at the viewport's (0,0), over
the nav. On loads with an auto-scroll (the Gantt's scroll-to-data-date) the capture-phase
scroll-hide masked the flash within a frame; on loads without one the stack simply **stayed**, and
navigating re-created it — the operator's *"it returns after I switch pages,"* exactly. Verified:
on the unfixed code an insertion-time observer records every tip inserted with inline display `""`.

## Decision

All in `static/app.js`, the mechanism that owns the tip:

1. **Born hidden.** Every float tip is created with inline `display:none`; only hover-intent or
   focus shows it. This kills defect 3's whole class regardless of whether a load happens to
   auto-scroll.
2. **Module-level dismissal, driven from the document** — `hideFloatTips()` wired to capture-phase
   `keydown` (Escape — also the rescue for any tip a future bug strands visible, tracked or not),
   capture-phase passive `pointermove`, `window` `blur`, and `visibilitychange`. A
   `shownTip`/`shownRow` pair tracks the visible tip; `mark()` hides a *different* previously
   tracked tip before recording (two-tips-at-once interleaving), and the `dcmaPanel` rebuild
   clears the tracker with the tips.
3. **Pointer dismissal requires real motion**: an 8px travel threshold from the first position
   seen while the tip shows, so a desk bump or 1px sensor jitter cannot kill a deliberately
   keyboard-opened tip mid-read (preserves ADR-0286's "focus is a deliberate act" posture while
   still giving the operator the mouse-away dismissal they expect).
4. **The clamp is geometric, not position-typed**: the header's measured box decides. A RAIL
   (right edge short of the viewport) is cleared sideways via a left floor; a full-width BAR
   (sticky daylight, or the ≤760px in-flow burger header while on screen) is cleared downward via
   a top ceiling; a scrolled-away in-flow header has bottom ≤ 0 and costs nothing. Width compares
   against **`document.documentElement.clientWidth`, never `innerWidth`** — `innerWidth` includes
   a classic scrollbar (~15px), which made a full-width bar measure "narrower than the viewport,"
   classify as a rail, and shove the tip off-screen to a **9px sliver** (measured; see audit).
5. **Height is capped to the space below the bar** with `overflow-y: hidden`, NOT `auto`: the tip
   is `pointer-events:none`, so a scrollbar would be a control no input can ever operate —
   ADR-0304's dead-control law. Wheel input passes through to the page, which scrolls, which
   dismisses. The clipped tail engages only on viewports too short for the full text below the
   header; the same content lives in the DCMA audit table's tooltips and the metric dictionary.
6. **`placeFloatTip` returns whether it anchored** (`false` on a zero-rect row); only `true`
   records `shown*`.
7. **ARIA wiring**: each tip gets an id and its row `aria-describedby` — the same contract the
   server-rendered DCMA audit table already ships (ADR-0286); previously the overview's
   `role=tooltip` was orphaned and announced never.

## The audit (Ultracode, ADR-0240) — and what it caught

The first fix attempt was audited before landing: four dimension reviewers (JS/DOM semantics,
suite regressions, UX/design-system, test quality) with adversarial verification, findings
lead-re-verified executably. Twelve findings; the two **blockers** were real and shipped in the
first attempt:

- **The scrollbar misclassification** (decision 4): the first attempt compared against
  `innerWidth`. Every probe had passed because **headless Chromium hides scrollbars** — the defect
  only exists in a headed browser with classic scrollbars (Windows default, i.e. the operator's
  machine). Re-measured with `--hide-scrollbars` disabled: `oldIsRail: True → tip 9px visible;
  newIsRail: False → tip fully visible`.
- **The born-visible stack** (defect 3): the first attempt's pointermove dismissal was gated on
  the tracker, so the untracked at-load stack would have remained un-dismissable by pointer.

Plus: the dead-scrollbar trade the first attempt had accepted was reversed under ADR-0304's own
law (decision 5); the jitter threshold (decision 3); the two-tips interleaving; the ARIA gap; and
three test-hardening findings (a vacuous-pass counter, a layout-coupled magic coordinate, and the
untested burger-header viewport) — all folded into the shipped tests.

## Verification

- All six probed dismissals hide the tip; a 1px jitter deliberately does not.
- No overlap from any hit-checked hoverable row: 4 themes × 4 viewports (incl. 600×700 burger),
  plus the classic-scrollbar daylight case.
- `tests/web/test_float_tip_dismiss.py` (vendored-chromium posture, same as
  `test_float_tip_scroll.py`): the operator's own DCMA-11 callout dismissed by Escape /
  pointer-away / window-blur; tips born hidden (insertion-time MutationObserver — checking after
  load cannot tell "born hidden" from "hidden by the masking auto-scroll"); a 16-cell measured-box
  sweep counting only cells that actually measured a tip. **Proved able to fail**: on the unfixed
  code the dismissal test, the born-hidden test, and the daylight placement cell all FAIL
  (3 failed, measured); on the fixed code all 19 pass.
- All 136 existing app.js-content tests green; `node --check` green.
