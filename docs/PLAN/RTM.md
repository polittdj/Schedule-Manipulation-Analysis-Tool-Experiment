# Requirements Traceability Matrix (RTM)

Every §6.A–§6.G requirement (plus units §3 and the §7 QC/PM regime) → design/module → test →
parity evidence → delivering milestone → status. **Nothing ships until its row reads `✔`**
(`Implemented + Tested + Validated`). Milestones (M*) are defined in `BUILD-PLAN.md`.

Status: ☐ Not started · ◻ In progress / inputs ready · ▣ Implemented · ✔ Implemented+Tested+Validated.

## Phase 1 evidence captured (design inputs — not yet implemented)
- Metrics/formulas (A5, E1): `METRICS-CATALOG.md` · Acumen golden (B2): `PARITY-TARGETS.md` ·
  SSI driving slack (C1/C2/C3): `SSI-DRIVING-SLACK.md` · inputs (B1/B3/units): `PARITY-INPUTS.md` ·
  intake: `INTAKE-MANIFEST.md` · setup: `SETUP-DIRECTION.md`. Architecture: ADR-0004/0005.

## A. Platform, UX, packaging
| ID | Requirement | Design / module | Test | Evidence | M | Status |
|----|-------------|-----------------|------|----------|---|--------|
| A1 | All parsing/analysis/metrics/forensics in Python | whole `src/` (engine pure Python) | CI builds/runs | — | M1+ | ◻ stack chosen |
| A2 | Desktop icon → 100% local → opens in browser | `launcher.py`, `web/app.py` | launch smoke test | — | M16,M13 | ☐ |
| A3 | Dark-mode, NASA-themed, intuitive UI | `web/templates`,`web/static` theme | UI smoke/snapshot | — | M13 | ☐ |
| A4 | Interactive Power-BI-style viz; add/remove fields; drill into metadata; local assets (no CDN) | `web/static` ECharts+Tabulator | air-gap test + interaction test | — | M14 | ☐ |
| A5 | In-tool help: every metric/measure/analysis defined w/ supporting detail (UID, task, file) | `web/help.py` + catalog | help-coverage test (all metrics defined+cited) | `METRICS-CATALOG.md` | M13 | ◻ catalog ready |

## B. Ingestion & parity (non-negotiable)
| ID | Requirement | Design / module | Test | Evidence | M | Status |
|----|-------------|-----------------|------|----------|---|--------|
| B1 | Parse ≤10 native `.mpp` at once, no conversion, all metadata | `importers/mpp_mpxj.py`,`loader.py` | Project2/5 parse: 144 acts, UID 2–145; ≤10 load | `INTAKE-MANIFEST.md` | M4 | ◻ toolchain verified (JDK21+MPXJ) |
| B2 | Exact match to **Acumen v8.11.0** AND **SSI**; parity suite = gate | `engine/metrics/*`, `tests/parity` | parity suite (UID-keyed) | `PARITY-TARGETS.md`,`SSI-DRIVING-SLACK.md` | M6,M7,M8,M9 | ◻ targets captured |
| B3 | Cross-version matching by **UniqueID only** | `model` UID key, `engine/diff.py` | diff test asserts UID-only | — | M4,M11 | ☐ |

## C. CPM, driving slack & path tracing (SSI parity)
| ID | Requirement | Design / module | Test | Evidence | M | Status |
|----|-------------|-----------------|------|----------|---|--------|
| C1 | Critical path fwd/bwd pass; total float, free float, driving slack | `engine/cpm.py`,`float_analysis.py`,`driving_slack.py` | synthetic CPM + float parity | — | M5,M6 | ☐ |
| C2 | Target UID endpoint → trace driving path → Driving Slack in days == MSP+SSI | `engine/path_trace.py`,`driving_slack.py` | **SSI parity test (Project5/UID 143)** | `SSI-DRIVING-SLACK.md` | M6 | ◻ golden captured |
| C3 | User sets secondary/tertiary day-thresholds at upload | `web` upload form + engine params | threshold-classification test | `PARITY-INPUTS.md` (>0≤10 / >10≤20) | M6,M13 | ◻ defaults captured |

