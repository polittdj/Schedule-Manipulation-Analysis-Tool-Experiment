# ADR-0195 — Mission Ops redesign step 1: the four-theme token system

## Status

Accepted. Operator 2026-07-11: uploaded the "Mission Ops" UI-redesign handoff bundle
(interactive prototype `Mission Ops Redesign v2.dc.html` + `README.md` spec +
`DESIGN-GUIDE.md` rulebook + `sf-themes.css` drop-in tokens) — a full presentation-layer
redesign to be integrated in the bundle's own phased order: **tokens → global chrome →
page shells (one per PR) → new analytics panels**. This ADR is the tokens step.

## Context

The app had three views: light (the default), dark (bare `:root` tokens, no `data-theme`
attribute), and JARVIS (hud.css). The command-banner header hard-coded the NASA-blue
gradient and white inks in base.css, so no token change could re-theme it. The redesign
specifies four complete views — `console` (dark mission control, the new default),
`daylight` (clean light), `apollo` (retro CRT), `jarvis` (refined HUD) — selected from a
header View dropdown, with the ☀/☾ toggle remapped to daylight ↔ last-dark-view.

## Decisions

- **`static/sf-themes.css` (new)** carries the complete token block for each of the four
  views on `html[data-theme=…]`, including the new header tokens `--header-bg/-ink/-muted/
  -line/-shadow`, plus the Apollo chrome rules (mono type, square corners, scanline wash).
  Linked AFTER hud.css so its jarvis token values win ties while hud.css keeps the
  glow/scanline effect rules (tests still require hud.css wired on every page).
- **base.css keeps `:root` (dark) and `html[data-theme=light]`** as the no-JS fallback —
  the classic blue banner now rides in `:root --header-bg` — and the header chrome rules
  read the tokens (`header{background:var(--header-bg);border-bottom:3px solid
  var(--header-line)}`, inks via `--header-ink`/`--header-muted`). Byte-pinned geometry
  (slim-band padding, globe position, sticky) is untouched.
- **theme.js rewritten**: console is the default; legacy saves migrate (`light`→`daylight`,
  `dark`/unknown→`console`) and the migrated value is written back pre-paint; the View
  `<select id=themeSelect>` applies/persists any view; `#themeToggle` round-trips
  daylight ↔ the last dark view (`sf-theme-dark`). Never follows `prefers-color-scheme`
  (unchanged posture). uiScale/sf-scale zoom and the targetform stamp are preserved.
- **Migration executed, not assumed**: `tests/web/js/theme_switch_harness.mjs` runs
  theme.js under node (stubbed DOM/localStorage) and drives the migration, the select,
  and the toggle round-trip (21 checks); plus markup/token pins updated across
  `test_target_and_theme` / `test_accessibility` / `test_hud_layer` / `test_nasa_theme` /
  `test_airgap` / `test_static_cache`.
- **`docs/DESIGN-SYSTEM.md` (new)** — the bundle's DESIGN-GUIDE rulebook, adopted as the
  standing contract for all web-UI work (tokens only, chart contract, 12-chapter story
  spine for later steps, DoD checklist); CLAUDE.md now points to it.
- **Version 1.0.4 → 1.0.5** so deployed installs cache-bust the changed assets
  (ADR-0148 precedent); wheel + nine installers regenerated in the same commit.
- Fonts (Barlow / IBM Plex Mono) are NOT vendored yet — system stacks apply; vendoring
  woff2 locally is part of the chrome step.

## Consequences

- Every page re-themes across all four views with zero per-page changes (17 chart JS
  files route `var(--token)` fills/strokes through element.style, so SVG charts follow
  live). Gantt surfaces stay deliberately MS-Project-light in every view (app.css lock).
- The old "light"/"dark" vocabulary survives only as base.css fallback blocks and the
  localStorage migration path; the globe canvas keeps its fixed blue palette (matches
  console/daylight headers; revisit at the chrome step).
- Next steps (separate PRs, per the bundle): global chrome (header regrouping, story
  nav + Continue footers, global Analysis-Target selector), then per-page shells, then
  the new analytics panels — all on existing engine data only.
