"""MC-01 (audit 2026-08-16): a fired register OPPORTUNITY shortens work, it does not delete it.

``ScheduleRisk.impact_days`` is documented as *"additive working days when it fires (>=0 risk,
**<0 opportunity**)"*, and opportunities are a first-class product feature with their own 5x5
Opportunity matrix. Both engines nonetheless collapsed a fired opportunity through
``max(0, impact)``:

    overrides[u] = max(0, impact)      # sra.py:1701, and the twin at jcl.py:319

For a NEGATIVE impact that is 0 — the activity is replaced by a zero-duration task rather than
being shortened by the opportunity. Measured on the pre-fix tree (20 d driver -> 5 d focus,
duration noise switched off so the register is the only variable, focus = uid 2):

    no register                  P50 = 25.0 wd
    -5 d opportunity on driver   P50 =  5.0 wd     <- the driver vanished
    correct if honoured          P50 = 20.0 wd

A 15-working-day OPTIMISTIC error in a figure an SRA quotes. Law 2 calls a fast wrong number
worthless; an optimistic one in a testimony deliverable is worse than worthless.

**The parity leg is UNVERIFIED and says so.** ADR-0359 established that a fired risk REPLACES
the sampled duration, measured against SSI's own export — but only for POSITIVE impacts, where
replacement and "add then subtract the ML" are distinguishable and replacement won. No
committed SSI artifact exposes a fired NEGATIVE impact: the reference exports carry only the
aggregate distribution under an ``Includes Risks/Opportunities? Yes`` toggle, never a per-risk
register listing. So these tests pin the DOCUMENTED semantic (additive, floored at 0) and the
positive-impact tests below pin ADR-0359 unchanged. If an SSI opportunity export ever arrives
and disagrees, this module is the thing to re-baseline — deliberately, not silently.
"""

from __future__ import annotations

import datetime as dt

import pytest

from schedule_forensics.engine.sra import ScheduleRisk, SRAConfig, compute_sra_ssi
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _chain() -> Schedule:
    """A 20-working-day driver into a 5-working-day focus: 25 wd with nothing applied.

    Cost-loaded because ``compute_jcl`` refuses a schedule without a BAC (a duration-only run
    is an SCL, not a JCL). The cost carries no weight in these assertions — every one of them
    reads the FINISH marginal — but it lets the identical fixture drive both engines, which is
    the point: the two blocks are mirrors and must be measured against one ruler.
    """
    return Schedule(
        name="MC-01",
        project_start=MON,
        tasks=(
            Task(unique_id=1, name="driver", duration_minutes=20 * DAY, budgeted_cost=100.0),
            Task(unique_id=2, name="focus", duration_minutes=5 * DAY, budgeted_cost=50.0),
        ),
        relationships=(Relationship(predecessor_id=1, successor_id=2),),
    )


def _cfg() -> SRAConfig:
    """Duration noise OFF (low = ml = high = 1.0) so the register is the only variable.

    Without this the triangular sampler's spread would swamp a 5-day effect and the test would
    measure the sampler rather than the fix.
    """
    return SRAConfig(
        iterations=200,
        seed=7,
        auto_low=1.0,
        auto_most_likely=1.0,
        auto_high=1.0,
        target_uid=2,
        use_risk_register=True,
    )


def _risk(impact_days: float, *, affected: tuple[int, ...] = (1,), rid: str = "R") -> ScheduleRisk:
    return ScheduleRisk(
        id=rid,
        name=f"certain {impact_days:g} d",
        probability=1.0,  # certain: every iteration fires, so P50 is the fired outcome
        impact_days=impact_days,
        affected=affected,
    )


def _p50_wd(*risks: ScheduleRisk) -> float:
    return compute_sra_ssi(_chain(), config=_cfg(), risks=risks).p50 / DAY


def _jcl_p50_wd(*risks: ScheduleRisk) -> float:
    """The same question asked of the JCL engine, whose block mirrors the SRA one (ADR-0408).

    ``JCLResult`` publishes the finish marginal as a CDF of working-minute offsets rather than
    a scalar percentile, so the P50 is read off it directly — the same distribution ADR-0269
    pins byte-identical to the SSI run's.
    """
    from schedule_forensics.engine.jcl import compute_jcl

    cdf = compute_jcl(_chain(), config=_cfg(), risks=risks).finish_cdf
    return next(off for off, cum in cdf if cum >= 0.5) / DAY


