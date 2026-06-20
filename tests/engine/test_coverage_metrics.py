"""Edge-case unit tests for the single-schedule metric families.

Targets the defensive/edge branches the broader fixtures never reach: the staleness NA when
the status date precedes the project start (completion_performance), the Float Ratio scoring
guard for an activity with neither a stored float nor a CPM timing (float_ratio), the Ribbon's
half-up rounding + the all-non-summary-link path (ribbon), and the FEI/BRI status-date-unknown
NA returns (fei_bri). Every assertion checks the real returned value, never a placeholder.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.dcma_audit import audit_schedule
from schedule_forensics.engine.metrics import (
    CheckStatus,
    compute_bri,
    compute_completion_performance,
    compute_fei,
    compute_float_ratio,
    compute_ribbon,
)
from schedule_forensics.engine.metrics.ribbon import _audit_count, _round_half_up
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _sched(
    tasks: list[Task],
    *,
    rels: list[Relationship] | None = None,
    project_start: dt.datetime = MON,
    status_date: dt.datetime | None = None,
) -> Schedule:
    return Schedule(
        name="s",
        project_start=project_start,
        status_date=status_date,
        tasks=tuple(tasks),
        relationships=tuple(rels or []),
    )


# --- completion_performance.py:228 — staleness NA when elapsed <= 0 -----------------------------


def test_staleness_is_na_when_status_date_precedes_project_start() -> None:
    """elapsed = (status - project_start).days <= 0 -> the staleness metric reads NA, not a
    fabricated percentage (completion_performance.py line 228)."""
    # status date BEFORE the project start, yet an actual finish exists (so we pass the first guard)
    status = MON
    project_start = MON + dt.timedelta(days=5)  # project starts AFTER the data date -> elapsed < 0
    t = Task(
        unique_id=1,
        name="done",
        duration_minutes=DAY,
        percent_complete=100.0,
        actual_finish=MON,
    )
    out = compute_completion_performance(
        _sched([t], project_start=project_start, status_date=status)
    )
    stale = out["elapsed_since_last_finish"]
    assert stale.status is CheckStatus.NOT_APPLICABLE
    assert stale.count == 0 and stale.population == 0 and stale.value == 0.0


# --- float_ratio.py:86 — scoring guard: no stored float AND not in the CPM result ----------------


def test_float_ratio_skips_activity_with_no_stored_float_and_no_cpm_timing() -> None:
    """An in-progress, non-summary, non-milestone activity that has remaining duration but is
    absent from the CPM timings AND carries no stored float cannot contribute a ratio — it is
    skipped (float_ratio.py line 86). Here the ONLY scorable task is excluded, so the family is
    NA (population 0)."""
    # A task with positive remaining duration but, crucially, NOT present in the cpm_result we pass.
    scorable = Task(
        unique_id=99,
        name="orphan",
        duration_minutes=DAY,
        remaining_duration_minutes=DAY,
        percent_complete=0.0,
        stored_total_float_minutes=None,
    )
    sch = _sched([scorable])
    # Hand a CPMResult that does NOT contain UID 99 (compute it for an empty-task copy).
    empty_cpm = compute_cpm(_sched([]))
    assert 99 not in empty_cpm.timings
    out = compute_float_ratio(sch, empty_cpm)
    assert out["float_ratio"].status is CheckStatus.NOT_APPLICABLE
    assert out["float_ratio"].population == 0
    assert out["float_ratio_aggregate"].population == 0


def test_float_ratio_scores_activity_with_stored_float_even_when_absent_from_cpm() -> None:
    """Contrast: the same orphan WITH a stored total float is scored (the guard's other arm) —
    proving line 86 only skips when BOTH the stored value and the CPM timing are missing."""
    scorable = Task(
        unique_id=99,
        name="orphan",
        duration_minutes=DAY,
        remaining_duration_minutes=DAY,
        percent_complete=0.0,
        stored_total_float_minutes=DAY,  # one working day of stored float
    )
    sch = _sched([scorable])
    empty_cpm = compute_cpm(_sched([]))
    out = compute_float_ratio(sch, empty_cpm)
    assert out["float_ratio"].population == 1
    # one day of float over one day of remaining work -> ratio 1.0
    assert out["float_ratio"].value == 1.0


# --- ribbon.py:69 (_round_half_up) and the all-non-summary link branch (90->89) ------------------


def test_ribbon_round_half_up_rounds_away_from_zero() -> None:
    """Fuse rounds half away from zero, not banker's rounding (ribbon.py _round_half_up)."""
    assert _round_half_up(2.625) == 2.63  # banker's rounding would give 2.62
    assert _round_half_up(2.635) == 2.64


def test_ribbon_audit_count_returns_zero_when_check_absent() -> None:
    """_audit_count falls through to 0 when no audit check carries the requested metric id
    (ribbon.py line 69) — the lookup miss. The real ribbon flow always finds DCMA05/DCMA07, so
    this fall-through needs a direct call with an id the audit does not contain."""
    sch = _sched([Task(unique_id=1, name="T", duration_minutes=DAY)])
    audit = audit_schedule(sch, compute_cpm(sch))
    assert _audit_count(audit, "NO_SUCH_CHECK") == 0
    # contrast: a present id returns its real count (the line-68 hit), proving 69 is the miss arm
    assert _audit_count(audit, "DCMA05") == next(
        c.count for c in audit.checks if c.metric_id == "DCMA05"
    )


def test_ribbon_counts_links_among_non_summary_and_skips_external_links() -> None:
    """A link whose endpoints are both non-summary is counted into logic density (the 90->89
    loop body runs); the branch is also exercised when a relationship touches a summary so the
    `if` is False and the loop continues. Validates the resulting density + missing-logic."""
    tasks = [
        Task(unique_id=1, name="A", duration_minutes=DAY),
        Task(unique_id=2, name="B", duration_minutes=DAY),
        # a summary endpoint so the predecessor/successor filter rejects its links
        Task(unique_id=3, name="WBS", duration_minutes=DAY, is_summary=True),
        Task(unique_id=4, name="C", duration_minutes=DAY),
    ]
    rels = [
        Relationship(predecessor_id=1, successor_id=2),  # both non-summary -> counted
        Relationship(predecessor_id=3, successor_id=4),  # summary predecessor -> NOT counted
    ]
    sch = _sched(tasks, rels=rels)
    cpm = compute_cpm(sch)
    audit = audit_schedule(sch, cpm)
    ribbon = compute_ribbon(sch, cpm, audit)
    # 3 non-summary activities (1,2,4); exactly ONE counted link (1->2): density = 2*1/3 = 0.67
    assert ribbon.logic_density == _round_half_up(2 * 1 / 3)
    # 1 and 2 form a chain; 4 is an open end (no counted logic). Missing logic counts the open ends.
    assert ribbon.missing_logic >= 1


# --- fei_bri.py:63, 97 — NA returns when the status date is unknown ------------------------------


def test_fei_is_na_without_a_status_date() -> None:
    """compute_fei returns the NA-shaped starts/finish results when status_date is None
    (fei_bri.py line 63 path)."""
    sch = _sched(
        [Task(unique_id=1, name="T", duration_minutes=DAY, start=MON, finish=MON)],
        status_date=None,
    )
    fei = compute_fei(sch)
    assert fei["fei_starts"].status is CheckStatus.NOT_APPLICABLE
    assert fei["fei_finish"].status is CheckStatus.NOT_APPLICABLE
    assert fei["fei_starts"].population == 0 and fei["fei_finish"].population == 0


def test_bri_is_na_without_a_status_date() -> None:
    """compute_bri returns the NA-shaped result when status_date is None (fei_bri.py line 97)."""
    sch = _sched(
        [Task(unique_id=1, name="T", duration_minutes=DAY, baseline_finish=MON)],
        status_date=None,
    )
    bri = compute_bri(sch)
    assert bri.status is CheckStatus.NOT_APPLICABLE
    assert bri.metric_id == "bri_cumulative"
    assert bri.population == 0 and bri.value == 0.0
