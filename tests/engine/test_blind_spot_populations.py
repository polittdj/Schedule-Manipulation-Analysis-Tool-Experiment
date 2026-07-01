"""Blind-spot population guard — the committed parity goldens contain NO inactive task, NO elapsed
in-progress activity, and a well-formed summary, so the parity gate is blind to those
populations (exactly how the inactive-task and Float-Ratio bugs once hid). This test exercises all
of them together on one synthetic schedule and pins the engine's population handling, so an accuracy
regression there can't pass unseen.

Covers, in one place: summary exclusion + inactive-task exclusion (ADR-0128) in `non_summary` and
the CPM network, and the Float-Ratio per-axis handling of an elapsed activity (NEW-1 / QC D7).
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.metrics import compute_float_ratio
from schedule_forensics.engine.metrics._common import non_summary
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task


def _mixed_schedule() -> Schedule:
    return Schedule(
        name="mixed",
        project_start=dt.datetime(2025, 1, 6, 8, 0),
        status_date=dt.datetime(2025, 2, 1, 17, 0),
        tasks=(
            Task(unique_id=0, name="Project summary", duration_minutes=0, is_summary=True),
            Task(unique_id=1, name="Active leaf", duration_minutes=480),
            Task(unique_id=2, name="Inactive leaf", duration_minutes=480, is_active=False),
            Task(
                unique_id=3,
                name="Elapsed WIP",
                duration_minutes=7200,
                duration_is_elapsed=True,
                remaining_duration_minutes=7200,
                stored_total_float_minutes=2400,
            ),
        ),
        relationships=(),
    )


def test_population_excludes_summary_and_inactive_but_keeps_elapsed() -> None:
    sch = _mixed_schedule()
    pop = {t.unique_id for t in non_summary(sch)}
    assert pop == {1, 3}  # summary (0) and inactive (2) excluded; active + elapsed kept


def test_cpm_network_excludes_summary_and_inactive() -> None:
    sch = _mixed_schedule()
    scheduled = set(compute_cpm(sch).timings)
    assert 0 not in scheduled and 2 not in scheduled  # neither summary nor inactive is scheduled
    assert {1, 3} <= scheduled


def test_float_ratio_population_excludes_summary_and_inactive_and_scores_the_elapsed_task() -> None:
    # the metric population is the active, non-summary, incomplete leaves — {1, 3}; the elapsed
    # activity is scored without error, each term on its own axis (NEW-1 as corrected by QC audit
    # D7; the per-axis value is pinned in test_float_ratio.py). Here we guard that
    # summary/inactive don't leak into the population.
    result = compute_float_ratio(_mixed_schedule())["float_ratio"]
    assert result.population == 2  # summary (0) and inactive (2) excluded; {1, 3} kept
