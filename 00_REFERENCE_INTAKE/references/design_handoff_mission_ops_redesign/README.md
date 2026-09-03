> **UPDATED 2026-07-27 — current pixel truth is `ASTROLABE.dc.html` in this folder** (the v2
> prototype is kept as the previous generation). New since the last bundle: three-scene morphing
> boot lightshow (one 5,200-particle pool: DNA helix → signal wave → clustered soft-core galaxy,
> synthesized boot audio, Female/Male voices only), COMPARE stations (Compare Bay · Path Explorer ·
> Path Drift · Metric Trends · Field Metrics), export preview with standard/UDF field picker and
> honest totals, data-point inspector on every mark, reference lines painted above series,
> per-Gantt timescale zoom to day grain, and a full banned-word scrub (no NASA / Microsoft
> Project / Primavera / Oracle in any UI string). Replication instructions for Claude Code:
> `../handoff/CLAUDE-CODE-HANDOFF.md`.

# Handoff: Schedule Forensics — Mission Ops UI Redesign

## Overview
Full-application UI redesign for the **Schedule Forensics** tool (repo:
`Schedule-Manipulation-Analysis-Tool-Experiment`, FastAPI + Jinja2 pages in
`src/schedule_forensics/web/app.py`, vanilla-JS charts in `web/static/`). The redesign
(current file: **`Mission Ops Redesign v2.dc.html`**):

- Re-frames the whole app as a **three-act story** — **Act I · Situation**, **Act II ·
  Diagnosis**, **Act III · Outlook** — spanning **12 chapters** (01–12) with takeaway
  headlines and "Continue" segues, so an analyst is walked through *where the project
  stands, why it's moving, and where it lands*. Every analytics page in the original
  27-surface app is woven in as a chapter beat; utilities (groups/filters, AI settings,
  metric dictionary) live in a **Setup** nav group off the story spine.
- Adds a **View dropdown** with four complete themes: `console` (dark mission control,
  default), `daylight` (clean light), `apollo` (retro CRT), `jarvis` (refined HUD) — plus
  the existing dark/light toggle behavior.
- Standardizes a **chart contract** on *every* visual: labeled X/Y axes with tick values,
  a legend, hover callouts carrying the underlying datum, and a provenance chip
  (`SOURCE: KESTREL3_vN.xer · DD YYYY-MM-DD`) so it is always unambiguous which schedule
  file/version a number came from. Multi-version charts label each series/point by
  version; single-version charts carry a file picker. Plus takeaway titles, dotted
  reading grid, labeled data-date line, and per-chart "how to read this".
- Adds **time-granularity controls** where the data supports them (bow wave MO/QTR/YR;
  Command-Deck census & bow WK/MO/QTR; resources DAY/WEEK/MONTH).
- Rebuilds the **SRA (Schedule Risk Analysis)** page to full input+output parity with the
  engine: file picker; best/most-likely/worst duration uncertainty; unified risk register
  with days↔% auto-derive + lock flags; SSI risk factors; an **editable SSI grid** with
  MS-Project **column-paste** (paste a Factor column → fills every task → auto-calcs
  Best/Worst-case durations from the factor table → every cell still hand-editable);
  per-activity 3-point overrides; and the outputs — confidence S-curve (P10/50/80/90 +
  deterministic marker), duration-sensitivity + discrete-risk-driver tornadoes with
  tables, SSI focus results, 5×5 risk/opportunity assessment matrices, and OAT
  deterministic sensitivity. Every panel and grid is **Excel-exportable**.
- Preserves **all existing functionality**: Excel/CSV export, per-visual enlarge/shrink,
  data-table toggles, Gantt column picker/zoom/filters, Task Information dialog (7 tabs),
  Timescale tier dialog, play/step animations, print, UI text scale, the local cited
  "Ask the analyst" drawer, CUI marking bars + compliance drawer, local-only posture.
- Drops the "NASA" wordmark entirely; keeps the government command-banner identity
  (blue header gradient, red keel line, wireframe-globe insignia as the AI status light).

**Calculations, routes, importers, and the analysis engine are out of scope — do not
touch `engine/`, `importers/`, `ai/`. This is a presentation-layer change only.**

