"""Strict script-src CSP (ADR-0268) — the tracked follow-up the CSP comment recorded.

``script-src 'unsafe-inline'`` existed only because page chrome carried inline handlers and
inline ``window.SF_*`` boot scripts. Both classes are eliminated: handlers become delegated
listeners in the always-loaded ``chrome.js`` (marked by ``data-sf-*`` attributes), and every
boot payload becomes a non-executable ``<script type="application/json">`` block its consumer
parses. ``script-src`` then tightens to ``'self'`` — an injected inline ``<script>`` or
``on*=`` handler can no longer execute even if markup escaping ever failed (defense in
depth for a tool that renders opposing-party file content). ``style-src`` keeps
``'unsafe-inline'`` (the Gantt's legitimate inline px widths — unchanged scope).
"""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

_NS = 'xmlns="http://schemas.microsoft.com/project"'


def _mspdi(title: str, status: str) -> bytes:
    return (
        f"<Project {_NS}><StartDate>2025-01-06T08:00:00</StartDate>"
        f"<Title>{title}</Title><StatusDate>{status}</StatusDate>"
        "<Tasks><Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration>"
        "<Start>2025-01-06T08:00:00</Start><Finish>2025-01-06T17:00:00</Finish></Task>"
        "<Task><UID>2</UID><Name>Schedule Margin</Name><Duration>PT16H0M0S</Duration>"
        "<Start>2025-01-07T08:00:00</Start><Finish>2025-01-08T17:00:00</Finish>"
        "<PredecessorLink><PredecessorUID>1</PredecessorUID><Type>1</Type></PredecessorLink>"
        "</Task></Tasks></Project>"
    ).encode()


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    c.post(
        "/upload",
        files=[
            ("files", ("a1.xml", _mspdi("Alpha", "2025-01-10T00:00:00"), "text/xml")),
            ("files", ("a2.xml", _mspdi("Alpha", "2025-02-10T00:00:00"), "text/xml")),
        ],
    )
    return c


#: every page family that historically carried an inline handler or boot script, plus the
#: heavy chrome pages — the sweep population for the no-inline-script assertions
_PAGES = (
    "/",
    "/mission",
    "/portfolio",
    "/margin",
    "/cei",
    "/scurve",
    "/ribbon",
    "/sra",
    "/resources",
    "/trend",
    "/evolution",
    "/performance",
    "/groups",
    "/settings",
    "/driving-path",
    "/path",
    "/briefing",
)

_HANDLER_RE = re.compile(r"<[^>]+\son[a-z]+=", re.IGNORECASE)
_SCRIPT_RE = re.compile(r"<script\b([^>]*)>", re.IGNORECASE)


def test_csp_script_src_is_strict(client: TestClient) -> None:
    csp = client.get("/").headers["Content-Security-Policy"]
    assert "script-src 'self'" in csp
    m = re.search(r"script-src ([^;]*)", csp)
    assert m is not None and "unsafe-inline" not in m.group(1)
    # style-src keeps its documented allowance — scope unchanged
    m = re.search(r"style-src ([^;]*)", csp)
    assert m is not None and "unsafe-inline" in m.group(1)


def test_no_inline_event_handlers_anywhere(client: TestClient) -> None:
    for page in _PAGES:
        html = client.get(page).text
        hits = _HANDLER_RE.findall(html)
        assert not hits, (page, hits[:3])


def test_every_inline_script_is_a_json_data_block(client: TestClient) -> None:
    """A <script> without src must be non-executable (type="application/json") — the strict
    CSP blocks executable inline scripts, so any left behind would silently dead-code."""
    for page in _PAGES:
        html = client.get(page).text
        for attrs in _SCRIPT_RE.findall(html):
            if "src=" in attrs:
                continue
            assert 'type="application/json"' in attrs, (page, attrs)


def test_chrome_delegates_the_former_inline_handlers(client: TestClient) -> None:
    home = client.get("/").text
    assert "/static/chrome.js" in home  # the delegate ships on every page
    assert 'data-sf-confirm="Wipe all loaded schedules?"' in home
    assert "id=sfQuitLink" in home
    js = client.get("/static/chrome.js").text
    for marker in (
        "data-sf-autosubmit",
        "data-sf-navselect",
        "data-sf-nexturl-submit",
        "data-sf-confirm",
        "sfQuitLink",
    ):
        assert marker in js, marker


def test_boot_payloads_still_reach_their_consumers(client: TestClient) -> None:
    """The JSON boot blocks exist and each consumer script parses its block by id."""
    assert 'id=sfI18nBoot type="application/json"' in client.get("/").text
    assert 'id=sfScurveFields type="application/json"' in client.get("/scurve").text
    assert 'id=sfRibbonDrillData type="application/json"' in client.get("/ribbon").text
    sra = client.get("/sra").text
    assert 'id=sfRemainDays type="application/json"' in sra
    assert 'id=sfFieldHelp type="application/json"' in sra
    for js_file, block_id in (
        ("translate.js", "sfI18nBoot"),
        ("scurve.js", "sfScurveFields"),
        ("ribbon_drill.js", "sfRibbonDrillData"),
        ("sra_ssi.js", "sfFieldHelp"),
    ):
        assert block_id in client.get(f"/static/{js_file}").text, js_file
