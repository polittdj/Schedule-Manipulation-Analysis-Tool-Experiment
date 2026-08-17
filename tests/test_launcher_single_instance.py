"""Single-instance handover (ADR-0334) — the launcher claims the port before it serves.

**These gates exist because of a MEASUREMENT, not a theory.** On the deployed Windows box
(2026-08-01, v1.0.149 — captured verbatim in ``docs/STATE/OPERATOR-REQUESTS.md`` under OR-06):

======================================  ===================  ==============================
step                                    LISTENING on 8321    ``pythonw`` processes
======================================  ===================  ==============================
after stopping                          none                 none
after **1st** launch                    18664                18664 + 39740, both 19:33:17
after closing **only the browser**      18664 (survives)     18664 + 39740, both 19:33:17
after **2nd** launch                    18664                18664 + 39740, still 19:33:17
======================================  ===================  ==============================

The second launch produced **no new listener and no new process even transiently**: it exited mute
(uvicorn's bind failure → ``sys.exit`` into the ``os.devnull`` sink ``_ensure_streams`` installs)
while its already-armed browser timer opened a window onto the OLD server — with the previous
session's schedules and settings still in memory. That is the *server-side* half of OR-06, which no
amount of clearing browser storage could fix, and it also defeats ADR-0324's launch token (same
process ⇒ same token).

The survivor itself is correct behaviour: ``idle_grace`` is 600 s, so a server legitimately
outlives its browser by up to ten minutes. That window is exactly when a relaunch lands on it.

**Why these tests are not "a Linux port test".** Binding behaviour differs between platforms —
Windows lets a second ``SO_REUSEADDR`` bind succeed where POSIX refuses — so pinning bind semantics
here would pin the WRONG platform and prove nothing about the operator's machine. What is pinned
instead is the launcher's DECISION LOGIC, which is identical everywhere: probe → identify → stand
down → wait → serve, or refuse. The one test that touches a real socket asserts only that a
connect-probe distinguishes a listening socket from a free port, which is portable.
"""

from __future__ import annotations

import socket
from typing import Any

import pytest

from schedule_forensics import launcher
from schedule_forensics.launcher import PortUnavailable


class _ImmediateTimer:
    """A threading.Timer stand-in that runs the callback synchronously on start()."""

    def __init__(self, delay: float, func: Any, args: tuple[Any, ...] = ()) -> None:
        self._func = func
        self._args = args

    def start(self) -> None:
        self._func(*self._args)


# ── the probe endpoint the whole handover depends on ─────────────────────────────────────────


def test_whoami_identifies_the_server_without_touching_the_watchdog() -> None:
    """``/api/whoami`` must be SIDE-EFFECT-FREE — that is the entire reason it is not
    ``/api/heartbeat``.

    A probe that refreshed ``last_beat`` would extend the life of the very process it is about to
    replace, and setting ``browser_seen`` would arm the idle watchdog on a server no browser ever
    reached. Swapping the probe to POST ``/api/heartbeat`` fails this.
    """
    from fastapi.testclient import TestClient

    from schedule_forensics.web.app import SessionState, create_app

    app = create_app(SessionState(), auto_shutdown=True)
    client = TestClient(app)
    before_beat = app.state.last_beat
    assert app.state.browser_seen is False

    body = client.get("/api/whoami").json()

    assert body["app"] == "schedule-forensics"
    assert isinstance(body["pid"], int) and body["pid"] > 0
    assert body["launch_token"] == app.state.session.launch_token
    assert app.state.browser_seen is False, "the probe armed the idle watchdog"
    assert app.state.last_beat == before_beat, "the probe refreshed the predecessor's heartbeat"


def test_whoami_carries_no_schedule_content() -> None:
    """Law 1: the probe answers before any handover, so it may never leak schedule data."""
    from fastapi.testclient import TestClient

    from schedule_forensics.web.app import SessionState, create_app

    body = TestClient(create_app(SessionState())).get("/api/whoami").json()
    assert set(body) == {"app", "pid", "version", "launch_token"}


# ── the claim decision, pinned per branch (portable — no bind semantics involved) ─────────────


def test_a_free_port_is_claimed_without_contacting_anyone(monkeypatch: pytest.MonkeyPatch) -> None:
    """The common case: nothing is there, so no probe and no stand-down are attempted."""
    calls: list[str] = []
    monkeypatch.setattr(launcher, "port_is_free", lambda h, p: True)
    monkeypatch.setattr(launcher, "probe_instance", lambda *a, **k: calls.append("probe"))
    monkeypatch.setattr(launcher, "_stand_down", lambda *a, **k: calls.append("stand_down"))

    assert launcher.claim_port("127.0.0.1", 8321) == "free"
    assert calls == []


