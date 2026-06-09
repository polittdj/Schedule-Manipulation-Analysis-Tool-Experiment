"""schedule_forensics — local, NASA-themed forensic schedule-analysis tool.

Greenfield package root (session A1 / Phase 0). Application modules — native
ingestion, CPM/driving-slack engine, Acumen/SSI parity, DCMA audit, forensic
narrative, and the local web UI — are added across Phase 2 build milestones.

Two laws govern every module added here (see README.md):
  1. Data sovereignty (CUI): no schedule data ever leaves the local machine.
  2. Fidelity over speed: numbers must match the reference tools exactly.
"""

__version__ = "0.0.0"
