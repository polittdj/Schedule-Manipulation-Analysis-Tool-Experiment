"""Multi-.xer version grouping (operator report 2026-08-20).

The operator loaded several ``.xer`` status updates of ONE project and Mission Control's
cross-version visuals stayed inactive ("Needs at least two loaded versions of the active
project"), while the same workflow with ``.mpp``-derived MSPDI versions works. Root cause:
loose files group into Projects by ``Schedule.project_title``; the XER importer filled that
from ``PROJECT.proj_short_name`` — P6's *Project ID*, which is mandatory (so the files never
pool as untitled) and which the standard per-update copy workflow renames every period (P6
requires unique Project IDs inside one EPS). N updates therefore shattered into N one-version
populations. MSPDI grouped because ``<Title>`` is a document property that survives copies.

The fix has three legs, each pinned here:

* the XER importer takes ``project_title`` from the root ``PROJWBS`` row's ``wbs_name`` — the
  P6 *Project Name*, the true analogue of the MSPDI ``<Title>`` and stable across per-update
  copies — falling back to ``proj_short_name`` (``Schedule.name`` is unchanged either way);
* a project name shared across FORMATS groups cross-format (an .mpp Title and a .xer project
  name are the same grouping key), which is what makes future .mpp↔.xer comparison possible;
* when the internal names genuinely differ, the operator can COMBINE loaded projects into one
  from Portfolio (``POST /project/combine``) — reusing the folder-beats-title grouping lever —
  and Mission Control's degrade note names the other loaded Projects instead of leaving a
  silent mystery.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

_NS = 'xmlns="http://schemas.microsoft.com/project"'


def _xer(
    short_name: str,
    project_name: str | None,
    recalc: str,
    *,
    plan_start: str = "2020-01-06 08:00",
) -> bytes:
    """A minimal two-task XER: PROJECT + (optional) PROJWBS root + TASK/TASKPRED.

    ``short_name`` plays P6's Project ID (unique per EPS — differs across per-update
    copies); ``project_name`` is the root PROJWBS ``wbs_name`` (the P6 Project Name,
    which survives copies); ``recalc`` is the data date (``last_recalc_date``).
    """
    wbs = (
        "%T\tPROJWBS\n"
        "%F\twbs_id\tproj_id\tparent_wbs_id\twbs_short_name\twbs_name\n"
        f"%R\t5000\t1000\t\t{short_name}\t{project_name}\n"
        if project_name is not None
        else ""
    )
    return (
        "ERMHDR\t19.12\n"
        "%T\tPROJECT\n"
        "%F\tproj_id\tproj_short_name\tplan_start_date\tplan_end_date\tlast_recalc_date\n"
        f"%R\t1000\t{short_name}\t{plan_start}\t2020-12-18 17:00\t{recalc}\n"
        f"{wbs}"
        "%T\tTASK\n"
        "%F\ttask_id\tproj_id\twbs_id\ttask_code\ttask_name\ttask_type\t"
        "target_drtn_hr_cnt\tremain_drtn_hr_cnt\tearly_start_date\tearly_end_date\n"
        "%R\t1\t1000\t5000\tA1000\tMobilize\tTT_Task\t40\t40\t"
        f"{plan_start}\t2020-01-10 17:00\n"
        "%R\t2\t1000\t5000\tA1010\tExcavate\tTT_Task\t40\t40\t"
        "2020-01-13 08:00\t2020-01-17 17:00\n"
        "%T\tTASKPRED\n"
        "%F\ttask_pred_id\ttask_id\tpred_task_id\tpred_type\tlag_hr_cnt\n"
        "%R\t9\t2\t1\tPR_FS\t0\n"
        "%E\n"
    ).encode()


def _mspdi(title: str, status: str) -> bytes:
    return (
        f"<Project {_NS}><Title>{title}</Title>"
        "<StartDate>2020-01-06T08:00:00</StartDate>"
        f"<StatusDate>{status}</StatusDate>"
        "<Tasks><Task><UID>1</UID><Name>A</Name><Duration>PT40H0M0S</Duration></Task></Tasks>"
        "</Project>"
    ).encode()


@pytest.fixture
def sc() -> tuple[SessionState, TestClient]:
    st = SessionState()
    return st, TestClient(create_app(st))


def _upload(client: TestClient, *files: tuple[str, bytes]) -> None:
    resp = client.post(
        "/upload",
        files=[("files", (name, blob, "application/octet-stream")) for name, blob in files],
    )
    assert resp.status_code in (200, 303)


NEED2 = "Needs at least two loaded versions"


def test_xer_updates_with_distinct_short_names_form_one_population(
    sc: tuple[SessionState, TestClient],
) -> None:
    """Two updates of ONE project — same P6 Project Name, per-update Project IDs
    (JUICE-M02 → JUICE-M03), consecutive data dates — must be ONE two-version population,
    and Mission Control's cross-version tiles must activate."""
    st, client = sc
    _upload(
        client,
        ("v1.xer", _xer("JUICE-M02", "Juice UVS IMS", "2020-02-29 17:00")),
        ("v2.xer", _xer("JUICE-M03", "Juice UVS IMS", "2020-03-31 17:00")),
    )
    assert len(st.schedules) == 2  # both files imported
    pops = st.populations()
    assert len(pops) == 1, f"expected one population, got {[(p[0], p[2]) for p in pops]}"
    assert sorted(pops[0][2]) == sorted(st.schedules)  # both keys inside it
    assert len(st.ordered()) == 2  # the analysis population sees both versions
    html = client.get("/mission").text
    assert NEED2 not in html
    assert "Needs at least two analyzable versions" not in html


