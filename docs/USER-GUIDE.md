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
  [adoptium.net](https://adoptium.net)), then restart the tool. Java is found via `JAVA_HOME`, PATH,
  or the standard install folders (set `JAVA_HOME` for a custom location). The vendored MPXJ reader
  (`tools/mpxj/`) is auto-discovered; no Maven/build step. `.xml` (MSPDI) and `.xer` (Primavera)
  parse with no Java.
- **Local AI is optional.** The narrative works offline with the deterministic Null backend. For
  AI-polished narratives, install [Ollama](https://ollama.com) and pull a model; the in-app **AI
  Settings** panel lists/pulls/selects models. While the project is CLASSIFIED the tool only ever
  reaches a **loopback** model server — never the cloud.

## 2. Launch

- **Terminal:** `schedule-forensics`  (or `python -m schedule_forensics.launcher`)
- **Desktop icon:** use the shortcut for your OS in [`packaging/`](../packaging/README.md)
  (Linux `.desktop`, macOS `.command`, Windows `.bat`).

The launcher picks a free **127.0.0.1** port, starts the server, and opens your browser at the
dashboard. Stop it with `Ctrl-C`.

## 3. Use the dashboard

1. **Open or import** a schedule from the landing page — drag a file onto the dropzone or click
   **choose a file…** (`.json` `.xml`/`.mspdi` `.xer` `.mpp` `.mpt`, up to **10** at once), or click
   **Load example** to try the bundled sample project instantly. Files are parsed **locally**;
   nothing is uploaded anywhere. Each loaded schedule is listed with **Open report** and
   **Save .json** (exports the normalised schedule as a re-openable `.json`).
2. **Analysis** (click a schedule):
   - **DCMA-14 audit** — each of the 14 checks with pass/fail vs threshold and a plain-language
     suggested improvement; failing checks list the offending activities.
   - **Risks, opportunities & concerns** — a severity-ordered finding set (DCMA failures, baseline
     compliance, version-change signals, driving-path opportunity), **each cited (file + UID + task)**
     with a course of action.
   - **AI narrative** — a cited "story" of the schedule's health (CPM/manipulation trends, audit,
     recommendations). The model only rephrases the cited facts; it never invents a number.
   - **Interactive analysis** — charts (DCMA pass/fail, baseline compliance); an **activity grid** where
     you **add/remove columns**, sort, and **click any row to drill into its full metadata + citation**;
     and a **Gantt** that, for a **target UniqueID** you enter, highlights the **driving / secondary /
     tertiary** path to it (set the day thresholds in the controls).
3. **Compare** (with ≥2 versions loaded): a version-to-version view — CPM/progress trend and
   **manipulation-trend signals** (deleted logic, shortened durations, deleted tasks, baseline/actual
   date edits) with the **Net Finish Impact** in calendar days. Honest progress shows no false flags.
4. **AI Settings** — choose the backend (local Ollama / offline Null), list/pull/select models, and the
   project **classification**. A persistent banner names any external endpoint when UNCLASSIFIED; the
   tool **fails closed to local** otherwise.
5. **Metric Dictionary** (`/help`) — a plain-language definition + formula + source for **every** metric
   the tool emits (also in [`METRIC-DICTIONARY.md`](./METRIC-DICTIONARY.md)).
6. **Wipe Session** — clears all loaded schedules and derivatives from memory.

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
