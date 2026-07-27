# AISMAT — "The Command Deck" Design System

> Design language for **SMAT (Schedule Management Analysis Tool)** and its AI layer **AISMAT** — a forensic-grade, AI-assisted schedule-analysis instrument. This system encodes the "Command Deck" UI/UX vision: every screen leaves the viewer *smarter*, not just prettier; every visual is an instrument, not a widget; every number is cited, never invented.

**Compiler namespace:** `window.AISMATCommandDeck_f4ddd5`
**Global CSS entry:** `styles.css` (link this one file — it `@import`s all tokens + fonts)

```html
<link rel="stylesheet" href="styles.css">
<html data-theme="dark">           <!-- dark (default) | bright | contrast | console -->
<script src="_ds_bundle.js"></script>
<script>const { Button, MetricTile, StatusChip } = window.AISMATCommandDeck_f4ddd5;</script>
```

---

## 1. What this is

**SMAT / AISMAT** analyzes project schedules (P6 / MS Project / XER / MPP and other native formats) and reports their *health* — DCMA-14 quality checks, EVM (SPI/CPI/TCPI), float erosion, critical- and driving-path integrity, logic/constraint density, and schedule-risk analysis. Its differentiator is **defensibility**: any number on screen can be clicked through to the exact input fields, the formula, the source schedule update, and the citation (NASA Acumen `.aft` library, DCMA-14, or the EVM standard) it came from. When AI interprets data, the interpretation is disclosed and citation-grounded — the tool never surfaces a model-invented figure.

The interface is a **story in five acts**, not a dashboard of fifty widgets:

| Act | Name | For | Shows |
|-----|------|-----|-------|
| I | **Orbit** | anyone (exec default) | one plain-English headline finding + a constellation of program tiles sized by risk, colored by trend |
| II | **Portfolio** | PM / sponsor | dense sortable table: DCMA-14 strip, SPI/CPI sparkline, float trend, next milestone |
| III | **Program Deep-Dive** | scheduler / planner | instrument panel: Gantt w/ critical path, DCMA-14 scorecard, EVM curves, float histogram, driving-path explorer |
| IV | **Forensic Ledger** | claims / legal | every metric → its fact ledger: inputs, formula, citation, source update, disclosed AI narrative |
| V | **Data Room** | all | export / template / archive — nobody leaves empty-handed |

A **role switcher** (visible strip, not a hidden setting) re-cuts the *same* engine output for who's reading: Executive, PM, Scheduler, EVM Analyst, Forensic/Legal, Risk Manager, Compliance/CUI Reviewer. Roles change *emphasis and default landing act*, never the data.

### Load-bearing invariants (baked into the chrome, not a settings page)
- **Data sovereignty** — a persistent, undismissable offline / air-gap status chip on every screen. CUI-marked exports.
- **Fidelity** — any metric with an open question in the engine shows a visible `SUSPECTED` flag; confirmed ones show `CONFIRMED`. The UI never hides uncertainty behind a clean number.
- **Citations** — every AI-generated sentence renders its supporting fact IDs, click-through to raw data.
- **Progressive disclosure** — every instrument defaults to its takeaway view + one "expand" (⛶) to full depth. Features exist; they are one deliberate click away, never stacked on the first screen.

## 2. Sources

This system was authored from a single written brief:

- **`AISMAT — "The Command Deck"`** — the UI/UX vision document (pasted into the project). Explicitly *aspirational*: "written as if AISMAT had no front end today."

The brief cross-references these internal project artifacts, **none of which were attached** to this project. They are recorded here so a future reader with access can reconcile:
- `AISMAT-UI-CLAUDE-DESIGN-NOTE.md` — states the app is one ~845 KB server-string-templated `app.py`.
- `AISMAT-ROLES-AND-ORCHESTRATION.md` — the DECK role doctrine (tokens-only, instruments-not-widgets).
- `SMAT-MASTER-PROMPT.md` — the phased plan U1–U4 (tokens → inline-handler removal → shared charting module → restyle).
- `sf-themes.css` — the existing "console" theme this system's Console/Ops-Deck mode leans into.

**No logo, brand mark, icon set, font files, or color values were provided.** Every visual decision below is a from-scratch interpretation of the written vision, chosen to be defensible and consistent — **flagged for your review** (see CAVEATS at the end). Where a real brand asset exists, replace the interpretation.

## 3. Design principles

