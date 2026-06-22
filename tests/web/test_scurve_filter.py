"""S-Curve per-chart filter — scope the visual by up to 5 fields of the parent file.

Operator request: filter visuals such as the S-Curve by up to 5 of any of the fields in the
parent file (independent of the page-wide Groups & Filters). Implemented over the grouping
engine's filter_schedule, so the chart re-computes on the matching activities."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.engine.grouping import available_fields_union, distinct_values
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.web.app import SessionState, create_app

GOLDEN = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "golden"
    / "project2_5"
    / "Project5.mspdi.xml"
)


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    c.post("/upload", files={"files": ("Project5.mspdi.xml", GOLDEN.read_bytes(), "text/xml")})
    return c


def _field_value(sch: Schedule) -> tuple[str, str]:
    field = next(f for f in available_fields_union([sch]) if distinct_values([sch], f))
    return field, distinct_values([sch], field)[0]


def test_scurve_page_embeds_filter_fields_and_ui(client: TestClient) -> None:
    page = client.get("/scurve").text
    assert "window.SF_SCURVE_FIELDS" in page
    assert "id=scurveFilter" in page
    assert "Filter this chart by up to" in page
    assert "/static/scurve.js" in page


def test_scurve_js_builds_the_filter(client: TestClient) -> None:
    js = client.get("/static/scurve.js").text
    assert "SF_SCURVE_FIELDS" in js and "buildFilterUI" in js and "cf=" in js


def test_scurve_api_unfiltered_has_versions(client: TestClient) -> None:
    assert client.get("/api/scurve").json()["versions"]


def test_scurve_filter_narrows_population(client: TestClient, golden_project5: Schedule) -> None:
    field, value = _field_value(golden_project5)
    base = client.get("/api/scurve").json()
    filt = client.get("/api/scurve", params={"cf": field, "cv": value}).json()
    base_total = sum(v["activities"] for v in base["versions"])
    filt_total = sum(v["activities"] for v in filt["versions"])
    assert 0 <= filt_total <= base_total


def test_scurve_filter_recomputes_to_the_matching_population(
    client: TestClient, golden_project5: Schedule
) -> None:
    """Regression (cf/cv aliasing): cf and cv must be parsed as INDEPENDENT query params. A prior
    bug shared one FastAPI ``Query`` instance across both, so cv silently read cf's value — every
    real filter became the nonsense criterion ``(field, field)``, matched nothing, and the chart
    collapsed to empty instead of recomputing. The filtered population must equal the engine's own
    ``filter_schedule`` selection (and be non-empty for a genuine value)."""
    from schedule_forensics.engine.grouping import filter_schedule
    from schedule_forensics.web.app import non_summary

    # pick a real (field, value) whose matching subset actually carries finish dates to plot
    field = value = None
    for f in available_fields_union([golden_project5]):
        for v in distinct_values([golden_project5], f):
            tasks = non_summary(filter_schedule(golden_project5, [(f, v)]))
            if tasks and any(t.finish or t.baseline_finish for t in tasks):
                field, value = f, v
                break
        if field is not None:
            break
    assert field is not None
    expected = len(non_summary(filter_schedule(golden_project5, [(field, value)])))
    assert expected > 0
    d = client.get("/api/scurve", params={"cf": field, "cv": value}).json()
    assert d["versions"], "a genuine filter value must recompute, not collapse the chart"
    assert sum(v["activities"] for v in d["versions"]) == expected


def test_scurve_unknown_field_is_ignored(client: TestClient) -> None:
    base = client.get("/api/scurve").json()
    same = client.get("/api/scurve", params={"cf": "__nope__", "cv": "x"}).json()
    assert sum(v["activities"] for v in same["versions"]) == sum(
        v["activities"] for v in base["versions"]
    )


def test_scurve_filter_with_no_match_returns_empty(
    client: TestClient, golden_project5: Schedule
) -> None:
    field, _ = _field_value(golden_project5)
    d = client.get("/api/scurve", params={"cf": field, "cv": "__nonexistent_value__"}).json()
    assert d["versions"] == []


def test_scurve_has_auto_ai_interpretation(client: TestClient) -> None:
    """A grounded, always-present interpretation of the trend renders without asking."""
    page = client.get("/scurve").text
    assert "<h2>AI interpretation</h2>" in page
    assert "Auto-generated" in page
