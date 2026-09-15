"""The build chip, measured in Chromium in the four themes at two widths (OR-18, ADR-0494).

The server test pins the words; this one pins what the operator SEES: on ``/launch`` the version
line is a laid-out box directly under the compliance chrome with its CSS "BUILD" label; on ``/``
the header chip is visible inside the header beside the brand; and neither adds sideways scroll
(the document's scroll width with the chip shown equals its width with the chip hidden) at a
1,440 desktop and a 900-px narrow viewport.
"""

from __future__ import annotations

import socket
import threading
import time
from importlib.metadata import version
from typing import Any

import pytest

from web.browser_chrome import chrome_kwargs

pytest.importorskip("playwright", reason="playwright not installed (deliberate: see module docs)")

THEMES = ("console", "daylight", "apollo", "jarvis")
WIDTHS = (1440, 900)


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = int(s.getsockname()[1])
    s.close()
    return port


@pytest.fixture(scope="module")
def served() -> Any:
    import uvicorn

    from schedule_forensics.web.app import SessionState, create_app

    app = create_app(SessionState())
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


_BOX = """(sel) => {
  const el = document.querySelector(sel); if (!el) return null;
  const r = el.getBoundingClientRect();
  const cs = getComputedStyle(el, '::before');
  return {w: r.width, h: r.height, top: r.top, bottom: r.bottom, left: r.left, right: r.right,
          hidden: !!el.closest('[hidden]'), text: el.textContent, label: cs.content,
          color: getComputedStyle(el).color}; }"""
_SW = "() => document.scrollingElement.scrollWidth"
_HIDE = "(on) => { document.querySelector('[data-tool-version]').hidden = on; }"


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("width", WIDTHS)
def test_the_build_chip_is_visible_labelled_and_adds_no_sideways_scroll(
    served: str, theme: str, width: int
) -> None:
    from playwright.sync_api import sync_playwright

    expected = version("schedule-forensics")
    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        ctx = browser.new_context(viewport={"width": width, "height": 900})
        ctx.add_init_script(f"try{{localStorage.setItem('sf-theme','{theme}')}}catch(e){{}}")
        page = ctx.new_page()
        # the Boot Screen: the line sits under the compliance chrome, labelled, in the theme's ink
        page.goto(f"{served}/launch", wait_until="load")
        chip = page.evaluate(_BOX, ".boot-version")
        bar = page.evaluate(_BOX, ".cui-banner")
        assert chip and chip["w"] > 0 and chip["h"] > 0 and not chip["hidden"], (theme, width)
        assert chip["text"] == expected and "BUILD" in chip["label"], chip
        assert bar and chip["top"] >= bar["bottom"], (theme, width, chip["top"], bar["bottom"])
        shown = page.evaluate(_SW)
        page.evaluate(_HIDE, True)
        assert page.evaluate(_SW) == shown, ("launch sideways scroll", theme, width)
        # every chrome page: the header chip beside the brand, inside the header's box
        page.goto(f"{served}/", wait_until="load")
        assert page.evaluate("() => document.documentElement.getAttribute('data-theme')") == theme
        chip = page.evaluate(_BOX, ".brand-ver")
        head = page.evaluate(_BOX, "header")
        brand = page.evaluate(_BOX, "header h1.brand")
        assert chip and chip["w"] > 0 and chip["h"] > 0 and not chip["hidden"], (theme, width)
        assert chip["text"] == expected and "BUILD" in chip["label"], chip
        assert head["left"] <= chip["left"] and chip["right"] <= head["right"], (theme, width)
        assert head["top"] <= chip["top"] and chip["bottom"] <= head["bottom"], (theme, width)
        # beside or after the brand, never over it
        assert chip["left"] >= brand["left"], (theme, width)
        shown = page.evaluate(_SW)
        page.evaluate(_HIDE, True)
        assert page.evaluate(_SW) == shown, ("header sideways scroll", theme, width)
        browser.close()
