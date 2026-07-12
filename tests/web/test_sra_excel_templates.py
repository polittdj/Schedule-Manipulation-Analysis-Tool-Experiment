"""SRA Excel round-trip templates (ADR-0211).

The operator exports a pre-formatted fill-in workbook for the risk register and for the per-task
Best/Worst-Case durations + Risk Ranking Factors, edits it in Excel, and re-imports it. The reader
is std-lib only (Law 1); nothing is fabricated on import (Law 2) — unmatched UIDs are dropped and
counted, an inverted Best/Worst pair is skipped, and a one-shot banner reports exactly what landed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.reports.tables import Table, TableSet
from schedule_forensics.reports.xlsx import render_xlsx
from schedule_forensics.reports.xlsx_read import read_xlsx
from schedule_forensics.web.app import (
    SessionState,
    _latest_solvable,
    create_app,
)

GOLDEN = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "golden"
    / "project2_5"
    / "Project5.mspdi.xml"
)

_RR_HEADERS = (
    "Risk ID",
    "Risk name",
    "Probability %",
    "Impact (working days)",
    "Consequence (1-5)",
    "Affected UIDs (; separated)",
)
_TR_HEADERS = (
    "UID",
    "Task name",
    "Remaining (days)",
    "Risk Ranking Factor (0-5)",
    "Best-Case (days)",
    "Worst-Case (days)",
)

_XLSX_CT = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.fixture
def state() -> SessionState:
    return SessionState()


@pytest.fixture
def client(state: SessionState) -> TestClient:
    c = TestClient(create_app(state))
    c.post("/upload", files={"files": ("Project5.mspdi.xml", GOLDEN.read_bytes(), "text/xml")})
    return c


def _uids(state: SessionState, count: int = 2) -> list[int]:
    chosen = _latest_solvable(state)
    assert chosen is not None
    _key, sch, _cpm = chosen
    return [t.unique_id for t in sch.tasks if not t.is_summary][:count]


def _rr_upload(client: TestClient, rows: tuple[tuple[object, ...], ...]) -> None:
    blob = render_xlsx(TableSet("t", (Table("Risk Register", _RR_HEADERS, rows),)))
    client.post(
        "/sra/import/risk-register",
        files={"file": ("filled.xlsx", blob, _XLSX_CT)},
        follow_redirects=False,
    )


def _tr_upload(client: TestClient, rows: tuple[tuple[object, ...], ...]) -> None:
    blob = render_xlsx(TableSet("t", (Table("Task Risk Inputs", _TR_HEADERS, rows),)))
    client.post(
        "/sra/import/task-risk",
        files={"file": ("filled.xlsx", blob, _XLSX_CT)},
        follow_redirects=False,
    )


# ── exports ───────────────────────────────────────────────────────────────────────────────────


def test_risk_register_template_exports_headers_and_reference_sheet(client: TestClient) -> None:
    r = client.get("/export/xlsx/risk-register-template")
    assert r.status_code == 200
    assert r.headers["content-type"] == _XLSX_CT
    sheets = read_xlsx(r.content)
    # a Risk Register sheet with the header contract + a read-only task reference sheet
    assert "Risk Register" in sheets
    assert list(_RR_HEADERS) == sheets["Risk Register"][0]
    assert any("Tasks" in name for name in sheets)  # reference sheet present
    # with no register set, an EXAMPLE seed row is included (deleted by the operator)
    assert sheets["Risk Register"][1][0].startswith("EXAMPLE")


def test_task_risk_template_has_one_row_per_activity(
    client: TestClient, state: SessionState
) -> None:
    r = client.get("/export/xlsx/task-risk-template")
    assert r.status_code == 200
    sheets = read_xlsx(r.content)
    assert list(_TR_HEADERS) == sheets["Task Risk Inputs"][0]
    chosen = _latest_solvable(state)
    assert chosen is not None
    _key, sch, _cpm = chosen
    n_tasks = sum(1 for t in sch.tasks if not t.is_summary)
    assert len(sheets["Task Risk Inputs"]) == n_tasks + 1  # + header row


def test_template_export_needs_a_schedule() -> None:
    empty = TestClient(create_app(SessionState()))
    assert empty.get("/export/xlsx/risk-register-template").status_code == 400
    assert empty.get("/export/xlsx/task-risk-template").status_code == 400


def test_exported_template_round_trips_the_current_register(
    client: TestClient, state: SessionState
) -> None:
    """A register set on the session appears in its exported template (not the EXAMPLE seed)."""
    uid = _uids(state, 1)[0]
    _rr_upload(client, (("R1", "Vendor slip", 40, 12, 4, str(uid)),))
    assert len(state.sra_risks) == 1
    sheets = read_xlsx(client.get("/export/xlsx/risk-register-template").content)
    body = sheets["Risk Register"][1:]
    assert any(row and row[1] == "Vendor slip" for row in body)
    assert not any(row and row[0].startswith("EXAMPLE") for row in body)


# ── risk-register import ────────────────────────────────────────────────────────────────────────


def test_import_risk_register_rebuilds_the_session(client: TestClient, state: SessionState) -> None:
    u1, u2 = _uids(state, 2)
    _rr_upload(
        client,
        (
            ("R1", "Vendor slip", 40, 12, 4, str(u1)),
            ("R2", "Weather", 25, 6, 2, f"{u1}; {u2}; 99999999"),  # dangling uid dropped
            ("", "", "", "", "", ""),  # blank row -> skipped silently
        ),
    )
    assert [r.name for r in state.sra_risks] == ["Vendor slip", "Weather"]
    r1, r2 = state.sra_risks
    assert r1.probability == pytest.approx(0.40)
    assert r1.impact_days == pytest.approx(12.0)
    assert r1.consequence_rating == 4
    assert r1.affected == (u1,)
    assert r2.affected == (u1, u2)  # the 99999999 was dropped
    assert state.sra_use_risk_register is True


def test_import_risk_register_skips_the_example_row(
    client: TestClient, state: SessionState
) -> None:
    """The seeded EXAMPLE row (round-tripped verbatim) must not become a real risk."""
    uid = _uids(state, 1)[0]
    _rr_upload(
        client,
        (
            ("EXAMPLE (delete this row)", "e.g. vendor delay", 30, 10, 3, str(uid)),
            ("R1", "Real risk", 50, 8, 3, str(uid)),
        ),
    )
    assert [r.name for r in state.sra_risks] == ["Real risk"]


def test_import_risk_register_reports_a_summary(client: TestClient, state: SessionState) -> None:
    u1 = _uids(state, 1)[0]
    _rr_upload(client, (("R1", "Slip", 40, 12, 4, f"{u1}; 99999999"),))
    assert state.sra_import_msg is not None
    assert "Imported 1 risk" in state.sra_import_msg
    assert "dropped 1 unmatched" in state.sra_import_msg
    # one-shot: rendering /sra consumes and clears it
    client.get("/sra")
    assert state.sra_import_msg is None


def test_import_banner_shows_on_sra_page(client: TestClient, state: SessionState) -> None:
    u1 = _uids(state, 1)[0]
    _rr_upload(client, (("R1", "Slip", 40, 12, 4, str(u1)),))
    page = client.get("/sra").text
    assert "Imported 1 risk" in page


# ── task-risk import ──────────────────────────────────────────────────────────────────────────


def test_import_task_risk_sets_factors_and_bcwc(client: TestClient, state: SessionState) -> None:
    chosen = _latest_solvable(state)
    assert chosen is not None
    _key, sch, _cpm = chosen
    mpd = sch.calendar.working_minutes_per_day or 480
    u1, u2 = _uids(state, 2)
    _tr_upload(
        client,
        (
            (u1, "n/a", 5.0, 3, 4.0, 7.0),  # factor + valid BC <= WC
            (u2, "n/a", 5.0, 2, 9.0, 3.0),  # inverted BC > WC -> factor set, BC/WC skipped
            (99999999, "ghost", 5, 5, 1, 2),  # unknown uid -> dropped entirely
        ),
    )
    assert state.sra_factors == {u1: 3, u2: 2}
    assert set(state.sra_bcwc) == {u1}  # the inverted and unknown rows contributed no BC/WC
    bc, wc = state.sra_bcwc[u1]
    assert (bc, wc) == (round(4.0 * mpd), round(7.0 * mpd))
    assert state.sra_import_msg is not None
    assert "dropped 1 unmatched" in state.sra_import_msg


def test_import_task_risk_clamps_factor_range(client: TestClient, state: SessionState) -> None:
    u1 = _uids(state, 1)[0]
    _tr_upload(client, ((u1, "n/a", 5.0, 9, "", ""),))  # factor 9 -> clamped to 5
    assert state.sra_factors[u1] == 5


# ── error handling ──────────────────────────────────────────────────────────────────────────


def test_import_rejects_a_non_xlsx_file(client: TestClient, state: SessionState) -> None:
    client.post(
        "/sra/import/risk-register",
        files={"file": ("bad.xlsx", b"not a zip", "application/octet-stream")},
        follow_redirects=False,
    )
    assert state.sra_import_msg is not None
    assert "Could not read that file" in state.sra_import_msg
    assert state.sra_risks == []  # nothing was mutated


def test_import_needs_a_schedule() -> None:
    st = SessionState()
    c = TestClient(create_app(st))
    rows = (("R1", "x", 1, 1, 1, "1"),)
    blob = render_xlsx(TableSet("t", (Table("Risk Register", _RR_HEADERS, rows),)))
    c.post(
        "/sra/import/risk-register",
        files={"file": ("f.xlsx", blob, _XLSX_CT)},
        follow_redirects=False,
    )
    assert st.sra_import_msg is not None
    assert "Load a schedule" in st.sra_import_msg
