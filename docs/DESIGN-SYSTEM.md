# Schedule Forensics — Design System & Theme Rulebook (Mission Ops)

> Adopted from the operator's Mission Ops design handoff (ADR-0195). Every session that
> touches the web UI must follow it, the same way HANDOFF.md governs build state. The
> interactive reference is the operator-held prototype (`Mission Ops Redesign v2.dc.html`
> in the design handoff bundle — not committed; ask the operator when pixel truth is
> needed); when this doc and the prototype disagree, the prototype wins. Integration is
> phased (ADR-0195): **tokens (done) → global chrome (done) → page shells, one per PR (done —
> all 12 chapters shelled, through ADR-0210) → new analytics panels (in progress)**. Never
> big-bang.

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
  12 The briefing.
- Off-spine rails (ADR-0425, per the v2 prototype): pages outside the story sit in one
  of **four** named nav groups — **Forensics** (Schedule Integrity), **Library** (Metric
  Workbench, One-Pager Timeline, WBS Rollup, Schedule ID Card, EVM), **Control** (Margin Dashboard,
  Standards & Execution, Assessment Scorecards) and **Setup** (Groups & Filters, AI
  Settings, Metric Dictionary). New pages must be given a place in the narrative, or a
  rail — and a rail is chosen by what the page *is*, not by what is convenient: an
  analysis surface never lands in Setup.
- Rail membership is nav **placement only**. A page's chapter comes from its `_page`
  title / explicit `chapter=`, never from where its link renders, so a page may sit on a
  rail and still be a chapter drill (`/integrity` is a Chapter-02 page on the Forensics
  rail). Off-spine membership is **declared** in `_OFF_SPINE`, never inferred from a
  label — a rail omitted from that set silently joins the Continue segue and the progress
  dashes.
- A rail entry whose route cannot resolve yet (`@wbs` / `@card` with nothing loaded) is
  **skipped, not rendered pointing at `/`** — the same rule ADR-0255 gives the role
  Start-here cards. Never ship a nav entry for a screen that does not exist.

## 3. Panel anatomy
Head: `h2` (12px display, uppercase) + one-line muted description ("what am I looking
at") + right-aligned toolbar. Body: content. Foot: legend / source line (mono, muted).

**Toolbar contract — every data visual ships all three:**
- `▦ DATA` — toggles the underlying table inline (the accessibility table, made visible)
- `⤓ EXCEL` — exports that visual's data (server: existing xlsx/csv endpoints)
- `⛶ ENLARGE` — the panel grows. **Two layouts, one glyph (ADR-0305):** a `.mosaic .tile` panel
  spans the wall in place (`grid-column:1/-1` + a `74vh` chart host) and stays in the flow, so
  several may be open at once; any other panel lifts into a near-full-viewport **focus overlay**
  (`.panel.is-big:not(.tile):not(:has(.sf-tilebox))`), of which only **one** may be open at a time,
  dismissable with Escape. It is a focus view, not a magnifier: a panel taller than the overlay gets
  an internal scroller. The enlarged state is **NOT persisted** — restoring a page with a modal
  already up is worse than not restoring it.
Tables get `⤓ EXCEL` only. Options (column pickers, zoom, filters) sit left of the
toolbar as chips/selects, and persist.

## 4. Chart language (the consistency rules)
- One coordinate treatment: dotted reading grid, hairline axes, 8–9px mono tick labels.
- **One caption convention per medium (ADR-0298/0326):** SVG charts caption axes via
  `SFChartFrame.axisTitles` (`.ch-at`, corner placement); DOM visuals caption natively —
  a data table carries `<caption class="ch-atd">` via `SFGantt.tableCaption`, and a
  Gantt-family timescale carries the ONE slot row `buildTierScale` renders from the page's
  `data-ts-caption` marker. Both DOM mechanisms live in `gantt.js` because it is head-loaded
  and every captioned table is built by a body script (ADR-0340); no other module may name
  `.ch-atd`. Same token, same case, same color voice; only the mechanism follows the medium.
- Data date: always a red vertical line labeled `DD` / `DATA DATE`, on every
  time-axis chart, no exceptions. **One mechanism (ADR-0342):** `SFGantt.dataDateLine`,
  in `gantt.js` for the same head-loaded reason `tableCaption` is — most charted pages
  draw at parse time, before `chartframe.js` exists. Colour and type come from `.ch-dd`
  (`--bad`, and the same `--sf-fs-axis-title` token the captions read); no chart may
  hand-roll a marker or hard-code its size. **"Time axis" is narrower than "ordered by
  time" and narrower than "denominated in dates"** — a *version* axis (one tick per
  loaded file) and an *outcome* axis (a distribution over a simulated finish) both carry
  dates and take no DD line, because neither has a position for one. The population is a
  derived ledger, not a list: `tests/web/test_dd_line_ledger.py`.
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
      (the story-chrome and all 12 page shells have landed — the full spine applies)
- [ ] Every visual: legend, read-me line, ▦/⤓/⛶ toolbar, options persist — and a DD line
      via `SFGantt.dataDateLine` **if its x is a real calendar axis**; if it is a version or
      outcome axis it takes none, and either way the chart must be bucketed in
      `tests/web/test_dd_line_ledger.py`, which fails until it is (ADR-0342)
- [ ] CUI bars print; controls hidden in print (`data-noprint` / `.cf-bar` pattern)
- [ ] Keyboard focus ring visible (`--focus`); reduced-motion kills animation/timers
- [ ] No remote asset (air-gap test stays green); no calculation touched
- [ ] No engine/calculation change; every displayed number traces to the engine payload;
      missing values show `—`, never a fabricated figure
