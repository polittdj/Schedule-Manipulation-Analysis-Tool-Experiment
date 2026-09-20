"""The tool's displayed rounding families, observed AT AN EXACT TIE on the rendered payloads
(R-04, ADR-0515).

R-04 asked that each displayed rounding be read against the reference tool's own rule at a tie.
The reading (ADR-0515, `tests/parity/test_fuse_forensic_rounding_oracle.py`): every rule Acumen
Fuse's own code applies at a tie is half-to-even — its whole-day fields, its day changes, its 2-dp
ratios — which is what Python's ``round()`` is. So these pins do not certify a fix; they make the
rule OBSERVABLE where the corpus makes it common (292 stored floats and 74 durations sit on a
displayed tie across the goldens), and they name the half-up reading each site refuses. Every
tie here is DERIVED from the raw result inside the test (an odd sixteenth, an odd thirty-second,
an exact quarter day), so a change in the engine's draws fails loudly instead of quietly pinning
a non-tie. Each pin was observed red under a ``round_half_up`` mutant at its caller on a shadow
copy of the package (the ADR's verification table).
"""

from __future__ import annotations

import datetime as dt
from fractions import Fraction

from fastapi.testclient import TestClient

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.jcl import JCLConfig, compute_jcl
from schedule_forensics.engine.sra import SRAConfig, compute_sra
from schedule_forensics.engine.sra_conclusions import _pct, _wd
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import SessionState, _jcl_data, _jcl_export_tables, create_app
from schedule_forensics.web.sra import _sra_data

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _ties() -> Schedule:
    """Two parallel legs of near-equal length (so the criticality index lands on odd
    thirty-seconds), a 0.25-day lag, a 1.25-day and a 1.125-day duration, and a 30-day chain
    so the sampled finishes spread across calendar days."""
    tasks = (
        Task(unique_id=1, name="Kickoff", duration_minutes=DAY, budgeted_cost=100.0),
        Task(unique_id=2, name="Design", duration_minutes=600, budgeted_cost=1000.0),  # 1.25 d
        Task(unique_id=3, name="Build", duration_minutes=720, budgeted_cost=800.0),
        Task(unique_id=4, name="Test", duration_minutes=30 * DAY, budgeted_cost=6000.0),
        Task(unique_id=5, name="Handover", duration_minutes=0, is_milestone=True),
        Task(  # 1.125 d, off the critical path
            unique_id=6,
            name="Spare",
            duration_minutes=540,
            budgeted_cost=300.0,
            remaining_duration_minutes=540,
            baseline_duration_minutes=540,
        ),
    )
    fs = RelationshipType.FS
    rels = (
        Relationship(predecessor_id=1, successor_id=2, type=fs, lag_minutes=120),  # 0.25 d
        Relationship(predecessor_id=1, successor_id=3, type=fs),
        Relationship(predecessor_id=2, successor_id=4, type=fs),
        Relationship(predecessor_id=3, successor_id=4, type=fs),
        Relationship(predecessor_id=4, successor_id=5, type=fs),
        Relationship(predecessor_id=1, successor_id=6, type=fs),
    )
    return Schedule(
        name="Ties", project_start=MON, status_date=MON, tasks=tasks, relationships=rels
    )


def _client(sch: Schedule) -> TestClient:
    st = SessionState()
    st.schedules["ties"] = sch
    return TestClient(create_app(st))


def _odd_sixteenths(value: float) -> int:
    """The numerator of ``value`` over 16 — asserting it IS a sixteenth and it is odd (a tie at
    one decimal of a percent: k x 6.25)."""
    f = Fraction(value).limit_denominator(16) * 16
    assert f.denominator == 1 and int(f) % 2 == 1, f"not an odd sixteenth: {value}"
    return int(f)


# ── whole days / whole percent (the SRA conclusions' own helpers) ────────────────────────────


def test_whole_day_and_whole_percent_helpers_round_half_to_even() -> None:
    # Fuse's whole-day fields: 0.5 → 0, 1.5 → 2, 2.5 → 2 (ADR-0515 M1; half-up says 1 / 2 / 3)
    assert (_wd(240, 480), _wd(720, 480), _wd(1200, 480)) == (0, 2, 2)
    assert (_pct(0.125), _pct(0.625)) == (12, 62)  # half-up says 13 / 63