## Recent additions (post-baseline)
- **Global analysis target** — a header-level Target selector (default UID 1190 Launch Readiness Review; options include Launch Campaign, Pre-Ship Review, TVAC-complete, Project finish) drives every calc/analysis: the driving-path endpoint, SRA SSI focus (input select + grid Focus radios, two-way), forecast endpoint and briefing verdict all measure to it; persisted to `sf-target`; each affected panel shows a "measured to …" chip.
- **Industry-standard SRA methods** (all presentation on existing engine data, no calc change): Risk Driver Method marginal-impact tornado (delete-and-rerun P80 leverage), Latin Hypercube vs Monte Carlo sampling + stop-at-convergence, cruciality lens on the sensitivity tornado, pre/post-mitigation confidence-curve overlay ("N days earlier at P80").
- **Standard schedule analytics**: critical-path drag (Devaux) on the driving path, merge-bias/hotspot panel, per-activity float-erosion trend (Ch 05), schedule compression index (Ch 07 KPI strip), probabilistic Gantt P80 risk-tail whiskers (Ch 01).

## About the Design Files
The files in this bundle are **design references created in HTML** — an interactive
prototype showing intended look and behavior, not production code to copy directly.
The task is to **recreate this design inside the existing environment**: server-rendered
Jinja2 page shells in `app.py`, theme tokens in CSS custom properties, dependency-free
vanilla JS in `web/static/` (air-gap rule: no CDN, no frameworks, no remote fonts —
`Mission Ops Redesign.dc.html` uses Google-hosted fonts for preview convenience only;
production must vendor the font files locally or fall back to system stacks).

Open `Mission Ops Redesign.dc.html` in a browser to interact with every screen, theme,
and control. It is the pixel truth when this document is ambiguous.

## Fidelity
**High-fidelity.** Colors, typography, spacing, chart treatments, copy voice, and
interaction behaviors are final design intent. Recreate pixel-perfectly using the
codebase's existing patterns (CSS variables on `html[data-theme]`, `.panel` classes,
per-page static JS modules). Mock data in the prototype (KESTREL-3 campaign) maps to
whatever schedule is actually loaded — bind the same visual to the real numbers.

## Integration strategy (recommended order)
1. **Tokens** — ship `sf-themes.css` + theme-select control (snippet below). Zero
   template changes; the whole app re-themes because it is already variable-driven.
2. **Global chrome** — header retitle (drop "NASA" wordmark), nav regrouped into the
   story chapters, Continue footers, story-progress indicator.
3. **Page shells, one per session** — restyle each page to its chapter spec below;
   wire the panel toolbar contract to the existing export endpoints and chartframe.js.
4. **New features** — follow `DESIGN-GUIDE.md` (copy to `docs/DESIGN-SYSTEM.md`; add a
   compliance line + its Definition-of-Done checklist to the build prompt).

## Page mapping (prototype chapter → existing app surface)
Story spine is three acts / twelve chapters. "Beats" are secondary panels folded into a
chapter (the old standalone pages they came from are named so you know what to restyle).

| Prototype screen | Where it sits | Existing route / assets to restyle |
|---|---|---|
| Import (+ role strip) | 00 · Load | `/` — `home.js`, `dashboard.js`; role strip per ADR-0255 |
| Program Portfolio | Portfolio | `/portfolio` — project rollup (ADR-0225/0260) |
| Portfolio at Scale | Library | `/portfolio` at 100+ projects — virtualized ledger (ADR-0226/0261) |
| Mission Control | Overview | `/mission` — `mission.js` tile grid + play-all master |
| Where we stand | I · 01 | `/analysis/<key>` — `gantt.js`, `histogram.js`, DCMA, findings; **ID-card beat** |
| Can we trust the plan? | I · 02 | `/ribbon` — `ribbon_drill.js` quality board + drill (board also carries the `/trend` 14×6 view) |
| Forensics · Schedule Integrity | off-spine (Forensics) | `/integrity` — any-pair manipulation detectors, masking quotient, field-level evidence ledger |
| What drives the date | II · 03 | `/path`, `/driving-path` — `path.js`, `driving_path.js`, `driving_tiers.js` |
| How stable is the path | II · 04 | `/evolution`, `/volatility` — `path_evolution.js` |
| How it moved | II · 05 | `/trend` — `drift.js`, `curves.js`; **margin-burndown beat** |
| Work piling up | II · 06 | `/cei` — `cei.js` (grain chips added) |
| How we execute | II · 07 | `/performance` + `/evm` — `performance.js` |
| Who is overloaded | II · 08 | `/resources` — `resources.js` |
| Where it lands | III · 09 | `/forecast`, `/scurve`, `/curves` — `scurve.js` |
| What changed | III · 10 | `/compare` — diff + manipulation signals |
| What could go wrong | III · 11 | `/sra` — `sra*.js` + the **JCL panel** (ADR-0269) |
| The briefing | III · 12 | `/brief`, `/briefing` — `ai/briefing.py` |
| **Metric Workbench** | Library | **`/workbench`** — `workbench.js`, `engine/metric_catalog.py` (ADR-0204) |
| Metric Lab | Library | `/workbench` single-metric focus view — same route, second tab |
| Segment Forecast · WBS Rollup · Schedule ID Card · Beyond the Schedule | Library | prototype-only additions; build on existing engine payloads |
| **Margin Dashboard** | Control | **`/margin`** — `margin_dashboard.js` (ADR-0222/0230/0253/0254) |
| **Standards & Indices** | Control | **`/standards`** — `help.py` MetricDocs + `engine/metrics/sem.py` (ADR-0237/0238) |
| **Assessment Scorecards** | Control | **`/scorecards`** — `scorecards.js` (ADR-0213) |
| Groups & Filters · AI Settings · Metric Dictionary | Setup | `/groups` · `/settings` · `/help` |

