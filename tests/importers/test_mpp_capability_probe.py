"""The native-.mpp capability is probed ONCE per ingest, ahead of the I/O (ADR-0293).

"Can this machine convert a native ``.mpp``?" is a property of the machine, not of the file, so
the answer is identical for every file in an ingest. It used to be re-derived per file — and, in
the web upload path, only *after* the file's bytes had already been spilled to a temp path. On a
machine with no JRE that meant a folder of ``.mpp`` wrote and immediately discarded every megabyte
before failing on each one.

These are op-count / equality pins (ADR-0249 doctrine — never wall-clock; discovery costs
microseconds, and the win is the work it *skips*, not its own speed):

* an N-file ``.mpp`` ingest runs JRE/runner discovery **once**, not N times;
* an upload that cannot possibly convert writes **zero** temp bytes;
* the two failure messages, and the order they are reported in, are **unchanged**;
* the probe is scoped to the batch session, so a machine that gains a JRE between two uploads is
  re-probed rather than answered from a stale process-wide memo;
* a successful parse is byte-identical to the pre-probe path (Law 2).
"""

from __future__ import annotations

import shutil
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.importers import ImporterError, mpp_mpxj, parse_mpp
from schedule_forensics.web.app import SessionState, create_app

REPO = Path(__file__).resolve().parents[2]
MPP_DIR = REPO / "00_REFERENCE_INTAKE" / "mpp"
PROJECT2 = MPP_DIR / "Project2.mpp"

needs_java = pytest.mark.skipif(
    shutil.which("java") is None, reason="Java runtime not available in this environment"
)
needs_sample = pytest.mark.skipif(
    not PROJECT2.is_file(), reason="Project2.mpp not present (reference intake)"
)

_MINIMAL_MSPDI = (
    '<Project xmlns="http://schemas.microsoft.com/project">'
    "<StartDate>2025-01-06T08:00:00</StartDate>"
    "<Tasks><Task><UID>1</UID><Name>Solo</Name><Duration>PT8H0M0S</Duration></Task></Tasks>"
    "</Project>"
)


class _Spy:
    """Counts calls to a module-level helper without changing what it returns."""

    def __init__(self, real: object) -> None:
        self._real = real
        self.n = 0

    def __call__(self, *a: object, **k: object) -> object:
        self.n += 1
        return self._real(*a, **k)  # type: ignore[operator]


def _fake_converter(monkeypatch: pytest.MonkeyPatch) -> None:
    """A JVM-free ``.mpp`` → MSPDI conversion: pretend java is on PATH, write the output slot."""
    monkeypatch.setenv("SF_MPXJ_NO_SERVER", "1")  # the one-shot path — the per-file re-derivation
    monkeypatch.setattr(mpp_mpxj, "_find_java", lambda: "/usr/bin/java")

    def _run(cmd: list[str], *_a: object, **_k: object) -> object:
        Path(cmd[5]).write_text(_MINIMAL_MSPDI, encoding="utf-8")
        return types.SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(mpp_mpxj.subprocess, "run", _run)


def test_an_n_file_ingest_probes_the_capability_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The pin: discovery is O(1) in the ingest, not O(files). Pre-fix this was 8 and 9."""
    _fake_converter(monkeypatch)
    find, home = _Spy(mpp_mpxj._find_java), _Spy(mpp_mpxj._mpxj_home)
    monkeypatch.setattr(mpp_mpxj, "_find_java", find)
    monkeypatch.setattr(mpp_mpxj, "_mpxj_home", home)

    samples = []
    for i in range(8):
        p = tmp_path / f"v{i}.mpp"
        p.write_bytes(b"dummy")
        samples.append(p)
    with mpp_mpxj.mpxj_batch_session():
        for p in samples:
            assert parse_mpp(p).task_by_id(1).name == "Solo"

    assert (find.n, home.n) == (1, 1), "the JRE/runner lookup must be probed once per ingest"


def test_an_upload_that_cannot_convert_writes_no_temp_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The measured waste: 16 x 691,712 B spilled to disk, then discarded, before failing.

    Counted at ``Path.write_bytes`` because that is literally the wasted work — the upload path
    materialised each file so the MPXJ subprocess could read it, on a machine where no subprocess
    was ever going to run.
    """
    data = b"\xd0\xcf\x11\xe0" + b"x" * 200_000  # OLE magic + filler; never actually parsed
    monkeypatch.setattr(mpp_mpxj, "_find_java", lambda: None)  # no JRE anywhere

    written = {"calls": 0, "bytes": 0}
    real_write = Path.write_bytes

    def counting(self: Path, payload: bytes) -> int:
        written["calls"] += 1
        written["bytes"] += len(payload)
        return real_write(self, payload)

    monkeypatch.setattr(Path, "write_bytes", counting)

    client = TestClient(create_app(SessionState()))
    files = [("files", (f"v{i}.mpp", data, "application/octet-stream")) for i in range(16)]
    response = client.post("/upload", files=files)

    assert response.status_code == 200
    assert written == {"calls": 0, "bytes": 0}, (
        f"{written['bytes']:,} B written for an ingest that could never convert"
    )


