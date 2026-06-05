# Requirements Traceability Matrix (RTM)

> **STATUS: STUB (session A1 / Phase 0).** Seeded with every §6.A–§6.G requirement (plus
> the global units rule §3 and the §7 QC/PM regime) so nothing is forgotten. Design /
> Module / Test / Parity-evidence columns are filled as Phase 2 milestones land. **Nothing
> ships until its row reads `Implemented + Tested + Validated`.**

Status legend: ☐ Not started · ◻ In progress · ▣ Implemented · ✔ Implemented + Tested +
Validated.

## Phase 1 evidence captured (design inputs — not yet implemented)
- **Metric formulas/definitions** (A5, E1): `docs/PLAN/METRICS-CATALOG.md` — DCMA-14 ribbon +
  DECM V7.0 (143 metrics) + Acumen engine + EVM indices + cost fields.
- **Acumen golden parity targets** (B2): `docs/PLAN/PARITY-TARGETS.md` — Project2 vs Project5.
- **SSI driving-slack golden + methodology** (C1/C2/C3): `docs/PLAN/SSI-DRIVING-SLACK.md` —
  focus UID 143, full driving-slack-by-UID table, thresholds.
- **Confirmed inputs** (B1/B3/units): `docs/PLAN/PARITY-INPUTS.md`. **Intake**:
  `docs/PLAN/INTAKE-MANIFEST.md`. **Setup**: `docs/PLAN/SETUP-DIRECTION.md`.
- Outstanding inputs: the two source `.mpp` (needed to *reproduce* B2/C2 numbers) and the
  `.pbix` visuals/measures (A4 reference) — both deferred to Phase 2 per SETUP-DIRECTION.

## A. Platform, UX, and packaging

| ID | Requirement | Design | Module | Test | Parity/Evidence | Status |
|----|-------------|--------|--------|------|-----------------|--------|
| A1 | All parsing/analysis/metrics/forensics implemented in Python | TBD | TBD | TBD | — | ☐ |
| A2 | Launches from a desktop icon; runs 100% locally; opens in a web browser | TBD | TBD | TBD | — | ☐ |
| A3 | Dark-mode, NASA-themed, highly intuitive UI | TBD | TBD | TBD | — | ☐ |
| A4 | Interactive Power-BI-style visuals (charts, Gantt); add/remove fields; drill into underlying metadata; viz/JS assets bundled locally (air-gapped, no CDN) | TBD | TBD | TBD | — | ☐ |
| A5 | In-tool help: plain-language definition of every metric/measure/analysis with supporting detail (UniqueID, task name, source file) | TBD | TBD | TBD | — | ☐ |

## B. Ingestion & parity (non-negotiable)

| ID | Requirement | Design | Module | Test | Parity/Evidence | Status |
|----|-------------|--------|--------|------|-----------------|--------|
| B1 | Parse/analyze up to 10 native `.mpp` at once, without converting first; access all underlying metadata | TBD | TBD (MPXJ path) | TBD | — | ☐ |
| B2 | All metrics/measures/results exactly match Acumen Fuse v8.11.0 AND the SSI add-on for the same inputs; parity suite is the acceptance gate | TBD | TBD | TBD | golden Acumen + SSI exports | ☐ |
| B3 | Cross-version matching by UniqueID only (never row ID, never name) | TBD | TBD | TBD | — | ☐ |

## C. CPM, driving slack & path tracing (SSI parity)

| ID | Requirement | Design | Module | Test | Parity/Evidence | Status |
|----|-------------|--------|--------|------|-----------------|--------|
| C1 | Critical path via forward/backward pass; total float, free float, driving slack | TBD | TBD | TBD | — | ☐ |
| C2 | User enters target UniqueID → endpoint; trace driving logic path; report Driving Slack in days per task exactly as SSI (== MS Project + SSI) | TBD | TBD | TBD | SSI driving-slack export | ☐ |
| C3 | At upload, user sets day thresholds for secondary and tertiary paths | TBD | TBD | TBD | — | ☐ |

## D. Forensic & trend analysis

| ID | Requirement | Design | Module | Test | Parity/Evidence | Status |
|----|-------------|--------|--------|------|-----------------|--------|
| D1 | Local AI "generates a story" + insights: CPM trend analysis and schedule-manipulation trends (deleted logic, shortened durations, deleted tasks protecting a target UniqueID / critical path) + other industry-standard analyses | TBD | TBD | TBD | — | ☐ |
| D2 | Every AI statement carries citations (file, UniqueID, task name) | TBD | TBD | TBD | — | ☐ |

## E. Independent audits & recommendations

| ID | Requirement | Design | Module | Test | Parity/Evidence | Status |
|----|-------------|--------|--------|------|-----------------|--------|
| E1 | Audit each schedule independently for DCMA compliance, with suggested improvements | TBD | TBD | TBD | DCMA reference | ☐ |
| E2 | Identify risks, opportunities, areas of concern — each with a suggested course of action; citations (≥ file, UniqueID, task name) | TBD | TBD | TBD | — | ☐ |

## F. Local AI backend

| ID | Requirement | Design | Module | Test | Parity/Evidence | Status |
|----|-------------|--------|--------|------|-----------------|--------|
| F1 | Ollama is the default local model | TBD | TBD | TBD | — | ☐ |
| F2 | User can download additional local models and switch active model in-app (list installed, pull new, select active) | TBD | TBD | TBD | — | ☐ |
| F3 | Sensible default model for a high-end workstation (quality may trade for performance); no cloud by default | TBD | TBD | TBD | — | ☐ |

## G. Data locality

| ID | Requirement | Design | Module | Test | Parity/Evidence | Status |
|----|-------------|--------|--------|------|-----------------|--------|
| G1 | Tool transfers no data off the machine (CUI); all compute local/offline | partly enforced via `.gitignore` + planned egress guard | TBD | egress guard test (planned) | — | ◻ |

## Global units & formatting (§3)

| ID | Requirement | Design | Module | Test | Status |
|----|-------------|--------|--------|------|--------|
| U1 | All durations expressed in `day`/`days` | TBD | TBD | TBD | ☐ |
| U2 | Percentages render with the sign (e.g. `100%`) | TBD | TBD | TBD | ☐ |
| U3 | Internal storage may use minutes; convert to days at the presentation boundary with deterministic rounding (no float drift) | TBD | TBD | TBD | ☐ |

## Cross-cutting QC/PM regime (§7)

| ID | Requirement | Status |
|----|-------------|--------|
| Q1 | TDD + pytest; coverage gates (engine ≥85%, overall ≥70%) | ☐ (pytest/coverage configured in `pyproject.toml`) |
| Q2 | ruff (lint+format), mypy (strict), bandit, pip-audit | ◻ (configured; CI wiring in Phase 2) |
| Q3 | Network-egress guard test (fails if forbidden HTTP libs import) | ☐ |
| Q4 | CI: lint+types+tests+security+parity on every push; red blocks merge | ☐ (greenfield placeholder CI present) |
| Q5 | Feature branches, Conventional Commits, draft PRs, no force-push to `main`, DoD per PR | ◻ (in effect) |
| Q6 | ADRs, risk register (`docs/risks.md`), change log | ◻ (ADRs 0000-0002 + risks.md seeded) |
| Q7 | Structured logging with CUI redaction (paths/counts/timings only) | ☐ |
| Q8 | Docs: user guide, metric dictionary (formula + citation), parity report | ☐ |
