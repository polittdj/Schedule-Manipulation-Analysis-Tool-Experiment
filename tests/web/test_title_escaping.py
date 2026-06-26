"""The page ``<title>`` escapes schedule-derived text (audit F-06 / ADR-0130).

``_LAYOUT`` is a bare ``jinja2.Template`` (autoescape OFF, because ``body``/``banner`` are
already-built raw HTML), and the CSP allows ``'unsafe-inline'`` — so HTML-escaping, not CSP, is
the only barrier against reflected XSS through the one untrusted ``title`` value (the schedule
key, which ``_clean_key`` derives from the uploaded filename and does NOT strip HTML
metacharacters). This test uploads a schedule under a hostile filename and asserts the rendered
``<title>`` carries the **escaped** form, with no raw tag — ``_e(title)`` at the boundary holds.
"""

from __future__ import annotations

import re
import urllib.parse
from pathlib import Path

from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "golden"
    / "project2_5"
    / "Project5.mspdi.xml"
)


def test_hostile_schedule_key_is_escaped_in_the_page_title() -> None:
    client = TestClient(create_app(SessionState()))
    payload = "<svg onload=alert(1)>"
    # _clean_key keeps the metacharacters (only the dir + a known extension are stripped),
    # so the schedule key == payload.
    up = client.post(
        "/upload",
        files={"files": (f"{payload}.xml", GOLDEN.read_bytes(), "text/xml")},
    )
    assert up.status_code == 200

    page = client.get(f"/analysis/{urllib.parse.quote(payload)}").text
    match = re.search(r"<title>(.*?)</title>", page, re.S)
    assert match is not None, "no <title> in the rendered page"
    title = match.group(1)
    assert "&lt;svg onload=alert(1)&gt;" in title  # the key is escaped in the title
    assert "<svg" not in title  # and never appears as a raw tag
