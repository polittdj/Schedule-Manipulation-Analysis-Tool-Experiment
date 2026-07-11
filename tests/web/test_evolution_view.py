"""Critical-Path Evolution view tests (M18 item 7, ADR-0044)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def _upload(client: TestClient, name: str) -> None:
    data = (GOLDEN / "project2_5" / f"{name}.mspdi.xml").read_bytes()
    assert (
        client.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")}).status_code
        == 200
    )


def test_evolution_needs_two_versions(client: TestClient) -> None:
    assert "at least two analyzable versions" in client.get("/evolution").text
    _upload(client, "Project5")
    assert "at least two analyzable versions" in client.get("/evolution").text
    assert client.get("/api/evolution").status_code == 400


def test_evolution_page_has_stepper_controls(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")
    page = client.get("/evolution").text
    assert "Critical-Path Evolution" in page
    assert "id=prevEvo" in page and "id=nextEvo" in page and "id=evoPlay" in page
    assert "id=evoChart" in page and "/static/path_evolution.js" in page


def test_evolution_tier_selector_and_data_attr(client: TestClient) -> None:
    """Operator: choose the path tier — critical / secondary / tertiary / all."""
    _upload(client, "Project2")
    _upload(client, "Project5")
    page = client.get("/evolution?tier=secondary").text
    assert "name=tier" in page and "Path tier:" in page
    assert '<option value="secondary" selected>' in page
    assert 'data-tier="secondary"' in page  # the JS reads this to fetch the tier path
    # default keeps the float critical-path view (no tier scoping)
    assert 'data-tier="off"' in client.get("/evolution").text


def test_evolution_default_is_unchanged_float_critical_path(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")
    d = client.get("/api/evolution").json()
    assert "snapshots" in d and "tier" not in d  # default payload carries no tier key


def test_evolution_tier_api_classifies_by_driving_slack(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")

    def uids(tier: str) -> set[int]:
        d = client.get(f"/api/evolution?tier={tier}").json()
        assert d["tier"] == tier
        last = d["snapshots"][-1]
        # every row is tagged with its tier and the top-level tier matches the request
        for r in last["critical_rows"]:
            assert r["tier"] in ("driving", "secondary", "tertiary")
        return {r["uid"] for r in last["critical_rows"]}

    crit, sec, ter, all_ = uids("critical"), uids("secondary"), uids("tertiary"), uids("all")
    # the driving (critical) tier and the near-driving tiers are disjoint, and "all" is their union
    assert crit and not (crit & sec) and not (crit & ter)
    assert all_ == crit | sec | ter
    # "all" rows carry all three tier labels
    all_last = client.get("/api/evolution?tier=all").json()["snapshots"][-1]["critical_rows"]
    assert {r["tier"] for r in all_last} == {"driving", "secondary", "tertiary"}


def test_path_evolution_js_wires_the_tier(client: TestClient) -> None:
    js = client.get("/static/path_evolution.js").text
    assert "data-tier" in js and "tier=" in js  # fetch includes the tier
    assert "barClass" in js and "TIER_CLASS" in js  # colour-by-tier in the "all" mode


def test_evolution_page_carries_the_counterfactual_panel(client: TestClient) -> None:
    """The 'what-if' panel reverts the duration/logic/constraint changes that took non-completed
    activities off the path and reports the finish impact (and explains 'gained float')."""
    _upload(client, "Project2")
    _upload(client, "Project5")
    page = client.get("/evolution").text
    assert "What-if: work removed from the critical path" in page
    assert "gained float" in page.lower()  # the explanation the operator asked for
    # the panel still renders with the session target UID set
    client.post("/target", data={"uid": "143", "next_url": "/evolution"})
    assert "What-if: work removed from the critical path" in client.get("/evolution").text


def test_api_evolution_serves_per_version_snapshots(client: TestClient) -> None:
    _upload(client, "Project5")  # load order reversed on purpose
    _upload(client, "Project2")
    data = client.get("/api/evolution").json()
    snaps = data["snapshots"]
    assert [s["label"] for s in snaps] == ["Project2.mspdi.xml", "Project5.mspdi.xml"]
    first, second = snaps
    assert first["finish_delta_days"] is None  # no prior version
    # ADR-0150: effective (stored-flag) critical basis — the Acumen-validated 41/4
    assert len(first["critical"]) == 41 and len(second["critical"]) == 4
    assert second["finish_delta_days"] == 148  # the known P2->P5 slip
    assert len(second["left"]) == 38 and second["entered"] == [131]
    # critical UIDs carry display names; the "left" ones resolve from the prior version
    assert all(str(u) in second["names"] for u in second["critical"])
    assert all(str(u) in second["names"] for u in second["left"])


def test_api_evolution_carries_gantt_geometry_and_reasons(client: TestClient) -> None:
    """M18 follow-up: the evolution data carries per-activity Gantt bars + the entered/left
    attribution (the reason WHY each entered or left the path) + a locked date axis."""
    _upload(client, "Project2")
    _upload(client, "Project5")
    data = client.get("/api/evolution").json()
    assert data["axis"]["min"] and data["axis"]["max"]  # the locked Gantt axis
    second = data["snapshots"][1]
    assert len(second["critical_rows"]) == 4  # one Gantt bar per critical activity
    row = second["critical_rows"][0]
    assert row["start"] and row["finish"] and "entered" in row and "uid" in row
    # the six that LEFT the path each carry a reason and their prior-version bar geometry
    assert len(second["left_rows"]) == 38
    assert {r["reason"] for r in second["left_rows"]} <= {
        "completed",
        "gained_float",
        "logic_removed",
    }
    assert all(r["start"] and r["finish"] for r in second["left_rows"])


def test_api_evolution_reason_detail_is_specific(client: TestClient) -> None:
    """ADR-0057: the entered/left reason detail (the chip hover) is specific — completed cites
    the progress %, and gained_float quantifies the movement vs the project finish."""
    _upload(client, "Project2")
    _upload(client, "Project5")
    left = client.get("/api/evolution").json()["snapshots"][1]["left_rows"]
    assert left
    for r in left:
        assert r["detail"]  # every left activity carries a hover detail
        if r["reason"] == "completed":
            assert "%" in r["detail"]
        if r["reason"] == "gained_float":
            assert "project finish moved" in r["detail"]


def test_evolution_page_describes_gantt_and_reasons(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")
    page = client.get("/evolution").text
    assert "Gantt" in page and "reason chip" in page
    assert "id=evoChart" in page and "/static/path_evolution.js" in page


def test_api_evolution_rows_carry_grid_columns(client: TestClient) -> None:
    """Evolution enhancements: every Gantt row carries its grid columns — % complete,
    duration (working days), and the robust complete flag (ADR-0051) — for both the
    critical rows and the activities that left the path."""
    _upload(client, "Project2")
    _upload(client, "Project5")
    second = client.get("/api/evolution").json()["snapshots"][1]

    for r in second["critical_rows"]:
        assert isinstance(r["percent_complete"], int) and 0 <= r["percent_complete"] <= 100
        assert isinstance(r["duration"], str) and r["duration"].endswith("wd")
        assert isinstance(r["complete"], bool)

    # an activity that LEFT *because it completed* carries the current complete flag (True),
    # even though its grid %/duration read from the prior position where it was still running
    completed = [r for r in second["left_rows"] if r["reason"] == "completed"]
    assert completed, "expected at least one activity that left the path by completing"
    assert all(r["complete"] is True for r in completed)
    assert all(isinstance(r["complete"], bool) for r in second["left_rows"])


def test_evolution_page_has_hide_completed_toggle(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")
    page = client.get("/evolution").text
    assert "id=evoHideDone" in page and "hide completed" in page
    js = client.get("/static/path_evolution.js").text
    # the standard table-Gantt columns (ADR-0187) and the robust hide-completed filter
    assert "hideDone" in js
    assert '"Start"' in js and '"Finish"' in js  # column headers
    assert "r.complete" in js  # filter reads the robust complete flag


def test_evolution_target_focus(client: TestClient) -> None:
    """A ?target=<uid> focuses one activity across every frame: the page prefills the focus
    form + sets data-target, and /api/evolution echoes the target so the JS can highlight it."""
    _upload(client, "Project2")
    _upload(client, "Project5")
    page = client.get("/evolution?target=100").text
    assert 'data-target="100"' in page  # the chart picks it up
    assert 'value="100"' in page  # focus form prefilled
    assert "clear focus" in page
    assert client.get("/api/evolution?target=100").json()["target"] == 100
    # no focus -> echoed as null, and the chart carries an empty data-target
    assert client.get("/api/evolution").json()["target"] is None
    assert 'data-target=""' in client.get("/evolution").text


def test_evolution_has_zoom_controls_and_focus_js(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")
    page = client.get("/evolution").text
    for cid in ("evoZoomIn", "evoZoomOut", "evoZoomReset", "evoPanL", "evoPanR"):
        assert "id=" + cid in page, cid
    js = client.get("/static/path_evolution.js").text
    assert "function zoom(" in js and "function pan(" in js and "resetZoom" in js
    # zoom is pixels-per-day on the LOCKED full axis (ADR-0187 table Gantt); pan scrolls
    assert "fullLo" in js and "fullHi" in js and "attachEdgeExtend" in js
    assert "focusUid" in js and 'getAttribute("data-target")' in js  # focus highlight


def test_api_evolution_path_to_target_is_predecessor_closure(client: TestClient) -> None:
    """Mode 1 (driving path to the focused UID): each snapshot carries path_to_target — the
    focused activity plus its transitive predecessors — so the filter can scope to that chain.
    Empty without a focus; with one it contains the target and is a subset of the version."""
    _upload(client, "Project2")
    _upload(client, "Project5")
    plain = client.get("/api/evolution").json()["snapshots"]
    assert all(s["path_to_target"] == [] for s in plain)  # no focus -> empty

    # focus a real critical UID and confirm the closure includes it and lives in the version
    crit = plain[1]["critical"]
    uid = crit[len(crit) // 2]
    focused = client.get(f"/api/evolution?target={uid}").json()["snapshots"][1]
    closure = focused["path_to_target"]
    assert uid in closure
    all_uids = {r["uid"] for r in focused["critical_rows"]} | {
        r["uid"] for r in focused["left_rows"]
    }
    # the closure is the target + predecessors; the target itself is one of the rendered rows
    assert uid in all_uids and len(closure) >= 1


def test_evolution_page_has_filter_modes(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")
    page = client.get("/evolution").text
    assert "id=evoFilterMode" in page
    for opt in ("driving", "version", "movement", "search"):
        assert f"value={opt}" in page, opt
    assert "id=evoFilterVersion" in page and "id=evoFilterText" in page and "evoMove" in page
    js = client.get("/static/path_evolution.js").text
    # the four filter behaviours are all wired in the client
    assert "function applyFilter" in js
    for token in ("path_to_target", "moveSet", "searchText", "filterVersion"):
        assert token in js, token


def test_evolution_export_xlsx_and_docx(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")
    for fmt in ("xlsx", "docx"):
        resp = client.get(f"/export/{fmt}/evolution")
        assert resp.status_code == 200 and len(resp.content) > 0
    assert client.get("/export/pdf/evolution").status_code == 404


def test_evolution_chapter_04_page_shell(client: TestClient) -> None:
    """ADR-0200 — chapter 04 "How stable is the path": the data-driven takeaway h1, the churn
    KPI strip, and the Latest-critical-path / Total-churn composition bars, all read from the
    evolution the page already computes. The interactive stepper/Gantt scaffold survives beneath."""
    _upload(client, "Project2")
    _upload(client, "Project5")
    page = client.get("/evolution").text

    # data-driven takeaway names the critical path and carries the real churn/slip figures
    assert 'class="page-takeaway"' in page
    assert "critical path" in page
    assert "1 activity entered it and 38 left" in page  # golden P2->P5 churn
    assert "the finish slipped 148 calendar days" in page  # known P2->P5 slip

    # the six-KPI strip and both composition bars
    assert 'class="ws-kpi"' in page and "Versions compared" in page and "Critical now" in page
    assert "Latest critical path" in page and "Total churn" in page
    assert 'class="stack-bar"' in page

    # chapter chrome fires here (kicker + Continue -> chapter 05)
    assert "CHAPTER 04 · HOW STABLE IS THE PATH" in page
    assert "Chapter 05" in page

    # the interactive evolution scaffold is untouched beneath the header
    assert "id=prevEvo" in page and "id=evoChart" in page
    assert "/static/path_evolution.js" in page


def test_dashboard_and_nav_link_evolution(client: TestClient) -> None:
    # nav links it unconditionally; the dashboard body row appears with >= 2 versions
    _upload(client, "Project2")
    home = client.get("/").text
    assert 'href="/evolution"' in home  # nav — chapter 04 "How stable is the path" (ADR-0196)
    assert "Critical-path evolution &rarr;" not in home  # body row not yet (one version)
    _upload(client, "Project5")
    assert "Critical-path evolution &rarr;" in client.get("/").text
