"""v4 Feature 2: a folder upload of native .mpp files converts in ONE persistent JVM, not one per
file. End-to-end through the upload route (needs a JVM + the sample .mpp; skips in CI)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import schedule_forensics.importers.mpp_mpxj as mpp_mpxj
from schedule_forensics.web.app import SessionState, create_app

_MPP = Path(__file__).resolve().parents[2] / "00_REFERENCE_INTAKE" / "mpp"
_P2 = _MPP / "Project2.mpp"
_P5 = _MPP / "Project5.mpp"

needs_java_and_samples = pytest.mark.skipif(
    shutil.which("java") is None or not (_P2.is_file() and _P5.is_file()),
    reason="a JVM and the sample .mpp files are required",
)


@needs_java_and_samples
def test_folder_upload_of_mpp_reuses_one_jvm(monkeypatch: pytest.MonkeyPatch) -> None:
    st = SessionState()
    client = TestClient(create_app(st))
    starts = {"n": 0}
    real = mpp_mpxj._try_start_server

    def counting(home: Path) -> object:
        starts["n"] += 1
        return real(home)

    monkeypatch.setattr(mpp_mpxj, "_try_start_server", counting)
    files = [
        ("files", ("Project2.mpp", _P2.read_bytes(), "application/octet-stream")),
        ("files", ("Project5.mpp", _P5.read_bytes(), "application/octet-stream")),
    ]
    client.post("/upload", files=files)
    assert len(st.schedules) == 2  # both native files ingested
    assert starts["n"] == 1  # the whole ingest ran in ONE heap-capped JVM, not one boot per file
