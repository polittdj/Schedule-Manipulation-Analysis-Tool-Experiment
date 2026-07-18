"""PR-U1 (operator directives): the per-file banner + switcher on /analysis ("Where We Stand") —
the page names ITS one file and offers a switch; multi-file mixing wording is gone there."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLD = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    for f in ("Project2.mspdi.xml", "Project5.mspdi.xml"):
        c.post("/upload", files={"files": (f, (GOLD / f).read_bytes(), "text/xml")})
    return c


def test_analysis_banner_names_one_file_and_offers_switch(client: TestClient) -> None:
    page = client.get("/analysis/Project5").text
    assert "This page shows ONE file" in page
    assert "switch file" in page and "never mixed here" in page
    # both files are offered; the current one is selected
    assert "Project2" in page and "Project5" in page
    assert "data-sf-navselect" in page  # chrome.js delegates the switch (ADR-0268)


def test_other_pages_keep_the_multi_file_banner(client: TestClient) -> None:
    page = client.get("/trend").text
    assert "loaded files" in page  # the cross-version pages still disclose the aggregate honestly


def test_find_inputs_accept_names_now(client: TestClient) -> None:
    page = client.get("/analysis/Project5").text
    assert 'id=gridFind type=text placeholder="UID or name' in page
    assert client.get("/path").text.count("UID or name") == 1
