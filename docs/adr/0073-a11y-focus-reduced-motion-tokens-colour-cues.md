# ADR-0073 — Accessibility foundations: focus ring, reduced-motion, theme tokens, non-colour cues

Date: 2026-06-18 · Status: accepted

## Context

An external seven-role audit work order (the agency is federal, so Section 508 / WCAG 2.1 AA
matters) found several front-end accessibility gaps, all re-confirmed valid on current `main`:

* **A1 (WCAG 2.4.7)** — the `--focus` token was defined but used nowhere; there were no
  `:focus-visible`/`outline` rules, so keyboard users got no visible focus on links, buttons,
  inputs, or sortable headers.
* **A2 (WCAG 2.3.3)** — five auto-play stepper charts (`cei`, `drift`, `path_evolution`, `scurve`,
  `trend_drill`) flip frames on a `setInterval`, and CSS uses transitions, with no
  `prefers-reduced-motion` guard anywhere.
* **A6** — `app.css` used `var(--border, …)` and `var(--grid-line, …)` but neither token was ever
  defined, so both always fell back to hardcoded values that don't adapt to the light theme.
* **A8 (WCAG 1.4.1)** — Gantt criticality (critical/driving = red) was encoded by hue alone on the
  bars themselves (≈8% of men have a colour-vision deficiency).

## Decision

Presentation-only, dependency-free, same-origin (air-gap intact):

1. **Visible keyboard-focus ring (`base.css`).** `:where(a,button,input,select,textarea,summary,
   [tabindex]):focus-visible { outline:2px solid var(--focus); outline-offset:2px }` — theme-aware
   (the previously-orphaned `--focus` token), keyboard-only (`:focus-visible`, no ring on mouse
   click).
2. **Reduced-motion honored.** A `@media (prefers-reduced-motion: reduce)` block neutralizes CSS
   animations/transitions, and each of the five auto-play `toggleAuto()` handlers gates its timer on
   the same preference — under "reduce motion" the Auto-play button advances **one frame** instead of
   starting a continuous flip (Prev/Next manual stepping is unaffected, so all content stays
   reachable).
3. **Define the orphaned tokens (`base.css`).** `--border` (= `var(--line)`) and `--grid-line` are
   defined in **both** the dark `:root` and the `html[data-theme=light]` blocks, so export-bar
   borders and path/grid tick lines match the active theme in light mode.
4. **Non-colour cue for criticality (`app.css`).** Critical (`.g-bar.g-crit`) and driving-path
   (`.gantt-bar.tier-DRIVING`) bars also carry a diagonal **hatch** (a `repeating-linear-gradient`
   overlay) so criticality is distinguishable without relying on hue. The palette is unchanged.

Also added the `.sr-only` visually-hidden helper to `base.css` as groundwork for the chart
screen-reader data-table fallback (audit A3), which lands as its own follow-up PR.

## Scope / safety

No engine/CPM/metric change → **parity 10/10**. Air-gap unchanged (no library, no webfont, no remote
asset; air-gap scan still green). Tests (`tests/web/test_accessibility.py`): the `:focus-visible`
ring referencing `var(--focus)`; the reduced-motion media block plus a `prefers-reduced-motion`
reference in all five auto-play files; `--border`/`--grid-line` defined in both theme blocks; the
`.sr-only` helper; and the hatch cue on the critical/driving bars. Full gate green;
ruff/format/mypy/bandit clean.

Remaining audit items as their own PRs: A3 (chart accessible names + sr-only data tables), A4 (table
`scope`), A5 (print stylesheet), A7 (CSP + nosniff), A9/A10 (responsive nav + theme polish), A11
(HANDOFF-drift test). The HANDOFF staleness half of A11 was already fixed by the #128–#132 updates.
