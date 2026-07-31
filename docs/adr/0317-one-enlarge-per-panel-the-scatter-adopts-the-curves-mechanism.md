# 0317 — One ⛶ per panel: the scatter adopts the /curves mechanism

Date: 2026-07-30
Status: accepted

## Context

The `/analysis/{name}` scatter panel rendered **two** Enlarge controls. The server head's
`_shell_tools` ⛶ (`data-sf-big`, contract vocabulary) flipped its label through panelkit.js but
moved nothing — the panel gains scatter.js's `.sf-tilebox` wrapper at runtime, so the overlay
rule's `:not(:has(.sf-tilebox))` exclusion keeps it `position:static` (measured in round 11 and
recorded as a knowing exemption in the r11 guard, whose static sweep cannot see a JS-injected
wrapper). Beside it, scatter.js's own sentence-case `⛶ Enlarge` (`tile-expand` →
`tile-expanded`) did the real work. Two glyphs, one inert — the exact ADR-0304 defect class the
round-11 contract exists to remove, and one of the operator-queued items in the approved plan
(PR-3, `docs/STATE/PLAN-20260730.md`).

/curves already solved this shape (rank 9): each curve panel's chart row carries the panel's
ONE ⛶ — the button itself wears `data-sf-big`, panelkit.js's delegated listener owns the
`⛶ ENLARGE / ⛶ SHRINK` label + `aria-pressed` (and toggles the panel's `.is-big`, inert there by
the same exclusion), while the original click wiring lifts the chart into its viewport overlay.
One owner per concern, no duplicate glyph, and the event is deliberately not stopped so it
reaches panelkit's document listener.

## Decision

- `scatter.js::sfControls` adopts the /curves mechanism verbatim: a `.sf-tools` cluster
  (`data-noprint`) whose single `tile-expand` button says `⛶ ENLARGE`, carries `data-sf-big`,
  and toggles `tile-expanded` on the tilebox in its own (un-stopped) listener. The sentence-case
  labels leave the file; panelkit owns label + aria.
- `_shell_tools` gains `big: bool = True`; the scatter panel's head passes `big=False` — the
  **server emits no ⛶ for this one panel**, so the page carries exactly one Enlarge control and
  the r11 guard's knowing exemption disappears *statically*: the guard is byte-unchanged and now
  covers the page for the right reason (no server-rendered `data-sf-big` sits on a
  tilebox-bearing panel at all). The head keeps its real ⤓ EXCEL.
- The 16-site axis-caption census keeps its count and every caption digest; only scatter.js's
  recorded line number refreshes (102 → 111 — `sfControls` grew above the call site), exactly
  the refresh path the census's own failure message prescribes. No caption byte moved.

## Verification

`tests/web/test_scatter_one_enlarge.py`: the static half (the scatter panel's server chunk has
`⤓ EXCEL` but no `data-sf-big`) and the measured half — real-chromium clicks on
console/daylight (+ a scrollbar-visible cell, the ADR-0314 lesson): exactly ONE ⛶ on the panel,
the click flips the label to `⛶ SHRINK` (proving panelkit's delegation fired) **and** grows the
tilebox's scroll-invariant size axes by >100 px (console widens across the rail; daylight,
already full-width, grows tall), and a second click restores width/height/x to <2 px. The
trends-animation pin is deliberately updated: scatter.js joins the contract-vocabulary set and
the legacy sentence-case list shrinks to margin.js alone (its own conversion round pending).
Proved able to fail: with src stashed all three key tests fail.

## Consequences

One control, both mechanisms, measured. Viewport-relative `bounding_box` y is scroll-polluted
by the click's own `scrollIntoView` — box assertions here use the scroll-invariant size axes
(a harness lesson recorded in the state docs). margin.js is now the only remaining
sentence-case Enlarge carrier.