## D. Forensic & trend analysis
| ID | Requirement | Design / module | Test | Evidence | M | Status |
|----|-------------|-----------------|------|----------|---|--------|
| D1 | Local AI story + CPM trend + manipulation trends (deleted logic/shortened durations/deleted tasks) + industry analyses | `ai/narrative.py`,`engine/manipulation.py`,`diff.py` | manipulation-detection tests (P2→P5) | `PARITY-TARGETS §F` deltas | M11,M12 | ☐ |
| D2 | Every AI statement cited (file, UID, task) | `ai/citations.py` | citation-enforcement test (fail if uncited) | — | M12 | ☐ |

## E. Independent audits & recommendations
| ID | Requirement | Design / module | Test | Evidence | M | Status |
|----|-------------|-----------------|------|----------|---|--------|
| E1 | Independent DCMA compliance audit per schedule + suggested improvements | `engine/dcma_audit.py` | DCMA audit parity test | `PARITY-TARGETS §B`,`METRICS-CATALOG §1/§2` | M10 | ◻ formulas ready |
| E2 | Risks/opportunities/concerns each w/ course of action + citations | `engine/recommendations.py` | recommendation tests w/ citations | — | M10 | ☐ |

## F. Local AI backend
| ID | Requirement | Design / module | Test | Evidence | M | Status |
|----|-------------|-----------------|------|----------|---|--------|
| F1 | Ollama default local model | `ai/ollama.py`,`ai/backend.py` | backend-selection test | — | M12 | ☐ |
| F2 | Download + switch models in-app (list/pull/select) | `web` settings + `ai` backend | settings/model-switch test | — | M12,M13 | ☐ |
| F3 | Sensible default model; no cloud by default | `ai` config | default-model + no-cloud test | `SETUP-DIRECTION §6` | M12 | ☐ |

## G. Data locality
| ID | Requirement | Design / module | Test | Evidence | M | Status |
|----|-------------|-----------------|------|----------|---|--------|
| G1 | No data off-machine; all compute local/offline | `net_guard.py`, `ai` routing, `.gitignore` | **egress-guard test** | — | M1,M12 | ◻ `.gitignore` in place; guard pending |

## Global units & formatting (§3)
| ID | Requirement | Module | Test | M | Status |
|----|-------------|--------|------|---|--------|
| U1 | Durations in `day`/`days` | `model/units.py` | unit-render test | M2 | ☐ |
| U2 | Percentages with a sign | `model/units.py` | percent-format test | M2 | ☐ |
| U3 | Minutes internal → days deterministic rounding (no float drift) | `model/units.py` | rounding/no-drift test | M2 | ☐ |

## Cross-cutting QC/PM (§7)
| ID | Requirement | Evidence | M | Status |
|----|-------------|----------|---|--------|
| Q1 | TDD + pytest; coverage (engine ≥85%, overall ≥70%) | `pyproject.toml` configured | M1 | ◻ configured |
| Q2 | ruff + mypy(strict) + bandit + pip-audit | `pyproject.toml` configured | M1 | ◻ configured |
| Q3 | Network-egress guard test | `net_guard.py` + test | M1 | ☐ |
| Q4 | CI: lint+types+tests+security+parity; red blocks merge | `.github/workflows/ci.yml` (placeholder now) | M1 | ◻ placeholder |
| Q5 | Branches, Conventional Commits, draft PRs, no force-push, DoD | this branch + PR #51 | all | ◻ in effect |
| Q6 | ADRs, risk register, change log | ADR 0000–0005, `docs/risks.md` | all | ◻ in effect |
| Q7 | Structured logging w/ CUI redaction | `logging_redaction.py` | M1 | ☐ |
| Q8 | Docs: user guide, metric dictionary, parity report | `METRICS-CATALOG.md` + M17 | M17 | ◻ catalog ready |
