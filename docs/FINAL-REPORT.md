# Final report — Schedule Manipulation Analysis Tool

Local, NASA-themed forensic schedule-analysis tool, built autonomously across sessions A1–A18 per
`AUTONOMOUS-BUILD-PROMPT.md`. This report maps every build-contract requirement (§6.A–§6.G), the global
units rule (§3), and the QC/PM regime (§7) to its implementing module(s) and verifying evidence. The
authoritative, row-by-row status is `docs/PLAN/RTM.md`; this is the narrative closeout.

**Status: complete and parity-green except one externally-gated item.** Every §6 requirement is
`Implemented + Tested + Validated` except **§6.A's `.pbix` enrichment (M15)**, which is **blocked pending
the operator depositing `NSATDeploymentRevisionAlpha.pbix`** (git-ignored CUI does not travel between
sessions, R-12) — this is a pending input, not a build defect. The acceptance gate (Acumen Fuse v8.11.0 +
SSI) is green; the tool runs from a desktop icon, fully offline.

## §6.A — Platform, UX & packaging
| Requirement | Evidence |
|---|---|
| All parsing/analysis/metrics/forensics in Python | `src/schedule_forensics/` (pure-Python engine); CI builds/tests on 3.11 + 3.13 |
| Desktop icon → 100% local → opens in browser | `launcher.py` (`schedule-forensics`) + `packaging/` shortcuts; binds 127.0.0.1, refuses non-loopback (`tests/test_launcher.py`, 100% cov) |
| Dark-mode, NASA-themed, intuitive UI | `web/app.py` dark theme; `tests/web/test_app.py` |
| Interactive Power-BI-style visuals; add/remove fields; drill into metadata; local assets (no CDN) | `web/static/{app.js,app.css}` (charts, drill-down grid, tiered Gantt); air-gap enforced by `tests/web/test_airgap.py` |
| In-tool help: every metric defined w/ formula + supporting detail | `web/help.py` `/help` + `docs/METRIC-DICTIONARY.md`; coverage asserted by `tests/web/test_help.py` |
| **`.pbix` enrichment (M15)** | **◻ BLOCKED — pending operator deposit (R-12). The interactive visuals (M14) already deliver the capability the .pbix would inform.** |

## §6.B — Ingestion & parity (acceptance gate)
| Requirement | Evidence |
|---|---|
| Parse ≤10 native `.mpp` at once, no conversion, all metadata | `importers/{mspdi,xer,mpp_mpxj,loader}.py`; Project2/5 → 144 activities UID 2–145; `tests/importers/*` |
| Exact match to Acumen Fuse v8.11.0 **and** SSI; parity suite = gate | `tests/parity/test_parity_gate.py` (`pytest -m parity`, CI step); `docs/PARITY-REPORT.md` — SSI 107/107, Acumen §A/§B/§C/§E all reproduced exact; residuals documented + locked |
| Cross-version matching by UniqueID only | `engine/diff.py`, `model/schedule.py` (UID-keyed); `tests/engine/test_diff.py` |

## §6.C — CPM, driving slack & path tracing (SSI parity)
| Requirement | Evidence |
|---|---|
| Critical path fwd/bwd pass; total/free float; driving slack | `engine/{cpm,float_analysis,driving_slack,path_trace}.py`; ADR-0010/0011 |
| Target UID → trace driving path → Driving Slack in days == MSP+SSI | `engine/driving_slack.py`; SSI parity 107/107 (Project5/UID 143); `tests/engine/test_driving_slack.py` |
| User-set secondary/tertiary day thresholds | configurable tiers (defaults 10/20d); exposed in the dashboard Gantt controls + `/api/driving` |

## §6.D — Forensic & trend analysis
| Requirement | Evidence |
|---|---|
| Local-AI story + CPM trend + manipulation trends (deleted logic/durations/tasks, baseline/actual edits) | `engine/{diff,manipulation}.py` + `ai/narrative.py`; `tests/engine/test_manipulation.py` (no false positives on honest P2→P5); ADR-0016 |
| Every AI statement cited (file, UID, task) | `ai/citations.py` (`assert_all_cited`, `reattach`); `tests/ai/test_{citations,narrative}.py` |

## §6.E — Independent audits & recommendations
| Requirement | Evidence |
|---|---|
| Independent DCMA audit per schedule + suggested improvements | `engine/dcma_audit.py` (`audit_schedule`); `tests/engine/test_dcma_audit.py` |
| Risks/opportunities/concerns each w/ course of action + citations | `engine/recommendations.py` (`recommend`); every finding cites file+UID+task; `tests/engine/test_recommendations.py` |

## §6.F — Local AI backend
| Requirement | Evidence |
|---|---|
| Ollama default local model | `ai/{ollama,backend}.py`; `AIConfig` default = local Ollama; `tests/ai/test_backends.py` |
| Download + switch models in-app (list/pull/select) | `ai/ollama.py` + `web` `/settings` panel |
| Sensible default; no cloud by default; fail closed | `ai/backend.py` `route_backend` — CLASSIFIED refuses cloud; cloud only on explicit UNCLASSIFIED + persistent banner |

## §6.G — Data locality (CUI)
| Requirement | Evidence |
|---|---|
| No data off-machine; all compute local/offline | `net_guard.py` egress guard (`tests/guards/test_egress.py`, 22/22); air-gap test; loopback-only server + AI; stdlib-only AI transport; `.gitignore` blocks all schedule formats |

## §3 — Units & formatting
Durations in `day`/`days`; signed percents; minutes→days deterministic rounding (`model/units.py`,
`tests/test_units.py`).

## §7 — QC/PM regime
TDD + pytest (**469 passed, 3 skipped**); coverage gates **engine ≥85% (≈99%), overall ≥70% (≈99%)**;
`ruff` + `mypy --strict` + `bandit` + `pip-audit` + the **parity gate** + the **egress/air-gap guards**,
wired into CI on `main` push + every PR (Python 3.11 + 3.13); Conventional Commits on feature branches
with PRs (#55–#57 merged to `main`; #58 = import feedback + full-audit remediation); 24 ADRs
(`docs/adr/`, incl. ADR-0024 audit remediation), a risk register (`docs/risks.md`), durable state
(`docs/STATE/`), and CUI-redacted logging (`logging_redaction.py`).

## Definition of Done (§8)
- Every §6 RTM row `Implemented + Tested + Validated` — **except §6.A `.pbix` enrichment (M15)**, ◻ BLOCKED
  on the operator's `.pbix` deposit (the single pending input).
- Parity suite matches Acumen Fuse v8.11.0 + SSI (deltas = 0, or documented + driven to zero + gate-locked).
- CI green; desktop launcher starts the local web UI; docs complete (this report, the user guide, the
  metric dictionary, the parity report); draft PR presented, not merged.

**When the `.pbix` is deposited, M15 folds its extra metrics/visuals into the dashboard and the last RTM
row closes.** Everything else is complete, validated, and runnable offline today.
