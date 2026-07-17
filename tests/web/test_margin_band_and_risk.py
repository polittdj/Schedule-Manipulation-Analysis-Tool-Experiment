"""Fig 5-30 guideline-band controls + the §7.3.3.2.3 risk-sufficiency API/export (ADR-0254).

Pins: the band control renders the verbatim handbook rows with the cited default rates; POST
/margin/band persists (and is fail-soft on garbage); the band JSON appears only once the phase
dates are entered; month verdicts classify against the band; /api/margin/risk returns the honest
degenerate disclosure on a no-uncertainty fixture with every provenance parameter echoed; the
corrected 50%-consumed citation (§7.3.3.2.3, example-framed) renders instead of the old
§7.3.3.1.6 attribution; and the Excel export states the band + SRA parameters.
"""

from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient

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


def _version(status: str, margin_days: float) -> Schedule:
    return Schedule(
        name=status,
        source_file=f"{status}.mpp",
        project_start=dt.datetime(2026, 1, 5, 8, 0),
        status_date=dt.datetime.fromisoformat(status),
        tasks=(
            _t(1, "Work", 500),
            _t(2, "Schedule MARGIN: pre-delivery", margin_days),
            _t(3, "Deliver SV1", 0, is_milestone=True),
        ),
        relationships=(_r(1, 2), _r(2, 3)),
    )


_MARGINS = [("2026-02-27", 40), ("2026-03-31", 30), ("2026-04-30", 20), ("2026-05-29", 10)]

_BAND_FORM = {
    "action": "apply",
    "phase0": "2026-01-05",
    "phase1": "2026-09-01",
    "phase2": "2027-01-04",
    "phase3": "2027-03-01",
    "low0": "30",
    "high0": "60",
    "low1": "60",
    "high1": "75",
    "low2": "30",
    "high2": "84",
    "watch_pct": "70",
    "ca_pct": "50",
}


def _client(margins: list[tuple[str, float]] | None = None) -> TestClient:
    st = SessionState()
    for status, m in margins or _MARGINS:
        v = _version(status, m)
        st.schedules[v.source_file] = v
    st.target_uid = DELIVER_UID
    return TestClient(create_app(st))


def test_band_control_renders_the_verbatim_rows_and_cited_defaults() -> None:
    body = _client().get("/margin").text
    # the three Fig 5-30 amounts, word for word
    assert "Varies: 1-2 month of schedule margin per year" in body
    assert "Varies: 2-2.5 months of schedule margin per year" in body
    assert "Varies: 1 day per week, 1 week per month, 1 month per year" in body
    # the disclosed conversion + the example framing of the thresholds
    assert "1 month = 30 work days" in body
    assert "example" in body  # thresholds framed as the handbook's example values
    # default rates prefilled
    for v in ("30", "60", "75", "84"):
        assert f'value="{v}"' in body


def test_band_absent_until_configured_then_classifies_months() -> None:
    c = _client()
    assert c.get("/api/margin/dashboard").json()["band"] is None
    r = c.post("/margin/band", data=_BAND_FORM, follow_redirects=False)
    assert r.status_code == 303
    band = c.get("/api/margin/dashboard").json()["band"]
    assert band is not None
    # evaluation points include the phase boundaries (the chart kinks) + the 4 status dates
    point_dates = {p["date"] for p in band["points"]}
    assert {"2026-01-05", "2026-09-01", "2027-01-04", "2027-03-01"} <= point_dates
    # every dated month is classified; this fixture's margins sit below the early-phase band
    assert [m["position"] for m in band["months"]] == ["below", "below", "below", "below"]
    # the page now draws it (the JS reads DATA.band) and the panel survives a reload
    assert '"band":' in c.get("/margin").text


def test_band_post_is_failsoft_and_clear_removes_it() -> None:
    c = _client()
    c.post("/margin/band", data=_BAND_FORM, follow_redirects=False)
    good = c.get("/api/margin/dashboard").json()["band"]
    # garbage dates/rates are ignored — the stored band is untouched
    c.post(
        "/margin/band",
        data={**_BAND_FORM, "phase0": "2028-01-01", "phase1": "not-a-date", "low0": "-9"},
        follow_redirects=False,
    )
    assert c.get("/api/margin/dashboard").json()["band"] == good
    # clear drops the band entirely
    c.post("/margin/band", data={"action": "clear"}, follow_redirects=False)
    assert c.get("/api/margin/dashboard").json()["band"] is None


