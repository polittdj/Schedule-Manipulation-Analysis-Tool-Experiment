"""Cross-version robustness regressions (QC audit 2026-07-01, batch R4 / ADR-0141).

D11: a tz-aware datetime from a hand-written friendly JSON, mixed with naive imports, crashed
`order_versions` — the funnel for every multi-version page. D12: XER never populated the stored
Total Float, so the "stored float wins" Acumen-parity path never engaged for P6 files. D19: two
modules rounded Logic Density two different ways (banker's vs the Fuse-validated half-up).
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.trend import order_versions
from schedule_forensics.importers.json_schedule import parse_json_text
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task


def test_tz_aware_json_dates_are_normalized_naive_qc_d11() -> None:
    """A '...Z' status_date loads naive (like MSPDI/XER), so mixing it with a naive version can
    never raise 'can't compare offset-naive and offset-aware datetimes' in order_versions."""
    aware = parse_json_text(
        '{"name": "Zulu", "project_start": "2026-01-05T08:00:00Z",'
        ' "status_date": "2026-02-01T17:00:00+02:00",'
        ' "tasks": [{"unique_id": 1, "name": "A", "duration_minutes": 480,'
        '            "start": "2026-01-05T08:00:00Z"}]}'
    )
    assert aware.project_start.tzinfo is None
    assert aware.status_date is not None and aware.status_date.tzinfo is None
    assert aware.tasks[0].start is not None and aware.tasks[0].start.tzinfo is None
    naive = Schedule(
        name="Naive",
        project_start=dt.datetime(2026, 1, 5, 8, 0),
        status_date=dt.datetime(2026, 1, 15, 17, 0),
        tasks=(Task(unique_id=1, name="A", duration_minutes=480),),
    )
    ordered = order_versions([aware, naive])  # used to raise TypeError
    assert [s.name for s in ordered] == ["Naive", "Zulu"]


def test_xer_reads_stored_total_float_qc_d12() -> None:
    """`total_float_hr_cnt` maps to `stored_total_float_minutes` (hours -> working minutes), so
    `effective_total_float` prefers P6's own progress-aware float exactly as it does for MSPDI."""
    from schedule_forensics.importers.xer import parse_xer_text

    xer = (
        "ERMHDR\t19.12\t2025-02-01\tProject\tadmin\tAdmin\tdb\tPM\tUSD\n"
        "%T\tPROJECT\n"
        "%F\tproj_id\tproj_short_name\tplan_start_date\tplan_end_date\tlast_recalc_date\n"
        "%R\t1\tP1\t2025-01-06 08:00\t2025-03-31 17:00\t2025-02-01 17:00\n"
        "%T\tCALENDAR\n%F\tclndr_id\tclndr_name\tclndr_data\n%R\t10\tStd\t\n"
        "%T\tTASK\n"
        "%F\ttask_id\tproj_id\ttask_name\ttask_code\ttask_type\tstatus_code\t"
        "target_drtn_hr_cnt\ttotal_float_hr_cnt\tclndr_id\n"
        "%R\t100\t1\tPour footings\tA100\tTT_Task\tTK_NotStart\t40\t16\t10\n"
        "%R\t101\t1\tNo float carried\tA101\tTT_Task\tTK_NotStart\t40\t\t10\n"
        "%E\n"
    )
    sch = parse_xer_text(xer)
    # every task carries a unique task_code, so tasks are keyed by the stable
    # Activity-ID identity (ADR-0185), not the renumbering-prone raw task_id
    by_name = {t.name: t for t in sch.tasks}
    assert by_name["Pour footings"].stored_total_float_minutes == 960  # 16 h * 60
    # absent stays None, never fabricated
    assert by_name["No float carried"].stored_total_float_minutes is None


def test_logic_density_rounds_half_up_matching_the_ribbon_qc_d19() -> None:
    """2.625 must round to 2.63 (the Fuse-validated ribbon convention), in BOTH modules —
    banker's round() gave 2.62 in schedule_quality while the ribbon showed 2.63."""
    from schedule_forensics.engine.metrics.schedule_quality import compute_schedule_quality
    from schedule_forensics.model.relationship import Relationship

    # 16 activities, 21 links -> 2 * 21 / 16 = 2.625 exactly
    tasks = tuple(Task(unique_id=i, name=f"T{i}", duration_minutes=480) for i in range(1, 17))
    edges = [(a, a + 1) for a in range(1, 16)]  # 15 chain links
    edges += [(a, a + 2) for a in range(1, 7)]  # + 6 skip links = 21 total
    rels = tuple(Relationship(predecessor_id=a, successor_id=b) for a, b in edges)
    sch = Schedule(
        name="d19",
        project_start=dt.datetime(2026, 1, 5, 8, 0),
        tasks=tasks,
        relationships=rels,
    )
    q = compute_schedule_quality(sch)
    assert q["logic_density"].value == 2.63  # half-up, not banker's 2.62


def test_derived_rates_round_half_up_qc_d19() -> None:
    from schedule_forensics.engine.metrics.derived import dcma_pass_rate, population_share

    assert population_share(1, 16) == 6.3  # 6.25 half-up, not banker's 6.2
    assert dcma_pass_rate(1, 15) == 6.3
