"""The known-pass / known-fail battery (ADR-0361, operator 2026-08-06).

Every detection metric is tested in a PAIR: a hand-built CLEAN program that every populated
DCMA check PASSES on, and — per check — a seeded twin carrying exactly one known defect class
that the check MUST flag. The pair is self-falsifying in both directions: a seeder that fails
to plant its defect fails the FAIL half, and a check that flags healthy data fails the PASS
half. Each seed also declares its expected COLLATERAL flags (a hard constraint that creates
negative float legitimately trips both checks) and the battery asserts NO UNDECLARED check
flips — so an over-broad seeder or an over-eager check is caught, not absorbed.

Beyond DCMA the same pair discipline covers the float-band split, completion performance,
and the cross-version manipulation detector (a clean roll produces NO findings; a seeded
driving-path duration cut produces them). Finally every GET page must render 200 on the
clean, the seeded, and the TP4 five-version corpora — a defect in the data must never crash
a page.

Phase 2 (ADR-0362) extends the same pair discipline to the seven queued families: cei, hmi,
fei/bri, evm, schedule_quality, forecast and the SRA-readiness gate. Three of them are
informational ratios (status always NA), so their pairs pin VALUES and offender uids rather
than CheckStatus flips. Two need enriched variants — ``_dated`` (stored start/finish + WBS;
schedule_quality's Insufficient Detail divides by the stored-finish span, and FEI/CEI read
stored forecast dates) and ``_wide`` (N=41 so the two structural open ends sit inside Missing
Logic's 5%) — because the bare 25-task program cannot honestly pass those metrics, exactly as
a bare real-world export could not. Every pinned figure below was MEASURED before it was
pinned (probe first, assert second).
"""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.dcma_audit import audit_schedule
from schedule_forensics.engine.forecast import compute_finish_forecasts
from schedule_forensics.engine.manipulation import detect_manipulation
from schedule_forensics.engine.metrics._common import CheckStatus, MetricResult
from schedule_forensics.engine.metrics.cei import compute_cei
from schedule_forensics.engine.metrics.completion_performance import (
    compute_completion_performance,
)
from schedule_forensics.engine.metrics.evm import (
    compute_baseline_compliance,
    compute_evm_indices,
)
from schedule_forensics.engine.metrics.fei_bri import compute_bri, compute_fei
from schedule_forensics.engine.metrics.float_bands import compute_float_bands
from schedule_forensics.engine.metrics.hmi import compute_hmi
from schedule_forensics.engine.metrics.schedule_quality import compute_schedule_quality
from schedule_forensics.engine.scorecards import Scorecard, compute_sra_readiness
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import ConstraintType, Task
from schedule_forensics.web.app import SessionState, create_app

REPO = Path(__file__).resolve().parents[2]
FIX = REPO / "tests" / "fixtures" / "test_projects"

DAY = 480
START = dt.datetime(2026, 1, 5, 8, 0)  # a Monday
DD = dt.datetime(2026, 2, 2, 8, 0)  # the status date, four weeks in
N = 24


def clean_program() -> Schedule:
    """A 24-leaf serial program + finish milestone: fully linked, baselined, resource- and
    cost-loaded, progressed consistently to the data date, no constraints, modest durations.
    Measured clean: every DCMA check with a population PASSES (the one terminal open end is
    1/22 = 4.5%, inside DCMA01's 5% tolerance — that is how real programs pass it too)."""
    tasks: list[Task] = []
    rels: list[Relationship] = []
    for i in range(1, N + 1):
        done = i <= 3
        prog = i == 4
        tasks.append(
            Task(
                unique_id=i,
                name=f"A{i:02d}",
                duration_minutes=10 * DAY,
                remaining_duration_minutes=0 if done else (5 * DAY if prog else 10 * DAY),
                percent_complete=100.0 if done else (50.0 if prog else 0.0),
                baseline_start=START + dt.timedelta(days=(i - 1) * 14),
                baseline_finish=START + dt.timedelta(days=(i - 1) * 14 + 13),
                actual_start=START + dt.timedelta(days=(i - 1) * 7) if (done or prog) else None,
                actual_finish=START + dt.timedelta(days=(i - 1) * 7 + 9) if done else None,
                resource_names=("Crew",),
                budgeted_cost=1000.0,
                cost=1000.0,
                actual_cost=1000.0 if done else (500.0 if prog else 0.0),
            )
        )
    tasks.append(
        Task(
            unique_id=99,
            name="Program Complete",
            duration_minutes=0,
            is_milestone=True,
            remaining_duration_minutes=0,
            baseline_start=START + dt.timedelta(days=(N - 1) * 14 + 13),
            baseline_finish=START + dt.timedelta(days=(N - 1) * 14 + 13),
        )
    )
    for i in range(1, N):
        rels.append(
            Relationship(
                predecessor_id=i, successor_id=i + 1, type=RelationshipType.FS, lag_minutes=0
            )
        )
    rels.append(
        Relationship(predecessor_id=N, successor_id=99, type=RelationshipType.FS, lag_minutes=0)
    )
    return Schedule(
        name="CleanProgram",
        source_file="clean.xml",
        project_start=START,
        status_date=DD,
        tasks=tuple(tasks),
        relationships=tuple(rels),
    )


def _statuses(sch: Schedule) -> dict[str, tuple[CheckStatus, int]]:
    audit = audit_schedule(sch, compute_cpm(sch))
    return {c.metric_id: (c.status, c.count) for c in audit.checks}


