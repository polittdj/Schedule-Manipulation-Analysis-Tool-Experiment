"""Three recorded residuals closed together (ADR-0268).

1. GET /cei no longer mutates session state — focusing a target is a POST /target now
   (a GET with a side effect was the ADR-0061 residual; the SEC-2 Origin gate also can't
   cover a GET, so the mutation belongs on POST). ``uids`` stays a display-only GET param.
2. /export/{fmt}/mission degrades to a valid workbook with a note below two versions,
   mirroring the on-screen ADR-0262 wall degrade — never a raw 422 the browser downloads
   as a broken document.
3. /export/{fmt}/margin?zero_margin=1 exports the Fig 7-43 zero-margin sufficiency snapshot
   (ADR-0266), the same curve the panel toggle shows.
"""

from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

_NS = 'xmlns="http://schemas.microsoft.com/project"'


def _mspdi(title: str, status: str) -> bytes:
    return (
        f"<Project {_NS}><StartDate>2025-01-06T08:00:00</StartDate>"
        f"<Title>{title}</Title><StatusDate>{status}</StatusDate>"
        "<Tasks><Task><UID>1</UID><Name>Design</Name><Duration>PT8H0M0S</Duration>"
        "<Start>2025-01-06T08:00:00</Start><Finish>2025-01-06T17:00:00</Finish></Task>"
        "<Task><UID>2</UID><Name>Schedule Margin</Name><Duration>PT16H0M0S</Duration>"
        "<Start>2025-01-07T08:00:00</Start><Finish>2025-01-08T17:00:00</Finish>"
        "<PredecessorLink><PredecessorUID>1</PredecessorUID><Type>1</Type></PredecessorLink>"
        "</Task></Tasks></Project>"
    ).encode()


def _sheet_xml(content: bytes) -> str:
    with ZipFile(BytesIO(content)) as z:
        return " ".join(z.read(n).decode("utf-8", "replace") for n in z.namelist())


@pytest.fixture
def sc() -> tuple[SessionState, TestClient]:
    st = SessionState()
    return st, TestClient(create_app(st))


# ── 1. GET /cei is side-effect-free; the target is set via POST ───────────────────────────────────


def test_get_cei_never_sets_the_target(sc) -> None:  # type: ignore[no-untyped-def]
    st, client = sc
    client.post(
        "/upload",
        files=[
            ("files", ("a1.xml", _mspdi("Alpha", "2025-01-10T00:00:00"), "text/xml")),
            ("files", ("a2.xml", _mspdi("Alpha", "2025-02-10T00:00:00"), "text/xml")),
        ],
    )
    # a stray target query (an old bookmark) must NOT mutate the session anymore
    client.get("/cei?target=2")
    assert st.target_uid is None
    # the page carries the POST focus form, not a GET side-effect form
    page = client.get("/cei").text
    assert "method=post action=/target" in page
    assert "action=/cei" in page  # the track form stays GET (display-only uids)


def test_cei_focus_form_sets_the_target_via_post(sc) -> None:  # type: ignore[no-untyped-def]
    st, client = sc
    client.post(
        "/upload",
        files=[
            ("files", ("a1.xml", _mspdi("Alpha", "2025-01-10T00:00:00"), "text/xml")),
            ("files", ("a2.xml", _mspdi("Alpha", "2025-02-10T00:00:00"), "text/xml")),
        ],
    )
    r = client.post(
        "/target",
        data={"uid": "2", "next_url": "/cei"},
        headers={"origin": "http://127.0.0.1"},
        follow_redirects=False,
    )
    assert r.status_code == 303 and r.headers["location"] == "/cei"
    assert st.target_uid == 2


# ── 2. mission export degrades to a valid workbook below two versions ─────────────────────────────


def test_mission_export_degrades_to_a_note_with_one_version(sc) -> None:  # type: ignore[no-untyped-def]
    _st, client = sc
    client.post(
        "/upload", files=[("files", ("a1.xml", _mspdi("Alpha", "2025-01-10T00:00:00"), "text/xml"))]
    )
    r = client.get("/export/xlsx/mission")
    assert r.status_code == 200  # a real workbook, not a 422
    assert r.headers["content-type"].startswith("application/vnd.openxmlformats")
    # the explanatory cell text (the sheet NAME truncates at 28 chars; the note lives in a cell)
    assert "underlying series (quality trend" in _sheet_xml(r.content)


def test_mission_export_is_whole_with_two_versions(sc) -> None:  # type: ignore[no-untyped-def]
    _st, client = sc
    client.post(
        "/upload",
        files=[
            ("files", ("a1.xml", _mspdi("Alpha", "2025-01-10T00:00:00"), "text/xml")),
            ("files", ("a2.xml", _mspdi("Alpha", "2025-02-10T00:00:00"), "text/xml")),
        ],
    )
    r = client.get("/export/xlsx/mission")
    assert r.status_code == 200
    assert "Needs at least two" not in _sheet_xml(r.content)


# ── 3. margin export can carry the zero-margin snapshot ───────────────────────────────────────────


def test_margin_export_zero_margin_snapshot(sc) -> None:  # type: ignore[no-untyped-def]
    st, client = sc
    client.post(
        "/upload", files=[("files", ("m1.xml", _mspdi("Alpha", "2025-01-10T00:00:00"), "text/xml"))]
    )
    st.sra_bcwc[2] = (3 * 480, 8 * 480)
    default_xml = _sheet_xml(client.get("/export/xlsx/margin").content)
    zero_xml = _sheet_xml(client.get("/export/xlsx/margin?zero_margin=1").content)
    assert "in-network margin at plan durations" in default_xml
    assert "Zero Margin" in zero_xml  # the Fig 7-43 basis label rides the exported snapshot
    assert "in-network margin at plan durations" not in zero_xml
