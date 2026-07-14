"""v4 grouped ingestion (Feature 1): uploaded files/folders group into Projects.

Loose files group by their real document Title; a folder (any nesting depth) is one Project named
by its top folder with every schedule beneath it a version; there is no file-count cap; non-schedule
files inside a folder are skipped; a title-less loose file is flagged needs-attention.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

_NS = 'xmlns="http://schemas.microsoft.com/project"'
_TASK = "<Tasks><Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration></Task></Tasks>"


def _mspdi(title: str | None, status: str | None = None) -> bytes:
    """A minimal valid MSPDI document with an optional project <Title> and <StatusDate>."""
    title_el = f"<Title>{title}</Title>" if title is not None else ""
    status_el = f"<StatusDate>{status}</StatusDate>" if status else ""
    return (
        f"<Project {_NS}><StartDate>2025-01-06T08:00:00</StartDate>"
        f"{title_el}{status_el}{_TASK}</Project>"
    ).encode()


@pytest.fixture
def sc() -> tuple[SessionState, TestClient]:
    st = SessionState()
    return st, TestClient(create_app(st))


def test_loose_files_group_by_document_title(sc: tuple[SessionState, TestClient]) -> None:
    st, client = sc
    files = [
        ("files", ("a.xml", _mspdi("Alpha", "2025-01-10T00:00:00"), "text/xml")),
        ("files", ("b.xml", _mspdi("Alpha", "2025-02-10T00:00:00"), "text/xml")),
        ("files", ("c.xml", _mspdi("Beta", "2025-01-10T00:00:00"), "text/xml")),
    ]
    client.post("/upload", files=files)
    projects = {p.title: p for p in st.projects()}
    assert set(projects) == {"Alpha", "Beta"}
    assert projects["Alpha"].origin == "title"
    # two versions of Alpha, oldest data-date first
    assert [v.key for v in projects["Alpha"].versions] == ["a", "b"]
    assert len(projects["Beta"].versions) == 1


def test_folder_is_one_project_named_by_the_top_folder(sc: tuple[SessionState, TestClient]) -> None:
    st, client = sc
    # a nested folder (years/months) — every schedule inside is one version of ONE project
    rels = ["Apollo/2023/Jan/v1.xml", "Apollo/2023/Feb/v2.xml", "Apollo/2024/v3.xml"]
    files = [
        (
            "files",
            (r.rsplit("/", 1)[-1], _mspdi("ignored", f"2025-0{i + 1}-10T00:00:00"), "text/xml"),
        )
        for i, r in enumerate(rels)
    ]
    meta = json.dumps([{"rel": r, "mtime": 1000 + i} for i, r in enumerate(rels)])
    client.post("/upload", files=files, data={"file_meta": meta})
    projects = st.projects()
    assert len(projects) == 1
    assert projects[0].title == "Apollo"  # the TOP folder, not the 2023/Feb sub-folders
    assert projects[0].origin == "folder"
    assert len(projects[0].versions) == 3


def test_no_file_count_cap(sc: tuple[SessionState, TestClient]) -> None:
    st, client = sc
    files = [
        ("files", (f"v{i}.xml", _mspdi("Big", f"2025-01-{i + 1:02d}T00:00:00"), "text/xml"))
        for i in range(120)  # comfortably past the old 100-file cap
    ]
    page = client.post("/upload", files=files).text
    assert "batch cap" not in page
    assert len(st.schedules) == 120
    assert len(st.projects()) == 1  # all one Project "Big"


def test_non_schedule_files_in_a_folder_are_skipped(sc: tuple[SessionState, TestClient]) -> None:
    st, client = sc
    files = [
        ("files", ("notes.txt", b"not a schedule", "text/plain")),
        ("files", ("s.xml", _mspdi("Proj"), "text/xml")),
    ]
    meta = json.dumps([{"rel": "Proj/notes.txt", "mtime": 1}, {"rel": "Proj/s.xml", "mtime": 2}])
    page = client.post("/upload", files=files, data={"file_meta": meta}).text
    assert "Skipped 1 non-schedule file" in page
    assert len(st.schedules) == 1  # only the schedule was kept


def test_titleless_loose_file_is_needs_attention(sc: tuple[SessionState, TestClient]) -> None:
    st, client = sc
    client.post("/upload", files=[("files", ("mystery.xml", _mspdi(None), "text/xml"))])
    projects = st.projects()
    assert len(projects) == 1
    assert projects[0].needs_attention is True
    assert projects[0].origin == "filename"


def test_portfolio_view_rolls_up_one_row_per_project(sc: tuple[SessionState, TestClient]) -> None:
    _st, client = sc
    # empty state first
    assert "portfolio rollup" in client.get("/portfolio").text
    files = [
        ("files", ("a.xml", _mspdi("Alpha", "2025-01-10T00:00:00"), "text/xml")),
        ("files", ("b.xml", _mspdi("Alpha", "2025-02-10T00:00:00"), "text/xml")),
        ("files", ("c.xml", _mspdi("Beta", "2025-01-10T00:00:00"), "text/xml")),
    ]
    client.post("/upload", files=files)
    page = client.get("/portfolio").text
    assert "Portfolio" in page
    # both projects appear, with a version count and a DCMA rollup + drill links
    assert "Alpha" in page and "Beta" in page
    assert "pass /" in page and "fail" in page  # DCMA-14 rollup rendered
    assert "/analysis/a" in page and "/analysis/b" in page  # version drill links
    # Portfolio is in the nav spine
    assert 'href="/portfolio"' in page


def test_folder_with_disagreeing_titles_uses_folder_name_with_a_notice(
    sc: tuple[SessionState, TestClient],
) -> None:
    st, client = sc
    files = [
        ("files", ("a.xml", _mspdi("One", "2025-01-10T00:00:00"), "text/xml")),
        ("files", ("b.xml", _mspdi("Two", "2025-02-10T00:00:00"), "text/xml")),
    ]
    meta = json.dumps([{"rel": "Mission/a.xml", "mtime": 1}, {"rel": "Mission/b.xml", "mtime": 2}])
    page = client.post("/upload", files=files, data={"file_meta": meta}).text
    projects = st.projects()
    assert len(projects) == 1 and projects[0].title == "Mission"
    assert "different document titles" in page  # non-blocking manifest notice
