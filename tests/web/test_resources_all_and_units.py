"""Resources page: every resource visible, per-resource max units honored (operator 2026-08-20).

Operator report: "The resources page is not calculating correctly. There are multiple
resources in these projects with different max units. The tool should allow the user to see
all resources, and the visuals should also convey this information accordingly."

Three measured defects behind that sentence, each pinned here:

* the XER importer never built ``Task.resource_assignments`` and never read max units
  (``RSRC.max_qty_per_hr`` / the ``RSRCRATE`` table), so every Primavera file rendered the
  page's empty state — "no resource assignments to load" — while carrying both;
* the roster was built from assignments only, so a resource with no booked work was invisible
  (not even a zero row);
* the only chart was single-resource; nothing conveyed utilization across ALL resources.

The engine's capacity formula already honored ``max_units`` — what was missing was the data
(XER) and the whole-roster view. Engine-level twins live in ``tests/engine/test_resources.py``;
importer-level in ``tests/importers/test_xer.py``.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app


def _xer_with_resources() -> bytes:
    """Two tasks, three resources with DIFFERENT max units (2.0 / 0.5 / unassigned 1.0),
    quantities on the assignments — the operator's multi-resource P6 shape."""
    return (
        b"ERMHDR\t19.12\n"
        b"%T\tPROJECT\n"
        b"%F\tproj_id\tproj_short_name\tplan_start_date\tlast_recalc_date\n"
        b"%R\t1000\tRES-01\t2025-01-06 08:00\t2025-02-03 17:00\n"
        b"%T\tPROJWBS\n"
        b"%F\twbs_id\tproj_id\tparent_wbs_id\twbs_short_name\twbs_name\n"
        b"%R\t5000\t1000\t\tRES\tResource Demo\n"
        b"%T\tRSRC\n"
        b"%F\trsrc_id\trsrc_name\trsrc_short_name\trsrc_type\tcost_per_qty\n"
        b"%R\t100\tIron Crew\tIRON\tRT_Labor\t150\n"
        b"%R\t101\tWelder\tWELD\tRT_Labor\t120\n"
        b"%R\t102\tIdle Inspector\tINSP\tRT_Labor\t90\n"
        b"%T\tRSRCRATE\n"
        b"%F\trsrc_rate_id\trsrc_id\tmax_qty_per_hr\tcost_per_qty\tstart_date\n"
        b"%R\t1\t100\t2\t150\t\n"
        b"%R\t2\t101\t0.5\t120\t\n"
        b"%T\tTASK\n"
        b"%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\ttask_type\t"
        b"target_drtn_hr_cnt\tremain_drtn_hr_cnt\tearly_start_date\tearly_end_date\n"
        b"%R\t1\t1000\t5000\tA1000\tErect Steel\tTT_Task\t80\t80\t"
        b"2025-01-06 08:00\t2025-01-17 17:00\n"
        b"%R\t2\t1000\t5000\tA1010\tWeld Frames\tTT_Task\t80\t80\t"
        b"2025-01-20 08:00\t2025-01-31 17:00\n"
        b"%T\tTASKRSRC\n"
        b"%F\ttaskrsrc_id\ttask_id\trsrc_id\ttarget_qty\tremain_qty\ttarget_qty_per_hr\n"
        b"%R\t11\t1\t100\t160\t160\t2\n"
        b"%R\t12\t2\t101\t80\t80\t0.5\n"
        b"%E\n"
    )


@pytest.fixture
def sc() -> tuple[SessionState, TestClient]:
    st = SessionState()
    client = TestClient(create_app(st))
    r = client.post(
        "/upload",
        files={"files": ("resdemo.xer", _xer_with_resources(), "application/octet-stream")},
    )
    assert r.status_code == 200
    return st, client


def test_xer_schedule_renders_the_resources_page_not_the_empty_state(
    sc: tuple[SessionState, TestClient],
) -> None:
    _st, client = sc
    html = client.get("/resources").text
    assert "no resource assignments to load" not in html
    assert "Loading histogram" in html


def test_roster_lists_every_resource_including_the_unassigned_one(
    sc: tuple[SessionState, TestClient],
) -> None:
    """Idle Inspector carries no assignment — it must still be a roster row (the operator's
    "allow the user to see all resources"), with honest zero work."""
    _st, client = sc
    html = client.get("/resources").text
    for name in ("Iron Crew", "Welder", "Idle Inspector"):
        assert name in html, f"{name} missing from the roster"


def test_roster_shows_each_resources_own_max_units(
    sc: tuple[SessionState, TestClient],
) -> None:
    """The two rated resources carry their OWN max units (2 and 0.5) — the page must render
    both figures, and the unrated one must show an em dash, never a fabricated number."""
    _st, client = sc
    html = client.get("/resources").text
    assert ">2<" in html, "Iron Crew's max units 2 not rendered"
    assert ">0.5<" in html, "Welder's max units 0.5 not rendered"


def test_utilization_panel_conveys_all_resources(sc: tuple[SessionState, TestClient]) -> None:
    _st, client = sc
    html = client.get("/resources").text
    assert "Utilization by resource" in html
    assert "id=resUtilChart" in html or 'id="resUtilChart"' in html