- [ ] Any sound follows the audio rule (§8): synthesized, gesture-primed, visibly controllable

## 7a. The Boot Screen (`/launch`, ADR-0426) — the one page outside the shell
The startup lightshow is the **only** route that does not render through `_page`. A boot
screen with a nav rail is a dashboard with a picture on it, so it has no nav, no chapter
kicker, no Continue segue — and therefore §7's chapter checklist does not apply to it. Four
rules do:
- **Compliance chrome is not optional off the shell.** Both CUI bars come from
  `_cui_marking(state)` and the drawer from `_compliance_drawer(state)` — the SAME functions
  `_page` uses, so the notice cannot drift. There is exactly one copy of the CUI/ITAR/EAR
  prose in the tree; if you ever need a second, you need a shared function instead.
- **Cinema does not license invented numbers.** The prototype's telemetry counts down
  "225.4 M km" and "14 pre-flight checks" with nothing behind either. §7's rule holds here
  too: the tiles read real session facts, and an unknown renders `—`, never `0`.
- **The ground is dark in every theme — the one sanctioned departure from theme-following.**
  An additive particle field adds light to a dark ground and has no light-mode equivalent
  (daylight renders as a grey smear with unreadable ink — measured, not assumed). The stage
  carries its own `--boot-*` surface tokens, declared in `launch.css`, which only this page
  loads. The themes still differentiate through `--boot-accent` / `--boot-warm`. **This is
  not a precedent for other pages**: any other screen that wants to stop following the theme
  needs its own ADR.
- **Reduced motion means STILL, not BLANK.** Compose one frame and never re-arm the loop; skip
  the transit rather than making someone wait through it. A screen that renders nothing under
  `prefers-reduced-motion` has not honored it — it has removed itself.

Any new full-bleed or animated surface answers all four before it ships.

## 7b. Two populations on one page (ADR-0420 / ADR-0427)
A page may legitimately carry more than one population — Chapter 04 pairs an ALL-VERSION
stability band with PAIR-scoped what-if ledgers, and both are correct. The rule is not
"make them agree"; it is **every panel names the population it was computed from, in its
own takeaway**. A count with no scope beside it will be read against whatever the rest of
the page is about. When two surfaces share a dataset, assert they embed it **byte for
byte** rather than that both "look right": one schedule must never yield two answers.

## 8. Audio (the Boot Audio Hum rule — ADR-0328)
Sound in this tool is SYNTHESIZED WebAudio, never a shipped asset (the air-gap and the lean
wheel/installers both stay trivially true). An `AudioContext` is created/resumed ONLY inside a
genuine user-gesture handler (autoplay policy — a programmatic event never primes); playback
scoped to one page phase must FADE (≤200 ms) before any navigation, never hard-cut. Any sound
that starts automatically carries a VISIBLE mute + volume control near the sound's home
(WCAG 1.4.2 asks for a control, not silence — the operator chose audible-at-low-gain defaults),
persisted in localStorage under the `sf-*` house pattern. Every gain change is a ramp (a stepped
gain clicks). Generative patterns beat loops: a shuffled-bag pattern has no loop point and so no
seam to mix. The one shipped sound is the Launch Sequence's Boot Audio Hum
(`static/launch_audio.js`); anything louder, longer, or on more pages is a new operator decision.

## 9. The Claude Design page layout — the `.cd-*` family (ADR-0451 · ADR-0456)
The operator's second design pass (`00_REFERENCE_INTAKE/Mission Ops Redesign v2.dc.html`, the
artboard per chapter) is being adopted **one page per session**, the ADR-0451 way: the artboard is
recovered by EXECUTING the canvas (its runtime needs React/Babel — `npm pack` them, patch
`support.js` to local paths, set `sfops-boot.skipNext` and `sfredux-guided` so neither the boot nor
the teaching card covers the screen, then screenshot `section[data-screen-label="NN …"]` in all
four themes) and the page is re-arranged into that layout with **every id, form byte, panel,
toolbar glyph and figure it carried before** ("don't modify any of the functionality"). Rules:
- **Blocks are not panels.** A design surface that is new to a page is a `.cd-block` (or the
  page-prefixed `.vol-block` that preceded it), never `.panel`: the promotion census pins each
  page's `.panel` count, and a block must not join jarvis's broad `html[data-theme=jarvis] .panel`
  rule. Existing panels keep their `.panel` shell verbatim inside the new grid.
- **One cursor.** The version chips (`.cd-chip[data-idx]`, served by the page, one per version)
  call the SAME step/render the page's stepper already drives; the active chip follows the index
  wherever it was moved from. The primary button is the page's own play control, restyled.
- **Chips carry no `id` and no family word** — the control census recognises families by
  id+className (`zoom|fit|pan|entire|play|prev|next|step|cf-btn`), so a chip named `cd-chip` is
  never mistaken for an undriven stepper, and the chips' effect is proven by a browser driver.
- **Not everything in a mock ships.** A mock figure (`61 %`, `8 of 12`) is never ported; a mock
  control with no engine data behind it (a WK grain over monthly profiles) is not built; a mock
  glyph the page's contract forbids (▦ DATA on /cei) stays absent. Each omission is named in the
  page's ADR.
- **Prose beats reuse the page's own words** (`chrome._EXPLAINERS`) rather than adding new prose
  to the loaded-terms audit surface; a "How to read this" block is that explainer in the open.
- Verify in all four themes by render (`render-verify`), and diff the DOM census (panels · forms ·
  chart bars · zero page errors · nothing wider than the viewport) against the pristine page.
