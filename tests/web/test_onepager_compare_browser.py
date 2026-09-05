"""The One-Pager COMPARE in a real browser (ADR-0465): the two slots, the painted delta encoding,
the refused stray drop, the four themes, the download.

The oracles read the painted SVG — a ghost per prior position, an arrow per moved finish pointing
the way the finish moved, a tag per NEW / REMOVED row, the delta text on the label, the summary
column — so a painter that drew the layout wrong fails here even though the layout tests pass.
Red-first (2026-09-05): before the painter existed the page painted no ``svg.opc-svg``.
"""

from __future__ import annotations

import base64
import datetime as dt
import io
import socket
import threading
import time
import zipfile
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app
from web.browser_chrome import chrome_kwargs
from web.onepager_twin import TWIN_ROWS, twin_xlsx
from web.test_onepager_compare_page import CURRENT_ROWS

TODAY = dt.date(2026, 9, 1)
THEMES = ("console", "daylight", "apollo", "jarvis")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="module")
def served() -> Any:
    pytest.importorskip("playwright", reason="playwright not installed (runtime stays stdlib-only)")
    import uvicorn

    st = SessionState()
    st.onepager_today = TODAY
    app = create_app(st)
    with TestClient(app):
        pass
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(150):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
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


@pytest.fixture(scope="module")
def sheets(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    d = tmp_path_factory.mktemp("onepager_compare")
    prior, current = d / "March_baseline.xlsx", d / "April_update.xlsx"
    prior.write_bytes(twin_xlsx(TWIN_ROWS))
    current.write_bytes(twin_xlsx(CURRENT_ROWS))
    return prior, current


_PAINTED = """() => {
  const q = s => document.querySelectorAll(s);
  const arrows = [...q('.opc-item .opc-arrow')].map(a => ({
    item: a.closest('.opc-item').dataset.status,
    dx: Number(a.getAttribute('x2')) - Number(a.getAttribute('x1')),
  }));
  return {
    svg: !!document.querySelector('svg.opc-svg'),
    bars: q('.op-bar').length, diamonds: q('.op-diamond').length,
    ghosts: q('.opc-ghost').length, ghostDiamonds: q('.opc-ghost-ms').length,
    arrows, heads: q('.opc-arrow-head').length,
    headsAtEnd: [...q('.opc-item .opc-arrow-head')].filter(h => {
      const line = h.previousElementSibling;
      const pts = h.getAttribute('points').split(' ').map(p => Number(p.split(',')[0]));
      const x1 = Number(line.getAttribute('x1')), x2 = Number(line.getAttribute('x2'));
      // the tip sits at the line's END and the head's base lies back toward its start
      return pts[0] === x2 && Math.sign(pts[0] - pts[1]) === Math.sign(x2 - x1);
    }).length,
    deltas: [...q('.opc-delta')].map(t => t.textContent.trim()),
    badges: [...q('.opc-badge-text')].map(t => t.textContent),
    statuses: [...q('.opc-item')].map(g => g.dataset.status),
    summaries: q('.opc-summary').length, sumLines: q('.opc-sum-text').length,
    dd: q('.ch-dd line').length, captions: q('.ch-at').length,
    legend: q('.op-legend-item').length, lanes: q('.op-lane-name-bg').length,
  };
}"""


def _load_both(page: Any, served: str, sheets: tuple[Path, Path]) -> None:
    """Load the pair into BOTH slots unconditionally — the served session is shared by the module,
    and another test may have left a different list in a slot."""
    page.goto(served + "/onepager-compare")
    with page.expect_navigation():
        page.set_input_files("#opcFilePrior", str(sheets[0]))
    with page.expect_navigation():
        page.set_input_files("#opcFileCurrent", str(sheets[1]))
    page.wait_for_selector("svg.opc-svg")


def test_the_two_slots_upload_and_the_delta_encoding_is_painted(
    browser: Any, served: str, sheets: tuple[Path, Path]
) -> None:
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(served + "/onepager-compare")
    assert (
        page.locator("#opcDropPrior").is_visible() and page.locator("#opcDropCurrent").is_visible()
    )
    assert not page.locator("svg.opc-svg").count()
    with page.expect_navigation():
        page.set_input_files("#opcFilePrior", str(sheets[0]))  # the change handler submits the form
    assert "Loaded March_baseline.xlsx" in page.inner_text("#opcSlotPrior")
    assert not page.locator("svg.opc-svg").count()  # one list is not a comparison
    with page.expect_navigation():
        page.set_input_files("#opcFileCurrent", str(sheets[1]))
    page.wait_for_selector("svg.opc-svg")
    got = page.evaluate(_PAINTED)
    assert got["svg"] and got["lanes"] == 7 and got["summaries"] == 7 and got["sumLines"] >= 7
    # 17 rows: 16 current (one of them NEW) + 1 REMOVED; 15 ghosts (every row with a prior),
    # one of them a diamond ghost under the TRR bar; the REMOVED row has no solid shape
    assert len(got["statuses"]) == 17 and got["ghosts"] == 16 and got["ghostDiamonds"] == 6
    assert got["bars"] + got["diamonds"] == 16
    # three moved finishes: two slips point right, the pull-in points left; every arrow has a head
    slips = [a for a in got["arrows"] if a["item"] == "slipped"]
    pulls = [a for a in got["arrows"] if a["item"] == "pulled in"]
    assert len(slips) == 2 and all(a["dx"] > 0 for a in slips)
    assert len(pulls) == 1 and pulls[0]["dx"] < 0 and got["heads"] == 3 + 2  # + the legend's two
    assert got["headsAtEnd"] == 3  # each item arrow's head sits at the end the finish moved TO
    assert sorted(got["deltas"]) == ["+19 cal d", "+30 cal d", "\u22127 cal d"]
    assert sorted(got["badges"]) == ["NEW", "REMOVED"]
    assert got["dd"] == 1 and got["captions"] == 2 and got["legend"] == 7 + 7
    # the DD marker is today's line at the layout's x
    x = page.evaluate("() => Number(document.querySelector('.ch-dd line').getAttribute('x1'))")
    lay_x = page.evaluate(
        "() => JSON.parse(document.getElementById('opcData').textContent).today_x"
    )
    assert x == pytest.approx(lay_x)
    # ▦ DATA reveals the compared rows with their delta columns
    page.click("[data-sf-data]")
    assert page.locator(".sf-drawer").is_visible()
    assert page.locator(".opc-table tbody tr").count() == 17
    assert "+30" in page.inner_text(".opc-table")
    assert errors == []
    page.close()


def test_a_drop_on_a_slot_loads_that_slot_and_a_stray_drop_is_refused(
    browser: Any, served: str
) -> None:
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.goto(served + "/onepager-compare")
    if page.locator("form.op-clear-form").count():
        with page.expect_navigation():
            page.click("form.op-clear-form button")
    page.wait_for_selector("#opcDropPrior")
    b64 = base64.b64encode(twin_xlsx(TWIN_ROWS)).decode()
    drop = """([b64, target]) => {
      const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
      const file = new File([bytes], 'dropped list.xlsx', {type: 'application/octet-stream'});
      const dt = new DataTransfer(); dt.items.add(file);
      (target ? document.querySelector(target) : window).dispatchEvent(
        new DragEvent('drop', {dataTransfer: dt, bubbles: true, cancelable: true}));
    }"""
    # a drop OUTSIDE both slots is refused with the hint — nothing uploads, the page stays put
    page.evaluate(drop, [b64, None])
    page.wait_for_timeout(300)
    assert page.locator("#opcHint").is_visible()
    assert "never guesses" in page.inner_text("#opcHint")
    assert "Nothing loaded yet." in page.inner_text("#opcSlotPrior")
    assert "Nothing loaded yet." in page.inner_text("#opcSlotCurrent")
    # a drop ON the current slot loads the CURRENT list, and only it
    with page.expect_navigation():
        page.evaluate(drop, [b64, "#opcDropCurrent"])
    page.wait_for_selector("#opcSlotCurrent")
    assert "Loaded dropped list.xlsx" in page.inner_text("#opcSlotCurrent")
    assert "Nothing loaded yet." in page.inner_text("#opcSlotPrior")
    assert "as the CURRENT list" in page.inner_text("body")
    page.close()


def test_every_theme_paints_the_encoding_with_tokens_and_no_errors(
    browser: Any, served: str, sheets: tuple[Path, Path]
) -> None:
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    _load_both(page, served, sheets)
    seen: dict[str, tuple[str, str, str]] = {}
    for theme in THEMES:
        page.evaluate("(t) => document.documentElement.setAttribute('data-theme', t)", theme)
        got = page.evaluate(
            """() => {
              const cs = e => getComputedStyle(e);
              const lanes = [...document.querySelectorAll('.op-lane-edge')].map(r => cs(r).fill);
              return {
                lanes,
                slip: cs(document.querySelector('.opc-arrow-slip')).stroke,
                pull: cs(document.querySelector('.opc-arrow-pull')).stroke,
                ghostFill: cs(document.querySelector('.opc-ghost')).fill,
                ghostDash: cs(document.querySelector('.opc-ghost')).strokeDasharray,
                badge: cs(document.querySelector('.opc-badge-new')).fill,
                tableScrolls: cs(document.querySelector('.opc-scroll')).overflowX === 'auto',
                wider: [...document.querySelectorAll('body *')].some(
                  e => e.getBoundingClientRect().right > window.innerWidth + 1),
              };
            }"""
        )
        assert len(set(got["lanes"])) == 7, (theme, got["lanes"])
        assert got["slip"] != got["pull"], (theme, "a slip and a pull-in must not share a colour")
        assert got["ghostFill"] == "none" and got["ghostDash"] not in ("", "none"), theme
        assert got["badge"] not in ("", "none", "rgba(0, 0, 0, 0)"), theme
        assert not got["wider"], theme
        assert got["tableScrolls"], (theme, "the summary table must scroll in its own wrapper")
        seen[theme] = (got["slip"], got["pull"], got["badge"])
    assert seen["daylight"] != seen["console"], "a light theme resolves different tokens"
    assert errors == []
    page.close()


def test_the_powerpoint_button_downloads_the_compare_slide(
    browser: Any, served: str, sheets: tuple[Path, Path]
) -> None:
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    _load_both(page, served, sheets)
    page.wait_for_selector("#opcPptx")
    with page.expect_download() as dl:
        page.click("#opcPptx")
    download = dl.value
    assert download.suggested_filename.endswith(".pptx")
    data = Path(download.path()).read_bytes()
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        slide = zf.read("ppt/slides/slide1.xml").decode()
    assert 'name="Slip: Boots 1"' in slide and 'name="Prior activity: ' in slide
    page.close()
