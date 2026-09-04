"""MC-03 (WP6, ADR-0463): an ABSENT actual cost on open work is not a spent 0.

``compute_jcl`` read a missing ``actual_cost`` on an in-progress task as ``0.0`` spent, so the
performed share of its budget vanished from the EAC: at 50 % complete a 1,000 task contributed
500 (the remaining half) and nothing for the half already performed, while the completed branch
had always assumed the budget when actuals were absent. Measured: EAC 680 with the actual absent,
1,180 with it recorded at budget, and a 990 jump between 99 % and 100 % complete. The performed
share of the budget is now the point estimate when the source carries no actual — the completed
branch's own assumption, continuous at 100 % — and the count of tasks it applied to is disclosed.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from schedule_forensics.engine.jcl import compute_jcl
from schedule_forensics.engine.sra import SRAConfig
from schedule_forensics.importers.mspdi import parse_mspdi
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2026, 3, 2, 8, 0)
DAY = 480
CFG = SRAConfig(iterations=20)
GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"


def _chain(pc: float, actual: float | None) -> Schedule:
    done = Task(
        unique_id=1,
        name="done",
        duration_minutes=DAY,
        budgeted_cost=100.0,
        actual_cost=130.0,
        percent_complete=100.0,
        actual_start=MON,
        actual_finish=dt.datetime(2026, 3, 2, 17, 0),
    )
    extra = {"actual_finish": dt.datetime(2026, 3, 16, 17, 0)} if pc >= 100 else {}
    started = {"actual_start": dt.datetime(2026, 3, 3, 8, 0)} if pc > 0 else {}
    open_ = Task(
        unique_id=2,
        name="open",
        duration_minutes=10 * DAY,
        budgeted_cost=1000.0,
        actual_cost=actual,
        percent_complete=pc,
        **started,
        **extra,
    )
    later = Task(unique_id=3, name="later", duration_minutes=2 * DAY, budgeted_cost=50.0)
    return Schedule(
        name="S",
        project_start=MON,
        status_date=dt.datetime(2026, 3, 16, 8, 0),
        tasks=(done, open_, later),
        relationships=(
            Relationship(predecessor_id=1, successor_id=2),
            Relationship(predecessor_id=2, successor_id=3),
        ),
    )


def test_absent_actual_on_open_work_is_the_performed_share_of_budget() -> None:
    absent = compute_jcl(_chain(50.0, None), config=CFG)
    recorded = compute_jcl(_chain(50.0, 500.0), config=CFG)
    assert absent.deterministic_eac == recorded.deterministic_eac == 1180.0
    assert absent.sunk_total == recorded.sunk_total == 630.0


def test_the_eac_is_continuous_across_completion_when_actuals_are_absent() -> None:
    almost = compute_jcl(_chain(99.0, None), config=CFG)
    done = compute_jcl(_chain(100.0, None), config=CFG)
    assert almost.deterministic_eac == done.deterministic_eac == 1180.0


def test_a_recorded_actual_is_never_overridden() -> None:
    over = compute_jcl(_chain(50.0, 700.0), config=CFG)
    assert over.deterministic_eac == 130.0 + 700.0 + 500.0 + 50.0


def test_the_assumption_is_disclosed_by_count() -> None:
    assert compute_jcl(_chain(50.0, None), config=CFG).actuals_assumed_count == 1
    assert compute_jcl(_chain(50.0, 500.0), config=CFG).actuals_assumed_count == 0
    assert (
        compute_jcl(_chain(0.0, None), config=CFG).actuals_assumed_count == 0
    )  # nothing performed


def test_the_evm_goldens_carry_their_actuals_so_nothing_is_assumed() -> None:
    for name in ("EVM1", "EVM2"):
        sch = parse_mspdi(GOLDEN / "evm" / f"{name}.mspdi.xml")
        assert compute_jcl(sch, config=CFG).actuals_assumed_count == 0