def _replace_task(sch: Schedule, uid: int, **updates: object) -> Schedule:
    tasks = tuple(t.model_copy(update=updates) if t.unique_id == uid else t for t in sch.tasks)
    return sch.model_copy(update={"tasks": tasks})


def _replace_rel(sch: Schedule, pred: int, succ: int, **updates: object) -> Schedule:
    rels = tuple(
        r.model_copy(update=updates) if r.predecessor_id == pred and r.successor_id == succ else r
        for r in sch.relationships
    )
    return sch.model_copy(update={"rels" if False else "relationships": rels})


# --- the clean half ---------------------------------------------------------------


def test_the_clean_program_passes_every_populated_check() -> None:
    """The PASS half of every pair at once — and the populations are real, not empty."""
    audit = audit_schedule(clean_program(), compute_cpm(clean_program()))
    by = {c.metric_id: c for c in audit.checks}
    na_by_design = {"DCMA04_SSFF", "DCMA04_SF"}  # the clean program carries FS links only
    for metric_id, check in by.items():
        if metric_id in na_by_design:
            assert check.status is CheckStatus.NOT_APPLICABLE
            continue
        assert check.status is CheckStatus.PASS, (
            f"{metric_id} must PASS on the clean program (got {check.status}, "
            f"count {check.count}/{check.population})"
        )
        assert check.population > 0, f"{metric_id} passed on an EMPTY population — vacuous"


# --- the seeded half: one known defect per check ----------------------------------


def _seed_missing_logic(s: Schedule) -> Schedule:
    """Orphan task 10 both ways: it and its neighbours lose logic — DCMA01 counts jump."""
    rels = tuple(r for r in s.relationships if 10 not in (r.predecessor_id, r.successor_id))
    return s.model_copy(update={"relationships": rels})


def _seed_lead(s: Schedule) -> Schedule:
    return _replace_rel(s, 5, 6, lag_minutes=-240)


def _seed_lag(s: Schedule) -> Schedule:
    s = _replace_rel(s, 5, 6, lag_minutes=10 * DAY)
    return _replace_rel(s, 7, 8, lag_minutes=10 * DAY)


def _seed_non_fs(s: Schedule) -> Schedule:
    """Six of 24 links become SS: FS share 75% (< 90) and the SS share crosses its own 10%."""
    picks = {(5, 6), (7, 8), (9, 10), (11, 12), (13, 14), (15, 16)}
    rels = tuple(
        r.model_copy(update={"type": RelationshipType.SS})
        if (r.predecessor_id, r.successor_id) in picks
        else r
        for r in s.relationships
    )
    return s.model_copy(update={"relationships": rels})


def _seed_hard_constraints(s: Schedule) -> Schedule:
    for uid in (7, 9, 11):
        s = _replace_task(
            s,
            uid,
            constraint_type=ConstraintType.MSO,
            constraint_date=START + dt.timedelta(days=30 + uid * 14),
        )
    return s


def _seed_high_float(s: Schedule) -> Schedule:
    """Two short parallel floaters 1 → x → 99: months of float each. Resourced, costed and
    SNET-held past the data date so the ONLY defect they carry is the float itself."""
    extra = tuple(
        Task(
            unique_id=uid,
            name=f"Float{uid}",
            duration_minutes=2 * DAY,
            resource_names=("Crew",),
            budgeted_cost=100.0,
            cost=100.0,
            constraint_type=ConstraintType.SNET,
            constraint_date=DD + dt.timedelta(days=14),
        )
        for uid in (50, 51)
    )
    rels = (
        s.relationships
        + tuple(
            Relationship(
                predecessor_id=1, successor_id=uid, type=RelationshipType.FS, lag_minutes=0
            )
            for uid in (50, 51)
        )
        + tuple(
            Relationship(
                predecessor_id=uid, successor_id=99, type=RelationshipType.FS, lag_minutes=0
            )
            for uid in (50, 51)
        )
    )
    return s.model_copy(update={"tasks": s.tasks + extra, "relationships": rels})


def _seed_negative_float(s: Schedule) -> Schedule:
    """An MFO on the finish milestone 20 working days before it is reachable."""
    return _replace_task(
        s,
        99,
        constraint_type=ConstraintType.MFO,
        constraint_date=START + dt.timedelta(days=(N - 1) * 14 - 28),
    )


def _seed_high_duration(s: Schedule) -> Schedule:
    """DCMA08 flags on the BASELINE duration (> 44 wd), so the seed moves all three."""
    for uid in (8, 9):
        s = _replace_task(
            s,
            uid,
            duration_minutes=50 * DAY,
            remaining_duration_minutes=50 * DAY,
            baseline_duration_minutes=50 * DAY,
        )
    return s


def _seed_invalid_dates(s: Schedule) -> Schedule:
    """A completed task whose actual finish sits AFTER the data date."""
    return _replace_task(s, 2, actual_finish=DD + dt.timedelta(days=10))


def _seed_missing_resources(s: Schedule) -> Schedule:
    for uid in (6, 7, 8):
        s = _replace_task(s, uid, resource_names=(), budgeted_cost=0.0, cost=None)
    return s


def _seed_missed_task(s: Schedule) -> Schedule:
    """Task 2 finished LATER than its baseline said — the baseline is pulled earlier so the
    lateness never crosses the data date (that would be DCMA09's defect, not this one)."""
    actual = s.tasks_by_id[2].actual_finish
    assert actual is not None
    return _replace_task(s, 2, baseline_finish=actual - dt.timedelta(days=5))


