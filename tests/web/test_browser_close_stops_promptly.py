"""Closing the browser stops the tool in seconds, not in ten minutes (OR-12, ADR-0482).

**The operator-reported defect.** Close the browser window without using *Wipe and Quit* and
the tool does not stop. It keeps running — and so does Ollama, holding several GB of VRAM for a
program the operator believes they closed.

**Measured on this tree before the fix**, and the repo already knew it: `idle_grace` is
**600 s**, and `static/heartbeat.js` sends NOTHING on unload. So a deliberate window close and
an operator who wandered off to lunch are the SAME event to the server, and both wait the full
ten minutes. `launcher.py`'s own comment says it out loud — *"the survivor is not a bug in
itself: idle_grace is 600s, so a server legitimately outlives its browser by up to ten
minutes. That ten-minute window is exactly when a relaunch lands on it."* ADR-0334 built the
port handover to SURVIVE that window rather than close it.

**Why this is not a one-line `idle_grace` reduction.** The 600 s grace is load-bearing: an
operator reading a long report with no interaction must not be killed. Lowering it trades one
defect for a worse one.

**And why a naive unload handler is worse still.** This app is 35 server-rendered routes, so
**every link click is a real page unload**. A `pagehide` that means "stop" would kill the tool
the first time the operator clicks anything.

So `pagehide` does not mean *stop*. It **arms a short fuse** that the next page's heartbeat
disarms: a navigation re-beats within ~1 s (heartbeat.js beats immediately on load) and the
fuse is cancelled; a real close never beats again and the fuse expires. The 600 s idle rule is
untouched for the walked-away case.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import (
    CLOSE_GRACE,
    HEARTBEAT_INTERVAL,
    _shutdown_due,
    create_app,
)

ROOT = Path(__file__).resolve().parents[2]


# --- the decision, as a pure function -----------------------------------------------------


def test_a_close_signal_stops_the_tool_once_the_fuse_burns() -> None:
    """The whole point: an explicit close does NOT wait for the 600 s idle grace."""
    assert _shutdown_due(
        browser_seen=True,
        idle_seconds=6.0,  # nowhere near the 600 s idle grace
        grace=600.0,
        closing_seconds=CLOSE_GRACE + 0.1,
        close_grace=CLOSE_GRACE,
    )


def test_a_navigation_does_not_stop_the_tool() -> None:
    """THE trap. Every one of the 35 server-rendered routes unloads the page on a click, so
    `pagehide` fires constantly during ordinary use. The new page's heartbeat clears
    `closing_at` (that is what `closing_seconds=None` represents here), and nothing stops."""
    assert not _shutdown_due(
        browser_seen=True,
        idle_seconds=0.2,
        grace=600.0,
        closing_seconds=None,  # a heartbeat arrived after the close signal
        close_grace=CLOSE_GRACE,
    )


def test_the_fuse_is_not_instant() -> None:
    """A close signal that has not yet burned its grace must not stop anything — that margin
    is exactly what lets an in-flight navigation cancel it."""
    assert not _shutdown_due(
        browser_seen=True,
        idle_seconds=0.5,
        grace=600.0,
        closing_seconds=CLOSE_GRACE - 0.1,
        close_grace=CLOSE_GRACE,
    )


def test_the_long_idle_rule_still_applies_with_no_close_signal() -> None:
    """The walked-away case is UNCHANGED — this fix must not shorten it."""
    assert _shutdown_due(
        browser_seen=True,
        idle_seconds=601.0,
        grace=600.0,
        closing_seconds=None,
        close_grace=CLOSE_GRACE,
    )
    assert not _shutdown_due(
        browser_seen=True,
        idle_seconds=599.0,
        grace=600.0,
        closing_seconds=None,
        close_grace=CLOSE_GRACE,
    )


def test_a_close_signal_before_any_browser_ever_connected_is_ignored() -> None:
    """`browser_seen` still gates everything: a server that no browser has reached must not
    shut itself down on a stray POST."""
    assert not _shutdown_due(
        browser_seen=False,
        idle_seconds=9_999.0,
        grace=600.0,
        closing_seconds=9_999.0,
        close_grace=CLOSE_GRACE,
    )


def test_the_fuse_outlasts_the_heartbeat_interval() -> None:
    """A CONSTRAINT, not a preference. The fuse is cancelled by the next heartbeat, so it must
    burn for longer than the gap between beats — otherwise an ordinary navigation could expire
    it before the new page's first beat arrives and the tool would stop on a click."""
    assert CLOSE_GRACE > HEARTBEAT_INTERVAL