def test_a_single_xer_still_degrades_the_cross_version_tiles(
    sc: tuple[SessionState, TestClient],
) -> None:
    """True-positive twin: with ONE loaded version the degrade note must still appear —
    proving the absence assertion above can fail for the right reason."""
    _st, client = sc
    _upload(client, ("v1.xer", _xer("JUICE-M02", "Juice UVS IMS", "2020-02-29 17:00")))
    assert NEED2 in client.get("/mission").text


def test_mspdi_and_xer_of_one_project_group_cross_format(
    sc: tuple[SessionState, TestClient],
) -> None:
    """An .mpp-derived MSPDI Title and a .xer P6 Project Name that match are the SAME
    project identity — the two formats group into one population (the operator's
    forward-looking .mpp ↔ .xer comparison)."""
    st, client = sc
    _upload(
        client,
        ("feb.xml", _mspdi("Juice UVS IMS", "2020-02-29T17:00:00")),
        ("mar.xer", _xer("JUICE-M03", "Juice UVS IMS", "2020-03-31 17:00")),
    )
    pops = st.populations()
    assert len(pops) == 1, f"expected one cross-format population, got {len(pops)}"
    assert len(st.ordered()) == 2


def test_operator_can_combine_projects_into_one_from_portfolio(
    sc: tuple[SessionState, TestClient],
) -> None:
    """When the internal names genuinely differ (here: two different P6 Project Names),
    automatic grouping must NOT merge them — but the operator can, explicitly, from
    Portfolio. Combining rebuilds the populations as ONE project and activates the wall."""
    st, client = sc
    _upload(
        client,
        ("a.xer", _xer("ALPHA-01", "Alpha IMS", "2020-02-29 17:00")),
        ("b.xer", _xer("BRAVO-01", "Bravo IMS", "2020-03-31 17:00")),
    )
    pops = st.populations()
    assert len(pops) == 2  # honestly separate until the operator says otherwise
    resp = client.post(
        "/project/combine",
        data={"pids": [p[0] for p in pops], "title": "Alpha IMS"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    combined = st.populations()
    assert len(combined) == 1, f"combine left {len(combined)} populations"
    assert sorted(combined[0][2]) == sorted(st.schedules)
    assert len(st.ordered()) == 2
    assert NEED2 not in client.get("/mission").text
    # the combined grouping shows up in Portfolio as one project
    assert combined[0][1] == "Alpha IMS"


def test_combine_is_fail_soft_on_bad_input(sc: tuple[SessionState, TestClient]) -> None:
    """Unknown pids / fewer than two pids / blank title never throw and never regroup."""
    st, client = sc
    _upload(
        client,
        ("a.xer", _xer("ALPHA-01", "Alpha IMS", "2020-02-29 17:00")),
        ("b.xer", _xer("BRAVO-01", "Bravo IMS", "2020-03-31 17:00")),
    )
    before = [p[0] for p in st.populations()]
    for payload in (
        {"pids": before[:1], "title": "One"},  # fewer than two
        {"pids": ["title:ghost", "title:phantom"], "title": "Ghosts"},  # unknown pids
        {"pids": before, "title": "   "},  # blank title
    ):
        resp = client.post("/project/combine", data=payload, follow_redirects=False)
        assert resp.status_code == 303
        assert [p[0] for p in st.populations()] == before


def test_mission_note_names_the_other_loaded_projects(
    sc: tuple[SessionState, TestClient],
) -> None:
    """With >1 Project loaded, the degrade note must explain WHERE the other files went —
    not leave 'load another schedule update' as a silent mystery when updates ARE loaded."""
    _st, client = sc
    _upload(
        client,
        ("a.xer", _xer("ALPHA-01", "Alpha IMS", "2020-02-29 17:00")),
        ("b.xer", _xer("BRAVO-01", "Bravo IMS", "2020-03-31 17:00")),
    )
    html = client.get("/mission").text
    assert NEED2 in html  # still degraded — the two files are different Projects
    assert "grouped into a different Project" in html
    assert "Portfolio" in html
