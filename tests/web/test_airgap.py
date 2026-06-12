"""Air-gap guarantee (§6.A / Law 1) — nothing the UI serves points off the local machine.

Scans every served HTML page and every static asset for external references (absolute
http(s):// URLs and protocol-relative //host references). Only loopback and same-origin
relative paths are allowed — so the dashboard can never pull a CDN/script/style/font from a
remote host (no CUI-leaking beacon, no offline breakage).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"

_ABSOLUTE_URL = re.compile(r"""\bhttps?://[^\s"'<>)]+""", re.IGNORECASE)
_PROTOCOL_RELATIVE = re.compile(r"""["'(]//[^\s"'<>)]+""")
_REMOTE_ASSET = re.compile(r"""(?:src|href)\s*=\s*["'](?!/|#|data:)[^"']*//""", re.IGNORECASE)
_LOOPBACK = ("127.0.0.1", "localhost")


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    data = (GOLDEN / "project2_5" / "Project5.mspdi.xml").read_bytes()
    c.post("/upload", files={"files": ("Project5.mspdi.xml", data, "text/xml")})
    return c


def _external_refs(text: str) -> list[str]:
    # W3C XML namespace URIs (e.g. createElementNS's "http://www.w3.org/2000/svg") are
    # identifiers compared by string value — the browser never dereferences them.
    found = [
        u
        for u in _ABSOLUTE_URL.findall(text)
        if not any(h in u for h in _LOOPBACK) and not u.startswith("http://www.w3.org/")
    ]
    found += _PROTOCOL_RELATIVE.findall(text)
    found += _REMOTE_ASSET.findall(text)
    return found


def test_no_external_references_anywhere(client: TestClient) -> None:
    pages = [
        "/",
        "/analysis/Project5",
        "/briefing",
        "/settings",
        "/help",
        "/static/app.js",
        "/static/app.css",
        "/static/base.css",
        "/static/home.js",
        "/static/heartbeat.js",
        "/static/trend.js",
        "/static/cei.js",
        "/static/theme.js",
        "/static/path.js",
        "/static/ask.js",
    ]
    offenders: dict[str, list[str]] = {}
    for path in pages:
        refs = _external_refs(client.get(path).text)
        if refs:
            offenders[path] = refs
    assert not offenders, f"air-gap violated — external references served: {offenders}"


def test_assets_are_local_relative(client: TestClient) -> None:
    page = client.get("/analysis/Project5").text
    # the only script/style references are same-origin /static paths
    assets = re.findall(r"""(?:src|href)\s*=\s*["']([^"']+)["']""", page)
    asset_refs = [a for a in assets if a.endswith((".js", ".css"))]
    assert asset_refs and all(a.startswith("/static/") for a in asset_refs)
