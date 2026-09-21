"""Float Ratio™ tests — the Bible's two forms over Acumen Fuse's whole-day FIELDS (R-78).

Hand-verified on small committed fixtures (real .mpp files are CUI): the population filter (normal,
planned/in-progress), both algebraic forms (mean-of-ratios and ratio-of-means), the
remaining-duration fallback, Fuse's N/A on a zero Remaining Duration field, the very-tight
offenders, and the period-to-period trend with its delta. Float and remaining duration are working
minutes at 480/day (4800 = 10 days), and both terms are converted to WHOLE days on the activity's
own day before dividing — the reference tool's own fields (ADR-0516 / ADR-0518 / ADR-0519). The
reference numbers themselves are pinned in ``tests/parity/test_fuse_duration_fields_oracle.py``
against the ribbons that display each form; these tests pin the semantics around them.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.metrics import CheckStatus, compute_float_ratio
from schedule_forensics.engine.trend import compute_float_ratio_trend
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

PAST = dt.datetime(2025, 2, 1, 17, 0)
NOW = dt.datetime(2025, 3, 10, 17, 0)


def _t(
    uid: int,
    *,
    duration: int = 4800,
    remaining: int | None = None,
    float_min: int | None = 0,
    pct: float = 0.0,
    ms: bool = False,
    summary: bool = False,
    loe: bool = False,
) -> Task:
    return Task(
        unique_id=uid,
        name=f"T{uid}",
        duration_minutes=0 if ms else duration,
        remaining_duration_minutes=remaining,
        stored_total_float_minutes=float_min,
        percent_complete=pct,
        is_milestone=ms,
        is_summary=summary,
        is_level_of_effort=loe,
    )


def _sched(tasks: list[Task]) -> Schedule:
    return Schedule(
        name="s", project_start=PAST, status_date=NOW, tasks=tuple(tasks), relationships=()
    )


def test_float_ratio_both_forms_and_population_filter() -> None:
    s = _sched(
        [
            # A: planned, 5d float over 10d remaining -> ratio 0.5
            _t(1, duration=4800, remaining=4800, float_min=2400),
            # B: in-progress 50%, 1d float over 5d remaining -> ratio 0.2
            _t(2, duration=4800, remaining=2400, float_min=480, pct=50.0),
            # C: planned, 0 float over 20d remaining -> ratio 0.0 (very tight, an offender)
            _t(3, duration=9600, remaining=9600, float_min=0),
            # excluded from the population: milestone, summary, complete, level-of-effort
            _t(4, float_min=2400, ms=True),
            _t(5, duration=4800, remaining=4800, float_min=2400, summary=True),
            _t(6, duration=4800, remaining=0, float_min=2400, pct=100.0),
            _t(7, duration=4800, remaining=4800, float_min=2400, loe=True),
        ]
    )
    out = compute_float_ratio(s)
    primary = out["float_ratio"]
    # mean of per-activity ratios = (0.5 + 0.2 + 0.0) / 3 = 0.2333 -> 0.23
    assert primary.value == round((0.5 + 0.2 + 0.0) / 3, 2) == 0.23
    assert primary.population == 3  # only the three normal planned/in-progress activities
    assert primary.offender_uids == (3,)  # the sub-0.1 (very tight) activity is cited
    # aggregate = sum(float_days) / sum(remaining_days) = (5+1+0) / (10+5+20) = 6/35 = 0.17
    assert out["float_ratio_aggregate"].value == round(6 / 35, 2) == 0.17


def test_float_ratio_remaining_duration_falls_back_to_percent_left() -> None:
    # no stored remaining duration -> duration * (100 - pct)/100 = 4800 * 0.5 = 2400 min = 5 days
    s = _sched([_t(1, duration=4800, remaining=None, float_min=2400, pct=50.0)])
    # float 5 days over remaining 5 days -> 1.0
    assert compute_float_ratio(s)["float_ratio"].value == 1.0


def test_float_ratio_is_na_for_the_whole_project_when_any_remaining_field_rounds_to_zero() -> None:
    """Fuse's N/A is a divide-by-zero, and it takes the WHOLE project with it: one activity whose
    Remaining Duration FIELD rounds to 0 whole days makes that per-activity ratio an error, and
    ``AVERAGE`` propagates it — not just that activity's term. The engine carries it as a **0
    population**, the only "this has no figure" signal its consumers have (the status pill is
    spent on "informational, no threshold"). The ratio-of-means form has no per-activity division
    to fail: it keeps the zero-remaining activity in BOTH sums and still prints. Measured on the
    24-hour Hard_File, whose two ribbons print N/A and -3.58 for the same save."""
    s = _sched(
        [
            # 200 minutes on a 480-minute day is 0.42 -> the field reads 0 whole days
            _t(1, duration=200, remaining=200, float_min=960),
            _t(2, duration=4800, remaining=4800, float_min=2400),  # a healthy 5d / 10d = 0.5
        ]
    )
    out = compute_float_ratio(s)
    primary = out["float_ratio"]
    assert (primary.population, primary.value, primary.offender_uids) == (0, 0.0, ())
    assert primary.status is CheckStatus.NOT_APPLICABLE
    aggregate = out["float_ratio_aggregate"]
    # fields: UID 1 float 2d over remaining 0d, UID 2 float 5d over remaining 10d -> 7 / 10
    assert (aggregate.population, aggregate.value) == (2, 0.7)


def test_float_ratio_is_na_when_the_population_is_empty() -> None:
    # nothing normal and incomplete to score -> both forms NA with no population at all
    out = compute_float_ratio(_sched([_t(1, float_min=2400, ms=True)]))
    assert out["float_ratio"].population == 0
    assert out["float_ratio"].status is CheckStatus.NOT_APPLICABLE
    assert out["float_ratio_aggregate"].population == 0
    assert out["float_ratio_aggregate"].status is CheckStatus.NOT_APPLICABLE


def test_float_ratio_negative_float_drags_the_ratio_below_zero() -> None:
    # behind a constraint: -5d float over 5d remaining -> -1.0 (the right forensic signal)
    s = _sched([_t(1, duration=2400, remaining=2400, float_min=-2400)])
    primary = compute_float_ratio(s)["float_ratio"]
    assert primary.value == -1.0
    assert primary.offender_uids == (1,)  # negative float is, of course, very tight


def test_float_ratio_trend_is_period_to_period_with_deltas() -> None:
    # three periods, loosening then tightening; the delta is the period-over-period change
    v1 = _sched([_t(1, duration=4800, remaining=4800, float_min=480)])  # 1d/10d = 0.1
    v2 = _sched([_t(1, duration=4800, remaining=4800, float_min=1440)])  # 3d/10d = 0.3
    v3 = _sched([_t(1, duration=4800, remaining=4800, float_min=960)])  # 2d/10d = 0.2
    series = compute_float_ratio_trend([v1, v2, v3])
    assert series.values == (0.1, 0.3, 0.2)
    assert series.deltas == (None, round(0.3 - 0.1, 2), round(0.2 - 0.3, 2)) == (None, 0.2, -0.1)
    assert series.populations == (1, 1, 1)


def test_float_ratio_trend_single_version_has_no_prior_delta() -> None:
    series = compute_float_ratio_trend([_sched([_t(1, remaining=4800, float_min=2400)])])
    assert series.values == (0.5,) and series.deltas == (None,)


def test_float_ratio_elapsed_activity_reads_fuses_two_elapsed_day_fields() -> None:
    """An elapsed activity's two fields share the 1,440-minute day but round DIFFERENTLY, and the
    ratio follows what Fuse displays, not what MS Project shows an analyst.

    Fuse's *Total Float* field is RAW elapsed days for an elapsed activity (R-75, ADR-0516: the
    24-hour Hard_File displays UID 146 at -13.333333333333334 for a stored -19,200 minutes) while
    its *Remaining Duration* field is WHOLE elapsed days (R-76, ADR-0518: the same 2,880 minutes
    display 2). So 2,400 stored minutes of float over a 7,200-minute elapsed remainder reads
    (2400/1440) / 5 = 0.33. The engine printed 1.0 here while it divided the float term by the
    WORKING day and left the remainder in elapsed days — a ratio no Fuse grid displays. The
    measured case is Jacked Up Schedule 1's elapsed UID 20 (46,080 minutes: Original 96,
    Remaining 32), inside the 0.77 tile the parity oracle pins.
    """
    elapsed = Task(
        unique_id=1,
        name="elapsed WIP",
        duration_minutes=7200,
        duration_is_elapsed=True,
        remaining_duration_minutes=7200,
        stored_total_float_minutes=2400,
    )
    out = compute_float_ratio(_sched([elapsed]))
    assert out["float_ratio"].value == round((2400 / 1440) / 5, 2) == 0.33


def test_float_ratio_trend_emits_none_not_a_fabricated_zero_for_an_na_version() -> None:
    """The series' "no value" test keys on the POPULATION, and it has to: ``float_ratio`` carries
    a NOT_APPLICABLE *status* even when it carries a figure, so a status-keyed test would blank
    every version of the chart. An N/A version must therefore arrive with population 0 — were it
    to keep its real candidate count, the trend would plot a FABRICATED 0.0 and difference a real
    version against it. The aggregate form still prints for that same version, and the delta is
    None on both sides of the gap."""
    na_version = _sched(
        [
            _t(1, duration=200, remaining=200, float_min=960),  # field 0 -> the version is N/A
            _t(2, duration=4800, remaining=4800, float_min=2400),
        ]
    )
    ok_version = _sched(
        [
            _t(1, duration=4800, remaining=4800, float_min=2400),
            _t(2, duration=4800, remaining=4800, float_min=2400),
        ]
    )
    series = compute_float_ratio_trend([na_version, ok_version])
    assert series.values == (None, 0.5)
    assert series.aggregate_values == (0.7, 0.5)
    assert series.deltas == (None, None)  # nothing to difference the second version against
    assert series.populations == (0, 2)


def test_float_ratio_presents_an_exact_tie_half_away_from_zero() -> None:
    """The reference tool WRITES 0.63 for a mean of exactly 5/8 (TP4_DataCenter_v1's ribbon
    tile), where Python's half-to-even ``round`` writes 0.62 — so both forms present through
    ``round_half_up`` (MF-08, ADR-0467). ADR-0515 left the ``value_dp`` family on half-to-even
    because no reference display was known at 2 dp; for this metric one was found (R-78,
    ADR-0519). A NEGATIVE tie does not occur in the reference corpus, so away-from-zero rather
    than toward positive infinity is the spreadsheet convention applied, not a measurement."""
    s = _sched(
        [
            _t(1, duration=4800, remaining=4800, float_min=2400),  # 5d / 10d = 0.5
            _t(2, duration=9600, remaining=9600, float_min=7200),  # 15d / 20d = 0.75
        ]
    )
    assert compute_float_ratio(s)["float_ratio"].value == 0.63  # mean is exactly 0.625
    assert round(0.625, 2) == 0.62  # …which half-to-even would have printed
