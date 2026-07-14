"""The /path ('What drives a date') page must default its driving-path grid to the SAME version its
summary header describes (the latest by data date). Before the fix the header was anchored on the
latest version while the schedule <select> defaulted to the browser's first option (the OLDEST
version) — so one file's header sat above another file's path: the operator's 'the critical path is
mixing up information from the various files' report."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

_NS = 'xmlns="http://schemas.microsoft.com/project"'


def _mspdi(title: str, status: str) -> bytes:
    task = "<Tasks><Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration></Task></Tasks>"
    return (
        f"<Project {_NS}><StartDate>2025-01-06T08:00:00</StartDate>"
        f"<Title>{title}</Title><StatusDate>{status}</StatusDate>{task}</Project>"
    ).encode()


@pytest.fixture
def sc() -> tuple[SessionState, TestClient]:
    st = SessionState()
    return st, TestClient(create_app(st))


def test_path_grid_defaults_to_the_latest_version(sc: tuple[SessionState, TestClient]) -> None:
    _st, client = sc
    # two versions of one project; 'newer' has the later data date → it is keys[-1] (the latest)
    client.post(
        "/upload",
        files=[
            ("files", ("older.xml", _mspdi("IMS", "2025-01-10T00:00:00"), "text/xml")),
            ("files", ("newer.xml", _mspdi("IMS", "2025-06-10T00:00:00"), "text/xml")),
        ],
    )
    page = client.get("/path").text
    # the latest version's <option> carries `selected`; the older one does not — so the grid the
    # user first sees is the same version the header above it summarizes.
    assert '<option value="newer" selected>' in page
    assert '<option value="older" selected>' not in page
    assert '<option value="older">' in page
