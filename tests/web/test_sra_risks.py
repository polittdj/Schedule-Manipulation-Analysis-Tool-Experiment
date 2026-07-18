"""Unified SRA risk register UI.

A risk is entered ONCE via ``POST /sra/risk-register`` (name, probability %, affected UIDs, and
BOTH a days and a %/multiplicative magnitude of the same event); it lives on the session as a
``UnifiedRisk`` and feeds BOTH SRA models: the legacy multiplicative ``/api/sra`` (from
``impact_pct``) and the SSI additive ``/api/sra/ssi`` (from ``impact_days``). Typing one magnitude
auto-derives the other from the affected tasks' average remaining duration (client-side, and
mirrored on the server for the JS-off path).
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
    days: str = "",
    pct: str = "20",
    consequence: str = "",
) -> None:
    """Register a risk. By default a +20% (multiplicative) magnitude; pass ``days=`` for the
    additive side (the unset magnitude auto-derives server-side from the affected tasks)."""
    client.post(
        "/sra/risk-register",
        data={
            "action": "add",
            "name": name,
            "prob": prob,
            "affected": affected,
            "impact_days": days,
            "impact_pct": pct,
            "consequence": consequence,
        },
    )


# ── registration / persistence ───────────────────────────────────────────────────────────


def test_risk_persists_and_shows_on_page(client: TestClient, state: SessionState) -> None:
    uid = _real_uids(state, 1)[0]
    _add_risk(client, "Permit delay", "40", str(uid), pct="20")
    assert len(state.sra_risks) == 1
    risk = state.sra_risks[0]
    assert risk.name == "Permit delay"
    assert risk.probability == pytest.approx(0.40)
    assert risk.impact_pct == pytest.approx(20.0)
    assert risk.pct_locked is True  # the operator typed % → it is locked for the legacy model
    assert (
        risk.impact_days > 0
    )  # the days magnitude auto-derived from the affected task's remaining
    assert risk.affected == (uid,)
    page = client.get("/sra").text
    assert "Permit delay" in page
    assert "Risk / Opportunity register" in page


def test_typing_days_derives_the_percent(client: TestClient, state: SessionState) -> None:
    """Enter the additive DAYS magnitude; the % auto-derives from the affected task's remaining days
    (pct = days / avg_remaining * 100) and days is locked."""
    uid = _real_uids(state, 1)[0]
    _add_risk(client, "Slip", "50", str(uid), days="10", pct="")
    risk = state.sra_risks[0]
    assert risk.impact_days == pytest.approx(10.0)
    assert risk.days_locked is True
    assert risk.pct_locked is False
    # the affected task has a positive remaining duration, so a % was derived
    assert risk.impact_pct != 0


def test_both_magnitudes_locked_when_both_entered(client: TestClient, state: SessionState) -> None:
    uid = _real_uids(state, 1)[0]
    _add_risk(client, "Both", "50", str(uid), days="7", pct="15")
    risk = state.sra_risks[0]
    assert risk.impact_days == pytest.approx(7.0) and risk.impact_pct == pytest.approx(15.0)
    assert risk.days_locked is True and risk.pct_locked is True  # both used verbatim


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


def test_probability_clamped(client: TestClient, state: SessionState) -> None:
    uid = _real_uids(state, 1)[0]
    _add_risk(client, "Clamp", "250", str(uid))  # probability > 100% clamps to 1.0
    assert state.sra_risks[0].probability == pytest.approx(1.0)


def test_consequence_clamped(client: TestClient, state: SessionState) -> None:
    uid = _real_uids(state, 1)[0]
    _add_risk(client, "Cons", "30", str(uid), days="5", consequence="9")
    assert state.sra_risks[0].consequence_rating == 5  # 1..5 clamp


# ── removal / clear / wipe ───────────────────────────────────────────────────────────────


def test_remove_one_risk(client: TestClient, state: SessionState) -> None:
    uids = _real_uids(state, 2)
    _add_risk(client, "Keep", "30", str(uids[0]))
    _add_risk(client, "Drop", "30", str(uids[1]))
    drop_id = state.sra_risks[-1].id
    client.post("/sra/risk-register", data={"action": "remove", "rid": drop_id})
    assert [r.name for r in state.sra_risks] == ["Keep"]


def test_clear_all_risks(client: TestClient, state: SessionState) -> None:
    uid = _real_uids(state, 1)[0]
    _add_risk(client, "One", "30", str(uid))
    client.post("/sra/risk-register", data={"action": "clear"})
    assert not state.sra_risks


def test_wipe_clears_risk_register(client: TestClient, state: SessionState) -> None:
    uid = _real_uids(state, 1)[0]
    _add_risk(client, "One", "30", str(uid))
    assert state.sra_risks
    client.post("/session/wipe")
    assert state.sra_risks == []
    assert state.sra_risk_seq == 0


# ── simulation payload (both models read the one register) ───────────────────────────────


def test_api_sra_returns_risk_drivers(client: TestClient, state: SessionState) -> None:
    uid = _real_uids(state, 1)[0]
    _add_risk(client, "Permit delay", "60", str(uid), pct="20")
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
    _add_risk(client, "Big slip", "95", ",".join(str(u) for u in uids), pct="150")
    worse = client.get("/api/sra?iterations=300").json()
    assert worse["percentiles"][3]["date"] >= base["percentiles"][3]["date"]


def test_the_one_register_feeds_the_ssi_model_too(client: TestClient, state: SessionState) -> None:
    """The SAME registered risk (days magnitude) appears in the SSI run's risk register output."""
    uid = _real_uids(state, 1)[0]
    _add_risk(client, "Permit delay", "50", str(uid), days="30", pct="")
    data = client.get("/api/sra/ssi?iterations=200").json()
    names = {r["name"] for r in data.get("risks", [])}
    assert "Permit delay" in names