def test_a_previous_session_is_stood_down_and_replaced(monkeypatch: pytest.MonkeyPatch) -> None:
    """THE MEASURED CASE. A predecessor holds the port; it is asked to stop, it releases, and the
    launch proceeds — a REPLACEMENT, never a reuse ("always start clean").

    Reverting ``main`` to serve without claiming makes the second launch land on the predecessor,
    which is precisely the measurement above.
    """
    free = iter([False, False, True])  # held, still held one poll later, then released
    stood_down: list[tuple[str, int]] = []
    monkeypatch.setattr(launcher, "port_is_free", lambda h, p: next(free))
    monkeypatch.setattr(
        launcher, "probe_instance", lambda *a, **k: {"app": "schedule-forensics", "pid": 18664}
    )
    monkeypatch.setattr(launcher, "_stand_down", lambda h, p, **k: stood_down.append((h, p)))

    result = launcher.claim_port("127.0.0.1", 8321, sleep=lambda _s: None)

    assert result == "handover"
    assert stood_down == [("127.0.0.1", 8321)], "the predecessor was never asked to stand down"


def test_a_stubborn_predecessor_fails_visibly_instead_of_opening_a_browser(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the port never frees, the launch STOPS. The alternative — bind anyway — is what a
    testimony tool must never do: on Windows the second bind can succeed and route requests
    indeterminately between two servers.

    The error names the pid so the operator can act on it.
    """
    monkeypatch.setattr(launcher, "port_is_free", lambda h, p: False)
    monkeypatch.setattr(
        launcher, "probe_instance", lambda *a, **k: {"app": "schedule-forensics", "pid": 18664}
    )
    monkeypatch.setattr(launcher, "_stand_down", lambda *a, **k: None)

    ticks = iter([0.0, 1.0, 99.0])
    with pytest.raises(PortUnavailable, match="18664"):
        launcher.claim_port("127.0.0.1", 8321, sleep=lambda _s: None, now=lambda: next(ticks))


def test_an_unrelated_program_on_the_port_is_never_shut_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The tool may only stand down ITS OWN predecessor. Something else on 8321 (another app, a
    proxy) must produce a visible refusal — never a shutdown POST aimed at a stranger."""
    monkeypatch.setattr(launcher, "port_is_free", lambda h, p: False)
    monkeypatch.setattr(launcher, "probe_instance", lambda *a, **k: None)
    stood_down: list[Any] = []
    monkeypatch.setattr(launcher, "_stand_down", lambda *a, **k: stood_down.append(a))

    with pytest.raises(PortUnavailable, match="another program"):
        launcher.claim_port("127.0.0.1", 8321)
    assert stood_down == [], "a stranger's port was sent a shutdown request"


def test_probe_rejects_a_stranger_that_answers_http(monkeypatch: pytest.MonkeyPatch) -> None:
    """A 200 from something that is not us must not be mistaken for our own predecessor."""
    import json

    class _Resp:
        status = 200

        def read(self) -> bytes:
            return json.dumps({"app": "something-else", "pid": 1}).encode()

        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *_a: object) -> None:
            return None

    monkeypatch.setattr(launcher._LOOPBACK_OPENER, "open", lambda *a, **k: _Resp())
    assert launcher.probe_instance("127.0.0.1", 8321) is None


# ── the ordering that the measurement actually indicts ───────────────────────────────────────


def test_the_port_is_claimed_before_the_browser_timer_is_armed() -> None:
    """THE ORDERING GATE. The measured failure is not "the launch failed" — it is that the browser
    opened ANYWAY, onto the old session, because the timer was armed before the bind was attempted.

    So the claim must complete before the browser is ever scheduled. Note this does NOT mean
    "arm the timer after ``serve_fn``": ``serve_fn`` blocks for the life of the process, so a
    timer started after it would never fire at all.
    """
    order: list[str] = []

    def claim(host: str, port: int) -> str:
        order.append("claim")
        return "free"

    launcher.main(
        port=9,  # never bound: serve is a stub
        serve=lambda *a, **k: order.append("serve"),
        browser=lambda url: order.append("browser") or True,
        timer=_ImmediateTimer,
        manage_ollama=False,
        claim=claim,
    )
    assert order == ["claim", "browser", "serve"]


def test_a_failed_claim_stops_the_launch_before_any_browser_opens() -> None:
    """The operator must never get a window onto an unknown session. If the claim raises, no
    browser is opened and nothing is served — ``__main__`` turns the raise into a native message
    box under ``pythonw``, where a bare ``sys.exit`` was previously invisible."""
    opened: list[str] = []
    served: list[str] = []

    def claim(host: str, port: int) -> str:
        raise PortUnavailable("still held")

    with pytest.raises(PortUnavailable):
        launcher.main(
            port=9,
            serve=lambda *a, **k: served.append("serve"),
            browser=lambda url: opened.append(url) or True,
            timer=_ImmediateTimer,
            manage_ollama=False,
            claim=claim,
        )
    assert opened == [], "a browser opened onto a session the launcher could not claim"
    assert served == [], "the app served despite an unclaimable port"


