# Handoff — 2026-06-10

This session: full-build audit remediation (bugs / perf / CI / cleanup / docs)     Next session: — (build complete)
Model/mode required next session: Opus 4.8 (1M context) (only if resuming M15)
Phase/Gate: **DONE** — M1–M14 + M16 + M17 complete and parity-green, plus a top-to-bottom audit
remediation (13 commits). **M15 (.pbix enrichment) is the one remaining item, BLOCKED pending the
operator depositing `NSATDeploymentRevisionAlpha.pbix` (R-12).**
Repo/branch: `polittdj/Schedule-Manipulation-Analysis-Tool-Experiment` @ `claude/clever-carson-uovtkk`
(**PR #58** — import feedback + full-audit remediation; #55–#57 merged to `main`).

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

## Green state (final)
**469 passed, 3 skipped; parity gate 10/10; egress 22/22; air-gap pass; engine ~99%; overall ~99%.**
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
2. Confirm the 469 green baseline + the file present in `00_REFERENCE_INTAKE/` (non-CUI attested).
3. Add `importers/pbix.py` (unzip + parse DataModel/Layout, local-only); fold metrics/visuals into the
   dashboard; tests + ADR-0022; close the last RTM row; refresh this HANDOFF.

## CI hygiene (LESSON): `git add -A` every milestone; run the gate with honored exit codes (never
`bandit | tail`); after pushing verify the run conclusion is `success` (webhooks don't deliver CI success).

Open questions / blockers: only M15's `.pbix` deposit. Everything else is DONE and parity-green.
