"""v4 Feature 2: the upload route caches parsed schedules by content hash.

Re-uploading identical bytes (e.g. the same file inside a re-scanned folder) must skip the parse —
which for a native ``.mpp`` is a JVM subprocess — and a session wipe must leave nothing on disk.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

import schedule_forensics.web.app as app_module
from schedule_forensics.engine.cache import content_hash, get_default_cache
from schedule_forensics.web.app import SessionState, create_app

_NS = 'xmlns="http://schemas.microsoft.com/project"'
_TASK = "<Tasks><Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration></Task></Tasks>"


def _mspdi(title: str, status: str) -> bytes:
    return (
        f"<Project {_NS}><StartDate>2025-01-06T08:00:00</StartDate>"
        f"<Title>{title}</Title><StatusDate>{status}</StatusDate>{_TASK}</Project>"
    ).encode()


@pytest.fixture
def sc() -> tuple[SessionState, TestClient]:
    st = SessionState()
    return st, TestClient(create_app(st))


def test_reupload_of_identical_bytes_is_collapsed_loudly(
    sc: tuple[SessionState, TestClient], monkeypatch: pytest.MonkeyPatch
) -> None:
    """ADR-0259 hash-first dedup: identical bytes in the SAME grouping context (both loose here)
    are the same version twice — the duplicate never becomes a second session entry, never
    parses, and the skip is reported in the manifest (nothing silent)."""
    st, client = sc
    calls = {"n": 0}
    real = app_module._parse_upload

    def counting(name: str, data: bytes) -> object:
        calls["n"] += 1
        return real(name, data)

    monkeypatch.setattr(app_module, "_parse_upload", counting)
    payload = _mspdi("Gemini", "2025-01-10T00:00:00")
    client.post("/upload", files=[("files", ("v1.xml", payload, "text/xml"))])
    page = client.post(
        "/upload", files=[("files", ("v2.xml", payload, "text/xml"))]
    ).text  # same bytes

    assert calls["n"] == 1  # the duplicate never reached the parser
    assert set(st.schedules) == {"v1"}  # ...and never became a second version
    assert "byte-identical" in page  # the collapse is loud, not silent


def test_identical_bytes_in_different_folders_stay_separate_and_parse_once(
    sc: tuple[SessionState, TestClient], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Identical bytes in DIFFERENT grouping contexts are legitimately a version of two different
    Projects — both stay loaded (no collapse across contexts), while the content-hash cache still
    means the bytes parse only once (the cache changes speed, never the answer)."""
    st, client = sc
    calls = {"n": 0}
    real = app_module._parse_upload

    def counting(name: str, data: bytes) -> object:
        calls["n"] += 1
        return real(name, data)

    monkeypatch.setattr(app_module, "_parse_upload", counting)
    payload = _mspdi("Gemini", "2025-01-10T00:00:00")
    client.post(
        "/upload",
        files=[("files", ("v1.xml", payload, "text/xml"))],
        data={"file_meta": json.dumps([{"rel": "ProgA/v1.xml", "mtime": 1}])},
    )
    client.post(
        "/upload",
        files=[("files", ("v2.xml", payload, "text/xml"))],
        data={"file_meta": json.dumps([{"rel": "ProgB/v2.xml", "mtime": 2}])},
    )

    assert calls["n"] == 1  # parse served from the content-hash cache
    assert set(st.schedules) == {"v1", "v2"}  # both kept — different Projects
    assert st.schedules["v1"].project_title == st.schedules["v2"].project_title == "Gemini"
    assert {p.title for p in st.projects()} == {"ProgA", "ProgB"}


def test_wipe_clears_the_on_disk_cache(sc: tuple[SessionState, TestClient]) -> None:
    st, client = sc
    payload = _mspdi("Wiped", "2025-01-10T00:00:00")
    client.post("/upload", files=[("files", ("v.xml", payload, "text/xml"))])
    ch = content_hash(payload)
    assert get_default_cache().get_schedule(ch) is not None  # the parse was cached
    client.post("/session/wipe")
    assert get_default_cache().get_schedule(ch) is None  # a wipe leaves no CUI behind
    assert st.schedules == {}


def test_portfolio_reads_the_in_memory_summary_cache(
    sc: tuple[SessionState, TestClient], monkeypatch: pytest.MonkeyPatch
) -> None:
    from schedule_forensics.engine.summary import compute_summary as real

    calls = {"n": 0}

    def counting(sch: object, **kw: object) -> object:
        calls["n"] += 1
        return real(sch, **kw)  # type: ignore[arg-type]

    monkeypatch.setattr(app_module, "compute_summary", counting)
    _st, client = sc
    client.post(
        "/upload",
        files=[("files", ("a.xml", _mspdi("Solo", "2025-01-10T00:00:00"), "text/xml"))],
    )
    assert "Solo" in client.get("/portfolio").text
    after_first = calls["n"]
    assert after_first >= 1  # the first render computed the version summary
    client.get("/portfolio")
    assert calls["n"] == after_first  # the second render came from the in-memory summary cache


def test_portfolio_summary_persists_across_sessions(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = _mspdi("Persist", "2025-01-10T00:00:00")
    st1 = SessionState()
    c1 = TestClient(create_app(st1))
    c1.post("/upload", files=[("files", ("a.xml", payload, "text/xml"))])
    assert "Persist" in c1.get("/portfolio").text  # computes + persists the summary to SQLite

    # a fresh session in the same process shares the on-disk cache: it must read the summary from
    # disk, never recompute — proven by making any recompute explode
    def boom(sch: object) -> object:
        raise AssertionError("the summary must come from the SQLite cache, not a recompute")

    monkeypatch.setattr(app_module, "compute_summary", boom)
    st2 = SessionState()
    c2 = TestClient(create_app(st2))
    c2.post("/upload", files=[("files", ("a.xml", payload, "text/xml"))])
    page = c2.get("/portfolio").text
    assert "Persist" in page and "pass /" in page  # rendered entirely from the cached summary
