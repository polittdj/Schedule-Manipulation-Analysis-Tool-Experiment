"""Zero-margin SRA toggle (ADR-0266 — the Fig 7-43 follow-up ADR-0254 documented).

The §7.3.3.2.3 sufficiency panel's SRA carried the margin activities in-network at their plan
durations, while the handbook's Fig 7-43 curves are "Current Plan, ZERO Margin, With Risks".
The toggle runs the same seeded SRA with every margin activity's three-point set to (0, 0, 0)
— via the existing three-point surface, exactly as ADR-0254 prescribed — so the curve is the
handbook-faithful zero-margin distribution read against the unchanged [E, D] margin window.

The proof fixture is seed-independent: the MARGIN task carries the run's ONLY duration
uncertainty, so the zero-margin run must collapse to a DEGENERATE distribution (every
iteration identical) landing exactly on E — deterministic evidence the margin really was
zeroed inside the sampling, not merely relabeled.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

_NS = 'xmlns="http://schemas.microsoft.com/project"'


def _mspdi_with_margin() -> bytes:
    """Design (2d) -> Schedule Margin (5d) -> Build (3d): the margin task is name-detected
    and sits on the only chain, so zeroing it pulls the finish in by exactly its duration."""
    return (
        f"<Project {_NS}><StartDate>2025-01-06T08:00:00</StartDate>"
        "<Title>Alpha</Title>"
        "<Tasks><Task><UID>1</UID><Name>Design</Name><Duration>PT16H0M0S</Duration></Task>"
        "<Task><UID>2</UID><Name>Schedule Margin</Name><Duration>PT40H0M0S</Duration>"
        "<PredecessorLink><PredecessorUID>1</PredecessorUID><Type>1</Type></PredecessorLink>"
        "</Task><Task><UID>3</UID><Name>Build</Name><Duration>PT24H0M0S</Duration>"
        "<PredecessorLink><PredecessorUID>2</PredecessorUID><Type>1</Type></PredecessorLink>"
        "</Task></Tasks></Project>"
    ).encode()


@pytest.fixture
def sc() -> tuple[SessionState, TestClient]:
    st = SessionState()
    client = TestClient(create_app(st))
    client.post("/upload", files=[("files", ("m1.xml", _mspdi_with_margin(), "text/xml"))])
    # the MARGIN task carries the ONLY uncertainty: BC 3d / ML 5d / WC 8d (minutes)
    st.sra_bcwc[2] = (3 * 480, 8 * 480)
    return st, client


def test_default_run_is_the_in_network_basis(sc) -> None:  # type: ignore[no-untyped-def]
    _st, client = sc
    d = client.get("/api/margin/risk").json()
    assert "error" not in d, d
    assert d["zero_margin"] is False
    assert "in-network" in d["curve_basis"]
    assert d["degenerate"] is False  # the margin task's spread makes a real distribution
    # explicit zero_margin=0 is byte-identical to the absent param (seeded determinism)
    assert client.get("/api/margin/risk?zero_margin=0").json() == d


def test_zero_margin_run_collapses_to_e_exactly(sc) -> None:  # type: ignore[no-untyped-def]
    """With the ONLY uncertainty living on the margin task, zeroing it must produce a
    degenerate distribution whose every percentile finish IS the zero-margin bound E —
    the margin was provably removed from the sampling, not just from the label."""
    _st, client = sc
    d = client.get("/api/margin/risk?zero_margin=1").json()
    assert "error" not in d, d
    assert d["zero_margin"] is True
    assert "Zero Margin" in d["curve_basis"]  # the Fig 7-43 label travels with the data
    assert d["degenerate"] is True  # the only uncertainty was the margin task — now zeroed
    e_zero = d["zero_margin_finish"]
    assert d["margin_wd"] == 5.0  # D - E = the 5-day margin task, unchanged by the toggle
    for row in d["rows"]:
        assert row["finish_offset"] == e_zero  # every iteration lands exactly on E
        assert row["covered"] is True  # zero-margin risks fit inside the plan's margin


def test_panel_and_js_carry_the_toggle(sc) -> None:  # type: ignore[no-untyped-def]
    _st, client = sc
    html = client.get("/margin").text
    assert "id=marginRiskZero" in html
    assert "Zero Margin, With Risks" in html  # the Fig 7-43 citation stays on the panel
    js = client.get("/static/margin_dashboard.js").text
    assert "zero_margin=" in js  # the button forwards the checkbox
    assert "curve_basis" in js  # the provenance chip names the basis


def test_margin_export_names_the_curve_basis(sc) -> None:  # type: ignore[no-untyped-def]
    from io import BytesIO
    from zipfile import ZipFile

    _st, client = sc
    r = client.get("/export/xlsx/margin")
    assert r.status_code == 200
    with ZipFile(BytesIO(r.content)) as z:
        xml = " ".join(z.read(n).decode("utf-8", "replace") for n in z.namelist())
    assert "Curve basis" in xml and "in-network" in xml
