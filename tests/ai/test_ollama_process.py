"""OllamaLauncher lifecycle — start only when the user enables AI, tidy up on close.

The tool engages Ollama only when the operator turns the Ollama backend on (``ensure_running``),
never at launch. On close it frees the model RAM (unloads loaded models) and stops the
``ollama serve`` it started; if the tool never engaged Ollama, shutdown touches nothing — a
pre-existing Ollama the operator runs themselves is left alone. I/O is injected (no real server).
"""

from __future__ import annotations

from schedule_forensics.ai.ollama_process import (
    OllamaLauncher,
    find_ollama_executable,
    unload_loaded_models,
)


class _FakeProc:
    def __init__(self) -> None:
        self.terminated = False
        self.killed = False
        self._alive = True

    def poll(self) -> int | None:
        return None if self._alive else 0

    def terminate(self) -> None:
        self.terminated = True
        self._alive = False

    def wait(self, timeout: float | None = None) -> int:
        return 0

    def kill(self) -> None:
        self.killed = True
        self._alive = False


def test_adopts_a_running_ollama_unloads_and_then_stops_the_server_on_close() -> None:
    spawned: list[tuple[str, str]] = []
    unloaded = {"n": 0}
    stopped = {"n": 0}
    launcher = OllamaLauncher(
        prober=lambda ep: True,  # something is already listening (e.g. the Windows tray's server)
        finder=lambda: "/x/ollama",
        spawn=lambda exe, hp: spawned.append((exe, hp)) or _FakeProc(),  # type: ignore[func-returns-value,return-value]
        unloader=lambda ep: unloaded.__setitem__("n", unloaded["n"] + 1) or 1,
        stopper=lambda: stopped.__setitem__("n", stopped["n"] + 1),
    )
    assert launcher.ensure_running() == "already-running"
    assert spawned == []  # we did NOT start one
    launcher.shutdown()  # engaged: free the model RAM AND stop the server (operator's choice)
    assert unloaded["n"] == 1  # the model was unloaded so it stops holding memory
    assert stopped["n"] == 1  # the adopted server is stopped too — nothing left running


def test_starts_ollama_when_down_and_stops_it_on_shutdown() -> None:
    proc = _FakeProc()
    seen = {"n": 0}

    def prober(ep: str) -> bool:
        seen["n"] += 1
        return seen["n"] > 1  # down on the initial check (so we start), up after the spawn

    unloaded = {"n": 0}
    stopped = {"n": 0}
    launcher = OllamaLauncher(
        prober=prober,
        finder=lambda: "/x/ollama",
        spawn=lambda exe, hp: proc,
        unloader=lambda ep: unloaded.__setitem__("n", unloaded["n"] + 1) or 1,
        stopper=lambda: stopped.__setitem__("n", stopped["n"] + 1),
        start_timeout=5.0,
    )
    assert launcher.ensure_running() == "started"
    launcher.shutdown()
    assert proc.terminated is True  # we started it, so we stop it gracefully
    assert unloaded["n"] >= 1 and stopped["n"] >= 1  # RAM freed + server fully stopped
    launcher.shutdown()  # idempotent — no raise


def test_shutdown_is_a_no_op_when_ai_was_never_enabled() -> None:
    # ensure_running() is never called -> the tool never engaged Ollama -> shutdown must not touch
    # a pre-existing Ollama the operator runs themselves (no unload, no server stop).
    unloaded = {"n": 0}
    stopped = {"n": 0}
    launcher = OllamaLauncher(
        prober=lambda ep: True,
        unloader=lambda ep: unloaded.__setitem__("n", unloaded["n"] + 1) or 1,
        stopper=lambda: stopped.__setitem__("n", stopped["n"] + 1),
    )
    launcher.shutdown()
    assert unloaded["n"] == 0 and stopped["n"] == 0


def test_no_binary_means_no_spawn() -> None:
    launcher = OllamaLauncher(
        prober=lambda ep: False,
        finder=lambda: None,
        spawn=lambda exe, hp: _FakeProc(),
        unloader=lambda ep: 0,
        stopper=lambda: None,
    )
    assert launcher.ensure_running() == "no-binary"
    launcher.shutdown()  # engaged but nothing started -> unload + stop attempted, no terminate


def test_started_but_not_up_within_budget_reports_starting() -> None:
    launcher = OllamaLauncher(
        prober=lambda ep: False,
        finder=lambda: "/x/ollama",
        spawn=lambda exe, hp: _FakeProc(),
        start_timeout=0.0,
    )
    assert launcher.ensure_running() == "starting"  # spawned, not yet listening


def test_unload_loaded_models_is_best_effort_when_server_is_down() -> None:
    # nothing listening here -> connection refused -> 0 unloaded, never raises (close-time cleanup)
    assert unload_loaded_models("http://127.0.0.1:1", timeout=0.3) == 0


def test_find_executable_prefers_path() -> None:
    assert find_ollama_executable(which=lambda name: "/usr/bin/ollama") == "/usr/bin/ollama"