1. **Instruments, not widgets.** Every visual carries a plain-English *takeaway headline* above it, a legend, and a toolbar (grid / download / expand). If a chart doesn't change what someone does next, it doesn't ship.
2. **Cited, or it doesn't exist.** Numbers trace to facts. AI sentences trace to fact IDs. No free-floating model output.
3. **Uncertainty is visible.** `SUSPECTED` / `CONFIRMED` is load-bearing UI, on every flagged metric.
4. **Motion explains, never performs.** Animation is used only where it does something a static chart can't (trend reveal, before/after morph, driving-path walk, altitude zoom). It never gates a number appearing, and it has a hard off-switch.
5. **Depth on demand.** Takeaway first; full data table, filters, and statistics one labeled click (⛶) away.
6. **Role-aware, data-identical.** Emphasis and default act change by role; the underlying facts never do.
7. **Sovereign by default.** Offline/air-gap posture is shown in the chrome, always.

---

## 4. CONTENT FUNDAMENTALS

How AISMAT writes. The product's copy voice is **the analyst who already read the schedule for you** — authoritative, plain-spoken, and *teaching*. Every string should leave the reader able to act.

**Voice & person.** Declarative and imperative. Addresses the operator directly and sparingly with "you" / imperatives ("watch it", "start here"). Avoids "we" and all corporate first-person. No hype, no adjectives-as-argument.
- Finding: *"3 of 14 programs are trending red on critical-path health; Program Falcon lost 11 days of float in the last update."*
- Teaching tooltip: *"4 days of float means this activity can slip 4 workdays before it starts eating into the critical path — watch it if the upstream driving activity is already running late."*

**Findings are sentences, not labels.** The headline of every screen and instrument is a complete, plain-English sentence written from cited engine facts — never a bare metric name. The number lives inside the sentence.

**Casing.**
- *Sentence case* — headlines, findings, body, button labels, tooltips. ("Export forensic ledger", not "Export Forensic Ledger".)
- *UPPERCASE + `--ls-label` tracking* — eyebrows, column headers, status chips, section kickers. ("CRITICAL-PATH HEALTH", "SUSPECTED", "AIR-GAPPED".)
- *Title Case* — only proper nouns and program names ("Program Falcon", "DCMA-14", "Data Room").

**Numbers.** Always specific, always attributed, always in the mono face with `tabular-nums`. Teaching contexts spell the unit ("4 workdays", "11 days of float"); dense tables abbreviate ("11d", "0.92 SPI"). A number that can't be cited doesn't render as a fact — it renders as an estimate with its caveat.

**Uncertainty, in the copy.** If the engine flags a metric SUSPECTED, the sentence says so: *"SPI is 0.92 — flagged SUSPECTED (earning-rule mismatch, see caveat)."* Never smooth it into a clean number.

**Tooltips (the highest-leverage copy in the product) follow a fixed shape:** *what the value is → how it's computed → a worked example of how to act on it.* Three beats, plain English, one short paragraph.

**Errors are specific and actionable, never silent.** *"Row 14 of the SRA template has a blank 3-point estimate — most-likely duration is required. Fix the cell and re-upload."* A malformed import is rejected with a precise reason; it is never half-loaded.

**Tone register.** Serious and forensic by default — this output may end up in a claim or a deposition. Dry wit is permitted *only* in the opt-in easter eggs and never in any export, print, or court-facing view. No exclamation marks. No emoji, anywhere.

**Punctuation.** Em-dashes for teaching asides. Semicolons to join two related findings in one headline. Oxford comma. Ranges use en-dash ("90–125%").

---

## 5. VISUAL FOUNDATIONS

The look is a **dark instrument panel** — aerospace mission-control meets forensic lab. Restraint is a feature: in a tool whose output may be testimony, nothing is decorative.

### Color
Dark-first. Deep blue-black surfaces separated by **hairline borders**, a single **Signal Cyan** primary (instrumentation / interactive / brand), a **Command Gold** secondary (driving/critical path; the deliberate HUD nod), and a full **RAG** semantic set (green pass / amber near-critical / red fail) plus info blue and risk violet. **Tokens only — no loose hex in markup, ever.** Max one to two background colors per screen. Four appearance modes (Dark default, Bright, High-Contrast, Console) remap the *same* semantic tokens; see `tokens/themes.css`. Data-viz uses a fixed 6-color categorical sequence (`--viz-1…6`) so series colors are stable across charts.

### Type
Three faces, strict roles: **Space Grotesk** (display — act titles, headlines, hero metrics), **IBM Plex Sans** (UI/body — 14px dense default, tables, controls), **IBM Plex Mono** (data — float values, metrics, fact IDs, timestamps, console chrome). All numeric readouts use `tabular-nums`. Labels are uppercase with wide tracking.

### Spacing & layout
4px grid, dense. Fixed chrome: a 56px top bar, a 44px role strip beneath it, a persistent 32px bottom status bar (the air-gap indicator lives here), optional 248px left sidebar. Content is a panel grid. Fixed elements are pinned; content scrolls under them.

