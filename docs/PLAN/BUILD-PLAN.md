# BUILD-PLAN — Schedule Manipulation Analysis Tool

> **Phase 2 plan (session A2).** Full architecture + ordered, session-sized milestones. Design
> decisions in `docs/adr/0004` (stack) and `0005` (parity). Requirement traceability in
> `docs/PLAN/RTM.md`. Design inputs already captured: `METRICS-CATALOG.md`, `PARITY-TARGETS.md`,
> `SSI-DRIVING-SLACK.md`, `PARITY-INPUTS.md`, `INTAKE-MANIFEST.md`, `SETUP-DIRECTION.md`.

## Purpose
A local, offline, NASA-themed forensic schedule-analysis tool. Ingests native MS Project /
Primavera schedules (≤10 at once), computes CPM / driving-slack and a full metric set to **exact
parity** with **Acumen Fuse v8.11.0** and the **SSI** MS Project add-on, audits each schedule
(DCMA-14), detects schedule-manipulation trends, and renders interactive, locally-bundled visuals
with a **local-AI** narrative — every number and sentence **cited** (file + UniqueID + task name).
The two laws: **(1) data sovereignty (CUI runtime)** and **(2) fidelity over speed.**

## Architecture (see ADR-0004)
```
                         ┌──────────────────────────────────────────────┐
 desktop launcher  ──▶   │  web UI  (FastAPI + Uvicorn, Jinja2 + HTMX)    │
 (opens browser)         │  dark NASA theme · ECharts + Tabulator (local)│
                         └───────────────┬──────────────────────────────┘
                                         │ services (orchestration, sessions, citations)
                         ┌───────────────▼──────────────────────────────┐
                         │  engine (pure Python, deterministic)          │
                         │   cpm · float · driving_slack/path_trace ·    │
                         │   metrics (DCMA-14 + Acumen SQ + EVM + DECM) · │
                         │   diff · manipulation-trends · dcma_audit      │
                         └───────────────┬──────────────────────────────┘
                         ┌───────────────▼──────────────────────────────┐
                         │  domain model  (pydantic v2, frozen, UID-key) │
                         │  minutes internal → days at presentation      │
                         └───────────────┬──────────────────────────────┘
                         ┌───────────────▼──────────────────────────────┐
                         │  importers: MSPDI · XER · MPXJ(.mpp→MSPDI) ·  │
                         │             COM(optional, Windows)            │
                         └───────────────────────────────────────────────┘
   local AI (pluggable):  Null | Ollama(default) | Unclassified-cloud(toggle+banner)
   parity harness:        tests/parity vs golden fixtures (acceptance gate, ADR-0005)
```

## Planned package layout (`src/schedule_forensics/`)
- `model/` — `schedule.py`, `task.py`, `relationship.py`, `resource.py`, `calendar.py`, `units.py`
  (minutes↔days, percent formatting).
- `importers/` — `mspdi.py`, `xer.py`, `mpp_mpxj.py` (subprocess wrapper), `com_msproject.py` (opt),
  `loader.py` (multi-file ≤10, UID keying).
- `engine/` — `cpm.py`, `float_analysis.py`, `driving_slack.py`, `path_trace.py`,
  `metrics/` (`dcma14.py`, `schedule_quality.py`, `evm.py`, `decm.py`), `diff.py`,
  `manipulation.py`, `dcma_audit.py`, `recommendations.py`.
- `ai/` — `backend.py` (interface), `null.py`, `ollama.py`, `unclassified.py`, `narrative.py`,
  `citations.py` (enforce file+UID+task on every statement).
- `web/` — `app.py` (FastAPI), `routes/`, `templates/`, `static/` (vendored ECharts/Tabulator + CSS),
  `help.py` (metric dictionary).
- `reports/` — `excel.py`, `word.py` (optional exports).
- `launcher.py` — start Uvicorn + open browser.
- `logging_redaction.py` — structured logs, CUI-redacted (paths/counts/timings only).
- `net_guard.py` — import-time guard; the egress test asserts no forbidden HTTP client is importable
  in CUI mode.

