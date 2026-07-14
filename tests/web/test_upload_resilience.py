"""Upload resilience: a fetch (AJAX) upload returns a JSON redirect, and files the browser could
not read (reported by home.js as ``skipped_files``) are surfaced in the manifest, never silently
lost — the fix for the folder-upload ``ERR_ACCESS_DENIED`` (an un-hydrated OneDrive placeholder or a
file open in MS Project fails the browser's read; the readable files still load)."""

from __future__ import annotations

import json

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


def test_ajax_upload_returns_json_redirect_not_a_303(sc: tuple[SessionState, TestClient]) -> None:
    st, client = sc
    r = client.post(
        "/upload",
        files=[("files", ("a.xml", _mspdi("Alpha"), "text/xml"))],
        headers={"X-SF-Ajax": "1"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["redirect"] == "/analysis/a"  # single clean file → jump to its report
    assert body["accepted"] == 1
    assert len(st.schedules) == 1


def test_skipped_unreadable_files_are_reported_and_readable_ones_still_load(
    sc: tuple[SessionState, TestClient],
) -> None:
    st, client = sc
    skipped = [{"path": "Large Test File/Large_Test_File.mpp", "reason": "NotReadableError"}]
    r = client.post(
        "/upload",
        files=[("files", ("ok.xml", _mspdi("Alpha"), "text/xml"))],
        data={
            "file_meta": json.dumps([{"rel": "Large Test File/ok.xml", "mtime": 1}]),
            "skipped_files": json.dumps(skipped),
        },
        headers={"X-SF-Ajax": "1"},
    )
    body = r.json()
    assert body["skipped_unreadable"] == 1
    assert body["redirect"] == "/"  # a skipped file forces the dashboard so the manifest is seen
    assert len(st.schedules) == 1  # the readable file still loaded
    # the dashboard flash names the unreadable file and the self-service fix
    page = client.get("/").text
    assert "Could not read 1 file" in page
    assert "Large_Test_File.mpp" in page
    assert "Always keep on this device" in page


def test_non_ajax_upload_still_redirects_303(sc: tuple[SessionState, TestClient]) -> None:
    # backward compatibility: a plain form POST (no JS / no header) still gets the 303 redirect
    _st, client = sc
    r = client.post(
        "/upload",
        files=[("files", ("a.xml", _mspdi("Alpha"), "text/xml"))],
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/analysis/a"
