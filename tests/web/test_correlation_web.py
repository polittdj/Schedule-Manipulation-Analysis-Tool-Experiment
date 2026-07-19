"""Correlation-matrix web UI + API (ADR-0270): the editor panel, the add/clear POST routes,
input validation, and the feasibility provenance surfaced in the SSI run payload (so the
repair is disclosed to the analyst, never silent)."""

from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient

from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import SessionState, create_app

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _sched() -> Schedule:
    tasks = tuple(
        Task(unique_id=u, name=f"T{u}", duration_minutes=int(d * DAY))
        for u, d in ((1, 1), (2, 10), (3, 2), (4, 1))
    )
    rels = tuple(
        Relationship(predecessor_id=p, successor_id=s, type=RelationshipType.FS, lag_minutes=0)
        for p, s in ((1, 2), (1, 3), (2, 4), (3, 4))
    )
    return Schedule(name="C", project_start=MON, tasks=tasks, relationships=rels)


def _client() -> TestClient:
    st = SessionState()
    st.schedules["c1"] = _sched()
    return TestClient(create_app(st))


# --- the editor panel -----------------------------------------------------------------


def test_panel_renders_with_forms_and_empty_state() -> None:
    page = _client().get("/sra").text
    assert "Correlation matrix (advanced)" in page
    assert 'action="/sra/correlation-matrix"' in page
    assert "Add pair" in page and "Add group" in page
    assert "id=corrBadge" in page
    assert "No correlation matrix entered" in page  # the empty state
    # the matrix is honestly framed as overriding the blanket + repairing infeasible inputs
    assert "OVERRIDES" in page and "nearest valid correlation matrix" in page


def test_add_pair_persists_and_lists() -> None:
    c = _client()
    r = c.post(
        "/sra/correlation-matrix",
        data={"action": "add-pair", "uid_a": "2", "uid_b": "3", "rho": "0.5"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    page = c.get("/sra").text
    assert "2 &harr; 3" in page and "0.5" in page
    assert "Clear all correlations" in page


def test_add_group_persists() -> None:
    c = _client()
    c.post(
        "/sra/correlation-matrix", data={"action": "add-group", "uids": "2, 3", "group_rho": "0.4"}
    )
    page = c.get("/sra").text
    assert "group" in page and "2, 3" in page and "0.4" in page


def test_clear_empties() -> None:
    c = _client()
    c.post(
        "/sra/correlation-matrix",
        data={"action": "add-pair", "uid_a": "2", "uid_b": "3", "rho": "0.5"},
    )
    c.post("/sra/correlation-matrix", data={"action": "clear"})
    assert "No correlation matrix entered" in c.get("/sra").text


def test_invalid_uids_are_dropped() -> None:
    c = _client()
    # uid 99 is absent → the pair must not persist (never a fabricated correlation)
    c.post(
        "/sra/correlation-matrix",
        data={"action": "add-pair", "uid_a": "2", "uid_b": "99", "rho": "0.5"},
    )
    assert "No correlation matrix entered" in c.get("/sra").text
    # a self-pair (a == b) is also rejected
    c.post(
        "/sra/correlation-matrix",
        data={"action": "add-pair", "uid_a": "2", "uid_b": "2", "rho": "0.5"},
    )
    assert "No correlation matrix entered" in c.get("/sra").text


# --- the run surfaces feasibility provenance (the badge data) --------------------------


def test_run_surfaces_feasible_matrix_provenance() -> None:
    c = _client()
    c.post("/sra/factor", data={"uids": "2 3", "factor": "3"})  # make 2 and 3 uncertain
    c.post(
        "/sra/correlation-matrix", data={"action": "add-group", "uids": "2 3", "group_rho": "0.5"}
    )
    cm = c.get("/api/sra/ssi?iterations=200").json()["correlation_matrix"]
    assert cm["applied"] and not cm["repaired"]
    assert cm["min_eigenvalue"] > 0  # feasible → used verbatim
    assert cm["frobenius_distance"] == 0.0


def test_run_surfaces_infeasible_repair_provenance() -> None:
    c = _client()
    c.post("/sra/factor", data={"uids": "1 2 3", "factor": "3"})  # three uncertain tasks
    c.post(
        "/sra/correlation-matrix",
        data={"action": "add-group", "uids": "1 2 3", "group_rho": "-0.6"},
    )
    cm = c.get("/api/sra/ssi?iterations=200").json()["correlation_matrix"]
    assert cm["applied"] and cm["repaired"]
    assert cm["min_eigenvalue"] < 0  # the entered infeasibility is surfaced, not hidden
    assert cm["frobenius_distance"] > 0


def test_run_without_matrix_reports_not_applied() -> None:
    c = _client()
    c.post("/sra/factor", data={"uids": "2 3", "factor": "3"})
    cm = c.get("/api/sra/ssi?iterations=100").json()["correlation_matrix"]
    assert not cm["applied"] and not cm["repaired"]
