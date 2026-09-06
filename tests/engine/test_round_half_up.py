"""MF-08 (WP6b, ADR-0467): displayed ratios and percentages round half UP, not half to even.

Plain ``round()`` is banker's rounding: ``round(0.125, 2) == 0.12`` and ``round(12.5) == 12``.
Every metric value the engine reports at 1 or 2 decimal places went through it, while the one
place this repo had measured against Fuse (logic density, QC audit D19: 2.625 -> 2.63) and the
verification-contract helper ``derived._half_up`` both round half up. A ratio at an exact tie is
common in small populations (1 of 8 = 0.125; 1 of 8 incomplete = 12.5 %), so the two conventions
disagree in the last displayed digit exactly where an analyst compares figures by eye.

Red-first (2026-09-06): CEI 1 of 8 read 0.12; Critical 1 of 8 read 12 %.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.metrics._common import round_half_up
from schedule_forensics.engine.metrics.cei import compute_cei
from schedule_forensics.engine.metrics.schedule_quality import compute_schedule_quality
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

PREV = dt.datetime(2026, 3, 2, 8, 0)
NOW = dt.datetime(2026, 3, 30, 8, 0)
DAY = 480


def test_ties_round_half_up_where_bankers_rounding_goes_to_even() -> None:
    assert round(0.125, 2) == 0.12  # the defect, by contrast
    assert round_half_up(0.125, 2) == 0.13
    assert round_half_up(2.5, 0) == 3.0 and round_half_up(12.5, 0) == 13.0
    assert round_half_up(-0.125, 2) == -0.13  # ties away from zero, the spreadsheet ROUND rule
    assert round_half_up(0.186, 2) == 0.19  # non-ties unchanged
    assert round_half_up(0.1666, 2) == 0.17


def _tasks(n: int, *, done: int = 0, critical: int = 0) -> tuple[Task, ...]:
    out = []
    for i in range(1, n + 1):
        finished = i <= done
        out.append(
            Task(
                unique_id=i,
                name=f"T{i}",
                duration_minutes=DAY,
                start=dt.datetime(2026, 3, 16, 8, 0),
                finish=dt.datetime(2026, 3, 16, 17, 0),
                percent_complete=100.0 if finished else 0.0,
                actual_start=dt.datetime(2026, 3, 16, 8, 0) if finished else None,
                actual_finish=dt.datetime(2026, 3, 16, 17, 0) if finished else None,
                stored_is_critical=i <= critical,
            )
        )
    return tuple(out)


def test_cei_one_of_eight_reads_point_one_three() -> None:
    prior = Schedule(name="p", project_start=PREV, status_date=PREV, tasks=_tasks(8))
    current = Schedule(name="c", project_start=PREV, status_date=NOW, tasks=_tasks(8, done=1))
    cei = compute_cei(prior, current)["cei_tasks"]
    assert (cei.count, cei.population) == (1, 8)
    assert cei.value == 0.13, cei.value


def test_critical_one_of_eight_incomplete_reads_thirteen_percent() -> None:
    s = Schedule(name="s", project_start=PREV, status_date=NOW, tasks=_tasks(8, critical=1))
    crit = compute_schedule_quality(s)["critical"]
    assert (crit.count, crit.population) == (1, 8)
    assert crit.value == 13.0, crit.value
