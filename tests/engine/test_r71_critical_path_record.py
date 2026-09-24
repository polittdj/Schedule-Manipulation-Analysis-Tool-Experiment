"""R-71's flag half (operator ruling 2026-09-23, ADR-0527): finished work is never on the critical
path, and ``TaskTiming.is_critical`` keeps its documented meaning.

MS Project stores ``Critical = No`` on every finished activity (0 of 8,644 across the 44-file
corpus carry ``Critical = 1``). The operator ruled that the documented, pure-CPM
``is_critical`` (``total_float <= 0``) does NOT change meaning — the record-aware answer already
lives in ``is_effective_critical`` — and that ``CPMResult.critical_path`` alone drops an activity
whose whole window is a record (:func:`is_recorded_complete`).

Red-first (2026-09-24): on the pristine tree the committed goldens carried FOUR recorded-complete
activities on ``critical_path``, all stored ``Critical = No`` — Hard_File_updated2 UID 290,
Hard_File_updated3 UID 261 (in both golden copies of that file) and Large_Test_File2 UID 6956 —
and the synthetic chain's finished head sat on it.
"""

from __future__ import annotations

import datetime as dt
import gzip
from pathlib import Path

from schedule_forensics.engine.cpm import compute_cpm, is_recorded_complete
from schedule_forensics.importers.mspdi import parse_mspdi, parse_mspdi_text
from schedule_forensics.model import Relationship, Schedule, Task

DAY = 480
MON = dt.datetime(2026, 3, 2, 8, 0)
GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"


def _chain() -> Schedule:
    """A finished head (recorded: 100 %, both actuals) driving two open tasks to the finish."""
    done = Task(
        unique_id=1,
        name="Done",
        duration_minutes=2 * DAY,
        percent_complete=100.0,
        actual_start=MON,
        actual_finish=dt.datetime(2026, 3, 3, 17, 0),
    )
    return Schedule(
        name="r71",
        project_start=MON,
        status_date=dt.datetime(2026, 3, 4, 8, 0),
        tasks=(
            done,
            Task(unique_id=2, name="Next", duration_minutes=3 * DAY),
            Task(unique_id=3, name="Last", duration_minutes=1 * DAY),
        ),
        relationships=(
            Relationship(predecessor_id=1, successor_id=2),
            Relationship(predecessor_id=2, successor_id=3),
        ),
    )


def test_a_finished_activity_is_off_the_critical_path_but_keeps_its_pure_cpm_flag() -> None:
    sch = _chain()
    assert is_recorded_complete(sch.tasks_by_id[1])
    cpm = compute_cpm(sch)
    head = cpm.timings[1]
    assert head.total_float <= 0 and head.is_critical is True  # the documented pure property
    assert cpm.critical_path == (2, 3)  # ...and the path holds only work that can still move


def test_a_complete_task_without_its_actuals_is_not_a_record_and_stays_on_the_path() -> None:
    """``is_recorded_complete`` needs 100 % AND both actuals — a percentage alone is a claim."""
    base = _chain()
    claimed = base.tasks_by_id[1].model_copy(update={"actual_finish": None})
    sch = base.model_copy(update={"tasks": (claimed, *base.tasks[1:])})
    assert not is_recorded_complete(claimed)
    assert compute_cpm(sch).critical_path == (1, 2, 3)


def _load(path: Path) -> Schedule:
    if path.suffix == ".gz":
        return parse_mspdi_text(gzip.decompress(path.read_bytes()).decode(), source_file=path.name)
    return parse_mspdi(path)


def test_the_critical_path_is_uid_exact_against_ms_projects_stored_critical_flag() -> None:
    """Every committed golden, keyed on its PATH (two goldens share a basename with others): the
    set on ``critical_path`` is exactly the set MS Project stores ``Critical = Yes`` on, over every
    non-summary activity that carries the flag — 7,935 of them, a population asserted, not
    assumed."""
    files = sorted(p for p in GOLDEN.rglob("*") if p.name.endswith((".mspdi.xml", ".mspdi.xml.gz")))
    assert len(files) == 15
    population = 0
    disagree: list[tuple[str, int]] = []
    for path in files:
        sch = _load(path)
        on_path = set(compute_cpm(sch).critical_path)
        for t in sch.tasks:
            if t.is_summary or t.stored_is_critical is None:
                continue
            population += 1
            if (t.unique_id in on_path) != bool(t.stored_is_critical):
                disagree.append((str(path.relative_to(GOLDEN)), t.unique_id))
    assert population == 7935
    assert disagree == []
