# ADR-0146 — HUD/UI layer: compliance drawer, page explainers, JARVIS theme, live telemetry, guided hints

## Status

Accepted.

## Context

Operator directive: make the UI a top-tier NASA schedule-forensics interface — with all required
CUI/ITAR warnings, discoverable hints throughout, per-metric and per-visual explanations with
decision guidance, a unique look, an optional JARVIS-style theme, live machine telemetry
(CPU/RAM/GPU/disk/temps) in small expandable windows, and languages that translate everything with
a guaranteed way back. All of it must respect Law 1 (loopback-only, air-gapped, std-lib runtime
I/O) and Law 2 (no engine number changes — this layer is pure presentation).

## Decision

One additive presentation layer, no engine or metric changes:

1. **Compliance drawer (every page, every theme).** A collapsed `<details class=compliance-drawer>`
   directly under the top CUI banner: three sections covering CUI handling (32 CFR Part 2002),
   ITAR (22 CFR 120–130) / EAR (15 CFR 730–774) export-control exposure of NASA schedule data,
   and the operator's responsibility. It is **unconditional** — shown even when the session is
   marked UNCLASSIFIED, because the education applies regardless of the current marking (the
   *marking banners* still switch; `test_cui_marking_reflects_unclassified_mode` now asserts on
   the banner elements, not the whole page). CUI banner colors align to convention: CUI purple,
   UNCLASSIFIED green.
2. **Page explainers.** `_page()` injects a collapsed `details.explain` block ("What am I looking
   at — and how do I use it?") from a title-keyed map (`_EXPLAINERS`, 21 pages), each with three
   fixed sections: *What this shows / How to read it / Decisions it informs* — analyst-grade,
   decision-focused prose. Central injection guarantees coverage without touching 22 views.
3. **Hints.** CSS-only tooltips via `data-sf-hint` attributes; dismissable per-page `.guide-tip`
   blocks persisted in localStorage (`hints.js`); a one-time soft pulse nudge on the first key
   control a new user needs. `/help` rows gained `id=m-<metric>` anchors and the DCMA tooltips
   deep-link to them ("Full definition, example and decision guidance »").
4. **JARVIS theme.** A third `data-theme=jarvis` skin in `hud.css` (cyan/gold HUD: glass panels
   with corner brackets, grid background, scanline sweep, glowing headers). `theme.js` cycles
   Light → Dark → JARVIS and announces the *next* theme via `aria-label` (aria-pressed is
   two-state semantics — wrong for a cycler). Default remains Light; the professional themes are
   untouched. All effects are pure CSS — no fonts, no images, no remote assets (air-gap holds).
5. **Live telemetry.** `web/system.py` + `GET /api/system` + `sysmon.js`: a fixed dock of
   CPU/RAM/GPU/DISK chips, each expandable to a detail card (cores, temps, totals, VRAM). Polls
   loopback every 2 s (CSP `connect-src 'self'`), pauses when hidden, ON by default only in
   JARVIS, toggleable and persisted in every theme. Collectors are **local reads only** —
   `/proc`, `/sys`, `shutil.disk_usage`, an optional local `nvidia-smi` subprocess — with
   `psutil` as an *optional* enhancer (`[project.optional-dependencies] monitor`; installers
   attempt it best-effort, never fatally). Every field is nullable; missing values render "—".
   Law 1 untouched: nothing here can reach a network.
6. **i18n.** The new fixed strings (explainer headings, drawer headings, theme labels, "Tip:")
   joined the `_TERMS` catalog in all four languages; long explainer prose rides the existing
   AI-fallback + non-destructive `translate.js` pass, which stores originals per node — so
   switch-back to English is structurally guaranteed. Telemetry numbers are `data-no-i18n`.
7. **Packaging.** The wheel now carries `system.py` + the new static assets (package-data), and
   all nine installers were regenerated from the rebuilt wheel — verified end-to-end by executing
   the Linux installer and importing the deployed telemetry module.

## Consequences

- Every page now educates on CUI/ITAR handling, explains itself, and guides first use — without
  a single engine figure changing (full parity/test gate green).
- The JARVIS skin and telemetry dock are strictly opt-in layers over the professional default;
  reduced-motion preferences neutralize the decorative animation.
- `/api/system` exposes machine load metrics on loopback only — no schedule content, no egress.
- Regenerating installers on UI changes is now part of the release loop (the embedded wheel must
  match the source, enforced by the installer regression tests).
