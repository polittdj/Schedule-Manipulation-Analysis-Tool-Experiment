"""Resource loading & over-allocation engine (ADR-0125).

Time-phases assignment work into a monthly load-vs-capacity histogram and flags months booked beyond
a resource's capacity. Deterministic, parity-isolated (plain dataclasses).
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.resources import ResourcePeriod, compute_resource_loading
from schedule_forensics.importers.mspdi import parse_mspdi
from schedule_forensics.model import Assignment, Resource, Schedule, Task

DAY = 480
MON = dt.datetime(2026, 4, 6, 8, 0)  # a Monday
GOLDEN = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "golden"
    / "project2_5"
    / "Project5.mspdi.xml"
)


def _task(uid: int, dur_days: float, assignments: tuple[Assignment, ...] = ()) -> Task:
    return Task(
        unique_id=uid,
        name=f"T{uid}",
        duration_minutes=int(dur_days * DAY),
        resource_assignments=assignments,
    )


def _sched(tasks: list[Task]) -> Schedule:
    return Schedule(name="S", project_start=MON, tasks=tuple(tasks))


def test_no_assignments_means_no_loading() -> None:
    sch = _sched([_task(1, 5)])
    rl = compute_resource_loading(sch, compute_cpm(sch))
    assert rl.resources == () and rl.has_work is False


def test_work_is_time_phased_and_totalled() -> None:
    a = (Assignment(resource_id=1, work_minutes=10 * DAY, units=1.0),)
    sch = _sched([_task(1, 10, a)])
    rl = compute_resource_loading(sch, compute_cpm(sch))
    assert rl.has_work is True
    assert len(rl.resources) == 1
    r = rl.resources[0]
    assert r.resource_id == 1 and r.task_count == 1
    # the totalled work survives the monthly bucketing (10 working days == 4800 min)
    assert round(r.total_work_minutes) == 10 * DAY


def test_over_allocation_is_flagged() -> None:
    # two full-time tasks on the same resource over the same span => 2x its daily capacity
    a = (Assignment(resource_id=1, work_minutes=22 * DAY, units=1.0),)
    sch = _sched([_task(1, 22, a), _task(2, 22, a)])
    rl = compute_resource_loading(sch, compute_cpm(sch))
    r = next(res for res in rl.resources if res.resource_id == 1)
    assert r.over_allocated_periods, "a doubly-booked resource must show over-allocated months"
    # the over-allocated month's booked load exceeds its capacity
    over = next(p for p in r.series if p.over_allocated)
    assert over.load_minutes > over.capacity_minutes


def test_granularity_buckets_day_week_month() -> None:
    """#74: the same work totals the same at every granularity, but finer buckets slice it into more
    (or equal) periods with proportionally smaller per-bucket capacity."""
    a = (Assignment(resource_id=1, work_minutes=20 * DAY, units=1.0),)
    sch = _sched([_task(1, 20, a)])
    cpm = compute_cpm(sch)
    totals = {}
    period_counts = {}
    for g in ("day", "week", "month"):
        rl = compute_resource_loading(sch, cpm, g)
        assert rl.granularity == g
        r = rl.resources[0]
        totals[g] = round(sum(p.load_minutes for p in r.series))
        period_counts[g] = len(r.series)
    # total work is invariant to the bucket
    assert totals["day"] == totals["week"] == totals["month"] == 20 * DAY
    # finer buckets never have fewer periods
    assert period_counts["day"] >= period_counts["week"] >= period_counts["month"]
    assert period_counts["day"] > period_counts["month"]  # 20 working days vs ~1 month


def test_unknown_granularity_falls_back_to_month() -> None:
    a = (Assignment(resource_id=1, work_minutes=5 * DAY, units=1.0),)
    sch = _sched([_task(1, 5, a)])
    rl = compute_resource_loading(sch, compute_cpm(sch), "fortnight")
    assert rl.granularity == "month"


def test_bucket_contributors_carry_the_tasks_behind_each_period() -> None:
    """#74 click-a-bar drill: each period records the per-task work that produced it, summing to the
    period load, ordered by minutes desc."""
    a = (Assignment(resource_id=1, work_minutes=10 * DAY, units=1.0),)
    b = (Assignment(resource_id=1, work_minutes=10 * DAY, units=1.0),)
    sch = _sched([_task(1, 10, a), _task(2, 10, b)])
    rl = compute_resource_loading(sch, compute_cpm(sch), "month")
    r = next(res for res in rl.resources if res.resource_id == 1)
    for p in r.series:
        assert abs(sum(mins for _uid, mins in p.contributors) - p.load_minutes) < 1e-6
        mins = [m for _u, m in p.contributors]
        assert mins == sorted(mins, reverse=True)  # ordered by contribution desc
        assert {uid for uid, _m in p.contributors} <= {1, 2}


def test_golden_schedule_loads_without_error() -> None:
    sch = parse_mspdi(str(GOLDEN))
    rl = compute_resource_loading(sch, compute_cpm(sch))
    assert rl.has_work is True
    assert rl.resources and rl.periods
    # every resource's series is sorted and self-consistent
    for r in rl.resources:
        assert r.total_work_minutes >= 0
        assert all(p.capacity_minutes >= 0 for p in r.series)


# ── audit 2026-07-29 (V5 + V6): zero capacity is a statement, not a missing value ──────────
# ``Resource.max_units`` is ``ge=0.0`` (model/resource.py), so 0.0 legally means "this resource has
# no capacity" — a placeholder, or a crew that has left. It used to be coerced to 1.0, printing an
# invented full unit-day of capacity; and ``ResourcePeriod.over_allocated`` used to require
# ``capacity_minutes > 0``, so the most extreme over-allocation there is — work booked against NO
# capacity — reported False. The two fixes are paired on purpose: preserving the 0 alone would have
# SUPPRESSED the flag instead of sharpening it.


def _resourced(uid: int, dur_days: float, work_minutes: int, max_units: float | None) -> Schedule:
    a = (Assignment(resource_id=7, work_minutes=work_minutes, units=1.0),)
    return Schedule(
        name="S",
        project_start=MON,
        tasks=(_task(uid, dur_days, a),),
        resources=(Resource(unique_id=7, name="Departed crew", max_units=max_units),),
    )


def test_a_declared_zero_max_units_is_preserved_not_coerced_to_one() -> None:
    sch = _resourced(1, 1, DAY, max_units=0.0)
    r = compute_resource_loading(sch, compute_cpm(sch), granularity="day").resources[0]
    assert r.max_units == 0.0, "a file that says MaxUnits=0 must not be reported as 1"
    assert all(p.capacity_minutes == 0.0 for p in r.series)


def test_a_missing_max_units_still_defaults_to_one_full_unit() -> None:
    """The control: None means "the file did not say", which keeps the 1.0 assumption."""
    r = compute_resource_loading(
        _resourced(1, 1, DAY, max_units=None),
        compute_cpm(_resourced(1, 1, DAY, None)),
        granularity="day",
    ).resources[0]
    assert r.max_units == 1.0


def test_work_booked_against_zero_capacity_is_over_allocated() -> None:
    """Work against a zero-capacity resource is over-allocation, not a condition to hide."""
    sch = _resourced(1, 1, DAY, max_units=0.0)
    r = compute_resource_loading(sch, compute_cpm(sch), granularity="day").resources[0]
    assert r.over_allocated_periods, "booked work against zero capacity must be reported"
    over = next(p for p in r.series if p.over_allocated)
    assert over.capacity_minutes == 0.0 and over.load_minutes > 0


def test_an_idle_zero_capacity_bucket_is_not_over_allocated() -> None:
    """Removing the ``capacity_minutes > 0`` guard must not make empty buckets noisy."""
    idle = ResourcePeriod(period="2026-04", load_minutes=0.0, capacity_minutes=0.0)
    assert idle.over_allocated is False


# ── differing max units + the whole-roster view (operator 2026-08-20) ────────────────────────
# The capacity formula always honored max_units, but no fixture carried TWO resources at
# DIFFERENT max units (the audit measured every fixture at a uniform 1.0), and the roster was
# built from assignments only — a resource with no booked work was invisible.


def test_two_resources_with_different_max_units_judge_against_their_own_capacity() -> None:
    """Same booked work, different capacity: the half-unit resource over-allocates, the
    two-unit crew does not — each judged against ITS OWN max units, never a shared 1.0."""
    a = (
        Assignment(resource_id=1, work_minutes=DAY, units=1.0),
        Assignment(resource_id=2, work_minutes=DAY, units=1.0),
    )
    sch = Schedule(
        name="S",
        project_start=MON,
        tasks=(_task(1, 1, a),),
        resources=(
            Resource(unique_id=1, name="Two-unit crew", max_units=2.0),
            Resource(unique_id=2, name="Half-unit specialist", max_units=0.5),
        ),
    )
    rl = compute_resource_loading(sch, compute_cpm(sch), granularity="day")
    by_name = {r.name: r for r in rl.resources}
    assert not by_name["Two-unit crew"].over_allocated_periods
    assert by_name["Half-unit specialist"].over_allocated_periods
    assert by_name["Two-unit crew"].max_units == 2.0
    assert by_name["Half-unit specialist"].max_units == 0.5


def test_every_file_resource_appears_even_with_no_assignments() -> None:
    """A resource the file declares but nothing books must still be a roster row with honest
    zeros — "the tool should allow the user to see all resources" (operator 2026-08-20)."""
    a = (Assignment(resource_id=1, work_minutes=DAY, units=1.0),)
    sch = Schedule(
        name="S",
        project_start=MON,
        tasks=(_task(1, 1, a),),
        resources=(
            Resource(unique_id=1, name="Busy", max_units=1.0),
            Resource(unique_id=2, name="Bench", max_units=1.5),
        ),
    )
    rl = compute_resource_loading(sch, compute_cpm(sch), granularity="day")
    by_name = {r.name: r for r in rl.resources}
    assert "Bench" in by_name, "an unassigned resource vanished from the roster"
    bench = by_name["Bench"]
    assert bench.total_work_minutes == 0.0
    assert bench.task_count == 0
    assert bench.series == ()
    assert bench.max_units == 1.5


def test_declared_flag_distinguishes_a_stated_max_units_from_the_assumed_default() -> None:
    """The engine substitutes 1.0 for a MISSING max units (documented default); the view must
    be able to render "—" for the assumption instead of a fabricated figure (Law 2), so the
    row carries whether the file actually stated the value."""
    stated = compute_resource_loading(
        _resourced(1, 1, DAY, max_units=1.0), compute_cpm(_resourced(1, 1, DAY, 1.0))
    ).resources[0]
    assumed = compute_resource_loading(
        _resourced(1, 1, DAY, max_units=None), compute_cpm(_resourced(1, 1, DAY, None))
    ).resources[0]
    assert stated.max_units_declared is True
    assert assumed.max_units_declared is False
    assert assumed.max_units == 1.0  # the math keeps the documented default
