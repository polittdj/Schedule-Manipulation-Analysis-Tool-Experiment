"""SEC-2 / SEC-3 hardening (ADR-0264) — Host allowlist + Origin gate on unsafe methods.

SEC-3: the loopback tool must refuse any request whose Host header is not a genuine loopback
name — the DNS-rebinding read vector (an attacker domain re-resolved to 127.0.0.1 carries the
ATTACKER'S name in Host) is a path to real CUI on a production machine.

SEC-2: a state-mutating request carrying a foreign (or ``null``) Origin is the cross-site
request-forgery signature — browsers attach Origin to every cross-site POST, forms included.
Absent-Origin requests are non-browser local clients and pass; same-origin browser POSTs carry
the loopback origin and pass; reads are never Origin-gated (browsers omit Origin on
same-origin GET navigations, so gating reads would break normal use).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app


@pytest.fixture
def sc() -> tuple[SessionState, TestClient]:
    st = SessionState()
    return st, TestClient(create_app(st))


# ── SEC-3: the Host allowlist ─────────────────────────────────────────────────────────────────────


def test_foreign_host_is_refused_before_any_route_runs(sc) -> None:  # type: ignore[no-untyped-def]
    _st, client = sc
    for host in ("evil.example.com", "evil.example.com:8471", "attacker.test", ""):
        r = client.get("/", headers={"host": host})
        assert r.status_code == 400, host
        assert r.json() == {"error": "invalid host header"}
        # the rejection still carries the air-gap headers (Law 1 on every response)
        assert "Content-Security-Policy" in r.headers


def test_loopback_hosts_are_served(sc) -> None:  # type: ignore[no-untyped-def]
    _st, client = sc
    for host in (
        "127.0.0.1",
        "127.0.0.1:8471",
        "localhost",
        "localhost:8471",
        "[::1]",
        "[::1]:8471",
        "testserver",  # Starlette TestClient's default — single-label, publicly unresolvable
    ):
        assert client.get("/", headers={"host": host}).status_code == 200, host


def test_host_check_covers_posts_and_static(sc) -> None:  # type: ignore[no-untyped-def]
    _st, client = sc
    assert (
        client.post(
            "/session/ram-threshold", data={"gb": "2"}, headers={"host": "evil.example.com"}
        ).status_code
        == 400
    )
    assert client.get("/static/base.css", headers={"host": "evil.example.com"}).status_code == 400
    assert client.get("/static/base.css").status_code == 200


# ── SEC-2: the Origin gate on unsafe methods ──────────────────────────────────────────────────────


def test_cross_site_post_is_refused_and_changes_nothing(sc) -> None:  # type: ignore[no-untyped-def]
    """The Origin FALLBACK path (no Sec-Fetch-Site): a foreign/null Origin is refused."""
    st, client = sc
    before = st.ram_warn_bytes
    for origin in ("https://evil.example.com", "http://evil.example.com:8471", "null"):
        r = client.post("/session/ram-threshold", data={"gb": "7"}, headers={"origin": origin})
        assert r.status_code == 403, origin
        assert r.json() == {"error": "cross-site request refused"}
    assert st.ram_warn_bytes == before  # the CSRF probe changed NOTHING


def test_sec_fetch_site_cross_site_is_refused(sc) -> None:  # type: ignore[no-untyped-def]
    """ADR-0268: Sec-Fetch-Site is the PRIMARY discriminator — a cross-site request is
    refused even if it forges a loopback Origin (it cannot forge Sec-Fetch-Site)."""
    st, client = sc
    before = st.ram_warn_bytes
    for sfs in ("cross-site", "same-site", "cross-origin"):
        r = client.post(
            "/session/ram-threshold",
            data={"gb": "9"},
            headers={"sec-fetch-site": sfs, "origin": "http://127.0.0.1"},
        )
        assert r.status_code == 403, sfs
    assert st.ram_warn_bytes == before


def test_same_origin_form_nav_with_null_origin_passes(sc) -> None:  # type: ignore[no-untyped-def]
    """ADR-0268 regression: a REAL browser POST form navigation under Referrer-Policy:
    no-referrer sends Origin: null WITH Sec-Fetch-Site: same-origin — this is the tool's own
    form and MUST pass (the Origin-only gate refused it, breaking every POST form live)."""
    st, client = sc
    r = client.post(
        "/session/ram-threshold",
        data={"gb": "7"},
        headers={"sec-fetch-site": "same-origin", "origin": "null"},
        follow_redirects=False,
    )
    assert r.status_code == 303  # the same-origin form works despite the null Origin
    assert st.ram_warn_bytes == 7 * 1024**3


def test_sec_fetch_site_none_is_a_user_navigation_and_passes(sc) -> None:  # type: ignore[no-untyped-def]
    """Sec-Fetch-Site: none = a user-initiated top-level navigation (address bar / bookmark),
    not a CSRF vector — allowed."""
    st, client = sc
    r = client.post(
        "/session/ram-threshold",
        data={"gb": "3"},
        headers={"sec-fetch-site": "none"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert st.ram_warn_bytes == 3 * 1024**3


def test_loopback_and_absent_origins_pass(sc) -> None:  # type: ignore[no-untyped-def]
    st, client = sc
    r = client.post(
        "/session/ram-threshold",
        data={"gb": "7"},
        headers={"origin": "http://127.0.0.1:8471"},
        follow_redirects=False,
    )
    assert r.status_code == 303  # the browser's own same-origin POST works
    assert st.ram_warn_bytes == 7 * 1024**3
    r = client.post(
        "/session/ram-threshold", data={"gb": "2"}, follow_redirects=False
    )  # non-browser client: no Origin and no Sec-Fetch-Site at all
    assert r.status_code == 303
    assert st.ram_warn_bytes == 2 * 1024**3


def test_reads_are_never_csrf_gated(sc) -> None:  # type: ignore[no-untyped-def]
    _st, client = sc
    # a GET with a foreign Origin still serves (SOP/CSP govern reads; gating GETs would break
    # same-origin navigations, which omit the header entirely)
    assert client.get("/", headers={"origin": "https://evil.example.com"}).status_code == 200
