# ADR-0298 — Axis captions: one shared helper, one type token, an explicit remaining-work ledger

- **Status:** Accepted
- **Date:** 2026-07-27
- **Implements:** `00_REFERENCE_INTAKE/AXIS-TITLES-PATCH.md` batch 0 — **with five corrections**,
  each verified against the source (see below)
- **Related:** ADR-0195 (design system; one convention, phased integration), ADR-0289 (a behaviour
  needs a node harness, not a source pin), ADR-0249 (encode the claim as an executable assertion)

## Context

`docs/DESIGN-SYSTEM.md` §0 Law 2 — "every visual is an instrument" — and §4's chart-language rules
imply named, captioned axes. The tree had **two conflicting caption implementations** and 28 chart
modules with none:

- `performance.js` drew a caption pair locally (`txt(..., size: 9, weight: "bold")`), X
  right-aligned at the plot's bottom-right, Y horizontal at the top-left;
- `scatter.js` drew its own pair inline at 11px — a **centred** X caption and a **rotated (-90°)**
  Y caption.

Two placements, two sizes, two code paths. The regression worth guarding is not "a chart forgot a
caption" — it is "someone drew a caption a **second way**", which is what re-fragments a convention.

### Five corrections to the spec, each verified before implementing

The applyable spec was written without a Python runtime or an app to render, and it says so. Its
census is otherwise exact (all 58 static modules accounted for), but five load-bearing claims did
not survive checking:

1. **`SFChartFrame.text` does not exist.** `chartframe.js` exported `{ frame, scan }` only; the
   spec's helper called a `text()` that was never there. The helper now builds its own SVG node.
2. **No type or font tokens exist.** `font-size: var(--sf-fs-label)` / `var(--sf-font-mono)` would
   have resolved to nothing — `sf-themes.css` carries **colour** tokens only. This ADR *defines*
   the token (`--sf-fs-axis-title`, in `base.css` where DESIGN-SYSTEM §1 says tokens live).
3. **`scatter.js` already had an X caption.** The spec called it "Y only … gains the X caption it
   never had". It had both (L100 centred X, L103 rotated Y). So this change *relocates and
   resizes* two existing captions rather than adding one — declared plainly below, not as a gain.
4. **`gantt.js` renders HTML, not SVG** ("shared Microsoft-Project-style **HTML** Gantt timeline
   primitives"). The spec insists "a Gantt is **not** exempt … both get captions", but an SVG
   `<text>` helper cannot caption a DOM Gantt. Eleven further modules in the spec's §3 caption
   table likewise render no SVG at all (`drilldown`, `scorecards`, `workbench`, `sra_risk`, …).
5. **The spec's own §7 golden SHAs are stale** (pre-ADR-0296) and its §6 points at
   `docs/UI-INVENTORY.md`, which is an intake doc at `00_REFERENCE_INTAKE/UI-INVENTORY.md`.

## Decision

**One helper.** `SFChartFrame.axisTitles(svg, {L,R,T,B}, opts)` in `chartframe.js` (layout-global,
so no chart imports anything). Placement and option names are promoted verbatim from
`performance.js`. **Horizontal, never rotated** — rotation was the second convention, and
horizontal text stays legible in all four themes and never collides with the widest tick label.

**One type token.** `--sf-fs-axis-title: 11px` in `base.css`; `.ch-at` reads it. No chart sets a
numeric size or colour in JS, so the queued CRISPNESS readability floor moves **one value** instead
of editing 30 modules. 11px is grounded three ways: DESIGN-SYSTEM §1's compact base size,
`scatter.js`'s existing caption size, and the operator-chosen 11px floor. `font-family` is
deliberately **not** set — captions inherit exactly like the tick labels beside them, leaving the
vendored-font question wholly to the batch that owns it.

**One case treatment.** `.ch-at` applies `text-transform: uppercase` + `.08em` tracking, so every
caption reads the same whatever case a caller passes. Degrades benignly (the string's own case).

**An explicit ledger instead of a heuristic.** `tests/web/test_axis_titles.py` classifies every
non-exempt module into exactly one of *captioned* / `PENDING` (16 real SVG charts still to do) /
`NO_SVG_AXES` (11 DOM visuals the SVG helper cannot serve). The spec's tick-detecting regex
under-detected by half — it missed `path.js` and `resources.js` and was silent on every HTML
visual. A **new** module matching no bucket fails the test; that is the anti-regression property
the regex could not provide, and it makes the remaining work countable rather than implied.

## What visibly changes (the honest list)

Only the five captions that already existed. No plotted value, scale, domain, tick or axis range
is touched, and no server payload changes.

| | before | after |
| --- | --- | --- |
| `performance.js` ×3 | 9px, mixed case, local `txt()` | 11px, uppercase, shared helper |
| `scatter.js` X | 11px, **centred** at bottom | 11px, uppercase, right-aligned |
| `scatter.js` Y | 11px, **rotated −90°** at left | 11px, uppercase, horizontal top-left |

## Consequences

- **Proof:** full suite **2,704 passed**; the three dashboard payload golden SHAs unchanged (a
  caption cannot move a payload hash — the spec's own invariant, held); `ruff` / `ruff format` /
  `mypy --strict` / `bandit` / `node --check` clean.
- **The guard was proved to bite.** Six mutants, each caught by its intended assertion: a
  reintroduced rotated caption; a new unclassified module; a numeric `font-size` in the caption
  block; the token removed from the CSS; the helper call deleted; and a DOM-only module mis-parked
  in `PENDING`. An earlier, narrower version of the size assertion **missed** the third mutant —
  it sliced from `function axisTitles` and the planted size sat in the node builder just above.
  Widened to the whole caption block.
- **Behaviour is executed, not pinned.** `tests/web/js/axis_titles_harness.mjs` boots
  `chartframe.js` against a DOM stub and asserts placement, the `.ch-at` hook, non-rotation, the
  no-numeric-type law, and that missing arguments are a no-op rather than a throw.
- **Outstanding, and NOT claimed:** the DoD's "renders correctly in all 4 themes + 90–125% scale"
  needs a browser; this sandbox has no automation for it (the repo's prior Chromium checks were
  manual). The static + node layers cover structure and styling hooks; the four-theme visual pass
  is owed. `text-transform` on SVG `<text>` is the one property worth eyeballing.
- **Remaining batches** are ordinary follow-on work, driven by the `PENDING` ledger shrinking to
  empty. Captioning the 11 `NO_SVG_AXES` modules needs a **DOM** label mechanism — a separate
  design decision, deliberately not invented here.