## Ordered milestones (one session each; TDD; stop with margin)
Each milestone: start-of-session ritual → implement with TDD → lint/types/tests/security (+parity
where noted) → update RTM → end-of-session ritual. Parity milestones are **hard gates**. Milestones
may be split further if a session can't finish with margin.

| ID | Milestone | Key acceptance criteria |
|----|-----------|-------------------------|
| **M1** | **Project skeleton + real CI + quality gates + egress guard** | Real package layout; `.claude/settings.json` (curated allowlist); pre-commit hook (block schedule/Office/pickle) + SessionStart hook (verify py/jdk/ollama); replace placeholder CI with **ruff + mypy(strict) + pytest + bandit + pip-audit**; `net_guard` + **egress-guard test** (fails if a forbidden HTTP lib imports); structured CUI-redacted logging. CI green. |
| **M2** | **Domain model + units** | pydantic v2 frozen models (Schedule/Task/Relationship/Resource/Calendar), UID-keyed; `units.py` minutes↔**days** deterministic rounding + signed-percent formatting. ≥90% unit cov on model/units. |
| **M3** | **MSPDI + XER importers (synthetic)** | Parse synthetic MSPDI XML + XER into the model; all metadata accessible; UID keys. Field-coverage tests on hand-authored fixtures. |
| **M4** | **Native `.mpp` ingest via MPXJ + multi-file (≤10)** | `Project2.mpp` + `Project5.mpp` → MSPDI → model; **144 activities, UID 2–145** each; load ≤10 at once; metadata intact; (COM path stubbed/xfail off-Windows). Commit MSPDI conversions as golden fixtures (ADR-0005). |
| **M5** | **CPM: forward/backward pass + total/free float** | Constraints (SNET/FNET/MSO/MFO/SNLT/FNLT) + calendars honored. Synthetic CPM parity; sanity vs Acumen "Critical" counts (P2 41 / P5 37). |
| **M6** | **Driving slack + path trace to target UID** ⛳ **SSI parity gate** | User enters target UID → endpoint; trace driving logic path; **Driving Slack in days per task == SSI** for `Project5`/UID **143** (reproduce `SSI-DRIVING-SLACK.md` table exactly). User-set secondary (>0 ≤10d) / tertiary (>10 ≤20d) thresholds at upload. |
| **M7** | **Acumen metric catalog: Schedule Quality + DCMA-14** ⛳ **Acumen parity gate** | Reproduce `PARITY-TARGETS.md §A/§B` for Project2 & Project5 exactly: Schedule-Quality summary (score 88) and DCMA-14 ribbon (**score 57/49, BEI 0.74/0.59, Missed 18/37, CPLI, High Float, Logic, Lags…**). |
| **M8** | **EVM indices + baseline/half-step-delay + change (SN) metrics** ⛳ **parity** | SPI/SPI(t)/CPI/BEI/CPLI/CEI/TCPI; baseline compliance + HSD (`PARITY-TARGETS §C`); Schedule-Network change metrics (`§E`). Match exactly (incl. Net Finish Impact −99d). |
| **M9** | **Parity suite + golden fixtures (acceptance gate)** | `tests/parity/` parametrized over the committed golden fixtures (ADR-0005); UID-only matching; full suite green; any residual delta documented w/ citations and driven to zero. |
| **M10** | **DCMA audit + recommendations (per schedule)** | Independent DCMA-14 audit per file with suggested improvements; risks/opportunities/concerns each with a course of action; **every item cites file+UID+task**. |
| **M11** | **Version diff + manipulation-trend detection (forensic)** | UID-only diff Project2→Project5; detect deleted logic, shortened durations, deleted tasks, **baseline-date changes (29I401a)**, **actual-date changes (06A504*)**; CPM trend. Detect the known P2→P5 signals (slips, Missed 18→37, float erosion) with citations. |
| **M12** | **Local AI backend (Ollama) + cited narrative** | Pluggable Null/Ollama; in-app **list/pull/select** model; "generate a story" + insights; **every sentence cited** (enforced in `citations.py`); CUI fail-closed routing + persistent unclassified banner; egress guard holds. |
| **M13** | **Web UI shell + dark NASA theme + settings + in-tool help** | FastAPI app; upload ≤10 `.mpp`; dashboard; model settings panel; **metric dictionary** (plain-language + formula + citation for every metric/measure/analysis); session wipe. Local-only. |
| **M14** | **Interactive Power-BI-style visuals (charts, Gantt, drill-down)** | Vendored ECharts + Tabulator (no CDN); add/remove fields; **drill into underlying metadata of any data point**; Gantt highlighting driving/secondary/tertiary paths to the target UID. Air-gap test (no external URLs). |
| **M15** | **`.pbix` reference + visual/metric enrichment** | Parse `NSATDeploymentRevisionAlpha.pbix` locally (unzip → DataModel + Report/Layout); fold its extra metrics/example visuals into the dashboard (improve on them). |
| **M16** | **Desktop launcher + packaging** | One-click desktop icon → starts local server → opens browser; OS shortcut; offline. |
| **M17** | **Docs + final report + RTM closeout** | User guide; metric dictionary (formula+citation); parity report (computed vs golden, deltas=0); final report mapping every §6 requirement → evidence. **HANDOFF → DONE.** All RTM rows ✔. |

