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
| A1 | All parsing/analysis/metrics/forensics in Python | whole `src/` (engine pure Python) | CI builds/runs | `tests/test_smoke.py` | M1+ | ▣ skeleton+CI in Python (M1) |
| A2 | Desktop icon → 100% local → opens in browser | `launcher.py`, `web/app.py` | launch smoke test | — | M16,M13 | ☐ |
| A3 | Dark-mode, NASA-themed, intuitive UI | `web/templates`,`web/static` theme | UI smoke/snapshot | — | M13 | ☐ |
| A4 | Interactive Power-BI-style viz; add/remove fields; drill into metadata; local assets (no CDN) | `web/static` ECharts+Tabulator | air-gap test + interaction test | — | M14 | ☐ |
| A5 | In-tool help: every metric/measure/analysis defined w/ supporting detail (UID, task, file) | `web/help.py` + catalog | help-coverage test (all metrics defined+cited) | `METRICS-CATALOG.md` | M13 | ◻ catalog ready |

## B. Ingestion & parity (non-negotiable)
| ID | Requirement | Design / module | Test | Evidence | M | Status |
|----|-------------|-----------------|------|----------|---|--------|
| B1 | Parse ≤10 native `.mpp` at once, no conversion, all metadata | `importers/{mspdi,xer,_common}.py` (M3); `importers/{mpp_mpxj,loader}.py` (M4) | Project2/5 parse: 144 acts, UID 2–145; ≤10 load | `tests/importers/*`; golden `tests/fixtures/golden/project2_5/` | M3,M4 | ✔ **M4: native `.mpp` via out-of-process MPXJ + ≤10 loader; Project2/5 → 144 acts UID 2–145 validated on the real uploads; distilled MSPDI committed as golden inputs; importers 100% cov.** (Field-value parity vs Acumen/SSI = B2, M6–M9.) |
| B2 | Exact match to **Acumen v8.11.0** AND **SSI**; parity suite = gate | `engine/metrics/*`, `engine/driving_slack.py`, **`tests/parity/test_parity_gate.py`** | **parity gate (UID-keyed, `pytest -m parity`, CI step)** | `tests/fixtures/golden/{ssi_uid143,project2_5}/case.json` | M6,M7,M8,M9 | ✔ **M9: consolidated parity acceptance gate live + CI-wired.** Exact: SSI 107/107; Acumen §A; §B 13/14; §C counts+BFC; §E Added/New-Critical/Finish-Slips(9)/Completed/In-Progress + Net Finish Impact −99. Residuals **formally accepted + locked** (probe: neither pure-CPM nor stored-MSP reproduces them — ADR-0014): High Float +1, BSC %, SN04/06/07/09. Composite scores deferred (Acumen weighting unpublished; counts exact) |
| B3 | Cross-version matching by **UniqueID only** | `model` UID key, `importers/*` (M3/M4), `engine/diff.py` (M11) | `tests/engine/test_diff.py` (UID-only added/deleted/changed) | `model/schedule.py` (UID-keyed); P2/P5 same UID set | M2,M3,M4,M11 | ✔ **M11: `diff_versions` matches strictly by UniqueID (summaries excluded); P2→P5 added/deleted = 0, 106 changed by UID — never row id/name.** |

## C. CPM, driving slack & path tracing (SSI parity)
| ID | Requirement | Design / module | Test | Evidence | M | Status |
|----|-------------|-----------------|------|----------|---|--------|
| C1 | Critical path fwd/bwd pass; total float, free float, driving slack | `engine/cpm.py`,`float_analysis.py` (M5); `driving_slack.py` (M6) | synthetic CPM + float parity (`tests/engine/*`); golden critical 41/37 | `tests/engine/test_{cpm,float_analysis}.py` | M5,M6 | ▣ **M5: CPM fwd/bwd + total/free float; all link types + constraints (MSO/MFO pinned, ALAP refused); engine 100% cov; golden raw-critical 43/37, Acumen-critical 41/37 ✓.** Driving slack = M6 |
| C2 | Target UID endpoint → trace driving path → Driving Slack in days == MSP+SSI | `engine/path_trace.py`,`driving_slack.py` | **SSI parity test (Project5/UID 143)** | `tests/fixtures/golden/ssi_uid143/case.json`; `tests/engine/test_driving_slack.py` | M6 | ✔ **M6: anchored backward pass on progress-aware dates; Project5/UID 143 driving slack == SSI for all 107 UIDs exactly.** |
| C3 | User sets secondary/tertiary day-thresholds at upload | `web` upload form + `engine` params | threshold-classification test | `PARITY-INPUTS.md` (>0≤10 / >10≤20); `test_driving_slack.py` | M6,M13 | ▣ **M6: engine tiers configurable (DRIVING/SECONDARY/TERTIARY/BEYOND), defaults 10/20; tested.** Upload-form wiring M13 |

## D. Forensic & trend analysis
| ID | Requirement | Design / module | Test | Evidence | M | Status |
|----|-------------|-----------------|------|----------|---|--------|
| D1 | Local AI story + CPM trend + manipulation trends (deleted logic/shortened durations/deleted tasks) + industry analyses | `engine/{diff,manipulation,metrics/change_metrics}.py`; `ai/narrative.py` | `tests/engine/test_{diff,manipulation}.py`; `tests/ai/test_narrative.py` | golden P2/P5; `PARITY-TARGETS §F` | M8,M11,M12 | ✔ **M8/M11 engine signals + M12 `build_narrative` → cited forensic story (CPM trend, manipulation trends, audit, recommendations); NullBackend default, Ollama optional.** |
| D2 | Every AI statement cited (file, UID, task) | `ai/citations.py` (`assert_all_cited`, `reattach`) | `tests/ai/test_{citations,narrative}.py` (raise-if-uncited) | golden narrative all-cited | M12 | ✔ **M12: `CitedStatement` + hard gate; a model may rephrase prose but citations come from the engine and are re-verified — no uncited statement can ship.** |