> The four **bold** rows are pages that exist in the repo but were not in the first design
> pass. They are specified in "New screens (post-sync)" below and are now in the prototype.

## Global chrome (every page)
Top→bottom: CUI bar → compliance drawer → header → nav → main → CUI bar.

- **CUI bars**: full-width, `#502B85` bg, white, centered, mono 700 10px, letter-spacing
  .22em, uppercase, padding 5px 10px. Text: `CUI — CONTROLLED UNCLASSIFIED INFORMATION ·
  LOCAL PROCESSING ONLY`. Bottom bar adds `border-top:1px solid rgba(255,255,255,.14)`.
  Bars must survive print and appear in exports.
- **Compliance drawer**: `<details>` beneath top bar; summary centered, muted, 10px.
- **Header**: `background:var(--header-bg)` (console: `linear-gradient(95deg,#0B3D91,
  #0A2D6E 55%,#071F4D)`), `border-bottom:3px solid var(--hline)` (console `#FC3D21`).
  Contents, left→right (flex, gap 16px, padding 10px 20px):
  1. Insignia 42px (SVG in prototype: outer circle r21 + inner r8.5 + 3 star dots +
     red delta `M24 12 L29 30 L24 26 L19 30 Z` + orbit ellipse group rotating 26s linear,
     `transform-origin:24px 24px`). Keep as the AI status light (`.ai-thinking` glow).
  2. Title block: `SCHEDULE FORENSICS` — display font 700 17px, uppercase, ls .07em,
     header-ink; sub `MANIPULATION ANALYSIS CONSOLE · FLIGHT PROJECTS` mono 500 9.5px ls .14em.
  3. Schedule chip: bordered pill (1px header-ink at 30%, radius var(--rs)) — schedule
     name mono 11px + `N VERSIONS · CURRENT vX · DD YYYY-MM-DD` mono 9px.
  4. Right cluster: LOCAL pill (`● LOCAL · 127.0.0.1`, pulsing ok dot, mono 9px, 20px
     radius) · `Text` scale select (90/100/110/125%) · `View` theme select · ☀/☾ ·
     Quit ghost button. Controls: `rgba(0,0,0,.22)` bg, header-ink text, mono 10px.
- **Nav** — dark themes: left rail 212px, `var(--nav)` bg, right hairline; groups
  `LOAD / OVERVIEW / THE STORY / THE EVIDENCE` (mono 700 9px ls .18em muted); items =
  chapter number (mono 9px accent when active) + label (11px 600); active: `var(--pn2)`
  bg + `inset 2px 0 0 var(--ac)`. Rail foot: "STORY SO FAR" + 7 progress dashes
  (16×4px, radius 2 — accent = current, 45% accent = visited, line = ahead) + current
  chapter takeaway (10px muted). **Daylight**: same items as a horizontal top bar.
- **Continue footer** (every chapter): right-aligned muted segue sentence + primary
  button `Chapter NN → <name>`. Clicking scrolls the new page to top.

## Screens (layout · components · exact copy)
Numbers below are the compact-density defaults at 100% scale. All panels:
`background:var(--pn); border:1px solid var(--ln); border-radius:var(--r);
box-shadow:var(--glow); padding:12–14px 14–16px`. Panel `h2`: display 700 12px,
uppercase, ls .06em + one-line muted description under it. Chart canvases:
`var(--cnv)` bg, 1px line border, radius var(--rs), dotted grid
`radial-gradient(var(--dot) 1.2px, transparent 1.3px)` / 22px pitch.

