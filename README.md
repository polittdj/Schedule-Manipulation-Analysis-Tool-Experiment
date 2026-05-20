# Schedule Manipulation Analysis Tool (Experiment)

A forensic schedule-analysis tool. It ingests project schedules (MS Project / Primavera)
and runs DCMA-14 schedule-quality metrics and critical-path (CPM) analysis. This repository
is an **autonomous build experiment** — see [`EXPERIMENT-REPORT.md`](EXPERIMENT-REPORT.md).

> Fidelity-first: results aim to match Acumen Fuse / Steelray / MS Project semantics.
> Speed and elegance are tiebreakers, never overrides.

## Status
- **M1 — Scaffolding:** Flask app factory, 500 MB upload guard + 413 handler, CI.
- **M2 — Data model:** strict/frozen Pydantic `Schedule`/`Task`/`Relation`/`Calendar` (+ constraints, deadlines, baseline/actual tracking data).
- **M3 — Parser seam:** monkeypatchable stub (real `.mpp` parsing needs MS Project COM, out of scope).
- **M4 — CPM engine:** FS/SS/FF/SF + lag, MS Project date constraints, deadlines, total/free slack, negative float, critical path.
- **M5+ — DCMA metrics:** **all 14** of the DCMA 14-Point assessment, plus an integrity/health score.

See [`docs/dcma-metrics.md`](docs/dcma-metrics.md) and [`docs/cpm-model.md`](docs/cpm-model.md).

## Layout
- `app/` — application package: `create_app` factory, config, error handlers, routes.
- `tests/` — pytest suite.
- `docs/` — design notes.

## Development
```sh
python3.13 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
ruff check . && ruff format --check . && mypy app/ && pytest -q
```

## Running
```sh
flask --app "app:create_app" run        # http://localhost:5000/health

# Analyze a schedule (JSON Schedule body in -> CPM + DCMA metrics report out):
curl -X POST http://localhost:5000/analyze \
  -H 'Content-Type: application/json' --data-binary @schedule.json
```
`POST /analyze` validates a JSON `Schedule`, runs the CPM engine and all 14 DCMA metrics, and
returns per-task timings (ES/EF/LS/LF/slack), the critical path, project finish (working days),
per-metric results, and an integrity/health score (share of runnable metrics that pass, with the
failing metrics listed as findings).

## Security note
Schedule files (`*.mpp`, `*.xer`, `*.xml`) may carry Controlled Unclassified Information
and are git-ignored. Do not commit them.