## E. Independent audits & recommendations
| ID | Requirement | Design / module | Test | Evidence | M | Status |
|----|-------------|-----------------|------|----------|---|--------|
| E1 | Independent DCMA compliance audit per schedule + suggested improvements | `engine/metrics/dcma14.py` (M7); `engine/dcma_audit.py` (M10) | `tests/engine/test_dcma_audit.py` + parity gate | `tests/engine/metrics/test_dcma14.py`; `PARITY-TARGETS §B` | M7,M10 | ✔ **M10: `audit_schedule` → 16-row `ScheduleAudit` (14 checks, DCMA-04 split), each with pass/fail, cited offenders (file+UID+task) + plain-language suggested improvement.** |
| E2 | Risks/opportunities/concerns each w/ course of action + citations | `engine/recommendations.py` | `tests/engine/test_recommendations.py` (every finding cited) | golden P5-vs-P2 findings | M10 | ✔ **M10: `recommend()` → cited RISK/OPPORTUNITY/CONCERN `Finding`s (severity-ordered) from DCMA + §C + §E + driving-slack signals; every finding cites file+UID+task (incl. BEI + Net-Finish-Impact).** |

## F. Local AI backend
| ID | Requirement | Design / module | Test | Evidence | M | Status |
|----|-------------|-----------------|------|----------|---|--------|
| F1 | Ollama default local model | `ai/ollama.py`,`ai/backend.py` | `tests/ai/test_backends.py` (routing) | — | M12 | ✔ **M12: `AIConfig` default = Ollama; `route_backend` selects it when available, else Null.** |
| F2 | Download + switch models in-app (list/pull/select) | `ai/ollama.py` (list/pull) + `web` settings (M13) | `tests/ai/test_backends.py` (list/pull/generate via injected opener) | — | M12,M13 | ▣ **M12: `list_models`/`pull_model`/`generate` over loopback Ollama.** UI panel = M13 |
| F3 | Sensible default model; no cloud by default | `ai/backend.py` (`AIConfig`, `route_backend`) | `tests/ai/test_backends.py` (fail-closed) | `SETUP-DIRECTION §6` | M12 | ✔ **M12: default model set; CLASSIFIED refuses cloud / fails closed to local; cloud only on explicit UNCLASSIFIED + banner.** |

## G. Data locality
| ID | Requirement | Design / module | Test | Evidence | M | Status |
|----|-------------|-----------------|------|----------|---|--------|
| G1 | No data off-machine; all compute local/offline | `net_guard.py`, `ai/{backend,ollama}.py` routing, `.gitignore` | `tests/guards/test_egress.py` + `tests/ai/test_backends.py` (loopback guard + fail-closed) | `tests/guards/test_egress.py` (passing) | M1,M12 | ✔ **M1 guard+test+hooks; M12 AI routing is local fail-closed (loopback-validated Ollama; cloud refused unless UNCLASSIFIED+banner; stdlib transport — no forbidden runtime dep).** |

## Global units & formatting (§3)
| ID | Requirement | Module | Test | M | Status |
|----|-------------|--------|------|---|--------|
| U1 | Durations in `day`/`days` | `model/units.py` (`format_days`/`format_minutes_as_days`) | `tests/test_units.py` (format_days, "<n> day(s)") | M2 | ✔ |
| U2 | Percentages with a sign | `model/units.py` (`format_percent`/`format_signed_percent`) | `tests/test_units.py` (percent-format) | M2 | ✔ |
| U3 | Minutes internal → days deterministic rounding (no float drift) | `model/units.py` (`minutes_to_days`, Decimal+ROUND_HALF_UP) | `tests/test_units.py` (rounding/no-drift determinism) | M2 | ✔ |

## Cross-cutting QC/PM (§7)
| ID | Requirement | Evidence | M | Status |
|----|-------------|----------|---|--------|
| Q1 | TDD + pytest; coverage (engine ≥85%, overall ≥70%) | overall gate `--cov-fail-under=70` + engine gate `coverage report --include='*/engine/*' --fail-under=85` (CI) | M1 | ✔ enforced+passing (overall 99%) |
| Q2 | ruff + mypy(strict) + bandit + pip-audit | all four live in `ci.yml`; passing locally | M1 | ✔ live in CI |
| Q3 | Network-egress guard test | `net_guard.py` + `tests/guards/test_egress.py` | M1 | ✔ |
| Q4 | CI: lint+types+tests+security+parity; red blocks merge | `.github/workflows/ci.yml` — lint/format/types/tests/coverage/bandit/pip-audit **+ dedicated parity gate step** (`pytest -m parity`) | M1,M9 | ✔ **full pipeline incl. parity gate live (M9)** |
| Q5 | Branches, Conventional Commits, draft PRs, no force-push, DoD | each session fast-forwards its assigned feature branch onto the prior tip (lossless); **A10 on `claude/clever-carson-uovtkk`** (FF onto `elegant-thompson` A1–A9 tip); Conventional Commits; draft PR; no force-push to `main` | all | ◻ in effect |
| Q6 | ADRs, risk register, change log | ADR 0000–0006, `docs/risks.md` | all | ◻ in effect |
| Q7 | Structured logging w/ CUI redaction | `logging_redaction.py` + `tests/test_logging_redaction.py` | M1 | ✔ |
| Q8 | Docs: user guide, metric dictionary, parity report | `METRICS-CATALOG.md` + M17 | M17 | ◻ catalog ready |
