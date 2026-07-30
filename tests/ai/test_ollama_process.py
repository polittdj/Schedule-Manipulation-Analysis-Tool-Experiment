"""OllamaLauncher lifecycle — start only when the user enables AI, free the GPU on close.

The tool engages Ollama only when the operator turns the Ollama backend on (``ensure_running``),
never at launch. On close it tidies up in three tiers (ADR-0315): engaged → unload + VERIFY the
list drains + tree-kill our spawn while it is alive + full stop (ADR-0122, unchanged);
used-but-never-engaged → unload ONLY the models this session generated with, touching no
process; never used → a total no-op, so a pre-existing Ollama the operator runs themselves is
left alone. A durable marker (under the per-test ``$SF_CACHE_DIR``) survives a hard-killed
session for startup reconciliation. I/O is injected (no real server).
"""

from __future__ import annotations

import pytest

from schedule_forensics.ai import ollama_process as op
from schedule_forensics.ai.ollama_process import (
    OllamaLauncher,
    find_ollama_executable,
    unload_loaded_models,
)

_LOG = "schedule_forensics.ai.ollama_process"


class _FakeProc:
    def __init__(self) -> None:
        self.terminated = False
        self.killed = False
        self._alive = True
        self.pid = 4242  # never dereferenced by a real kill — tests inject tree_killer

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
        unloader=lambda ep, only=None: unloaded.__setitem__("n", unloaded["n"] + 1) or 1,
        stopper=lambda: stopped.__setitem__("n", stopped["n"] + 1),
        ps_reader=lambda ep, t: [],  # the post-unload verify sees a drained server (hermetic)
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
        unloader=lambda ep, only=None: unloaded.__setitem__("n", unloaded["n"] + 1) or 1,
        stopper=lambda: stopped.__setitem__("n", stopped["n"] + 1),
        tree_killer=lambda pid: None,  # the alive-at-kill ordering is pinned by its own test
        ps_reader=lambda ep, t: [],
        start_timeout=5.0,
    )
    assert launcher.ensure_running() == "started"
    launcher.shutdown()
    assert proc.terminated is True  # we started it, so we stop it gracefully
    assert unloaded["n"] >= 1 and stopped["n"] >= 1  # RAM freed + server fully stopped
    launcher.shutdown()  # idempotent — no raise


def test_shutdown_is_a_no_op_when_ai_was_never_enabled() -> None:
    # ensure_running() is never called AND record_use() never fired -> tier (d) of ADR-0315:
    # shutdown must not touch a pre-existing Ollama the operator runs themselves (no unload,
    # no server stop).
    unloaded = {"n": 0}
    stopped = {"n": 0}
    launcher = OllamaLauncher(
        prober=lambda ep: True,
        unloader=lambda ep, only=None: unloaded.__setitem__("n", unloaded["n"] + 1) or 1,
        stopper=lambda: stopped.__setitem__("n", stopped["n"] + 1),
    )
    launcher.shutdown()
    assert unloaded["n"] == 0 and stopped["n"] == 0


