# POLARIS² — Schedule Manipulation Analysis Tool

A local, NASA-themed **forensic schedule-analysis** desktop tool — branded **POLARIS²** (*Program
Oversight & Logic Analysis for Risk & Integrity of Schedules*) in the running UI. It ingests native
Microsoft Project / Primavera schedules, runs comparative and forensic analysis (CPM / driving slack,
DCMA-14, Acumen Fuse v8.11.0 & SSI parity metrics, EVM, manipulation-trend detection), and produces
interactive, locally-rendered reports — organized as a **12-chapter "Mission Ops" story** across four
selectable themes — with a cited local-AI narrative, **entirely on your machine**. Nothing about a
schedule ever leaves the box. As built there is one sanctioned exception, an armed Approved AI
gateway, and one known gap, an AI endpoint typed as a host name; both are described under
[The two laws](#the-two-laws).

It is built for the five roles its landing page offers — Scheduler / Planner, Program / Project
Manager, Forensic Analyst, Auditor (DCMA / IG) and Counsel / Testifying Expert. You load one or more
versions of a schedule; the tool computes every figure from the files themselves ("every number in
this report is computed, never typed"), cites each finding to **file + UniqueID + task name**, and
exports what you see to Excel and Word (and the One-Pager slide to PowerPoint).

> **Where things stand.** The tool is built and runs end to end: ingest → CPM / forensic analysis →
> interactive, locally-rendered report → cited local-AI narrative. Every page header shows the build
> number of the tool you are running. Current state always lives in
> [`docs/STATE/HANDOFF.md`](./docs/STATE/HANDOFF.md); the finished-build summary is in
> [`docs/FINAL-REPORT.md`](./docs/FINAL-REPORT.md). **Before you cite any figure, read
> [Known issues before you cite a figure](#known-issues-before-you-cite-a-figure).**

## Contents

- [What it does](#what-it-does) · [The two laws](#the-two-laws) ·
  [Install](#install) · [Launch](#launch)
- **How to use POLARIS² — step by step:** [1 Install](#step-1-install) ·
  [2 Launch](#step-2-launch-and-read-the-launch-page) · [3 Load](#step-3-load-your-schedules) ·
  [4 Navigate](#step-4-find-your-way-around) · [5 Dashboard](#step-5-read-the-dashboard-and-a-report) ·
  [6 Driving path](#step-6-find-the-critical-and-driving-path) ·
  [7 Versions](#step-7-compare-versions-and-read-manipulation-signals) ·
  [8 DCMA / Acumen](#step-8-run-the-dcma-14-and-acumen-style-checks) · [9 Risk](#step-9-assess-risk-sra) ·
  [10 One-Pager](#step-10-make-a-one-pager-and-meet-lodestar) · [11 Export](#step-11-export) ·
  [12 Ask the AI](#step-12-ask-the-ai) · [13 Verify](#step-13-verify-a-number-before-you-cite-it) ·
  [14 CUI](#step-14-follow-the-cui-rules) · [15 Quit](#step-15-quit) ·
  [Troubleshooting](#troubleshooting)
- [Known issues before you cite a figure](#known-issues-before-you-cite-a-figure) ·
  [Build state & where to look](#build-state--where-to-look) · [Quality](#quality)

## What it does

- **Reads your schedules on this machine** — Microsoft Project `.mpp` / `.mpt` (through the bundled
  MPXJ converter, which needs Java), MS Project XML (`.xml` / `.mspdi`), Primavera `.xer`, and the
  tool's own `.json`. A folder is one Project and every schedule inside it is a version.
- **Computes the schedule itself** — its own CPM pass (dates, total and free float, driving slack) on
  the calendars imported from the file. Two known exceptions: a Primavera `.xer` activity on its own
  P6 calendar is computed on the project calendar, and a day with a single work block (no lunch
  break) is mis-measured (open findings A0923-IMP-003 and A0923-IMP-002; no committed file exercises
  either, but an operator file can). Where the file stores the source tool's own Critical flag,
  critical counts use it (Acumen's basis) and fall back to pure-logic CPM float only where it does not.
- **Scores it against the standards** — the DCMA 14-point assessment, the NASA / Acumen-Fuse execution
  indices, the Schedule Execution Metrics (SEM), a schedule-quality ribbon, and the NASA STAT / GAO /
  SRA-readiness scorecards. Every metric's definition, formula and source is in the Metric Dictionary.
- **Follows it across versions** — trend, bow wave / CEI, finish and slippage curves, critical-path
  evolution and volatility, a version-to-version compare, and manipulation-pattern signals (deleted
  tasks or logic, shortened in-progress durations, added hard constraints, loosened calendars,
  baseline-date changes, edited or erased actuals), each cited.
- **Looks ahead** — finish forecasts, an S-curve, a Monte-Carlo schedule risk analysis (SRA), a
  5x5 risks-and-opportunities matrix, and a margin burn-down.
- **Briefs** — an Executive Briefing and a Diagnostic Brief in which every statement carries its
  citation.
- **Explains, optionally** — a local AI can polish the narrative and answer questions over the
  engine's cited facts. With no model it returns the cited facts themselves; the tool works fully
  offline without any AI.

The whole report is arranged as a **12-chapter Mission Ops story** (Import → Mission Control → Act I
Situation → Act II Diagnosis → Act III Outlook), with a Setup rail (Workbench, Groups & Filters, AI
Settings, Metric Dictionary) off the spine. That summary is out of date on two points (open finding
A0923-DOC-003): **Metric Workbench** sits on the LIBRARY rail, not SETUP, and the overview between
Import and Act I also holds **Portfolio**. The off-spine pages fall into four rails — FORENSICS,
LIBRARY, CONTROL and SETUP (Groups & Filters, AI Settings, Metric Dictionary);
[Step 4](#step-4-find-your-way-around) lays out every entry as this build renders it.

See [`docs/USER-GUIDE.md`](./docs/USER-GUIDE.md) for the page-by-page reference and
[`docs/METRIC-DICTIONARY.md`](./docs/METRIC-DICTIONARY.md) (also at `/help`) for a definition +
formula + source for every metric the tool emits.

## The two laws

1. **Data sovereignty (CUI).** No schedule data, file content, task name, date, UniqueID, or derived
   metric ever leaves the local machine. That is the rule; as built it has one sanctioned exception
   and one known gap (open findings of the 2026-09-23 audit). The exception (ADR-0402): the
   **Approved AI gateway** backend, once an operator selects it, picks the approved endpoint and
   ticks the acknowledgment, sends AI prompts — task names, UniqueIDs, dates — off the machine to
   that endpoint under either classification, bannered and logged (A0923-CUI-003). The gap: the
   local backends refuse a non-loopback address, but a host name such as `ip6-localhost` passes the
   check and is resolved by the operating system when the prompt is sent, so it can reach another
   machine (A0923-CUI-001) — keep the literal `127.0.0.1` default. The AI defaults to
   local Ollama and falls back to the offline Null backend when it cannot reach the model. A
   network-egress guard fails the build if any forbidden cloud HTTP client enters the runtime, and
   an air-gap test fails if any served page references a remote asset.
2. **Fidelity over speed.** Numbers must match the reference tools (Acumen Fuse v8.11.0, SSI,
   Microsoft Project) on the same inputs. A fast, wrong number is worthless in a forensic/testimony
   context. Parity is gate-locked (`pytest -m parity`).

What Law 1 asks of you as a user is in [Step 14](#step-14-follow-the-cui-rules); what Law 2 asks of
you is in [Step 13](#step-13-verify-a-number-before-you-cite-it).

## Install

Two ways in. Analysts normally use **an installer**; developers work **from a checkout with pip**.

### Option A: an installer (one file per machine)

The installers are in the `installer/` folder, with their own
[README](./installer/README-DISTRIBUTABLE.md). Give each machine **one** file matching its operating
system and hardware tier:

| Tier | For a machine with | Local AI it offers | Windows | Linux | macOS |
|------|--------------------|--------------------|---------|-------|-------|
| 1 | 16 GB RAM, no discrete GPU | a small model | `install-tier1.ps1` | `install-tier1.sh` | `install-tier1.command` |
| 2 | 64 GB RAM + discrete GPU | a mid-size model | `install-tier2.ps1` | `install-tier2.sh` | `install-tier2.command` |
| 3 | 128 GB RAM + discrete GPU | a large model (~43 GB download) | `install-tier3.ps1` | `install-tier3.sh` | `install-tier3.command` |

```powershell
# Windows: right-click the file -> Run with PowerShell, or:
powershell -ExecutionPolicy Bypass -File install-tier1.ps1
```

```bash
bash install-tier1.sh          # Linux
bash install-tier1.command     # macOS (or double-click the .command file)
```

Each installer embeds one exact version of the tool (its first banner line prints it), checks what
is already present, and installs only what is missing:

- **Python 3.11+** — the Windows installer installs it with winget, the macOS one with Homebrew when
  Homebrew is present; the Linux one names the package to install and stops.
- **The tool** — into its own private environment, from the copy embedded in the file.
- **The MPXJ converter** that native `.mpp` import needs.
- **Optional:** Java 17+ (the Windows installer offers it; on Linux and macOS install Java yourself if
  you will load `.mpp` files) and Ollama with the tier's model — every installer asks before the AI
  step, and you can answer no.

It finishes with a **Polaris²** icon on the Desktop (and in the Start menu on Windows, the app menu on
Linux), an uninstaller and a first-run README. The installer uses the internet only for public
prerequisites; on an air-gapped machine set `SF_MPXJ_OFFLINE=1`, or put a copy of `tools/mpxj`
beside the installer (or point `SF_MPXJ_HOME` at one); for what the running tool can send, see
[The two laws](#the-two-laws). To update, download the **latest** installer and run it again — an
old file reinstalls the old version.

### Option B: from a checkout with pip

```bash
python -m venv .venv
. .venv/bin/activate            # Windows: .venv\Scripts\Activate.ps1
pip install -e .                # installs the `schedule-forensics` launcher command
```

- **Python 3.11+** required. Native **`.mpp`** ingestion also needs a **Java runtime (JRE/JDK 17+)** —
  Windows: `winget install EclipseAdoptium.Temurin.21.JRE` (or download it from adoptium.net), then
  restart the tool. **No admin rights?** Extract a portable JRE *zip* into the checkout's `tools/jre/`
  folder or into `%LOCALAPPDATA%\Programs\Microsoft` — no installer, no elevation, no configuration.
  Java is found via `SF_JAVA`/`JAVA_HOME`, PATH, `tools/jre/`, or the standard install folders. The
  vendored MPXJ reader (`tools/mpxj/`) is auto-discovered (no Maven/build step). `.xml` (MSPDI),
  `.xer` (Primavera) and the tool's own `.json` parse with no Java.
- **Local AI is optional.** The narrative works offline with the deterministic Null backend; for
  AI-polished prose, install [Ollama](https://ollama.com) and pull a model with `ollama pull` in a
  terminal (the in-app **AI Settings** page lists the installed models, **Refresh models** re-reads
  them, and you select one). While CLASSIFIED the tool only ever reaches a loopback model
  server. That sentence is out of date: an armed Approved AI gateway or a host-name endpoint can
  send prompts off the machine whatever the classification ([The two laws](#the-two-laws)).
- A step-by-step guide to connecting a larger local model is in
  [`docs/CONNECT-A-BIGGER-AI-MODEL.md`](./docs/CONNECT-A-BIGGER-AI-MODEL.md); its default-model and
  timeout figures are out of date (open finding A0923-DOC-010) — **AI Settings** shows the live ones.

## Launch

- **Installed with an installer:** double-click the **Polaris²** Desktop icon. It serves the tool at
  `http://127.0.0.1:8321`; if that port is held and will not release, the launch moves to a free port
  rather than refusing to start.
- **Terminal (pip install):** `schedule-forensics` (or `python -m schedule_forensics.launcher`). It
  picks a free **127.0.0.1** port and prints the live address.
- **Desktop shortcut for a pip install:** Windows — run
  `powershell -ExecutionPolicy Bypass -File packaging\windows\Install-Desktop-Shortcut.ps1` once from
  the activated venv to get a **Schedule Forensics** Desktop icon; Linux — copy
  `packaging/schedule-forensics.desktop` into `~/.local/share/applications/` and mark it trusted;
  macOS — double-click `packaging/schedule-forensics.command` (`chmod +x` it once). Both files run
  the `schedule-forensics` command by name, so it must be on the PATH the double-click sees (put the
  venv's `bin` on PATH, or edit the file to the venv's full path; [`packaging/README.md`](./packaging/README.md)).

Every launch path binds **127.0.0.1** only (a non-loopback host is refused) and opens your browser on
the **launch page**. How to stop it is in [Step 15](#step-15-quit).

- **Headless reports:** the companion `schedule-forensics-report` console script renders a
  **deterministic** exhibit pack (SVG/CSV/HTML) with no browser and no server, for scheduled/batch
  generation (`schedule-forensics-report --help`; `--out` is required, and it currently renders from
  a prebuilt `--payload` — `--inputs` exits with code 4 until the CP-basis engine lands, or with code
  3 first when no `--target-uid` is given).

## How to use POLARIS² — step by step

This walk-through takes a first-time analyst from install to a figure they can defend. It names the
buttons as the pages render them; the page-by-page reference is
[`docs/USER-GUIDE.md`](./docs/USER-GUIDE.md), which this guide links to rather than repeats. Practise
first on the bundled example (**Load example** on the Import page) or, in a repository checkout, on the
synthetic five-version set `tests/fixtures/test_projects/TP4_DataCenter_v1.xml` … `_v5.xml` — copy
those five files into a folder of their own and load that folder, so they become one Project with
five versions.

### Step 1. Install

Pick [Option A or Option B](#install). If you will load native `.mpp` files, make sure Java 17+ is
present (the Windows installer offers it; otherwise install it yourself). Nothing else is
required: the AI is optional and every analysis page works without it.

### Step 2. Launch and read the launch page

Start the tool ([Launch](#launch)). The browser opens on **Launch Sequence**, the boot screen: tiles
for **SCHEDULES ABOARD** and **NEWEST DATA DATE**, **BEGIN LAUNCH SEQUENCE**, **Skip to the deck**, a
**Go straight to the deck next time** tick-box, and **GO TO IMPORT** (**ENTER THE DECK** once
schedules are loaded). In the default CLASSIFIED session every page — this one included — carries
the **Controlled Unclassified Information • CUI** banner top and bottom, and a *Handling &
export-control notice* drawer (CUI / ITAR / EAR) you should read once.

The header on every other page holds the navigation, the build number, and the session controls:
**Wipe Session**, **Quit**, **Reset view**, **Measure to** (a milestone) / **or UID** + **Set**, **View**
(CONSOLE, DAYLIGHT, APOLLO, JARVIS), **Theme**, **Size** and **Language** (English, Español, Français,
Deutsch, Português).

### Step 3. Load your schedules

On the Import page (chapter 00, the dropzone at `/`):

1. **Open or import** on the landing page — drag a file onto the dropzone or click **choose a file…**
   (`.json` / `.xml` / `.mspdi` / `.xer` / `.mpp` / `.mpt`, up to 100 at once), or **Load example** for
   the bundled sample. Files parse locally; the dashboard tells you exactly what loaded and what
   failed (no silent failures). Each schedule lists **Open report** and **Save .json**.
2. Two corrections to item 1 (open findings A0923-DOC-002, A0923-WEB-001). The buttons read **choose
   files…** (Ctrl-click, Cmd-click on a Mac, or Shift-click to take several) and **choose one
   folder…**, and you can drop several folders at once. There is no file-count limit, but one upload
   carries at most 1,000 files — every readable file in the selection counts, schedule or not — and a
   larger one is refused with no message ([Troubleshooting](#troubleshooting)). A native `.mpp` /
   `.mpt` needs Java 17+; the other formats do not. A file over 500 MB is refused with a named reason,
   and non-schedule files inside a folder are skipped and counted.
3. **How files become Projects and versions.** A folder is one Project and every schedule inside it
   (nested sub-folders and all) is a version; loose files group by their document Title (`.mpp`) or
   P6 project name (`.xer`). If one picked folder holds schedules in two or more sub-folders, the
   page stops and asks whether they are updates of one schedule (one Project with versions) or
   different programs (one Project each). Versions are ordered by data date, oldest first. If the
   versions of one schedule land as separate one-version Projects, open **Portfolio** and use
   **Combine Projects** (tick them, name the result, press **Combine**).
4. **Read the import messages** at the top of the page: `Loaded N: …`, `Could not import <file>:
   <reason>`, and notes such as a file with no project title or skipped non-schedule files.
5. One version unlocks the per-file pages. The cross-version pages (Trend, Compare, Critical-Path
   Evolution, CP Volatility, Bow Wave / CEI, Schedule Integrity) ask you to load at least two
   versions until two or more versions of the same Project are loaded.
6. **Save .json** downloads the normalised schedule as a `.json` you can load again later (it fails
   for a file name with characters outside ISO-8859-1 — see [Troubleshooting](#troubleshooting)).

### Step 4. Find your way around

The navigation is a story spine plus four off-spine rails. As this build renders it:

| Group | Entries (page) |
|-------|----------------|
| LOAD | 00 Import (`/`) |
| OVERVIEW | Portfolio (`/portfolio`) · Mission Control (`/mission`) |
| ACT I · SITUATION | 01 Where we stand (the report, `/analysis/<file>`) · 02 Can we trust the plan? (`/ribbon`) |
| ACT II · DIAGNOSIS | 03 What drives the date (`/path`; beat: Driving Path) · 04 How stable is the path (`/evolution`; beat: CP Volatility) · 05 How it moved (`/trend`; beat: Finish & Slippage) · 06 Work piling up (`/cei`) · 07 How we execute (`/performance`) · 08 Who is overloaded (`/resources`) |
| ACT III · OUTLOOK | 09 Where it lands (`/forecast`; beat: S-Curve) · 10 What changed (`/compare`) · 11 What could go wrong (`/sra`; beat: Risks & Opportunities) · 12 The briefing (`/briefing`; beat: Diagnostic Brief) |
| FORENSICS | Schedule Integrity (`/integrity`) |
| LIBRARY | Metric Workbench · One-Pager Timeline · One-Pager Compare · WBS Rollup · Schedule ID Card · EVM |
| CONTROL | Margin Dashboard · Standards & Execution · Assessment Scorecards |
| SETUP | Groups & Filters · AI Settings · Metric Dictionary |

WBS Rollup and Schedule ID Card appear once a schedule is loaded. Most pages open with a collapsed
**What am I looking at — and how do I use it?** explainer, and the chapter pages end with a **STORY SO
FAR** strip and a link to the next chapter (for example **Chapter 04 → How stable is the path**). On
the Import page, **Who’s analyzing today?** picks a role that highlights the chapters that role
usually needs — nothing is hidden and no number changes.

Two session-wide controls change what every page measures, and each shows a banner on every page
while it is on: **Groups & Filters** (`/groups`) scopes every page to the activities you pick (in
the default **Reduce** mode; the **Highlight** mode offered beside an `.mpp` file's saved filters
only marks the matches, and the banner then reads "metrics NOT scoped"), and **Measure to** / **or
UID** limits every metric to one activity and the work that drives it (`Analysis endpoint: UID n …
clear endpoint`). Clear both before quoting whole-project numbers.

### Step 5. Read the dashboard and a report

- The **dashboard** (`/`) lists every loaded version under **LOADED VERSIONS** — activities, source
  file, data date, computed finish, effective margin and the DCMA-14 pass/fail count — with **Open
  report · Card · WBS · Save .json** per row and an **Executive briefing →** link.
- **Open report** is chapter 01, *Where we stand*: status mix, float, the interactive Gantt grid, the
  working calendar imported from the file, low-float bands, completion performance, structural and
  logic checks, the **DCMA-14 audit**, **Risks, opportunities & concerns** and the **AI narrative
  (local, cited)**. This page shows ONE file: the line under the header names it and, when more
  than one version is loaded, offers a switch to another.
- **Mission Control** (`/mission`) puts every loaded version's key indicators on one wall;
  **Portfolio** (`/portfolio`) is the one cross-project page.

### Step 6. Find the critical and driving path

1. Open chapter 03, **What drives the date** (`/path`, the page titled Path Analysis). Pick the
   **Schedule**, type a **Target UID**, set the **Secondary ≤ d** / **Tertiary ≤ d** bands and press
   **Trace**. The driving path (slack ≤ 0) and the secondary / tertiary tiers trace back from the
   target: data on the left, a scalable timeline with
   the gold data-date line on the right. The **hide 100% complete** box and the **Tier**, **Filter**
   and **Find** controls narrow the rows; **View entire project** zooms back out.
2. **Driving Path** (`/driving-path`) traces **From** a source UniqueID **To** a target across every
   loaded version (**All files (chronological)**), so you can watch the corridor shift.
3. For a quick exact answer anywhere, use **Show driving path** in the Ask panel — it is computed, not
   AI.
4. With two or more versions, chapter 04 (**Critical-Path Evolution**, **CP Volatility**) shows which
   activities joined, left and stayed on the critical path.

Leave **Ignore constraints** and **Ignore leveling delay** off on a fully-dated file, do not cite the
Path Analysis **Drag** column, and on **Driving Path** and **Critical-Path Evolution** do not read a
ticked Ignore option's path, tiers or counts as the re-solve its banner promises (open findings
A0923-CPM-036 / 038) — all three are on the [known-issues list](#known-issues-before-you-cite-a-figure).

### Step 7. Compare versions and read manipulation signals

1. Load two or more versions of one Project ([Step 3](#step-3-load-your-schedules)).
2. Chapter 10, **What changed** (`/compare`, the page titled Compare): choose **Baseline (A)** and
   **Comparison (B)** and press **Apply** (it starts on the two most recent versions). It counts
   activities changed, added and
   removed, logic added and removed, and the finish move; the **Net Finish Impact** is in calendar
   days (negative means the finish moved later); the **Manipulation-trend signals** table lists each
   signal with its severity and course of action, or reads "No manipulation signals detected (honest
   progress)".
3. **Schedule Integrity** (`/integrity`, FORENSICS rail) goes deeper on one pair: every
   manipulation-pattern signal cited to file + UniqueID + task, what each change did to the critical /
   driving path, and a counterfactual finish without those changes. Its own words: *this is analysis
   for review, not an accusation* — treat each signal as a question to put to the schedule owner.
4. Chapters 05 and 06 show the direction over time: **Trend**, **Finish & Slippage** and **Bow Wave /
   CEI**.

### Step 8. Run the DCMA-14 and Acumen-style checks

1. **Standards & Execution** (`/standards`, CONTROL rail) puts three families on one page for the
   latest file: the **DCMA-14 point assessment** (value, PASS / FAIL / N/A, threshold, verbatim
   formula and source), the **NASA / Acumen-Fuse execution indices**, and the **Schedule Execution
   Metrics (SEM)**. Its **EXCEL** button exports the analysis workbook.
2. The report page carries the **DCMA-14 audit**: each check's status, count and percentage, its
   definition and a suggested improvement. A new session starts with **Acumen Fuse parity mode**
   ticked, which scores the checks the way Acumen Fuse does; untick it and press **Apply** for the
   pure-logic / forensic view. When to use which: [`docs/ACUMEN-PARITY-MODE.md`](./docs/ACUMEN-PARITY-MODE.md)
   (its account of what check 9 reports is out of date — open finding A0923-DOC-011).
3. Chapter 02 adds the **Schedule Quality Ribbon** (`/ribbon`) and **Assessment Scorecards**
   (`/scorecards`: NASA STAT, the GAO guide's ten best practices, an SRA-readiness gate).
4. **Metric Workbench** (`/workbench`) lays any metric out across every loaded version, oldest to
   newest; click a value to list the activities behind it.
5. **Parity with the reference tools.** How the numbers match Acumen Fuse v8.11.0 and SSI is in
   [`docs/PARITY-REPORT.md`](./docs/PARITY-REPORT.md); the synthetic battery for checking it yourself
   side by side is in [`docs/TEST-PROJECTS.md`](./docs/TEST-PROJECTS.md). Parts of both are out of
   date (open findings A0923-DOC-005 to DOC-009); the values the test suite pins for the TP battery
   are in `tests/test_projects/`. Developers re-run the gate from a checkout with
   `python -m pytest -m parity` (some oracles need Java and the committed reference intake).

### Step 9. Assess risk (SRA)

1. Chapter 11, **What could go wrong** (`/sra`, the page titled Risk Analysis (SRA)): choose the
   version under **Run SRA against file** and press **Run on this file**.
2. Give tasks a 1–5 Risk Ranking Factor or Best / Worst-Case durations (**Calculate SRA Durations —
   all** fills them from the factor table), add discrete risks (**Add risk**), and **Run simulation**:
   the finish-date distribution with P50 / P80 markers and a tornado of the activities that drive the
   spread.
3. To work in Excel, download the **Risk Register template (Excel)** or **Task Risk template (Excel)**,
   fill it in, and bring it back with **Import**; incomplete rows and unmatched UIDs are skipped and
   counted in the import summary.
4. **Risks & Opportunities** (`/risks`) ranks the engine's cited findings in a 5x5 matrix;
   **Assessment Scorecards** sizes the reserve that protects a committed date; **Margin Dashboard**
   (`/margin`) tracks margin burn-down; chapter 09, **Where it lands** (`/forecast`), sets the
   finish-forecast methods side by side.

### Step 10. Make a One-Pager (and meet LODESTAR)

1. Open **One-Pager Timeline** (`/onepager`, LIBRARY rail) and click **Download the template**. Fill
   one sheet: **A** swimlane, **B** task or milestone, **C** start, **D** finish, **E** complete.
2. Drop the list on the page or **choose a file…**, then **Upload**. The page draws the slide.
3. Add **Logic links**: pick **From** and **To** (or click the two items on the slide) and press **Add
   logic link** — up to 200. Set a **Data date** with **Apply data date**, or leave the computer's date.
4. **POWERPOINT** exports the slide as native, editable shapes; the panel's **EXCEL** button exports
   the list. **One-Pager Compare** (`/onepager-compare`) puts a PRIOR and a CURRENT list on one slide.
5. **LODESTAR** is the same two pages as a standalone program: `lodestar/LODESTAR.pyz`, which needs
   nothing but Python 3.10+ — no install and no AI. Share the whole `lodestar/` folder; start it with
   `LODESTAR.bat` (Windows), `LODESTAR.command` (macOS) or `sh lodestar.sh` (Linux). See
   [`lodestar/README.md`](./lodestar/README.md).

### Step 11. Export

| What | Where | Format |
|------|-------|--------|
| A page's tables | the right-aligned **Excel** / **Word** links on most analytical pages (a few offer Excel only; `/path` and `/driving-path` show them after a trace) | `.xlsx` / `.docx` |
| One panel | the **EXCEL** button in the panel's toolbar | `.xlsx` |
| An Ask-the-AI answer with its cited facts | **EXCEL** / **WORD** beside **Ask**, once an answer is shown | `.xlsx` / `.docx` |
| A schedule you can load again | **Save .json** on the dashboard | `.json` |
| The One-Pager slide | **POWERPOINT** on the One-Pager pages | `.pptx` |
| SRA inputs | the two Excel templates on `/sra` | `.xlsx` |

Files are generated on this machine and download through your browser. The Excel and Word exports
carry a **CONTROLLED UNCLASSIFIED INFORMATION (CUI)** header and footer, and the One-Pager PowerPoint
carries the page's own marking (CUI in the default CLASSIFIED session). Once saved they are CUI files
([Step 14](#step-14-follow-the-cui-rules)).

### Step 12. Ask the AI

1. The **Ask the AI** panel sits at the foot of every page (the launch screen aside) once a schedule
   is loaded. Choose the scope under **About** (the whole workbook or one version), type a question
   and press **Ask** (Enter sends; Shift+Enter starts a new line). The engine's cited facts are
   always shown with the answer.
2. With no local model you get the cited facts themselves. To add written analysis, open **AI
   Settings** (`/settings`), choose the **Backend** — **Ollama (local)** or **OpenAI-compatible
   (local — …)** for a model on this machine, **Null (offline, deterministic)** for none — pick the
   **Model** and press **Save**. The walk-through for a larger model is
   [`docs/CONNECT-A-BIGGER-AI-MODEL.md`](./docs/CONNECT-A-BIGGER-AI-MODEL.md) (mind its out-of-date
   default figures — [Install](#install)).
3. Pick the **AI answer mode** on the same page:
   - **Annotate** (default) — the model may derive figures from the cited facts; any figure the engine
     did not compute is flagged as AI-derived.
   - **Strict** — an answer containing a figure the engine never computed is discarded wholesale. The
     page's own advice: pick strict for testimony work.
   - **Interpretive** — the model's text verbatim, ungated.
   - **Unrestricted** — the model also receives the per-activity data table and may calculate new
     figures; its text is shown verbatim and ungated.

   Strict and Annotate check figures written in digits: a number written another way can pass
   unflagged — see the [known-issues list](#known-issues-before-you-cite-a-figure) (open findings
   A0923-AI-001 / 002 / 003).
4. An optional **Cross-check second model** (local only) answers every question independently and the
   engine compares the two answers' figures.
5. The standing rule on the panel applies in every mode: *AI can err — verify against citations.*

### Step 13. Verify a number before you cite it

1. **Which file?** The line under the header names the file(s) the page is computed from, and most
   panels carry a `SOURCE: <file> · DD <data date>` chip.
2. **Which population?** If a filter banner or an `Analysis endpoint` banner is showing, the figure is
   scoped — clear it, or say so when you quote it.
3. **Which activities?** Findings and AI facts cite **file + UniqueID + task**. Cross-version matching
   is by UniqueID only (never the row id, never the name), so you can open the cited activity in the
   source schedule by its UniqueID and confirm it.
4. **Which formula?** The **Metric Dictionary** (`/help`, or
   [`docs/METRIC-DICTIONARY.md`](./docs/METRIC-DICTIONARY.md)) gives each metric's definition, formula
   and source; many table headings carry the same definition in a hover note.
5. **Is it on the known-issues list?** Check
   [Known issues before you cite a figure](#known-issues-before-you-cite-a-figure).
6. **Does it match the reference tool?** See [`docs/PARITY-REPORT.md`](./docs/PARITY-REPORT.md) (parts
   are out of date; see Step 8), and re-run the file in Acumen Fuse, SSI or MS Project when it matters.

### Step 14. Follow the CUI rules

1. Treat every loaded schedule and every derived metric as CUI unless the project is explicitly
   marked UNCLASSIFIED in AI Settings. Keep **Classification** at **CLASSIFIED (CUI — local only)**,
   the default, for CUI work, and read the export-control (ITAR / EAR) notice in the header drawer.
   The option reads "local only", but it does not stop an armed Approved AI gateway (open finding
   A0923-CUI-003).
2. Keep every AI endpoint a literal loopback address such as the default `http://127.0.0.1:11434` —
   never a host name, and never an address containing `@` (open finding A0923-CUI-001).
3. Do not choose the **Approved AI gateway (remote — …)** backend for data your organization has not
   approved for it. As built, once you select it, pick the approved endpoint and tick the
   acknowledgment, prompts are sent off this machine to that endpoint; a banner then names the
   endpoint on every page, and every transmission is recorded in a local log.
4. Exports and `.json` saves are CUI files once they are on disk: store and share them only as your
   CUI program allows.
5. **Wipe Session** before you switch to another program's schedules: it clears the loaded
   schedules, the on-disk analysis cache and the AI setting (back to off).
6. Never commit a real schedule or a reference export to this repository — see
   [Build state & where to look](#build-state--where-to-look).

### Step 15. Quit

- **Quit** in the header stops the tool at once.
- Closing the last browser window stops it within a few seconds; a tab left in the background keeps
  the session for up to 10 minutes without a heartbeat. In a terminal, `Ctrl-C` stops it.
- Loaded schedules live in memory and are gone when the tool stops, and the on-disk analysis cache is
  cleared on the way out — **Save .json** first if you want to reopen a schedule later.

### Troubleshooting

| Symptom | What to do |
|---------|------------|
| A `.mpp` fails with *Java runtime not found* | Install Java 17+ (or unzip a portable JRE into `%LOCALAPPDATA%\Programs\Microsoft`, or into a checkout's `tools/jre/`), or set `JAVA_HOME`, then restart the tool. |
| A `.mpp` fails with *MPXJ runner not found* | Re-run the installer, or point `SF_MPXJ_HOME` at a `tools/mpxj` copy; offline, see [`installer/README-DISTRIBUTABLE.md`](./installer/README-DISTRIBUTABLE.md). |
| Trend / Compare ask you to load at least two versions although you loaded several | The versions landed as separate Projects: use **Combine Projects** on **Portfolio**, or load them as one folder. |
| A very large folder comes back to an unchanged dashboard with no message | One upload is refused above 1,000 files (tracked as A0923-WEB-001): pick fewer files at a time. |
| **Save .json** fails with an error page | The loaded file's name carries characters outside ISO-8859-1, such as an en dash or a curly apostrophe (tracked as A0923-WEB-004): rename the file with plain characters and load it again. |
| The Windows Desktop icon of a pip install does nothing | Re-run `packaging\windows\Install-Desktop-Shortcut.ps1` from the activated venv — see [`packaging/README.md`](./packaging/README.md). |
| AI Settings says *Local AI is OFF* | The tool cannot reach Ollama. A launch never starts Ollama (whatever the page's hint says); saving **AI Settings** with an Ollama backend does. Choose **Backend** **Ollama (local)**, pick a **Model** you have installed, press **Save**, then wait a few seconds and reload. If it stays OFF, Ollama is not installed or listens on another port: follow [`docs/CONNECT-A-BIGGER-AI-MODEL.md`](./docs/CONNECT-A-BIGGER-AI-MODEL.md). Every page still works without the AI. |
| A figure differs from Acumen Fuse, SSI or MS Project | Check the banners and the known-issues list ([Step 13](#step-13-verify-a-number-before-you-cite-it)), then [`docs/PARITY-REPORT.md`](./docs/PARITY-REPORT.md). |

## Known issues before you cite a figure

The audit of 2026-09-23 keeps a list of **known defects an analyst must allow for** at the top of
[`docs/STATE/AUDIT-2026-09-23-OPERATOR-ASKS.md`](./docs/STATE/AUDIT-2026-09-23-OPERATOR-ASKS.md) —
the immediate-disclosure lines. Most are figures the tool gets wrong (several only on file shapes no
committed file exercises); two are AI-endpoint issues marked LAW-1. Read it before you quote a number.
Most lines say what to do until the fix lands — what to read instead, or what to check in a file
before citing it — and some name the pages affected. Rules of thumb it gives, among others:

- Read an elapsed activity's remaining work from its Duration, never from "Remaining duration".
- Do not cite the Path Analysis "Drag (d)" figure; read drag from SSI's own Directional Path export.
- Leave "Ignore constraints" / "Ignore leveling delay" off on a fully-dated file.
- With either option ticked on Driving Path or Critical-Path Evolution, do not cite the path, tiers
  or counts as a counterfactual; tick both options together and read the re-solved finish only.
- When an elapsed or 24-hour-calendar task drives the finish, read the finish from the `/path` table's
  rows or the file's own Finish — the printed CPM finish can read a day early.
- Do not cite a counterfactual that restores the duration of an activity that had already started.
- On a file saved with "Split in-progress tasks" turned off, or one that carries a started manually
  scheduled task, check the printed finish against the file's own Finish before citing it; on a file
  that declares multiple critical paths or a critical slack limit, read Critical from the file's own flag.
- Verify AI prose against the citations: a number written as a word, with a typographic minus or
  dash, as a fraction, superscript, circled or Roman numeral, or as digits split by an invisible
  character can pass the figure gates.
- Keep AI endpoints literal loopback addresses ([Step 14](#step-14-follow-the-cui-rules)).

## How this build was run

Built autonomously across sessions `A1, A2, …`, one milestone each, with all state committed to git
(never only in chat). The build spec and per-session workflow are in
[`AUTONOMOUS-BUILD-PROMPT.md`](./AUTONOMOUS-BUILD-PROMPT.md) and
[`AUTONOMOUS-BUILD-SETUP-CHECKLIST.md`](./AUTONOMOUS-BUILD-SETUP-CHECKLIST.md).

## Build state & where to look

- **`docs/STATE/HANDOFF.md`** — single source of truth for "where we are / what's next."
- `docs/STATE/SESSION-LOG.md` — append-only per-session history · `docs/STATE/LESSONS-LEARNED.md` —
  what worked, what did not, and why.
- `docs/FINAL-REPORT.md` — the finished-build summary · `docs/PARITY-REPORT.md` — how the numbers
  match Acumen Fuse v8.11.0 / SSI (parts are out of date: open findings A0923-DOC-005 / 006 / 007).
- `docs/TEST-PROJECTS.md` — the synthetic verification battery (TP1–TP4) to open in MS Project and
  run through SSI / Fuse side by side. Some of its printed expected values are out of date (open
  findings A0923-DOC-007 / 008 / 009); the values the test suite pins are in `tests/test_projects/`.
- `docs/USER-GUIDE.md` — the page-by-page reference · `docs/METRIC-DICTIONARY.md` — every metric
  (generated from the running tool's own help) · `docs/DESIGN-SYSTEM.md` — the UI rulebook.
- `docs/PLAN/` — build plan + requirements traceability (RTM) · `docs/adr/` — architecture decision
  records · `docs/risks.md` — risk register.
- `docs/STATE/AUDIT-2026-09-23-OPERATOR-ASKS.md` — the current audit's disclosure lines and the
  decisions it asks of the operator.
- `00_REFERENCE_INTAKE/` — the **non-CUI reference / golden-parity suite** (the NASA metric-library
  `.aft`, the SSI/Acumen comparison exports, and the build `.mpp` inputs), committed per ADR-0152 so
  the parity and formula-pinning tests run against real oracles. A **real CUI** production schedule is
  never committed: the pre-commit guard blocks `.mpp`/`.xlsx`/`.aft`/`.xer`/`.docx` outside the
  committed reference set and the `tests/fixtures/` synthetic allowlist. That describes an older hook
  (open finding A0923-TST-010): `.githooks/pre-commit` now blocks more names (`.xml`, `.csv` and
  disguises such as `data.mpp.bak` among them) and sniffs `.json`, `.txt`, `.md`, image, PDF and ZIP
  files for schedule content, admitting a match only under `tests/fixtures/` or
  `src/schedule_forensics/web/examples/`, or when it is byte-identical to `origin/main` at the same
  path — so a new or changed file under `00_REFERENCE_INTAKE/` is refused.
- `docs/INTAKE-MANIFEST.md` — the inventory of that committed intake.

## Quality

`ruff` + `ruff format` + `mypy --strict` + `pytest` with coverage gates (engine ≥85%, overall ≥70%),
a named parity gate, `bandit`, and `pip-audit`, all wired into CI on Python 3.11 and 3.13. The runtime
is **standard-library-only** for I/O (no `requests`/`httpx`/etc.); the only runtime dependencies are
pydantic, FastAPI, a plain uvicorn, Jinja2 and python-multipart.

The local gate, from a checkout (`pip install -e '.[dev]'` first):

```bash
ruff check .
ruff format --check .
python -m mypy src/
bandit -q -r src
python -m pytest -q
python -m pytest -m parity
```

CI also runs a `cui-guard` job that applies the repository's pre-commit hook to every pull request
and every push to `main`.
