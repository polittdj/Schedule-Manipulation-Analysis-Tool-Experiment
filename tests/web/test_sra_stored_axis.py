"""The legacy SRA surface sits on ONE date axis — the stored plan's (ADR-0353).

The legacy ``/api/sra`` + ``/api/scorecards/buffer`` pair carried the cross-basis defect the
2026-07-30 root-cause file recorded as "SRA-LEGACY": the deterministic anchor was the ordinary
full-duration CPM finish bisected against a remaining-basis distribution (EVM1 measured
``deterministic_percentile`` 0.991 — a false "conservative plan" verdict), and every rendered
date was the naive pure-CPM conversion while the operator's committed date lives on the stored
plan axis (Project2's buffer panel measured 100% confidence / 0 reserve against a committed
date the distribution actually straddles).

The fixture is the EVM1 class distilled: one in-progress activity (50%, 5d remaining, NO
Resume reschedule — so no ADR-0309 floor reconciles the bases) plus a successor, with stored
Finish dates ~2 months past the naive axis. Everything below fails on the pre-ADR-0353 code.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

_NS = 'xmlns="http://schemas.microsoft.com/project"'

#: The latest stored finish — the anchor every displayed date realigns to.
_STORED_LATEST = "2025-03-18T17:00:00"


def _progressed_mspdi() -> bytes:
    """Groundwork (10d, 50% complete, 5d remaining) -> Closeout (2d); stored finishes far
    beyond the naive axis (all-ML solve = 7d from 2025-01-06 ~ mid-January)."""
    return (
        f"<Project {_NS}><StartDate>2025-01-06T08:00:00</StartDate>"
        "<Title>Progressed</Title>"
        "<Tasks><Task><UID>1</UID><Name>Groundwork</Name><Duration>PT80H0M0S</Duration>"
        "<PercentComplete>50</PercentComplete>"
        "<RemainingDuration>PT40H0M0S</RemainingDuration>"
        "<Finish>2025-03-14T17:00:00</Finish></Task>"
        "<Task><UID>2</UID><Name>Closeout</Name><Duration>PT16H0M0S</Duration>"
        f"<Finish>{_STORED_LATEST}</Finish>"
        "<PredecessorLink><PredecessorUID>1</PredecessorUID><Type>1</Type></PredecessorLink>"
        "</Task></Tasks></Project>"
    ).encode()


@pytest.fixture
def client() -> TestClient:
    st = SessionState()
    c = TestClient(create_app(st))
    r = c.post("/upload", files=[("files", ("prog.xml", _progressed_mspdi(), "text/xml"))])
    assert r.status_code in (200, 303)
    return c


def test_api_sra_deterministic_lands_on_the_stored_finish(client: TestClient) -> None:
    """Leg B end-to-end: the payload's deterministic date IS the latest stored finish (the
    anchor), not the naive conversion (~2025-01-14); and leg A: the percentile is a real
    same-basis read, not the saturated ~100% the full-duration anchor produced."""
    d = client.get("/api/sra?iterations=200").json()
    assert "error" not in d, d
    assert d["deterministic"]["date"] == _STORED_LATEST
    assert 15.0 <= d["deterministic"]["percentile"] <= 85.0
    # the S-curve is on the same axis: its dates bracket the stored anchor, not mid-January
    first_date, _p = d["cdf"][0]
    last_date, _p2 = d["cdf"][-1]
    assert first_date.startswith("2025-03")
    assert last_date.startswith("2025-03")
    # percentile rows too (the commitment card's inputs)
    assert all(row["date"].startswith("2025-03") for row in d["percentiles"])


def test_buffer_confidence_is_honest_on_the_shared_axis(client: TestClient) -> None:
    """The committed date converts through the run's correction onto the CDF's axis.

    Committing to 2025-03-17 — one working day BEFORE the anchor — must read as at-risk
    (the distribution straddles the anchor), with a positive P80 reserve and row dates on
    the stored axis. Pre-ADR-0353 this read 100% confidence / 0.0 reserve, because the naive
    committed offset sat weeks past the entire packed distribution."""
    d = client.get("/api/scorecards/buffer?committed=2025-03-17&iterations=200").json()
    assert "error" not in d, d
    assert d["committed_confidence"] < 0.5
    assert d["recommended_p80_days"] > 0.0
    assert d["deterministic_finish_date"] == _STORED_LATEST
    rows = {r["percentile"]: r for r in d["rows"]}
    assert rows[80]["finish_date"].startswith("2025-03")
    assert rows[80]["reserve_days"] > 0.0
