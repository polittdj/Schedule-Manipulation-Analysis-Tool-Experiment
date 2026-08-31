"""M5-02's security half: the ``next_url`` the language form now posts must stay LOCAL.

Giving ``/language`` an operator-supplied destination is what fixed the "always bounces to the
dashboard" defect (audit M5-02), and it is also the classic way to introduce an open redirect.
The same validation ``/target`` and ``/project/select`` apply is asserted here directly, against
the payloads that would exploit it — a host-bearing URL, a protocol-relative one, and a scheme.

This is a route-level test on purpose: it needs no browser, so it runs in the normal suite where
an open redirect would otherwise only be caught by a browser job.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


#: Every payload must land on "/" — never on the attacker's host, and never off-origin.
HOSTILE = [
    "https://evil.example/pwned",
    "http://evil.example",
    "//evil.example/pwned",
    "///evil.example",
    "javascript:alert(1)",
    "\\\\evil.example",
]


@pytest.mark.parametrize("payload", HOSTILE)
def test_language_never_redirects_off_the_local_origin(client: TestClient, payload: str) -> None:
    r = client.post("/language", data={"lang": "es", "next_url": payload}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/", (
        f"/language accepted {payload!r} as a destination — that is an open redirect"
    )


@pytest.mark.parametrize("path", ["/standards", "/evm", "/path?source=1", "/analysis/x"])
def test_language_honours_a_local_next_url(client: TestClient, path: str) -> None:
    """The fix must still do its job: a genuine local path is where the operator returns."""
    r = client.post("/language", data={"lang": "es", "next_url": path}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == path


#: Backslash payloads are the subtle case: some URL parsers fold ``\`` into ``/``, which would
#: turn a "local-looking" ``/\evil.example`` into a protocol-relative ``//evil.example``. Measured
#: rather than assumed — Starlette percent-encodes it to ``/%5Cevil.example``, which stays on this
#: origin. Pinned so a future change of redirect machinery cannot quietly reopen the hole.
BACKSLASH = ["/\\evil.example", "/\\/evil.example", "/\\\\evil.example", "/\\@evil.example"]


@pytest.mark.parametrize("payload", BACKSLASH)
def test_a_backslash_path_can_never_become_protocol_relative(
    client: TestClient, payload: str
) -> None:
    r = client.post("/language", data={"lang": "es", "next_url": payload}, follow_redirects=False)
    assert r.status_code == 303
    location = r.headers["location"]
    assert location.startswith("/"), f"{payload!r} escaped the local origin: {location!r}"
    assert not location.startswith("//"), (
        f"{payload!r} became protocol-relative ({location!r}) — that leaves the machine"
    )
    assert "\\" not in location, (
        f"{payload!r} kept a raw backslash ({location!r}); a parser that folds it into '/' would "
        f"make this protocol-relative"
    )
