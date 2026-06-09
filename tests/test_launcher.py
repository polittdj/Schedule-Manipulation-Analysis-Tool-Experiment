"""Desktop-launcher tests (M16) — port selection, loopback guard, and serve/browser wiring."""

from __future__ import annotations

import socket
from typing import Any

import pytest

from schedule_forensics import launcher


class _ImmediateTimer:
    """A threading.Timer stand-in that runs the callback synchronously on start()."""

    def __init__(self, delay: float, func: Any, args: tuple[Any, ...] = ()) -> None:
        self._func = func
        self._args = args

    def start(self) -> None:
        self._func(*self._args)


def test_find_free_port_is_usable() -> None:
    port = launcher.find_free_port()
    assert 1024 < port < 65536
    # the port is free: we can bind it right after
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", port))


def test_main_refuses_non_loopback_host() -> None:
    with pytest.raises(ValueError, match="local-only"):
        launcher.main(host="0.0.0.0", serve=lambda *a, **k: None)  # a non-loopback host is refused
    with pytest.raises(ValueError, match="local-only"):
        launcher.main(host="example.com", serve=lambda *a, **k: None)


def test_main_wires_serve_and_opens_browser() -> None:
    served: dict[str, Any] = {}
    opened: list[str] = []

    def fake_serve(app: Any, **kwargs: Any) -> None:
        served["app"] = app
        served.update(kwargs)

    launcher.main(
        port=12345,
        serve=fake_serve,
        browser=lambda url: opened.append(url) or True,
        timer=_ImmediateTimer,
    )
    assert served["host"] == "127.0.0.1" and served["port"] == 12345
    assert served["app"] is not None  # the FastAPI app was constructed and passed to serve
    assert opened == ["http://127.0.0.1:12345"]  # browser opened at the served URL


def test_main_can_skip_browser() -> None:
    opened: list[str] = []
    launcher.main(
        port=23456,
        open_browser=False,
        serve=lambda *a, **k: None,
        browser=lambda url: opened.append(url) or True,
        timer=_ImmediateTimer,
    )
    assert opened == []  # no browser opened when disabled
