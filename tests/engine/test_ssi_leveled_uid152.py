"""SSI Directional Path parity for the operator's LEVELED master IMS (focus UID 152).

Ground truth: the operator's own SSI Directional Path Tool exports for ``Large Test File
Leveled.mpp`` (delivered 2026-07-14) — one "get all dependencies" run and one critical/secondary/
tertiary run. Settings (from the delivered SSI screenshot): Path Direction = **Predecessors**,
**Ignore constraints ON**, **Ignore leveling delay ON**, Dependency Range = Driving Slack ≤ 0d
(the critical path), 2 near paths at parent+10d. Names are anonymized in the source .mpp; Drag was
not computed (ignored).

This is the "assume nothing — check everything" gate for the operator's report that the critical
path looked wrong: it pins that the engine reproduces SSI's **critical path to UID 152 exactly** and
the **full driving-dependency set membership** on the operator's real file. Any regression in the
CPM / driving-slack engine that would corrupt the critical path fails here.
"""

from __future__ import annotations

import gzip
import json
from functools import cache
from pathlib import Path

import pytest

from schedule_forensics.engine.driving_slack import compute_driving_slack
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.schedule import Schedule

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "ssi_uid152_leveled"


@cache
def _leveled() -> Schedule:
    raw = gzip.decompress((GOLDEN / "Large_Test_File_Leveled.mspdi.xml.gz").read_bytes())
    return parse_mspdi_text(raw.decode("utf-8-sig", errors="replace"))


@cache
def _case() -> dict:
    return json.loads((GOLDEN / "case.json").read_text())


def _results() -> dict:
    # SSI settings: predecessors, ignore constraints + ignore leveling delay, near-path bands 10/20d
    return compute_driving_slack(
        _leveled(),
        target_uid=_case()["focus_task_uid"],
        ignore_constraints=True,
        ignore_leveling_delay=True,
        secondary_max_days=10,
        tertiary_max_days=20,
    )


@pytest.mark.parity
def test_ssi_leveled_critical_path_to_uid152_is_exact() -> None:
    """Every task on SSI's critical path (Path 01, 60 tasks) is on the engine's driving path to
    UID 152, at 0 days of driving slack — the operator's 'critical path', pinned UID-exact."""
    results = _results()
    crit = {int(u): v for u, v in _case()["critical_path_01_slack_by_uid"].items()}
    assert len(crit) == 60
    missing = [uid for uid in crit if uid not in results or not results[uid].on_driving_path]
    assert not missing, f"SSI-critical UIDs not on the engine driving path: {missing}"
    # SSI reports these at ≤ 0 days; the engine reproduces 0 days of driving slack for each
    off = [uid for uid in crit if float(results[uid].driving_slack_days) != 0.0]
    assert not off, f"SSI-critical UIDs the engine does not read at 0-day slack: {off}"


@pytest.mark.parity
def test_ssi_leveled_full_driving_set_and_slack_reproduced() -> None:
    """The engine's driving-dependency SET to UID 152 matches SSI's 'get all dependencies' export
    (783 tasks, UID-for-UID), and the driving-slack magnitudes reproduce SSI: the vast majority
    exact, with a handful differing only by a sub-day / one-day calendar-handoff rounding that SSI
    applies at path junctions (documented provenance, not an engine error — cf. ADR-0158)."""
    results = _results()
    alldeps = {int(u): v for u, v in _case()["all_dependencies_driving_slack_by_uid"].items()}
    assert len(alldeps) == 783
    assert set(results) == set(alldeps)  # exact membership: every driving predecessor, no extras
    diffs = {uid: abs(float(results[uid].driving_slack_days) - alldeps[uid]) for uid in alldeps}
    exact = sum(1 for d in diffs.values() if d < 0.02)
    assert exact >= 775, f"only {exact}/783 driving-slack values are exact (expected >=775)"
    worst = max(diffs.values())
    assert worst <= 1.01, f"a driving-slack value is off by {worst:.2f} d (expected <=1.01)"