# ── the one real-socket assertion, deliberately platform-neutral ──────────────────────────────


def test_port_is_free_distinguishes_a_listener_from_an_empty_port() -> None:
    """A connect-probe, not a bind-probe. Binding would answer the wrong question on Windows,
    where a second bind can succeed against a port another process is already serving; connecting
    is the same everywhere."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        port = srv.getsockname()[1]
        assert launcher.port_is_free("127.0.0.1", port) is False
    # the socket is closed now — the port reads as free again
    assert launcher.port_is_free("127.0.0.1", port) is True


def test_the_probe_never_goes_through_a_system_proxy() -> None:
    """LAW 1. urllib's DEFAULT opener reads the machine's proxy settings, so on a
    corporate-managed Windows laptop even ``http://127.0.0.1:8321`` can be routed through the
    company proxy — the probe would be refused (a live predecessor misread as "not ours", so the
    launcher refuses to start for no reason) or, far worse, sent off-machine.

    The launcher therefore builds its opener with an EMPTY ``ProxyHandler``, the same hardening
    ``ai/ollama.py`` applies for the same reason.

    **The assertion is ABSENCE, and that is not a technicality.** ``ProxyHandler`` installs one
    ``<scheme>_open`` method per configured proxy; with an empty mapping it installs none, and
    ``OpenerDirector.add_handler`` only registers handlers that contribute a method — so a
    correctly hardened opener carries NO ``ProxyHandler`` at all, and proxying is impossible
    because nothing implements it. Reverting to a bare ``urllib.request.build_opener()`` (or to
    ``urllib.request.urlopen``) puts back a ``ProxyHandler`` populated from the environment, which
    is what this catches.
    """
    import urllib.request

    proxied = [
        h
        for h in launcher._LOOPBACK_OPENER.handlers
        if isinstance(h, urllib.request.ProxyHandler) and h.proxies
    ]
    assert not proxied, (
        f"the probe opener carries system proxies {[h.proxies for h in proxied]} — a loopback "
        "probe must connect directly (Law 1)"
    )


# ── ADR-0412: an unclaimable port RELOCATES; it never locks the operator out ──────────────────


def test_an_unclaimable_port_relocates_instead_of_refusing_to_start() -> None:
    """Operator directive 2026-08-17: "no matter how the user closes the program there is no
    issue."

    Field report: the app was closed without using Quit, and every later launch refused with
    "already running on port 8321". Two paths dead-ended in :class:`PortUnavailable` — a holder
    that does not answer ``/api/whoami`` (a wedged or half-dead instance, or a stranger), and a
    predecessor that never releases. Both told the operator to "quit it from its own window",
    which is impossible: the desktop icon runs ``pythonw`` and there IS no window.

    The launch now moves to a free port instead. ADR-0334's safety property is untouched — the
    contested port is still never bound (that is what would route requests indeterminately
    between two servers); we simply serve somewhere else.
    """
    served: list[int] = []
    opened: list[str] = []

    def claim(host: str, port: int) -> str:
        if port == 8321:
            raise PortUnavailable("held by something that will not answer")
        return "free"

    launcher.main(
        port=8321,
        serve=lambda app, host, port, **k: served.append(port),
        browser=lambda url: opened.append(url) or True,
        timer=_ImmediateTimer,
        manage_ollama=False,
        claim=claim,
    )

    assert served, "the launcher refused to serve — the operator is locked out"
    assert served[0] != 8321, "the CONTESTED port was bound (ADR-0334 safety property broken)"
    assert opened and opened[0].endswith(f":{served[0]}"), (
        f"the browser must open onto the port actually served: {opened} vs {served}"
    )


def test_relocation_does_not_happen_when_the_preferred_port_is_claimable() -> None:
    """The control: relocation is the exception, not the habit. A claimable preferred port is
    used as-is, so the operator's bookmark and the documented 8321 keep working."""
    served: list[int] = []
    launcher.main(
        port=8321,
        serve=lambda app, host, port, **k: served.append(port),
        browser=lambda url: True,
        timer=_ImmediateTimer,
        manage_ollama=False,
        claim=lambda host, port: "free",
    )
    assert served == [8321]


def test_resolve_port_reports_how_it_got_the_port() -> None:
    """``resolve_port`` is the seam the launcher uses; it must report which path it took so the
    console line can tell the operator the address moved."""
    assert launcher.resolve_port("127.0.0.1", 8321, claim=lambda h, p: "free") == (8321, "free")
    assert launcher.resolve_port("127.0.0.1", 8321, claim=lambda h, p: "handover") == (
        8321,
        "handover",
    )

    def stubborn(host: str, port: int) -> str:
        if port == 8321:
            raise PortUnavailable("wedged")
        return "free"

    port, how = launcher.resolve_port("127.0.0.1", 8321, claim=stubborn)
    assert how == "relocated" and port != 8321
