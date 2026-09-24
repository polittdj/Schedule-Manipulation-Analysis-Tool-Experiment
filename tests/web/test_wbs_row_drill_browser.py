"""/wbs: every row of BOTH pivots opens its WBS branch's activities — RENDERED (R-22, ADR-0530).

ADR-0471 ported the "Library WBS Rollup" layout and named the mock's row click ("open this
branch's activities") as an omission, priced as R-22: the SPI bar already drilled a group, but
only a group with a computable SPI(t) HAS a bar, and a table row was inert. ``wbs.js`` now marks
every body row of the completion pivot and the earned-schedule pivot with the same
``SFDrill.mark`` the bar uses (the group's own ``uids``, keyed by the WBS name in the row header),
so a click on any row lists that branch — the identical overlay the bar opens.

Red-first on the pristine tree: no ``tr.sf-drill`` on the page (0 of 2 x groups); the click test
cannot find a row to click. Markup is not evidence in this repo — the click-through is
Chromium-verified.
"""

from __future__ import annotations

import re
import socket
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app
from web.browser_chrome import chrome_kwargs

REPO = Path(__file__).resolve().parents[2]
GOLDEN = REPO / "tests" / "fixtures" / "golden" / "project2_5" / "Project5.mspdi.xml"
KEY = "Project5"


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = int(s.getsockname()[1])
    s.close()
    return port


@pytest.fixture(scope="module")
def served() -> Any:
    pytest.importorskip("playwright", reason="playwright not installed (runtime stays stdlib-only)")
    import uvicorn

    app = create_app(SessionState())
    with TestClient(app) as c:
        files = [("files", (f"{KEY}.mspdi.xml", GOLDEN.read_bytes(), "text/xml"))]
        assert c.post("/upload", files=files).status_code == 200
        groups = c.get(f"/api/wbs/{KEY}").json()["groups"]
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(150):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}", groups
    server.should_exit = True


@pytest.fixture(scope="module")
def browser() -> Any:
    pytest.importorskip("playwright", reason="playwright not installed (runtime stays stdlib-only)")
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    b = pw.chromium.launch(**chrome_kwargs())
    yield b
    b.close()
    pw.stop()


_ROWS = """() => [...document.querySelectorAll('table.wbs-table tr')].map((tr) => ({
  head: tr.querySelector('th') ? tr.querySelector('th').textContent : null,
  drill: tr.classList.contains('sf-drill'),
  uids: tr.getAttribute('data-uids'), title: tr.getAttribute('data-title'),
  file: tr.getAttribute('data-file')}))"""


def _open(browser: Any, served: tuple[str, list[dict[str, Any]]]) -> Any:
    page = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{served[0]}/wbs/{KEY}", wait_until="load")
    page.wait_for_selector("#wbsChart svg", timeout=30000)
    page.wait_for_timeout(500)
    page._sf_errors = errors
    return page


def test_every_pivot_row_carries_its_branch_drill(
    browser: Any, served: tuple[str, list[dict[str, Any]]]
) -> None:
    groups = served[1]
    assert len(groups) >= 10, "fixture too small to mean anything"
    page = _open(browser, served)
    rows = page.evaluate(_ROWS)
    by_name = {g["wbs"]: g for g in groups}
    header = [r for r in rows if r["head"] == "WBS"]
    body = [r for r in rows if r["head"] != "WBS"]
    assert len(header) == 2 and not any(r["drill"] for r in header)  # column headers stay inert
    assert len(body) == 2 * len(groups), (len(body), len(groups))
    marked = [r for r in body if r["drill"]]
    assert len(marked) == 2 * len(groups), f"{len(marked)} of {2 * len(groups)} rows drill"
    for r in marked:
        g = by_name[r["head"]]
        assert r["uids"] and len(r["uids"].split(",")) == g["total"], r["head"]
        assert r["title"] == f"WBS {g['wbs']}" and r["file"] == KEY
    assert page._sf_errors == []
    page.context.close()


def test_a_row_click_opens_the_branch_activities_overlay(
    browser: Any, served: tuple[str, list[dict[str, Any]]]
) -> None:
    groups = served[1]
    page = _open(browser, served)
    # a row of the COMPLETION pivot (the first table), for a group with NO SPI(t) bar when one
    # exists — the row is that branch's only drill
    target = next((g for g in groups if g["spi_t"] is None), groups[0])
    # the row whose HEADER is exactly this WBS name — a substring match ("6" is inside "16")
    # picked another branch's row and read that branch's count (found red-first, by the count)
    row = (
        page.locator("table.wbs-table")
        .first.locator("tr.sf-drill")
        .filter(has=page.locator("th", has_text=re.compile(rf"^{re.escape(target['wbs'])}$")))
    )
    assert row.count() == 1, (target["wbs"], row.count())
    row.first.locator("td").first.click()
    page.wait_for_selector("#sfDrillOverlay", timeout=10000)
    page.wait_for_selector("#sfDrillOverlay .sf-drill-grid td", timeout=15000)
    n = page.evaluate(
        "() => [...document.querySelectorAll('#sfDrillOverlay .sf-drill-grid tr')]"
        ".filter((tr) => tr.querySelector('td')).length"
    )
    assert n == target["total"], (n, target["total"])
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
    assert page.locator("#sfDrillOverlay").count() == 0
    assert page._sf_errors == []
    page.context.close()
