"""IMP-05 (WP6b, ADR-0467): an XER import SAYS that its baseline dates are P6's planned dates.

``xer.py`` reads ``target_start_date`` / ``target_end_date`` into ``baseline_start`` /
``baseline_finish``. MPXJ 16.2.0 (the vendored, independent reader) maps those same columns to
PLANNED_START / PLANNED_FINISH, never to a baseline; P6 shows an activity's planned dates as its
BL dates only while no baseline project is assigned, and an assigned baseline project is not read
from an XER at all. The values stay (they ARE what P6 shows in the no-baseline case) but the
import now discloses their provenance in ``import_notes``, which /analysis renders.

Red-first (2026-09-06): the fixture imported with ``import_notes == ()``.
"""

from __future__ import annotations

from pathlib import Path

from schedule_forensics.importers import parse_xer

XER = Path(__file__).resolve().parents[1] / "fixtures" / "xer" / "commercial_construction.xer"


def test_the_import_discloses_that_baseline_dates_are_p6_planned_dates() -> None:
    s = parse_xer(XER)
    notes = [n for n in s.import_notes if "planned" in n.lower() and "baseline" in n.lower()]
    assert len(notes) == 1, s.import_notes
    assert "target_start_date" in notes[0] and "baseline project" in notes[0]


def test_the_values_themselves_are_unchanged() -> None:
    s = parse_xer(XER)
    assert sum(1 for t in s.tasks if t.baseline_start is not None) == 2  # measured on the fixture
