"""Fig 5-30 guideline band + SRA margin-sufficiency reads (F3c-fuller, ADR-0254).

Hand-computed band arithmetic (the stepped burndown that mimics the Fig 5-30 rates), the
band-position classifier, and the §7.3.3.2.3 CDF reads — including the equivalence pins that
tie the pure reads back to the SRA engine's own outputs (Law 2: the panel can never diverge
from the trusted solver):

* ``_cdf_at(cdf, deterministic) == deterministic_percentile`` on a REAL ``compute_sra`` result;
* ``deterministic_margin_bounds`` reproduces ``compute_sra_ssi``'s all-ML anchor exactly, and
  ``E == D`` when no margin activity exists.
"""

from __future__ import annotations

import datetime as dt

import pytest

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.margin_guideline import (
    FIG_5_30_DEFAULT_RATES,
    GuidelineBandConfig,
    _cdf_at,
    _finish_at,
    band_position,
    expected_margin_band,
    margin_risk_read,
)
from schedule_forensics.engine.sra import (
    SRAConfig,
    compute_sra,
    compute_sra_ssi,
    deterministic_margin_bounds,
)
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)  # a Monday, working-day start
DAY = 480


def _task(uid: int, dur_days: float, name: str | None = None, **kw: object) -> Task:
    return Task(
        unique_id=uid,
        name=name or f"T{uid}",
        duration_minutes=int(dur_days * DAY),
        **kw,  # type: ignore[arg-type]
    )


def _rel(p: int, s: int) -> Relationship:
    return Relationship(predecessor_id=p, successor_id=s, type=RelationshipType.FS, lag_minutes=0)


def _sched(tasks: list[Task], rels: list[Relationship] | None = None) -> Schedule:
    return Schedule(
        name="S", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels or [])
    )


# --- tier-a: the band ------------------------------------------------------------------------

_CFG = GuidelineBandConfig(
    # CR 2026-01-01; I&T 2027-01-01 (365 d); ship 2027-07-01 (181 d); launch 2027-10-01 (92 d)
    phase_dates=(
        dt.date(2026, 1, 1),
        dt.date(2027, 1, 1),
        dt.date(2027, 7, 1),
        dt.date(2027, 10, 1),
    )
)


def test_band_at_confirmation_review_is_the_full_three_phase_sum() -> None:
    # hand arithmetic: low = 365*30/365 + 181*60/365 + 92*30/365 = 30 + 29.8 + 7.6 = 67.3
    #                  high = 365*60/365 + 181*75/365 + 92*84/365 = 60 + 37.2 + 21.2 = 118.4
    (pt,) = [
        p
        for p in expected_margin_band(_CFG, (dt.date(2026, 1, 1),))
        if p.date == dt.date(2026, 1, 1)
    ]
    assert (pt.low_wd, pt.high_wd) == (67.3, 118.4)


def test_band_is_stepped_piecewise_and_zero_after_launch() -> None:
    pts = {
        p.date: p
        for p in expected_margin_band(
            _CFG, (dt.date(2025, 6, 1), dt.date(2027, 8, 15), dt.date(2027, 11, 1))
        )
    }
    # before CR: clamped to the full sum (never grows further back)
    assert (pts[dt.date(2025, 6, 1)].low_wd, pts[dt.date(2025, 6, 1)].high_wd) == (67.3, 118.4)
    # inside phase 3 (47 remaining of 92 days): low = 47*30/365 = 3.9, high = 47*84/365 = 10.8
    assert (pts[dt.date(2027, 8, 15)].low_wd, pts[dt.date(2027, 8, 15)].high_wd) == (3.9, 10.8)
    # after launch: zero, never negative
    assert (pts[dt.date(2027, 11, 1)].low_wd, pts[dt.date(2027, 11, 1)].high_wd) == (0.0, 0.0)
    # the phase boundaries are always included so a chart renders the kinks exactly
    assert set(_CFG.phase_dates) <= set(pts)


def test_band_config_validation() -> None:
    with pytest.raises(ValueError):
        GuidelineBandConfig(
            phase_dates=(
                dt.date(2027, 1, 1),
                dt.date(2026, 1, 1),
                dt.date(2027, 7, 1),
                dt.date(2027, 10, 1),
            )
        )
    with pytest.raises(ValueError):
        GuidelineBandConfig(
            phase_dates=_CFG.phase_dates, rates=((0.0, 30.0), *FIG_5_30_DEFAULT_RATES[1:])
        )