def test_the_reasons_are_the_ones_the_conversion_path_has_always_raised(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Law 2 applies to the operator-facing text too: the probe reports, it does not reword."""
    sample = tmp_path / "x.mpp"
    sample.write_bytes(b"dummy")

    # (a) no JRE — the full install-help message, verbatim
    monkeypatch.setattr(mpp_mpxj, "_find_java", lambda: None)
    cap = mpp_mpxj.probe_mpp_capability()
    assert not cap.available and cap.java is None
    assert cap.reason == mpp_mpxj._NO_JAVA_REASON
    assert "winget" in cap.reason and "JAVA_HOME" in cap.reason
    with pytest.raises(ImporterError) as exc:
        parse_mpp(sample)
    assert str(exc.value) == cap.reason

    # (b) a missing runner OUTRANKS a missing JRE — a broken deployment must name itself, not
    #     blame a JRE the conversion never got far enough to need
    monkeypatch.setenv("SF_MPXJ_HOME", str(tmp_path))  # no classes/ under here
    runner_cap = mpp_mpxj.probe_mpp_capability()
    assert not runner_cap.available
    assert runner_cap.reason.startswith("MPXJ runner not found under ")
    assert "setup.sh" in runner_cap.reason
    with pytest.raises(ImporterError, match="MPXJ runner not found"):
        parse_mpp(sample)


def test_an_available_capability_carries_the_resolved_java_and_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The probe is not just a boolean — the conversion argv is built from what it resolved, so a
    second lookup can never disagree with the one that decided the ingest was possible."""
    monkeypatch.setattr(mpp_mpxj, "_find_java", lambda: "/usr/bin/java")
    cap = mpp_mpxj.probe_mpp_capability()
    assert cap.available and cap.reason == "" and cap.java == "/usr/bin/java"
    argv = mpp_mpxj._build_command(cap, Path("in.mpp"), Path("out.xml"))
    assert argv[0] == "/usr/bin/java"
    assert argv[3] == "MpxjToMspdi"
    assert argv[-2:] == ["in.mpp", "out.xml"]  # the fake-converter tests index cmd[5]
    assert str(cap.mpxj_home / "classes") in argv[2]


def test_the_probe_is_scoped_to_the_ingest_not_the_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Why a batch-scoped memo is safe where a process-wide one would not be: install a JRE (or
    lose one) between two uploads and the next ingest sees the new answer."""
    sample = tmp_path / "x.mpp"
    sample.write_bytes(b"dummy")
    _fake_converter(monkeypatch)

    monkeypatch.setattr(mpp_mpxj, "_find_java", lambda: None)
    with mpp_mpxj.mpxj_batch_session():
        assert not mpp_mpxj.mpp_capability().available
        with pytest.raises(ImporterError, match="Java runtime not found"):
            parse_mpp(sample)

    monkeypatch.setattr(mpp_mpxj, "_find_java", lambda: "/usr/bin/java")
    with mpp_mpxj.mpxj_batch_session():
        assert mpp_mpxj.mpp_capability().available
        assert parse_mpp(sample).task_by_id(1).name == "Solo"


def test_outside_a_session_every_call_probes_fresh(monkeypatch: pytest.MonkeyPatch) -> None:
    """No ambient global state: a bare ``mpp_capability()`` reflects the machine right now."""
    monkeypatch.setattr(mpp_mpxj, "_find_java", lambda: None)
    assert not mpp_mpxj.mpp_capability().available
    monkeypatch.setattr(mpp_mpxj, "_find_java", lambda: "/usr/bin/java")
    assert mpp_mpxj.mpp_capability().available


@needs_java
@needs_sample
def test_a_real_mpp_parses_identically_through_the_probe(tmp_path: Path) -> None:
    """Law 2: the probe may not change a single field of what a real conversion produces.

    Both the batch (persistent-JVM) and one-shot paths now build their argv from the probe, so the
    two must still agree with each other exactly — the same guarantee ADR-0289 made for ordering.
    """
    copy = tmp_path / "Project2.mpp"
    shutil.copyfile(PROJECT2, copy)
    with mpp_mpxj.mpxj_batch_session():
        batched = parse_mpp(copy)
    one_shot = parse_mpp(copy)
    assert batched == one_shot
    assert batched.name == "Commercial Construction"
    assert set(batched.tasks_by_id) == {0} | set(range(2, 146))
