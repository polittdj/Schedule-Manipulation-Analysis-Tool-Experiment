"""MPXJ native-.mpp wrapper tests.

Real-.mpp conversions run only where the (gitignored, non-CUI) sample files and a
JVM are present — they skip in CI. The wrapper's orchestration and every error path
are covered without a JVM by faking the subprocess, so CI exercises the logic.
"""

from __future__ import annotations

import shutil
import types
from pathlib import Path

import pytest

from schedule_forensics.importers import ImporterError, mpp_mpxj, parse_mpp

REPO = Path(__file__).resolve().parents[2]
MPP_DIR = REPO / "00_REFERENCE_INTAKE" / "mpp"
PROJECT2 = MPP_DIR / "Project2.mpp"
PROJECT5 = MPP_DIR / "Project5.mpp"

needs_real_mpp = pytest.mark.skipif(
    not PROJECT2.is_file() or shutil.which("java") is None,
    reason="real .mpp / Java runtime not available in this environment",
)

_MINIMAL_MSPDI = (
    '<Project xmlns="http://schemas.microsoft.com/project">'
    "<StartDate>2025-01-06T08:00:00</StartDate>"
    "<Tasks><Task><UID>1</UID><Name>Solo</Name><Duration>PT8H0M0S</Duration></Task></Tasks>"
    "</Project>"
)


def _fake_java(_name: str) -> str:
    return "/usr/bin/java"  # pretend a JVM is on PATH (subprocess is also faked)


def _writer_run(mspdi_text: str):
    """A fake ``subprocess.run`` that writes ``mspdi_text`` to the output argv slot."""

    def _run(cmd, *_args, **_kwargs):
        Path(cmd[5]).write_text(mspdi_text, encoding="utf-8")
        return types.SimpleNamespace(returncode=0, stderr="")

    return _run


# --- real-file integration (skipped without the sample .mpp + a JVM) --------------


@needs_real_mpp
@pytest.mark.parametrize(("path", "name"), [(PROJECT2, "Project2.mpp"), (PROJECT5, "Project5.mpp")])
def test_parse_real_mpp(path: Path, name: str) -> None:
    s = parse_mpp(path)
    assert s.source_file == name
    assert s.name == "Commercial Construction"
    # 145 rows = the UID-0 project summary + 144 activities (UID 2..145); UID 1 absent.
    assert set(s.tasks_by_id) == {0} | set(range(2, 146))
    activities = [t for t in s.tasks if t.unique_id != 0]
    assert len(activities) == 144


# --- error paths (no JVM needed) --------------------------------------------------


def test_nonexistent_file_raises() -> None:
    with pytest.raises(ImporterError, match=r"cannot read \.mpp"):
        parse_mpp("/no/such/file.mpp")


def test_missing_mpxj_runner_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sample = tmp_path / "x.mpp"
    sample.write_bytes(b"dummy")
    monkeypatch.setenv("SF_MPXJ_HOME", str(tmp_path))  # no classes/ here
    with pytest.raises(ImporterError, match="MPXJ runner not found"):
        parse_mpp(sample)


def test_java_not_found_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sample = tmp_path / "x.mpp"
    sample.write_bytes(b"dummy")
    monkeypatch.setattr(mpp_mpxj.shutil, "which", lambda _name: None)
    with pytest.raises(ImporterError, match="Java runtime not found"):
        parse_mpp(sample)


def test_conversion_failure_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sample = tmp_path / "x.mpp"
    sample.write_bytes(b"dummy")
    monkeypatch.setattr(mpp_mpxj.shutil, "which", _fake_java)

    def _run(cmd, *_a, **_k):
        return types.SimpleNamespace(returncode=2, stderr="MPXJ could not recognize the file")

    monkeypatch.setattr(mpp_mpxj.subprocess, "run", _run)
    with pytest.raises(ImporterError, match="exit 2"):
        parse_mpp(sample)


def test_no_output_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sample = tmp_path / "x.mpp"
    sample.write_bytes(b"dummy")
    monkeypatch.setattr(mpp_mpxj.shutil, "which", _fake_java)
    monkeypatch.setattr(
        mpp_mpxj.subprocess,
        "run",
        lambda *_a, **_k: types.SimpleNamespace(returncode=0, stderr=""),
    )
    with pytest.raises(ImporterError, match="produced no output"):
        parse_mpp(sample)


def test_runner_fails_to_start_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sample = tmp_path / "x.mpp"
    sample.write_bytes(b"dummy")
    monkeypatch.setattr(mpp_mpxj.shutil, "which", _fake_java)

    def _boom(*_a, **_k):
        raise OSError("cannot exec")

    monkeypatch.setattr(mpp_mpxj.subprocess, "run", _boom)
    with pytest.raises(ImporterError, match="failed to start"):
        parse_mpp(sample)


def test_happy_path_orchestration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Fakes a JVM + MPXJ run that writes MSPDI; proves convert->parse->rename wiring
    # (the default repo MPXJ runner is present, so the runner-found check passes).
    sample = tmp_path / "sample.mpp"
    sample.write_bytes(b"dummy")
    monkeypatch.setattr(mpp_mpxj.shutil, "which", _fake_java)
    monkeypatch.setattr(mpp_mpxj.subprocess, "run", _writer_run(_MINIMAL_MSPDI))
    s = parse_mpp(sample)
    assert s.source_file == "sample.mpp"  # original name, not the temp MSPDI
    assert s.task_by_id(1).name == "Solo"


def test_mpxj_home_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SF_MPXJ_HOME", "/custom/mpxj/home")
    assert mpp_mpxj._mpxj_home() == Path("/custom/mpxj/home")
    monkeypatch.delenv("SF_MPXJ_HOME", raising=False)
    # Default points at the repo's vendored runner.
    assert mpp_mpxj._mpxj_home().name == "mpxj"
