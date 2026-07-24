"""Loopback Host allowlist + cross-origin mutation gate (ADR-0257, audit SEC-2/SEC-3).

The DNS-rebinding read vector dies at the Host check (a rebound page's browser sends the
ATTACKER'S hostname as Host → 421 before any route runs); cross-site POSTs die at the Origin
gate (modern browsers always attach Origin cross-site → 403, session state proven untouched).
Same-origin operation is unchanged: loopback Hosts on any port pass, absent Origin passes
(curl/TestClient/legacy same-origin form posts), loopback Origins pass, and reads are ungated
(browser same-origin policy + CSP already prevent cross-origin response reading).
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app


def _client() -> tuple[SessionState, TestClient]:
    st = SessionState()
    return st, TestClient(create_app(st))


def test_foreign_host_is_refused_before_any_route() -> None:
    _st, c = _client()
    for path in ("/", "/api/margin/dashboard", "/margin"):
        r = c.get(path, headers={"host": "evil.example.com"})
        assert r.status_code == 421
        assert "loopback" in r.text
        # the rejection still carries the security headers (Law 1)
        assert "Content-Security-Policy" in r.headers


def test_loopback_hosts_pass_on_any_port() -> None:
    _st, c = _client()
    for host in ("127.0.0.1", "127.0.0.1:8000", "localhost:9411", "[::1]:8000", "testserver"):
        assert c.get("/", headers={"host": host}).status_code == 200


def test_empty_host_is_refused() -> None:
    _st, c = _client()
    assert c.get("/", headers={"host": ""}).status_code == 421


def test_cross_origin_post_is_refused_and_state_untouched() -> None:
    st, c = _client()
    for origin in ("https://evil.example.com", "null"):
        r = c.post("/role", data={"role": "pm"}, headers={"origin": origin})
        assert r.status_code == 403
        assert st.role is None  # the mutation never ran
    r2 = c.post(
        "/margin/band",
        data={"action": "apply", "phase0": "2026-01-01"},
        headers={"origin": "http://attacker.test"},
    )
    assert r2.status_code == 403
    assert st.margin_band_dates is None


def test_loopback_and_absent_origins_mutate_normally() -> None:
    st, c = _client()
    # absent Origin (curl / TestClient / legacy same-origin form post)
    assert c.post("/role", data={"role": "pm"}, follow_redirects=False).status_code == 303
    assert st.role == "pm"
    # explicit loopback Origins (modern browser same-origin fetch/form)
    for origin in ("http://127.0.0.1:8000", "http://localhost:9411"):
        r = c.post(
            "/role", data={"role": "analyst"}, headers={"origin": origin}, follow_redirects=False
        )
        assert r.status_code == 303
    assert st.role == "analyst"


def test_reads_are_ungated_by_origin() -> None:
    # response-reading cross-origin is the browser's job (SOP + CSP); the server gate covers
    # MUTATIONS only — a hostile Origin on a GET must not break same-origin embedding edge cases
    _st, c = _client()
    assert c.get("/", headers={"origin": "https://evil.example.com"}).status_code == 200
