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
