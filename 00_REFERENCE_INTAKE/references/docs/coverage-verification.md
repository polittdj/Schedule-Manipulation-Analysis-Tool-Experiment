# Coverage verification — repo UI → MERLIN deck
Verified 2026-08-14 against `polittdj/Schedule-Manipulation-Analysis-Tool-Experiment` HEAD `71a56d32` (route/module inventory from `docs/UI-INVENTORY.md`, tree `10b2cc1b`; structural audit re-confirmed at `1a9c900b`). Deck = `Mission Ops Redesign v2.dc.html` (MERLIN). Purpose: prove nothing in the shipped UI is missing from the redesign before Claude Code handoff.

## 1. All 32 HTML routes → deck screens (32/32 covered)

| Repo route | Deck screen (`data-screen-label`) |
|---|---|
| `/` (home, upload, roles) | 00 Import — dropzone, formats, role strip, Excel round-trip templates |
| `/analysis/{name}` | 01 Where we stand — Gantt (field columns, links, dates, timescale), float band, findings, DCMA-14 |
| `/card/{name}` | Library Schedule ID Card (+ ID-card panel on ch. 01) |
| `/wbs/{name}` | Library WBS Rollup |
| `/standards` | Control Standards and Execution Indices |
| `/portfolio` | Program Portfolio — Command Grid · Ledger · Geo/Sites (map) · **Trend Lab (new)** + program drill |
| `/mission` | Mission Control — tile wall, play-all, step-back |
| `/compare` | **10 What changed — full any-pair compare page**: pair picker (v0→v1 … v4→v5) with CLEAN/WATCH/MASKING verdict, net-finish-impact attribution bar (reported vs absorbed by class), file-level what-moved census (CPM finish, DCMA score, CP membership/Jaccard, edits), biggest movers (→ Task Information), per-class manipulation scan, field-level diff ledger with driving-path scope + pair/all-pairs exports. Same pair engine as `/integrity` |
| `/path` + `/driving-path` | 03 What drives the date — target UID, tiers P1/P2/P3, deps view, drag, merge hotspots, Path-between-two-points (over time) |
| `/trend` | 02 quality board (14 × 6) + 05 How it moved (drift, per-update decomposition) |
| `/margin` | Control Margin Dashboard (+ margin burndown on ch. 05) |
| `/evm` | Library EVM (+ EVM ledger on ch. 07) |
| `/resources` | 08 Who is overloaded — loading vs capacity, period drill, roster |
| `/cei` | 06 Work piling up — CEI, bow wave |
| `/scurve` + `/curves` | 09 Where it lands — S-curve & finish walk (+ Library Metric Lab ribbon for any-metric curves) |
| `/ribbon` | 02 Can we trust the plan — quality ribbon + Behind the number drill |
| `/volatility` + `/evolution` | 04 How stable is the path — stability signal, flow, membership matrix, transition ribbons, what-if ledger |
| `/performance` | 07 How we execute — census, duration ratio, bow wave + cumulative S, indices, quads, SPI(t) by WBS |
| `/integrity` | **Forensics · Schedule Integrity — dedicated screen**: seven manipulation detectors (baseline re-dates, constraints, logic edits, duration cuts, out-of-sequence, manufactured float, calendar) with per-pair sparklines, masking-quotient chart (real vs reported movement), field-level evidence ledger (before → after, wd absorbed, severity, Task Information links), any-pair picker, driving-path scope, per-pair + all-pairs export. Cross-linked from ch. 02 and ch. 10 |
| `/groups` | Setup Groups and Filters — session-wide filter, 10-rule builder, saved views |
| `/forecast` | 09 — forecast drift, which-to-believe (+ Library Segment Forecast = `/export field-forecast` family) |
| `/workbench` | Library Metric Workbench — any measures × every version |
| `/scorecards` | Control Assessment Scorecards |
| `/brief` + `/briefing` | 12 The briefing — walked forecast, manipulation brief, outliers, recovery plan, Word/PDF export |
| `/risks` + `/sra` | 11 What could go wrong — register, sim inputs, SRA histogram, criticality, confidence S-curve, pre/post-mitigation, JCL, tornado ×2, risk-driver marginal impact, SSI run, 5×5 matrices, branching |
| `/settings` (+ AI settings) | Setup AI Settings — backend, models, fail-closed |
| `/help` | Setup Metric Dictionary |