def _seed_cp_broken(s: Schedule) -> Schedule:
    """A mid-chain task MFO-pinned at its OWN current finish: float stays 0 everywhere (so
    nothing else flips — one hard constraint is 4%, inside DCMA05's own tolerance), but the
    test's injected upstream delay is absorbed at the pin and the finish does not move."""
    from schedule_forensics.engine.cpm import offset_to_datetime

    fin5 = offset_to_datetime(s.project_start, compute_cpm(s).timings[5].early_finish, s.calendar)
    return _replace_task(s, 5, constraint_type=ConstraintType.MFO, constraint_date=fin5)


def _seed_low_cpli(s: Schedule) -> Schedule:
    return _seed_negative_float(s)


def _seed_low_bei(s: Schedule) -> Schedule:
    """Tasks 2 and 3 un-finished: baseline said done by the data date, reality says not."""
    for uid in (2, 3):
        s = _replace_task(
            s,
            uid,
            percent_complete=60.0,
            actual_finish=None,
            remaining_duration_minutes=4 * DAY,
        )
    return s


#: (target check, seeder, declared collateral flips). The battery asserts the target FAILS
#: with a non-zero count, the clean twin PASSES it, and NO undeclared check flips to FAIL.
SEEDS: tuple[tuple[str, Callable[[Schedule], Schedule], frozenset[str]], ...] = (
    ("DCMA01", _seed_missing_logic, frozenset({"DCMA06", "DCMA09"})),
    ("DCMA02", _seed_lead, frozenset()),
    ("DCMA03", _seed_lag, frozenset()),
    ("DCMA04_FS", _seed_non_fs, frozenset({"DCMA04_SSFF"})),
    ("DCMA05", _seed_hard_constraints, frozenset({"DCMA06", "DCMA12"})),
    ("DCMA06", _seed_high_float, frozenset()),
    ("DCMA07", _seed_negative_float, frozenset({"DCMA05", "DCMA12", "DCMA13"})),
    ("DCMA08", _seed_high_duration, frozenset()),
    ("DCMA09", _seed_invalid_dates, frozenset({"DCMA11"})),
    ("DCMA10", _seed_missing_resources, frozenset()),
    ("DCMA11", _seed_missed_task, frozenset()),
    ("DCMA12", _seed_cp_broken, frozenset()),
    ("DCMA13", _seed_low_cpli, frozenset({"DCMA05", "DCMA07", "DCMA12"})),
    ("DCMA14", _seed_low_bei, frozenset({"DCMA09", "DCMA11"})),
)


@pytest.mark.parametrize(("target", "seed", "collateral"), SEEDS, ids=[s[0] for s in SEEDS])
def test_each_seeded_defect_is_flagged_and_only_where_declared(
    target: str, seed: Callable[[Schedule], Schedule], collateral: frozenset[str]
) -> None:
    clean = _statuses(clean_program())
    seeded = _statuses(seed(clean_program()))
    # the PASS half: the clean twin passes the very check the seed targets
    assert clean[target][0] is CheckStatus.PASS
    # the FAIL half: the seeded twin flags it, with real offenders
    status, count = seeded[target]
    assert status is CheckStatus.FAIL, f"{target} did not flag its seeded defect"
    if target not in ("DCMA13", "DCMA14"):  # the two pure ratios carry no offender count
        assert count > 0, f"{target} FAILed with a zero count — the flag cites nothing"
    # and nothing else flips beyond the declared collateral
    unexpected = (
        {
            m
            for m, (st_, _c) in seeded.items()
            if st_ is CheckStatus.FAIL and clean[m][0] is not CheckStatus.FAIL
        }
        - {target}
        - set(collateral)
    )
    assert not unexpected, (
        f"seeding {target} flipped undeclared check(s) {sorted(unexpected)} — either the "
        "seeder is over-broad or a check is over-eager; declare it only if it is genuinely "
        "the same physical defect"
    )


# --- beyond DCMA: the same pair discipline ----------------------------------------


def test_float_bands_pair() -> None:
    """On the serial clean program every task sits inside the <10d band; the high-float seed
    puts exactly its two floaters OUTSIDE every band — the split must show them."""
    clean = clean_program()
    bands_clean = compute_float_bands(clean, compute_cpm(clean))
    b = bands_clean["float_total_lt10"]
    assert b.population - b.count == 0
    seeded = _seed_high_float(clean)
    bands_bad = compute_float_bands(seeded, compute_cpm(seeded))
    b2 = bands_bad["float_total_lt10"]
    assert b2.population - b2.count == 2


def test_completion_performance_pair() -> None:
    clean = clean_program()
    perf_clean = compute_completion_performance(clean)
    late_clean = next((v for k, v in perf_clean.items() if "late" in k.lower()), None)
    seeded = _seed_missed_task(clean)
    perf_bad = compute_completion_performance(seeded)
    late_bad = next((v for k, v in perf_bad.items() if "late" in k.lower()), None)
    assert late_clean is not None and late_bad is not None
    assert late_bad.count > late_clean.count


