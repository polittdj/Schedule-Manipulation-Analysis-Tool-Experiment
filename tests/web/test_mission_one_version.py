"""/mission 1-version tile degrade (ADR-0258 known pre-existing defect; handoff NEXT #1).

With one loaded version, the wall's multi-version tiles (Bow Wave/CEI, Critical-Path
Evolution, Quality Offenders, Quality Trend) used to render their chart hosts anyway; the
chart scripts then fetched /api/cei · /api/trend · /api/evolution, which legitimately 400
below two versions — filling the browser console with 4xx noise and leaving dead tiles.
The fix degrades those tiles SERVER-SIDE to a "needs at least two versions" note (no chart
host ⇒ the dedicated-page scripts early-return ⇒ zero fetches, zero console noise), while
every tile whose API genuinely supports one version (S-Curve, Forecast Drift, the three
curves charts) keeps rendering.

Also pinned here: the /api/cei population guard must count the ACTIVE population
(st.ordered(), ADR-0258 — no cross-project mixing), not the whole-session file dict; with
two single-version Projects loaded, CEI has one snapshot to show, and pretending otherwise
served a cross-project count as the gate.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

_NS = 'xmlns="http://schemas.microsoft.com/project"'


def _mspdi(title: str, status: str) -> bytes:
    """A minimal, CPM-solvable MSPDI document with a <Title>, <StatusDate>, dated tasks, and
    one FS link — dated so the stored-date views (bow wave) have a real month axis."""
    return (
        f"<Project {_NS}><StartDate>2025-01-06T08:00:00</StartDate>"
        f"<Title>{title}</Title><StatusDate>{status}</StatusDate>"
        "<Tasks><Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration>"
        "<Start>2025-01-06T08:00:00</Start><Finish>2025-01-06T17:00:00</Finish></Task>"
        "<Task><UID>2</UID><Name>B</Name><Duration>PT16H0M0S</Duration>"
        "<Start>2025-01-07T08:00:00</Start><Finish>2025-01-08T17:00:00</Finish>"
        "<PredecessorLink><PredecessorUID>1</PredecessorUID><Type>1</Type></PredecessorLink>"
        "</Task></Tasks></Project>"
    ).encode()


@pytest.fixture
def sc() -> tuple[SessionState, TestClient]:
    st = SessionState()
    return st, TestClient(create_app(st))


def _upload(client: TestClient, *files: tuple[str, bytes]) -> None:
    client.post(
        "/upload",
        files=[("files", (name, data, "text/xml")) for name, data in files],
    )


# ── the defect: one loaded version ────────────────────────────────────────────────────────────────


def test_mission_one_version_degrades_the_multiversion_tiles(sc) -> None:  # type: ignore[no-untyped-def]
    """With ONE version, the four cross-version tiles carry a degrade note and NO chart host —
    so their scripts never fetch the ≥2-version APIs and the console stays clean."""
    _st, client = sc
    _upload(client, ("a1.xml", _mspdi("Alpha", "2025-01-10T00:00:00")))
    html = client.get("/mission").text
    # the four multi-version chart hosts must be gone (script early-return = no fetch)
    for host in ("id=ceiChart", "id=evoChart", "id=qualBars", "id=trendCharts"):
        assert host not in html
    # their steppers go with them (dead controls would imply an animation that cannot run)
    for ctl in ("id=autoPlay", "id=evoPlay", "id=qualPlay"):
        assert ctl not in html
    # each degraded tile says WHY, and still links out to its dedicated page
    assert html.count("Needs at least two") >= 4
    # the single-version-capable tiles keep their charts
    for host in (
        "id=scurveChart",
        "id=driftChart",
        "id=finishesChart",
        "id=dataDateChart",
        "id=slippageChart",
    ):
        assert host in html


def test_mission_two_versions_renders_every_tile(sc) -> None:  # type: ignore[no-untyped-def]
    """With TWO analyzable versions of one Project the wall is whole — no degrade notes,
    every chart host present (the pre-fix ≥2 rendering, byte-comparable)."""
    _st, client = sc
    _upload(
        client,
        ("a1.xml", _mspdi("Alpha", "2025-01-10T00:00:00")),
        ("a2.xml", _mspdi("Alpha", "2025-02-10T00:00:00")),
    )
    html = client.get("/mission").text
    assert "Needs at least two" not in html
    for host in (
        "id=ceiChart",
        "id=evoChart",
        "id=qualBars",
        "id=trendCharts",
        "id=scurveChart",
        "id=driftChart",
        "id=finishesChart",
        "id=dataDateChart",
        "id=slippageChart",
    ):
        assert host in html


def test_the_multiversion_apis_still_guard_below_two_versions(sc) -> None:  # type: ignore[no-untyped-def]
    """The tile APIs keep their honest ≥2 guards (unchanged contract for every other caller) —
    the mission wall simply no longer calls them below the threshold."""
    _st, client = sc
    _upload(client, ("a1.xml", _mspdi("Alpha", "2025-01-10T00:00:00")))
    for api in ("/api/cei", "/api/trend", "/api/evolution"):
        assert client.get(api).status_code == 400, api


# ── ADR-0258 residual: the CEI guard must be population-scoped ────────────────────────────────────


def test_cei_guard_counts_the_active_population_not_the_session(sc) -> None:  # type: ignore[no-untyped-def]
    """Two single-version Projects loaded: the whole-session file count is 2, but the ACTIVE
    population holds ONE version — /api/cei (and its export) must 400 exactly as a
    single-project single-version session does, never gate on another Project's files."""
    st, client = sc
    _upload(client, ("a1.xml", _mspdi("Alpha", "2025-01-10T00:00:00")))
    _upload(client, ("b1.xml", _mspdi("Beta", "2025-01-15T00:00:00")))
    assert len(st.schedules) == 2  # the session holds two files…
    assert len(st.ordered()) == 1  # …but the active population is ONE version
    assert client.get("/api/cei").status_code == 400
    assert client.get("/export/xlsx/cei").status_code == 400


