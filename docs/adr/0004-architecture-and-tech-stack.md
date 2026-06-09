# ADR-0004: Application architecture & technology stack

- **Status:** Accepted
- **Date:** 2026-06-05 (session A2 — Phase 2 plan)
- **Relates to:** §6.A (Python, local web UI, interactive viz), §6.B (native `.mpp`), §6.F (Ollama),
  §6.G (data locality)

## Context
We need a local, offline, NASA-themed forensic schedule tool: Python engine, browser UI with
Power-BI-style interactive visuals (air-gapped assets), native `.mpp` ingestion to exact Acumen/
SSI parity, and a local-AI narrative. The prior build (PR #47, head `0324ba4`) is a working
reference (pydantic + Flask + MPXJ + pluggable inference, 42 tests) — study, don't lift wholesale.

## Decision
**Layers (clean dependency direction: ui → services → engine → model → importers):**
- **Language:** Python **3.11** (matches the build container + CI matrix; ADR-context: env verified).
- **Domain model:** **pydantic v2**, frozen/strict, **UniqueID-keyed**. Internal durations in
  **minutes**; convert to **days** only at the presentation boundary with deterministic rounding
  (§3). Percentages formatted with a sign.
- **Ingestion:** vendored **MPXJ 16.2.0 subprocess** (`MpxjToMspdi`: native `.mpp`/`.mpx`/`.xer` →
  MSPDI XML) → **pure-Python MSPDI importer**; plus a pure-Python **XER** importer; optional
  Windows **COM** cross-check. Up to **10 files** at once. All metadata retained.
- **Engine (pure Python, deterministic, no I/O):** CPM forward/backward pass; total/free float;
  **driving slack + path tracing to a target UID** (SSI parity); metric catalog (DCMA-14 + Acumen
  Schedule Quality + EVM indices; DECM V7.0 as extended); version diff + manipulation-trend
  detection.
- **Parity harness:** golden fixtures + parametrized tests as the **acceptance gate** (ADR-0005).
- **Local AI:** pluggable backend — **Null** (deterministic template) and **Ollama** (default,
  local `127.0.0.1:11434`); a cloud backend exists **only** when a project is explicitly toggled
  "unclassified," behind a persistent banner. In-app list/pull/switch. Every AI sentence carries
  citations (file + UniqueID + task name), enforced in code.
- **Web UI:** **FastAPI + Uvicorn** (typed, local, serves API + static) with **Jinja2** templates
  and **HTMX** for interactivity; **dark NASA theme** CSS. **Interactive viz:** **ECharts**
  (charts + custom Gantt) and **Tabulator** (interactive tables, field add/remove, drill-to-
  metadata) — **vendored locally** (no CDN). Bundling via the available Node 22 only at build time;
  shipped assets are static files.
- **Reports (optional):** openpyxl / python-docx for Excel/Word exports.
- **Desktop launcher:** entry-point script starts Uvicorn on localhost and opens the default
  browser; shipped with an OS shortcut (`.bat` / `.desktop` / `.command`).

## Alternatives considered
- **Flask (prior build) vs FastAPI** → FastAPI for typing/OpenAPI/async; Flask was viable.
- **Plotly.js vs ECharts** → ECharts (smaller single-file bundle, strong Gantt/customisation, MIT);
  Plotly also fine. Either is air-gappable.
- **Full SPA (React) vs server-rendered + HTMX** → HTMX keeps the build chain tiny and air-gapped
  while still giving interactive drill-down; avoids a heavy JS toolchain for a single-user local app.

## Consequences
- All compute is local; no network egress by default (§6.G) — enforced by an egress-guard test.
- The MSPDI seam lets the engine/tests run on synthetic fixtures without a JVM; native `.mpp` adds
  only the MPXJ subprocess.
- ECharts/Tabulator vendored → air-gapped; Node is a build-time-only dependency.