def test_manipulation_pair_clean_roll_vs_driving_path_cut() -> None:
    """A faithful re-status produces NO findings; cutting a driving-path duration 40% while
    the finish holds produces them. Both halves matter: the detector must fire on the cut
    and must NOT cry wolf on the honest update."""
    v1 = clean_program()
    honest = _replace_task(
        _replace_task(v1, 5, percent_complete=25.0, actual_start=DD),
        99,
        name="Program Complete",
    )
    f_honest = detect_manipulation(
        honest, v1, current_cpm=compute_cpm(honest), prior_cpm=compute_cpm(v1)
    )
    titles = [x.title for x in f_honest]
    assert f_honest == (), f"honest statusing must raise no findings, got {titles}"
    cut = _replace_task(v1, 12, duration_minutes=6 * DAY, remaining_duration_minutes=6 * DAY)
    f_cut = detect_manipulation(cut, v1, current_cpm=compute_cpm(cut), prior_cpm=compute_cpm(v1))
    assert f_cut, "a 40% duration cut on the driving path must raise a finding"


# --- every page renders on every corpus -------------------------------------------


def _mount(schedules: dict[str, Schedule]) -> TestClient:
    st = SessionState()
    for key, sch in schedules.items():
        st.schedules[key] = sch
    return TestClient(create_app(st))


def _get_pages(client: TestClient) -> list[str]:
    return sorted(
        {
            getattr(r, "path", "")
            for r in client.app.routes  # type: ignore[attr-defined]
            if "GET" in (getattr(r, "methods", None) or set())
            and "{" not in getattr(r, "path", "")
            and not getattr(r, "path", "").startswith(("/api", "/export", "/download", "/static"))
        }
    )


# ==================================================================================
# PHASE 2 (ADR-0362): cei · hmi · fei/bri · evm · schedule_quality · forecast ·
# SRA-readiness — every pinned figure below was measured before it was pinned.
# ==================================================================================

#: The previous data date for the period metrics (two weeks before DD, mid-execution).
PREV = dt.datetime(2026, 1, 19, 8, 0)


def _dated(s: Schedule) -> Schedule:
    """Stored start/finish (actuals where they exist, else baselines) + WBS on every task.

    The bare program carries none — but schedule_quality's Insufficient Detail divides by the
    stored-finish span (span 1 day would flag everything), FEI/CEI read stored forecast dates,
    and the readiness gate requires WBS mapping. Real imports always carry these; the variant
    makes the synthetic program as honest as a real file."""
    tasks = tuple(
        t.model_copy(
            update={
                "start": t.actual_start or t.baseline_start,
                "finish": t.actual_finish or t.baseline_finish,
                "wbs": f"1.{t.unique_id}",
            }
        )
        for t in s.tasks
    )
    return s.model_copy(update={"tasks": tasks})


def _wide(s: Schedule) -> Schedule:
    """_dated + 16 fully-linked short parallel tasks (1 -> x -> 2), N=41: the two structural
    open ends (first task, terminal milestone) sit at 2/41 = 4.9%, inside Missing Logic's 5%
    — the metric's floor is 2/N on ANY program, so a small population can never pass it."""
    s = _dated(s)
    extra = tuple(
        Task(
            unique_id=uid,
            name=f"Par{uid}",
            duration_minutes=2 * DAY,
            remaining_duration_minutes=2 * DAY,
            baseline_start=START + dt.timedelta(days=14),
            baseline_finish=START + dt.timedelta(days=15),
            start=START + dt.timedelta(days=14),
            finish=START + dt.timedelta(days=15),
            wbs=f"2.{uid}",
            resource_names=("Crew",),
            budgeted_cost=100.0,
            cost=100.0,
        )
        for uid in range(200, 216)
    )
    rels = (
        s.relationships
        + tuple(
            Relationship(
                predecessor_id=1, successor_id=uid, type=RelationshipType.FS, lag_minutes=0
            )
            for uid in range(200, 216)
        )
        + tuple(
            Relationship(
                predecessor_id=uid, successor_id=2, type=RelationshipType.FS, lag_minutes=0
            )
            for uid in range(200, 216)
        )
    )
    return s.model_copy(update={"tasks": s.tasks + extra, "relationships": rels})


def _unfinish(s: Schedule, uid: int, pc: float = 60.0, rem: int = 4 * DAY) -> Schedule:
    """The shared period-miss seed: a completed task reverts to in-progress (no actual finish)."""
    return _replace_task(
        s, uid, percent_complete=pc, actual_finish=None, remaining_duration_minutes=rem
    )


# --- CEI: forecast-anchored period execution (two snapshots) ----------------------


def _cei_prior(s: Schedule) -> Schedule:
    """The dated program rolled back to PREV (Jan 19): tasks 2/3 in progress carrying their
    then-forecast finishes Jan 21 / Jan 28 (inside the coming period), task 4 unstarted with
    a forecast start Jan 26 (inside) and finish Feb 6 (outside)."""
    s = _dated(s)
    s = _replace_task(
        s, 2, percent_complete=50.0, actual_finish=None, remaining_duration_minutes=5 * DAY
    )
    s = _replace_task(
        s, 3, percent_complete=25.0, actual_finish=None, remaining_duration_minutes=7 * DAY
    )
    s = _replace_task(
        s,
        4,
        percent_complete=0.0,
        actual_start=None,
        actual_cost=0.0,
        remaining_duration_minutes=10 * DAY,
        start=START + dt.timedelta(days=21),
        finish=dt.datetime(2026, 2, 6, 17, 0),
    )
    return s.model_copy(update={"status_date": PREV})


