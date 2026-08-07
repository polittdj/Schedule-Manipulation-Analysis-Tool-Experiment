"""Sub-day counterfactual effects render signed "<1 wd", never "no effect" (audit F1/F7).

``round()`` maps a true sub-day effect (even exactly half a working day, via round-half-even) to
0 wd; the /integrity change-effects table previously rendered that as "no effect" and the
aggregate line as "+0 working day(s)" — a Law 2 lie about a real, engine-measured movement. The
page now reads the exact ``*_minutes`` fields. These tests render ``_integrity_body`` (the same
HTML the route returns through ``_page``) on synthetic model pairs, plus the Ask-the-AI fact.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.integrity import _integrity_body

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _sched(name: str, t1_minutes: int) -> Schedule:
    """T1 → FINISH milestone; T1's duration is the experiment's only variable."""
    return Schedule(
        name=name,
        project_start=MON,
        tasks=(
            Task(unique_id=1, name="T1", duration_minutes=t1_minutes),
            Task(unique_id=2, name="FINISH", duration_minutes=0, is_milestone=True),
        ),
        relationships=(Relationship(predecessor_id=1, successor_id=2),),
    )


def _render(prior: Schedule, current: Schedule) -> str:
    return _integrity_body(
        [prior, current],
        [compute_cpm(prior), compute_cpm(current)],
        None,
        baseline_idx=0,
        comparison_idx=1,
    )


def test_sub_day_cut_renders_signed_lt1_wd_not_no_effect() -> None:
    # current cut T1 by exactly half a working day (240 min): round-half-even hides it as 0 wd
    page = _render(_sched("prior", 10 * DAY + 240), _sched("current", 10 * DAY))
    assert "+&lt;1 wd" in page  # per-change target column AND project column, signed
    assert "no effect" not in page  # the audit-F1 lie
    assert "+&lt;1 working day" in page  # the "all changes together" aggregate line
    assert "+0 working day(s)" not in page
    # the duration label carries the exact minutes instead of collapsing (audit F7)
    assert "(4800→5040 min)" in page


def test_sub_day_raise_renders_negative_sign() -> None:
    # current RAISED T1 by 240 min: reverting pulls the finish IN — "-<1 wd", ok-toned
    page = _render(_sched("prior", 10 * DAY), _sched("current", 10 * DAY + 240))
    assert "-&lt;1 wd" in page
    assert "no effect" not in page
    assert "-&lt;1 working day" in page


def test_true_zero_still_says_no_effect_and_whole_days_keep_legacy_form() -> None:
    """TRUE-POSITIVE TWINS: a genuinely zero-effect change must still read "no effect" (honest
    zero stays honest), and a ≥1-day effect keeps the legacy "+N wd" / "+N working day(s)"."""

    def offpath(name: str, t1_days: int) -> Schedule:
        # T3 (30d) drives the milestone; T1 is far off the path, so a T1 change has NO effect
        return Schedule(
            name=name,
            project_start=MON,
            tasks=(
                Task(unique_id=1, name="T1", duration_minutes=t1_days * DAY),
                Task(unique_id=3, name="T3", duration_minutes=30 * DAY),
                Task(unique_id=2, name="FINISH", duration_minutes=0, is_milestone=True),
            ),
            relationships=(
                Relationship(predecessor_id=1, successor_id=2),
                Relationship(predecessor_id=3, successor_id=2),
            ),
        )

    zero_page = _render(offpath("prior", 5), offpath("current", 4))
    assert "no effect" in zero_page
    assert "&lt;1 wd" not in zero_page
    assert "+0 working day(s)" in zero_page  # the aggregate keeps its legacy true-zero text

    whole_page = _render(_sched("prior", 15 * DAY), _sched("current", 10 * DAY))
    assert "+5 wd" in whole_page
    assert "+5 working day(s)" in whole_page
    assert "&lt;1" not in whole_page


def test_ai_fact_states_sub_day_effect_not_no_effect() -> None:
    """The Ask-the-AI fact base previously answered "no effect on this target" for a real
    sub-day effect — the exact wrong answer this engine module exists to prevent (ADR-0162)."""
    from schedule_forensics.ai.qa import manipulation_forensics_facts

    prior, current = _sched("prior", 10 * DAY + 240), _sched("current", 10 * DAY)
    facts = manipulation_forensics_facts(
        [prior, current], [compute_cpm(prior), compute_cpm(current)], target_uid=2
    )
    joined = " ".join(f.text for f in facts)
    assert "less than one working day LATER" in joined
    assert "no effect on this target" not in joined

    # true-zero twin: a change with genuinely zero effect still states "no effect on this target"
    def offpath(name: str, t1_days: int) -> Schedule:
        return Schedule(
            name=name,
            project_start=MON,
            tasks=(
                Task(unique_id=1, name="T1", duration_minutes=t1_days * DAY),
                Task(unique_id=3, name="T3", duration_minutes=30 * DAY),
                Task(unique_id=2, name="FINISH", duration_minutes=0, is_milestone=True),
            ),
            relationships=(
                Relationship(predecessor_id=1, successor_id=2),
                Relationship(predecessor_id=3, successor_id=2),
            ),
        )

    p0, c0 = offpath("prior", 5), offpath("current", 4)
    facts0 = manipulation_forensics_facts(
        [p0, c0], [compute_cpm(p0), compute_cpm(c0)], target_uid=2
    )
    joined0 = " ".join(f.text for f in facts0)
    assert "no effect on this target" in joined0
    assert "less than one working day" not in joined0
