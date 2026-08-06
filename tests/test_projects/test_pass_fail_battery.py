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

Queued extensions (framework in place, same pair pattern): per-family pairs for cei, hmi,
fei/bri, evm, schedule_quality, forecast and the SRA readiness gate.
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
from schedule_forensics.engine.manipulation import detect_manipulation
from schedule_forensics.engine.metrics._common import CheckStatus
from schedule_forensics.engine.metrics.completion_performance import (
    compute_completion_performance,
)
from schedule_forensics.engine.metrics.float_bands import compute_float_bands
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