### 00 · Import — "Load the mission."
Two columns `1.1fr .9fr`, gap 14px. Left: dropzone (2px dashed line, radius var(--r),
30px padding, centered): insignia glyph 40px, "Drop schedule files" display 700 14px,
sub "up to 20 at once — each becomes a version on the timeline", format chips
(`.mpp .mpt .xer .xml .mspdi .json` — mono 9.5px, bordered), buttons `Choose files…`
(primary) + `Load example` (outline accent). Below: data-sovereignty banner (ok-tinted
border/bg): "DATA SOVEREIGNTY — imports parse locally · no network egress · AI on
loopback only · closing the last window stops the server". Right: "Loaded versions"
panel — one row per file: version id (mono 700 10px), filename (mono 11px, ellipsis),
`DD … · CPM finish …` (mono 9.5px muted), slip chip (`BASE/+6d/+11d…` — muted/warn/bad
at ≥11d), `Open` ghost button; current version row tinted accent 7%.

### Overview · Mission Control — "…49 days behind — and the trend is accelerating."
Headline row + `▶ Play the story` (primary; 1.5s beat stepping every animated tile in
lockstep — reuse mission.js pattern) and `Step ▸` (ghost). KPI strip: 4 stat cards
(2px top edge in status color): CPM finish / Percent complete / CEI / Verdict
(`BEHIND` in red, display 700 20px). Tile wall: 3-col grid (gap 10px), 6 tiles —
Finish trend (slope) · Bow wave (animated columns) · Progress s-curve · Execution
index · Forecast window (date ruler) · Schedule quality (DCMA chip board). Each tile:
number+title (display 700 11px uppercase), toolbar `▦ DATA · ⤓ EXCEL · ⛶ ENLARGE ·
Open NN →`, chart 150px (320px enlarged, tile spans full row), one-line reading
(10px muted).

### 01 · Where we stand (Analysis report)
KPI strip ×6 (Activities · Earned 46% "plan at DD: 61%" · Critical · CPM finish ·
vs baseline `+49d` · Data date). Two half-width panels: **Activity status mix**
(single stacked bar 14px, radius 7, segments ok/warn/accent = Complete/In
progress/Planned + legend counts) and **Float remaining** (stacked bar bad/warn/accent
= 0d / 1–4d / 5–9d + "14 INCOMPLETE ACTIVITIES"). **Integration & test timeline**
(the Gantt, full width): controls right-aligned — legend (IN WORK/CRITICAL/COMPLETE/
DATA DATE) · `COLUMNS` chip set (UID TF START FINISH % DUR — toggle chips, accent
when on) · zoom select (`FULL RANGE / 2026 ONLY / EXECUTION WINDOW`) · `Hide completed`
· `Critical only` · `▦ DATA` · `⤓ EXCEL` · `⛶ ENLARGE`. Grid template:
`minmax(150px,210px) + 34–58px per active column + minmax(240px,1fr)` timeline lane.
Rows 22px (30px enlarged); bars 10px (13px), radius 3 — track = series color at 30%,
progress fill solid; milestones = rotated squares; month gridlines from repeating
1px lines; DD = 1.5px red line + `DD 04-06` flag in the header lane. Clamp bars to the
zoom domain. **Findings** panel (1.15fr) — severity rows (52px sev column HIGH/MED/LOW
colored, 3px left border) + citation line `⌖ file · UID · task` (mono 9px). **DCMA-14**
panel (.85fr) — 14 chips (mono 8.5px, pill, pass/fail/na tinted), pass/fail/na counts,
two failing checks explained.

### 02 · What drives the date (Path Analysis)
Left panel (1fr): Target select (`Launch Readiness Review · UID 1190` / `Pre-Ship
Review · UID 1160`) + band legend (`DRIVING · TF 0` red, `≤ 5 D` warn, `≤ 10 D`
accent) + `⤓ EXCEL · ⛶ ENLARGE`. Cascade rows (grid `230px 1fr`): tier badge
(P/S/T bordered 14px), name, UID, `TF Nd` colored; lane 24px with bar in tier color;
**dashed elbow connectors** (left+bottom border, tier color at 65%) linking each
driving bar's finish to the next start; DD line; sections separated by band headers
(`NEAR-CRITICAL · WITHIN 5 DAYS`, `TERTIARY · WITHIN 10 DAYS`). Right column (300px):
**Why this chain** key-value facts (Path to target · Total float 0 days (red) ·
Biggest drag · Single-thread risk · Hand-offs with zero gap) and **Where the days
went** drag bars (FSW +18d 100% · TVAC +9d 50% · Avionics +5d 28%, red) + counterfactual
note: "fix FSW Build 3 alone and the finish improves only 12 d — the TVAC queue
becomes the new driver."