Plus deck-only additions (no repo route lost): boot/launch sequence (ADR-0328 audio + scenes), Portfolio at Scale reference, Beyond the Schedule, Metric Lab, portfolio Trend Lab + Manipulation Watch.

## 2. The 35 static chart modules → deck instruments
`gantt/histogram/curves/scurve/drift/path*/driving_*/cei/performance/resources/margin*/scorecards/scatter/ribbon_drill/drilldown/findings_drill/workbench/volatility/trend*/sra*/wbs/whatif` — all have on-screen counterparts (see §1 rows). Shared machinery equivalents: `chartframe.js` → per-panel ▦ DATA / ⤓ EXPORT (XLSX·PDF·CSV) / ⛶ PRESENT chrome; `timeaxis/timescale.js` → Timescale dialog; `taskinfo.js` → 7-tab Task Information dialog (openable from Gantt rows, matrices, SRA grid, WBS, explorer); `vizhints.js` → per-instrument how-to-read lines; `legend_toggle.js` → series chips on multi-series charts (partial — see §3); `globe.js` → header insignia + AI status on Setup·AI; play-all coordinator → Mission Control PLAY ALL + pair/version steppers; `theme.js` 4 themes → console/daylight/apollo/jarvis theme switch; role model → role strip on 00 Import.

## 3. Known deviations (deliberate, presentation-scope)
- **i18n (EN/ES/FR/DE, ADR-0099/0102/0267)**: no language switcher in the deck — copy is EN-only by design; the engine's catalog is untouched.
- **legend_toggle parity is partial**: series show/hide exists where it matters (forecast methods, path overlays, metric ribbon); not every legend chip is clickable.
- **Trend Lab histories are demo-seeded** (flagged on-screen) — the shipped engine must read them from the stored update chain.
- Sub-11px type: deck floors at 7.5–8px for mono micro-labels only, matching the repo's stated 8px mono floor.
- Words scrubbed per repo design law: NASA, vendor names (see repo-audit.md).

## 4. Handoff pointers
- Deliverable: `Mission Ops Redesign v2.dc.html` (MERLIN). Previous exploration: `ASTROLABE.dc.html` (has Compare Bay A/B + Path Explorer variants worth mining).
- Handoff bundle: `design_handoff_mission_ops_redesign/` + root `HANDOFF.md`; sync state in `github.md`; repo truths in `docs/repo-audit.md`, `docs/UI-INVENTORY.md`.
- Everything a page shows is computed or cited in-file; exports carry CUI marks; every panel presents via ⛶/double-click (ADR-0305 overlay law).
- Every screen wears a ⇄ ROUTE chip in the header chrome naming the repo route(s) it restyles (`ROUTEMAP` in the deck logic) — the 32-route map is visible in the UI itself, not only in the docs.


## Re-verification 2026-09-02 — main @ tree 844e1d3a (v1.0.230, ADR ≤ 0452)

HTML route census re-run from `app.py` (`response_class=HTMLResponse`): **34 routes** (was 32). New since 71a56d32:

| Route | Deck screen | Status |
|---|---|---|
| `/launch` (ADR-0426) | Boot / launch sequence | already present (the repo ported the deck's screen); telemetry tiles re-cut to session facts to match |
| `/onepager` (ADR-0446) | Library · One-Pager Timeline (`op`) | **built** — intake grammar, layout engine, preview, ▦/⤓ EXCEL/⤓ POWERPOINT/⛶, drop + picker |

Functionality added to existing screens (ADR → screen): 0431 Combine Projects → Program Portfolio · 0432/0438 whole-schedule + UID retarget + cross-Project picker → 03 · 0433 Utilization by resource → 08 · 0437 multi-folder drop copy → 00 Import · 0450 Field roles → Setup Groups & Filters + Library WBS Rollup · 0402/0403/0404 gateway backend + key + persistence → Setup AI Settings · 0424 pairwise series → Ask panel (every screen) · 0441/0447/0452 adaptive tiers + label styles → Timescale dialog · 0436 POLARIS² → chrome, boot, exports · 0429 MSO constraint story → 02, 10, 11, 12, Integrity, ID card, dictionary.

Deliberate deviations unchanged: EN-only copy; demo-seeded Trend Lab histories; the .pptx export is exercised in the browser but PowerPoint itself was not run here (the repo records the same UNVERIFIED leg).
