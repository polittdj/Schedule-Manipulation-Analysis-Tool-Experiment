# Schedule Forensics — Design System & Theme Rulebook
> Drop this file into `docs/DESIGN-SYSTEM.md`. Every session that touches the web UI
> must follow it, the same way HANDOFF.md governs build state. The interactive
> reference is the prototype (`Mission Ops Redesign.dc.html`); when this doc and the
> prototype disagree, the prototype wins.

## 0. The two design laws (add to your build prompt)
1. **Nothing styles itself.** Every color, font, radius, and shadow comes from a CSS
   custom property in `sf-themes.css`. A hex value in page markup is a build failure
   (exceptions: the fixed CUI marking colors and the risk-heat band colors).
2. **Every visual is an instrument.** A chart without a takeaway headline, a labeled
   data-date line, a legend, and the Data/Excel/Enlarge toolbar is not done.

## 1. Tokens (names as used in the repo's base.css)
Themes: `console` (default dark) · `daylight` (light) · `apollo` (CRT) · `jarvis` (HUD),
set as `html[data-theme=…]`, chosen via the header View dropdown, persisted in
localStorage. The ☀/☾ toggle maps daylight ↔ last dark theme.

Semantic roles (never repurpose):
- `--accent` — interaction + "current/planned" series. NEVER for warnings.
- `--ok` / `--warn` / `--bad` — pass / caution / fail·critical. Same meaning in every chart.
- NASA red `#FC3D21` family (`--rd` in prototype) — reserved: critical path, data-date
  line, alarm verdicts. Not decoration.
- `--muted` — secondary text, completed work, baseline series.
- `--panel` on `--bg`; hairlines `--line`; chart canvas gets the dotted reading grid
  (`--grid-dot`, 22px pitch).

Type (vendor locally for air-gap):
- UI: Barlow (400/600/700) · Display/headers: Barlow Semi Condensed 700
- Data, numbers, labels, citations: IBM Plex Mono (tabular numerals)
- Base size 11px (operator compact standard); header UI-scale control multiplies it.
  Floors: 8px mono labels, never smaller.
- Apollo theme: everything mono + uppercase + 0 radius (handled by tokens, don't hand-style).

## 2. Page anatomy (every report page)
```
CUI bar (top, purple #502B85) → compliance drawer → command header →
nav (left rail on dark themes / top bar on daylight) → main → CUI bar (bottom)
```
- Header: insignia (wireframe globe = AI status light) + "SCHEDULE FORENSICS /
  Manipulation Analysis Console". The word NASA never appears.
- Every page is a **chapter**: kicker (`CHAPTER NN · NAME`), takeaway h1 (a sentence
  with a number in it, not a label — "Six months in: 46% complete — and the margin is
  gone."), one muted context line, then panels, then a **Continue footer** (segue
  sentence + button to the next chapter). Nav shows chapter numbers + story-progress
  dots + the current chapter's one-line takeaway.
- Chapter order: 00 Import → Mission Control → 01 Status → 02 Drivers → 03 Trend →
  04 Bow Wave → 05 Forecast → 06 Compare → 07 Briefing. New pages must be given a
  place in this narrative (or live under Setup/Help, outside the story).

## 3. Panel anatomy
Head: `h2` (12px display, uppercase) + one-line muted description ("what am I looking
at") + right-aligned toolbar. Body: content. Foot: legend / source line (mono, muted).

**Toolbar contract — every data visual ships all three:**
- `▦ DATA` — toggles the underlying table inline (the accessibility table, made visible)
- `⤓ EXCEL` — exports that visual's data (server: existing xlsx/csv endpoints)
- `⛶ ENLARGE` — panel spans full width / grows; state persists per persist.js
Tables get `⤓ EXCEL` only. Options (column pickers, zoom, filters) sit left of the
toolbar as chips/selects, and persist.

## 4. Chart language (the consistency rules)
- One coordinate treatment: dotted reading grid, hairline axes, 8–9px mono tick labels.
- Data date: always a `--rd` vertical line labeled `DD` / `DATA DATE`, on every
  time-axis chart, no exceptions.
- Series semantics: baseline = muted dashed · current/actual = accent solid ·
  forecast = warn dashed · critical = red. Milestones are 45°-rotated squares.
- Every chart carries a one-line "how to read this" in muted text.
- Chart-type fitness (the "wrong visual" fix): trends over versions → slope/line with
  labeled deltas; composition → single stacked bar with legend counts; schedule spans
  → Gantt bars with progress fill; distribution over months → columns with DD marker;
  forecasts → date ruler with a P10–P90 window band; diffs → old → new ledger rows
  with a shift column. No pies, no 3D, no dual axes.
- Numbers in charts are computed, never typed; cite source (`file · UID · task`) in
  the foot line where a claim is made.

## 5. Voice
Headlines state findings ("Five updates, five slips — and the slips aren't
shrinking."), not topics ("Trend Analysis"). Buttons are verbs. Citations are chips:
`⌖ KESTREL3_v5.xer · UID 1080`. Severity words: HIGH/MED/LOW, colored by role tokens.

## 6. Compliance chrome (never restyle away)
CUI bars top+bottom on every page and every print/export; compliance drawer under the
top bar; `LOCAL · 127.0.0.1` pill in the header. Exports embed the marking (see the
briefing .doc pattern).

## 7. Definition of Done for any new/edited page
- [ ] Tokens only; renders correctly in all 4 themes + both densities + 90–125% scale
- [ ] Chapter kicker, takeaway h1, context line, Continue segue, nav entry with takeaway
- [ ] Every visual: DD line, legend, read-me line, ▦/⤓/⛶ toolbar, options persist
- [ ] CUI bars print; controls hidden in print (`data-noprint` / `.cf-bar` pattern)
- [ ] Keyboard focus ring visible (`--focus`); reduced-motion kills animation/timers
- [ ] No remote asset (air-gap test stays green); no calculation touched
