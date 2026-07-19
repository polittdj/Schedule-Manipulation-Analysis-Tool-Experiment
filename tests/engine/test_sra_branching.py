"""Probabilistic branching for the SSI Monte-Carlo (ADR-0273, Hulett #8).

A probabilistic branch inserts a *rework* fragnet onto an existing FS tie in p% of iterations,
producing the bi-modal finish distribution (a spike at "no failure" + a shifted lump when the
rework happens) the deterministic plan hides. These pin: the freeze (no branch == byte-identical),
the passthrough (a fired branch that stays off the driving path never moves the finish — merge
bias), the exact shift when it drives, the reported stats, inert disclosure, and determinism.
The augmentation mechanism itself was verified against the trusted ``compute_cpm`` before build.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.sra import (
    ProbabilisticBranch,
    SRAConfig,
    compute_sra_ssi,
)
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _task(uid: int, dur_days: float) -> Task:
    return Task(unique_id=uid, name=f"T{uid}", duration_minutes=int(dur_days * DAY))


def _rel(p: int, s: int) -> Relationship:
    return Relationship(predecessor_id=p, successor_id=s, type=RelationshipType.FS, lag_minutes=0)


def _focus_net() -> Schedule:
    # 1(1d) -> 2(10d driver) -> 4(focus 1d); 1 -> 3(2d) -> 4. Deterministic focus finish = 12 days.
    return Schedule(
        name="S",
        project_start=MON,
        tasks=(_task(1, 1), _task(2, 10), _task(3, 2), _task(4, 1)),
        relationships=(_rel(1, 2), _rel(1, 3), _rel(2, 4), _rel(3, 4)),
    )


def _branch(after: int, before: int, days: float, p: float, **kw: object) -> ProbabilisticBranch:
    d = int(days * DAY)
    return ProbabilisticBranch(
        id=str(kw.get("id", "B1")),
        name=str(kw.get("name", "Rework")),
        probability=p,
        after_uid=after,
        before_uid=before,
        low=int(kw.get("low", d)),  # type: ignore[arg-type]
        ml=d,
        high=int(kw.get("high", d)),  # type: ignore[arg-type]
    )


# --- the freeze --------------------------------------------------------------------------


def test_no_branches_is_byte_identical() -> None:
    """Passing no branches (the default) leaves the run byte-frozen."""
    s = _focus_net()
    cfg = SRAConfig(iterations=100, seed=1, target_uid=4)
    a = compute_sra_ssi(s, config=cfg)
    b = compute_sra_ssi(s, config=cfg, branches=())
    assert a.cdf == b.cdf
    assert a.branches == () == b.branches


# --- firing shifts the finish; bi-modal split --------------------------------------------


def test_branch_on_the_driving_path_is_bimodal() -> None:
    """A point-mass 5-day rework on the driving 2->4 tie, firing half the time, splits the finish
    into exactly two values: 12 d (no fire) and 17 d (fire) — the bi-modal signature."""
    s = _focus_net()
    br = _branch(after=2, before=4, days=5, p=0.5)
    r = compute_sra_ssi(s, config=SRAConfig(iterations=400, seed=1, target_uid=4), branches=[br])
    finishes = {off for off, _p in r.cdf}
    assert finishes == {12 * DAY, 17 * DAY}  # two modes, exactly
    bs = r.branches[0]
    assert bs.applied and bs.id == "B1"
    assert 0.4 < bs.fired_fraction < 0.6  # ~50% firing
    assert bs.mean_fragnet_days == 5.0  # the rework magnitude
    assert abs(bs.mean_delta_days - 5.0) < 1e-9  # fired finishes 5 working days later, on average


def test_certain_branch_shifts_every_iteration() -> None:
    s = _focus_net()
    br = _branch(after=2, before=4, days=5, p=1.0)
    r = compute_sra_ssi(s, config=SRAConfig(iterations=50, seed=2, target_uid=4), branches=[br])
    assert r.p10 == r.p50 == r.p90 == 17 * DAY  # fires every time -> a clean +5d shift
    assert r.branches[0].fired_fraction == 1.0


# --- merge bias: a fired branch off the driving path need not move the finish -------------


def test_offpath_branch_that_does_not_overtake_leaves_finish_unchanged() -> None:
    """A 3-day rework on the SHORT 3->4 path (slack 8 d) fires every iteration but never overtakes
    the 10-day driver, so the focus finish stays 12 d — the branch participates in merge bias as a
    real node, unlike a blanket duration add. Its mean_delta is 0 (fired but immaterial)."""
    s = _focus_net()
    br = _branch(after=3, before=4, days=3, p=1.0)
    r = compute_sra_ssi(s, config=SRAConfig(iterations=40, seed=1, target_uid=4), branches=[br])
    assert r.p10 == r.p50 == r.p90 == 12 * DAY  # unchanged despite firing
    assert r.branches[0].fired_fraction == 1.0 and r.branches[0].applied


def test_offpath_branch_overtakes_when_large() -> None:
    s = _focus_net()
    br = _branch(after=3, before=4, days=12, p=1.0)  # 1+2+12+1 = 16 > 12 -> overtakes
    r = compute_sra_ssi(s, config=SRAConfig(iterations=30, seed=1, target_uid=4), branches=[br])
    assert r.p50 == 16 * DAY


# --- inert disclosure + determinism ------------------------------------------------------


def test_branch_on_missing_tie_is_inert_and_disclosed() -> None:
    """A branch whose after->before FS tie does not exist is never inserted; the finish is
    unchanged and the branch is reported applied=False (never silent)."""
    s = _focus_net()
    base = compute_sra_ssi(s, config=SRAConfig(iterations=50, seed=1, target_uid=4))
    br = _branch(after=99, before=4, days=5, p=1.0)  # no 99->4 tie exists
    r = compute_sra_ssi(s, config=SRAConfig(iterations=50, seed=1, target_uid=4), branches=[br])
    assert r.cdf == base.cdf  # inert -> byte-identical to no branch
    assert r.branches[0].applied is False and r.branches[0].hits == 0


def test_branching_is_deterministic_for_a_seed() -> None:
    s = _focus_net()
    br = _branch(after=2, before=4, days=5, p=0.5)
    cfg = SRAConfig(iterations=200, seed=7, target_uid=4)
    a = compute_sra_ssi(s, config=cfg, branches=[br])
    b = compute_sra_ssi(s, config=cfg, branches=[br])
    assert a.cdf == b.cdf
    assert a.branches == b.branches


def test_zero_probability_branch_is_ignored() -> None:
    s = _focus_net()
    base = compute_sra_ssi(s, config=SRAConfig(iterations=40, seed=1, target_uid=4))
    br = _branch(after=2, before=4, days=5, p=0.0)  # never fires -> not even inserted
    r = compute_sra_ssi(s, config=SRAConfig(iterations=40, seed=1, target_uid=4), branches=[br])
    assert r.cdf == base.cdf and r.branches == ()