### 03 · How it moved (Trend)
Left (1.2fr): **Computed finish, by version** — slope chart 250px (430 enlarged):
y = finish date (ticks SEP 1…DEC 1, gridlines), x = versions v0–v5 with DD sub-labels;
red 2px line + 8px points; per-point delta labels (`BASE, +6d, +11d…` — warn <11d,
bad ≥11d); dashed muted baseline at 09-14. Toolbar `▦/⤓/⛶` + `+49 CAL DAYS TOTAL`
badge. Right (.8fr): **Net finish impact, per update** — horizontal cumulative
waterfall: row per pair `v0→v1…`, bar positioned at running offset, width ∝ days,
color = worst signal in that update (ok=clean · warn=signals · bad=high-severity);
axis `0 → +49 cal days`; legend CLEAN SLIP / SIGNALS / HIGH-SEVERITY. Full-width
**Inside update vX → vY**: range scrubber (1–5, accent), signals list (severity-
bordered rows, `✓ No signals — honest progress raises no flags` ok-chip when clean)
and "What it means" paragraph + `⌖ diff vX→vY · change-effects engine` citation.

### 04 · Work piling up (Bow Wave / CEI)
Main panel: `▶ Play the wave` / `Step ▸` / version chips v0–v5 (active = accent fill)
+ frame label `V5 · DD 2026-04-06` + `▦/⤓/⛶`. Chart 240px (410): 14 month columns
(NOV 25 → DEC 26), count labels above bars (red when ≥3), colors: ≤DD muted 55% ·
future accent · pile-up warn · ≥3/mo bad; 2px red DD line + `DATA DATE` flag —
all with 450ms ease transitions; caption `This frame: <version note>`. Below `1.1fr
.9fr`: **Current Execution Index** — line chart (warn), points labeled 0.92→0.66,
dashed ok reference at 1.00 (`1.00 = EXECUTING TO PLAN`), x = v1…v5 + table
UPDATE/PROMISED/DELIVERED/CEI (CEI colored ok ≥.85 / warn ≥.75 / bad below) +
`⤓ EXCEL`; **How to read this** — The wave / The index / Why it matters.

### 05 · Where it lands (Forecast)
**Where the finish lands** ruler panel (152px, 280 enlarged, `⛶`): month ticks
SEP→JAN 27, center axis line, P10–P90 band (warn 14% fill, warn 40% border,
`FORECAST WINDOW P10–P90`), four 2.5px markers with staggered labels: BASELINE 09-14
(muted) · CPM 11-02 (accent) · RATE 11-20 (warn) · EARNED SCHED 12-08 (bad).
Method cards ×3 (2px top edge in method color): kicker `Method A/B/C`, name, date
(display 700 19px, colored), `INPUTS · …` (mono 9px), note. Never fabricate a missing
input — show "—". Below `1.1fr .9fr`: **Forecast drift, by version** table
(VERSION/CPM/RATE/EARNED SCHED/SPREAD; spread warn→bad as it widens; current row
accent-tinted; `⤓ EXCEL`) and **Which to believe** (CPM is the floor / Rate is the
pattern / Earned schedule is the discipline / "Plan to the window, not a date").

### 06 · What changed (Compare)
Two panels: **What moved** — ledger rows `metric · v4 → v5 · delta` (delta colored;
`Reported finish variance −4 d ⚑` flagged red) + NFI banner: red-tinted, `+7` display
700 15px, "…after unwinding the baseline edits, true drift this update is **18 days**."
**Manipulation scan** — six category rows (count mono 700 13px, name, note, severity
chip): Deleted tasks 0 CLEAN · Deleted relationships 1 MED · Durations shortened 3
MED · Baseline date edits 9 HIGH · Actual-date edits 2 MED · New hard constraints 1
MED; each with `⤓ EXCEL`. Full-width **The nine baseline edits** evidence table
(UID/TASK/FIELD/v4/v5/SHIFT — shift red 700; `⤓ EXCEL`).