# ── days at 1 dp / 2 dp ───────────────────────────────────────────────────────────────────────


def test_days_at_one_dp_on_the_driving_payload() -> None:
    payload = _client(_ties()).get("/api/driving/ties?target=5").json()
    links = {(r["unique_id"], lk["uid"]): lk for r in payload["rows"] for lk in r["drives"]}
    assert Fraction(120, DAY) == Fraction(1, 4)  # the lag is an exact quarter day
    assert links[(1, 2)]["lag_days"] == 0.2  # half-even; half-up would print 0.3
    rows = {r["unique_id"]: r for r in payload["rows"]}
    assert Fraction(600, DAY) == Fraction(5, 4)
    assert rows[2]["duration_days"] == 1.2  # 1.25 d; half-up would print 1.3


def test_days_at_two_dp_on_the_analysis_payload() -> None:
    payload = _client(_ties()).get("/api/analysis/ties").json()
    row = next(r for r in payload["activities"] if r["unique_id"] == 6)
    assert Fraction(540, DAY) == Fraction(9, 8)  # 1.125 d — an exact tie at two decimals
    assert row["remaining_duration_days"] == 1.12  # half-up would print 1.13
    assert row["baseline_duration_days"] == 1.12


# ── percent at 1 dp (the SRA / JCL payloads and the Excel hand-out) ──────────────────────────


def test_percent_at_one_dp_on_the_jcl_payload_and_export() -> None:
    sch = _ties()
    three_point = {2: (540, 600, 660), 3: (648, 720, 792), 4: (12960, 14400, 15840)}
    result = compute_jcl(
        sch, config=SRAConfig(iterations=16, seed=1), three_point=three_point, jcl=JCLConfig()
    )
    k = _odd_sixteenths(result.scl)  # 9 of 16 finishes on/before the target date
    assert k * Fraction(625, 100) == Fraction(5625, 100)  # 56.25 %, the tie
    data = _jcl_data(sch, result)
    assert data["levels"]["scl"] == 56.2  # half-up would print 56.3
    rows = dict(_jcl_export_tables(result)[0].rows)
    assert rows["SCL - P(finish on/before target date) %"] == 56.2


def test_percent_at_one_dp_on_the_sra_payload() -> None:
    sch = _ties()
    result = compute_sra(sch, config=SRAConfig(iterations=16, seed=5))
    assert _odd_sixteenths(result.deterministic_percentile) == 9
    data = _sra_data(SessionState(), sch, compute_cpm(sch), result)
    assert data["deterministic"]["percentile"] == 56.2  # half-up would print 56.3


# ── a value at 4 dp (the SRA sensitivity table) ───────────────────────────────────────────────


def test_value_at_four_dp_on_the_sra_sensitivity() -> None:
    sch = _ties()
    result = compute_sra(sch, config=SRAConfig(iterations=32, seed=1))
    ci = next(a.criticality_index for a in result.activities if a.unique_id == 2)
    assert Fraction(ci).limit_denominator(32) == Fraction(17, 32)  # 0.53125 — the tie
    data = _sra_data(SessionState(), sch, compute_cpm(sch), result)
    shown = next(s for s in data["sensitivity"] if s["uid"] == 2)
    assert shown["ci"] == 0.5312  # half-up would print 0.5313


# ── a whole percent on a rendered page ────────────────────────────────────────────────────────


def test_whole_percent_on_the_analysis_pressure_table() -> None:
    """A 12.5 %-complete critical activity prints 12 % (half-up would print 13 %)."""
    tasks = (
        Task(
            unique_id=1,
            name="Started",
            duration_minutes=20 * DAY,
            percent_complete=12.5,
            actual_start=MON,
        ),
        Task(unique_id=2, name="Next", duration_minutes=5 * DAY),
    )
    rels = (Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.FS),)
    sch = Schedule(
        name="Pct",
        project_start=MON,
        status_date=MON + dt.timedelta(days=3),
        tasks=tasks,
        relationships=rels,
    )
    page = _client(sch).get("/analysis/ties").text
    assert "<td>12%</td>" in page and "<td>13%</td>" not in page
