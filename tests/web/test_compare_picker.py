"""/compare picks ANY two versions (operator 2026-08-20).

"On the What Changed page I want the user to be able to select any two schedules and have the
program do a comparison of the two and show what has changed and not just the last two status
dates." Before this, ``/compare`` (and its export) hardcoded ``schedules[-2]``/``[-1]``.

The picker follows /integrity's precedent exactly (ADR's a/b Query params + the index-resolution
guard that defends chronology): defaults keep today's two-most-recent behavior byte-compatible
(the bare URL emits the bare export target), pick order can never render a reversed diff, and
the export routes resolve the SAME pair as the page (one shared resolver)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

_NS = 'xmlns="http://schemas.microsoft.com/project"'


def _mspdi(status: str, extra_task: bool = False) -> bytes:
    tasks = "<Task><UID>1</UID><Name>A</Name><Duration>PT40H0M0S</Duration></Task>"
    if extra_task:
        tasks += "<Task><UID>2</UID><Name>B</Name><Duration>PT16H0M0S</Duration></Task>"
    return (
        f"<Project {_NS}><Title>Triple</Title><StartDate>2025-01-06T08:00:00</StartDate>"
        f"<StatusDate>{status}</StatusDate><Tasks>{tasks}</Tasks></Project>"
    ).encode()


@pytest.fixture
def three(request: pytest.FixtureRequest) -> TestClient:
    client = TestClient(create_app(SessionState()))
    resp = client.post(
        "/upload",
        files=[
            ("files", ("jan.xml", _mspdi("2025-01-31T17:00:00"), "text/xml")),
            ("files", ("feb.xml", _mspdi("2025-02-28T17:00:00"), "text/xml")),
            ("files", ("mar.xml", _mspdi("2025-03-31T17:00:00", extra_task=True), "text/xml")),
        ],
    )
    assert resp.status_code == 200
    return client


def test_default_still_compares_the_two_most_recent(three: TestClient) -> None:
    """The twin: a bare /compare keeps today's behavior — feb → mar — and the bare export
    target (existing pins depend on that byte shape)."""
    page = three.get("/compare").text
    assert "feb.xml &rarr; mar.xml" in page
    assert 'data-export="/export/xlsx/compare"' in page


def test_operator_picks_any_two_versions(three: TestClient) -> None:
    page = three.get("/compare?a=0&b=1").text
    assert "jan.xml &rarr; feb.xml" in page
    assert "mar.xml &rarr;" not in page
    # the pair chip carries the picked ordinals (v1→v2, not v2→v3)
    assert "v1→v2" in page


def test_pick_order_never_reverses_chronology(three: TestClient) -> None:
    """a=1&b=0 must render the SAME chronological diff as a=0&b=1 — a reversed pair would be
    a Law-2 fidelity bug (deletions read as additions)."""
    forward = three.get("/compare?a=0&b=1").text
    backward = three.get("/compare?a=1&b=0").text
    assert "jan.xml &rarr; feb.xml" in backward
    assert forward == backward


def test_out_of_range_indices_fail_soft_to_the_default_pair(three: TestClient) -> None:
    page = three.get("/compare?a=99&b=-7").text
    assert "feb.xml &rarr; mar.xml" in page


def test_picker_renders_only_when_there_is_a_choice(three: TestClient) -> None:
    page = three.get("/compare").text
    assert "Baseline (A)" in page and "<select name=a>" in page
    # with exactly two versions there is nothing to pick — no picker controls
    two = TestClient(create_app(SessionState()))
    resp = two.post(
        "/upload",
        files=[
            ("files", ("jan.xml", _mspdi("2025-01-31T17:00:00"), "text/xml")),
            ("files", ("feb.xml", _mspdi("2025-02-28T17:00:00"), "text/xml")),
        ],
    )
    assert resp.status_code == 200
    assert "Baseline (A)" not in two.get("/compare").text


def test_export_resolves_the_same_picked_pair(three: TestClient) -> None:
    """The page at a picked pair points its export at the SAME pair, and that export is a
    live workbook — the page and the workbook can never describe different pairs."""
    page = three.get("/compare?a=0&b=1").text
    assert 'data-export="/export/xlsx/compare?a=0&amp;b=1"' in page
    resp = three.get("/export/xlsx/compare?a=0&b=1")
    assert resp.status_code == 200
    assert resp.content[:2] == b"PK"
    assert three.get("/export/docx/compare?a=0&b=1").status_code == 200
