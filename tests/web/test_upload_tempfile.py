"""Native .mpp upload temp-file handling (W1) — the file must be written *and closed* before
the MPXJ java subprocess reads it. On Windows an open NamedTemporaryFile handle blocks the
subprocess, so every native .mpp upload failed there (the operator's OS)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import schedule_forensics.web.app as app_module
from schedule_forensics.web.app import _parse_upload


def _handles_to(target: Path) -> list[Path]:
    """Open file descriptors in this process that resolve to ``target`` (Linux honest check)."""
    fd_dir = Path("/proc/self/fd")
    if not fd_dir.is_dir():
        return []
    held: list[Path] = []
    for fd in fd_dir.iterdir():
        try:
            if fd.resolve() == target.resolve():
                held.append(fd)
        except OSError:
            continue
    return held


def test_mpp_upload_writes_a_closed_readable_temp_file(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}
    sentinel = object()

    def fake_load(path: Path) -> Any:
        p = Path(path)
        seen["path"] = p
        seen["content"] = p.read_bytes()  # written and readable before parsing
        seen["held"] = _handles_to(p)  # no open handle still pins the file
        return sentinel

    monkeypatch.setattr(app_module, "load_schedule", fake_load)
    result = _parse_upload("plan.mpp", b"PK\x03\x04 fake mpp bytes")

    assert result is sentinel
    assert seen["content"] == b"PK\x03\x04 fake mpp bytes"
    assert seen["held"] == []  # the held-open-handle Windows bug would show here
    assert not seen["path"].exists()  # TemporaryDirectory is cleaned up after the with-block