### Backgrounds
Flat dark fills. **No decorative gradients, no photographic hero imagery, no hand-drawn illustration** — the charts and Gantt *are* the imagery. A faint mission-control **graticule grid** (`--texture-grid`) may sit behind the Orbit canvas and empty states. The Console theme adds a subtle **scanline** texture (`--texture-scanline`). That's the entire background vocabulary.

### Corner radii
Small and precise — sharp reads as engineering-grade. Controls 6px, chips/tags/badges 4px, cards/panels 10px, pills/dots full. Nothing softer.

### Cards / panels (the instrument pattern)
Flat `--surface` fill + 1px `--border` + 10px radius + optional `--shadow-panel`. An instrument = takeaway-headline strip (top) → the visual → legend + toolbar (grid ⊞ / download ↓ / expand ⛶). **No colored-left-border accent cards. No heavy drop shadows.** Borders do the separating; shadow only lifts overlays.

### Borders & shadows
1px hairlines are the primary delimiter (`--border`, `--border-subtle` for dividers, `--border-strong` for emphasis). Shadows are minimal on flat content and deep/diffuse only under overlays (dialogs, popovers, menus). **Glow is a signal, not decoration** — reserved for live / active / focused instruments and the focus ring (2px cyan).

### Transparency & blur
A scrim (`--scrim`) dims the page behind dialogs. Status surfaces use low-alpha tints of their semantic color. `backdrop-filter: blur()` is allowed on the sticky top bar, role strip, and popovers only — never as a decorative frosted panel.

### Motion
Purposeful, and off-switchable. Signature motions: **trend reveal** (time-series draws left-to-right on load, `--dur-reveal` / `--ease-out`, so the eye tracks direction before parsing the legend); **status pulse** (a tile pulses *only* if its status changed since the last update); **driving-path march** (the critical path can "walk itself" from data date to finish); **altitude transitions** (zooming between Acts I–III is a continuous zoom, never a page cut). Everything honors `prefers-reduced-motion` (see `tokens/motion.css`) and never delays data.

### States
- **Hover** — surfaces lift to `--surface-hover`; interactive text/icons brighten toward `--accent`; borders strengthen; charts show a crosshair + value readout. No scale on surfaces.
- **Press** — buttons darken to `--accent-active` and nudge `translateY(1px)` (or `scale(0.98)`); no bounce, no elastic.
- **Focus** — 2px `--focus-ring` (cyan), optionally with a soft glow (`--ring-glow`). Always visible; never removed.
- **Disabled** — 45% opacity, `cursor: not-allowed`, no hover.
- **Selected/active** — `--accent-muted` fill + `--accent` text/border.

### Imagery vibe
Cool, dark, instrument-grade. If any photographic imagery is ever introduced, it is desaturated and cool-toned — never warm/lifestyle. Default to data as imagery.

---

## 6. ICONOGRAPHY

