"""schedule_forensics — local, NASA-themed forensic schedule-analysis tool.

Greenfield package root (session A1 / Phase 0). Application modules — native
ingestion, CPM/driving-slack engine, Acumen/SSI parity, DCMA audit, forensic
narrative, and the local web UI — are added across Phase 2 build milestones.

Two laws govern every module added here (see README.md):
  1. Data sovereignty (CUI): no schedule data ever leaves the local machine.
  2. Fidelity over speed: numbers must match the reference tools exactly.
"""

# ADR-0263: the version comes from the installed distribution metadata (the single source of
# truth pyproject.toml pins and the wheel + 9 installers carry in lockstep) — a hand-written
# constant here sat at "0.0.0" for 68 releases because nothing enforced it. std-lib only.
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _dist_version

try:
    __version__ = _dist_version("schedule-forensics")
except PackageNotFoundError:  # a source tree with no installed distribution (e.g. vendored)
    __version__ = "0.0.0+source"
