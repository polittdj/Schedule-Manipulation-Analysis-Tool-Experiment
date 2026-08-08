"""The /integrity logic-change diagram in a REAL browser, in ALL FOUR themes (2026-08-08).

Markup alone is not evidence (the standing rank-2/D1 lesson): the diagram's removed/added
semantics are carried by tokens (``--bad`` / ``--ok``) and a line-through — a theme could
resolve either into invisibility without changing one byte of HTML. Measured per theme:

* the removed-link row is genuinely on screen (a real box, not a collapsed one);
* the arrow's computed colour differs from the node text colour (the --bad token resolved to
  something, not inherited ink) and carries the line-through strike;
* the effect chip (the measured revert effect) is on screen inside the row.

Skips unless playwright + the bundled chromium are present (the test_act3_themes_chromium
posture — the runtime stays stdlib-only, Law 1)."""

from __future__ import annotations

import datetime as dt
import socket
import threading
import time
from pathlib import Path
from typing import Any

import pytest

CHROME = Path("/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

pytest.importorskip("playwright", reason="playwright not installed (deliberate: see module docs)")
pytestmark = pytest.mark.skipif(not CHROME.exists(), reason=f"bundled chromium not at {CHROME}")

THEMES = ("console", "daylight", "apollo", "jarvis")


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = int(s.getsockname()[1])
    s.close()
    return port


@pytest.fixture(scope="module")
def served() -> Any:
    import uvicorn

    from schedule_forensics.model.calendar import Calendar
    from schedule_forensics.model.relationship import Relationship, RelationshipType
    from schedule_forensics.model.schedule import Schedule
    from schedule_forensics.model.task import Task
    from schedule_forensics.web.app import SessionState, create_app

    fs = RelationshipType.FS
    cal = Calendar(name="Std")
    start = dt.datetime(2026, 1, 7)
    tasks = (
        Task(unique_id=1, name="Dig", duration_minutes=2400),
        Task(unique_id=2, name="Pour", duration_minutes=2400),
        Task(unique_id=3, name="Roof", duration_minutes=480),
        Task(unique_id=4, name="Wire", duration_minutes=480),
    )
    prior = Schedule(
        name="Job",
        source_file="A.mpp",
        project_start=start,
        status_date=dt.datetime(2026, 1, 7),
        calendar=cal,
        tasks=tasks,
        relationships=(
            Relationship(predecessor_id=1, successor_id=2, type=fs),
            Relationship(predecessor_id=2, successor_id=3, type=fs),
            Relationship(predecessor_id=4, successor_id=3, type=fs),
        ),
    )
    current = prior.model_copy(
        update={
            "source_file": "B.mpp",
            "status_date": dt.datetime(2026, 2, 4),
            "relationships": (
                Relationship(predecessor_id=1, successor_id=2, type=fs),
                Relationship(predecessor_id=4, successor_id=3, type=fs),
            ),
        }
    )
    st = SessionState()
    app = create_app(st)
    st.schedules["A.mpp"] = prior
    st.schedules["B.mpp"] = current
    st.set_target(3)

    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


def test_logic_diagram_reads_in_all_four_themes(served: str) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(CHROME))
        page = browser.new_page(viewport={"width": 1360, "height": 900})
        page.goto(served + "/integrity?a=0&b=1", wait_until="domcontentloaded")
        page.wait_for_selector(".logic-row.removed", timeout=10000)
        for theme in THEMES:
            page.evaluate(f"() => document.documentElement.setAttribute('data-theme','{theme}')")
            page.wait_for_timeout(80)
            probe = page.evaluate(
                """() => {
                  const row = document.querySelector('.logic-row.removed');
                  const arrow = row.querySelector('.logic-arrow');
                  const node = row.querySelector('.logic-node');
                  const chip = row.querySelector('.logic-effect');
                  const rb = row.getBoundingClientRect();
                  const cb = chip.getBoundingClientRect();
                  return {
                    rowW: rb.width, rowH: rb.height,
                    chipW: cb.width, chipH: cb.height,
                    arrowColor: getComputedStyle(arrow).color,
                    nodeColor: getComputedStyle(node).color,
                    strike: getComputedStyle(arrow).textDecorationLine,
                    arrowText: arrow.textContent,
                  };
                }"""
            )
            assert probe["rowW"] > 100 and probe["rowH"] > 10, (theme, probe)
            assert probe["chipW"] > 20 and probe["chipH"] > 5, (theme, probe)
            # the --bad token resolved: the arrow is NOT just inheriting the node ink
            assert probe["arrowColor"] != probe["nodeColor"], (theme, probe)
            assert "line-through" in probe["strike"], (theme, probe)
            assert "FS" in probe["arrowText"], (theme, probe)
        browser.close()
