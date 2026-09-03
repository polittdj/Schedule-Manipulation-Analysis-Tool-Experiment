# Project Handoff — Schedule Forensics UI Redesign

**Read this first. It is the complete state, scope, and history so a new chat loses nothing.**

---

## What this project is

A full UI redesign of the **Schedule Forensics** tool — GitHub repo
`polittdj/Schedule-Manipulation-Analysis-Tool-Experiment` (default branch `main`, NOT the
"…-Experiment8" name the user first gave — that 404s; the real repo has no "8"). It is a
FastAPI + Jinja2 app (`src/schedule_forensics/web/app.py`, ~12k lines) with
dependency-free vanilla-JS charts in `web/static/`. It ingests multiple **versions of one
project's schedule** (`.xer`/MS-Project files), each with its own data date, and analyzes
schedule quality, critical-path behavior, forecasts, and manipulation signals. Local-only,
air-gapped, with a loopback AI ("Ask the analyst").

The repo IS readable via the github_* tools (access was granted). `app.py`, several
modules, and static JS were copied into `src/…` in this project for local grep — read
those for engine truth. **Never** re-derive from memory; read the source.

## The user's standing requirements (all honored — keep honoring)

1. **Never change how anything is calculated.** Presentation layer only. Every number is
   read from the engine payload.
2. **Never remove functionality or visuals.** May *combine* visuals when it makes sense
   (nothing dropped, original one click away). All Gantt controls (column picker, zoom,
   filter, format, resize), export, enlarge, data toggles, persist/reset, print, text
   scale, CUI bars stay.
3. **Remove the "NASA" wordmark** everywhere (done). Keep the neutral command-banner look.
4. **4 independent themes** the user can switch between; ≥1 futuristic "mission control".
5. **Story-like experience** — loading project files walks the user logically through
   screens, telling the story of the data's past/present/forecast state.
6. **Keep "Ask the AI"** functionality.
7. **Provide options at each phase**; act as expert graphic/UI designer.
8. **Every visual**: X/Y axes with labels+values, a legend, hover callouts + a show-values
   option, and a crystal-clear source/version chip; user can pick the version where
   applicable; user can change time granularity (day/week/month/qtr/yr).
9. **Max automation / SRA input parity** — all real SRA inputs incl. MS-Project column
   paste + auto-calc; all real inputs of every visual mirrored.
10. **Global target UID** drives all calcs/analysis (driving-path endpoint, SRA focus,
    forecast, briefing).

## Chosen design directions (locked)

- Story architecture **1b** — **Three Acts**: I Situation · II Diagnosis · III Outlook,
  over **12 chapters**, utilities in a **Setup** nav group off-spine.
- CP Volatility **1c** — **Flight Recorder** (10 visuals → 4 composites, one cursor).
- Performance **1f** — **Command Deck** (7 graph families → 5 panels + index strip).
- 4 themes: `console` (default dark mission-control), `daylight` (light), `apollo` (CRT),
  `jarvis` (HUD). Selected via header **View** dropdown; persisted to localStorage.

## Files in THIS project

- **`Mission Ops Redesign v2.dc.html`** — THE deliverable. Current, feature-complete,
  verified loading clean. Single Design Component (template + `class Component` logic).
  Uses `support.js` (the DC runtime — do not edit).
- `Mission Ops Redesign.dc.html` — v1 (7-chapter), kept as historical fallback. Don't edit.
- `Redesign Explorations.dc.html` — the options canvas (story maps 1a/1b, volatility
  1c/1d/1e, performance 1f/1g). Historical.
- `Recreation - Analysis.dc.html`, `Recreation - Dashboard.dc.html` — early recreations of
  the original UI (pre-redesign reference). Historical.
- `src/schedule_forensics/…` — copied repo source for grepping engine truth.
- `design_handoff_mission_ops_redesign/` — the **Claude Code handoff bundle** (see below).
- `handoff/` — older theme-only handoff (superseded by the folder above).

## The dataset in the prototype (mock, consistent across all screens)

