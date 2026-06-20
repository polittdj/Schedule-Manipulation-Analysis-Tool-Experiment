"""SRA discrete-risk register UI (ADR-0106, risk-driver method).

The analyst registers discrete risks (name, probability %, 3-point multiplicative impact %, and the
affected activity UIDs) via ``POST /sra/risk-event``; they live on the session and feed the next
``/api/sra`` run, which returns a ``risk_drivers`` tornado payload. Tests keep the simulation small
(200 iterations) for speed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import (
    SessionState,
    _latest_solvable,
    _parse_uid_list,
    create_app,
)

GOLDEN = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "golden"
    / "project2_5"
    / "Project5.mspdi.xml"
)


@pytest.fixture
def state() -> SessionState:
    return SessionState()


@pytest.fixture
def client(state: SessionState) -> TestClient:
    c = TestClient(create_app(state))
    c.post("/upload", files={"files": ("Project5.mspdi.xml", GOLDEN.read_bytes(), "text/xml")})
    return c


def _real_uids(state: SessionState, count: int = 2) -> list[int]:
    """The first ``count`` real non-summary UIDs in the latest solvable schedule."""
    chosen = _latest_solvable(state)
    assert chosen is not None
    _key, sch, _cpm = chosen
    uids = [t.unique_id for t in sch.tasks if not t.is_summary]
    assert len(uids) >= count
    return uids[:count]


def _add_risk(
    client: TestClient,
    name: str,
    prob: str,
    affected: str,
    *,
    lo: str = "100",
    ml: str = "120",
    hi: str = "150",
) -> None:
    client.post(
        "/sra/risk-event",
        data={
            "name": name,
            "prob": prob,
            "imp_low": lo,
            "imp_ml": ml,
            "imp_high": hi,
            "affected": affected,
        },
    )


# ── registration / persistence ───────────────────────────────────────────────────────────


def test_risk_persists_and_shows_on_page(client: TestClient, state: SessionState) -> None:
    uid = _real_uids(state, 1)[0]
    _add_risk(client, "Permit delay", "40", str(uid))
    assert len(state.sra_risks) == 1
    risk = state.sra_risks[0]
    assert risk.name == "Permit delay"
    assert risk.probability == pytest.approx(0.40)
    assert risk.impact_ml == pytest.approx(1.20)
    assert risk.affected == (uid,)
    page = client.get("/sra").text
    assert "Permit delay" in page
    assert "Risk register" in page


def test_risk_ids_are_unique_and_stable(client: TestClient, state: SessionState) -> None:
    uids = _real_uids(state, 2)
    _add_risk(client, "Risk A", "30", str(uids[0]))
    _add_risk(client, "Risk B", "50", str(uids[1]))
    ids = [r.id for r in state.sra_risks]
    assert len(ids) == len(set(ids)) == 2


def test_affected_uids_validated_unknown_dropped(client: TestClient, state: SessionState) -> None:
    uid = _real_uids(state, 1)[0]
    _add_risk(client, "Mixed", "25", f"{uid}, 99999999")
    assert len(state.sra_risks) == 1
    assert state.sra_risks[0].affected == (uid,)  # the dangling uid is dropped


def test_risk_with_no_valid_activity_is_ignored(client: TestClient, state: SessionState) -> None:
    _add_risk(client, "Dangling", "50", "99999999")
    assert not state.sra_risks


def test_unnamed_risk_is_ignored(client: TestClient, state: SessionState) -> None:
    uid = _real_uids(state, 1)[0]
    _add_risk(client, "   ", "50", str(uid))
    assert not state.sra_risks


def test_probability_clamped_and_impacts_ordered(client: TestClient, state: SessionState) -> None:
    uid = _real_uids(state, 1)[0]
    # probability > 100% clamps to 1.0; impacts given out of order are coerced lo <= ml <= hi
    _add_risk(client, "Clamp", "250", str(uid), lo="150", ml="120", hi="100")
    risk = state.sra_risks[0]
    assert risk.probability == pytest.approx(1.0)
    assert risk.impact_low <= risk.impact_ml <= risk.impact_high


# ── removal / clear / wipe ───────────────────────────────────────────────────────────────


def test_remove_one_risk(client: TestClient, state: SessionState) -> None:
    uids = _real_uids(state, 2)
    _add_risk(client, "Keep", "30", str(uids[0]))
    _add_risk(client, "Drop", "30", str(uids[1]))
    drop_id = state.sra_risks[-1].id
    client.post("/sra/risk-event", data={"remove": drop_id})
    assert [r.name for r in state.sra_risks] == ["Keep"]


def test_clear_all_risks(client: TestClient, state: SessionState) -> None:
    uid = _real_uids(state, 1)[0]
    _add_risk(client, "One", "30", str(uid))
    client.post("/sra/risk-event", data={"clear": "1"})
    assert not state.sra_risks


def test_wipe_clears_risk_register(client: TestClient, state: SessionState) -> None:
    uid = _real_uids(state, 1)[0]
    _add_risk(client, "One", "30", str(uid))
    assert state.sra_risks
    client.post("/session/wipe")
    assert state.sra_risks == []
    assert state.sra_risk_seq == 0


# ── simulation payload ──────────────────────────────────────────────────────────────────


def test_api_sra_returns_risk_drivers(client: TestClient, state: SessionState) -> None:
    uid = _real_uids(state, 1)[0]
    _add_risk(client, "Permit delay", "60", str(uid))
    data = client.get("/api/sra?iterations=200").json()
    drivers = data["risk_drivers"]
    assert len(drivers) == 1
    d = drivers[0]
    assert d["name"] == "Permit delay"
    assert d["iterations"] == 200
    # ~60% of 200 iterations should fire (seeded — allow generous slack)
    assert 80 <= d["hits"] <= 160
    assert "delta_days" in d


def test_no_risks_yields_empty_drivers(client: TestClient) -> None:
    data = client.get("/api/sra?iterations=200").json()
    assert data["risk_drivers"] == []


def test_high_impact_risk_pushes_finish_out(client: TestClient, state: SessionState) -> None:
    # a near-certain, high-impact risk on the critical activities should worsen the P90 finish
    base = client.get("/api/sra?iterations=300").json()
    uids = _real_uids(state, 4)
    _add_risk(
        client, "Big slip", "95", ",".join(str(u) for u in uids), lo="180", ml="220", hi="300"
    )
    worse = client.get("/api/sra?iterations=300").json()
    assert worse["percentiles"][3]["date"] >= base["percentiles"][3]["date"]


# ── uid-list parse helper ───────────────────────────────────────────────────────────────


def test_parse_uid_list_separators_and_dedup() -> None:
    assert _parse_uid_list("101, 102 103;104") == [101, 102, 103, 104]
    assert _parse_uid_list("5 5 5") == [5]  # dedup, first wins
    assert _parse_uid_list("7, x, -3, 0, 9") == [7, 9]  # non-numeric / non-positive dropped
    assert _parse_uid_list("") == []
    assert _parse_uid_list(None) == []
