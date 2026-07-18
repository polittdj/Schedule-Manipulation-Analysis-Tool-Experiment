"""Find-a-task coverage: the shared name-or-UID Find on every Gantt surface.

Operator ask: "find a task by a name or a part of a name" on ALL Gantt charts. These pins keep
every Gantt-bearing page shipping its Find box wired to the ONE shared implementation
(``SFGantt.findTask``) — and keep /evolution's built-in name/UID search mode present — so a page
edit cannot silently drop or fork the control (pattern: test_gantt_controls_fix.py string pins).
The /sra grid's Find was UID-only (a bespoke pre-shared implementation); it now takes a name or
part of a name like every other grid.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

_GOLDEN_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"


@pytest.fixture
def client() -> TestClient:
    # two versions of the golden project: the multi-version pages (/evolution, /driving-path)
    # only render their control bars — including Find — with a version series loaded
    c = TestClient(create_app(SessionState()))
    c.post(
        "/upload",
        files=[
            ("files", (n, (_GOLDEN_DIR / n).read_bytes(), "text/xml"))
            for n in ("Project2.mspdi.xml", "Project5.mspdi.xml")
        ],
    )
    return c


def test_every_gantt_page_ships_the_name_or_uid_find(client: TestClient) -> None:
    for path, box in (
        ("/analysis/Project5", "id=gridFind"),
        ("/path", "id=pathFind"),
        ("/sra", "id=ssiFind"),
    ):
        page = client.get(path).text
        assert box in page, f"{path} lost its Find box"
        assert "UID or name" in page, f"{path} Find is not the shared name-or-uid control"


def test_driving_path_corridor_ships_the_find(client: TestClient) -> None:
    # the corridor panel (and its Find) renders only once a source→target pair with a real
    # corridor is chosen, so pin BOTH sources of truth: the template string and the JS wiring
    import schedule_forensics.web.app as app_module

    src = Path(app_module.__file__).read_text(encoding="utf-8")
    assert "id=dpFind" in src and "UID or name" in src
    js = client.get("/static/driving_path.js").text
    assert "SFGantt.findTask(mount, dpFind.value" in js


def test_sra_grid_uses_the_shared_findtask_not_a_uid_only_fork(client: TestClient) -> None:
    js = client.get("/static/sra_grid.js").text
    assert "SFGantt.findTask(host" in js  # the one shared implementation (name or UID)


def test_evolution_keeps_its_name_or_uid_search_mode(client: TestClient) -> None:
    page = client.get("/evolution").text
    assert "id=evoFilterText" in page  # the search input
    assert "name / UID search" in page  # the filter-mode option that drives it