def test_band_position_edges() -> None:
    assert band_position(9.9, 10, 20) == "below"
    assert band_position(10.0, 10, 20) == "within"  # the edge itself is inside the band
    assert band_position(20.0, 10, 20) == "within"
    assert band_position(20.1, 10, 20) == "above"


# --- tier-b: the CDF reads -------------------------------------------------------------------


def test_cdf_at_reproduces_deterministic_percentile_on_a_real_sra_result() -> None:
    # The pin that ties the pure read to the engine: sra stores deterministic_percentile as
    # bisect_right(sorted_finishes, D)/n and builds the CDF from the SAME samples, so the
    # step read at D must reproduce the stored figure exactly.
    sch = _sched([_task(1, 2), _task(2, 3), _task(3, 1)], [_rel(1, 2), _rel(2, 3)])
    result = compute_sra(sch, compute_cpm(sch), config=SRAConfig(iterations=300, seed=7))
    assert _cdf_at(result.cdf, result.deterministic_finish) == result.deterministic_percentile


def test_finish_at_exact_breakpoints_and_beyond() -> None:
    cdf = ((100, 0.25), (200, 0.5), (300, 0.75), (400, 1.0))
    assert _finish_at(cdf, 25.0) == 100  # exact breakpoint matches (epsilon-guarded)
    assert _finish_at(cdf, 50.0) == 200
    assert _finish_at(cdf, 50.1) == 300  # just past a breakpoint steps up
    assert _finish_at(cdf, 100.0) == 400
    assert _finish_at(cdf, 5.0) == 100  # below the first breakpoint: the minimum


def test_margin_risk_read_consistency_and_verdicts() -> None:
    cdf = ((100, 0.25), (200, 0.5), (300, 0.75), (400, 1.0))
    read = margin_risk_read(cdf, deterministic_finish=300, zero_margin_finish=200, wmpd=DAY)
    assert read.covered_pct == 75.0  # CDF(300) = 0.75
    assert read.verdict == "sufficient"  # 75 >= watch 70
    # internal consistency: covered <=> finish <= D <=> margin_needed <= margin_wd
    for row in read.rows:
        assert row.covered == (row.finish_offset <= 300)
        assert row.covered == (row.margin_needed_wd <= read.margin_wd + 1e-9)
    # verdict thresholds classify the SAME covered percentile differently
    assert margin_risk_read(cdf, 300, 200, wmpd=DAY, watch_pct=80).verdict == "watch"
    assert (
        margin_risk_read(cdf, 300, 200, wmpd=DAY, watch_pct=90, corrective_pct=80).verdict
        == "corrective"
    )


def test_margin_risk_read_degenerate_yields_no_verdict() -> None:
    read = margin_risk_read(((500, 1.0),), 500, 500, wmpd=DAY)
    assert read.degenerate is True and read.verdict is None
    assert read.covered_pct == 100.0  # disclosed, but no verdict is issued on a point mass


def test_margin_risk_read_rejects_empty_cdf_and_bad_wmpd() -> None:
    with pytest.raises(ValueError):
        margin_risk_read((), 1, 0, wmpd=DAY)
    with pytest.raises(ValueError):
        margin_risk_read(((1, 1.0),), 1, 0, wmpd=0)


# --- the (D, E) bounds -----------------------------------------------------------------------


def test_deterministic_margin_bounds_reproduce_the_ssi_anchor() -> None:
    # D must equal compute_sra_ssi's deterministic_finish EXACTLY (same all-ML override map,
    # same finish read — the ADR-0106 equivalence), and zeroing the margin pulls E in by the
    # margin's duration on the driving chain.
    sch = _sched(
        [
            _task(1, 5, "Work"),
            _task(2, 4, "Schedule MARGIN"),
            _task(3, 0, "Deliver", is_milestone=True),
        ],
        [_rel(1, 2), _rel(2, 3)],
    )
    ssi = compute_sra_ssi(sch, config=SRAConfig(iterations=100, seed=3))
    d_anchor, e_zero = deterministic_margin_bounds(sch, None, frozenset({2}))
    assert d_anchor == ssi.deterministic_finish
    assert d_anchor - e_zero == 4 * DAY  # the 4-day margin sat on the driving chain


def test_deterministic_margin_bounds_no_margin_means_e_equals_d() -> None:
    sch = _sched([_task(1, 5), _task(2, 3)], [_rel(1, 2)])
    d_anchor, e_zero = deterministic_margin_bounds(sch, None, frozenset())
    assert d_anchor == e_zero
