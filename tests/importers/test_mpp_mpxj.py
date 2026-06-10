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


def _no_java_anywhere(monkeypatch: pytest.MonkeyPatch) -> None:
    """Blind every Java-discovery channel (the test host may genuinely have a JDK)."""
    monkeypatch.delenv("SF_JAVA", raising=False)
    monkeypatch.delenv("JAVA_HOME", raising=False)
    monkeypatch.setattr(mpp_mpxj.shutil, "which", lambda _name: None)
    monkeypatch.setattr(mpp_mpxj, "_WINDOWS_JAVA_ROOTS", ())
    monkeypatch.setattr(mpp_mpxj, "_POSIX_JAVA_GLOBS", ())


def test_java_not_found_raises_with_install_help(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sample = tmp_path / "x.mpp"
    sample.write_bytes(b"dummy")
    _no_java_anywhere(monkeypatch)
    with pytest.raises(ImporterError, match="Java runtime not found") as exc:
        parse_mpp(sample)
    # the message tells the user exactly how to fix it
    assert "winget" in str(exc.value) and "JAVA_HOME" in str(exc.value)


def test_find_java_prefers_sf_java_then_java_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _no_java_anywhere(monkeypatch)
    jdk_bin = tmp_path / "jdk" / "bin"
    jdk_bin.mkdir(parents=True)
    java_home_java = jdk_bin / "java"
    java_home_java.write_text("")
    monkeypatch.setenv("JAVA_HOME", str(tmp_path / "jdk"))
    assert mpp_mpxj._find_java() == str(java_home_java)
    # an explicit SF_JAVA outranks JAVA_HOME
    pinned = tmp_path / "pinned-java"
    pinned.write_text("")
    monkeypatch.setenv("SF_JAVA", str(pinned))
    assert mpp_mpxj._find_java() == str(pinned)


def test_find_java_scans_windows_roots_and_picks_newest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Windows installers often do NOT update PATH; the importer must still find the JVM.
    _no_java_anywhere(monkeypatch)
    for version in ("jdk-9.0.4", "jdk-21.0.4+7", "jdk-17.0.2"):
        exe = tmp_path / version / "bin" / "java.exe"
        exe.parent.mkdir(parents=True)
        exe.write_text("")
    monkeypatch.setattr(mpp_mpxj, "_WINDOWS_JAVA_ROOTS", (tmp_path,))
    found = mpp_mpxj._find_java()
    # numeric version ordering: 21 beats 17 beats 9 (lexicographic would pick jdk-9)
    assert found is not None and "jdk-21.0.4+7" in found


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
