# Handoff — 2026-06-10 (evening)

This session: operator-driven enhancements (PRs #58–#62, all merged)     Next session: — (build complete)
Model/mode required next session: Opus 4.8 (1M context) (only if resuming M15)
Phase/Gate: **DONE** — M1–M14 + M16 + M17 complete and parity-green, plus the full-audit remediation
(ADR-0024) and the multi-version analysis suite (ADR-0025). **M15 (.pbix enrichment) is the one
remaining item, BLOCKED pending the operator depositing `NSATDeploymentRevisionAlpha.pbix` (R-12).**
Repo/branch: `polittdj/Schedule-Manipulation-Analysis-Tool-Experiment` — `main` carries everything
(#55–#62 merged); work branch `claude/clever-carson-uovtkk` is recreated from `main` per PR.

## Operator standing directive (persisted)
**"Continue and don't stop until the tool is completely built."** → Honored: the entire build except the
externally-gated `.pbix` enrichment is complete, tested, validated, parity-green, and runnable offline.

## What was delivered (M1–M14 + M16 + M17)
A complete local, NASA-themed forensic schedule-analysis tool:
- **Ingestion:** native `.mpp` (MPXJ), MSPDI, XER; ≤10 at once; UID-keyed (M3/M4).
- **Engine:** CPM + total/free float; SSI driving slack (107/107 exact); DCMA-14 + Acumen §A Schedule
  Quality + §C baseline compliance + EVM indices + §E change metrics + Net Finish Impact (−99); version
  diff + manipulation-trend detection; DCMA audit + cited recommendations (M5–M11).
- **AI:** pluggable Null (default) / loopback Ollama; cited narrative (every sentence cited); CUI
  fail-closed routing + persistent banner (M12).
- **Web:** local dark-NASA dashboard — upload, audit, recommendations, narrative, version compare,
  interactive charts/grid/Gantt (drill-to-metadata, add/remove fields), AI settings, metric dictionary,
  session wipe; air-gapped (M13/M14).
- **Packaging:** one-click desktop launcher + OS shortcuts, 127.0.0.1 only (M16).
- **Docs:** user guide, metric dictionary (generated + sync-tested), parity report, final report (M17).

## Audit remediation (this session)
A three-track audit (engine/model/importers; web/AI/launcher/packaging; tests/CI/docs/hygiene) found
29 issues, fixed across 13 commits on `claude/clever-carson-uovtkk`:
- **Bugs:** dropzone now submits the real form so import feedback survives in real browsers; native
  `.mpp` upload writes a *closed* temp file (Windows handle bug); `/session/wipe` + `/example` are
  POST-only (GET could prefetch-mutate); download filename sanitized; deleted-logic citations carry the
  prior file (never-uncited contract); SPI(t) Earned-Schedule dead interpolation simplified.
- **Perf:** `tasks_by_id`/`resources_by_id` cached on the frozen model; each report computes one
  `_Analysis` (one CPM) reused across page/JSON/driving views; CPM date math is O(weeks) not O(days)
  (equivalence-swept against the old loops); Ollama availability probes use a 2 s timeout.
- **CI/hygiene/docs:** push runs on `main` only, `checkout@v5`/`setup-python@v6`, pip cache; shared
  session-scoped golden fixtures + central warning filter; this doc set refreshed; `pyproject` 1.0.0.

## Operator-driven enhancements (PRs #59–#62, merged after the audit)
- **Java discovery (#59/#60):** native `.mpp` works without Java on PATH — SF_JAVA → JAVA_HOME →
  PATH → the repo's **portable `tools/jre/` drop-in** (gitignored; no admin rights needed) →
  user-scope `%LOCALAPPDATA%\Programs` → machine install roots; newest version wins; actionable
  not-found error. The operator's locked-down work machine is the driving case.
- **Compare correctness (#61):** the compare pair is ordered by **data date** (ProjectTimeNow), not
  load order, and the page shows the **Net Finish Impact** in calendar days.
- **Multi-version suite (#62, ADR-0025):** `/trend` across 10+ versions (headline table, Net Finish
  Impact across the series, quality-trend sentences, consecutive-pair manipulation signals, SVG
  charts via `static/trend.js`); `/briefing` — the cited, print-ready **Diagnostic Executive
  Briefing** (`ai/briefing.py`, golden-pinned counts); the activity grid is now an **MS-Project-
  style Gantt** (timeline column with month ticks, critical/progress/milestone/summary bars,
  data-date line, add/remove fields incl. duration/baselines/resources). New `engine/trend.py`.
  Ten-version end-to-end test locks the 10-file requirement.

## Green state (final)
**497 passed, 3 skipped; parity gate 10/10; egress 22/22; air-gap pass; engine ~99%; overall ~99%.**
CI green. Verify:
`pip install -e '.[dev]' && ruff check . && ruff format --check . && python -m mypy &&
pytest --cov=schedule_forensics --cov-fail-under=70 &&
coverage report --include='*/schedule_forensics/engine/*' --fail-under=85 &&
pytest -m parity && bandit -q -r src && pip-audit --progress-spinner=off` — all exit 0.
Run: `schedule-forensics` → http://127.0.0.1:<port> dashboard.

## The one remaining item — M15 (.pbix enrichment), BLOCKED
Needs `NSATDeploymentRevisionAlpha.pbix` deposited into the session workspace (git-ignored CUI, doesn't
travel between sessions — R-12). When provided: parse locally (unzip → DataModel + Report/Layout), fold
its extra metrics/visuals into the dashboard. The interactive visuals (M14) already deliver the capability
the `.pbix` would inform; this is a pending **input**, not a defect. Do not fabricate `.pbix` content.

## To resume M15 (only if/when the .pbix is deposited)
1. Confirm the branch tip has M17 (`git log --oneline | grep m17`), fast-forward your branch onto it.
2. Confirm the 497 green baseline + the file present in `00_REFERENCE_INTAKE/` (non-CUI attested).
3. Add `importers/pbix.py` (unzip + parse DataModel/Layout, local-only); fold metrics/visuals into the
   dashboard; tests + ADR-0022; close the last RTM row; refresh this HANDOFF.

## CI hygiene (LESSON): `git add -A` every milestone; run the gate with honored exit codes (never
`bandit | tail`); after pushing verify the run conclusion is `success` (webhooks don't deliver CI success).

Open questions / blockers: only M15's `.pbix` deposit. Everything else is DONE and parity-green.