def test_cei_pair() -> None:
    """PASS half: everything the prior schedule forecast for the period actually finished
    (CEI 1.0, no misses). FAIL half: un-finishing task 3 halves it and cites exactly task 3.
    The start cut must NOT move (task 4 did start), and the empty populations stay NA."""
    prior = _cei_prior(clean_program())
    current = _dated(clean_program())
    clean = compute_cei(prior, current)
    assert (clean["cei_tasks"].count, clean["cei_tasks"].population) == (2, 2)
    assert clean["cei_tasks"].value == 1.0 and clean["cei_tasks"].offender_uids == ()
    assert (clean["cei_task_starts"].count, clean["cei_task_starts"].population) == (1, 1)
    assert (clean["cei_tasks_adjusted"].count, clean["cei_tasks_adjusted"].population) == (2, 2)
    # honest NA: no milestones forecast in the period, no stored-critical population
    assert clean["cei_milestones"].population == 0
    assert clean["cei_milestones"].status is CheckStatus.NOT_APPLICABLE
    assert clean["cei_critical"].status is CheckStatus.NOT_APPLICABLE

    seeded_cur = _replace_task(
        _unfinish(current, 3, rem=3 * DAY), 3, finish=dt.datetime(2026, 2, 6, 17, 0)
    )
    seeded = compute_cei(prior, seeded_cur)
    assert (seeded["cei_tasks"].count, seeded["cei_tasks"].population) == (1, 2)
    assert seeded["cei_tasks"].value == 0.5
    assert seeded["cei_tasks"].offender_uids == (3,), "the miss must cite exactly task 3"
    assert (seeded["cei_tasks_adjusted"].count, seeded["cei_tasks_adjusted"].population) == (1, 2)
    assert seeded["cei_task_starts"].value == 1.0, "the start cut must not move on a finish miss"


# --- HMI: baseline-anchored period execution --------------------------------------


def test_hmi_pair() -> None:
    """PASS half: the one activity baselined to finish in (Jan 19, Feb 2] (task 2, baseline
    Feb 1) completed in the period — HMI 1.0. FAIL half: un-finishing it scores 0.0 and cites
    it. A non-advancing period reads NA — never a fabricated ratio."""
    c = clean_program()
    clean = compute_hmi(c, PREV)
    assert (clean["hmi_tasks"].count, clean["hmi_tasks"].population) == (1, 1)
    assert clean["hmi_tasks"].value == 1.0 and clean["hmi_tasks"].offender_uids == ()
    assert clean["hmi_milestones"].population == 0
    assert clean["hmi_milestones"].status is CheckStatus.NOT_APPLICABLE

    seeded = compute_hmi(_unfinish(c, 2), PREV)
    assert (seeded["hmi_tasks"].count, seeded["hmi_tasks"].population) == (0, 1)
    assert seeded["hmi_tasks"].value == 0.0
    assert seeded["hmi_tasks"].offender_uids == (2,), "the miss must cite exactly task 2"

    stalled = compute_hmi(c, DD)  # prev == now: the period is undefined
    assert stalled["hmi_tasks"].status is CheckStatus.NOT_APPLICABLE
    assert (stalled["hmi_tasks"].count, stalled["hmi_tasks"].population) == (0, 0)


# --- FEI / BRI: to-go bow wave and cumulative baseline realism --------------------


def test_fei_bri_pair() -> None:
    """PASS half: on-plan execution keeps both FEI cuts under 1.0 (to-go window no heavier
    than the baseline placed it) and BRI at 1.0. FAIL half: slipping tasks 2/3 wholesale past
    the data date pushes FEI to/over 1.0 — the bow wave — and un-finishing task 2 halves BRI
    with the miss cited."""
    d = _dated(clean_program())
    fei = compute_fei(d)
    assert (fei["fei_starts"].count, fei["fei_starts"].population) == (20, 22)
    assert fei["fei_starts"].value == 0.91
    assert (fei["fei_finish"].count, fei["fei_finish"].population) == (21, 22)
    assert fei["fei_finish"].value == 0.95
    bri = compute_bri(d)
    assert (bri.count, bri.population, bri.value) == (2, 2, 1.0)
    assert bri.offender_uids == ()

    slip = d
    for uid, s0, f0 in ((2, 35, 46), (3, 42, 53)):
        slip = _replace_task(
            slip,
            uid,
            percent_complete=0.0,
            actual_finish=None,
            actual_start=None,
            actual_cost=0.0,
            remaining_duration_minutes=10 * DAY,
            start=START + dt.timedelta(days=s0),
            finish=START + dt.timedelta(days=f0),
        )
    waved = compute_fei(slip)
    assert waved["fei_starts"].value == 1.0 and waved["fei_starts"].count == 22
    assert waved["fei_finish"].value == 1.05 and waved["fei_finish"].count == 23
    assert waved["fei_finish"].value > fei["fei_finish"].value

    bri_bad = compute_bri(_unfinish(d, 2))
    assert (bri_bad.count, bri_bad.population, bri_bad.value) == (1, 2, 0.5)
    assert bri_bad.offender_uids == (2,), "the realism miss must cite exactly task 2"


# --- EVM: indices + baseline compliance (real thresholds — flip discipline) -------


def _evm_all(s: Schedule) -> dict[str, MetricResult]:
    out = dict(compute_baseline_compliance(s))
    out.update(compute_evm_indices(s))
    return out


#: Every EVM/compliance metric that carries a pass bar on the clean program.
_EVM_SCORED = (
    "spi",
    "cpi",
    "tcpi",
    "spi_t",
    "spi_t_acumen",
    "completed_on_time",
    "completed_late",
    "started_on_time",
    "started_late",
    "baseline_finish_compliance",
    "baseline_start_compliance",
    "cei_finish",
    "cei_start",
)