KESTREL-3 lunar comms relay I&T campaign. **6 versions v0–v5** (v0 baseline
`KESTREL3_v0_BASELINE.xer` … v5 `KESTREL3_v5.xer`, DD 2026-04-06). Finish slipped +49 d vs
baseline. Critical chain: FSW Build 3 (UID 1080) → FSW Qual (1100) → Vehicle Functional
(1120) → TVAC (1140) → Vibe & Acoustics (1150) → Pre-Ship Review (1160) → … → Launch
Readiness Review (1190). Target UIDs: 1190 LRR (default), 1180 Launch Campaign, 1160
Pre-Ship, 1140 TVAC, 0 = project finish. These UIDs/names must stay consistent if you add
screens.

## What is BUILT in v2 (all verified, no console errors)

**Chrome:** command banner (no NASA), global **Target** selector + **Text** scale +
**View** theme in header, three-act rail nav (left on dark, top on daylight), Continue
footers, CUI bars, "⌖ ASK" drawer (grounded, cited, per-screen context) floating on every
screen.

**Chapters (all designed, all with the chart contract):**
- 00 Import · Mission Control (overview wall)
- 01 Where we stand — Schedule ID card + KPIs + status mix + float bands + I&T Gantt (+P80 whiskers)
- 02 Can we trust the plan — quality board 13×6 (click-drill) + integrity scan per version pair
- 03 What drives the date — tiered driving-path corridor + **critical-path drag (Devaux)** + **merge hotspots**; in-panel + global target
- 04 How stable is the path — Flight Recorder: stability signal, flow, membership matrix (→Task Info), transition ribbons, evolution corridor + what-if ledger; version cursor + play
- 05 How it moved — finish-trend slope + NFI + **margin burndown** + **float-erosion trend**
- 06 Work piling up — bow wave (grain MO/QTR/YR) + CEI
- 07 How we execute — Command Deck: census+burden (WK/MO/QTR), bow+S curves, BEI/HMI/roll-3, duration-ratio, portfolio quads, EVM ledger, SPI(t)/ES WBS combo, **compression index** KPI; Finishes/Starts toggle + file stepper
- 08 Who is overloaded — resources histogram (DAY/WEEK/MONTH) + drill + roster
- 09 Where it lands — forecast window (3 methods) + **progress S-curve & finish walk**; measured-to-target chip
- 10 What changed — change-effects / manipulation signals
- 11 What could go wrong — **the full SRA** (see below)
- 12 The briefing — one-page verdict
- Setup: Groups & Filters · AI Settings · Metric Dictionary

