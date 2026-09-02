"""/volatility wears the Claude Design "How stable is the path" layout (operator 2026-09-02):
masthead + ONE master cursor strip with version chips, then the five numbered panels of the
prototype (① Stability signal · ② Flow of the path · ③ Membership matrix · ④ Transition
ribbons · ⑤ the scoreboard as the ▦ DATA drawer) — with every existing visual, control, id and
data blob intact ("don't modify any of the functionality"). Red-first: the pre-restyle page
had a flat ten-tile mosaic and no cursor strip.
"""

from __future__ import annotations

import datetime as dt
import json
import re

from fastapi.testclient import TestClient

from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import SessionState, create_app

DAY = 480
#: every host / control the ten visuals, the stepper and the scoreboard already used — all must
#: survive the restyle (the JS finds them by these ids)
IDS = (
    "volGauge",
    "volChurn",
    "volFlow",
    "volArea",
    "volHeatmap",
    "volTenure",
    "volDwell",
    "volJumpers",
    "volStrips",
    "volRibbon",
    "volTable",
    "volPrev",
    "volNext",
    "volPlay",
    "volLabel",
    "volData",
)


def _version(name: str, status: str, chain: list[int]) -> Schedule:
    start = dt.datetime(2026, 1, 5, 8)
    tasks = [
        Task(
            unique_id=u,
            name=f"T{u}",
            duration_minutes=DAY * (3 if u in chain else 1),
            start=start,
            finish=start + dt.timedelta(days=3 if u in chain else 1),
        )
        for u in (1, 2, 3, 4)
    ]
    return Schedule(
        name=name,
        source_file=f"{name}.xml",
        project_start=start,
        status_date=dt.datetime.fromisoformat(status),
        tasks=tuple(tasks),
    )


def _client() -> tuple[TestClient, SessionState]:
    st = SessionState()
    c = TestClient(create_app(st))
    c.__enter__()
    for i, (name, status, chain) in enumerate(
        [
            ("v1", "2026-01-30T17:00", [1, 2]),
            ("v2", "2026-02-27T17:00", [1, 3]),
            ("v3", "2026-03-27T17:00", [1, 3]),
        ]
    ):
        st.schedules[name] = _version(name, status, chain)
        st.file_meta[name] = (None, 1_700_000_000_000 + i)
    return c, st


def test_page_carries_the_five_design_panels_in_order_and_every_original_id() -> None:
    c, _ = _client()
    html = c.get("/volatility").text
    panels = re.findall(r'<section class="vol-block[^"]*" data-vol-panel="(\d)"', html)
    assert panels == ["1", "2", "3", "4", "5"], panels
    for pid in IDS:
        assert f"id={pid}" in html or f'id="{pid}"' in html, f"lost #{pid}"
    # the master cursor strip: Prev / Play / Next plus ONE chip per version and the DD pill
    assert "id=volCursor" in html or 'id="volCursor"' in html
    chips = re.findall(r'class="vol-chip[^"]*" data-idx="(\d+)"', html)
    assert chips == ["0", "1", "2"], chips
    assert "id=volKpi" in html or 'id="volKpi"' in html
    # the data blob still rides the page unchanged in shape
    blob = re.search(r'<script type="application/json" id=volData>(.*?)</script>', html, re.S)
    assert blob
    d = json.loads(blob.group(1))
    assert {"versions", "tasks", "pairs", "stability"} <= set(d)
    # the scoreboard is the ▦ DATA drawer of the fifth panel, still exportable
    assert "/export/xlsx/volatility" in html
