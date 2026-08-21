"""/driving-path opens on the COMPLETE schedule and every loaded schedule is selectable.

Operator (2026-08-21): "on the driving path page … show me the full schedule whichever project
or schedule the user chooses, the user should be able to choose any of the ones loaded … the
full schedule gantt by default like in what drives the date with the same columns by default."

Source pins here; the RENDERED behavior (grid rows, default columns, cross-project switching)
is proven in a real browser by ``test_driving_path_whole_schedule_browser.py``.

* With no source and no target, the page embeds the same whole-schedule workspace /path renders
  (``_path_body`` — ``#pathView`` + ``path.js``), preselecting the chosen file (else the active
  project's latest), its Schedule select offering EVERY loaded session key across projects.
* The trace form's File picker also offers every loaded schedule — grouped by Project — with the
  session KEY as the option value (unique across projects) while ``?file=`` keeps accepting the
  legacy display label (``_find_schedule`` resolves both).
* With a target traced, the tiers views render exactly as before and the workspace is absent
  (one panelkit include per page — the tiers block carries it).
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

_NS = 'xmlns="http://schemas.microsoft.com/project"'


def _mspdi(n_tasks: int, status: str) -> bytes:
    tasks = "".join(
        f"<Task><UID>{i}</UID><Name>T{i}</Name><Duration>PT8H0M0S</Duration></Task>"
        for i in range(1, n_tasks + 1)
    )
    return (
        f"<Project {_NS}><StartDate>2025-01-06T08:00:00</StartDate>"
        f"<StatusDate>{status}</StatusDate><Tasks>{tasks}</Tasks></Project>"
    ).encode()


@pytest.fixture
def sc() -> tuple[SessionState, TestClient]:
    """Two folder Projects: Apollo (2 versions x 3 tasks) and Artemis (1 version x 5 tasks).
    Apollo lands last, so it is the ACTIVE population (ADR-0258 newest-loaded)."""
    st = SessionState()
    client = TestClient(create_app(st))
    files = [
        ("files", ("ArtemisV1.xml", _mspdi(5, "2025-01-15T00:00:00"), "text/xml")),
        ("files", ("ApolloV1.xml", _mspdi(3, "2025-01-10T00:00:00"), "text/xml")),
        ("files", ("ApolloV2.xml", _mspdi(3, "2025-02-10T00:00:00"), "text/xml")),
    ]
    rels = ["Artemis/ArtemisV1.xml", "Apollo/ApolloV1.xml", "Apollo/ApolloV2.xml"]
    meta = json.dumps([{"rel": r, "mtime": 1000 + i} for i, r in enumerate(rels)])
    assert client.post("/upload", files=files, data={"file_meta": meta}).status_code == 200
    active = st.active_population()
    assert active is not None and active[1] == "Apollo"  # the fixture's premise, not a hope
    return st, client


def test_default_state_embeds_the_whole_schedule_workspace(
    sc: tuple[SessionState, TestClient],
) -> None:
    _st, client = sc
    page = client.get("/driving-path").text
    assert "id=pathView" in page and "/static/path.js" in page
    # the workspace's Schedule select offers EVERY loaded key — the other project's too
    assert "id=pathSchedule" in page
    for key in ("ApolloV1", "ApolloV2", "ArtemisV1"):
        assert f'<option value="{key}"' in page, key
    # preselected on the ACTIVE project's latest, matching the page's own anchor
    assert '<option value="ApolloV2" selected>' in page
    # exactly ONE panelkit include (the workspace's own; no tiers block in this state)
    assert page.count("/static/panelkit.js") == 1


def test_choosing_a_file_preselects_it_in_the_workspace(
    sc: tuple[SessionState, TestClient],
) -> None:
    _st, client = sc
    page = client.get("/driving-path?file=ArtemisV1").text
    assert '<option value="ArtemisV1" selected>' in page


def test_workspace_absent_once_a_target_is_traced(sc: tuple[SessionState, TestClient]) -> None:
    _st, client = sc
    page = client.get("/driving-path?target=3").text
    assert "Driving tiers to 3" in page
    assert "id=pathView" not in page  # the trace views own the page; no duplicate workspace
    assert page.count("/static/panelkit.js") == 1  # the tiers block's include, exactly once


def test_file_picker_offers_every_loaded_schedule_grouped_by_project(
    sc: tuple[SessionState, TestClient],
) -> None:
    """The trace form's File select spans ALL loaded schedules (operator 2026-08-21), grouped
    by Project so same-named files from different folders stay tellable apart."""
    _st, client = sc
    page = client.get("/driving-path").text
    for key, label in (
        ("ApolloV1", "ApolloV1.xml"),
        ("ApolloV2", "ApolloV2.xml"),
        ("ArtemisV1", "ArtemisV1.xml"),
    ):
        assert f'<option value="{key}"' in page and f">{label}</option>" in page
    assert 'optgroup label="Apollo"' in page and 'optgroup label="Artemis"' in page


def test_file_from_another_project_scopes_the_trace(sc: tuple[SessionState, TestClient]) -> None:
    """Selecting the OTHER project's schedule traces in it — the banner names it and the
    tiers export link carries its session key (resolvable, no 404)."""
    import re

    _st, client = sc
    page = client.get("/driving-path?target=5&file=ArtemisV1").text
    assert "Driving path computed on <b>ArtemisV1.xml</b>" in page
    m = re.search(r'data-export="(/export/xlsx/driving-tiers/[^"]+)"', page)
    assert m is not None
    assert client.get(m.group(1).replace("&amp;", "&")).status_code == 200


def test_file_param_still_accepts_the_display_label(sc: tuple[SessionState, TestClient]) -> None:
    """Back-compat: bookmarked ``?file=<label>`` URLs (the pre-key form) keep working."""
    _st, client = sc
    page = client.get("/driving-path?target=5&file=ArtemisV1.xml").text
    assert "Driving path computed on <b>ArtemisV1.xml</b>" in page


def test_hint_points_at_the_complete_schedule_below(sc: tuple[SessionState, TestClient]) -> None:
    _st, client = sc
    page = client.get("/driving-path").text
    assert "Enter a source and a target" in page  # the long-standing pin keeps holding
    assert "complete schedule" in page
