"""OllamaLauncher lifecycle — start only when needed, stop only what we started (injected I/O)."""

from __future__ import annotations

from schedule_forensics.ai.ollama_process import OllamaLauncher, find_ollama_executable


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


def test_uses_an_already_running_ollama_and_never_stops_it() -> None:
    spawned: list[tuple[str, str]] = []
    launcher = OllamaLauncher(
        prober=lambda ep: True,  # something is already listening
        finder=lambda: "/x/ollama",
        spawn=lambda exe, hp: spawned.append((exe, hp)) or _FakeProc(),  # type: ignore[func-returns-value,return-value]
    )
    assert launcher.ensure_running() == "already-running"
    assert spawned == []  # we did NOT start one
    launcher.shutdown()  # no-op — we must never kill an Ollama we didn't start


def test_starts_ollama_when_down_and_stops_it_on_shutdown() -> None:
    proc = _FakeProc()
    seen = {"n": 0}

    def prober(ep: str) -> bool:
        seen["n"] += 1
        return seen["n"] > 1  # down on the initial check (so we start), up after the spawn

    launcher = OllamaLauncher(
        prober=prober, finder=lambda: "/x/ollama", spawn=lambda exe, hp: proc, start_timeout=5.0
    )
    assert launcher.ensure_running() == "started"
    launcher.shutdown()
    assert proc.terminated is True  # we started it, so we stop it
    launcher.shutdown()  # idempotent — no second terminate / no raise


def test_no_binary_means_no_spawn() -> None:
    launcher = OllamaLauncher(
        prober=lambda ep: False, finder=lambda: None, spawn=lambda exe, hp: _FakeProc()
    )
    assert launcher.ensure_running() == "no-binary"
    launcher.shutdown()  # no-op


def test_started_but_not_up_within_budget_reports_starting() -> None:
    launcher = OllamaLauncher(
        prober=lambda ep: False,
        finder=lambda: "/x/ollama",
        spawn=lambda exe, hp: _FakeProc(),
        start_timeout=0.0,
    )
    assert launcher.ensure_running() == "starting"  # spawned, not yet listening


def test_find_executable_prefers_path() -> None:
    assert find_ollama_executable(which=lambda name: "/usr/bin/ollama") == "/usr/bin/ollama"
