# ADR-0286 — one tooltip per hover, revealed after a 1.5s hover-intent delay

Status: accepted (2026-07-24) — operator bug report + UX directive

## Context

The operator hovered a DCMA-14 check name on `/analysis/<version>` and got **two overlapping
tooltip boxes** (screenshot). Both were correct content, drawn twice by two different mechanisms.

The tool had grown two tooltip families plus the browser's own:

| Mechanism | Where | How it shows |
|---|---|---|
| `data-sf-hint` → CSS `::after` | chart headings, nav controls, Mission tiles (`hud.css`, `app.css`) | instantly on `:hover` |
| `.dcma-tip` sibling box | DCMA-14 audit table, SRA/SSI metric headers (`app.css`) | instantly, `display:none` → `block` |
| `.dcma-tip-float` | the DCMA overview panel, positioned by `app.js` on `<body>` | instantly, JS `display` toggle |
| native `title=` | ~104 server-rendered sites + `sra_ssi.js` | the browser's own box, on its own timing |

The duplicate came from triggers that carried **both** a custom tooltip and a `title=`.
`_dcma_metric_cell` did this deliberately — the `title` was documented as a "no CSS/JS" fallback —
so with CSS enabled (always, in practice) the rich callout *and* the native box both appeared.

Two further problems: tooltips fired the instant the pointer crossed a trigger, so sweeping the
cursor across the DCMA table flashed a cascade of boxes; and the native tooltips ran on the OS's
own delay, which cannot be configured, so timing was inconsistent between surfaces.

## Decision

**One tooltip per hover, everywhere, revealed only after the pointer RESTS on the target for 1.5s.**

- **New `web/static/tooltips.js`**, loaded from the shared `_LAYOUT` so it covers every page.
  On load and on DOM insertion (charts, SRA/SSI tables and trend drills render client-side) it
  normalises every `title`:
  1. a trigger that **already has a custom tooltip** (`data-sf-hint`, `.dcma-metric`, `.viz-hint`,
     or an element followed by a `.dcma-tip`) has its `title` moved to **`data-sf-title`** — the
     text is preserved for exports/no-CSS readers, but the browser no longer paints a second box;
  2. a **plain** `title` is **promoted** to `data-sf-hint`, so it renders as the same styled
     callout on the same delay instead of the OS tooltip. Replaced/void elements (`input`,
     `select`, `img`, `svg`, `iframe`, …) cannot host `::after`, so they keep their native
     `title` — still exactly one tooltip.
- **The delay is a `transition-delay`**, not a timer, for both CSS families: the callout is always
  in the box tree but `opacity:0; visibility:hidden`, and the `:hover`/`:focus-visible` rule
  reveals it after `var(--sf-tip-delay)` (**1.5s**, defined once in `hud.css`). This is what makes
  the reveal *cancellable* — moving the cursor away before the delay elapses means the transition
  never completes and nothing ever paints. Hiding stays immediate (no delay on the base rule).
  `.dcma-tip` moved off `display` (which cannot be transitioned) onto opacity/visibility.
- **The JS-positioned floating tip** (`app.js`) waits the same interval via
  `window.SF_TIP_DELAY_MS`, with the timer cleared on `mouseleave`. **Keyboard focus shows
  immediately** — focus is already a deliberate act, and delaying it would read as broken.
- `prefers-reduced-motion` drops the fade but **keeps the delay** (the delay is requested
  behaviour, not decoration).

## Consequences

- A hover anywhere in the tool produces exactly one tooltip, styled consistently, after 1.5s of
  rest. Sweeping across a table no longer flashes anything.
- No per-call-site edits: the ~104 server-rendered `title=` attributes and any future ones are
  normalised at runtime, so this cannot regress by someone adding a `title` next to a hint.
- The `title` text is never lost — it moves to `data-sf-title`, and `aria-describedby` (already on
  the DCMA trigger) continues to give assistive tech the rich text.
- With JS disabled the native `title` survives untouched, so the no-JS fallback still works; only
  the de-duplication and the promotion are JS-dependent.

## Verification

`tests/web/test_tooltips.py`: `tooltips.js` is loaded on every page; it retires the native title
when a custom tip exists and preserves it as `data-sf-title`; replaced elements are excluded; the
MutationObserver covers late-rendered content; the 1500 ms and 1.5 s constants agree; both CSS
families reveal via `transition-delay: var(--sf-tip-delay)` and `.dcma-tip` no longer uses
`display:none`; the floating tip defers with `setTimeout` and cancels with `clearTimeout` while
focus stays immediate.