def test_the_python_and_javascript_beat_intervals_cannot_drift_apart() -> None:
    """`CLOSE_GRACE > HEARTBEAT_INTERVAL` is only a real guarantee if `HEARTBEAT_INTERVAL`
    still describes what the JS actually does. The JS is vendored with no build step, so
    nothing else keeps the two numbers together — this reads the literal back out of
    `heartbeat.js` and fails if someone changes one side alone."""
    js = (ROOT / "src" / "schedule_forensics" / "web" / "static" / "heartbeat.js").read_text(
        encoding="utf-8"
    )
    found = re.findall(r"setInterval\(\s*beat\s*,\s*(\d+)\s*\)", js)
    assert found == [str(int(HEARTBEAT_INTERVAL * 1000))], (
        f"heartbeat.js beats every {found} ms but web.app.HEARTBEAT_INTERVAL says "
        f"{HEARTBEAT_INTERVAL}s — CLOSE_GRACE is derived from that number"
    )


# --- the wiring: the endpoints that set and clear the fuse ---------------------------------


def test_the_closing_endpoint_arms_the_fuse() -> None:
    app = create_app(auto_shutdown=True)
    client = TestClient(app)
    client.post("/api/heartbeat")
    assert app.state.closing_at is None
    assert client.post("/api/closing").status_code == 200
    assert app.state.closing_at is not None


def test_a_heartbeat_disarms_the_fuse() -> None:
    """The navigation path end-to-end: page unloads (fuse armed), next page loads and beats
    (fuse cleared). Without this the tool stops on the operator's first click."""
    app = create_app(auto_shutdown=True)
    client = TestClient(app)
    client.post("/api/heartbeat")
    client.post("/api/closing")
    assert app.state.closing_at is not None
    client.post("/api/heartbeat")
    assert app.state.closing_at is None


def test_the_probe_endpoint_never_arms_or_disarms_the_fuse() -> None:
    """`/api/whoami` is deliberately side-effect-free — it is what a RELAUNCHING LAUNCHER calls
    to identify a predecessor (ADR-0334). If the probe cleared the fuse, the very act of
    relaunching would cancel the close that is stopping the old server, and the handover would
    be racing a predecessor that just decided to live another ten minutes.

    The assertion is ABSOLUTE, and that is the point. It first read the pre-probe value and
    compared the post-probe value to it — which a mutation clearing the fuse on EVERY request
    walked straight through, because it corrupted both sides and `None == None` held. An oracle
    read out of the state under test cannot judge that state (QC-1). So: it must be armed at
    all, and only then must it be unchanged."""
    app = create_app(auto_shutdown=True)
    client = TestClient(app)
    client.post("/api/heartbeat")
    client.post("/api/closing")
    armed = app.state.closing_at
    assert armed is not None, "precondition: the close endpoint must have armed the fuse"
    client.get("/api/whoami")
    assert app.state.closing_at is not None, "the probe disarmed a pending close"
    assert app.state.closing_at == armed


# --- the client half, EXECUTED (a grep cannot see behaviour — ADR-0480's C9) ----------------


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_heartbeat_js_beacons_on_pagehide_and_not_on_bfcache() -> None:
    """Runs `heartbeat.js` under node with a stub DOM and asserts BEHAVIOUR:

    * a real `pagehide` sends the close beacon,
    * a bfcache `pagehide` (`persisted: true`) does NOT — the page is still alive and coming
      back, and beaconing there would stop the tool behind a back button,
    * `sfQuit()` still works and stops the beats.
    """
    node = shutil.which("node")
    assert node is not None
    harness = Path(__file__).parent / "js" / "heartbeat_close_harness.mjs"
    proc = subprocess.run(  # fixed argv, repo-local harness
        [node, str(harness)], cwd=ROOT, capture_output=True, text=True, timeout=120
    )
    assert proc.returncode == 0, f"harness failed:\n{proc.stdout}\n{proc.stderr}"
    assert proc.stdout.rstrip().endswith("OK heartbeat close"), proc.stdout
