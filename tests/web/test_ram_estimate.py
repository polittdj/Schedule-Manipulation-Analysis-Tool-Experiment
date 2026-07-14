"""v4 Feature 2: the RAM-estimate safety rail — a big ingest WARNS, never blocks, and the operator
can tune the threshold. The estimate + control surface on the Portfolio page."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

_NS = 'xmlns="http://schemas.microsoft.com/project"'
_TASK = "<Tasks><Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration></Task></Tasks>"


def _mspdi(title: str) -> bytes:
    return (
        f"<Project {_NS}><StartDate>2025-01-06T08:00:00</StartDate>"
        f"<Title>{title}</Title>{_TASK}</Project>"
    ).encode()


@pytest.fixture
def sc() -> tuple[SessionState, TestClient]:
    st = SessionState()
    return st, TestClient(create_app(st))


def test_ingest_over_threshold_warns_but_still_loads(sc: tuple[SessionState, TestClient]) -> None:
    st, client = sc
    st.ram_warn_bytes = 1  # any load exceeds → the warning always fires
    page = client.post(
        "/upload",
        files=[
            ("files", ("a.xml", _mspdi("Alpha"), "text/xml")),
            ("files", ("b.xml", _mspdi("Beta"), "text/xml")),
        ],
    ).text
    assert "estimated" in page and "memory" in page  # the non-blocking warning rendered
    assert len(st.schedules) == 2  # never blocked — both files loaded


def test_ram_threshold_is_configurable(sc: tuple[SessionState, TestClient]) -> None:
    st, client = sc
    client.post("/session/ram-threshold", data={"gb": "42"})
    assert st.ram_warn_bytes == (42 * 1024**3)


def test_threshold_floor_prevents_a_zero(sc: tuple[SessionState, TestClient]) -> None:
    st, client = sc
    client.post("/session/ram-threshold", data={"gb": "0"})
    assert st.ram_warn_bytes == 1  # clamped to a >=1 floor, never 0/negative


def test_portfolio_shows_the_memory_readout(sc: tuple[SessionState, TestClient]) -> None:
    _st, client = sc
    client.post("/upload", files=[("files", ("a.xml", _mspdi("Alpha"), "text/xml"))])
    page = client.get("/portfolio").text
    assert "Memory" in page
    assert "estimated resident memory" in page
    assert "/session/ram-threshold" in page  # the threshold control is present