**No icon set was provided.** AISMAT uses **[Lucide](https://lucide.dev)** — chosen (and flagged) as the closest fit for the instrument aesthetic: consistent **2px stroke, 24px grid, round caps/joins, `currentColor`**, open-source, huge coverage. Line-only; no filled or duotone variants.

- **Delivery.** Lucide is linked from CDN in specimen cards, UI-kit screens, and the `Icon` component. To self-host or air-gap, vendor the Lucide sprite/SVGs into `assets/icons/` and repoint the component.
- **Sizing.** 14 / 16 / 20 / 24px via the `Icon` `size` prop; color inherits `currentColor`, so icons take the surrounding text token.
- **Usage.** Functional first. Instrument toolbars use icon-only actions (grid `⊞`, download `↓`, expand `⛶`) with tooltips; primary navigation pairs icon + label. The **expand `⛶`** glyph from the vision maps to Lucide `maximize` / `expand`.
- **Status is drawn with chips and dots, not icons or color alone** — a `StatusChip` carries a text label plus its dot so RAG state survives color-blindness and grayscale print.
- **No emoji, ever** (forensic/legal posture). The confetti easter-egg is canvas particles, not emoji. Unicode symbols are avoided except the established `⛶` expand affordance.

See the "Brand" group in the Design System tab for the icon specimen. If a copied/vendored asset set lands in `assets/`, document it here.

---

## 7. APPEARANCE MODES

One token system, four modes. Toggle with `data-theme` on any ancestor (`<html>` or an app wrapper). Each mode remaps the *semantic* aliases only; base ramps never change.

- **Dark** (`data-theme="dark"`, the `:root` default) — long-session analyst default; the primary brand expression.
- **Bright** (`bright`) — daylight-readable; high default for conference-room screen-sharing.
- **High-Contrast** (`contrast`) — WCAG-AA-or-better; pure black/white, thick borders, max-chroma status.
- **Console / Ops Deck** (`console`) — HUD phosphor chrome + scanline texture. Opt-in personal preference only — never a default, and stripped from every export/print/court-facing view.

Density (comfortable/compact) and a 90–125% scale control are intended to apply across all four (wire in the consuming app).

## 8. INDEX / MANIFEST

**Root**
- `styles.css` — the one file consumers link (@import manifest → tokens + component CSS).
- `readme.md` — this guide. · `SKILL.md` — Agent-Skills entry. · `thumbnail.html` — homepage tile.

**Tokens** (`tokens/`, all reached from `styles.css`)
- `fonts.css` (Google Fonts) · `colors.css` (ramps + semantic aliases) · `themes.css` (bright/contrast/console) · `typography.css` · `spacing.css` · `radii.css` · `elevation.css` · `motion.css`

**Components** (`components/<group>/`, namespace `window.AISMATCommandDeck_f4ddd5`) — each has `.jsx` + `.d.ts` + `.prompt.md`, one `@dsCard` per group:
- **core/** — `Button`, `IconButton`, `Icon`, `Badge`, `StatusChip`, `Tag`
- **forms/** — `Input`, `Select`, `Checkbox`, `Radio`, `Switch`
- **feedback/** — `Tooltip`, `Dialog`, `Toast`, `CaveatBanner`
- **instruments/** (the domain heart) — `InstrumentPanel`, `MetricTile`, `ProgramTile`, `Sparkline`, `DcmaStrip`, `CitationChip`, `GanttChart`, `TrendChart`
- **navigation/** — `Tabs`, `RoleStrip`, `AirGapIndicator`

**Intentional additions** (beyond a standard primitive set — this product's vocabulary):
- `Icon` — wrapper over the chosen Lucide set, so icon usage is one consistent API.
- `StatusChip`, `CaveatBanner` — RAG health and the SUSPECTED/CONFIRMED doctrine are load-bearing, so they are first-class components, not ad-hoc markup.
- `InstrumentPanel`, `MetricTile`, `ProgramTile`, `Sparkline`, `DcmaStrip`, `CitationChip` — the "instruments, not widgets" doctrine and the citation trail are the reason the product exists; they ship as components so no screen re-implements them.
- `GanttChart`, `TrendChart` — THE standardized chart formats: every Gantt and every metric-over-time chart in the product renders through these, so the format and the options strip (Float · Driving · Walk · Baseline) sit in the same place everywhere; specialized tabs append page-specific options to the same strip.
- `RoleStrip`, `AirGapIndicator` — the visible role switcher and the persistent sovereignty chip are required chrome per the vision.

**UI kit** (`ui_kits/aismat/`) — full five-act app recreation plus role stations (Risk/SRA, Compliance/CUI) and a Data station (native XER/MPP/XML/XLSX/CSV/JSON ingest with the no-silent-failures pipeline and update chain-of-custody), a resumable story tour, live global search with deep links, and a six-tab Deep-Dive covering the full metric inventory: trends of every measure across updates, the complete EVM set (SV/CV/VAC/ETC/TCPI/SPI(t)/BEI/CPLI), schedule-quality scoring (health gauge, open ends, constraint/logic density, out-of-sequence), forensic instruments (manipulation detection, windows analysis, delay responsibility matrix, CP shift log), a driving-path logic explorer, before/after Gantt morphing, depth-on-demand data tables, density + 90–125% scale controls, and the four vision easter eggs (extras-gated). Entry `index.html`; see its `README.md`.

**Foundations** — 18 specimen cards across the Design System tab groups: Colors (6), Type (5), Spacing (3), Brand (4).

## 9. CAVEATS — please help me make this perfect

Everything visual here is a from-scratch interpretation of the written vision — **no logo, brand colors, fonts, icons, or codebase were provided.** The biggest open questions:
- **Fonts** are loaded from Google Fonts CDN (Space Grotesk / IBM Plex Sans / IBM Plex Mono) — chosen to read as engineering-grade. If AISMAT has real brand faces, send the files and I'll self-host + rewire `@font-face`.
- **Colors** (Signal Cyan primary, Command Gold, RAG set) are my interpretation of the "Command Deck / HUD" direction. If there is a real palette (or the existing `sf-themes.css` console theme), share it and I'll retune every token.
- **Icons** substitute **Lucide** (flagged). If there's a house icon set, vendor it in and I'll repoint `Icon`.
- **No logo/mark** was supplied, so the brand renders as a type-only "AISMAT" wordmark everywhere a mark would go. I did not invent a logo.
- The five acts, roles, and metrics reflect the vision doc; the referenced `app.py` / `sf-themes.css` were **not attached**, so nothing is verified against the real engine. The Risk station's Monte-Carlo distribution carries the vision's own **UNVERIFIED** flag in-UI.

**Tell me which of these to lock down first** — real palette, real fonts, or the logo — and I'll iterate until it's exactly AISMAT.

