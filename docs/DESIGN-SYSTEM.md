# Schedule Forensics — Design System & Theme Rulebook (Mission Ops)

> Adopted from the operator's Mission Ops design handoff (ADR-0195). Every session that
> touches the web UI must follow it, the same way HANDOFF.md governs build state. The
> interactive reference is the operator-held prototype (`Mission Ops Redesign v2.dc.html`
> in the design handoff bundle — not committed; ask the operator when pixel truth is
> needed); when this doc and the prototype disagree, the prototype wins. Integration is
> phased (ADR-0195): **tokens (done) → global chrome → page shells, one per PR → new
> analytics panels**. Never big-bang.

## 0. The two design laws
1. **Nothing styles itself.** Every color, font, radius, and shadow comes from a CSS
   custom property in `sf-themes.css`. A hex value in page markup is a build failure
   (exceptions: the fixed CUI marking colors and the risk-heat band colors).
2. **Every visual is an instrument.** A chart without a takeaway headline, a labeled
   data-date line, a legend, and the Data/Excel/Enlarge toolbar is not done.

## 1. Tokens (names as used in the repo's base.css)
Themes: `console` (default dark) · `daylight` (light) · `apollo` (CRT) · `jarvis` (HUD),
set as `html[data-theme=…]`, chosen via the header View dropdown, persisted in
localStorage (`sf-theme`; theme.js migrates legacy `light`→daylight, `dark`→console).
The #themeToggle button maps daylight ↔ the last dark theme (`sf-theme-dark`).

Semantic roles (never repurpose):
- `--accent` — interaction + "current/planned" series. NEVER for warnings.
- `--ok` / `--warn` / `--bad` — pass / caution / fail·critical. Same meaning in every chart.
- NASA red `#FC3D21` family (`--nasa-red` / `--header-line`) — reserved: critical path,
  data-date line, alarm verdicts. Not decoration.
- `--muted` — secondary text, completed work, baseline series.
- `--panel` on `--bg`; hairlines `--line`; chart canvas gets the dotted reading grid
  (`--grid-dot`, 22px pitch).
- Header chrome reads `--header-bg` / `--header-ink` / `--header-muted` /
  `--header-line` / `--header-shadow` (wired in base.css; per-view values in
  sf-themes.css; base.css `:root` keeps the classic blue banner as the no-JS fallback).

Type (vendor locally for air-gap — NOT yet done; system stacks in use):
- UI: Barlow (400/600/700) · Display/headers: Barlow Semi Condensed 700
- Data, numbers, labels, citations: IBM Plex Mono (tabular numerals)
- Base size 11px (operator compact standard); header UI-scale control multiplies it.
  Floors: 8px mono labels, never smaller.
- Apollo theme: everything mono + uppercase + 0 radius (handled by tokens, don't hand-style).

## 2. Page anatomy (every report page)
```
CUI bar (top, purple) → compliance drawer → command header →
nav (left rail on dark themes / top bar on daylight) → main → CUI bar (bottom)
```
- Header: insignia (wireframe globe = AI status light). The word NASA never appears.
- Every page is a **chapter**: kicker (`CHAPTER NN · NAME`), takeaway h1 (a sentence
  with a number in it, not a label — "Six months in: 46% complete — and the margin is
  gone."), one muted context line, then panels, then a **Continue footer** (segue
  sentence + button to the next chapter). Nav shows chapter numbers + story-progress
  dots + the current chapter's one-line takeaway.
- Story spine (three acts / twelve chapters, per the v2 prototype): 00 Import →
  Mission Control (overview) → Act I · Situation: 01 Where we stand · 02 Can we trust
  the plan? → Act II · Diagnosis: 03 What drives the date · 04 How stable is the path ·
  05 How it moved · 06 Work piling up · 07 How we execute · 08 Who is overloaded →
  Act III · Outlook: 09 Where it lands · 10 What changed · 11 What could go wrong ·
  12 The briefing. Utilities (Groups & Filters, AI Settings, Metric Dictionary) live
  in a **Setup** nav group off the spine. New pages must be given a place in this
  narrative (or live under Setup, outside the story).

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
- Data date: always a red vertical line labeled `DD` / `DATA DATE`, on every
  time-axis chart, no exceptions.
- Series semantics: baseline = muted dashed · current/actual = accent solid ·
  forecast = warn dashed · critical = red. Milestones are 45°-rotated squares.
- Every chart carries a one-line "how to read this" in muted text.
- Provenance: a chip reading `SOURCE: <file> · DD YYYY-MM-DD`; single-version visuals
  get a file/version picker; multi-version visuals label each series/point by version;
  target-dependent visuals show a `measured to <target>` chip.
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
`⌖ <file> · UID <n>`. Severity words: HIGH/MED/LOW, colored by role tokens.

## 6. Compliance chrome (never restyle away)
CUI bars top+bottom on every page and every print/export; compliance drawer under the
top bar; the local-only posture messaging in the header/footer. Exports embed the
marking (see the briefing .doc pattern).

## 7. Definition of Done for any new/edited page
- [ ] Tokens only; renders correctly in all 4 themes + both densities + 90–125% scale
- [ ] Chapter kicker, takeaway h1, context line, Continue segue, nav entry with takeaway
      (applies once the story-chrome step lands; until then keep the current nav intact)
- [ ] Every visual: DD line, legend, read-me line, ▦/⤓/⛶ toolbar, options persist
- [ ] CUI bars print; controls hidden in print (`data-noprint` / `.cf-bar` pattern)
- [ ] Keyboard focus ring visible (`--focus`); reduced-motion kills animation/timers
- [ ] No remote asset (air-gap test stays green); no calculation touched
- [ ] No engine/calculation change; every displayed number traces to the engine payload;
      missing values show `—`, never a fabricated figure