**SRA (Ch 11) — inputs:** file picker; uncertainty best/most-likely/worst % + presets;
iterations (guidance: ~2,500 working / 10,000 final); Triangular/PERT/**Uniform/Normal**;
**Monte-Carlo vs Latin-Hypercube + stop-at-convergence**; **resource-leveling-per-iteration
toggle**; **risk banding** (common ranges by activity type, editable bands);
**BRANCHING tab** — probabilistic (fail % → FIX-IT/RETEST O/M/P, bimodal warning) and
conditional (Plan-B cutoff rule + scenario compare table, exportable);
correlation ρ slider; unified risk register with **days↔% auto-derive + lock flags**; SSI
factors (focus event synced to global target, occurrence mode, editable factor table,
auto-calc); **editable SSI grid with MS-Project column-paste** (paste Factor column → fills
down → auto-calcs BC/WC → every cell still hand-editable; Save/Reload/Excel/show-completed;
row→Task Info); per-activity 3-point overrides.
**SRA — outputs:** confidence S-curve (P10/50/80/90 + deterministic marker); **pre/post-
mitigation overlay** ("23 days earlier at P80"); duration-sensitivity tornado with
**sensitivity↔cruciality lens toggle**; **Risk Driver Method marginal-impact tornado**;
discrete risk-driver tornado; SSI focus results; **5×5 risk + opportunity matrices**; OAT
deterministic sensitivity. All Excel-exportable.

**Shared dialogs:** Task Information (7 tabs) from any row; Timescale (tier stack); Ask drawer.

**Chart contract applied to every visual:** axes+values, legend, hover callouts, `SOURCE:
file · DD` chip (+version pickers/labels, measured-to-target chips), ▦ Data / ⤓ Excel / ⛶
Enlarge, grain chips where time-binned, takeaway headline.

## Build conventions (how v2 is authored — follow these)

- It is ONE Design Component. Template edits via `dc_html_str_replace`; logic edits via
  `dc_js_str_replace` (hot-reloads, preserves state). Read before editing.
- **Inline styles only**, all via CSS custom-property tokens (`var(--ac)`, `var(--ink)`,
  `var(--pn)`, `var(--mut)`, `var(--ln)`, `var(--bd)`=red, `var(--ok)`=green, `var(--wa)`=
  amber, `var(--fm)`=mono font, `var(--fd)`=display, `var(--f)`=body, `var(--rs)`/`var(--r)`
  radii, `var(--cnv)` chart canvas, `var(--dot)` grid dots). Never hard-code a hex that
  should be a token — themes depend on it.
- Screens are `<sc-if value="{{ isXx }}">` blocks; `isXx`/`goXx` handlers + `screen` state
  drive nav. Each builder is `buildXxx()` returning flat renderVals; wire into the big
  return map (`xx: this.buildXxx ? this.buildXxx() : {}`).
- Every chart builder exposes `fr` frame helpers (`this.fr('key')` → tglBig/tglData/
  span/bigLab/dataLab) and a `this.csv(name, headers, rows)` export.
- Charts drawn with divs/SVG + `title=""` hover; NO chart libs.
- `this.grainChips(id, allowed, def)` + `this.regroup(vals, grain)` for granularity.
- Global target: `this.state.targetUid`, `this.targetDefs()`, `this.targetOf()`,
  `this.setTarget(uid)` (syncs driving-path, sraFocus, sraFocusGrid; persists).
- After edits, `ready_for_verification({path})`; use `skip_verifier_agent:true` for small
  changes, full verify for big ones. It loads clean today.
- NOTE: tool output warns `support.js` is older than the current DC runtime — harmless, it
  loads and runs clean. Don't "fix" it by overwriting unless something actually breaks.

## The Claude Code handoff bundle (`design_handoff_mission_ops_redesign/`)

Delivered for the user to drop into the repo so Claude Code rewrites the real app to match
and follows the style forever. Contains:
- **`CLAUDE.md`** — the operating brief: TASK 1 rewrite order (tokens → chrome → one page/
  PR → new panels), non-negotiables, the chart contract, global target, structure, "how to
  add a feature later" recipe, Definition-of-Done checklist. Claude Code auto-loads it.
- `README.md` — screen specs + page-mapping table (chapter → repo route) + tokens + copy.
- `DESIGN-GUIDE.md` — design rulebook (→ repo `docs/DESIGN-SYSTEM.md`).
- `sf-themes.css` — all four themes as drop-in tokens.
- `Mission Ops Redesign v2.dc.html` + `support.js` — current prototype copy.
Keep this bundle in sync with v2 if the prototype changes materially.

## Status / open items

**Later additions (after this file was first written — all built + verified):**
- **Global chrome:** ❓ GUIDE ME on every screen (what/when-why/example/how-to-read, Next-chapter walk, auto-opens first run); ◎ SHOW UIDs visibility overlay (≤20 UIDs + target pins that slide as versions play — bow wave, Ch07 census, float-erosion lines; never affects calcs).
- **Ch 03:** “Path between two points” — pick Start+End UID, watch the driving chain re-form across v0–v5 (+JOINED/−LEFT), Excel/enlarge.
- **Ch 05:** one version cursor animates slope + margin + float erosion; Ch 02 ▶ Play pairs.
- **Ch 01 Gantt:** searchable ⊞ COLUMNS dropdown (standard + custom fields, ＋ADD field), ⤓ EXCEL of the configured grid; Groups & Filters = grouped dropdowns.
- **Reference-doc additions** (from refs/*.txt — concepts_a, advanced_sra/Hulett, int02_advanced/GAO-DCMA): six-step SRA workflow strip + READINESS chips; “In plain language” brief box; P95; risk-critical-vs-CPM ⚠ flags; merge-bias joint-probability copy; CPLI as 14th quality measure + drill; per-measure DCMA threshold tooltips; dictionary entries (te, banding, branching, CPLI, LOE/hammock, scenario lottery); reserve-vs-mitigation rule on margin burndown. 5×5 matrices wrap responsively (verifier overflow fix).

**Metric Lab + universal Data Explorer + Beyond-the-Schedule (latest — built + verified):**
- **Library ▤ Metric Lab** (new nav group "Library"): Acumen-Fuse-style. Left = searchable
  metric library grouped into 4 families — **Schedule Quality** (FROM FILE / metadata),
  **Progress & Performance** (FROM FILE), **Risk & Realism** (schedule + your risk inputs),
  **Project Vitals · beyond the schedule** (metadata + you-provide + external). Each metric
  carries what/why/how + a source tag (FROM FILE / YOU PROVIDE / EXTERNAL). Right = a
  **ribbon**: every version v0–v5 as an independent schedule in data-date order, one card
  each, coloured against the metric's threshold, with Δ-vs-prior + a bar; ⤓ Excel of the
  ribbon; ▤ family matrix toggle. Click a version card → its **underlying tasks/records**
  drop into the drill grid.
- **Universal Data Explorer** — one grid engine (`gridBuild(ns, dataset, colDefs, exName)`
  + `gridSort/gridToggleCol/gridAddCol`, `taskColDefs()`, `augTask()`, `taskMetaMap()`).
  Powers the Metric Lab drill inline AND a global **⊞ EXPLORE** dialog (`openExplorer` /
  `buildExplorer`, state ns `dx`). Features: text **filter**, **add columns** (full standard
  + custom catalog, incl. ＋add-custom-field), **sort** (click header), **group-by** any
  groupable field, **export to Excel**, drill row → Task Information. ⊞ EXPLORE wired onto
  Ch01 Gantt, Ch03 drivers, Ch06 bow wave, Ch07 exec, Ch08 resources (dataset per visual).
  Metric Lab drill uses ns `ml`.
- **Library ◇ Beyond the Schedule** (new screen `bs`): the you-provide inputs the file can't
  supply — **Staffing coverage** (available vs required heads), **Funding alignment**
  (budget-to-go vs work-to-go), **Technical Performance Measures** (margin + in-tolerance
  toggle). Editable controlled inputs → `state.bsStaff/bsFund/bsTpm`; the three USER
  Project-Vitals metrics recompute their **v5 (current) ribbon value live** from these
  (earlier versions stay as historical trend). Crystal-clear what/why/tells-you per panel,
  live coloured readouts, ⤓ export inputs, "View on the ribbon →" per section.
- **Instructions + tooltips:** ⓘ how-to banners on Metric Lab (3-step) and Beyond
  (you-know-the-schedule-doesn't); what/why/how cards per metric; title tooltips on every
  ribbon card, grid control, and input field. Guide (GUIDE ME) entries for `ml` + `bs`; Ask
  drawer context for `ml`; 8 new dictionary entries (Metric Lab, Data Explorer, update
  discipline, baseline volatility, staffing coverage, funding alignment, TPM, requirements
  volatility). NO calc changes — vitals defaults mirror existing screens; ribbon numbers for
  quality/perf/risk reuse the exact per-version values already on other chapters.

**Grounded metric library + Segment Forecast + 10-filter One Filter (latest — built + verified):**
- **Metric Lab re-grounded on the real repo library** (`docs/METRIC-DICTIONARY.md`, the NASA
  Acumen "Bible"). The `.aft` file the user named is NOT in the pushed `main` branch — the
  dictionary (33 KB, ~80 metrics) is the authoritative source and was used. Library is now
  organised by the four NASA Handbook **reliability dimensions** as tabbed "pages"
  (Comprehensiveness · Construction · Realism · Affordability) + a **Project Vitals** page.
  ~40 metrics, each with real name, **formula** chip, definition, provenance citation, source
  tag, a 6-version ribbon, a sparkline trend, and a task/record drill. `metricCatalog()`,
  `metricFamilies()`, `srcTag()` rewritten (run_script splice); `buildMetricLab()` adds
  `dimTabs`/`spark`/`metricFormula`/`metricProv`; state `mlDim`.
- **Library ∑ Segment Forecast** (`buildSegForecast`, screen `wf`): pick ANY field
  (resource/IPT/subsystem/CA/WBS/critical/phase/calendar/…) → per-segment BEI, CEI, SPI(t),
  %complete, remaining-work weight, and a segment forecast finish. **Weighted forecast:**
  PF = SPI(t) clamped 0.30–1.50; segment forecast = data date + remaining span ÷ PF; segments
  weighted by remaining working days; **weighted all-work forecast** = DD + project remaining ÷
  work-weighted composite PF; **project driving forecast** = latest (worst) segment. **No-actuals
  fallback (industry practice, per requirement):** a segment with no completed work inherits the
  project composite PF capped at 1.0 (conservative EVM convention), flagged ◊ INH — never
  dropped. One-timeline viz (dot size = weight, colour = PF), full Explorer drill + Excel.
- **The "One Filter" upgraded to up to TEN rules + group-by** (`buildGroups`): each rule =
  field · operator · value over any schedule field (`filterFieldCatalog`), AND-combined;
  `activeTasks()` applies them; live match count; group-by field; "open filtered/grouped
  results" → Data Explorer; "forecast this scope" → Segment Forecast. State `gFilters`
  (≤10), `gGroupField`, `segField`. Helpers: `passesFilter`, `opsFor`, `setFilterRow`/
  `addFilterRow`/`removeFilterRow`, `activeFilterCount`. Guide/nav entries for `wf`.

**Executive briefing redesign + manipulation forensics + tiered driving path + any-UID target (latest — built + verified):**
- **Briefing (Ch 12) drastically redesigned** (`buildBrief`): masthead (project · N files · DD range · copy says it scales to 31), 4 verdict cards (status/trend/execution/integrity, each drills), a finish-forecast walk across all versions, 3 cited situation paras each with a ⊞ Verify button (opens the exact activities in the Explorer), an **Outliers** panel (statistically computed — duration σ, largest single-step NFI, steepest float erosion, driving segment), the **manipulation forensic panel**, and a recovery plan with impact/owner + Excel export.
- **Schedule-manipulation forensics** (`manipulationTests`): 16 research-backed measures (baseline/actual-date edits, driving-logic deletion, relationship-type conversion, lag insertion, unsupported duration compression, calendar switching, hard-constraint injection, constraint-driven finish, float suppression, out-of-sequence actuals, %-complete stall, bow-wave, critical-path instability, irregular cadence, delete/re-add). Each: category, severity, per-version firing strip, offending UIDs, what/how/plain/refs (DCMA-14, GAO SAG, PASEG, Acumen Fuse, Hulett). Aggregated to a **Schedule Integrity Index** (0–100, penalty Σ sev×fires) + tier. Excel export. State `brTest`.
- **Any UID as global target**: `targetInfo(uid)` resolves curated milestones OR any activity OR project finish; header `targetGroups()` lists Key milestones + every activity UID as optgroups. `targetOf`/`setTarget` generalised.
- **Ch 03 driving path MS-Project-style + interactive** (`buildDrivers`; state `drvVer`/`drvSec`/`drvTer`/`drvPlay`, `toggleDrvPlay`): user-set **secondary/tertiary total-float thresholds** (sliders) reclassify Driving (TF≤0)/Secondary(≤sec)/Tertiary(≤ter); **version cursor + Play** replays v0–v5; each row has a 6-cell **tier strip**; a per-version-float `model` drives the **On/off the driving path** panel naming what **JOINED / LEFT / RETURNED** and why; month-header Gantt matching Ch 01, tier bars, connectors, Explore/Excel.

**POLARIS² era (2026-08-14 — latest): route-complete verification + Forensics/Compare promotion.**
Deliverable renamed **POLARIS²**; `/integrity` is now a dedicated **Forensics · Schedule Integrity**
screen (7 detectors, masking quotient, any-pair evidence ledger); **Ch 10 promoted** to a full
any-pair compare page on the same pair engine (verdict, NFI attribution bar, what-moved census,
biggest movers, per-class scan, field-level ledger); integrity reported-slip math fixed (reads
per-update `b.d`). **All 32 repo HTML routes verified mapped** (ADR sweep 0285→0402 at HEAD
`71a56d32`: no new routes); every screen wears a **⇄ ROUTE chip** in the header naming the repo
page it restyles (`ROUTEMAP` in the logic class). Route maps refreshed in `github.md`,
`docs/coverage-verification.md`, bundle `CLAUDE.md` §8 (added `/card`, `/wbs`) + `README.md`;
bundle prototype copy re-synced.

**Repo re-audit + four new screens (2026-07-24 — latest):** the repo moved a long way
past the first design pass (now v1.0.91, highest ADR 0282, tree `df68be7b`). Audited it and
added the pages that did not exist when this project started — each grounded in its ADR, all
presentation-only:
- **Control · Margin Dashboard** (`mg` → `/margin`, ADR-0222/0230/0253/0254/0266) —
  cited MARGIN/CONTINGENCY/FLOAT glossary; operator Gold-Rule rate; Fig 5-30 band toggle;
  8 KPIs incl. **dual numbers** (effective margin AND Σ margin-activity durations);
  burn-down (stacked margin+contingency, per-column requirement line, planned notch, red
  bar = trigger, `⌃` at 50% consumed, `◇` below band); erosion trend with a **real
  least-squares fit** (R² disclosed, no projection when flat/growing); the confirmed
  margin-activity overlay (primary pre-ticked, near-misses unticked, clearing all restores
  the name default); the SRA sufficiency read with editable Watch/Corrective percentiles
  labelled as handbook *examples*; full workbook table (D/E/G/I/Σ/J/O/Q/R/T/F) + Excel.
- **Control · Standards & Execution Indices** (`sd` → `/standards`, ADR-0237/0238) — three
  family tabs (DCMA-14 16 rows · Fuse indices 14 · SEM 10); row = ref · value · status ·
  threshold · verbatim formula · source; latest-file provenance; `—`/N-A for unscorable;
  INFO for no-published-bar; Excel across all families.
- **Control · Assessment Scorecards** (`sk` → `/scorecards`, ADR-0213) — NASA STAT / GAO-10 /
  SRA-readiness ribbons, each line carrying its **provenance string** and a `⊞ n` drill into
  the Explorer; INFO lines excluded from the score with the count stated; reserve-sizing card
  (editable committed date → P50/70/80/90 reserve in wd + cal d, nearest-rank off the
  existing SRA CDF).
- **Library · Metric Workbench** (`wb` → `/workbench`, ADR-0204/0219/0223) — the real
  ADR-0204 shape my Metric Lab did not cover: **multi-select checkbox library** (4 families,
  per-family ALL/NONE, search, n/total) → **metrics × versions matrix** oldest→newest with
  threshold colouring, Δ v0→v5 coloured by *worse*, `—` for NA, and a click-to-drill grid
  (filter · sort · group-by · add columns · Task Info · Excel) reusing `gridBuild('wb', …)`.
- **Role strip on Import** (ADR-0255) — five roles + Show everything, Start-here cards, and
  the stated contract (never a mode; errors outrank the role landing). State `role`.
- Metric Lab is retained as the single-metric focus view of the same route (documented).

Nav gained a **Control** group (Margin · Standards · Scorecards); Workbench heads **Library**.
Guide + plain-language + Ask entries added for all four screens.

**Handoff bundle rewritten for Claude Code** — `CLAUDE.md` §8 is now a full route→screen
inventory (26 routes, with the repo assets and ADR per row) plus §8.1 "cross-cutting repo
behaviours the redesign must preserve" (play-all coordinator + the `isTrusted` guard,
interactive legend toggles, Acumen parity mode / DCMA milestone scope / CPLI stored float,
active-project scoping, hash dedup + same-date review, ignore toggles, calendar disclosures,
roles, the scale/cache tiers). README's page-mapping table replaced and a "New screens
(post-sync)" spec section added. Corrected the future-candidates line: **JCL/FICSM (0269),
correlation-matrix feasibility (0270), LHS (0271), probabilistic + conditional branching
(0273/0274) are BUILT in the repo** — restyle work now, not new features. `github.md` written
at the project root as the sync receipt (repo/branch/tree/version/ADR + screen map).

**Everything the user has asked for is built, verified, and documented. Nothing is
outstanding.** Decisions on record:
- Static screenshot set for the bundle: **intentionally skipped** — automated capture times
  out on this large page; README points reviewers to the live file. (User chose this.)
- Screenshots in `design_handoff_mission_ops_redesign/screenshots/` are from the OLD
  7-chapter v1 cut — README flags this. Regenerate from v2 only if the user asks.

**Known future candidates the user may request** (researched, not yet built; build them on
real engine data with the full chart contract): cost-loaded JCL (FICSM per JA CSRUH), probabilistic weather
calendars, series-vs-parallel risk mapping, realistic (non-early-start) simulation,
probabilistic branching.

**Sync 2026-09-02 (latest): repo main @ v1.0.230 / ADR-0452.** Product is now **POLARIS²** (ADR-0436; POLARIS² retired everywhere in the deck). New Library screen **One-Pager Timeline** (`op`, route `/onepager`, ADR-0446): `opDemoRows/opParseDate/opParseSpan/opParseRows/opReadXlsx/opParseCsv/opIngest/opLayout/buildOnePager/opPptx`; state `opDoc` ('demo' | parsed doc | null), `opTitle`, `opMsg`; lane tokens `LANES_LIGHT/LANES_DARK` appended per theme in renderVals. Also: Ch 03 `drvView` whole/path + `drvFile` picker + row `retarget`; Ch 08 `util` panel; Portfolio `buildCombine()` (`pfc`); Groups `fieldRoles` roles + role-named filter options (`gFilters[i].role`); WBS `wbsRole` picker; AI Settings gateway (`seAck/seKeyHeld/seKeyDraft`); Ask facts pairwise series; boot tiles = session facts; Timescale `tsLabel` + adapt note; TVAC constraint is an **MSO** (was SNET — soft under both engine definitions, ADR-0429). Details: `github.md` Last sync + `docs/coverage-verification.md`.

**2026-09-03 — verifier fixes (built + verified clean):** Portfolio Trend Lab stray `</div>`
removed (it leaked panels onto every screen). Boot/launch screen (`S.launch`: idle → travel →
done; `parked`/`traveling`/`showLaunch` renderVals) side cards (◄ EFFICIENCY OF PROOF · ABOARD ►)
now anchor `bottom:12px` inside the stage (was `top:38%/58%`, overlapping the BEGIN / Skip CTA
row); stage has `container-type:inline-size` and `@container (max-width:1100px){.astro-side-card
{display:none}}` (helmet) hides them on narrow stages. Bundle prototype copy re-synced.
`ASTROLABE.dc.html` / `ASTROLABE Command Deck.dc.html` at root = the earlier ASTROLABE
exploration (see `github.md`), kept, not the deliverable.

## How to resume

1. Read this file, then open `Mission Ops Redesign v2.dc.html` (the user is viewing it).
2. For engine/behavior questions, grep `src/schedule_forensics/web/app.py` + `web/static/`
   locally, or use github_* on `polittdj/Schedule-Manipulation-Analysis-Tool-Experiment@main`.
3. Make targeted edits with `dc_html_str_replace` / `dc_js_str_replace`; keep the
   conventions above; verify; keep the Claude Code bundle current if the change is material.
4. Preserve every requirement in "standing requirements" — especially: no calc changes, no
   lost functionality, tokens-only styling, chart contract on every visual.
