"""Multiple folders in ONE selection become SEPARATE Projects (operator 2026-08-21).

The server side of the ask was already true — ``_parse_upload_meta`` derives the top folder PER
FILE and ``group_into_projects`` buckets per distinct folder name — but nothing pinned it, and the
client had no way to deliver a multi-folder selection: Chromium's directory-picker dialog cannot
multi-select (``webkitdirectory`` overrides ``multiple`` — WICG entries-api #24), and the drop
handler never traversed a dropped directory at all. This module pins the server contract and the
dashboard copy; ``test_multi_folder_drop_browser.py`` proves the drop traversal RENDERED.

Teeth (prove-able-to-fail): the grouping pin was mutation-tested before landing — rewriting the
third rel into ``FolderA/`` (one folder, not two) fails it by name on the exact ``{'FolderA'}``
population assert.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

_NS = 'xmlns="http://schemas.microsoft.com/project"'
_TASK = "<Tasks><Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration></Task></Tasks>"


def _mspdi(title: str | None, status: str | None = None) -> bytes:
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


def test_two_folders_in_one_upload_become_two_projects(
    sc: tuple[SessionState, TestClient],
) -> None:
    """ONE POST whose ``file_meta`` rels span two top folders lands as two folder Projects,
    each holding exactly its own folder's files (nested sub-folders included)."""
    st, client = sc
    rels = ["FolderA/a1.xml", "FolderA/sub/a2.xml", "FolderB/b1.xml"]
    files = [
        (
            "files",
            (r.rsplit("/", 1)[-1], _mspdi("ignored", f"2025-0{i + 1}-10T00:00:00"), "text/xml"),
        )
        for i, r in enumerate(rels)
    ]
    meta = json.dumps([{"rel": r, "mtime": 1000 + i} for i, r in enumerate(rels)])
    assert client.post("/upload", files=files, data={"file_meta": meta}).status_code == 200
    projects = {p.title: p for p in st.projects()}
    assert set(projects) == {"FolderA", "FolderB"}
    assert projects["FolderA"].origin == "folder"
    assert projects["FolderB"].origin == "folder"
    assert len(projects["FolderA"].versions) == 2
    assert len(projects["FolderB"].versions) == 1
    # and the ADR-0258 analysis populations split the same way (no silent pooling)
    assert len(st.populations()) == 2


def test_a_loose_file_beside_folders_stays_loose(sc: tuple[SessionState, TestClient]) -> None:
    """A file picked/dropped WITHOUT a folder (empty rel) in the same batch keeps loose
    semantics — grouped by its own document Title, never absorbed into a dropped folder."""
    st, client = sc
    files = [
        ("files", ("a1.xml", _mspdi("ignored", "2025-01-10T00:00:00"), "text/xml")),
        ("files", ("solo.xml", _mspdi("Loosey", "2025-02-10T00:00:00"), "text/xml")),
    ]
    meta = json.dumps([{"rel": "FolderA/a1.xml", "mtime": 1}, {"rel": "", "mtime": 2}])
    client.post("/upload", files=files, data={"file_meta": meta})
    projects = {p.title: p for p in st.projects()}
    assert set(projects) == {"FolderA", "Loosey"}
    assert projects["Loosey"].origin == "title"


def test_dashboard_copy_offers_several_folders_each_its_own_project(
    sc: tuple[SessionState, TestClient],
) -> None:
    """The dropzone tells the operator the multi-folder contract: several folders at once,
    EACH folder its own Project (the old copy promised only 'a folder is one Project')."""
    _st, client = sc
    home = client.get("/").text
    assert "id=pickFolderBtn" in home  # the picker button keeps its id (home.js binds it)
    assert "each folder is its own Project" in home
    assert "drop several folders at once" in home