def test_evm_clean_every_scored_index_passes() -> None:
    """The PASS half of the whole family at once: consistent, cost-loaded, on-plan execution
    scores PASS on all thirteen thresholds, with real populations behind the ratios."""
    res = _evm_all(clean_program())
    for mid in _EVM_SCORED:
        assert res[mid].status is CheckStatus.PASS, f"{mid} must PASS on the clean program"
    assert res["spi"].value == 1.75 and res["cpi"].value == 1.0 and res["tcpi"].value == 1.0
    assert res["spi_t"].value == 1.5 and res["spi_t_acumen"].value == 1.08
    assert res["completed_on_time"].value == 100.0 and res["completed_on_time"].count == 2
    assert res["started_on_time"].population == 2, "the ratios must have a real population"
    # the pure counts stay informational — a count has no industry pass bar (Law 2)
    for mid in ("forecast_to_be_finished", "not_completed", "not_started"):
        assert res[mid].status is CheckStatus.NOT_APPLICABLE


def _seed_evm_unfinish(s: Schedule) -> Schedule:
    """Completed work reverts to in-progress while its cost stays spent."""
    return _unfinish(_unfinish(s, 2), 3)


def _seed_evm_cost_blowout(s: Schedule) -> Schedule:
    """The done work cost twice its budget — a pure cost defect, schedule untouched."""
    for uid in (1, 2, 3):
        s = _replace_task(s, uid, actual_cost=2000.0)
    return s


def _seed_evm_never_started(s: Schedule) -> Schedule:
    """Everything after task 1 simply never began — no starts, no spend, no earned value."""
    for uid in (2, 3):
        s = _replace_task(
            s,
            uid,
            percent_complete=0.0,
            actual_finish=None,
            actual_start=None,
            actual_cost=0.0,
            remaining_duration_minutes=10 * DAY,
        )
    return _replace_task(
        s,
        4,
        percent_complete=0.0,
        actual_start=None,
        actual_cost=0.0,
        remaining_duration_minutes=10 * DAY,
    )


def _seed_evm_late_vs_baseline(s: Schedule) -> Schedule:
    """Task 2 started AND finished later than the baseline said (baseline pulled earlier)."""
    return _replace_task(
        s,
        2,
        baseline_start=dt.datetime(2026, 1, 7, 8, 0),
        baseline_finish=dt.datetime(2026, 1, 16, 17, 0),
    )


#: (seed, the EXACT set of status flips it must cause — measured, then pinned).
_EVM_SEEDS: tuple[tuple[str, Callable[[Schedule], Schedule], frozenset[str]], ...] = (
    (
        "unfinish_2_3",
        _seed_evm_unfinish,
        frozenset(
            {
                "completed_on_time",
                "baseline_finish_compliance",
                "cei_finish",
                "cpi",
                "spi_t",
                "spi_t_acumen",
            }
        ),
    ),
    ("cost_blowout", _seed_evm_cost_blowout, frozenset({"cpi"})),
    (
        "never_started",
        _seed_evm_never_started,
        frozenset(
            {
                "completed_on_time",
                "baseline_finish_compliance",
                "started_on_time",
                "baseline_start_compliance",
                "spi",
                "cei_finish",
                "cei_start",
                "spi_t",
            }
        ),
    ),
    (
        "late_vs_baseline",
        _seed_evm_late_vs_baseline,
        frozenset(
            {
                "completed_on_time",
                "completed_late",
                "baseline_finish_compliance",
                "started_on_time",
                "started_late",
                "cei_finish",
                "cei_start",
                "spi_t_acumen",
            }
        ),
    ),
)


@pytest.mark.parametrize(("label", "seed", "flips"), _EVM_SEEDS, ids=[s[0] for s in _EVM_SEEDS])
def test_evm_seeded_flips_exactly_where_declared(
    label: str, seed: Callable[[Schedule], Schedule], flips: frozenset[str]
) -> None:
    """Each seeded defect flips EXACTLY its declared metric set — stronger than the DCMA
    battery's no-undeclared rule: an expected flip that fails to happen also fails here."""
    base = _evm_all(clean_program())
    res = _evm_all(seed(clean_program()))
    moved = {mid for mid in res if res[mid].status is not base[mid].status}
    assert moved == set(flips), f"{label}: flips {sorted(moved)} != declared {sorted(flips)}"


def test_evm_sharp_discriminators() -> None:
    """The two semantic edges the family carries, pinned so they can never silently blur:
    (1) work that NEVER STARTS fails SPI and Earned-Schedule SPI(t) but leaves Acumen's
    per-activity SPI(t) PASSING — that average only sees started work, it is structurally
    blind to work that never begins; (2) a late-vs-baseline start fails Started Late but
    leaves Baseline Start Compliance at 100% — its Half-Step-Delay numerator compares the
    actual start to the baseline FINISH (ADR-0083), the documented asymmetry."""
    never = _evm_all(_seed_evm_never_started(clean_program()))
    assert never["spi"].status is CheckStatus.FAIL and never["spi"].value == 0.5
    assert never["spi_t"].status is CheckStatus.FAIL and never["spi_t"].value == 0.5
    assert never["spi_t_acumen"].status is CheckStatus.PASS
    assert never["spi_t_acumen"].value == 1.44

    late = _evm_all(_seed_evm_late_vs_baseline(clean_program()))
    assert late["started_late"].status is CheckStatus.FAIL
    assert late["started_late"].offender_uids == (2,)
    assert late["completed_late"].offender_uids == (2,)
    assert late["baseline_start_compliance"].status is CheckStatus.PASS
    assert late["baseline_start_compliance"].value == 100.0
    # the cost indices never move on a pure schedule defect
    assert late["cpi"].status is CheckStatus.PASS and late["spi"].value == 1.75
    # the unfinish seed drags CPI too (cost stays spent while earned value drops) but SPI
    # survives at 1.35 — earned work still exceeds the baseline's due work
    undone = _evm_all(_seed_evm_unfinish(clean_program()))
    assert undone["cpi"].value == 0.77 and undone["spi"].value == 1.35
    assert undone["spi"].status is CheckStatus.PASS
    blown = _evm_all(_seed_evm_cost_blowout(clean_program()))
    assert blown["cpi"].value == 0.54 and blown["spi"].value == 1.75
    assert blown["tcpi"].status is CheckStatus.PASS and blown["tcpi"].value == 1.17