def _cyclic_mspdi(title: str, status: str) -> bytes:
    """Two tasks locked in a relationship cycle — loads fine, but the network cannot solve
    (verified: compute_cpm raises 'schedule logic contains a cycle')."""
    return (
        f"<Project {_NS}><StartDate>2025-01-06T08:00:00</StartDate>"
        f"<Title>{title}</Title><StatusDate>{status}</StatusDate>"
        "<Tasks><Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration>"
        "<PredecessorLink><PredecessorUID>2</PredecessorUID><Type>1</Type></PredecessorLink>"
        "</Task><Task><UID>2</UID><Name>B</Name><Duration>PT16H0M0S</Duration>"
        "<PredecessorLink><PredecessorUID>1</PredecessorUID><Type>1</Type></PredecessorLink>"
        "</Task></Tasks></Project>"
    ).encode()


def test_mission_distinguishes_loaded_from_analyzable(sc) -> None:  # type: ignore[no-untyped-def]
    """Two LOADED versions, one unsolvable (a logic cycle): the stored-date Bow Wave/CEI tile
    stays live (its API needs two loaded versions, no CPM), while the solve-gated tiles
    (Evolution + the two Quality tiles) degrade — each threshold mirrors its own API."""
    st, client = sc
    _upload(
        client,
        ("a1.xml", _mspdi("Alpha", "2025-01-10T00:00:00")),
        ("a2.xml", _cyclic_mspdi("Alpha", "2025-02-10T00:00:00")),
    )
    assert len(st.ordered()) == 2  # both load…
    html = client.get("/mission").text
    assert "id=ceiChart" in html  # …the stored-date wave has its two snapshots
    for host in ("id=evoChart", "id=qualBars", "id=trendCharts"):
        assert host not in html  # …but only ONE version solves — the CPM tiles say why
    assert html.count("Needs at least two analyzable") == 3
    assert client.get("/api/cei").status_code == 200


def test_mission_degrade_is_population_scoped(sc) -> None:  # type: ignore[no-untyped-def]
    """Same two-Project session: the wall serves the ACTIVE population (one version), so the
    cross-version tiles degrade even though the session dict holds two files."""
    _st, client = sc
    _upload(client, ("a1.xml", _mspdi("Alpha", "2025-01-10T00:00:00")))
    _upload(client, ("b1.xml", _mspdi("Beta", "2025-01-15T00:00:00")))
    html = client.get("/mission").text
    for host in ("id=ceiChart", "id=evoChart", "id=qualBars", "id=trendCharts"):
        assert host not in html
    assert html.count("Needs at least two") >= 4
