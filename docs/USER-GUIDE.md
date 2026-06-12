# Schedule Forensics — User Guide

A local, NASA-themed **forensic schedule-analysis** desktop tool. It ingests native Microsoft
Project / Primavera schedules, runs comparative and forensic analysis (CPM / driving slack,
DCMA-14, Acumen Fuse metrics, EVM, manipulation-trend detection, parity to Acumen Fuse v8.11.0
and SSI), and renders interactive, locally-rendered reports with a local-AI narrative — **entirely
on your machine**. No schedule data ever leaves the box (CUI-safe).

## 1. Install (once)

```bash
python -m venv .venv
. .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -e .                # installs the `schedule-forensics` launcher command
```

- **Python 3.11+** is required. **Native `.mpp`** ingestion also needs a **Java runtime (JRE/JDK 17+)**
  — Windows: `winget install EclipseAdoptium.Temurin.21.JRE` (or download from
  [adoptium.net](https://adoptium.net)), then restart the tool. **No admin rights?** Download the
  portable JRE *zip* from adoptium.net and extract it into the tool's `tools/jre/` folder — no
  installer, no elevation, no configuration needed. Java is found via `SF_JAVA`/`JAVA_HOME`, PATH,
  `tools/jre/`, or the standard install folders. The vendored MPXJ reader (`tools/mpxj/`) is
  auto-discovered; no Maven/build step. `.xml` (MSPDI) and `.xer` (Primavera) parse with no Java.
- **Local AI is optional.** The narrative works offline with the deterministic Null backend. For
  AI-polished narratives, install [Ollama](https://ollama.com) and pull a model; the in-app **AI
  Settings** panel lists/pulls/selects models. While the project is CLASSIFIED the tool only ever
  reaches a **loopback** model server — never the cloud.

## 2. Launch

- **Terminal:** `schedule-forensics`  (or `python -m schedule_forensics.launcher`)
- **Desktop icon:** on Windows run
  `powershell -ExecutionPolicy Bypass -File packaging\windows\Install-Desktop-Shortcut.ps1`
  once (no admin needed) to get a double-clickable **Schedule Forensics** Desktop icon with the
  tool's unique mark — the dark tile with the white ▲, the Gantt waterfall, and the gold
  data-date line (also the browser-tab favicon). Other OSes: see
  [`packaging/`](../packaging/README.md) (Linux `.desktop` + PNG icon, macOS `.command`).

The launcher picks a free **127.0.0.1** port, starts the server, and opens your browser at the
dashboard. Stop it with `Ctrl-C`.

## 3. Use the dashboard

1. **Open or import** a schedule from the landing page — drag a file onto the dropzone or click
   **choose a file…** (`.json` `.xml`/`.mspdi` `.xer` `.mpp` `.mpt`, up to **20** at once), or click
   **Load example** to try the bundled sample project instantly. Files are parsed **locally**;
   nothing is uploaded anywhere. Imports honor the file's **project calendar** — work week, hours
   per day, and holidays drive every computed date, float, and day-based threshold (an unreadable
   calendar degrades safely to the standard 8h/Mon-Fri default). Each loaded schedule is listed
   with **Open report** and **Save .json** (exports the normalised schedule as a re-openable
   `.json`, calendar and holidays included).
2. **Analysis** (click a schedule):
   - **DCMA-14 audit** — each of the 14 checks with pass/fail vs threshold and a plain-language
     suggested improvement; failing checks list the offending activities.
   - **Risks, opportunities & concerns** — a severity-ordered finding set (DCMA failures, baseline
     compliance, version-change signals, driving-path opportunity), **each cited (file + UID + task)**
     with a course of action.
   - **AI narrative** — a cited "story" of the schedule's health (CPM/manipulation trends, audit,
     recommendations). The model only rephrases the cited facts; it never invents a number.
   - **Interactive analysis** — charts (DCMA pass/fail, baseline compliance); an **MS-Project-style
     Gantt grid**: data columns you **add/remove** (UID, dates, baseline dates, duration, floats,
     % complete, resources, WBS…) beside a **timeline** with month ticks — red bars = critical,
     a translucent overlay = progress, diamonds = milestones, thin gray bars = WBS summaries, and
     an amber line at the **data date**; sort any column, **click any row to drill into its full
     metadata + citation**. A separate driving-path Gantt highlights the **driving / secondary /
     tertiary** path to a target UniqueID you enter.
   - **Target activity panel** — when a session-wide Target UID is set (see below), the report
     opens with the target's dates, floats, % complete, flags, and finish-vs-baseline variance,
     and the driving-path trace to it runs automatically.
   - **Working calendar** — the time basis behind the numbers: calendar name, hours/day (exact
     minutes), work week, and holidays, as imported from the file.
   - **Float analysis (low-float bands)** — how much of the to-go work is running out of room:
     incomplete activities at **0 / < 5 / < 10 working days** of total and free float (cumulative
     bands on the schedule's own calendar). A swelling low-float band is the early warning that
     the schedule can no longer absorb slips.
   - **Completion performance** — how the finished work actually performed: the **ahead / on
     schedule / behind** split vs baseline, average days gained/lost, activities longer/shorter
     than planned with the **duration ratio** (min/avg/max), **MEI** (the milestone execution
     index), and the staleness indicator (% of the schedule elapsed since anything finished).
3. **Path Analysis** — the SSI-style workspace: pick a schedule and a **target UniqueID**
   (the session-wide target pre-fills), set your own **secondary / tertiary day-bands**
   (> 0 days of driving slack), and **Trace**. The result reads like SSI: your **data on the
   left** (add/remove columns — UID, name, WBS, tier, slack, start/finish, baseline finish,
   duration, total float, % complete, resources) and a **scalable Gantt on the right**
   (zoom slider = pixels per day, horizontal scroll) with month ticks and the **gold
   data-date line**. Filter rows by tier or name/UID text and **hide 100%-complete** work.
   Below it, **Ask the AI**: type a question about the schedule — answers are grounded in
   the engine's computed, cited facts; with no local model active you get the matching
   facts themselves, and any model answer containing a number the engine never computed is
   discarded automatically.
4. **Trend** (with ≥2 versions loaded, up to 10+): every version ordered by **data date** — the
   per-version headline table (finish / completed / in-progress / critical), the **Net Finish
   Impact across the series**, **trend charts** (project finish, completed, critical, missing
   logic), per-metric **schedule-quality trend** sentences (improving/worsening, best and worst
   version named), and **manipulation-trend signals for each consecutive pair**. Enter a
   **focus UniqueID** to trend a specific activity: its computed finish and % complete per
   version, plus a finish-movement chart.
5. **Bow Wave / CEI** (≥2 versions): per snapshot, the monthly **Activity Finishes** chart —
   gold = baselined to finish, blue = scheduled to finish, green = actually finished, with the
   dashed data-date marker. Step **Prev/Next** through snapshots or press **Auto-play** to watch
   the bow wave of slipped work push right like a movie. The **CEI (Current Execution Index)**
   table compares, for each snapshot, what the *previous* snapshot planned to finish in the
   following month vs what this snapshot re-scheduled and what actually finished
   (CEI = completed-on-time ÷ previously planned; 1.00 = executed to plan — an unplanned finish in the month earns no credit).
6. **Forecast** — three independent answers to *"when will it really end?"*: the schedule's own
   **CPM logic**, a **completion-rate extrapolation** (to-go activities at the historical
   completions-per-month pace), and the **earned-schedule IEAC(t)** estimate
   (AT + (PD − ES) / SPI(t)). Each method shows the inputs it used; a method with missing inputs
   shows "—" — never a fabricated date. Methods that disagree are themselves a finding. With ≥2
   versions, the **forecast-drift table** re-runs all three per version — forecasts that keep
   sliding right are the bow-wave signature.
7. **Executive Briefing** — a print-ready diagnostic briefing in the Acumen Fuse style: a workbook
   summary (versions, earliest start, latest completion), the cross-version **Trend Analysis**, a
   per-project summary (dates, % complete/in-progress/planned, milestones/summaries, baseline
   window and **behind/ahead-of-schedule days**), and a per-project **schedule-quality verdict**
   for every DCMA check. Every sentence carries its **file + UID + task** citation; the local AI
   may polish the prose but can never change a number. Use the browser's **Print** for a hand-out.
8. **Compare** (with ≥2 versions loaded): the two most recent versions in data-date order — CPM/
   progress trend and **manipulation-trend signals** (deleted logic, shortened durations, deleted
   tasks, baseline/actual date edits) with the **Net Finish Impact** in calendar days. Honest
   progress shows no false flags.
9. **AI Settings** — choose the backend (local Ollama / offline Null), list/pull/select models, and the
   project **classification**. A persistent banner names any external endpoint when UNCLASSIFIED; the
   tool **fails closed to local** otherwise.
10. **Target UID (header)** — type any activity's UniqueID into the header's **Target UID** box and
   press **Set** to focus the whole session on that activity: the report page opens with its
   **Target activity** panel and auto-runs the driving-path trace to it, the **Trend** page focuses
   on it automatically, and **Compare** shows its computed-finish movement between versions. Leave
   the box blank and press Set (or **Wipe Session**) to clear it. A summary UID is named as such —
   pick one of its activities for a trace.
11. **Light / dark mode** — the header's **theme button** (☀/☾) switches between the dark default
    and a bright theme; the choice is stored locally in your browser (`localStorage`) and applies
    to every page, charts included. Nothing about the preference leaves the machine.
12. **Metric Dictionary** (`/help`) — a plain-language definition + formula + source for **every**
    metric the tool emits (also in [`METRIC-DICTIONARY.md`](./METRIC-DICTIONARY.md)).
13. **Wipe Session** — clears all loaded schedules and derivatives from memory (including the
    Target UID).

## 4. Verifying a number (forensic use)

Every figure the tool shows is traceable: metrics carry their offending activities, and findings/AI
sentences carry **file + UniqueID + task name**. Cross-version matching is by **UniqueID only** — never
row id, never name — so you can open the cited activity in the parent `.mpp` and confirm it. See
[`PARITY-REPORT.md`](./PARITY-REPORT.md) for how the numbers match Acumen Fuse v8.11.0 and SSI.

## 5. Data sovereignty (CUI)

The tool transfers **no data off the machine**: the server binds 127.0.0.1 only, all viz assets are
bundled locally (no CDN — enforced by an air-gap test), the AI defaults to local and fails closed, and a
network-egress guard fails the build if any forbidden cloud HTTP client enters the runtime. Schedule
files, parsed derivatives, and reports are git-ignored and never committed.

## Exporting to Excel and Word

Every analytical page carries **⬇ Excel / ⬇ Word** links (top right): the report page
(all panels + the full activity grid), Path Analysis (the traced grid — links activate
after you Trace), Trend, Bow Wave/CEI (the CEI table plus every snapshot's monthly
data), Forecast, and Compare (the manipulation signals). Files are generated locally
and download straight from your browser — nothing leaves the machine.