### 07 · The briefing (Executive Briefing)
Header + `⤓ Word (.doc)` (outline) + `⎙ Print / PDF` (primary) + `AI · LOCAL · CITED`
pill. **Verdict card**: 4px red left border — kicker `VERDICT · <schedule> · DD …`,
`BEHIND · DETERIORATING · PARTIALLY MASKED` (display 800 24px red), right-aligned
`FORECAST WINDOW 2026-11-02 → 2026-12-08` (warn). Left column: three narrative panels
(Where it stands / Why / What changes the outcome — accent h2, 11.5px/1.7 body,
citation chips `⌖ v5 · UID 1080`). Right: **Recommended actions** (when-chip NOW=red /
30 D=warn + action + why) and **Ask the analyst** (canned cited exchange + input +
`Ask`). Foot: `GENERATED LOCALLY · CITATIONS RESOLVE TO FILE + UNIQUEID · NOTHING LEFT
THIS MACHINE`. Print hides nav/controls, keeps CUI bars; exports embed the CUI marking.

## New screens (post-sync) — pages that already exist in the repo

These four routes shipped in the repo after the first design pass. The prototype now
specifies each; recreate them from the prototype the same way as any chapter. **No engine
change is needed for any of them** — every figure below is already computed.

### Control · Margin Dashboard (`/margin`)
Order down the page: (1) a cited **MARGIN / CONTINGENCY / FLOAT** glossary strip — margin is
a planned buffer *activity* (SMH §5.5.11), contingency is the calendar's non-working time to
the target, float is the CPM quantity the handbook manages margin *over*; (2) a control row —
status-date chips, the operator's **Gold-Rule rate** (wd/yr, default 30), a **Fig 5-30 band**
toggle, Excel; (3) an 8-card KPI strip carrying **both** effective margin and Σ margin-activity
durations (they differ when margin sits on a path with float — say so), contingency,
requirement, % available (R), % effective (T), consumed %, and the trigger; (4) the **burn-down**
— one column per status date, effective margin stacked under hatched contingency, a dashed
requirement line per column, a planned (F) notch, the Fig 5-30 band as a hatched region, the bar
turning `--bd` red below the requirement, a `⌃` caret at 50% consumed and a `◇` when below the
band; (5) the **erosion trend** — margin points, least-squares fit, projected zero-margin marker,
**R² disclosed** (and no projection at all when margin is flat or growing); (6) the **confirmed
margin overlay** — name matches pre-ticked, near-misses (reserve / contingency / integrated
return) unticked, each with duration · total float · on/off the driving path, and copy stating
that clearing every tick restores the name-based default while an explicitly empty set is a
deliberate "no margin"; (7) the **SRA sufficiency read** — the percentile the target date covers,
with operator-editable Watch/Corrective percentiles prefilled 70/50 **as the handbook's examples,
not a standard**, and the disclosed caveat that the run carries margin in-network at plan.
Full per-version workbook table (D/E/G/I/Σ/J/O/Q/R/T/F/consumed/flags) behind `▦ DATA`.

### Control · Standards & Execution Indices (`/standards`)
Three family tabs — DCMA-14 (16 rows), NASA/Acumen-Fuse indices (~14), Industry-Standards SEM
(10). One row per metric: **ref · metric · value · status pill · threshold · verbatim formula ·
source**, all five doc fields read from the single metric-doc dictionary (`help.py`), never
retyped in the view. Values compute on the **latest** loaded file (stated in the provenance
chip; the prior file feeds the period metrics). A metric the file cannot score prints `—` with
an N/A status. Rows with no published bar are INFO, not PASS. Excel export covers all three
families at once.

### Control · Assessment Scorecards (`/scorecards`)
Three side-by-side scorecards — NASA STAT, GAO ten best practices, SRA-readiness gate — each
with a headline score, a progress bar, and one row per check: status pill, value, **provenance
string**, and a `⊞ n` button opening the offending activities in the Data Explorer. Lines with
no numeric pass bar render INFO and are **excluded from the score**, with the exclusion count
stated under the bar, so the percentage is honest. Below: the **reserve-sizing card** — an
editable committed finish date and P50/P70/P80/P90 cards showing the work days (and calendar
days) of reserve needed to defend it, read off the existing SRA finish distribution by
nearest-rank — no new simulation.

### Library · Metric Workbench (`/workbench`)
Two columns `262px 1fr`. Left: the **selectable library** — search, a running `n / total`
count, SELECT ALL / CLEAR, and one block per family (DCMA-14 audit · Fuse schedule quality ·
Float extras · Registered follow-ons) with per-family ALL / NONE and a checkbox per metric
showing its unit and threshold. Right: the **matrix** — rows are the ticked measures, columns
are versions **oldest → newest by data date, each read as its own independent schedule**, plus
a threshold column and a Δ v0→v5 column coloured by whether the metric got *worse*. Cell fill
is the metric's own threshold (PASS / FAIL / INFO / `—` for not-applicable); a cell with
offenders shows `⊞ n` and opens the **drill grid** below — filter, click-to-sort headers,
group-by any project field, add/remove columns incl. a custom field, row → Task Information,
Excel. Copy must state that this is the **validated** library — the same gate-locked figures
the rest of the tool reports, not a re-interpretation of raw library formulas — and that an
unscored metric is NA, never a fabricated 0.