# ── the one form + the client-side days<->% auto-derive wiring ───────────────────────────


def test_unified_register_form_and_js_wiring(client: TestClient) -> None:
    page = client.get("/sra").text
    # ONE form, both magnitudes, the lock flags, and the remaining-days map for the client derive
    assert 'action="/sra/risk-register"' in page
    assert "id=riskDays" in page and "id=riskPct" in page and "id=riskAffected" in page
    assert "id=riskDaysLocked" in page and "id=riskPctLocked" in page
    assert "sfRemainDays" in page and "/static/sra_risk.js" in page
    # the two old separate forms are gone
    assert "/sra/risk-event" not in page and "/sra/ssi-risk" not in page
    js = client.get("/static/sra_risk.js").text
    assert "sfRemainDays" in js and "avgRemaining" in js  # the days<->% derive from avg remaining
    # air-gap: no external URLs in the vendored script
    import re

    assert not [u for u in re.findall(r"https?://[^\s\"'<>]+", js)]


# ── uid-list parse helper ───────────────────────────────────────────────────────────────


def test_parse_uid_list_separators_and_dedup() -> None:
    assert _parse_uid_list("101, 102 103;104") == [101, 102, 103, 104]
    assert _parse_uid_list("5 5 5") == [5]  # dedup, first wins
    assert _parse_uid_list("7, x, -3, 0, 9") == [7, 9]  # non-numeric / non-positive dropped
    assert _parse_uid_list("") == []
    assert _parse_uid_list(None) == []


def test_affected_avg_remaining_days_matches_client_precision() -> None:
    """Audit M5: the server must round each per-task remaining-days value at the SAME precision
    the client receives in window.SF_REMAIN_DAYS, so their derived days↔% magnitudes agree for
    sub-day tasks (previously the server averaged unrounded values → divergence)."""
    import datetime as dt

    from schedule_forensics.model.schedule import Schedule
    from schedule_forensics.model.task import Task
    from schedule_forensics.web.app import _REMAIN_DAYS_DP, _affected_avg_remaining_days

    mpd = 480
    tasks = (
        Task(unique_id=1, name="a", duration_minutes=36, remaining_duration_minutes=36),
        Task(unique_id=2, name="b", duration_minutes=20, remaining_duration_minutes=20),
    )
    sch = Schedule(
        name="s", project_start=dt.datetime(2025, 1, 6, 8, 0), tasks=tasks, relationships=()
    )
    # the exact values the client averages (SF_REMAIN_DAYS = round(rem/mpd, _REMAIN_DAYS_DP))
    client_vals = [round(36 / mpd, _REMAIN_DAYS_DP), round(20 / mpd, _REMAIN_DAYS_DP)]
    client_avg = sum(client_vals) / len(client_vals)
    assert _affected_avg_remaining_days(sch, [1, 2]) == client_avg