*Provisional count = 17; the planner may split M7/M8 or M13/M14 if a session can't finish with
margin. M1–M9 are the fidelity core (gate the rest); M10–M12 the forensic/AI value; M13–M17 the
product surface.*

## Dependencies / sequencing
- Hard order: **M1 → M2 → M3 → M4** (foundation), then **M5 → M6/M7/M8 → M9** (engine + parity
  gates), then **M10, M11, M12** (forensic/AI), then **M13 → M14 → M15** (UI), then **M16 → M17**.
- M6 (SSI) and M7/M8 (Acumen) are independent of each other after M5; M9 consolidates them.
- The UI (M13+) can begin once M5–M8 produce real numbers, but is scheduled after the parity gate
  so visuals never display unverified figures.

## Cross-cutting (every milestone — §7 QC/PM)
- **TDD + pytest**; coverage gates: **engine ≥ 85%, overall ≥ 70%** (enforced in CI from M1).
- **ruff** (lint+format), **mypy** (strict), **bandit**, **pip-audit** on every push; **egress-guard
  test**; CI red blocks merge.
- **Conventional Commits**, feature branch (`claude/intelligent-fermat-3MBqk`), **draft PRs**, no
  force-push to `main`, per-PR Definition-of-Done checklist.
- **ADRs**, `docs/risks.md`, change log; **structured logging with CUI redaction** (paths/counts/
  timings only).
- **Citations everywhere:** every metric/finding/AI sentence carries ≥ file + UniqueID + task name.
- **Durable state** updated each session (`HANDOFF.md`, `SESSION-LOG.md`, `RTM.md`).

## Global rules (restated)
- **Units (§3):** durations in `day`/`days`; percentages with a sign; minutes internal → days at the
  boundary with deterministic rounding (no float drift).
- **Matching (§6.B):** by **UniqueID only** — never row ID, never name.
- **CUI (§0, §6.G):** shipped tool transfers nothing off-machine; local Ollama default; cloud only
  on explicit "unclassified" toggle behind a persistent endpoint banner; fail closed.
- **Reference policy:** prior build (PR #47, `0324ba4`) and the deposited references are **study-only**
  inputs; reproduce behavior, don't lift code wholesale. Golden fixtures are non-CUI sample data.

## Definition of Done (§8)
Every §6.A–§6.G RTM row = `Implemented + Tested + Validated`; parity suite matches Acumen v8.11.0 +
SSI exactly (deltas = 0 or documented + driven to zero); CI green; desktop launcher starts the local
web UI; docs complete (user guide, metric dictionary, parity report, final report); `HANDOFF.md`
reads `DONE`; draft PR presented (not merged).
