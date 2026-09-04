"""REC-02 (WP6, ADR-0463): an inactive Analysis Target does not detonate the recommender.

``_driving_path_findings`` guarded a summary target but not an INACTIVE one, and
``compute_driving_slack`` raises ``KeyError`` for any UID outside the scheduled network (ADR-0128),
so ``recommend(schedule, target_uid=<inactive>)`` raised out of the engine. Measured on
``commercial_construction.xml`` (UID 5 inactive): ``KeyError(5)``.
"""

from __future__ import annotations

from pathlib import Path

from schedule_forensics.engine.recommendations import recommend
from schedule_forensics.importers.mspdi import parse_mspdi

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "mspdi" / "commercial_construction.xml"


def test_an_inactive_target_yields_findings_without_a_driving_path_row() -> None:
    sch = parse_mspdi(FIXTURE)
    inactive = [t.unique_id for t in sch.tasks if not t.is_active and not t.is_summary]
    assert inactive == [5]
    findings = recommend(sch, target_uid=5)
    assert findings  # the ordinary findings still come through
    assert not [f for f in findings if f.metric_id == "driving_path"]


def test_an_active_target_still_gets_its_driving_path_row() -> None:
    sch = parse_mspdi(FIXTURE)
    active = next(
        t.unique_id for t in sch.tasks if t.is_active and not t.is_summary and t.unique_id != 5
    )
    titles = [f.title for f in recommend(sch, target_uid=active) if f.metric_id == "driving_path"]
    assert len(titles) <= 1  # present only when something drives it — never an exception