### `/` role strip (ADR-0255)
Above the dropzone: "Start here — who are you today?" with five role buttons (Scheduler/Planner,
Program/Project Manager, Forensic Analyst, Auditor (DCMA/IG), Counsel/Testifying Expert) plus
**Show everything** (the default), each carrying a one-line why. Selecting a role reveals its 4
**Start-here cards**. The strip must state the contract in the UI: a role is an entry point,
never a mode — it cannot hide a page, change a default, or change a number — and **an ingest
with errors always lands on the manifest**, because disclosure outranks the role landing.

## Interactions & Behavior
- **Theme dropdown** (`console/daylight/apollo/jarvis`): sets `html[data-theme]`,
  persists (`sf-theme`). ☀/☾ maps daylight ↔ last dark theme. Migrate legacy
  `light` → `daylight`, default → `console`.
- **Text scale** 90/100/110/125% multiplies the 11px base (persist).
- **Toolbar contract** on every data visual: `▦ DATA` (inline table — make the
  existing sr-only accessibility table visible), `⤓ EXCEL` (existing xlsx/csv export
  endpoints; prototype downloads CSV client-side as a stand-in), `⛶ ENLARGE`
  (panel spans full width, chart height ×~1.8; label flips to SHRINK). Ghost buttons:
  mono 600 8.5–9px, muted → ink+accent-border on hover.
- **Gantt options** persist via the persist.js pattern (prototype key `sfredux-gopts`:
  `{gCols,gZoom,hideDone,critOnly,uiScale}`).
