"""Bow Wave / CEI view + trend-focus tests (modeled on the operator's reference decks)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.engine.bow_wave import BowWave, SnapshotProfile
from schedule_forensics.web.app import SessionState, _cei_body, create_app

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


def test_cei_view_needs_two_versions(client: TestClient) -> None:
    assert "at least two versions" in client.get("/cei").text
    assert client.get("/api/cei").status_code == 400


def _post_target(client, uid) -> None:
    """ADR-0268: the CEI Focus control POSTs the session target (a GET side effect was removed)."""
    client.post(
        "/target",
        data={"uid": str(uid), "next_url": "/cei"},
        headers={"origin": "http://127.0.0.1"},
        follow_redirects=False,
    )


def test_cei_target_change_invalidates_scope_and_couples_sra_focus(client: TestClient) -> None:
    # Audit: /cei focused the session-wide target with a RAW `st.target_uid = ...` assignment,
    # bypassing set_target — so `_invalidate_scope()` never ran (every page kept serving results
    # scoped to the PREVIOUS target) and `sra_focus_uid` was left stale. Changing the target from
    # one non-None UID to a different one must now go through set_target: caches invalidate and the
    # SRA focus tracks the header target (ADR-0196).
    _upload(client, "Project5")
    _upload(client, "Project2")
    st = client.app.state.session
    sch = next(iter(st.schedules.values()))
    uids = [t.unique_id for t in sch.tasks if not t.is_summary][:2]
    a, b = uids[0], uids[1]

    _post_target(client, a)
    _post_target(client, b)

    assert st.target_uid == b
    # set_target couples the SRA focus to the target and invalidates the scope/analysis caches;
    # the old raw `st.target_uid = ...` assignment left sra_focus_uid untouched (stale None here) —
    # so this equality is the decisive proof the change now routes through set_target.
    assert st.sra_focus_uid == b


def test_cei_page_has_animation_controls_and_summary(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")
    page = client.get("/cei").text
    assert "Bow Wave" in page and "Current Execution Index" in page
    # the animated chart controls: prev / next / auto-play (the movie mode)
    assert "id=prevSnap" in page and "id=nextSnap" in page and "id=autoPlay" in page
    assert "id=ceiChart" in page and "/static/cei.js" in page
    # the CEI summary table columns
    for col in ("Previously planned", "Re-scheduled", "Actually finished", "CEI"):
        assert col in page


def test_api_cei_serves_shared_axis_profiles(client: TestClient) -> None:
    _upload(client, "Project5")  # load order reversed on purpose
    _upload(client, "Project2")
    data = client.get("/api/cei").json()
    months = data["months"]
    snaps = data["snapshots"]
    assert [s["label"] for s in snaps] == [
        "Project2.mspdi.xml",
        "Project5.mspdi.xml",
    ]  # data-date order
    for s in snaps:
        assert len(s["baselined"]) == len(s["scheduled"]) == len(s["finished"]) == len(months)
    assert sum(snaps[0]["finished"]) == 20 and sum(snaps[1]["finished"]) == 27  # golden counts
    assert snaps[0]["cei"] is None  # first snapshot has no prior
    assert snaps[1]["cei_period"] is not None  # the later one carries the CEI comparison
    assert snaps[1]["status_index"] is not None  # data-date marker on the shared axis


def test_api_cei_carries_a_locked_y_axis_max(client: TestClient) -> None:
    # item 5: the bow-wave count scale is the max bar across EVERY snapshot, served once so
    # the animation never rescales between frames (the bow wave's growth stays visible).
    _upload(client, "Project2")
    _upload(client, "Project5")
    data = client.get("/api/cei").json()
    every_bar = [
        v
        for s in data["snapshots"]
        for series in ("baselined", "scheduled", "finished")
        for v in s[series]
    ]
    assert data["max_count"] == max(every_bar)  # the global max, not a per-snapshot one
    assert data["max_count"] >= max(max(s["finished"]) for s in data["snapshots"])


def test_cei_page_has_running_totals_toggle_and_target_focus(client: TestClient) -> None:
    """Item F: the Bow-Wave view offers a 'Running totals' toggle and a Target-UID focus."""
    _upload(client, "Project2")
    _upload(client, "Project5")
    page = client.get("/cei").text
    assert "id=ceiTotals" in page and "Running totals" in page
    assert "method=post action=/target" in page and "Target UID" in page
    js = client.get("/static/cei.js").text
    assert "cumulative" in js and "ceiTotals" in js  # the running-totals curves + toggle
    assert "targetMark" in js and "target_scheduled_index" in js  # the focus marker


def test_api_cei_carries_target_focus_indices(client: TestClient) -> None:
    """Focusing a target sets the session-wide UID and the /api/cei profiles carry where it
    lands (its scheduled / actual finish month index) per snapshot; clearing removes it."""
    _upload(client, "Project2")
    _upload(client, "Project5")
    # focusing UID 6 (an on-axis activity) via POST persists it; the API carries its indices
    _post_target(client, 6)
    data = client.get("/api/cei").json()
    assert data["target_uid"] == 6
    for s in data["snapshots"]:
        assert "target_scheduled_index" in s and "target_finished_index" in s
    assert any(s["target_scheduled_index"] is not None for s in data["snapshots"])
    # clearing the focus drops the target back to none
    _post_target(client, "")
    assert client.get("/api/cei").json()["target_uid"] is None


def test_cei_zero_is_styled_as_fail_not_pass() -> None:
    # CEI 0.00 (nothing the prior snapshot planned actually finished) is the WORST score —
    # it must render red/fail. A falsy-zero shortcut once made it green.
    def profile(cei: float | None) -> SnapshotProfile:
        return SnapshotProfile(
            label="S",
            status_index=0,
            baselined=(0,),
            scheduled=(0,),
            finished=(0,),
            cei=cei,
            cei_period="May-26",
            cei_planned=3,
            cei_scheduled=0,
            cei_finished=0,
        )

    body = _cei_body(BowWave(month_labels=("May-26",), snapshots=(profile(0.0),)))
    assert "class=fail>0.00" in body
    body = _cei_body(BowWave(month_labels=("May-26",), snapshots=(profile(1.0),)))
    assert "class=pass>1.00" in body
    body = _cei_body(BowWave(month_labels=("May-26",), snapshots=(profile(None),)))
    assert "class=pass>—" in body  # no measurement is neutral, not a failure


def test_cei_js_renders_grouped_bars_and_autoplay(client: TestClient) -> None:
    js = client.get("/static/cei.js").text
    assert "Baselined to Finish" in js and "Scheduled to Finish" in js and "Finished" in js
    assert "setInterval" in js and "Auto-play" in js  # the animated movie mode
    assert "CEI – " in js and "data date" in js  # noqa: RUF001 — the deck's en-dash callout


def test_trend_focus_uid(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")
    page = client.get("/trend?target=143").text
    assert "Focus activity UID 143" in page  # the focus table
    assert 'data-target="143"' in page  # the chart picks it up
    assert "clear focus" in page
    data = client.get("/api/trend?target=143").json()
    assert data["target"]["uid"] == 143
    assert len(data["target"]["finishes"]) == 2 and all(data["target"]["finishes"])
    # an unknown UID degrades gracefully (page renders, values are em-dashes/nulls)
    page = client.get("/trend?target=999999").text
    assert "No loaded version contains that UniqueID" in page
    data = client.get("/api/trend?target=999999").json()
    assert data["target"]["finishes"] == [None, None]


def test_trend_labels_are_deoverlapped(client: TestClient) -> None:
    js = client.get("/static/trend.js").text
    assert "shortLabels" in js  # common-prefix stripping for long version names
    assert "rotate(-35" in js  # rotated axis labels never overlap
    # identical filenames collapse to nothing after the prefix strip — the data date
    # (or version index) labels those instead of a bare "…"
    assert "status_date ||" in js


def test_track_uids_control_payload_and_cap(client: TestClient) -> None:
    """Operator 2026-07-09: the Bow-Wave page tracks up to 20 chosen UIDs — a Track UIDs
    control, per-snapshot tracked marks in /api/cei, and a hard 20-UID cap."""
    _upload(client, "Project2")
    _upload(client, "Project5")
    page = client.get("/cei?uids=106,113").text
    assert "id=ceiTrack" in page and 'value="106, 113"' in page
    data = client.get("/api/cei?uids=106,113").json()
    tracked = data["snapshots"][-1]["tracked"]
    assert [t["uid"] for t in tracked] == [106, 113]
    assert all("name" in t and "scheduled_index" in t and "pct" in t for t in tracked)
    # the 21st UID is dropped (cap 20, first kept)
    many = ",".join(str(u) for u in range(1, 30))
    capped = client.get(f"/api/cei?uids={many}").json()["snapshots"][0]["tracked"]
    assert len(capped) == 20 and capped[0]["uid"] == 1 and capped[-1]["uid"] == 20
    # cei.js reads the control and draws the tracked marks
    js = client.get("/static/cei.js").text
    assert "ceiTrack" in js and "tracked" in js


def test_cei_chapter_06_page_shell(client: TestClient) -> None:
    """ADR-0203 — chapter 06 "Work piling up": the data-driven takeaway h1, the CEI KPI
    strip, and the Latest-scored-month / Where-the-finishes-sit composition bars, all read
    from the bow-wave dataset the page already computes. The scaffold survives beneath."""
    _upload(client, "Project2")
    _upload(client, "Project5")
    page = client.get("/cei").text

    # data-driven takeaway carries the real CEI figures from the golden pair
    assert 'class="page-takeaway"' in page
    assert "CEI 1.00" in page and "3 of the 3 finishes" in page
    assert "sit ahead of the data date" in page

    # the six-KPI strip and both composition bars
    assert 'class="ws-kpi"' in page and "Latest CEI" in page and "Months under plan" in page
    assert "Latest scored month" in page and "Where the finishes sit" in page
    assert 'class="stack-bar"' in page

    # chapter chrome fires here (kicker + Continue -> chapter 07)
    assert "CHAPTER 06 · WORK PILING UP" in page
    assert "Chapter 07" in page
