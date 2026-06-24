"""Coverage for the local Ollama process launcher — discovery, socket probe, spawn/terminate, and
the OllamaLauncher lifecycle, with injected finder/prober/spawn (no real Ollama, no network)."""

from __future__ import annotations

import socket
import subprocess
import sys
import time

import pytest

from schedule_forensics.ai import ollama_process as op


def test_candidate_paths_includes_windows_locations(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", r"C:\\Users\\me\\AppData\\Local")
    monkeypatch.setenv("ProgramFiles", r"C:\\Program Files")
    monkeypatch.setenv("ProgramFiles(x86)", r"C:\\Program Files (x86)")
    paths = op._candidate_paths()
    assert sum("ollama.exe" in p for p in paths) >= 2  # the LOCALAPPDATA + ProgramFiles entries
    assert "/usr/local/bin/ollama" in paths


def test_find_ollama_on_path_then_candidate_then_none(monkeypatch: pytest.MonkeyPatch) -> None:
    assert op.find_ollama_executable(which=lambda n: "/usr/bin/ollama") == "/usr/bin/ollama"
    monkeypatch.setattr(op.os.path, "isfile", lambda p: p == "/usr/local/bin/ollama")
    assert op.find_ollama_executable(which=lambda n: None) == "/usr/local/bin/ollama"
    monkeypatch.setattr(op.os.path, "isfile", lambda p: False)
    assert op.find_ollama_executable(which=lambda n: None) is None


def test_endpoint_up_true_and_false() -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]
    try:
        assert op.endpoint_up(f"http://127.0.0.1:{port}") is True
    finally:
        srv.close()
    assert op.endpoint_up(f"http://127.0.0.1:{port}", timeout=0.2) is False


def test_default_spawn_runs_popen_non_windows() -> None:
    proc = op._default_spawn("/bin/true", "127.0.0.1:11434")
    try:
        proc.wait(timeout=5)
        assert proc.returncode is not None
    finally:
        if proc.poll() is None:
            proc.kill()


def test_terminate_already_exited() -> None:
    proc = subprocess.Popen(["/bin/true"])
    proc.wait()
    op._terminate(proc)  # poll() is not None -> early return, no signal sent
    assert proc.returncode == 0


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signal handling")
def test_terminate_times_out_then_kills() -> None:
    # a child that ignores SIGTERM -> terminate() won't stop it -> wait() times out -> kill()
    proc = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(30)",
        ]
    )
    time.sleep(0.6)  # let the child install its SIGTERM-ignore handler before we terminate
    op._terminate(proc, timeout=0.3)
    assert proc.wait(timeout=5) is not None  # killed


# --- OllamaLauncher lifecycle --------------------------------------------------------------------


def test_launcher_already_running() -> None:
    assert op.OllamaLauncher(prober=lambda e: True).ensure_running() == "already-running"


def test_launcher_no_binary() -> None:
    launcher = op.OllamaLauncher(prober=lambda e: False, finder=lambda: None)
    assert launcher.ensure_running() == "no-binary"


def test_launcher_spawn_failure_is_caught() -> None:
    def boom(exe: str, hp: str) -> subprocess.Popen[bytes]:
        raise OSError("spawn refused")

    launcher = op.OllamaLauncher(prober=lambda e: False, finder=lambda: "/x/ollama", spawn=boom)
    assert launcher.ensure_running() == "failed"


def test_launcher_started_then_shutdown() -> None:
    calls = {"n": 0}

    def prober(_e: str) -> bool:
        calls["n"] += 1
        return calls["n"] > 1  # not listening at first, listening after we "spawn"

    proc = subprocess.Popen(["/bin/true"])
    launcher = op.OllamaLauncher(
        prober=prober,
        finder=lambda: "/x/ollama",
        spawn=lambda exe, hp: proc,
        unloader=lambda e: 0,  # hermetic — no real /api/ps call on shutdown
        stopper=lambda: None,  # hermetic — no real taskkill/pkill on shutdown
    )
    assert launcher.ensure_running() == "started"
    launcher.shutdown()  # engaged + _proc set -> unload (no-op), _terminate, then stop-server


def test_launcher_starting_when_never_listens(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(op.time, "sleep", lambda s: None)  # don't actually wait
    proc = subprocess.Popen(["/bin/true"])
    try:
        launcher = op.OllamaLauncher(
            prober=lambda e: False,
            finder=lambda: "/x/ollama",
            spawn=lambda exe, hp: proc,
            start_timeout=0.2,
        )
        assert launcher.ensure_running() == "starting"
    finally:
        if proc.poll() is None:
            proc.kill()


def test_launcher_shutdown_without_engaging_is_a_no_op() -> None:
    op.OllamaLauncher(prober=lambda e: True).shutdown()  # never engaged -> no-op (nothing touched)


def test_launcher_shutdown_swallows_terminate_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    proc = subprocess.Popen(["/bin/true"])
    proc.wait()
    launcher = op.OllamaLauncher(unloader=lambda e: 0, stopper=lambda: None)
    launcher._engaged = True  # the tool managed Ollama this session, so shutdown proceeds
    launcher._proc = proc

    def boom(p: object, **k: object) -> None:
        raise RuntimeError("cleanup blew up")

    monkeypatch.setattr(op, "_terminate", boom)
    launcher.shutdown()  # exception is logged, not raised


def test_default_stop_server_runs_the_platform_kill(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(op.subprocess, "run", lambda cmd, **k: calls.append(cmd))
    op._default_stop_server()
    assert calls  # at least one OS kill was issued
    if sys.platform == "win32":  # pragma: no cover - Windows-only branch
        # the tray supervisor (ollama app.exe) AND the server (ollama.exe) are both killed — killing
        # only the server lets the tray respawn it (the operator saw ollama.exe survive Quit)
        images = {c[-1] for c in calls}
        assert "ollama app.exe" in images and "ollama.exe" in images
    else:
        assert len(calls) == 1 and calls[0][:2] == ["pkill", "-x"] and "ollama" in calls[0]


def test_default_stop_server_swallows_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(cmd: list[str], **k: object) -> None:
        raise FileNotFoundError("pkill missing")

    monkeypatch.setattr(op.subprocess, "run", boom)
    op._default_stop_server()  # missing utility / nothing to kill -> logged, never raised