- **Animations**: bow wave 1.5s beat (mission wall lockstep via shared timer clicking
  each tile's Next); line-draw ~1.1s ease on play/step; bar/DD transitions 450ms.
  `prefers-reduced-motion`: timers step once instead of looping; CSS animations killed
  globally (existing base.css block).
- **Story nav**: chapter click / Continue → scroll to top; progress dashes + takeaway
  update. Toasts (header, warn color, ~3s) confirm exports.
- **Focus**: visible `--focus` ring on all interactive elements (existing rule).

## State Management
Client-side only (server pages stay stateless): `sf-theme` · UI scale · Gantt options ·
per-panel enlarge/data-open (session state is fine) · deck position N/A. Existing
heartbeat/quit behavior unchanged.

## Design Tokens
`sf-themes.css` in this bundle is the source of truth (all four themes, keyed to the
repo's existing variable names). Prototype-only names map to repo names:

| Prototype | Repo (`sf-themes.css`) | Console value |
|---|---|---|
| `--bg` / `--pn` / `--pn2` | `--bg` / `--panel` / `--hover` | `#070B12` / `#0E1522` / `#131D2F` |
| `--ink` / `--mut` / `--ln` | `--ink` / `--muted` / `--line` | `#E7EEF7` / `#8295AB` / `#203049` |
| `--ac` / `--ok` / `--wa` / `--bd` | `--accent` / `--ok` / `--warn` / `--bad` | `#4AA3FF` / `#3FB950` / `#E0A62E` / `#FF5A52` |
| `--rd` | `--nasa-red` | `#FC3D21` (critical path, DD, alarms only) |
| `--hgrad` / `--hink` / `--hmut` / `--hline` | `--header-bg` / `--header-ink` / `--header-muted` / *(new)* `--header-line` | gradient / `#FFF` / 78% white / `#FC3D21` |
| `--fld` / `--bink` | `--field-bg` / `--btn-ink` | `#0A111D` / `#051323` |
| `--nav` / `--cnv` | *(new)* `--nav-bg` / `--chart-canvas` | `#0A101C` / `#0B1220` |
| `--cgrid` / `--dot` | `--grid-line` / `--grid-dot` | rgba(130,149,171,.16) / rgba(140,162,192,.13) |
| `--r` / `--rs` | *(new)* `--radius` / `--radius-s` | 10px / 7px (apollo: 0) |
| `--f` / `--fd` / `--fm` | *(new)* `--font` / `--font-display` / `--font-mono` | Barlow / Barlow Semi Condensed / IBM Plex Mono |
| `--tt` / `--glow` | *(new)* `--text-case` / `--panel-glow` | none / none (apollo: uppercase; jarvis: cyan glow) |

Daylight/apollo/jarvis values: see `sf-themes.css` and the prototype's `themeVarSets`.
Fixed (theme-independent): CUI purple `#502B85`, UNCLASSIFIED green `#007A33`,
risk-heat bands (existing `.rk-*`), MS-Project Gantt white-canvas tokens (existing
`--gantt-*`, applicable in daylight).

**Type scale** (compact, 100%): base 11px/1.5 · h1 takeaway display 700 22px/1.15 ·
panel h2 display 700 12px uppercase ls .06em · kicker mono 700 10px ls .16em ·
KPI value display 700 18–20px · chart ticks mono 500 8–8.5px · citations mono 500
8.5–9px · buttons 700 11–11.5px · toolbar buttons mono 600 8.5–9px. Floor: 8px.
**Spacing**: panel padding 12–14px; grid gaps 8–14px; section rhythm 10px;
KPI cards 9–11px pad. **Radii**: 10 / 7 / 4(jarvis) / 0(apollo). Density
"comfortable" = base 12px.

## Theme-select snippet (production)
```html
<label class="ui-scale-ctl">View
  <select id="themeSelect">
    <option value="console">CONSOLE — mission control</option>
    <option value="daylight">DAYLIGHT — clean light</option>
    <option value="apollo">APOLLO — retro CRT</option>
    <option value="jarvis">JARVIS — HUD</option>
  </select>
</label>
<script>/* theme-select.js */(function(){
  var sel=document.getElementById('themeSelect');if(!sel)return;
  var cur=localStorage.getItem('sf-theme')||'console';
  if(cur==='light')cur='daylight';
  document.documentElement.setAttribute('data-theme',cur);sel.value=cur;
  sel.addEventListener('change',function(){
    localStorage.setItem('sf-theme',sel.value);
    document.documentElement.setAttribute('data-theme',sel.value);
  });
})();</script>
```

## Assets
- **Insignia SVG** — original art, embedded in the prototype header (circle + orbit +
  delta). Lift verbatim; it replaces the "NASA" wordmark next to the globe canvas.
  No NASA wordmark or meatball/logotype anywhere.
- **Fonts** — Barlow, Barlow Semi Condensed, IBM Plex Mono (OFL-licensed): vendor
  woff2 files into `web/static/fonts/` with `@font-face` (air-gap — no Google links).
  System fallbacks are declared in the stacks.
- No raster images. Charts are DOM/SVG drawn by the existing static JS.

## Files in this bundle
- `Mission Ops Redesign v2.dc.html` + `support.js` — the **current** interactive prototype
  (open in a browser; needs `support.js` beside it). All 12 chapters + Mission Control +
  Import + Setup screens, 4 themes, working toolbars, the full SRA page, and the shared
  Task Information / Timescale dialogs + Ask drawer.
- `sf-themes.css` — drop-in theme tokens for the repo.
- `DESIGN-GUIDE.md` — the ongoing design rulebook (copy to `docs/DESIGN-SYSTEM.md`).
- `integration-notes.md` — short version of the wiring steps.
- `screenshots/` — captures from the earlier 7-chapter cut (historical). **`screenshots-v2/`** —
  current captures from v2 (Console theme): Mission Control + verdict banner, quality board,
  volatility, Command Deck, SRA, bow wave, forecast, briefing, Where-we-stand. The live
  `Mission Ops Redesign v2.dc.html` remains the pixel truth for the other themes.


## Addendum — sync 2026-09-02 (repo main @ v1.0.230, ADR ≤ 0452)

- Route inventory is now **34** HTML routes: `/launch` (boot screen, ADR-0426) and `/onepager` (ADR-0446) added; both have deck screens (boot sequence; Library · One-Pager Timeline).
- The deck adopts the repo's product name **POLARIS²** (ADR-0436). Any remaining "MERLIN" in older bundle text is superseded.
- Deck screens now also carry: Combine Projects (ADR-0431), whole-schedule default + UID retarget + cross-Project picker on the driving path (ADR-0432/0438), Utilization by resource (ADR-0433), multi-folder drop copy (ADR-0437), Field roles WBS / Cost Account / Work Package (ADR-0450), approved-gateway AI settings with persisted key (ADR-0402/0403/0404), pairwise comparison series in Ask (ADR-0424), adaptive timescale tiers (ADR-0441/0447/0452). These are restyles of shipped behaviour — presentation only, no engine change.
- The TVAC constraint in the demo story is an **MSO** (hard under the ribbon's MSO/MFO metric and under DCMA-05); the previous SNET was soft under both definitions (ADR-0429).
