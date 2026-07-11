"""Plain-language SRA conclusions tests (ADR-0201).

The conclusions layer turns a Monte-Carlo result into Hulett-style sentences ("the planned
date is only N% likely"). These tests pin the tier wording, the number agreement, the
degenerate-run honesty, and the figure-fidelity property: every digit that appears in a
``finding`` is backed by that conclusion's ``evidence`` pairs (Law 2 — no fabricated figure
can reach the analyst through a template).
"""

from __future__ import annotations

import datetime as dt
import re

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.sra import SRAConfig, SSIResult, compute_sra
from schedule_forensics.engine.sra_conclusions import (
    Conclusion,
    _commitment,
    _constraints,
    _contingency,
    _correlation,
    _precision,
    _realism,
    _spread,
    conclusions_as_dicts,
    conclusions_from_sra,
    conclusions_from_ssi,
)
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)  # a Monday, working-day start
DAY = 480


def _task(uid: int, dur_days: float) -> Task:
    return Task(unique_id=uid, name=f"T{uid}", duration_minutes=int(dur_days * DAY))


def _rel(p: int, s: int) -> Relationship:
    return Relationship(predecessor_id=p, successor_id=s, type=RelationshipType.FS, lag_minutes=0)


def _sched() -> Schedule:
    # 2d -> 3d -> 1d chain: one deterministic critical path.
    return Schedule(
        name="S",
        project_start=MON,
        tasks=(_task(1, 2), _task(2, 3), _task(3, 1)),
        relationships=(_rel(1, 2), _rel(2, 3)),
    )


# ── tier wording ─────────────────────────────────────────────────────────────────────────


def test_realism_tiers() -> None:
    assert _realism("2025-06-01", 0.10, "the project").severity == "bad"
    assert "optimistic" in _realism("2025-06-01", 0.10, "the project").finding
    assert _realism("2025-06-01", 0.30, "the project").severity == "warn"
    assert "coin flip" in _realism("2025-06-01", 0.50, "the project").finding
    assert _realism("2025-06-01", 0.50, "the project").severity == "info"
    assert _realism("2025-06-01", 0.70, "the project").severity == "good"
    assert "conservative" in _realism("2025-06-01", 0.95, "the project").finding


def test_realism_shortens_iso_datetimes_to_days() -> None:
    c = _realism("2025-06-01T16:00:00", 0.5, "the project")
    assert "T16:00:00" not in c.finding
    assert "2025-06-01" in c.finding


def test_contingency_positive_and_covered_with_number_agreement() -> None:
    # one working day beyond the plan -> singular "1 working day"
    c = _contingency(det_finish=0, p80=DAY, p80_date="2025-01-07", det_date="2025-01-06")
    assert c.severity == "warn" and "1 working day " in c.finding + " "
    assert "1 working days" not in c.finding
    covered = _contingency(det_finish=DAY, p80=0, p80_date="2025-01-06", det_date="2025-01-07")
    assert covered.severity == "good" and "no added" in covered.finding


def test_spread_commitment_and_precision_wording() -> None:
    s = _spread(0, 10 * DAY, "2025-01-06", "2025-01-20")
    assert "10 working days" in s.finding and s.topic == "Predictability"
    m = _commitment("2025-03-01", "2025-04-01")
    assert "80% confidence" in m.finding and "2025-04-01" in m.finding
    assert _precision(1000).severity == "info" and "screening" in _precision(1000).finding
    assert _precision(2500).severity == "good"


def test_constraints_number_agreement() -> None:
    assert _constraints(0) is None
    one = _constraints(1)
    many = _constraints(3)
    assert one is not None and "1 hard constraint caps" in one.finding
    assert many is not None and "3 hard constraints cap" in many.finding


def test_correlation_card_only_when_informative() -> None:
    zero = _correlation(0.0, used_risks=False)
    assert zero is not None and "independently" in zero.finding
    assert _correlation(0.0, used_risks=True) is None  # risks correlate; nothing to warn
    blanket = _correlation(0.4, used_risks=False)
    assert blanket is not None and "0.4" in blanket.finding


# ── adapters over real simulations ───────────────────────────────────────────────────────


