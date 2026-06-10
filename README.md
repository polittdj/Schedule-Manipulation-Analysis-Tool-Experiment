# Schedule Manipulation Analysis Tool

> **Status: built (M1–M17 complete; M15 `.pbix` export is the one deferred item).** The tool runs
> end-to-end: ingest → CPM/forensic analysis → interactive, locally-rendered report → cited local-AI
> narrative. Current state always lives in [`docs/STATE/HANDOFF.md`](./docs/STATE/HANDOFF.md); the
> finished-build summary is in [`docs/FINAL-REPORT.md`](./docs/FINAL-REPORT.md).

A local, NASA-themed **forensic schedule-analysis** desktop tool. It ingests native Microsoft
Project / Primavera schedules, runs comparative and forensic analysis (CPM / driving slack, DCMA-14,
Acumen Fuse v8.11.0 & SSI parity metrics, EVM, manipulation-trend detection), and produces
interactive, locally-rendered reports with a cited local-AI narrative — **entirely on your machine**.
Nothing about a schedule ever leaves the box.

## The two laws

1. **Data sovereignty (CUI).** No schedule data, file content, task name, date, UniqueID, or derived
   metric ever leaves the local machine. No cloud API call ever receives schedule content. The AI
   defaults to local Ollama and fails closed when in doubt. A network-egress guard fails the build if
   any forbidden cloud HTTP client enters the runtime, and an air-gap test fails if any served page
   references a remote asset.
2. **Fidelity over speed.** Numbers must match the reference tools (Acumen Fuse v8.11.0, SSI,
   Microsoft Project) on the same inputs. A fast, wrong number is worthless in a forensic/testimony
   context. Parity is gate-locked (`pytest -m parity`).

## Install

```bash
python -m venv .venv
. .venv/bin/activate            # Windows: .venv\Scripts\Activate.ps1
pip install -e .                # installs the `schedule-forensics` launcher command
```

- **Python 3.11+** required. Native **`.mpp`** ingestion also needs a **Java runtime (JRE/JDK 17+)** —
  Windows: `winget install EclipseAdoptium.Temurin.21.JRE` (or [adoptium.net](https://adoptium.net)),
  then restart the tool. **No admin rights?** Extract a portable JRE *zip* from adoptium.net into the
  repo's `tools/jre/` folder — no installer, no elevation, no configuration. Java is found via
  `SF_JAVA`/`JAVA_HOME`, PATH, `tools/jre/`, or the standard install folders. The vendored MPXJ
  reader (`tools/mpxj/`) is auto-discovered (no Maven/build step). `.xml` (MSPDI), `.xer`
  (Primavera) and the tool's own `.json` parse with no Java.
- **Local AI is optional.** The narrative works offline with the deterministic Null backend; for
  AI-polished prose, install [Ollama](https://ollama.com) and pull a model (the in-app **AI Settings**
  panel lists/pulls/selects models). While CLASSIFIED the tool only ever reaches a loopback model
  server.

## Launch

- **Terminal:** `schedule-forensics` (or `python -m schedule_forensics.launcher`).
- **Desktop shortcut:** use the one for your OS in [`packaging/`](./packaging/README.md) (Windows
  `.ps1` installer, Linux `.desktop`, macOS `.command`).

The launcher picks a free **127.0.0.1** port, starts the server, and opens your browser at the
dashboard. **Closing the last browser window turns the tool off** (the server's watchdog stops it when
the heartbeat stops); the in-page **Quit** control stops it immediately.

## Use

1. **Open or import** on the landing page — drag a file onto the dropzone or click **choose a file…**
   (`.json` / `.xml` / `.mspdi` / `.xer` / `.mpp` / `.mpt`, up to 10 at once), or **Load example** for
   the bundled sample. Files parse locally; the dashboard tells you exactly what loaded and what
   failed (no silent failures). Each schedule lists **Open report** and **Save .json**.
2. **Analysis** — DCMA-14 audit (pass/fail vs threshold + suggested fix), severity-ordered
   risks/opportunities/concerns (each cited: file + UniqueID + task), a cited AI narrative, and
   interactive charts + an activity grid + a driving-path Gantt.
3. **Compare** (≥2 versions) — CPM/progress trend and manipulation-trend signals (deleted logic,
   shortened durations, deleted tasks, baseline/actual edits) with the Net Finish Impact in calendar
   days. Honest progress raises no false flags.

See [`docs/USER-GUIDE.md`](./docs/USER-GUIDE.md) for the full walkthrough and
[`docs/METRIC-DICTIONARY.md`](./docs/METRIC-DICTIONARY.md) (also at `/help`) for a definition + formula
+ source for every metric the tool emits.

## How this build was run

Built autonomously across sessions `A1, A2, …`, one milestone each, with all state committed to git
(never only in chat). The build spec and per-session workflow are in
[`AUTONOMOUS-BUILD-PROMPT.md`](./AUTONOMOUS-BUILD-PROMPT.md) and
[`AUTONOMOUS-BUILD-SETUP-CHECKLIST.md`](./AUTONOMOUS-BUILD-SETUP-CHECKLIST.md).

## Build state & where to look

- **`docs/STATE/HANDOFF.md`** — single source of truth for "where we are / what's next."
- `docs/STATE/SESSION-LOG.md` — append-only per-session history.
- `docs/FINAL-REPORT.md` — the finished-build summary · `docs/PARITY-REPORT.md` — how the numbers
  match Acumen Fuse v8.11.0 / SSI.
- `docs/PLAN/` — build plan + requirements traceability (RTM) · `docs/adr/` — architecture decision
  records · `docs/risks.md` — risk register.
- `00_REFERENCE_INTAKE/DEPOSIT-HERE.md` — where reference / golden-parity files go (git-ignored, CUI
  defense).

## Quality

`ruff` + `ruff format` + `mypy --strict` + `pytest` with coverage gates (engine ≥85%, overall ≥70%),
a named parity gate, `bandit`, and `pip-audit`, all wired into CI on Python 3.11 and 3.13. The runtime
is **standard-library-only** for I/O (no `requests`/`httpx`/etc.); the only runtime dependencies are
pydantic, FastAPI, a plain uvicorn, Jinja2 and python-multipart.
