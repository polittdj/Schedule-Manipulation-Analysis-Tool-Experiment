# Schedule Forensics

A **local-only, CUI-compliant** forensic schedule-analysis tool. It ingests
project schedules (MS Project / Primavera), runs critical-path (CPM) analysis and
schedule-quality/forensic metrics (DCMA-14, SPI/CEI/BEI, SRA, manipulation
detection), and produces Excel/Word reports plus a plain-English executive
summary. It runs entirely on `127.0.0.1` — **no schedule data ever leaves the
machine** (see `CLAUDE.md`, Law 1).

> Fidelity-first: results aim to match Deltek Acumen Fuse / Steelray-SSI /
> Microsoft Project semantics. Speed and elegance are tiebreakers, never
> overrides (Law 2).

## Status (greenfield rebuild — early)

The trust-root spine is under construction. **Built and green so far:**

- **Frozen data model** (`schemas.py`): strict, immutable, referential-integrity
  guarded `Schedule` / `Task` / `Relation` / `Calendar`. Cross-version identity
  by `UniqueID` only.
- **MS Project XML importer** (`importers/msp_xml.py`): pure-Python, deterministic.
- **CPM engine** (`cpm.py`): forward + backward pass on an integer working-minute
  axis; Finish-to-Start links with lag, total/free float (incl. negative under an
  imposed finish), critical path. SS/FF/SF links, the full constraint matrix,
  XER/MPXJ/COM importers, DCMA metrics, SRA, reports, and the UI are **deferred**
  (named in `PHASE-COMPLETE-1.md`, not silently skipped).

## Develop

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
ruff check . && ruff format --check . && mypy && pytest
```

Both Python 3.11 and 3.13 work; the project targets **3.11+**.

## Layout

- `src/schedule_forensics/` — the package (schema, importers, CPM engine).
- `tests/` — pytest suite; `tests/fixtures/` holds **synthetic** schedules only.
- `docs/` — `ARCHITECTURE.md`, `REFERENCES.md` (source manifest), `HAZARDS.md`.
- `scripts/` — local validation harness (`validate_against_msp.py`, Windows/COM).
- `CLAUDE.md` — the project constitution (the two laws, commandments, hazards,
  file-ownership manifest). Read it before contributing.

## Platform note

The primary ingestion path (MS Project XML + Primavera XER + native `.mpp` via
MPXJ-as-subprocess) is cross-platform. COM automation is an **optional
Windows-only** enhancement, validated locally; it is never the only path.

## Security note (CUI)

Schedule files (`*.mpp`, `*.xer`, `*.xml`, `*.mpx`, `*.csv`) may carry Controlled
Unclassified Information and are git-ignored. Do not commit real schedule data.
Only synthetic fixtures under `tests/fixtures/` are tracked.
