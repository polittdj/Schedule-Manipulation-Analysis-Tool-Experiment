"""Real-world .mpp/MSPDI robustness — constructs the curated golden files never contain.

Uploaded via the web layer as MSPDI (.xml), the same model path a native .mpp takes after the
MPXJ conversion. Proves the file loads AND its report renders (no rejection, no 500)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

_NS = 'xmlns="http://schemas.microsoft.com/project"'


def _mspdi(body: str) -> bytes:
    start = "<StartDate>2026-01-05T08:00:00</StartDate>"
    return f"<Project {_NS}>{start}<Tasks>{body}</Tasks></Project>".encode()


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def test_external_link_and_alap_file_loads_and_reports(client: TestClient) -> None:
    # A two-activity schedule with (a) an external/sub-project predecessor (UID 9999 absent)
    # and (b) an ALAP constraint — both rejected the whole file before this fix.
    body = (
        "<Task><UID>1</UID><Name>Design</Name><Duration>PT8H0M0S</Duration>"
        "<ConstraintType>1</ConstraintType></Task>"  # ALAP
        "<Task><UID>2</UID><Name>Build</Name><Duration>PT16H0M0S</Duration>"
        "<PredecessorLink><PredecessorUID>1</PredecessorUID><Type>1</Type></PredecessorLink>"
        "<PredecessorLink><PredecessorUID>9999</PredecessorUID><Type>1</Type></PredecessorLink>"
        "</Task>"
    )
    r = client.post(
        "/upload",
        files={"files": ("RealPlan.xml", _mspdi(body), "text/xml")},
        follow_redirects=False,
    )
    assert r.status_code == 303 and r.headers["location"].startswith("/analysis/")
    assert client.get("/healthz").json()["loaded"] == 1  # loaded, not rejected
    page = client.get("/analysis/RealPlan")
    assert page.status_code == 200 and "DCMA-14 audit" in page.text  # report renders
    data = client.get("/api/analysis/RealPlan").json()
    assert data["tasks"] == 2  # the external 9999 link did not add a phantom task


def test_cp_test_failing_schedule_renders_report_and_trend(client: TestClient) -> None:
    # Operator-hit crash: a schedule failing the (schedule-level) DCMA Critical Path Test
    # produced an uncited narrative statement -> 500 on the report, API, and trend pages.
    def version(label: str, status_day: int) -> bytes:
        body = (
            b"<Task><UID>1</UID><Name>DeadlineDriven</Name><Duration>PT8H0M0S</Duration>"
            b"<Deadline>2026-01-05T08:00:00</Deadline></Task>"
            b"<Task><UID>2</UID><Name>Controlling</Name><Duration>PT80H0M0S</Duration></Task>"
        )
        start = (
            f"<StartDate>2026-01-05T08:00:00</StartDate>"
            f"<StatusDate>2026-01-{status_day:02d}T17:00:00</StatusDate>"
        )
        return f"<Project {_NS}>{start}<Tasks>{body.decode()}</Tasks></Project>".encode()

    for i, name in enumerate(("CPv1.xml", "CPv2.xml"), start=1):
        client.post("/upload", files={"files": (name, version(name, 5 + i), "text/xml")})
    assert client.get("/healthz").json()["loaded"] == 2
    assert client.get("/analysis/CPv1").status_code == 200  # report renders
    assert client.get("/api/analysis/CPv1").status_code == 200  # grid/drill data loads
    trend = client.get("/trend")
    assert trend.status_code == 200  # was: Internal Server Error
    assert "Version trend" in trend.text
    assert client.get("/briefing").status_code == 200


def test_one_bad_file_does_not_sink_the_multi_version_views(client: TestClient) -> None:
    # two good versions + one cyclic file: trend/compare/briefing analyze the good pair
    # and NAME the skipped version instead of returning a 500.
    def good(status_day: int) -> bytes:
        start = (
            f"<StartDate>2026-01-05T08:00:00</StartDate>"
            f"<StatusDate>2026-01-{status_day:02d}T17:00:00</StatusDate>"
        )
        body = "<Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration></Task>"
        return f"<Project {_NS}>{start}<Tasks>{body}</Tasks></Project>".encode()

    loop = (
        "<Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration>"
        "<PredecessorLink><PredecessorUID>2</PredecessorUID><Type>1</Type></PredecessorLink>"
        "</Task>"
        "<Task><UID>2</UID><Name>B</Name><Duration>PT8H0M0S</Duration>"
        "<PredecessorLink><PredecessorUID>1</PredecessorUID><Type>1</Type></PredecessorLink>"
        "</Task>"
    )
    client.post("/upload", files={"files": ("Good1.xml", good(6), "text/xml")})
    client.post("/upload", files={"files": ("Bad.xml", _mspdi(loop), "text/xml")})
    client.post("/upload", files={"files": ("Good2.xml", good(13), "text/xml")})
    for path in ("/trend", "/compare", "/briefing"):
        page = client.get(path)
        assert page.status_code == 200, path
        assert "Skipped" in page.text and "Bad" in page.text, path  # the bad version is named
    assert client.get("/api/trend").status_code == 200


def test_logic_cycle_shows_readable_notice_not_500(client: TestClient) -> None:
    # A circular dependency (1->2->1) cannot be scheduled; the page must explain, not crash.
    body = (
        "<Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration>"
        "<PredecessorLink><PredecessorUID>2</PredecessorUID><Type>1</Type></PredecessorLink>"
        "</Task>"
        "<Task><UID>2</UID><Name>B</Name><Duration>PT8H0M0S</Duration>"
        "<PredecessorLink><PredecessorUID>1</PredecessorUID><Type>1</Type></PredecessorLink>"
        "</Task>"
    )
    client.post("/upload", files={"files": ("Loop.xml", _mspdi(body), "text/xml")})
    assert client.get("/healthz").json()["loaded"] == 1  # the file still loaded
    page = client.get("/analysis/Loop")
    assert page.status_code == 200  # not a 500
    assert "cannot compute the network" in page.text and "circular dependency" in page.text
    assert client.get("/api/analysis/Loop").status_code == 422  # API reports it cleanly
