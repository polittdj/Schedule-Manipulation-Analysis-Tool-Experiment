"""REC-01 (audit 2026-08-16): a provenance DISCLOSURE never carries a quantified figure.

ADR-0407 wired ``CPMResult.actual_start_driven`` to the analyst as an INFO/OPPORTUNITY
finding and justified the category choice like this:

    "``web/risks.py`` builds the risk matrix, the risk ranking, and the recovery plan from
    RISK + CONCERN only, so an OPPORTUNITY/INFO disclosure informs without ever becoming a
    threat row or a recovery action."

That claim was verified against ``web/risks.py`` ONLY. It is false of the tree as a whole:
``_quantify`` quantifies every finding uniformly from its citations, so the disclosure
picked up ``impact_days`` = the worst negative float among the activities it cites — a
population selected for *provenance*, not for exposure — and every downstream surface then
relabelled that exposure as recovery. Measured on the pre-fix tree, one started activity
20 working days behind its deadline:

    briefing 5.2 Opportunities   column "Potential recovery"  -> "20 wd"
    briefing 6.  Recommended Actions column "Expected effect" -> "20 wd"
    briefing 6.2                 "up to about 20 workday(s) ... potentially recoverable"
    /risks card                  risk score 20/25 (rk-extreme), "Schedule exposure: 20.0 wd"

The finding's own course of action says re-tying logic "cannot and should not move a date
that already happened" — its recoverable contribution is definitionally ZERO. The 20 wd was
fabricated by relabelling, which is Law 2 and the design system's "missing shows an em dash,
never a fabricated figure".

The fix is a declared kind, not an inferred one: a producer marks its finding
``is_disclosure=True`` and ``_quantify`` leaves it unquantified, so every surface's existing
``is not None`` guard does the rest. ``driving_path`` — the OTHER INFO/OPPORTUNITY finding,
and a genuine recovery lever ("recovering any of them pulls the focus date in") — must keep
its quantification: it is the negative control that proves this test is about disclosures and
not about the category.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.recommendations import (
    Category,
    Likelihood,
    Severity,
    recommend,
)
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)  # a Monday, working-day start
DAY = 480


def _behind_schedule_with_a_recorded_actual_start() -> Schedule:
    """A started activity floored at its recorded actual start AND behind a deadline.

    UID 1 records an actual start a week past its logic date, so ADR-0391 floors it there and
    reports it on ``actual_start_driven``; its deadline is a week in, which it cannot meet, so
    its total float is -20 wd. Negative float is what ``_quantify`` converts into exposure —
    the raw material of the fabricated recovery figure.
    """
    start = MON + dt.timedelta(days=7)
    return Schedule(
        name="REC-01",
        project_start=MON,
        tasks=(
            Task(
                unique_id=1,
                name="started late, behind its deadline",
                duration_minutes=20 * DAY,
                start=start,
                finish=start + dt.timedelta(days=27, hours=9),
                actual_start=start,
                deadline=MON + dt.timedelta(days=7),
            ),
            Task(unique_id=2, name="successor", duration_minutes=5 * DAY),
        ),
        relationships=(Relationship(predecessor_id=1, successor_id=2),),
    )


def test_the_actual_start_disclosure_is_marked_as_a_disclosure() -> None:
    """The kind is DECLARED by the producer, never inferred from category or metric id.

    Category cannot carry it: ``driving_path`` is INFO/OPPORTUNITY too and is a real lever.
    A hard-coded metric-id set in the consumer would rot the moment a second disclosure is
    added, so the flag rides on the finding itself.
    """
    s = _behind_schedule_with_a_recorded_actual_start()
    f = next(f for f in recommend(s) if f.metric_id == "actual_start_driven")
    assert f.is_disclosure is True


def test_the_disclosure_carries_no_quantified_exposure() -> None:
    """Pre-fix this finding came back impact_days=20.0, float_days=-20.0, CERTAIN, 20/25.

    A provenance note asserts nothing about exposure. Leaving the quantified fields None is
    what makes every downstream ``is not None`` guard render an em dash instead of a number.
    """
    s = _behind_schedule_with_a_recorded_actual_start()
    f = next(f for f in recommend(s) if f.metric_id == "actual_start_driven")
    assert f.impact_days is None
    assert f.float_days is None
    assert f.driving_float_days is None


def test_the_disclosure_does_not_score_as_a_threat() -> None:
    """INFO + RARE = 1/25, the floor — not the 20/25 "rk-extreme" band it rendered pre-fix.

    ``impact_rank`` falls back to severity when exposure is None, and ``_quantify``'s
    likelihood fallback maps INFO -> RARE. Both must apply, so the card stops presenting a
    provenance note with the visual weight of a near-worst-case threat.
    """
    s = _behind_schedule_with_a_recorded_actual_start()
    f = next(f for f in recommend(s) if f.metric_id == "actual_start_driven")
    assert f.likelihood is Likelihood.RARE
    assert f.impact_score == 1
    assert f.likelihood_score == 1
    assert f.risk_score == 1


def test_a_real_recovery_lever_keeps_its_quantification() -> None:
    """Negative control: ``driving_path`` is INFO/OPPORTUNITY and stays fully quantified.

    This is the test that proves the fix targets DISCLOSURES rather than the OPPORTUNITY
    category — a fix keyed on category would break this, and a fix keyed on severity would
    break it too (both findings are INFO).
    """
    s = _behind_schedule_with_a_recorded_actual_start()
    findings = recommend(s, target_uid=2)
    lever = next(f for f in findings if f.metric_id == "driving_path")
    assert lever.category is Category.OPPORTUNITY  # same category as the disclosure
    assert lever.severity is Severity.INFO  # and the same severity
    assert lever.is_disclosure is False  # but not a disclosure
    assert lever.impact_days is not None  # so it keeps its exposure
    assert lever.float_days is not None


def test_an_unquantified_finding_is_still_cited() -> None:
    """Dropping the numbers must not drop the provenance (section 6: never uncited)."""
    s = _behind_schedule_with_a_recorded_actual_start()
    f = next(f for f in recommend(s) if f.metric_id == "actual_start_driven")
    assert f.citations and f.citations[0].unique_id == 1
    assert f.category is Category.OPPORTUNITY and f.severity is Severity.INFO


def test_the_cpm_still_floors_the_task_at_its_actual_start() -> None:
    """Guard the premise: if the floor stopped firing, every test above would pass vacuously.

    QC-1's "a check that has never failed has proven nothing" applies to fixtures too — this
    asserts the probe schedule really does produce the disclosure channel and really is
    behind, so the assertions above are about the fix and not about an empty population.
    """
    s = _behind_schedule_with_a_recorded_actual_start()
    cpm = compute_cpm(s)
    assert cpm.actual_start_driven == (1,)
    assert cpm.timings[1].total_float == -20 * DAY  # the exposure that used to leak
