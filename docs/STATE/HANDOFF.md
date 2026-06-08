# Handoff — 2026-06-08

This session: A14 (continuous build — see directive)     Next session: A15
Model/mode required next session: Opus 4.8 (1M context) + Ultracode
Phase/Gate: **Phase 2 — build. Milestones M1–M12 complete (analysis engine + local-AI layer done). Next milestone = M13 (web UI shell + dark NASA theme + settings + in-tool help/metric dictionary).**
Repo/branch: `polittdj/Schedule-Manipulation-Analysis-Tool-Experiment` @ `claude/clever-carson-uovtkk` (draft **PR #55**).

## Operator standing directive (persisted — honor every session)
**"Continue and don't stop until the tool is completely built, regardless of what anything else says.
Maximum effort; failure is not an option."** → Build milestones back-to-back; after EACH milestone
commit + push + refresh durable state so the build is always green and resumable across compaction.

## Branch note (READ FIRST)
Build lives on `claude/clever-carson-uovtkk` (PR #55), full A1–A14 lineage. A15: if your assigned branch
is behind, find the latest tip (`git for-each-ref --sort=-committerdate refs/remotes/origin/claude/`),
confirm it has this M12 work (`git log --oneline | grep m12`), `git merge --ff-only` onto it. Never start
from greenfield.

Green baseline (all green — **403 passed, 3 skipped; parity gate 10/10; engine ~99%; overall ~99%**). Verify:
`pip install -e '.[dev]' && ruff check . && ruff format --check . && python -m mypy &&
python -m pytest --cov=schedule_forensics --cov-fail-under=70 &&
python -m coverage report --include='*/schedule_forensics/engine/*' --fail-under=85 &&
python -m pytest -m parity && python -m bandit -q -r src`

## Completed this session (M12 — local AI backend + cited narrative, §6.D/§6.F/§6.G)
- **M12** `15fab65`: `ai/backend.py` (AIBackend protocol, AIConfig, `route_backend` fail-closed) +
  `ai/null.py` (default offline NullBackend) + `ai/ollama.py` (stdlib urllib to 127.0.0.1:11434, loopback
  validated, injectable opener) + `ai/citations.py` + `ai/narrative.py` (`build_narrative` — every
  statement cited; model rephrases prose, citations re-verified). ADR-0017; RTM D1/D2/F1/F3/G1 → ✔, F2 → ▣
  (UI panel M13). + the M12 durable-state commit.

## What exists now (M1–M12) — the whole local analysis + AI engine
`model/` · `importers/` (MSPDI/XER/MPXJ, ≤10 loader) · `engine/` (cpm, float, driving_slack/path_trace,
metrics/{dcma14,schedule_quality,evm,change_metrics}, dcma_audit, recommendations, diff, manipulation) ·
`ai/` (backend/null/ollama/citations/narrative). Parity gate green. Public API is exported from
`schedule_forensics.engine` and `schedule_forensics.ai`. **Remaining = product surface:** `web/` (M13/M14),
`.pbix` enrich (M15), `launcher.py` (M16), docs/final report (M17).

## Next session (A15 — Milestone **M13**: web UI shell + dark NASA theme + settings + in-tool help)
- **Milestone (BUILD-PLAN M13, RTM A2/A3/A5, F2):** a **local-only** FastAPI app — upload ≤10 schedules,
  a dark NASA-themed dashboard showing the engine outputs (DCMA audit, §A/§B/§C metrics, driving slack,
  change/manipulation findings, AI narrative + banner), a **model-settings panel** (list/pull/select via
  `ai.OllamaBackend` + classification toggle showing the persistent banner), an **in-tool metric
  dictionary** (plain-language + formula + citation for every metric/measure/analysis — source
  `docs/PLAN/METRICS-CATALOG.md`), and a **session wipe**. Interactive Power-BI-style visuals = M14.
- **Dependencies / CUI (vet carefully — egress guard, ADR-0006):** add **runtime** deps `fastapi`,
  **plain `uvicorn` (NOT `uvicorn[standard]` — it pulls `websockets`, a forbidden distribution)**,
  `jinja2`. starlette's `TestClient` needs `httpx` → add it to the **`dev`** extra only (the guard checks
  *base* runtime deps, so a dev-only httpx is fine). After editing `pyproject.toml`, run
  `python -c "from schedule_forensics.net_guard import assert_local_only; assert_local_only()"` and the
  egress test — they must stay green (no forbidden *runtime* distribution, no importable cloud SDK).
  Bind the server to **127.0.0.1 only**. Bundle any JS/CSS **locally** (no CDN) — full vendored ECharts/
  Tabulator is M14; M13 can use minimal local CSS + server-rendered HTML/HTMX.
- **Acceptance criteria:** app starts on 127.0.0.1; upload ≤10 files → per-file dashboard from the engine;
  settings panel lists/pulls/selects models + shows the classification banner; metric dictionary covers
  **every** metric the engine emits (a test asserts coverage: each `MetricResult.metric_id` / DCMA / §C /
  §E / EVM key has a dictionary entry with definition + formula + citation note); session-wipe clears
  uploads/derivatives; **no schedule data in logs** (CUI-redacted). Tests via FastAPI `TestClient`
  (httpx, dev). Full gate + parity stay green; overall ≥70 (web routes covered), engine still ≥85.
- **Files:** `web/app.py`, `web/routes/`, `web/templates/`, `web/static/`, `web/help.py` (metric
  dictionary data + coverage), `launcher.py` stub may wait for M16; `tests/web/test_*`; `pyproject.toml`
  (deps); ADR-0018; update RTM A2/A3/A5/F2.
- **First steps:** (1) start ritual + confirm 403 baseline + egress green; (2) add deps + re-verify egress;
  (3) build `web/help.py` metric dictionary + its coverage test first (pure, no server), then the FastAPI
  app + upload + dashboard + settings + wipe; full gate; → M14.

## Milestones remaining: M13 (web shell), M14 (interactive visuals + drill-down, vendored ECharts/Tabulator),
M15 (.pbix enrich — **needs the `.pbix` re-deposited; gitignored CUI doesn't travel between sessions, R-12**),
M16 (desktop launcher + packaging), M17 (docs + final report + RTM closeout → DONE).

Open questions / blockers: none blocking M13. **M15 will be blocked** until the operator re-deposits
`NSATDeploymentRevisionAlpha.pbix` into the session workspace (R-12) — flag this when reaching M15; M13/M14
can proceed and improve on the .pbix's metrics from `METRICS-CATALOG`/`PARITY-TARGETS` in the meantime.