# --- schedule_quality: the Acumen summary framework -------------------------------


def test_schedule_quality_pair_on_the_wide_program() -> None:
    """PASS half on the wide program (the metric floor is 2/N structural open ends, so only a
    real-sized population can pass Missing Logic; Insufficient Detail needs the stored-finish
    span). FAIL halves: the phase-1 orphan seed, three 40-working-day durations (the stored
    span stays fixed at 335 days — seeding durations does NOT move stored dates, so the ratio
    is honest), and three lagged links. Informational metrics are pinned by count+offenders."""
    w = _wide(clean_program())
    sq = compute_schedule_quality(w)
    assert sq["missing_logic"].status is CheckStatus.PASS
    assert (sq["missing_logic"].count, sq["missing_logic"].population) == (2, 41)
    assert sq["missing_logic"].offender_uids == (1, 99), "only the two structural open ends"
    assert sq["insufficient_detail"].status is CheckStatus.PASS
    assert sq["insufficient_detail"].count == 0
    assert sq["number_of_lags"].status is CheckStatus.PASS and sq["number_of_lags"].count == 0
    assert (sq["hard_constraints"].count, sq["negative_float"].count) == (0, 0)
    assert sq["merge_hotspot"].offender_uids == (2,), "the 17-predecessor merge point"
    assert (sq["logic_density"].count, sq["logic_density"].value) == (56, 2.73)

    orphaned = compute_schedule_quality(_seed_missing_logic(w))
    assert orphaned["missing_logic"].status is CheckStatus.FAIL
    assert orphaned["missing_logic"].offender_uids == (1, 9, 10, 11, 99)

    big = w
    for uid in (8, 9, 12):
        big = _replace_task(
            big, uid, duration_minutes=40 * DAY, remaining_duration_minutes=40 * DAY
        )
    detail = compute_schedule_quality(big)["insufficient_detail"]
    assert detail.status is CheckStatus.FAIL and detail.offender_uids == (8, 9, 12)

    lagged = w
    for pred, succ in ((5, 6), (7, 8), (9, 10)):
        lagged = _replace_rel(lagged, pred, succ, lag_minutes=10 * DAY)
    lags = compute_schedule_quality(lagged)["number_of_lags"]
    assert lags.status is CheckStatus.FAIL and lags.offender_uids == (6, 8, 10)

    constrained = compute_schedule_quality(_seed_hard_constraints(w))["hard_constraints"]
    assert (constrained.count, constrained.offender_uids) == (3, (7, 9, 11))
    negged = compute_schedule_quality(_seed_negative_float(w))["negative_float"]
    assert negged.count == 38 and negged.population == 38, "an MFO 4 weeks early sinks the chain"


# --- forecast: the four finish methods --------------------------------------------


def test_forecast_methods_pair() -> None:
    """PASS half: all four methods answer on the dated program, the performance methods land
    EARLIER than the logic methods (execution ran twice plan speed), and the logic/stored pair
    agree to two days. FAIL half: un-finishing tasks 2/3 pushes the throughput and
    earned-schedule answers out by over a year while the pure-logic and stored answers stand
    still — the divergence IS the finding. Missing inputs answer None with an honest basis."""
    d = _dated(clean_program())
    fs = compute_finish_forecasts(d)
    by = {f.method_id: f.finish for f in fs.forecasts}
    assert by["cpm"] == dt.date(2026, 12, 4)
    assert by["as_scheduled"] == dt.date(2026, 12, 6)
    assert by["rate"] == dt.date(2026, 8, 26)
    assert by["earned_schedule"] == dt.date(2026, 8, 14)
    assert fs.rate_per_month == 3.26 and fs.spi_t == 1.5
    assert fs.planned_finish == dt.date(2026, 12, 4)
    assert by["rate"] < by["cpm"] and by["earned_schedule"] < by["cpm"]

    slow = compute_finish_forecasts(_unfinish(_unfinish(d, 2), 3))
    slow_by = {f.method_id: f.finish for f in slow.forecasts}
    assert slow_by["rate"] == dt.date(2027, 12, 6) and slow_by["earned_schedule"] == dt.date(
        2027, 11, 5
    )
    assert slow.spi_t == 0.5
    assert slow_by["cpm"] == by["cpm"] and slow_by["as_scheduled"] == by["as_scheduled"]

    no_dd = compute_finish_forecasts(d.model_copy(update={"status_date": None}))
    for f in no_dd.forecasts:
        if f.method_id in ("rate", "earned_schedule"):
            assert f.finish is None, f"{f.method_id} must not fabricate without a data date"
            assert "needs a status date" in f.basis
        else:
            assert f.finish is not None

    bare = compute_finish_forecasts(clean_program())
    stored = next(f for f in bare.forecasts if f.method_id == "as_scheduled")
    assert stored.finish is None and "no stored finish dates" in stored.basis


