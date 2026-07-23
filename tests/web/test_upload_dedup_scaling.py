"""The /upload byte-identical dedup must scale O(M), not O(M^2) (Fix D), with the folder-context
rules preserved byte-for-byte.

On ``main`` the dedup rescans the whole ``content_hashes`` map for every file — M(M-1)/2 scanned
pairs (120 for 16 files, 496 for 32). Fix D builds a reverse index once per batch, so the scan is
linear. These are op-count pins (ADR-0249): committed FIRST, the linear assertion FAILS on ``main``.
"""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Iterator

from fastapi.testclient import TestClient

from schedule_forensics.importers.json_schedule import to_json_text
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import SessionState, create_app

_DAY = 480


class _CountingHashes(dict):
    """A ``content_hashes`` stand-in that counts every (key, hash) pair examined via ``items()`` —
    exactly the work the dedup scan does (the quadratic loop on ``main``; the one-time index build
    after Fix D)."""

    def __init__(self, *a: object, **k: object) -> None:
        super().__init__(*a, **k)
        self.scanned = 0

    def items(self) -> Iterator[tuple[str, str]]:  # type: ignore[override]
        for pair in super().items():
            self.scanned += 1
            yield pair


def _tiny(name: str, uid: int) -> tuple[str, bytes, str]:
    """A distinct, parseable JSON schedule (distinct bytes => distinct content hash)."""
    sch = Schedule(
        name=name,
        source_file=f"{name}.json",
        project_start=dt.datetime(2026, 1, 5, 8, 0),
        tasks=(Task(unique_id=uid, name=f"t{uid}", duration_minutes=_DAY),),
    )
    return (f"{name}.json", to_json_text(sch).encode(), "application/json")


def _post(client: TestClient, files: list[tuple[str, bytes, str]], meta: list[dict] | None = None):  # type: ignore[type-arg]
    data = {"file_meta": json.dumps(meta)} if meta is not None else {}
    return client.post("/upload", files=[("files", f) for f in files], data=data)


def _run_batch(count: int) -> tuple[int, int]:
    st = SessionState()
    st.content_hashes = _CountingHashes()
    client = TestClient(create_app(st))
    files = [_tiny(f"f{i}", uid=i + 1) for i in range(count)]
    st.content_hashes.scanned = 0
    resp = _post(client, files)
    assert resp.status_code == 200
    return st.content_hashes.scanned, len(st.schedules)


def test_upload_dedup_scan_is_linear_not_quadratic() -> None:
    scanned16, loaded16 = _run_batch(16)
    scanned32, loaded32 = _run_batch(32)
    assert loaded16 == 16 and loaded32 == 32  # every distinct file accepted
    # main scans M(M-1)/2 (120, 496); the fix keeps it linear (indexed lookup, no per-file rescan)
    assert scanned16 <= 16, f"16-file upload scanned {scanned16} pairs (quadratic dedup)"
    assert scanned32 <= 32, f"32-file upload scanned {scanned32} pairs (quadratic dedup)"


def test_byte_identical_reupload_same_folder_dedups() -> None:
    st = SessionState()
    client = TestClient(create_app(st))
    f = _tiny("dup", uid=1)
    meta = [{"rel": "FolderX/dup.json", "mtime": 1000}]
    _post(client, [f], meta)
    _post(client, [f], meta)  # same bytes AND same folder context -> the same version twice
    assert len(st.schedules) == 1


def test_identical_bytes_in_a_different_folder_still_load() -> None:
    st = SessionState()
    client = TestClient(create_app(st))
    f = _tiny("dup", uid=1)
    _post(client, [f], [{"rel": "FolderX/dup.json", "mtime": 1000}])
    _post(client, [f], [{"rel": "FolderY/dup.json", "mtime": 1000}])  # same bytes, other project
    assert len(st.schedules) == 2
