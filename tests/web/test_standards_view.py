"""The /standards "Standards & Execution Indices" page (PR-M1): DCMA-14 + the NASA/Acumen-Fuse
execution indices + the SEM family, one formula-first row per metric — re-projection of existing
engine calls only (no new math), with unbuilt SEM rows reading em-dash, never a fabricated 0."""

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


def test_standards_renders_three_families_with_formulas(client: TestClient) -> None:
    page = client.get("/standards").text
    assert "DCMA-14 point assessment" in page
    assert "NASA / Acumen-Fuse execution indices" in page
    assert "Schedule Execution Metrics (SEM)" in page
    # formula-first: the dictionary's verbatim formula + source columns render
    assert "<th scope=col>Formula</th>" in page and "<th scope=col>Source</th>" in page
    assert "DCMA 14-Point Assessment" in page  # a DCMA source citation string
    # the latest file is named as the computation basis
    assert "Project5" in page


def test_standards_sem_rows_are_live_with_golden_values(client: TestClient) -> None:
    # PR-M2: the full SEM family computes live; spot-pin the Fuse-golden values for Project5
    # (prior = Project2): Completed 27, BEI Current 0.67 = 2/3, TC-BEI 1.24, BEI Cumulative 0.59.
    page = client.get("/standards").text
    for label in ("Workoff Burden (SEM01)", "TC-BEI (SEM07)", "FRI Current (SEM08)"):
        assert label in page
    assert "not built" not in page  # every SEM metric now computes
    assert "0.67" in page and "1.24" in page and "0.59" in page


def test_standards_includes_cei_with_two_versions_loaded(client: TestClient) -> None:
    page = client.get("/standards").text
    assert "CEI" in page and "needs" not in page.split("Acumen-Fuse")[1][:400]


def test_standards_single_version_says_cei_needs_prior() -> None:
    c = TestClient(create_app(SessionState()))
    f = "Project5.mspdi.xml"
    c.post("/upload", files={"files": (f, (GOLD / f).read_bytes(), "text/xml")})
    page = c.get("/standards").text
    assert "CEI needs" in page


def test_standards_empty_state_and_nav_entry(client: TestClient) -> None:
    empty = TestClient(create_app(SessionState())).get("/standards")
    assert empty.status_code == 200 and "Load a schedule" in empty.text
    assert "Standards &amp; Execution" in client.get("/groups").text  # SETUP nav entry everywhere
