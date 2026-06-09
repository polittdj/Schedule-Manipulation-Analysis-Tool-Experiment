"""Import-feedback tests — the dashboard tells you what loaded and what failed (no silent fail)."""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

EXAMPLE = (
    Path(__file__).resolve().parents[2] / "src/schedule_forensics/web/examples/house_build.json"
)
warnings.filterwarnings("ignore", category=DeprecationWarning, module="starlette.*")


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def test_single_good_file_opens_its_report(client: TestClient) -> None:
    r = client.post(
        "/upload",
        files={"files": ("plan.json", EXAMPLE.read_bytes(), "application/json")},
        follow_redirects=False,
    )
    assert r.status_code == 303 and r.headers["location"].startswith("/analysis/")


def test_bad_file_shows_a_named_error_notice(client: TestClient) -> None:
    r = client.post(
        "/upload",
        files={"files": ("broken.json", b"{ not json", "application/json")},
        follow_redirects=False,
    )
    assert r.status_code == 303 and r.headers["location"] == "/"  # back to the dashboard
    home = client.get("/").text
    assert "Could not import" in home and "broken.json" in home  # explicit, named failure
    assert client.get("/healthz").json()["loaded"] == 0  # nothing loaded


def test_mixed_batch_reports_both_outcomes(client: TestClient) -> None:
    client.post(
        "/upload",
        files=[
            ("files", ("ok.json", EXAMPLE.read_bytes(), "application/json")),
            ("files", ("bad.xer", b"not-a-schedule", "application/json")),
        ],
        follow_redirects=False,
    )
    home = client.get("/").text
    assert "Loaded 1" in home  # the success notice
    assert "Could not import" in home and "bad.xer" in home  # the failure notice


def test_flash_is_one_shot(client: TestClient) -> None:
    client.post(
        "/upload",
        files={"files": ("broken.json", b"oops", "application/json")},
        follow_redirects=False,
    )
    assert "Could not import" in client.get("/").text  # shown once
    assert "Could not import" not in client.get("/").text  # cleared on the next view
