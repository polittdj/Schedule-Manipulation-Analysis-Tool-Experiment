"""Air-gap guarantee (§6.A / Law 1) — nothing the UI serves points off the local machine.

Scans every served HTML page and every static asset for external references (absolute
http(s):// URLs and protocol-relative //host references). Only loopback and same-origin
relative paths are allowed — so the dashboard can never pull a CDN/script/style/font from a
remote host (no CUI-leaking beacon, no offline breakage).

Coverage is ENUMERATED, not hand-listed (audit L5): the page walk iterates every GET route
on the live ``app.routes`` table and the asset walk iterates every vendored file in the
static directory on disk — a new page or asset is scanned the moment it exists, with no
list to forget to update.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.datastructures import DefaultPlaceholder
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from schedule_forensics.web.app import _STATIC_DIR, SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"

_ABSOLUTE_URL = re.compile(r"""\bhttps?://[^\s"'<>)]+""", re.IGNORECASE)
_PROTOCOL_RELATIVE = re.compile(r"""["'(]//[^\s"'<>)]+""")
_REMOTE_ASSET = re.compile(r"""(?:src|href)\s*=\s*["'](?!/|#|data:)[^"']*//""", re.IGNORECASE)
_LOOPBACK = ("127.0.0.1", "localhost")

#: Fillers for path parameters when walking ``app.routes``. ``name`` is the schedule the
#: fixture uploads; ``fmt`` exercises the export routes (binary responses are skipped by
#: content-type below). A NEW parameter name fails the walk loudly — add a filler
#: consciously so the new route family is really being scanned.
_PARAM_FILLERS = {"name": "Project5", "fmt": "xlsx"}

#: Content types the browser renders/executes — these MUST be free of external references.
#: Binary downloads (xlsx/docx/ico) are excluded: they are saved files, not browser-fetched
#: content, and OOXML legitimately embeds schema-namespace URIs that are never dereferenced.
_SCANNED_CONTENT_TYPES = (
    "text/html",
    "text/css",
    "text/javascript",
    "application/javascript",
    "application/json",
    "text/plain",
)

#: Pages the 2026-07-13 audit found missing from the old hand-kept list, plus the core
#: pages it did cover. The enumeration must yield AT LEAST these — if a refactor made the
#: route walk come back empty or partial, this fails instead of silently scanning nothing.
_MUST_ENUMERATE = {
    "/",
    "/analysis/{name}",
    "/brief",
    "/briefing",
    "/compare",
    "/curves",
    "/evm",
    "/evolution",
    "/forecast",
    "/groups",
    "/help",
    "/integrity",
    "/mission",
    "/path",
    "/performance",
    "/portfolio",
    "/risks",
    "/scurve",
    "/settings",
    "/sra",
    "/standards",
    "/volatility",
    "/wbs/{name}",
    "/workbench",
}


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


def _get_route_paths(client: TestClient) -> list[tuple[str, bool]]:
    """Every GET route as (concrete path, declares-HTML) — params filled or fail loudly."""
    walked: list[tuple[str, bool]] = []
    for route in client.app.routes:  # type: ignore[union-attr]
        if not isinstance(route, APIRoute) or "GET" not in route.methods:
            continue
        path = route.path
        for param in re.findall(r"{(\w+)[^}]*}", path):
            filler = _PARAM_FILLERS.get(param)
            assert filler is not None, (
                f"route {route.path} has path parameter {{{param}}} with no filler — "
                "add it to _PARAM_FILLERS so the air-gap walk really scans this route"
            )
            path = re.sub(r"{" + param + r"[^}]*}", filler, path)
        declared = route.response_class
        is_html = not isinstance(declared, DefaultPlaceholder) and issubclass(
            declared, HTMLResponse
        )
        walked.append((path, is_html))
    return walked


def test_every_get_route_serves_no_external_reference(client: TestClient) -> None:
    """Walk the live route table: every GET response the browser would render is scanned."""
    routes = _get_route_paths(client)
    enumerated = {r.path for r in client.app.routes if isinstance(r, APIRoute)}  # type: ignore[union-attr]
    missing = _MUST_ENUMERATE - enumerated
    assert not missing, f"route enumeration lost known pages: {sorted(missing)}"

    offenders: dict[str, list[str]] = {}
    broken: dict[str, int] = {}
    for path, is_html in routes:
        response = client.get(path)
        if response.status_code >= 500 or (is_html and response.status_code != 200):
            # A page that errors instead of rendering would "pass" the scan vacuously —
            # surface it as a failure of the walk itself.
            broken[path] = response.status_code
            continue
        content_type = response.headers.get("content-type", "")
        if not content_type.startswith(_SCANNED_CONTENT_TYPES):
            continue  # binary download (xlsx/docx/ico): saved, not rendered
        refs = _external_refs(response.text)
        if refs:
            offenders[path] = refs
    assert not broken, f"air-gap walk could not render these routes: {broken}"
    assert not offenders, f"air-gap violated — external references served: {offenders}"


def test_every_vendored_static_asset_is_clean(client: TestClient) -> None:
    """Walk the static directory on disk: every vendored JS/CSS file must serve and scan
    clean — including files no page happens to reference yet."""
    assets = sorted(p.name for p in _STATIC_DIR.iterdir() if p.suffix in {".js", ".css"})
    assert len(assets) >= 50, f"static enumeration looks broken — only found {assets}"
    offenders: dict[str, list[str]] = {}
    for name in assets:
        response = client.get(f"/static/{name}")
        assert response.status_code == 200, f"/static/{name} failed to serve"
        refs = _external_refs(response.text)
        if refs:
            offenders[name] = refs
    assert not offenders, f"air-gap violated — external references in assets: {offenders}"


def test_security_headers_enforce_the_airgap_in_the_browser(client: TestClient) -> None:
    """A7: a Content-Security-Policy enforces the no-remote-asset air-gap in EVERY browser at
    runtime (not just the scan above), plus nosniff / no-referrer / frame-deny hardening."""
    for path in ("/", "/analysis/Project5", "/settings", "/static/app.js", "/static/base.css"):
        r = client.get(path)
        csp = r.headers.get("Content-Security-Policy", "")
        # the air-gap-critical directives: nothing loads or connects off-origin
        assert "default-src 'self'" in csp, path
        assert "connect-src 'self'" in csp and "frame-ancestors 'none'" in csp, path
        assert r.headers.get("X-Content-Type-Options") == "nosniff", path
        assert r.headers.get("X-Frame-Options") == "DENY", path
        assert r.headers.get("Referrer-Policy") == "no-referrer", path


def test_assets_are_local_relative(client: TestClient) -> None:
    page = client.get("/analysis/Project5").text
    # the only script/style references are same-origin /static paths
    assets = re.findall(r"""(?:src|href)\s*=\s*["']([^"']+)["']""", page)
    # cache-busting appends ?v=<version> (ADR-0148); strip the query before classifying
    asset_refs = [a for a in assets if a.split("?", 1)[0].endswith((".js", ".css"))]
    assert asset_refs and all(a.startswith("/static/") for a in asset_refs)