def test_no_binary_means_no_spawn() -> None:
    launcher = OllamaLauncher(
        prober=lambda ep: False,
        finder=lambda: None,
        spawn=lambda exe, hp: _FakeProc(),
        unloader=lambda ep, only=None: 0,
        stopper=lambda: None,
        ps_reader=lambda ep, t: [],
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


# --- ADR-0315: the three-tier GPU-release shutdown + startup reconciliation ----------------------


def test_use_without_settings_unloads_only_and_kills_nothing() -> None:
    """The operator's reproduced scenario (audit F-4): Ask-the-AI ran on the DEFAULT config
    against an already-running Ollama — Settings never opened. Shutdown must unload exactly the
    models this session used and touch NO process. Able to fail: on the pre-ADR-0315 code
    shutdown returned at the not-engaged gate and the unloader was never called."""
    calls: list[tuple[str, frozenset[str] | None]] = []
    stopped = {"n": 0}
    killed: list[int] = []
    launcher = OllamaLauncher(
        prober=lambda ep: True,
        unloader=lambda ep, only=None: calls.append((ep, only)) or 1,
        stopper=lambda: stopped.__setitem__("n", stopped["n"] + 1),
        tree_killer=lambda pid: killed.append(pid),
        ps_reader=lambda ep, t: [],
    )
    launcher.record_use("qwen2.5:7b-instruct", "http://127.0.0.1:11434")
    launcher.shutdown()
    assert calls == [("http://127.0.0.1:11434", frozenset({"qwen2.5:7b-instruct"}))]
    assert stopped["n"] == 0 and killed == []  # no process is ever touched on this tier


def test_engaged_wins_over_used_full_stop_stands() -> None:
    """An engaged-AND-used session takes the ADR-0122 path: unload-ALL (only=None) + full stop —
    the softer used-only tier never reaches a session that turned the backend on in Settings."""
    calls: list[tuple[str, frozenset[str] | None]] = []
    stopped = {"n": 0}
    launcher = OllamaLauncher(
        prober=lambda ep: True,
        unloader=lambda ep, only=None: calls.append((ep, only)) or 1,
        stopper=lambda: stopped.__setitem__("n", stopped["n"] + 1),
        ps_reader=lambda ep, t: [],
    )
    launcher.record_use("m", launcher.endpoint)
    assert launcher.ensure_running() == "already-running"
    launcher.shutdown()
    assert calls == [(launcher.endpoint, None)]  # unload-all, not the used-only subset
    assert stopped["n"] == 1


def test_record_use_tracks_multiple_endpoints() -> None:
    """A mid-session endpoint change must not lose the first endpoint's unload."""
    calls: list[tuple[str, frozenset[str] | None]] = []
    launcher = OllamaLauncher(
        prober=lambda ep: True,
        unloader=lambda ep, only=None: calls.append((ep, only)) or 1,
        stopper=lambda: None,
        ps_reader=lambda ep, t: [],
    )
    launcher.record_use("a", "http://127.0.0.1:11434")
    launcher.record_use("b", "http://127.0.0.1:11500")
    launcher.shutdown()
    assert sorted(calls) == [
        ("http://127.0.0.1:11434", frozenset({"a"})),
        ("http://127.0.0.1:11500", frozenset({"b"})),
    ]


def test_second_shutdown_after_used_unload_is_a_no_op() -> None:
    """The launcher's ``finally`` and the atexit backstop both call shutdown; after a clean
    used-tier unload the second call must do nothing (the session state was settled)."""
    calls: list[tuple[str, frozenset[str] | None]] = []
    launcher = OllamaLauncher(
        prober=lambda ep: True,
        unloader=lambda ep, only=None: calls.append((ep, only)) or 1,
        stopper=lambda: None,
        ps_reader=lambda ep, t: [],
    )
    launcher.record_use("m", launcher.endpoint)
    launcher.shutdown()
    launcher.shutdown()
    assert len(calls) == 1


def test_shutdown_reaps_the_tree_while_the_parent_is_alive() -> None:
    """Audit F-7 (Critical): the model runner is reachable only through a LIVE ancestor. The old
    order terminated the parent first, so the image sweep that followed found nothing and the
    runner survived holding the GPU. Able to fail: on the pre-ADR-0315 code no tree-kill exists
    (alive_at_kill stays empty)."""
    proc = _FakeProc()
    seen = {"n": 0}

    def prober(ep: str) -> bool:
        seen["n"] += 1
        return seen["n"] > 1  # down on the initial check (so we start), up after the spawn

    alive_at_kill: list[bool] = []
    launcher = OllamaLauncher(
        prober=prober,
        finder=lambda: "/x/ollama",
        spawn=lambda exe, hp: proc,
        unloader=lambda ep, only=None: 0,
        stopper=lambda: None,
        tree_killer=lambda pid: alive_at_kill.append(proc.poll() is None),
        ps_reader=lambda ep, t: [],
        start_timeout=5.0,
    )
    assert launcher.ensure_running() == "started"
    launcher.shutdown()
    assert alive_at_kill == [True]  # tree-killed exactly once, while the parent still lived
    assert proc.terminated is True  # and only then reaped


def test_shutdown_verifies_the_unload_and_reports_failure(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Audit F-5/F-8: a POST count is not an unload. When ``/api/ps`` still lists models after
    the unload, shutdown must say so at WARNING and mark ``status`` — never silently claim
    success. Able to fail: on the pre-ADR-0315 code no re-probe existed."""
    monkeypatch.setattr(op.time, "sleep", lambda s: None)  # don't wait out the bounded re-probe
    launcher = OllamaLauncher(
        prober=lambda ep: True,
        unloader=lambda ep, only=None: 1,
        stopper=lambda: None,
        ps_reader=lambda ep, t: ["qwen2.5:7b-instruct"],  # resident forever
    )
    launcher.ensure_running()
    with caplog.at_level("WARNING", logger=_LOG):
        launcher.shutdown()
    assert launcher.status == "unload-incomplete"
    assert "still reports loaded models" in caplog.text


def test_startup_reconciliation_touches_ollama_only_with_a_marker() -> None:
    """ADR-0315: reconciliation acts ONLY on the durable marker's proof of ownership — an Ollama
    the operator runs for their own work is never touched. Able to fail: the method did not
    exist before this change."""
    calls: list[tuple[str, frozenset[str] | None]] = []
    kw = dict(
        prober=lambda ep: True,
        unloader=lambda ep, only=None: calls.append((ep, only)) or 1,
        stopper=lambda: None,
        ps_reader=lambda ep, t: [],
    )
    assert OllamaLauncher(**kw).reconcile_at_startup() == "no-marker"
    assert calls == []  # nothing touched without proof of ownership
    engaged = OllamaLauncher(**kw)
    engaged.record_use("m", engaged.endpoint)  # writes the durable marker
    fresh = OllamaLauncher(**kw)  # a NEW session: in-memory state gone, the marker survives
    assert fresh.reconcile_at_startup() == "reclaimed"
    assert calls == [(fresh.endpoint, frozenset({"m"}))]
    assert fresh.reconcile_at_startup() == "no-marker"  # marker cleared -> idempotent


def test_marker_survives_a_hard_kill_simulation() -> None:
    """Audit F-1/F-3: engagement must outlive the instance — a hard-killed session runs no
    shutdown. Engage, DROP the instance, and a new one must still see the proof."""
    kw = dict(
        prober=lambda ep: True,
        unloader=lambda ep, only=None: 0,
        stopper=lambda: None,
        ps_reader=lambda ep, t: [],
    )
    OllamaLauncher(**kw).ensure_running()  # no shutdown() — the simulated hard kill
    assert OllamaLauncher(**kw).reconcile_at_startup() == "nothing-loaded"


def test_reconciliation_names_the_orphan_when_nothing_listens(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Audit F-9: with the prior session's server gone, an orphaned runner is unreachable by any
    code path — reconciliation must SAY so (``orphan-suspected``), never pretend it cleaned up."""
    first = OllamaLauncher(
        prober=lambda ep: True,
        unloader=lambda ep, only=None: 0,
        stopper=lambda: None,
        ps_reader=lambda ep, t: [],
    )
    first.record_use("m", first.endpoint)  # durable proof, then the session hard-dies
    down = OllamaLauncher(
        prober=lambda ep: False,
        unloader=lambda ep, only=None: 0,
        stopper=lambda: None,
        ps_reader=lambda ep, t: [],
    )
    with caplog.at_level("WARNING", logger=_LOG):
        assert down.reconcile_at_startup() == "unreachable"
    assert down.status == "orphan-suspected"
    assert "cannot reach a runner" in caplog.text
