"""The One-Pager in a real browser: the drop zone, the painted slide, the four themes, the
download (ADR-0446). The same twin workbook the unit tests use is dropped through the page."""

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
def twin_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    p = tmp_path_factory.mktemp("onepager") / "Politte_PowerPoint_FINAL.xlsx"
    p.write_bytes(twin_xlsx(TWIN_ROWS))
    return p


_PAINTED = """() => ({
  svg: !!document.querySelector('svg.op-svg'),
  bars: document.querySelectorAll('.op-bar').length,
  diamonds: document.querySelectorAll('.op-diamond').length,
  labels: document.querySelectorAll('.op-label').length,
  dd: document.querySelectorAll('.ch-dd line').length,
  captions: document.querySelectorAll('.ch-at').length,
  months: document.querySelectorAll('.op-month-line').length,
  legend: document.querySelectorAll('.op-legend-item').length,
  lanes: document.querySelectorAll('.op-lane-name-bg').length,
})"""


def test_the_picker_uploads_and_the_slide_is_painted(
    browser: Any, served: str, twin_path: Path
) -> None:
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(served + "/onepager")
    assert page.locator("#opDrop").is_visible() and not page.locator("svg.op-svg").count()
    with page.expect_navigation():
        page.set_input_files("#opFile", str(twin_path))  # the change handler submits the form
    page.wait_for_selector("svg.op-svg")
    got = page.evaluate(_PAINTED)
    assert got == {
        "svg": True,
        "bars": 10,
        "diamonds": 6,
        "labels": 16,
        "dd": 1,
        "captions": 2,
        "months": 35,
        "legend": 3 + 7,
        "lanes": 7,
    }, got
    # the DD marker is the red today line, spanning header + lanes, at the layout's x
    x = page.evaluate("() => Number(document.querySelector('.ch-dd line').getAttribute('x1'))")
    lay_x = page.evaluate("() => JSON.parse(document.getElementById('opData').textContent).today_x")
    assert x == pytest.approx(lay_x)
    # ▦ DATA reveals the parsed rows and flips its label
    assert page.locator(".sf-drawer").is_hidden()
    page.click("[data-sf-data]")
    assert (
        page.locator(".sf-drawer").is_visible() and page.locator(".op-table tbody tr").count() == 16
    )
    assert page.locator("[data-sf-data]").inner_text().strip() == "▦ HIDE DATA"
    assert errors == []
    page.close()


def test_drag_and_drop_anywhere_on_the_page_loads_the_list(browser: Any, served: str) -> None:
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.goto(served + "/onepager")
    page.click("form.op-clear-form button") if page.locator("form.op-clear-form").count() else None
    page.wait_for_selector("#opDrop")
    b64 = base64.b64encode(twin_xlsx(TWIN_ROWS)).decode()
    with page.expect_navigation():
        page.evaluate(
            """(b64) => {
              const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
              const file = new File([bytes], 'dropped list.xlsx',
                                    {type: 'application/octet-stream'});
              const dt = new DataTransfer(); dt.items.add(file);
              window.dispatchEvent(new DragEvent('drop',
                {dataTransfer: dt, bubbles: true, cancelable: true}));
            }""",
            b64,
        )
    page.wait_for_selector("svg.op-svg")
    assert "Loaded 16 item(s) from dropped list.xlsx" in page.inner_text("body")
    assert "dropped list" in page.evaluate(
        "() => JSON.parse(document.getElementById('opData').textContent).title"
    )
    page.close()


def test_every_theme_resolves_the_lane_tokens_to_distinct_colours(
    browser: Any, served: str, twin_path: Path
) -> None:
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.goto(served + "/onepager")
    if not page.locator("svg.op-svg").count():
        with page.expect_navigation():
            page.set_input_files("#opFile", str(twin_path))
    page.wait_for_selector("svg.op-svg")
    seen: dict[str, list[str]] = {}
    for theme in THEMES:
        page.evaluate("(t) => document.documentElement.setAttribute('data-theme', t)", theme)
        fills = page.evaluate(
            """() => Array.from(document.querySelectorAll('.op-lane-edge'))
                      .map(r => getComputedStyle(r).fill)"""
        )
        assert len(fills) == 7 and all(f not in ("", "none", "rgba(0, 0, 0, 0)") for f in fills), (
            theme,
            fills,
        )
        assert len(set(fills)) == 7, (theme, "every swimlane must get its own hue", fills)
        bg = page.evaluate("() => getComputedStyle(document.querySelector('.op-bg')).fill")
        assert bg not in ("", "none"), theme
        seen[theme] = fills
    assert seen["daylight"] != seen["console"], "a dark theme brightens the palette"
    page.close()


def test_the_powerpoint_button_downloads_the_slide(
    browser: Any, served: str, twin_path: Path
) -> None:
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    page.goto(served + "/onepager")
    if not page.locator("svg.op-svg").count():
        with page.expect_navigation():
            page.set_input_files("#opFile", str(twin_path))
    page.wait_for_selector("#opPptx")
    with page.expect_download() as dl:
        page.click("#opPptx")
    download = dl.value
    assert download.suggested_filename.endswith(".pptx")
    data = Path(download.path()).read_bytes()
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        assert "ppt/slides/slide1.xml" in zf.namelist()
    page.close()
