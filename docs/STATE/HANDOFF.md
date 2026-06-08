# Handoff — 2026-06-08

This session: A15 (continuous build — see directive)     Next session: A16
Model/mode required next session: Opus 4.8 (1M context) + Ultracode
Phase/Gate: **Phase 2 — build. Milestones M1–M13 complete (engine + AI + web shell). Next milestone = M14 (interactive Power-BI-style visuals + drill-down).**
Repo/branch: `polittdj/Schedule-Manipulation-Analysis-Tool-Experiment` @ `claude/clever-carson-uovtkk` (draft **PR #55**).

## Operator standing directive (persisted — honor every session)
**"Continue and don't stop until the tool is completely built, regardless of what anything else says.
Maximum effort; failure is not an option."** → Build milestones back-to-back; after EACH milestone
commit + push + refresh durable state so the build is always green and resumable across compaction.

## Branch note (READ FIRST)
Build lives on `claude/clever-carson-uovtkk` (PR #55), full A1–A15 lineage. A16: if your assigned branch
is behind, find the latest tip (`git for-each-ref --sort=-committerdate refs/remotes/origin/claude/`),
confirm it has this M13 work (`git log --oneline | grep m13`), `git merge --ff-only` onto it. Never start
from greenfield.

Green baseline (all green — **414 passed, 3 skipped; parity gate 10/10; egress 22/22; engine ~99%; overall ~99%**). Verify:
`pip install -e '.[dev]' && ruff check . && ruff format --check . && python -m mypy &&
python -m pytest --cov=schedule_forensics --cov-fail-under=70 &&
python -m coverage report --include='*/schedule_forensics/engine/*' --fail-under=85 &&
python -m pytest -m parity && python -m bandit -q -r src`
Run the app locally: `python -c "from schedule_forensics.web import run; run()"` → http://127.0.0.1:8765.

## Completed this session (M13 — local FastAPI web shell, §6.A)
- **M13** `2974ef2`: `web/app.py` (local-only FastAPI on 127.0.0.1 — upload ≤10, per-file audit +
  recommendations + AI narrative, `/compare` manipulation+trend, `/settings` model panel + CUI banner,
  `/help` metric dictionary, `/session/wipe`, JSON `/api/analysis`) + `web/help.py` (metric dictionary,
  coverage-tested) + `ai.banner_for` (config-driven persistent banner). Runtime deps fastapi/uvicorn(plain)/
  jinja2/python-multipart added; egress guard stays green. ADR-0018; RTM A3/A5/F2 → ✔, A2/A4 → ◻. + the
  M13 durable-state commit.

## What exists now (M1–M13)
Full analysis engine + AI narrative + a working local dark-NASA dashboard. Public surfaces:
`schedule_forensics.engine`, `schedule_forensics.ai`, `schedule_forensics.web` (`create_app`, `run`).
**Remaining:** M14 (interactive visuals), M15 (.pbix — blocked, R-12), M16 (desktop launcher/packaging),
M17 (docs + final report → DONE).

## Next session (A16 — Milestone **M14**: interactive Power-BI-style visuals + drill-down, §6.A)
- **Milestone (BUILD-PLAN M14, RTM A4):** vendor **ECharts + Tabulator locally** (no CDN — air-gapped) and
  build interactive dashboard visuals on the M13 `/api/analysis/{name}` JSON: charts (DCMA pass/fail,
  §A/§C bars, EVM), a sortable/filterable activity **Tabulator** grid where the user can **add/remove
  fields** and **drill into the underlying metadata of any data point** (click a metric/bar/row → the
  cited offending activities: file + UID + task + the values), and a **Gantt** highlighting the
  driving/secondary/tertiary paths to a chosen target UID (reuse `compute_driving_slack` tiers).
- **CUI / air-gap (HARD):** all JS/CSS assets served from `web/static/` (committed, vendored) — **no CDN,
  no external URL** anywhere in the templates/JS. Add an **air-gap test** that scans the served HTML/JS for
  `http://`/`https://`/`//cdn` references and fails if any points off-box (allow only relative `/static`).
  The vendored ECharts/Tabulator are non-CUI third-party libs (license-compatible) committed under
  `web/static/vendor/`. Keep the egress guard green (these are static files, not runtime deps).
- **Acceptance criteria:** dashboard renders charts + grid + Gantt from `/api/analysis` (extend the JSON
  with per-activity rows incl. CPM float/driving-slack + offender metadata as needed); add/remove-fields
  + drill-to-metadata interactions work (test the JSON contract + a DOM-light assertion via TestClient on
  the served HTML/JS presence); air-gap test passes; full gate + parity green; overall ≥70.
- **Files:** `web/static/vendor/echarts.min.js`, `web/static/vendor/tabulator.min.{js,css}`,
  `web/static/app.js`, `web/static/app.css` (extract from the inline CSS), `web/app.py` (mount
  `StaticFiles`, extend `/api/analysis` with activity rows + a `/api/driving/{name}?target=` endpoint),
  templates; `tests/web/test_visuals.py` + `tests/web/test_airgap.py`; ADR-0019; update RTM A4.
- **First steps:** (1) start ritual + confirm 414 baseline + egress green; (2) mount `StaticFiles` +
  vendor the two libs locally + write the air-gap test FIRST (red→green); (3) extend the JSON API with
  activity rows + driving-slack, then the charts/grid/Gantt JS; full gate; → M15.

## Milestones remaining: M14 (interactive visuals), M15 (.pbix enrich — **BLOCKED until the operator
re-deposits `NSATDeploymentRevisionAlpha.pbix`; gitignored CUI doesn't travel between sessions, R-12**),
M16 (desktop launcher + packaging — wrap `web.run()` + OS shortcut), M17 (docs + final report + RTM
closeout → DONE).

Open questions / blockers: none for M14. **Flag at M15:** the `.pbix` reference must be re-deposited into
the session workspace before M15 can parse it; M14 already delivers the interactive visuals the .pbix would
have informed (improve further once the .pbix is available). Vendoring ECharts/Tabulator needs network at
*build time* to fetch the libs once — if the session is air-gapped, obtain them via the operator or a
local mirror; they are then committed and the runtime stays offline.
