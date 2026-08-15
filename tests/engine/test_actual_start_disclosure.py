"""ENG-DEAD-01 (ADR-0407): ``CPMResult.actual_start_driven`` finally reaches the analyst.

ADR-0391 floors a task at its recorded ``actual_start`` and reports the floored UIDs on
``CPMResult.actual_start_driven`` — deliberately NOT on ``date_driven``, whose CONCERN
("tie these activities into the network") would smear a false manipulation signal across
every progressed schedule. The 2026-08-13 audit verified the channel was produced but
consumed by no product code (ENG-DEAD-01). It now feeds:

* an INFO/OPPORTUNITY finding from :func:`recommend` — a cited disclosure, not a threat:
  OPPORTUNITY keeps it out of the risk matrix, the risk ranking, and the recovery plan,
  which take RISK + CONCERN only (``web/risks.py``);
* the ``/api/driving`` per-row flag and the path grid's optional "Actual-start-driven"
  column (``tests/web/test_path_view.py`` owns those pins);
* the metric dictionary, like every other emitted metric id (pinned here).
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.recommendations import Category, Severity, recommend
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.help import metric_doc

MON = dt.datetime(2025, 1, 6, 8, 0)  # a Monday, working-day start
DAY = 480


def _sched(tasks: list[Task], rels: list[Relationship] | None = None) -> Schedule:
    return Schedule(
        name="S", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels or [])
    )


def test_actual_start_floored_tasks_produce_the_info_disclosure() -> None:
    """One floored task -> one cited INFO/OPPORTUNITY finding on its own metric id.

    The task records an ``actual_start`` a week past its logic date, so ADR-0391 floors it
    there (`actual_start_driven == (1,)` — the shape pinned in test_cpm_stored_dates). The
    disclosure must cite the activity (§6) and must NOT fire the logic_unsupported_dates
    CONCERN — ADR-0391's separation, now held at the finding level too.
    """
    start = MON + dt.timedelta(days=7)  # the next Monday: floored five working days out
    s = _sched(
        [
            Task(
                unique_id=1,
                name="started late",
                duration_minutes=2 * DAY,
                start=start,
                finish=start + dt.timedelta(days=1, hours=9),
                actual_start=start,
            )
        ]
    )
    findings = recommend(s)
    f = next(f for f in findings if f.metric_id == "actual_start_driven")
    assert f.severity == Severity.INFO
    assert f.category == Category.OPPORTUNITY  # disclosure: no matrix, no recovery plan
    assert "1 activity is scheduled from its recorded actual start" in f.title
    assert f.citations and f.citations[0].unique_id == 1  # §6: never uncited
    assert all(f2.metric_id != "logic_unsupported_dates" for f2 in findings)


def test_no_disclosure_without_a_recorded_actual_start() -> None:
    """A logic-true, unprogressed schedule emits no actual-start disclosure at all."""
    s = _sched(
        [
            Task(unique_id=1, name="a", duration_minutes=DAY),
            Task(unique_id=2, name="b", duration_minutes=DAY),
        ],
        [Relationship(predecessor_id=1, successor_id=2)],
    )
    assert all(f.metric_id != "actual_start_driven" for f in recommend(s))


def test_the_disclosure_is_documented_in_the_metric_dictionary() -> None:
    """Every emitted metric id is documented (§6.A A5); the disclosure is no exception."""
    doc = metric_doc("actual_start_driven")
    assert doc is not None and doc.definition and doc.formula
    assert "ADR-0391" in doc.source
