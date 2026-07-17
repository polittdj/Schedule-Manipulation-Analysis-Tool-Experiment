"""ENGINE==SSI driving-slack parity for focus UID 155 across a Standard (8h) file and the SAME
schedule on a 24-hour calendar — the per-successor-calendar effect (ADR-0118).

``Hard_File_updated3.mpp`` (Standard, Mon-Fri 8h) and ``Hard_File_updated4 24 hour calendar.mpp``
(the driving chain on a 24-hour calendar) are the operator's SSI Directional Path exports
(2026-07-15). SSI lists every predecessor of focus UID 155 with its **Driving Slack in days**,
counted on each successor's own calendar. The two files are the same logic, so the SAME
predecessors appear — but their driving slack is **32 days on the 8h file and 18 days on the 24h
file** (and every other row shifts correspondingly, fractional and negative values included).

The engine's :func:`compute_driving_slack` reproduces **every** SSI row on BOTH snapshots — this
gate locks the 24-hour-calendar driving-slack behaviour cell-for-cell, complementing the strict
0-day ``ssi_hardfile_uid155`` Path-01 gate with a calendar-sensitive VALUE gate. Ground truth is
pinned in ``case.json`` straight from the SSI exports (no hand-transcription).
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from schedule_forensics.engine.driving_slack import compute_driving_slack
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.schedule import Schedule

pytestmark = pytest.mark.parity

CASE = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "ssi_hardfile_24h_uid155"

#: SSI reports driving slack in days to full precision; the engine derives it from the same
#: working-minute arithmetic, so agreement is tight. 0.01 day (~9 working-minutes on an 8h day,
#: ~14 on a 24h day) absorbs only display rounding in the export, never a real divergence.
_TOL_DAYS = 0.01


def _schedule(snapshot: str) -> Schedule:
    xml = gzip.decompress((CASE / f"{snapshot}.mspdi.xml.gz").read_bytes()).decode("utf-8")
    return parse_mspdi_text(xml, source_file=f"{snapshot}.mspdi.xml")


def _case() -> dict:
    return json.loads((CASE / "case.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("snapshot", ["Hard_File_updated3", "Hard_File_updated4_24h"])
def test_ssi_driving_slack_days_match_cell_for_cell(snapshot: str) -> None:
    case = _case()
    focus = case["focus_task_uid"]
    expected = case[snapshot]["driving_slack_days_by_uid"]  # {uid: SSI days}

    results = compute_driving_slack(_schedule(snapshot), target_uid=focus)

    missing = [uid for uid in expected if int(uid) not in results]
    assert not missing, f"{snapshot}: engine has no driving slack for SSI UIDs {missing}"

    mismatches = {
        uid: (sd, round(float(results[int(uid)].driving_slack_days), 4))
        for uid, sd in expected.items()
        if abs(float(results[int(uid)].driving_slack_days) - sd) > _TOL_DAYS
    }
    assert not mismatches, f"{snapshot}: engine != SSI driving slack (days) for {mismatches}"


def test_the_24_hour_calendar_shrinks_the_driving_slack() -> None:
    """The headline of the pair: the SAME predecessors (UID 379/321/381) carry 32 days of driving
    slack on the 8h file and 18 days on the 24h file — the calendar, not the logic, moved them."""
    case = _case()
    three = ("379", "321", "381")
    std = case["Hard_File_updated3"]["driving_slack_days_by_uid"]
    day24 = case["Hard_File_updated4_24h"]["driving_slack_days_by_uid"]
    assert all(std[u] == 32.0 for u in three), {u: std[u] for u in three}
    assert all(day24[u] == 18.0 for u in three), {u: day24[u] for u in three}

    for snapshot, expect in (("Hard_File_updated3", 32.0), ("Hard_File_updated4_24h", 18.0)):
        results = compute_driving_slack(_schedule(snapshot), target_uid=case["focus_task_uid"])
        for u in three:
            assert abs(float(results[int(u)].driving_slack_days) - expect) <= _TOL_DAYS
