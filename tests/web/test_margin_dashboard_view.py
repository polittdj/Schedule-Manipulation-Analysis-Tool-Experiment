"""Executive Margin Dashboard page + API (NASA Margin/Contingency Burn-Down + MET).

The golden fixtures carry no activity named "margin", so the burn-down needs its own synthetic
versions (a MARGIN buffer on the delivery chain, shrinking version to version). These pin the
page shell, the /api/margin/dashboard contract, the target/erosion wiring, and the empty state.
"""

from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient

from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.reports.xlsx_read import read_xlsx
from schedule_forensics.web.app import SessionState, create_app

DAY = 480
DELIVER_UID = 3


def _t(uid: int, name: str, days: float, **kw: object) -> Task:
    return Task(unique_id=uid, name=name, duration_minutes=int(days * DAY), **kw)  # type: ignore[arg-type]


def _r(p: int, s: int) -> Relationship:
    return Relationship(predecessor_id=p, successor_id=s, type=RelationshipType.FS, lag_minutes=0)


def _version(status: str, margin_days: float, *, named: bool = True) -> Schedule:
    mname = "Schedule MARGIN: pre-delivery" if named else "Buffer block"
    return Schedule(
        name=status,
        source_file=f"{status}.mpp",
        project_start=dt.datetime(2026, 1, 5, 8, 0),
        status_date=dt.datetime.fromisoformat(status),
        tasks=(
            _t(1, "Work", 500),
            _t(2, mname, margin_days),
            _t(3, "Deliver SV1", 0, is_milestone=True),
        ),
        relationships=(_r(1, 2), _r(2, 3)),
    )


_MARGINS = [("2026-02-27", 40), ("2026-03-31", 30), ("2026-04-30", 20), ("2026-05-29", 10)]


def _client(
    margins: list[tuple[str, float]], *, named: bool = True, target: int | None = DELIVER_UID
) -> TestClient:
    st = SessionState()
    for status, m in margins:
        v = _version(status, m, named=named)
        st.schedules[v.source_file] = v
    st.target_uid = target
    return TestClient(create_app(st))


def test_margin_page_renders_both_charts_and_nav_entry() -> None:
    page = _client(_MARGINS).get("/margin")
    assert page.status_code == 200
    body = page.text
    assert 'id="marginBurndownChart"' in body and 'id="marginErosionChart"' in body
    assert "/static/margin_dashboard.js" in body
    assert "Margin Dashboard" in body  # the SETUP nav entry
    assert "trigger" in body.lower()  # the below-requirement takeaway


def test_dashboard_api_carries_the_workbook_columns_and_erosion() -> None:
    d = _client(_MARGINS).get("/api/margin/dashboard").json()
    assert d["have_margin_tasks"] is True
    assert [m["effective_margin_wd"] for m in d["months"]] == [40.0, 30.0, 20.0, 10.0]
    assert all(m["target_name"] == "Deliver SV1" for m in d["months"])
    for m in d["months"]:
        assert m["total_available"] == round(m["effective_margin_wd"] + m["contingency_wd"], 1)
        assert m["nasa_rqmt_wd"] == round(m["days_to_go"] * 30.0 / 365.0, 1)
        assert m["below_requirement"] == (m["effective_margin_wd"] < m["nasa_rqmt_wd"])
    # the erosion trend projects a zero-margin date beyond the last status date
    assert 9.0 < d["erosion_wd_per_month"] < 11.0
    assert dt.date.fromisoformat(d["zero_margin_date"]) > dt.date(2026, 5, 29)


def test_dashboard_carries_planned_column_and_exports() -> None:
    c = _client(_MARGINS)
    d = c.get("/api/margin/dashboard").json()
    # the month-start planned column (workbook F) + margin consumed per period
    assert [m["planned_margin_wd"] for m in d["months"]] == [None, 40.0, 30.0, 20.0]
    assert [m["consumed_wd"] for m in d["months"]] == [None, 10.0, 10.0, 10.0]
    assert "Planned (wd)" in c.get("/margin").text
    # the burn-down + erosion summary export as a real Excel / Word file
    x = c.get("/export/xlsx/margin")
    assert x.status_code == 200 and "spreadsheetml" in x.headers["content-type"]
    assert len(x.content) > 0
    assert c.get("/export/docx/margin").status_code == 200
    assert c.get("/export/bogus/margin").status_code == 404


def test_dashboard_empty_when_no_margin_activity() -> None:
    d = _client(_MARGINS, named=False).get("/api/margin/dashboard").json()
    assert d["have_margin_tasks"] is False
    assert all(m["effective_margin_wd"] == 0.0 for m in d["months"])