# --- SRA-readiness gate -----------------------------------------------------------


def _readiness(s: Schedule) -> Scorecard:
    cpm = compute_cpm(s)
    return compute_sra_readiness(s, cpm, audit_schedule(s, cpm))


def _gate_statuses(card: Scorecard) -> dict[str, str]:
    return {c.key: c.status for c in card.checks}


def test_sra_readiness_clean_passes_every_gate() -> None:
    """The dated program passes all seven scored gates; three-point stays INFO by design
    (elicited on the Risk Analysis page, never stored in the file)."""
    card = _readiness(_dated(clean_program()))
    assert (card.passed, card.failed, card.info, card.na) == (7, 0, 1, 0)
    assert _gate_statuses(card)["three_point"] == "INFO"


def _seed_ready_wbs(s: Schedule) -> Schedule:
    for uid in (7, 8):
        s = _replace_task(s, uid, wbs=None)
    return s


def _seed_ready_calendar(s: Schedule) -> Schedule:
    """A 24-hour working day — the 'no crashing / standard calendar' violation."""
    return s.model_copy(update={"calendar": Calendar(working_minutes_per_day=1440)})


def _seed_ready_loe(s: Schedule) -> Schedule:
    return _replace_task(s, 6, is_level_of_effort=True)


#: (target gate, seeder, declared collateral gates). Note the hard-constraint seed's
#: critical-path collateral — the SAME physical defect the phase-1 DCMA battery declared
#: (a hard pin defeats the CP test), resurfacing through the scorecard's DCMA12 mapping.
_READY_SEEDS: tuple[tuple[str, Callable[[Schedule], Schedule], frozenset[str]], ...] = (
    ("wbs_mapped", _seed_ready_wbs, frozenset()),
    ("logic_linked", _seed_missing_logic, frozenset()),
    ("resource_loaded", _seed_missing_resources, frozenset()),
    ("critical_path", _seed_cp_broken, frozenset()),
    ("hard_constraints", _seed_hard_constraints, frozenset({"critical_path"})),
    ("standard_calendar", _seed_ready_calendar, frozenset()),
    ("minimal_loe", _seed_ready_loe, frozenset()),
)


@pytest.mark.parametrize(
    ("target", "seed", "collateral"), _READY_SEEDS, ids=[s[0] for s in _READY_SEEDS]
)
def test_sra_readiness_seeded_gate_fails_exactly_where_declared(
    target: str, seed: Callable[[Schedule], Schedule], collateral: frozenset[str]
) -> None:
    clean = _gate_statuses(_readiness(_dated(clean_program())))
    card = _readiness(seed(_dated(clean_program())))
    seeded = _gate_statuses(card)
    assert clean[target] == "PASS"
    assert seeded[target] == "FAIL", f"{target} did not flag its seeded defect"
    moved = {k for k in seeded if seeded[k] != clean[k]}
    assert moved == {target} | set(collateral), (
        f"seeding {target} moved {sorted(moved)}; declared {sorted({target} | set(collateral))}"
    )


def test_sra_readiness_offenders_cite_the_seeded_activities() -> None:
    """The gates cite the right activities: the stripped-WBS pair, the LOE task, and the
    phase-1 rule that ONE self-pinning MFO rides inside the hard-constraint tolerance (4%,
    still PASS) while it defeats the critical-path test."""
    by_key = {c.key: c for c in _readiness(_seed_ready_wbs(_dated(clean_program()))).checks}
    assert by_key["wbs_mapped"].offender_uids == (7, 8)
    by_key = {c.key: c for c in _readiness(_seed_ready_loe(_dated(clean_program()))).checks}
    assert by_key["minimal_loe"].offender_uids == (6,)
    by_key = {c.key: c for c in _readiness(_seed_cp_broken(_dated(clean_program()))).checks}
    assert by_key["critical_path"].status == "FAIL"
    assert by_key["hard_constraints"].status == "PASS"
    assert by_key["hard_constraints"].detail == "1 of 25 (4.0%)"


# --- every page renders on every corpus -------------------------------------------


@pytest.mark.parametrize("corpus", ["clean", "seeded", "tp4_family"])
def test_every_page_renders_on_the_corpus(corpus: str) -> None:
    """A defect in the data must degrade a panel, never crash the page."""
    if corpus == "clean":
        client = _mount({"clean.xml": clean_program()})
    elif corpus == "seeded":
        wrecked = clean_program()
        for _target, seed, _c in SEEDS:
            wrecked = seed(wrecked)
        client = _mount({"clean.xml": clean_program(), "wrecked.xml": wrecked})
    else:
        client = TestClient(create_app(SessionState()))
        paths = [FIX / f"TP4_DataCenter_v{i}.xml" for i in range(1, 6)]
        files = [("files", (p.name, p.read_bytes(), "text/xml")) for p in paths]
        meta = json.dumps(
            [
                {"rel": f"TP4/{p.name}", "mtime": 1_700_000_000_000 + i * 86_400_000}
                for i, p in enumerate(paths)
            ]
        )
        assert client.post("/upload", files=files, data={"file_meta": meta}).status_code == 200
    with client:
        failures = []
        for page in _get_pages(client):
            r = client.get(page)
            if r.status_code != 200:
                failures.append(f"{page} = {r.status_code}")
        assert not failures, f"pages that crash on the {corpus} corpus: {failures}"
