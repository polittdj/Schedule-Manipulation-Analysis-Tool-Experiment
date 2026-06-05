# BUILD-PLAN — Schedule Manipulation Analysis Tool

> **STATUS: STUB (session A1 / Phase 0).** The authoritative architecture and the
> final, ordered, session-sized milestone list are produced in the **Phase 2 "Plan
> session"** (after Gate 1 + Gate 2). The milestone outline below is **provisional** —
> it exists only to orient future sessions and will be replaced/refined in Phase 2.

## Purpose

A local, offline, NASA-themed forensic schedule-analysis desktop tool. Ingests native
MS Project / Primavera schedules, computes CPM / driving-slack and a full metric set to
**exact parity** with Acumen Fuse v8.11.0 and the SSI MS Project add-on, audits each
schedule (DCMA), detects schedule-manipulation trends, and produces interactive,
locally-rendered reports with a local-AI narrative — with every number and sentence
**cited** (file + UniqueID + task name). See `AUTONOMOUS-BUILD-PROMPT.md` §6.A–§6.G for
the binding requirements and `docs/PLAN/RTM.md` for traceability.

## Architecture (high level — to be detailed in Phase 2)

```
ingest (native .mpp via vendored MPXJ→MSPDI; pure-Python MSPDI/XER; optional COM)
  → typed schedule model (immutable, UniqueID-keyed)
    → engine: CPM (fwd/bwd pass), float (total/free), driving slack, path tracing
    → metrics: full Acumen-parity catalog + EVM (SPI/SPI(t)/BEI/CEI) + DCMA-14
    → compare/trend: version diff (UniqueID-only), manipulation-trend detection
      → parity harness (golden Acumen v8.11.0 + SSI exports = acceptance gate)
      → local-AI narrative (Ollama default; cited statements only)
        → local web UI (dark, NASA theme, Power-BI-style interactive viz, in-tool help)
          → desktop launcher (one click → local browser; air-gapped assets)
```

> **Reference, do not copy:** a prior implementation exists in git history (PR #47, head
> `0324ba4`) with a similar module layout (CPM, DCMA, EVM, SRA, parity, trends, Flask UI,
> pluggable Null/Ollama/Unclassified inference). It is a **reference** for approach and
> pitfalls (see its `docs/HAZARDS.md`), not a source to lift wholesale. Phase 2 decides
> what to reuse vs. rebuild, per the prompt's "rebuild from the prompt" intent.

## Provisional milestone outline (replace in Phase 2)

Each milestone = one session, scoped to finish with margin (§2.2). Indicative only:

- **M0 — Engine foundations:** typed schedule model + ingest of synthetic MSPDI/XER
  fixtures; project skeleton, real CI (ruff/mypy/pytest/bandit/pip-audit + egress guard).
- **M1 — Native `.mpp` ingest:** wire vendored MPXJ subprocess path; multi-file (≤10)
  load; full-metadata access; UniqueID keying.
- **M2 — CPM core:** forward/backward pass, total float, free float (synthetic parity).
- **M3 — Driving slack + path tracing (SSI parity):** target-UniqueID endpoint, driving
  logic path, Driving Slack in days; secondary/tertiary thresholds at upload.
- **M4 — Metric catalog (Acumen parity):** implement the Acumen Fuse v8.11.0 metric
  library to exact parity; metric dictionary (formula + citation).
- **M5 — Parity suite:** golden Acumen + SSI exports as the acceptance gate; drive deltas
  to zero (or document with citations).
- **M6 — DCMA audit + recommendations:** independent per-schedule DCMA-14 with suggested
  improvements; risks/opportunities/concerns with citations.
- **M7 — Forensic & trend analysis:** version diff + manipulation-trend detection
  (deleted logic, shortened durations, deleted tasks protecting a target/critical path).
- **M8 — Local AI backend:** Ollama default; in-app model list/pull/switch; cited
  narrative; fail-closed CUI routing + "unclassified" banner path.
- **M9 — Web UI + interactive viz:** dark NASA theme, Power-BI-style charts/Gantt with
  field add/remove + drill-to-metadata; in-tool help; locally bundled assets.
- **M10 — Desktop launcher + packaging:** one-click local launch into the browser.
- **M11 — Docs + final report:** user guide, metric dictionary, parity report, final RTM
  evidence map. HANDOFF → DONE.

(Counts/order are provisional; Phase 2 will split/merge to keep each session in budget.)

## Cross-cutting (applies to every milestone — §7)

TDD + pytest (engine ≥85%, overall ≥70% coverage); ruff (lint+format), mypy (strict),
bandit, pip-audit; **network-egress guard test**; CI red blocks merge; Conventional
Commits + draft PRs; ADRs + `docs/risks.md` + change log; structured logging with CUI
redaction; durable state in `docs/STATE/` + `docs/PLAN/`.
