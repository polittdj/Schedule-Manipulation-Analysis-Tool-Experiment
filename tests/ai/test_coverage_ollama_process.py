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
        unloader=lambda e, only=None: 0,  # hermetic — no real /api/ps call on shutdown
        stopper=lambda: None,  # hermetic — no real taskkill/pkill on shutdown
        tree_killer=lambda pid: None,  # hermetic — never tree-kill the test's own child
        ps_reader=lambda e, t: [],  # hermetic — the post-unload verify sees a drained server
    )
    assert launcher.ensure_running() == "started"
    launcher.shutdown()  # engaged + _proc set -> unload+verify, tree-kill, reap, stop-server


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
    launcher = op.OllamaLauncher(
        unloader=lambda e, only=None: 0, stopper=lambda: None, ps_reader=lambda e, t: []
    )
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


# --- ADR-0315: visible cleanup, selective unload, and the pid-rooted tree-kill --------------------

_LOG = "schedule_forensics.ai.ollama_process"


def test_stop_server_reports_real_failures_and_tolerates_no_such_process(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Audit F-6: ``check=False`` used to DISCARD the kill results, so total cleanup failure
    looked exactly like success. A real failure now logs at WARNING; "no such process"
    (taskkill 128 / pkill 1) stays informational. Able to fail: on the pre-ADR-0315 code no
    log record is emitted at all."""
    monkeypatch.setattr(
        op.subprocess,
        "run",
        lambda cmd, **k: subprocess.CompletedProcess(cmd, 5, stdout="", stderr="access denied"),
    )
    with caplog.at_level("INFO", logger=_LOG):
        op._default_stop_server()
    assert "exited 5" in caplog.text and "access denied" in caplog.text
    caplog.clear()
    monkeypatch.setattr(
        op.subprocess,
        "run",
        lambda cmd, **k: subprocess.CompletedProcess(cmd, 1, stdout="", stderr=""),
    )
    with caplog.at_level("INFO", logger=_LOG):
        op._default_stop_server()
    assert "no such process" in caplog.text
    assert not any(r.levelname == "WARNING" for r in caplog.records)  # nothing-to-kill is fine


def test_unload_listing_failure_is_logged_not_silent(caplog: pytest.LogCaptureFixture) -> None:
    """Audit F-5: the bare ``except: return 0`` hid the exact post-orphan state (connection
    refused against a dead proxy). The zero is still returned — but visibly."""
    with caplog.at_level("WARNING", logger=_LOG):
        assert op.unload_loaded_models("http://127.0.0.1:1", timeout=0.3) == 0
    assert "could not list loaded Ollama models" in caplog.text


def test_unload_only_filters_by_tolerant_base_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """The used-but-never-engaged tier must evict ONLY what the session loaded: config
    ``qwen2.5`` matches the loaded ``qwen2.5:7b-instruct`` (base-name rule) and the operator's
    other model is left resident. Able to fail: drop the ``only`` filter and both unload."""
    posts: list[str] = []

    class _Resp:
        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *a: object) -> None:
            return None

    def fake_open(req: object, timeout: float | None = None) -> _Resp:
        posts.append(op.json.loads(req.data.decode("utf-8"))["model"])  # type: ignore[attr-defined]
        return _Resp()

    monkeypatch.setattr(
        op, "_loaded_models", lambda ep, t: ["qwen2.5:7b-instruct", "llama3.2:latest"]
    )
    monkeypatch.setattr(op._DIRECT_OPENER, "open", fake_open)
    n = op.unload_loaded_models("http://127.0.0.1:11434", only=frozenset({"qwen2.5"}))
    assert n == 1 and posts == ["qwen2.5:7b-instruct"]


def test_windows_stop_list_pins_the_images_and_excludes_llama_server(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ADR-0315: the sweep stays tray-then-server, and NO runner image name is ever added —
    ``llama-server`` is llama.cpp's generic server binary (the tool's own supported
    OpenAI-compat backend runs one), so a name sweep could kill a server the tool doesn't own;
    the spawned serve's runner is reaped by the pid-rooted tree-kill instead. A future
    'helpful' image addition must trip this test and read the ADR."""
    from types import SimpleNamespace

    calls: list[list[str]] = []
    monkeypatch.setattr(op, "sys", SimpleNamespace(platform="win32"))  # never touch real sys
    monkeypatch.setattr(
        op.subprocess,
        "run",
        lambda cmd, **k: calls.append(cmd) or subprocess.CompletedProcess(cmd, 0, "", ""),
    )
    op._default_stop_server()
    images = [c[-1] for c in calls]
    assert images == ["ollama app.exe", "ollama.exe"]  # tray first (it respawns), then server
    assert not any("llama" in i and "server" in i for i in images)


def test_names_match_is_tolerant_but_never_empty() -> None:
    assert op._names_match("llama3.1", "llama3.1:8b")
    assert op._names_match("llama3.1:8b", "llama3.1")
    assert op._names_match("QWEN2.5:7B", "qwen2.5:7b")
    assert not op._names_match("llama3.1", "llama3.2:1b")
    assert not op._names_match("", "anything")


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX process groups")
def test_kill_tree_kills_a_detached_group() -> None:
    """The POSIX tree-kill: a child started in its own session (exactly how ``_default_spawn``
    starts ``ollama serve``) is gone after ``_kill_tree`` — TERM, then KILL after the grace."""
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        start_new_session=True,
        stdin=subprocess.DEVNULL,
    )
    try:
        op._kill_tree(proc.pid)
        assert proc.wait(timeout=5) is not None  # killed
    finally:
        if proc.poll() is None:
            proc.kill()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX process groups")
def test_kill_tree_refuses_our_own_process_group(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Defense-in-depth: our spawn always creates its own session, so a target sharing THIS
    process's group is not our spawn (or the pid was recycled) — ``killpg`` must never fire."""
    fired: list[tuple[int, int]] = []
    monkeypatch.setattr(op.os, "killpg", lambda pgid, sig: fired.append((pgid, sig)))
    with caplog.at_level("WARNING", logger=_LOG):
        op._kill_tree(op.os.getpid())  # our own pid: same group by construction
    assert fired == []
    assert "refusing tree-kill" in caplog.text
