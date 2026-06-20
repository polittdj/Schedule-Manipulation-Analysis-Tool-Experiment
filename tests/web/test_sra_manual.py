"""SRA manual-input UI (ADR-0106, manual path).

The analyst supplies the global triangular (low/ml/high %) and optional per-activity 3-point
overrides via ``POST /sra/risk``; both live on the session and drive the next ``/api/sra`` run.
Tests keep the simulation small (200 iterations) for speed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import (
    SessionState,
    _clamp_float,
    _latest_solvable,
    _to_float,
    create_app,
)

GOLDEN = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "golden"
    / "project2_5"
    / "Project5.mspdi.xml"
)


def _add_override(client: TestClient, uid: int, opt: str, ml: str, pess: str) -> None:
    client.post(
        "/sra/risk",
        data={"uid": str(uid), "opt_days": opt, "ml_days": ml, "pess_days": pess},
    )


@pytest.fixture
def state() -> SessionState:
    return SessionState()


@pytest.fixture
def client(state: SessionState) -> TestClient:
    c = TestClient(create_app(state))
    c.post("/upload", files={"files": ("Project5.mspdi.xml", GOLDEN.read_bytes(), "text/xml")})
    return c


def _real_task_uid(state: SessionState) -> int:
    """A real non-summary UID in the latest solvable schedule (the override happy path)."""
    chosen = _latest_solvable(state)
    assert chosen is not None
    _key, sch, _cpm = chosen
    for task in sch.tasks:
        if not task.is_summary:
            return task.unique_id
    raise AssertionError("no non-summary task in the golden schedule")


# ── global triangular ──────────────────────────────────────────────────────────────────


def test_global_risk_persists_and_shows_on_page(client: TestClient, state: SessionState) -> None:
    r = client.post("/sra/risk", data={"low": "80", "ml": "100", "high": "150"})
    assert r.status_code == 200  # TestClient follows the 303 to /sra
    assert state.sra_low == pytest.approx(0.80)
    assert state.sra_ml == pytest.approx(1.00)
    assert state.sra_high == pytest.approx(1.50)
    page = client.get("/sra").text
    # off-defaults now shows the analyst-supplied note, not the screening disclaimer
    assert "analyst-supplied uncertainty" in page
    assert "screening placeholder" not in page
    assert 'value="80"' in page and 'value="150"' in page


def test_global_risk_changes_distribution(client: TestClient) -> None:
    base = client.get("/api/sra?iterations=200").json()
    client.post("/sra/risk", data={"low": "60", "ml": "120", "high": "250"})
    wider = client.get("/api/sra?iterations=200").json()
    assert wider["manual"]["low"] == pytest.approx(0.60)
    assert wider["manual"]["high"] == pytest.approx(2.50)
    # a far wider, right-skewed triangular pushes the P90 finish out
    assert wider["percentiles"][3]["date"] != base["percentiles"][3]["date"]


def test_global_risk_clamps(client: TestClient, state: SessionState) -> None:
    client.post("/sra/risk", data={"low": "0", "ml": "999", "high": "999"})
    assert state.sra_low == pytest.approx(0.05)  # low floor (0.05, 1.0]
    assert state.sra_ml == pytest.approx(1.5)  # ml ceiling
    assert state.sra_high == pytest.approx(3.0)  # high ceiling


def test_global_risk_coerces_ordering(client: TestClient, state: SessionState) -> None:
    # low > ml > high inputs must be coerced to low <= ml <= high
    client.post("/sra/risk", data={"low": "100", "ml": "70", "high": "60"})
    assert state.sra_low <= state.sra_ml <= state.sra_high


# ── per-activity overrides ─────────────────────────────────────────────────────────────


def test_override_appears_in_table_and_is_honored(client: TestClient, state: SessionState) -> None:
    uid = _real_task_uid(state)
    client.post(
        "/sra/risk",
        data={"uid": str(uid), "opt_days": "1", "ml_days": "5", "pess_days": "30"},
    )
    assert uid in state.sra_overrides
    o, m, p = state.sra_overrides[uid]
    assert 0 <= o <= m <= p
    page = client.get("/sra").text
    assert f"<td>{uid}</td>" in page
    assert state.sra_overrides  # one override recorded
    # the run honors it (one override in effect)
    data = client.get("/api/sra?iterations=200").json()
    assert data["manual"]["overrides"] == 1


def test_unknown_uid_is_ignored(client: TestClient, state: SessionState) -> None:
    client.post(
        "/sra/risk",
        data={"uid": "99999999", "opt_days": "1", "ml_days": "2", "pess_days": "3"},
    )
    assert 99999999 not in state.sra_overrides
    assert not state.sra_overrides


def test_summary_uid_is_ignored(client: TestClient, state: SessionState) -> None:
    chosen = _latest_solvable(state)
    assert chosen is not None
    _key, sch, _cpm = chosen
    summary_uid = next((t.unique_id for t in sch.tasks if t.is_summary), None)
    if summary_uid is None:
        pytest.skip("golden schedule has no summary task")
    client.post(
        "/sra/risk",
        data={"uid": str(summary_uid), "opt_days": "1", "ml_days": "2", "pess_days": "3"},
    )
    assert summary_uid not in state.sra_overrides


def test_override_days_convert_to_minutes(client: TestClient, state: SessionState) -> None:
    chosen = _latest_solvable(state)
    assert chosen is not None
    _key, sch, _cpm = chosen
    per_day = sch.calendar.working_minutes_per_day
    uid = _real_task_uid(state)
    client.post(
        "/sra/risk",
        data={"uid": str(uid), "opt_days": "2", "ml_days": "4", "pess_days": "8"},
    )
    o, m, p = state.sra_overrides[uid]
    assert o == 2 * per_day and m == 4 * per_day and p == 8 * per_day


def test_override_coerces_three_point_ordering(client: TestClient, state: SessionState) -> None:
    uid = _real_task_uid(state)
    client.post(
        "/sra/risk",
        data={"uid": str(uid), "opt_days": "30", "ml_days": "5", "pess_days": "1"},
    )
    o, m, p = state.sra_overrides[uid]
    assert o <= m <= p


def test_remove_override(client: TestClient, state: SessionState) -> None:
    uid = _real_task_uid(state)
    _add_override(client, uid, "1", "2", "3")
    assert uid in state.sra_overrides
    client.post("/sra/risk", data={"remove": str(uid)})
    assert uid not in state.sra_overrides


def test_clear_all_overrides(client: TestClient, state: SessionState) -> None:
    uid = _real_task_uid(state)
    _add_override(client, uid, "1", "2", "3")
    assert state.sra_overrides
    client.post("/sra/risk", data={"clear": "1"})
    assert not state.sra_overrides


# ── lifecycle ──────────────────────────────────────────────────────────────────────────


def test_wipe_clears_sra_inputs(client: TestClient, state: SessionState) -> None:
    uid = _real_task_uid(state)
    client.post("/sra/risk", data={"low": "70", "ml": "110", "high": "140"})
    _add_override(client, uid, "1", "2", "3")
    assert state.sra_overrides
    client.post("/session/wipe")
    assert state.sra_low == pytest.approx(0.9)
    assert state.sra_ml == pytest.approx(1.0)
    assert state.sra_high == pytest.approx(1.10)
    assert state.sra_overrides == {}


def test_default_disclaimer_shows_on_fresh_session(client: TestClient) -> None:
    page = client.get("/sra").text
    assert "screening placeholder" in page
    assert "not SME-validated" in page or "not\nSME-validated" in page


def test_no_auto_high_query_param_needed(client: TestClient) -> None:
    # /api/sra no longer accepts auto_high — it reads the session; the run still succeeds
    data = client.get("/api/sra?iterations=200").json()
    assert data["iterations"] == 200
    assert "manual" in data


# ── numeric-parse helpers (defensive fallbacks) ───────────────────────────────────────


def test_to_float_fallbacks() -> None:
    assert _to_float(None, 1.0) == 1.0  # None -> default
    assert _to_float("not-a-number", 2.0) == 2.0  # non-numeric -> default
    assert _to_float(" 3.5 ", 0.0) == 3.5  # parsed (whitespace stripped)


def test_clamp_float_non_numeric_keeps_default() -> None:
    # a non-numeric value keeps the (already-scaled) default, then re-clamps it
    assert _clamp_float("abc", 0.05, 1.0, 0.9, scale=0.01) == pytest.approx(0.9)


def test_global_risk_ignores_non_numeric_input(client: TestClient, state: SessionState) -> None:
    # garbage in the percent fields leaves the current session values untouched
    client.post("/sra/risk", data={"low": "80"})  # set a known low first
    client.post("/sra/risk", data={"low": "xyz", "ml": "", "high": "??"})
    assert state.sra_low == pytest.approx(0.80)
