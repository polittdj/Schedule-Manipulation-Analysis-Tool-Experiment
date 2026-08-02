"""v4 Feature 2: the upload route caches parsed schedules by content hash.

Re-uploading identical bytes (e.g. the same file inside a re-scanned folder) must skip the parse —
which for a native ``.mpp`` is a JVM subprocess — and a session wipe must leave nothing on disk.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

import schedule_forensics.web.app as app_module
import schedule_forensics.web.state as state_module
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


def test_a_graceful_stop_takes_the_on_disk_cache_with_it(
    sc: tuple[SessionState, TestClient],
) -> None:
    """ADR-0335: the operator's rule is that nothing of theirs stays on the disk once the tool is
    not running. Every graceful exit funnels through ``_trigger_shutdown`` — the in-page Quit
    control, ``POST /api/shutdown`` (including a launcher standing its predecessor down), and the
    browser-gone watchdog."""
    _st, client = sc
    payload = _mspdi("Quitting", "2025-01-10T00:00:00")
    client.post("/upload", files=[("files", ("v.xml", payload, "text/xml"))])
    ch = content_hash(payload)
    assert get_default_cache().get_schedule(ch) is not None  # the parse was cached

    client.post("/api/shutdown")
    assert get_default_cache().get_schedule(ch) is None  # a quit leaves no CUI on disk


def test_an_import_finishing_after_quit_cannot_re_populate_the_cache(
    sc: tuple[SessionState, TestClient], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The measured hole that ``ScheduleCache.seal()`` closes (ADR-0335).

    uvicorn's graceful shutdown keeps serving until in-flight requests drain, so an import that
    began before the operator hit Quit finishes AFTER the clear and used to write the schedule it
    had just parsed straight back to disk. ADR-0263's ``wipe_gen`` does not cover this: only
    ``/session/wipe`` bumps that generation, never a shutdown. Here the quit lands mid-parse,
    which is exactly the ordering that was reproduced end-to-end against a real server."""
    st, client = sc
    real = app_module._parse_upload

    def quit_midway(name: str, data: bytes) -> object:
        parsed = real(name, data)
        app_module._trigger_shutdown(client.app)  # the operator hits Quit while this import runs
        return parsed

    monkeypatch.setattr(app_module, "_parse_upload", quit_midway)
    payload = _mspdi("InFlight", "2025-01-10T00:00:00")
    client.post("/upload", files=[("files", ("v.xml", payload, "text/xml"))])

    assert st.schedules != {}  # the import itself still completed — the session is unharmed
    assert get_default_cache().get_schedule(content_hash(payload)) is None


def test_the_asgi_lifespan_shutdown_clears_the_cache() -> None:
    """The hook that covers SIGTERM — and the only one that does (ADR-0335).

    Measured with a real server in a subprocess: uvicorn handles SIGTERM gracefully, but
    ``capture_signals`` restores the original handler and re-raises the captured signal, so the
    process dies of the default SIGTERM disposition *before* ``serve()`` returns — the launcher's
    ``finally`` and the ``atexit`` backstop both never run (exit ``-15``, no hooks). SIGINT
    escapes only because ``serve()`` deliberately suppresses ``KeyboardInterrupt``. Without this
    hook, an operator on macOS or Linux who logs out or shuts the machine down — a normal way to
    finish for the day — left the whole parsed-schedule cache on the disk.
    """
    payload = _mspdi("Lifespan", "2025-01-10T00:00:00")
    ch = content_hash(payload)
    with TestClient(create_app(SessionState())) as client:  # `with` is what runs the lifespan
        client.post("/upload", files=[("files", ("v.xml", payload, "text/xml"))])
        assert get_default_cache().get_schedule(ch) is not None
    assert get_default_cache().get_schedule(ch) is None  # torn down → nothing left on disk


def test_portfolio_reads_the_in_memory_summary_cache(
    sc: tuple[SessionState, TestClient], monkeypatch: pytest.MonkeyPatch
) -> None:
    from schedule_forensics.engine.summary import compute_summary as real

    calls = {"n": 0}

    def counting(sch: object, **kw: object) -> object:
        calls["n"] += 1
        return real(sch, **kw)  # type: ignore[arg-type]

    monkeypatch.setattr(state_module, "compute_summary", counting)
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

    monkeypatch.setattr(state_module, "compute_summary", boom)
    st2 = SessionState()
    c2 = TestClient(create_app(st2))
    c2.post("/upload", files=[("files", ("a.xml", payload, "text/xml"))])
    page = c2.get("/portfolio").text
    assert "Persist" in page and "pass /" in page  # rendered entirely from the cached summary
