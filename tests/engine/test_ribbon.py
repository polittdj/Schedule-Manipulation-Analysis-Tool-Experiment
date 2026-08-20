"""Fuse Ribbon metrics — calibrated to the operator's Acumen Fuse workbook.

See docs/FUSE-VALIDATION.md for the reference values these pin.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.dcma_audit import audit_schedule
from schedule_forensics.engine.metrics.ribbon import RibbonMetrics, compute_ribbon
from schedule_forensics.importers.mspdi import parse_mspdi

FIX = Path(__file__).resolve().parents[1] / "fixtures"
TP = FIX / "test_projects"
GOLD = FIX / "golden" / "project2_5"

# project -> (path, missing_logic, logic_density, critical, hard, neg_float, lags, leads, merge)
_FUSE = {
    "Project2": (GOLD / "Project2.mspdi.xml", 6, 2.79, 41, 0, 0, 2, 0, 10),
    "TP1": (TP / "TP1_Library_Progressed.xml", 4, 2.61, 11, 0, 0, 3, 0, 1),
    "TP2": (TP / "TP2_Bridge_4x10_Calendar.xml", 2, 2.63, 7, 0, 0, 0, 0, 1),
    # TP3 negative_float DELIBERATELY re-pinned 3 → 4 (multi-calendar/constraint-slack ADR):
    # UID 41's Must-Finish-On is violated by its predecessor chain (logic finish 06-30 vs MFO
    # 06-26), and MS Project reports a violated pin as NEGATIVE slack on the pinned task itself
    # — proven by the Jacked-2 oracle (UID 30, same SNET-pred→MFO shape, STORED TotalSlack
    # -2400). The workbook's 3 was captured against a TP3 artifact whose finish diverges from
    # this fixture by 5 days (docs/FUSE-VALIDATION.md "to reconcile" row), so the committed
    # fixture never matched that capture's dates to begin with.
    "TP3": (TP / "TP3_Outage_DCMA_Seeded.xml", 8, 2.38, 5, 2, 4, 3, 1, 2),
    "TP4v1": (TP / "TP4_DataCenter_v1.xml", 2, 2.67, 8, 0, 0, 0, 0, 1),
    "TP4v2": (TP / "TP4_DataCenter_v2.xml", 2, 2.67, 7, 0, 0, 0, 0, 1),
    "TP4v3": (TP / "TP4_DataCenter_v3.xml", 2, 2.67, 7, 0, 0, 0, 0, 1),
    "TP4v4": (TP / "TP4_DataCenter_v4.xml", 2, 2.67, 5, 0, 0, 0, 0, 1),
    "TP4v5": (TP / "TP4_DataCenter_v5.xml", 2, 2.67, 5, 0, 0, 0, 0, 1),
}


@pytest.mark.parametrize("name", list(_FUSE))
def test_ribbon_metrics_match_fuse(name: str) -> None:
    path, ml, ld, crit, hard, nf, lags, leads, mh = _FUSE[name]
    sch = parse_mspdi(path)
    cpm = compute_cpm(sch)
    r = compute_ribbon(sch, cpm, audit_schedule(sch, cpm))
    assert r.missing_logic == ml, ("missing_logic", name, r.missing_logic, ml)
    assert r.logic_density == ld, ("logic_density", name, r.logic_density, ld)
    assert r.critical == crit, ("critical", name, r.critical, crit)
    assert r.hard_constraints == hard, ("hard", name, r.hard_constraints, hard)
    assert r.negative_float == nf, ("neg_float", name, r.negative_float, nf)
    assert r.number_of_lags == lags, ("lags", name, r.number_of_lags, lags)
    assert r.number_of_leads == leads, ("leads", name, r.number_of_leads, leads)
    assert r.merge_hotspot == mh, ("merge_hotspot", name, r.merge_hotspot, mh)


def test_ribbon_float_stats_are_present() -> None:
    sch = parse_mspdi(GOLD / "Project2.mspdi.xml")
    cpm = compute_cpm(sch)
    r = compute_ribbon(sch, cpm, audit_schedule(sch, cpm))
    assert r.avg_float_days >= 0.0 and r.max_float_days >= r.avg_float_days


def test_ribbon_incomplete_float_count_tracks_the_population() -> None:
    """audit NEW-1: ``incomplete_float_count`` is the single signal all surfaces use to tell a real
    Avg/Max Float from a placeholder 0.0. It equals the incomplete-activity float population size:
    >0 on a progressed file with incomplete work, 0 when every non-summary activity is complete."""
    import datetime as dt

    from schedule_forensics.model.relationship import Relationship
    from schedule_forensics.model.schedule import Schedule
    from schedule_forensics.model.task import Task

    mon, day = dt.datetime(2025, 1, 6, 8, 0), 480
    rels = (
        Relationship(predecessor_id=1, successor_id=2),
        Relationship(predecessor_id=2, successor_id=3),
    )

    def _ribbon(sch: Schedule) -> RibbonMetrics:
        cpm = compute_cpm(sch)
        return compute_ribbon(sch, cpm, audit_schedule(sch, cpm))

    incomplete = Schedule(
        name="in-progress",
        project_start=mon,
        tasks=tuple(
            Task(unique_id=i, name=chr(64 + i), duration_minutes=day, percent_complete=0.0)
            for i in (1, 2, 3)
        ),
        relationships=rels,
    )
    assert _ribbon(incomplete).incomplete_float_count == 3

    complete = Schedule(
        name="all-complete",
        project_start=mon,
        tasks=tuple(
            Task(unique_id=i, name=chr(64 + i), duration_minutes=day, percent_complete=100.0)
            for i in (1, 2, 3)
        ),
        relationships=rels,
    )
    r_comp = _ribbon(complete)
    assert r_comp.incomplete_float_count == 0
    # …and both float figures degrade to the placeholder 0.0 in that empty-population case
    assert r_comp.avg_float_days == 0.0 and r_comp.max_float_days == 0.0


def test_ribbon_float_uses_stored_total_slack_not_recomputed_cpm() -> None:
    """Regression: Avg/Max Float (d) must score on the source tool's stored, progress-aware Total
    Slack (Acumen's basis, ADR-0080) — the SAME float the Critical count already uses — not the raw
    recomputed pure-logic CPM float. Operator: "Max Float (d) does not look like it is calculating
    correctly." Build a fully-critical chain (recomputed float 0 everywhere) where one task carries
    a stored Total Slack; that stored slack must surface (the raw float would report 0)."""
    import datetime as dt

    from schedule_forensics.model.relationship import Relationship
    from schedule_forensics.model.schedule import Schedule
    from schedule_forensics.model.task import Task

    mon, day = dt.datetime(2025, 1, 6, 8, 0), 480
    tasks = (
        Task(unique_id=1, name="A", duration_minutes=day, percent_complete=0.0),
        Task(
            unique_id=2,
            name="B",
            duration_minutes=day,
            percent_complete=0.0,
            stored_total_float_minutes=20 * day,  # 20 working days of stored Total Slack
        ),
        Task(unique_id=3, name="C", duration_minutes=day, percent_complete=0.0),
    )
    rels = (
        Relationship(predecessor_id=1, successor_id=2),
        Relationship(predecessor_id=2, successor_id=3),
    )
    sch = Schedule(name="s", project_start=mon, tasks=tasks, relationships=rels)
    cpm = compute_cpm(sch)
    r = compute_ribbon(sch, cpm, audit_schedule(sch, cpm))
    assert r.max_float_days == 20.0  # B's stored 20d slack; raw recomputed float here would be 0


def test_ribbon_lags_leads_count_completed_successors_unlike_dcma() -> None:
    """ADR-0081: Fuse's Ribbon Lags/Leads count activities across ALL statuses (incl. complete),
    so a lag/lead into a finished successor is counted — unlike the DCMA-14 checks, which restrict
    to incomplete successors. This is the 5→8 / 0→1 divergence on the operator's progressed file."""
    import datetime as dt

    from schedule_forensics.engine.dcma_audit import audit_schedule as _audit
    from schedule_forensics.model.relationship import Relationship
    from schedule_forensics.model.schedule import Schedule
    from schedule_forensics.model.task import Task

    mon, day = dt.datetime(2025, 1, 6, 8, 0), 480
    tasks = (
        Task(unique_id=1, name="A", duration_minutes=day, percent_complete=100.0),
        Task(unique_id=2, name="B (done)", duration_minutes=day, percent_complete=100.0),
        Task(unique_id=3, name="C", duration_minutes=day, percent_complete=100.0),
        Task(unique_id=4, name="D (done)", duration_minutes=day, percent_complete=100.0),
    )
    rels = (
        Relationship(predecessor_id=1, successor_id=2, lag_minutes=day),  # +lag into complete
        Relationship(predecessor_id=3, successor_id=4, lag_minutes=-day),  # lead into complete
    )
    sch = Schedule(name="s", project_start=mon, tasks=tasks, relationships=rels)
    cpm = compute_cpm(sch)
    audit = _audit(sch, cpm)
    r = compute_ribbon(sch, cpm, audit)
    # the Ribbon counts both (all statuses)…
    assert r.number_of_lags == 1 and r.number_of_leads == 1
    # …while the DCMA-14 checks (incomplete-only) count neither
    dcma = {c.metric_id: c.count for c in audit.checks}
    assert dcma["DCMA03"] == 0 and dcma["DCMA02"] == 0


def test_hard_constraints_is_the_fuse_mandatory_count_not_the_dcma05_count() -> None:
    """The Bible's ribbon metric (NASA .aft, verbatim): ``SUM(((ActivityConstraint=
    "MandatoryStart")+("MandatoryFinish")+("MustStartOn")+("MustFinishOn")+("StartAndFinish")
    >0)*1)`` — MUST/MANDATORY types only, over ALL statuses, no baseline filter. The library's
    DCMA metric ("5. Hard Constraint") is a DIFFERENT metric of the same name: it adds
    StartOnOrBefore/FinishOnOrBefore. Sourcing the ribbon column from DCMA05 showed 1 (parity
    audit) or 14 (default audit) on the operator's Starlight workbook where Fuse showed 4 —
    3 complete MSO + 1 incomplete MFO (ADR-0429).

    The fixture discriminates every candidate: mandatory-all-status = 2 · DCMA05 default = 4 ·
    DCMA05 parity (baselined incomplete) = 1. Only the Bible's answer may pass.
    """
    import datetime as dt

    from schedule_forensics.engine.metrics.schedule_quality import compute_schedule_quality
    from schedule_forensics.model.relationship import Relationship
    from schedule_forensics.model.schedule import Schedule
    from schedule_forensics.model.task import ConstraintType, Task

    mon, day = dt.datetime(2025, 1, 6, 8, 0), 480

    def _t(uid: int, ct: ConstraintType, pct: float) -> Task:
        return Task(
            unique_id=uid,
            name=f"T{uid}",
            duration_minutes=day,
            percent_complete=pct,
            baseline_duration_minutes=day,
            constraint_type=ct,
            constraint_date=mon,
        )

    sch = Schedule(
        name="s",
        project_start=mon,
        status_date=dt.datetime(2025, 1, 10, 17, 0),
        tasks=(
            _t(1, ConstraintType.MSO, 100.0),  # complete mandatory — Fuse counts, DCMA-parity drops
            _t(2, ConstraintType.MFO, 100.0),  # complete mandatory — Fuse counts, DCMA-parity drops
            _t(3, ConstraintType.SNLT, 100.0),  # cap type — DCMA-default counts, Fuse does NOT
            _t(4, ConstraintType.FNLT, 0.0),  # incomplete cap — the lone DCMA-parity survivor
            Task(unique_id=5, name="A", duration_minutes=day, percent_complete=0.0),
            Task(unique_id=6, name="B", duration_minutes=day, percent_complete=0.0),
        ),
        relationships=(Relationship(predecessor_id=5, successor_id=6),),
    )
    cpm = compute_cpm(sch)

    quality = compute_schedule_quality(sch, cpm)["hard_constraints"]
    assert quality.count == 2, ("schedule_quality must count MSO/MFO only", quality.count)
    assert quality.offender_uids == (1, 2), quality.offender_uids
    assert quality.population == 6  # ALL non-summary activities, no status/baseline filter

    # the ribbon figure must be the Bible's number under EITHER audit mode — the displayed value
    # may never depend on the session's DCMA-parity toggle (that is how Starlight showed 1)
    from schedule_forensics.engine.metrics.ribbon import ribbon_offender_map

    for parity in (False, True):
        audit = audit_schedule(sch, cpm, acumen_parity=parity)
        r = compute_ribbon(sch, cpm, audit)
        assert r.hard_constraints == 2, (f"ribbon (parity={parity})", r.hard_constraints)
        # the drill-down must list exactly the activities Fuse counted — the mandatory pair,
        # not DCMA05's offender set (which is (4,) under parity and (1,2,3,4) under default)
        offenders = ribbon_offender_map(sch, cpm, audit)["hard_constraints"]
        assert offenders == (1, 2), (f"offenders (parity={parity})", offenders)


def test_hard_constraint_offenders_are_the_mandatory_activities() -> None:
    """The drill-down behind the ribbon cell must list exactly the activities Fuse counted."""
    from schedule_forensics.engine.metrics.ribbon import ribbon_offender_map

    sch = parse_mspdi(TP / "TP3_Outage_DCMA_Seeded.xml")
    cpm = compute_cpm(sch)
    for parity in (False, True):
        audit = audit_schedule(sch, cpm, acumen_parity=parity)
        offenders = ribbon_offender_map(sch, cpm, audit)["hard_constraints"]
        by_id = sch.tasks_by_id
        types = {by_id[u].constraint_type.value for u in offenders}
        assert len(offenders) == 2, (parity, offenders)
        assert types == {"MSO", "MFO"}, types


def test_negative_float_is_the_stored_slack_count_not_the_dcma07_count() -> None:
    """ADR-0430 (Starlight): Fuse's ribbon "Negative Float" is arithmetic on the source tool's
    STORED Total Slack — an incomplete activity counts iff its stored slack is negative. On the
    operator's six-version workbook that definition reproduces Fuse EXACTLY (62/45/44/37/34/0)
    while the DCMA07 count the ribbon displayed missed in BOTH directions at once: the
    recompute fallback added phantoms on stored-less tasks (+15 on V05) and the Acumen-parity
    baselined filter dropped real stored negatives (-10).

    The fixture discriminates every candidate: stored-only = 2 (T1, T4) · effective/DCMA07
    default = 3 (T1, T3, T4) · DCMA07 parity = 1 (T1). Only the stored answer may pass, and it
    must not depend on the session's DCMA-parity toggle.
    """
    import datetime as dt

    from schedule_forensics.engine.metrics.ribbon import ribbon_offender_map
    from schedule_forensics.engine.metrics.schedule_quality import compute_schedule_quality
    from schedule_forensics.model.relationship import Relationship
    from schedule_forensics.model.schedule import Schedule
    from schedule_forensics.model.task import ConstraintType, Task

    mon, day = dt.datetime(2025, 1, 6, 8, 0), 480
    tasks = (
        # T1: stored NEGATIVE, baselined -> every definition counts it
        Task(
            unique_id=1,
            name="T1",
            duration_minutes=day,
            percent_complete=0.0,
            stored_total_float_minutes=-day,
            baseline_duration_minutes=day,
        ),
        # T2: stored POSITIVE -> nobody counts it
        Task(
            unique_id=2,
            name="T2",
            duration_minutes=day,
            percent_complete=0.0,
            stored_total_float_minutes=day,
            baseline_duration_minutes=day,
        ),
        # T3: NO stored slack, unbaselined, and a violated FNLT cap makes its RECOMPUTED CPM
        # float negative -> the old effective/recompute fallback counted it; Fuse does not
        Task(
            unique_id=3,
            name="T3",
            duration_minutes=5 * day,
            percent_complete=0.0,
            constraint_type=ConstraintType.FNLT,
            constraint_date=mon,
        ),
        # T4: stored NEGATIVE but UNBASELINED -> the DCMA-parity population dropped it;
        # Fuse counts it (a real stored negative, e.g. a milestone with no baseline)
        Task(
            unique_id=4,
            name="T4",
            duration_minutes=day,
            percent_complete=0.0,
            stored_total_float_minutes=-2 * day,
            is_milestone=True,
        ),
        # completed activity with stored negative -> never counted (population is incomplete)
        Task(
            unique_id=5,
            name="T5",
            duration_minutes=day,
            percent_complete=100.0,
            stored_total_float_minutes=-day,
            baseline_duration_minutes=day,
        ),
    )
    sch = Schedule(
        name="s",
        project_start=mon,
        status_date=dt.datetime(2025, 1, 10, 17, 0),
        tasks=tasks,
        relationships=(Relationship(predecessor_id=1, successor_id=2),),
    )
    cpm = compute_cpm(sch)
    q = compute_schedule_quality(sch, cpm)["negative_float"]
    assert q.count == 2, ("stored-slack semantics", q.count)
    assert q.offender_uids == (1, 4), q.offender_uids

    for parity in (False, True):
        audit = audit_schedule(sch, cpm, acumen_parity=parity)
        r = compute_ribbon(sch, cpm, audit)
        assert r.negative_float == 2, (f"ribbon (parity={parity})", r.negative_float)
        offenders = ribbon_offender_map(sch, cpm, audit)["negative_float"]
        assert offenders == (1, 4), (f"offenders (parity={parity})", offenders)


def test_negative_float_falls_back_to_recomputed_float_on_a_stored_less_file() -> None:
    """A schedule whose incomplete work carries NO stored slack anywhere (a pure-logic network,
    e.g. the tool's own JSON without float) keeps the recomputed-CPM count — the signal must not
    silently become 0 just because the source never wrote Total Slack ("—" never 0, and never a
    fabricated clean bill either)."""
    import datetime as dt

    from schedule_forensics.engine.metrics.schedule_quality import compute_schedule_quality
    from schedule_forensics.model.schedule import Schedule
    from schedule_forensics.model.task import ConstraintType, Task

    mon, day = dt.datetime(2025, 1, 6, 8, 0), 480
    sch = Schedule(
        name="s",
        project_start=mon,
        tasks=(
            Task(
                unique_id=1,
                name="A",
                duration_minutes=5 * day,
                percent_complete=0.0,
                constraint_type=ConstraintType.FNLT,
                constraint_date=mon,
            ),
            Task(unique_id=2, name="B", duration_minutes=day, percent_complete=0.0),
        ),
    )
    cpm = compute_cpm(sch)
    q = compute_schedule_quality(sch, cpm)["negative_float"]
    assert q.count == 1, q.count
    assert q.offender_uids == (1,), q.offender_uids