def test_dashboard_api_carries_total_margin_and_corrective_flag() -> None:
    d = _client(_MARGINS).get("/api/margin/dashboard").json()
    # BOTH numbers per version (dual): total (sum of durations) alongside effective
    assert [m["total_margin_wd"] for m in d["months"]] == [40.0, 30.0, 20.0, 10.0]
    # the 50%-consumed corrective-action flag: consumed_pct + the boolean trip on the last version
    assert [m["consumed_pct"] for m in d["months"]] == [None, 0.25, round(10 / 30, 4), 0.5]
    assert [m["corrective_action"] for m in d["months"]] == [False, False, False, True]


def test_dashboard_reflects_the_confirmed_margin_overlay() -> None:
    st = SessionState()
    for status, m in _MARGINS:
        v = _version(status, m, named=False)  # the buffer is NOT named "margin"
        st.schedules[v.source_file] = v
    st.target_uid = DELIVER_UID
    client = TestClient(create_app(st))
    # name-based: nothing is recognized as margin
    assert client.get("/api/margin/dashboard").json()["have_margin_tasks"] is False
    # confirm the buffer (UID 2) on one version; the union applies it across the burn-down
    client.post(
        "/margin/confirm", data={"key": "2026-05-29.mpp", "action": "confirm", "uid": ["2"]}
    )
    d = client.get("/api/margin/dashboard").json()
    assert d["have_margin_tasks"] is True
    assert [m["effective_margin_wd"] for m in d["months"]] == [40.0, 30.0, 20.0, 10.0]


def test_dashboard_page_shows_terminology_and_new_columns() -> None:
    body = _client(_MARGINS).get("/margin").text
    assert "MARGIN vs CONTINGENCY vs FLOAT" in body  # F3a cited glossary
    assert "Corrective" in body  # the per-version corrective-action column
    assert "Total (wd)" in body  # the dual-number (sum-of-durations) column


def test_margin_page_empty_state_without_schedules() -> None:
    page = TestClient(create_app(SessionState())).get("/margin")
    assert page.status_code == 200
    assert "Load one or more" in page.text


def _version_cal(status: str, margin_days: float, wmpd: int) -> Schedule:
    """A version whose calendar uses ``wmpd`` working minutes/day — a 1440 (24-hour) day changes the
    work-day BASIS the margin is expressed in vs an 8h (480) day."""
    weekdays = tuple(range(7)) if wmpd >= 1440 else (0, 1, 2, 3, 4)
    return Schedule(
        name=status,
        source_file=f"{status}.mpp",
        project_start=dt.datetime(2026, 1, 5, 8, 0),
        status_date=dt.datetime.fromisoformat(status),
        calendar=Calendar(working_minutes_per_day=wmpd, work_weekdays=weekdays),
        tasks=(
            _t(1, "Work", 500),
            Task(
                unique_id=2,
                name="Schedule MARGIN: pre-delivery",
                duration_minutes=int(margin_days * wmpd),
            ),
            _t(3, "Deliver SV1", 0, is_milestone=True),
        ),
        relationships=(_r(1, 2), _r(2, 3)),
    )


def test_margin_view_and_export_disclose_mixed_basis_and_suppress_erosion() -> None:
    """Audit (ADR-0247): PR-R3 suppresses the erosion fit and discloses the basis change in the
    ENGINE (tested in tests/engine/test_margin_dashboard.py), but the VIEW takeaway and the EXCEL
    export row that surface it to the analyst were untested. An 8h→24h basis change must render the
    disclosure prose on /margin and export a 'mixed — 8h/day vs 24h/day' basis row with '—' (never a
    fabricated erosion rate, Law 2)."""
    st = SessionState()
    for v in (_version_cal("2026-02-27", 40, 480), _version_cal("2026-03-31", 30, 1440)):
        st.schedules[v.source_file] = v
    st.target_uid = DELIVER_UID
    c = TestClient(create_app(st))

    # 1. the API confirms the engine suppressed the fit and flagged the mixed basis
    d = c.get("/api/margin/dashboard").json()
    assert d["erosion_wd_per_month"] is None and d["zero_margin_date"] is None
    assert d["erosion_mixed_basis"] == [480, 1440]

    # 2. the on-screen takeaway DISCLOSES it (not a silent blank)
    body = c.get("/margin").text
    assert "not shown" in body
    assert "different work-day bases" in body
    assert "8h/day vs 24h/day" in body

    # 3. the Excel export states the mixed basis and suppresses the erosion cell with '—' (not 0)
    x = c.get("/export/xlsx/margin")
    assert x.status_code == 200
    sheets = read_xlsx(x.content)
    cells = [cell for sheet in sheets.values() for row in sheet for cell in row]
    assert "mixed — 8h/day vs 24h/day" in cells  # the "Work-day basis" value
    erosion_rows = [
        row
        for sheet in sheets.values()
        for row in sheet
        if row and row[0] == "Erosion (work days / month)"
    ]
    assert erosion_rows and erosion_rows[0][1] == "—"  # suppression dash, not a fabricated number
    assert c.get("/export/docx/margin").status_code == 200
