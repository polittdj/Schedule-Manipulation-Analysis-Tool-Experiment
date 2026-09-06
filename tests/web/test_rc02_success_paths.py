"""RC-02 (WP6b, ADR-0467): the three routes the route-coverage instrument found reached but never
answered 2xx/3xx in the whole suite — ``GET /export/{fmt}/ribbon-drill/{name}``,
``GET /export/{fmt}/resource-drill`` and ``POST /sra/factor-table`` — each driven through its
success path with real inputs (a ribbon metric that has offenders, a resource-period bar that
exists, a five-row factor form), so the instrument's "never a success" bucket empties for them.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.engine.metrics.ribbon import ribbon_offender_map
from schedule_forensics.engine.resources import compute_resource_loading
from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"


@pytest.fixture(scope="module")
def loaded() -> tuple[SessionState, TestClient, str]:
    st = SessionState()
    client = TestClient(create_app(st))
    data = (GOLDEN / "Project5.mspdi.xml").read_bytes()
    files = {"files": ("Project5.mspdi.xml", data, "text/xml")}
    assert client.post("/upload", files=files).status_code == 200
    (key,) = list(st.schedules)
    return st, client, key


def test_ribbon_drill_export_answers_200_for_a_metric_with_offenders(loaded) -> None:  # type: ignore[no-untyped-def]
    st, client, key = loaded
    a = st.analysis_for(key, st.schedules[key])
    offenders = ribbon_offender_map(a.scoped, a.cpm, a.audit)
    metric = next(m for m, uids in offenders.items() if uids)
    resp = client.get(f"/export/xlsx/ribbon-drill/{key}", params={"metric": metric})
    assert resp.status_code == 200 and resp.content[:2] == b"PK", (metric, resp.status_code)


def test_resource_drill_export_answers_200_for_a_real_bar(loaded) -> None:  # type: ignore[no-untyped-def]
    st, client, key = loaded
    a = st.analysis_for(key, st.schedules[key])
    loading = compute_resource_loading(a.scoped, a.cpm, "month")
    res = next(r for r in loading.resources if r.series)
    resp = client.get(
        "/export/xlsx/resource-drill",
        params={"resource": res.resource_id, "period": res.series[0].period, "bucket": "month"},
    )
    assert resp.status_code == 200 and resp.content[:2] == b"PK", resp.status_code


def test_factor_table_post_redirects_and_stores_the_clamped_ladder(loaded) -> None:  # type: ignore[no-untyped-def]
    st, client, _key = loaded
    form = {f"sub{f}": str(s) for f, s in ((1, 150), (2, 40), (3, 30), (4, 20), (5, 10))}
    form |= {f"add{f}": str(a) for f, a in ((1, 10), (2, 20), (3, 30), (4, 400), (5, 50))}
    resp = client.post("/sra/factor-table", data=form, follow_redirects=False)
    assert resp.status_code == 303 and resp.headers["location"] == "/sra"
    assert st.sra_factor_rows[0] == (1, 100.0, 10.0)  # sub clamped to 100
    assert st.sra_factor_rows[3] == (4, 20.0, 300.0)  # add clamped to 300
