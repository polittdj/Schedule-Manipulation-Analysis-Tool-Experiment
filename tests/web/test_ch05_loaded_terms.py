"""The Chapter-05 prose this round introduces asserts nothing the engine did not (rank 9).

The panel contract lets a converted page add *presentation* prose — a story takeaway, a lede,
one ``.sf-take`` per panel. That prose is a testimony-context liability if it slips in an
accusatory/intent word the engine never asserted, which is exactly what
``ai.citations.introduces_loaded_terms`` guards for the AI paths (ADR-0132, audit H2). Here the
same gate is run over the SERVER-authored headline/lede/takeaway strings of /trend, /curves and
/scurve, harvested from the real rendered pages so a future edit is audited automatically.

A control string is checked in the SAME run: a gate that cannot fail proves nothing.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.ai.citations import introduces_loaded_terms
from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"

#: the presentation prose this round owns, as it is emitted
_PATTERNS = (
    re.compile(r"<p class=sf-take data-no-i18n>(.*?)</p>", re.S),
    re.compile(r'<h1 class="page-takeaway" data-no-i18n>(.*?)</h1>', re.S),
    re.compile(r'<p class="page-lede">(.*?)</p>', re.S),
)


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    for name in ("Project2", "Project5"):
        data = (GOLDEN / "project2_5" / f"{name}.mspdi.xml").read_bytes()
        assert (
            c.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")}).status_code
            == 200
        )
    return c


def _prose(page: str) -> list[str]:
    out: list[str] = []
    for pat in _PATTERNS:
        for raw in pat.findall(page):
            text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
            out.append(" ".join(text.split()))
    return out


def test_control_proves_the_gate_can_fail() -> None:
    """The audit below is only evidence if the same call flags a genuinely loaded string."""
    assert introduces_loaded_terms("", "deliberate concealed fraud") is True
    assert introduces_loaded_terms("", "The finish moved 148 calendar days later.") is False


@pytest.mark.parametrize("route", ["/trend", "/curves", "/scurve"])
def test_chapter05_presentation_prose_introduces_no_loaded_terms(
    client: TestClient, route: str
) -> None:
    strings = _prose(client.get(route).text)
    assert strings, f"no takeaway/lede/take harvested from {route} — the audit would be vacuous"
    for text in strings:
        assert introduces_loaded_terms("", text) is False, (route, text)


def test_the_audit_actually_covers_this_round_s_new_strings(client: TestClient) -> None:
    """Guards the harvest itself: the exact new lines must be among the audited strings."""
    harvested = {
        s for route in ("/trend", "/curves", "/scurve") for s in _prose(client.get(route).text)
    }
    joined = " || ".join(sorted(harvested))
    for fragment in (
        "Across 2 versions the Net Finish Impact is",  # /trend version-table take
        "Every chart plots the same 2 versions on a locked axis",  # /trend charts take
        "schedule-quality metrics stepped across 2 versions",  # /trend quality drill take
        "manipulation-trend signals across 1 consecutive-version step",  # /trend signals take
        "Total against effective margin across 2 submissions",  # /trend margin take
        "versions of finish and start months on one shared",  # /curves h1
        "Where finishes were promised against where they actually land",  # /curves lede
        "baselined finish months against actual or scheduled finish months",  # /curves take
        "of the work has finished against",  # /scurve h1
        "How much of the work has actually completed",  # /scurve lede
        "finished against 38% planned at its data date",  # /scurve take
    ):
        assert fragment in joined, fragment
