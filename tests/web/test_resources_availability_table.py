"""/resources on a file whose resources carry availability tables (ADR-0506, R-63): the roster's
Max units is the row at the status date and the histogram's capacity follows the table per bucket —
rendered through the real app on the Hard_File_updated3 golden, whose converter scalars are the
07-09 clock's rows (1 / 0.5 / 0.25) and whose status date (10-12) sits in later rows."""

from __future__ import annotations

import gzip
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "golden"
    / "fuse_hardfile"
    / "Hard_File_updated3.mspdi.xml.gz"
)


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    data = gzip.decompress(GOLDEN.read_bytes())
    r = c.post("/upload", files={"files": ("Hard_File_updated3.mspdi.xml", data, "text/xml")})
    assert r.status_code == 200
    return c


def _roster_row(html: str, name: str) -> str:
    m = re.search(rf"<tr><td>{re.escape(name)}</td>(.*?)</tr>", html, re.S)
    assert m is not None, f"{name} missing from the roster"
    return m.group(1)


def test_the_roster_shows_the_tables_row_at_the_status_date(client: TestClient) -> None:
    html = client.get("/resources").text
    # Customer Service Team: 1 through 08-01, 2 from 08-02; status date 10-12 → 2 (scalar 1)
    assert _roster_row(html, "Customer Service Team").startswith(
        "<td>Work</td><td class=num>2</td>"
    )
    # Logistics: 0.25 / 1 / 0.5 in three rows; status date 10-12 → 0.5 (scalar 0.25)
    assert _roster_row(html, "Logistics").startswith("<td>Work</td><td class=num>0.5</td>")
    assert "at the status date" in html  # the roster footnote names the basis


def test_the_payloads_daily_capacity_follows_the_table(client: TestClient) -> None:
    """The chart's per-bucket capacity (days) on the day bucket: one unit-day before 08-02, two
    from 08-02, for the resource whose table changes there."""
    html = client.get("/resources?bucket=day").text
    m = re.search(r'<script type="application/json" id=resData>(.*?)</script>', html, re.S)
    assert m is not None
    payload = json.loads(m.group(1))
    team = next(r for r in payload["resources"] if r["id"] == 1)
    assert team["max_units"] == 2
    caps_before = {p["cap"] for p in team["series"] if p["period"] < "2026-08-02"}
    caps_after = {p["cap"] for p in team["series"] if p["period"] >= "2026-08-02"}
    assert caps_before == {1.0} and caps_after == {2.0}
