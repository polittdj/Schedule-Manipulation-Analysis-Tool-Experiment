"""Static-asset freshness: version-busted URLs + always-revalidate headers (ADR-0148).

The operator's deployed install serves a FIXED port, so the browser's HTTP cache origin
persists across upgrades. Starlette's ``StaticFiles`` sends ETag/Last-Modified but **no
Cache-Control**, so browsers apply *heuristic* freshness and can keep executing a stale
cached JS for days after the server was upgraded — which is exactly how the PR #284 overlay
fix appeared "not fixed" on the operator's machine. Two belts:

1. every rendered page references its static assets as ``/static/<name>?v=<version>`` — a new
   release mints new URLs, so an old cache entry can never satisfy them;
2. ``/static/*`` responses carry ``Cache-Control: no-cache`` — stored copies must revalidate
   (cheap 304s), so even a same-URL fetch can't ride heuristic freshness.
"""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from schedule_forensics.web.app import _ASSET_VERSION, SessionState, create_app


def _client() -> TestClient:
    return TestClient(create_app(SessionState()))


def test_pages_reference_version_busted_static_urls() -> None:
    page = _client().get("/").text
    refs = re.findall(r"""(?:src|href)\s*=\s*["'](/static/[^"']+)["']""", page)
    assert refs, "no static references found on the dashboard"
    unbusted = [r for r in refs if f"?v={_ASSET_VERSION}" not in r]
    assert not unbusted, f"static URLs missing the ?v= cache-buster: {unbusted}"


def test_home_js_specifically_is_busted() -> None:
    # the asset whose staleness reproduced the stuck loading overlay
    assert f'src="/static/home.js?v={_ASSET_VERSION}"' in _client().get("/").text


def test_static_responses_always_revalidate() -> None:
    c = _client()
    for asset in ("home.js", "base.css", "app.js", "sf-themes.css"):
        r = c.get(f"/static/{asset}")
        assert r.status_code == 200
        assert r.headers.get("cache-control") == "no-cache", asset


def test_version_query_does_not_break_static_serving() -> None:
    # StaticFiles resolves by path; the ?v= query must be ignored server-side
    r = _client().get(f"/static/home.js?v={_ASSET_VERSION}")
    assert r.status_code == 200
    assert "pageshow" in r.text  # and it serves the CURRENT (overlay-fix) source