def test_risk_api_errors_without_schedules_and_discloses_degeneracy() -> None:
    empty = TestClient(create_app(SessionState()))
    assert empty.get("/api/margin/risk").status_code == 400
    c = _client()
    d = c.get("/api/margin/risk").json()
    # this fixture has no three-point estimates and no risks: every iteration is the plan —
    # the read DISCLOSES the point mass and issues no verdict (never fabricated certainty)
    assert d["degenerate"] is True and d["verdict"] is None
    assert d["covered_pct"] == 100.0
    assert d["margin_wd"] == 10.0  # the latest version's 10-day margin, on the SSI all-ML axis
    # provenance: every parameter of the seeded run is echoed
    for key in ("file", "iterations", "seed", "distribution", "occurrence_mode", "correlation"):
        assert key in d
    # deterministic by seed: a second run reproduces the read byte-for-byte
    assert c.get("/api/margin/risk").json() == d


def test_corrected_50pct_citation_renders_as_example_not_7_3_3_1_6() -> None:
    # ADR-0254 doc-truth fix: the 50%-consumed sentence lives in §7.3.3.2.3 (example-framed),
    # not §7.3.3.1.6 as ADR-0230 recorded. The burn-down prose must carry the corrected form.
    body = _client().get("/margin").text
    assert "7.3.3.2.3" in body
    assert "50%-consumed corrective-action threshold" in body
    # the old wrong attribution never renders next to the 50% claim
    assert (
        "50%-consumed corrective-action threshold, Schedule Management Handbook &sect;7.3.3.1.6"
        not in body
    )


def test_risk_dates_realigned_to_the_stored_finish_axis_on_progressed_schedules() -> None:
    # audit F1 (ADR-0256): on a progressed schedule the pure-CPM axis packs completed work at
    # the project start; the SSI result realigns every displayed date to the stored finish.
    # /api/margin/risk must print D on that SAME axis (== the /api/sra/ssi deterministic date),
    # with E landing on the stored finish of the work that precedes the margin.
    st = SessionState()
    sch = Schedule(
        name="prog",
        source_file="prog.mpp",
        project_start=dt.datetime(2026, 1, 5, 8, 0),
        status_date=dt.datetime(2026, 4, 1),
        tasks=(
            Task(
                unique_id=1,
                name="Work A",
                duration_minutes=100 * DAY,
                percent_complete=50,
                remaining_duration_minutes=50 * DAY,
                finish=dt.datetime(2026, 8, 14, 17, 0),
            ),
            Task(
                unique_id=2,
                name="Schedule MARGIN",
                duration_minutes=20 * DAY,
                finish=dt.datetime(2026, 9, 11, 17, 0),
            ),
            Task(
                unique_id=3,
                name="Deliver",
                duration_minutes=0,
                is_milestone=True,
                finish=dt.datetime(2026, 9, 11, 17, 0),
            ),
        ),
        relationships=(_r(1, 2), _r(2, 3)),
    )
    st.schedules["prog.mpp"] = sch
    st.sra_bcwc = {1: (40 * DAY, 70 * DAY)}  # genuine spread so the run is non-degenerate
    c = TestClient(create_app(st))
    risk = c.get("/api/margin/risk").json()
    ssi = c.get("/api/sra/ssi").json()
    assert risk["deterministic_finish_date"] == ssi["deterministic"]["date"] == "2026-09-11"
    assert risk["zero_margin_finish_date"] == "2026-08-14"  # the stored Work finish
    # every percentile row rides the same realigned axis (P50 matches the SRA page's P50)
    p50_risk = next(r["finish_date"] for r in risk["rows"] if r["pct"] == 50.0)
    p50_ssi = next(p["date"] for p in ssi["percentiles"] if p["label"] == "P50")
    assert p50_risk == p50_ssi


def test_export_states_band_and_sra_parameters() -> None:
    c = _client()
    c.post("/margin/band", data=_BAND_FORM, follow_redirects=False)
    x = c.get("/export/xlsx/margin")
    assert x.status_code == 200
    sheets = read_xlsx(x.content)
    names = set(sheets)
    assert any(n.startswith("Figure 5-30 guideline band") for n in names)
    assert any(n.startswith("Figure 5-30 band parameters") for n in names)
    assert any(n.startswith("Risk-based margin sufficienc") for n in names)
    flat = ["|".join(str(c0) for c0 in row) for sheet in sheets.values() for row in sheet]
    assert any("1 month = 30 work days" in f for f in flat)  # the conversion convention
    assert any("2026-01-05, 2026-09-01, 2027-01-04, 2027-03-01" in f for f in flat)  # phase dates
    assert any("below" in f for f in flat)  # the per-status-date position column
    assert any("deterministic by seed" in f for f in flat)  # the SRA provenance row
    assert any(
        "no verdict" in f for f in flat
    )  # the degenerate disclosure, not a fabricated verdict


def test_export_without_band_states_not_configured() -> None:
    x = _client().get("/export/xlsx/margin")
    flat = [
        "|".join(str(c0) for c0 in row) for sheet in read_xlsx(x.content).values() for row in sheet
    ]
    assert any("not configured" in f for f in flat)
