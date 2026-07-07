"""A Schedule must pickle even after its UID-map caches are primed (ADR-0150).

``tasks_by_id`` / ``resources_by_id`` cache a ``MappingProxyType`` (unpicklable) in the
instance dict. The SRA offload pickles the whole Schedule into its worker process, and every
analysis page touches ``tasks_by_id`` first — so every Monte-Carlo/sensitivity run failed with
"cannot pickle 'mappingproxy' object" (operator report, 2026-07-07). ``Schedule.__getstate__``
now drops the primed caches from the payload; they rebuild on first access in the worker.
"""

from __future__ import annotations

import datetime as dt
import pickle

from schedule_forensics.model.resource import Resource
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task


def _schedule() -> Schedule:
    return Schedule(
        name="s",
        project_start=dt.datetime(2025, 1, 6, 8, 0),
        tasks=(
            Task(unique_id=1, name="A", duration_minutes=480),
            Task(unique_id=2, name="B", duration_minutes=960),
        ),
        resources=(Resource(unique_id=7, name="R"),),
    )


def test_pickles_after_uid_caches_are_primed() -> None:
    sch = _schedule()
    assert sch.tasks_by_id[1].name == "A"  # prime both caches (the failing state)
    assert sch.resources_by_id[7].name == "R"
    back = pickle.loads(pickle.dumps(sch))
    assert [t.unique_id for t in back.tasks] == [1, 2]
    # and the caches rebuild fresh on the unpickled copy
    assert back.tasks_by_id[2].name == "B" and back.resources_by_id[7].name == "R"


def test_pickles_when_caches_never_primed() -> None:
    back = pickle.loads(pickle.dumps(_schedule()))
    assert back.task_by_id(1).duration_minutes == 480
