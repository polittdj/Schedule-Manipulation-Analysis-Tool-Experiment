# ADR-0175 — POLARIS brand + hand-set NASA-worm-style masthead wordmark

## Status

Accepted. Operator 2026-07-09: name the tool with a bold NASA-style title at the top. Five
alternatives were offered against the operator's AISMAT; the operator chose **POLARIS —
Program Oversight & Logic Analysis for Risk & Integrity of Schedules** "with the typography
plan cooked in."

## Context

The masthead was a plain-text `<h1>▲ SCHEDULE FORENSICS</h1>`. A NASA-style display face
(Orbitron-class geometric or the NASA worm) cannot come from a CDN — the strict air-gap CSP
forbids external assets — and vendoring a binary webfont adds licensing + payload for seven
letters. The wordmark also has to hold up on all three headers (light, dark, JARVIS HUD).

## Decisions

1. **Name: POLARIS.** The north star — fixed point you steer by when a schedule's been
   manipulated. Backronym: *Program Oversight & Logic Analysis for Risk & Integrity of
   Schedules*. Applied to the masthead, the page `<title>` ("&lt;page&gt; — POLARIS"), the FastAPI
   app title, the Word report title, the Executive Briefing / Diagnostic Brief document titles,
   and the launcher console line. The pip package / CLI (`schedule-forensics`) and the Windows
   `.vbs` launcher filename are unchanged — renaming distribution artifacts is out of scope.
2. **Hand-set SVG wordmark, no webfont.** The seven letterforms are drawn as inline SVG strokes
   in the NASA-worm idiom — uniform 13-unit stroke, rounded caps/joins, capsule O, crossbar-less
   arch A, single-stroke serpentine S — plus a four-point **north star** sparkle after the S.
   Fully inline in the layout template: zero external requests, byte-stable, renders identically
   on every machine (Law 1 / air-gap intact). Color is the worm's iconic red (#e8432e) with a
   restrained drop-shadow glow that reads on the light, dark, and HUD headers.
3. **Backronym tagline** tracked out beneath the mark (mission-patch style), `var(--muted)`,
   hidden under 1200px so the nav never crowds. The `h1.brand` carries the full name via
   `aria-label` (screen readers announce "POLARIS — Program Oversight…"), and the block is
   `data-no-i18n` so client-side translation never rewrites the brand.
4. **Layout gotcha pinned in CSS:** a column-flex child SVG stretches to the h1 width and
   `preserveAspectRatio` centers the drawing inside (an indent) — fixed with
   `aspect-ratio: 344/72; align-self: flex-start`.

## Consequences

- Verified in Chromium screenshots (reviewed): light, dark, and HUD headers + a zoomed letterform
  proof; flush-left with the tagline, zero console errors; `<title>` reads "Dashboard — POLARIS".
  Pinned by `test_app.py::test_polaris_masthead_wordmark` (title, brand block, SVG letterforms,
  backronym, aria-label) with the air-gap + a11y suites green.
- `src/` changed (`app.py` layout + `app.css`) → wheel + 9 installers rebuilt in the same commit
  (ADR-0148 lockstep).
- The repo/product prose still says "schedule forensics" where it describes the *discipline*;
  POLARIS is the product name. Deeper renames (package, repo, docs) are deliberate future work if
  the operator wants them.