# --------------------------------------------------------------------------- SRA


def test_baseline_chain_is_twenty_five_working_days() -> None:
    """The premise. If this drifts, every number below is measured against the wrong ruler."""
    assert _p50_wd() == pytest.approx(25.0)


def test_a_fired_opportunity_shortens_the_driver_instead_of_deleting_it() -> None:
    """MC-01 itself: -5 d on a 20 d driver leaves 15 d of driver, so the chain is 20 wd.

    Pre-fix this returned 5.0 — the whole driver gone, not five days of it.
    """
    assert _p50_wd(_risk(-5.0)) == pytest.approx(20.0)


def test_a_fired_risk_still_REPLACES_the_duration() -> None:
    """ADR-0359 unchanged, and this is the test that stops the fix over-reaching.

    +5 d on a 20 d driver replaces it with a 5 d driver => 10 wd. A "fix" that made every
    impact additive would give 25 + 5 = 30 here and break the parity ADR-0359 measured against
    SSI's own export.
    """
    assert _p50_wd(_risk(5.0)) == pytest.approx(10.0)


def test_an_opportunity_larger_than_the_duration_floors_at_zero_never_negative() -> None:
    """-50 d on the 5 d FOCUS floors its duration at 0, so the chain is the 20 d driver.

    The floor is the ONE thing ``max(0, ...)`` had right and it must survive — but it has to be
    asserted where it is *observable*. Aimed at the driver instead, this test cannot fail:
    ``compute_cpm`` does NOT clamp a negative duration (measured: an override of -14400 min
    yields ``early_finish = -14400``), yet the successor floors at the project start anyway, so
    the focus finish reads 5.0 wd with or without the floor. A mutation battery caught exactly
    that — M5 survived until the observable moved here.

    On the focus the leak is unmissable: without the floor the focus finishes 45 working days
    before the predecessor it depends on, i.e. a NEGATIVE project finish.
    """
    assert _p50_wd(_risk(-50.0, affected=(2,))) == pytest.approx(20.0)


def test_a_zero_impact_entry_changes_nothing() -> None:
    """The sign boundary. 0 is a risk (>=0) and replaces with 0 — ADR-0359's own rule.

    Pinned so the ``impact >= 0`` branch cannot be silently loosened to ``> 0``, which would
    reroute a 0-day entry through the opportunity path and change a shipped number.
    """
    assert _p50_wd(_risk(0.0)) == pytest.approx(5.0)


def test_mixed_entries_on_one_activity_settle_on_the_summed_sign() -> None:
    """+10 and -5 on the same driver sum to +5, a net risk => replacement => 10 wd.

    ADR-0359 already says several risks on one activity "replace with their summed impacts";
    summing FIRST and branching on the sign of the total keeps that sentence literally true and
    is the only reading under which the mixed case stays continuous.
    """
    assert _p50_wd(_risk(10.0, rid="R1"), _risk(-5.0, rid="O1")) == pytest.approx(10.0)


def test_a_net_negative_mix_shortens_rather_than_zeroing() -> None:
    """+3 and -5 sum to -2, a net opportunity => 20 - 2 = 18 d driver => 23 wd.

    Under the pre-fix code this was max(0, -2) = 0. Under a "replace on any positive present"
    reading it would be 3 - 5 -> 0 too. Only sign-of-the-sum gives the continuous answer.
    """
    assert _p50_wd(_risk(3.0, rid="R1"), _risk(-5.0, rid="O1")) == pytest.approx(23.0)


# --------------------------------------------------------------------------- JCL twin


def test_jcl_baseline_matches_the_sra_baseline() -> None:
    """ADR-0408 made the engines mirror each other; the premise must hold on both."""
    assert _jcl_p50_wd() == pytest.approx(25.0)


def test_jcl_opportunity_shortens_the_driver_too() -> None:
    """The twin at jcl.py:319 had the identical defect and needs the identical fix.

    A fix applied to only one engine would leave the JCL page quoting the optimistic number
    while the SRA page quoted the right one — the two-surfaces disagreement that localised
    MF-02 in a single probe.
    """
    assert _jcl_p50_wd(_risk(-5.0)) == pytest.approx(20.0)


def test_jcl_risk_still_replaces() -> None:
    """ADR-0359 preserved on the JCL side as well — the twin's negative control."""
    assert _jcl_p50_wd(_risk(5.0)) == pytest.approx(10.0)