def test_conclusions_from_sra_covers_the_core_topics() -> None:
    sch = _sched()
    cpm = compute_cpm(sch)
    result = compute_sra(sch, cpm, config=SRAConfig(iterations=300, seed=42))
    concl = conclusions_from_sra(sch, cpm, result)
    topics = [c.topic for c in concl]
    for expected in (
        "Planned-date realism",
        "Commitment dates",
        "Contingency needed",
        "Predictability",
        "Input quality",
        "Sampling precision",
    ):
        assert expected in topics, expected
    # auto triangular defaults -> the input-quality card must say screening, honestly
    quality = next(c for c in concl if c.topic == "Input quality")
    assert quality.severity == "warn" and "screening" in quality.finding


def test_conclusions_are_deterministic_for_a_seed() -> None:
    sch = _sched()
    cpm = compute_cpm(sch)
    a = conclusions_from_sra(sch, cpm, compute_sra(sch, cpm, config=SRAConfig(300, seed=7)))
    b = conclusions_from_sra(sch, cpm, compute_sra(sch, cpm, config=SRAConfig(300, seed=7)))
    assert a == b


def _ssi(p10: int, p90: int, **over: object) -> SSIResult:
    base: dict[str, object] = {
        "iterations": 300,
        "seed": 1,
        "target_uid": None,
        "distribution": "triangular",
        "occurrence_mode": "random",
        "correlation": 0.0,
        "used_risks": False,
        "deterministic_finish": p10,
        "deterministic_percentile": 0.5,
        "p10": p10,
        "p50": (p10 + p90) // 2,
        "p80": p90,
        "p90": p90,
        "mean": float(p10),
        "std_days": 0.0,
        "deterministic_finish_date": "2025-02-03",
        "p10_date": "2025-02-03",
        "p50_date": "2025-02-05",
        "p80_date": "2025-02-07",
        "p90_date": "2025-02-07",
        "mean_date": "2025-02-05",
        "cdf": (),
        "histogram": (),
    }
    base.update(over)
    return SSIResult(**base)  # type: ignore[arg-type]


def test_ssi_degenerate_run_says_no_uncertainty_inputs() -> None:
    concl = conclusions_from_ssi(_sched(), _ssi(p10=10 * DAY, p90=10 * DAY))
    assert concl[0].topic == "No uncertainty inputs" and concl[0].severity == "warn"
    # the misleading percentile cards are suppressed
    assert all(c.topic != "Commitment dates" for c in concl)


def test_ssi_normal_run_carries_the_core_topics() -> None:
    concl = conclusions_from_ssi(_sched(), _ssi(p10=8 * DAY, p90=12 * DAY))
    topics = [c.topic for c in concl]
    for expected in ("Planned-date realism", "Commitment dates", "Predictability"):
        assert expected in topics, expected


# ── figure fidelity: every digit in a finding is backed by the evidence pairs ────────────


def _digit_tokens(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?", text))


def _assert_figures_backed(conclusions: tuple[Conclusion, ...]) -> None:
    for c in conclusions:
        backing = " ".join(f"{label} {value}" for label, value in c.evidence)
        missing = _digit_tokens(c.finding) - _digit_tokens(backing)
        # tolerate the "80" of the fixed P80 phrasing and "1 in 7"-style idiom digits: they
        # are constants of the template, not run figures — everything else must be backed
        idiom = {"80", "50", "1", "7", "2", "500", "10", "000"}
        assert missing <= idiom, f"{c.topic}: unbacked figures {missing} in {c.finding!r}"


def test_findings_carry_no_unbacked_figures() -> None:
    sch = _sched()
    cpm = compute_cpm(sch)
    result = compute_sra(sch, cpm, config=SRAConfig(iterations=300, seed=42))
    _assert_figures_backed(conclusions_from_sra(sch, cpm, result))
    _assert_figures_backed(conclusions_from_ssi(sch, _ssi(p10=8 * DAY, p90=12 * DAY)))


def test_dict_form_matches_the_cards() -> None:
    sch = _sched()
    cpm = compute_cpm(sch)
    result = compute_sra(sch, cpm, config=SRAConfig(iterations=200, seed=3))
    concl = conclusions_from_sra(sch, cpm, result)
    dicts = conclusions_as_dicts(concl)
    assert len(dicts) == len(concl)
    assert dicts[0]["topic"] == concl[0].topic
    assert dicts[0]["evidence"] == [
        {"label": label, "value": value} for label, value in concl[0].evidence
    ]
