"""ENGINE==SSI parity for the driving path of focus UID 155 on ``Hard_File.mpp`` and
``Hard_File_updated.mpp`` (operator-delivered SSI Directional Path exports, 2026-07-08; #67).

These are SSI "get all dependencies" exports: SSI lists every predecessor of focus UID 155
with its Driving Slack and buckets each into a ``Path`` number by exact driving-slack value.
``Path 01`` is the strict 0-day driving path. The engine's zero-driving-slack set
(``driving_slack_minutes == 0``) reproduces SSI's Path 01 membership EXACTLY, UID-for-UID, on
BOTH the base and updated snapshots, and the engine's ordered driving chain filtered to those
members reproduces SSI's Path 01 row order exactly. This is the same gating basis as the
``ssi_uid67`` / ``ssi_uid145`` goldens; the engine's broader ``on_driving_path`` set additionally
flags sub-day-slack tasks as driving (the documented ragged-minutes rule) which SSI files under
Path 02/03, so we gate the strict 0-day path, not the near-path set. SSI's Drag column is
provenance-only and deliberately NOT gated (the engine does not compute drag; ADR-0158).
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from schedule_forensics.engine.driving_slack import (
    PathTier,
    compute_driving_slack,
    driving_path,
)
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.schedule import Schedule

pytestmark = pytest.mark.parity

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "fuse_hardfile"
CASE = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "ssi_hardfile_uid155"


def _schedule(name: str) -> Schedule:
    xml = gzip.decompress((FIXTURES / f"{name}.mspdi.xml.gz").read_bytes()).decode("utf-8")
    return parse_mspdi_text(xml, source_file=f"{name}.mspdi.xml")


def _case() -> dict:
    return json.loads((CASE / "case.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("snapshot", ["Hard_File", "Hard_File_updated"])
def test_ssi_driving_path_uid155_exact(snapshot: str) -> None:
    case = _case()
    focus = case["focus_task_uid"]
    expected_order = case[snapshot]["driving_path_uids_ordered"]
    expected_set = set(expected_order)

    sch = _schedule(snapshot)
    results = compute_driving_slack(sch, target_uid=focus)

    # 1. the engine's strict 0-day driving-slack set == SSI Path 01, UID-for-UID, no extras
    engine_zero = {uid for uid, r in results.items() if r.driving_slack_minutes == 0}
    assert engine_zero == expected_set

    # 2. every SSI Path 01 member is on the driving path at exactly 0 driving slack
    for uid in expected_set:
        r = results[uid]
        assert r.driving_slack_minutes == 0
        assert r.on_driving_path
        assert r.tier is PathTier.DRIVING

    # 3. the engine's ordered chain, filtered to those members, matches SSI's Path 01 row order
    engine_chain = [uid for uid in driving_path(sch, results) if uid in expected_set]
    assert engine_chain == expected_order

    # 4. the focus itself terminates the path at 0 slack
    assert results[focus].driving_slack_minutes == 0 and results[focus].on_driving_path


@pytest.mark.parametrize("snapshot", ["Hard_File", "Hard_File_updated"])
def test_ssi_driving_slack_days_are_zero_whole_days_uid155(snapshot: str) -> None:
    case = _case()
    results = compute_driving_slack(_schedule(snapshot), target_uid=case["focus_task_uid"])
    expected_days = {int(u): d for u, d in case[snapshot]["driving_slack_days_by_uid"].items()}
    got_days = {uid: int(results[uid].driving_slack_days) for uid in expected_days}
    assert got_days == expected_days  # all zero, as SSI's Path 01 reports "0 days"
