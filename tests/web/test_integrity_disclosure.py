"""/integrity disclosure hardening (audit F2/F4, ADR-0369).

Three silences the 2026-08-07 audit caught: (1) an unresolvable focus target made the
change-effects panel vanish with no explanation (the engine returned None for both "no target"
and "no changes"); (2) skipped reverts were disclosed count-only — never WHICH change; (3) the
DECM-29I401a baseline finding named the activity but showed no magnitude (FX-06 rendered no
old/new dates, no day delta). Renders ``_integrity_body`` on synthetic pairs + the qa facts.
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


def _sched(name: str, t1_days: int) -> Schedule:
    return Schedule(
        name=name,
        project_start=MON,
        tasks=(
            Task(unique_id=1, name="T1", duration_minutes=t1_days * DAY),
            Task(unique_id=2, name="FINISH", duration_minutes=0, is_milestone=True),
        ),
        relationships=(Relationship(predecessor_id=1, successor_id=2),),
    )


def _render(prior: Schedule, current: Schedule, target_uid: int | None) -> str:
    return _integrity_body(
        [prior, current],
        [compute_cpm(prior), compute_cpm(current)],
        target_uid,
        baseline_idx=0,
        comparison_idx=1,
    )


def test_unresolvable_target_renders_a_banner_not_silence() -> None:
    prior, current = _sched("prior", 15), _sched("current", 10)
    page = _render(prior, current, 999)  # UID 999 exists in neither version
    assert "target unavailable" in page
    assert "UID 999" in page
    assert "does not resolve to a scheduled activity" in page
    # no measurement is faked: the effects table and aggregate line are absent
    assert "Effect on target finish" not in page
    assert "working day(s)</b>" not in page
    # true-positive twin: a resolvable target still renders the real table
    ok = _render(prior, current, 2)
    assert "target unavailable" not in ok
    assert "Effect on target finish" in ok and "+5 wd" in ok


def test_skipped_revert_identities_are_listed() -> None:
    tasks = (
        Task(unique_id=1, name="T1", duration_minutes=10 * DAY),
        Task(unique_id=2, name="T2", duration_minutes=10 * DAY),
        Task(unique_id=3, name="FINISH", duration_minutes=0, is_milestone=True),
    )
    prior = Schedule(
        name="prior",
        project_start=MON,
        tasks=tasks,
        relationships=(Relationship(predecessor_id=1, successor_id=2),),
    )
    current = Schedule(
        name="current",
        project_start=MON,
        tasks=tasks,
        relationships=(Relationship(predecessor_id=2, successor_id=1),),
    )
    # restoring the removed 1→2 onto current (which carries 2→1) closes a cycle → skipped
    page = _render(prior, current, 3)
    assert "could not be measured" in page
    assert "skipped-changes" in page  # the identity list exists…
    assert "restore removed FS link 1→2" in page  # …and names the exact change


def test_baseline_finding_carries_old_new_dates_and_day_delta() -> None:
    """Audit F4: the DECM-29I401a finding rendered no magnitude — FX-06's frozen finish named
    UID 131 with neither the old/new baseline dates nor the day delta."""

    def with_bf(name: str, bf: dt.datetime) -> Schedule:
        return Schedule(
            name=name,
            project_start=MON,
            tasks=(
                Task(unique_id=1, name="T1", duration_minutes=10 * DAY, baseline_finish=bf),
                Task(unique_id=2, name="FINISH", duration_minutes=0, is_milestone=True),
            ),
            relationships=(Relationship(predecessor_id=1, successor_id=2),),
        )

    prior = with_bf("prior", dt.datetime(2025, 2, 1, 17, 0))
    current = with_bf("current", dt.datetime(2025, 4, 1, 17, 0))
    page = _render(prior, current, 2)
    assert "baseline dates changed (DECM 29I401a)" in page
    assert "2025-02-01" in page and "2025-04-01" in page  # old AND new dates
    assert "(+59 calendar days)" in page  # 2025-02-01 → 2025-04-01, derived: 28+31 = 59


def test_qa_facts_never_state_a_figure_for_an_unavailable_target() -> None:
    from schedule_forensics.ai.qa import manipulation_forensics_facts

    prior, current = _sched("prior", 15), _sched("current", 10)
    cpms = [compute_cpm(prior), compute_cpm(current)]
    facts = manipulation_forensics_facts([prior, current], cpms, target_uid=999)
    joined = " ".join(f.text for f in facts)
    assert "Aggregate change effect" not in joined  # no fabricated "+0 working day(s)"
    assert "Change effect on" not in joined
    # true-positive twin: a resolvable target still yields both fact families
    ok = " ".join(
        f.text for f in manipulation_forensics_facts([prior, current], cpms, target_uid=2)
    )
    assert "Change effect on" in ok
    assert "Aggregate change effect" in ok and "EVERY detected change reverted together" in ok
