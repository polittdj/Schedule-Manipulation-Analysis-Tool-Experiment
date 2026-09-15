"""The Save receipt and the version chip, measured in Chromium in all four themes (OR-17,
ADR-0493).

The server test pins the words; this one pins what the operator SEES after clicking Save on the
real form: the receipt notice is visible (a laid-out box inside the panel, the theme's ``.notice``
tokens — never a display trick the CSS must undo), it names the gateway key as replaced with the
length held, the installed version chip is visible on the same page, a reload shows no receipt
(one-shot), and the key's characters are nowhere in the document. The gateway is the real class
over an opener that never opens a socket, as in the disclosure test — nothing leaves the machine.
"""

from __future__ import annotations

import socket
import tempfile
import threading
import time
import urllib.error
from importlib.metadata import version
from pathlib import Path
from typing import Any

import pytest

from schedule_forensics.ai.gateway import GatewayBackend
from web.browser_chrome import chrome_kwargs

LOG = Path(tempfile.mkdtemp()) / "tx.jsonl"

pytest.importorskip("playwright", reason="playwright not installed (deliberate: see module docs)")

ENDPOINT = "https://proxy.fast.luna.nasa.gov"
THEMES = ("console", "daylight", "apollo", "jarvis")
KEY = "k" * 25


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = int(s.getsockname()[1])
    s.close()
    return port


def _never(url: str, data: bytes | None, timeout: float, headers: Any) -> str:
    raise urllib.error.HTTPError(url, 401, "refused", None, None)  # type: ignore[arg-type]


class _Refused(GatewayBackend):
    def __init__(self, *a: Any, **k: Any) -> None:
        k["opener"] = _never
        k.setdefault("log_path", LOG)
        super().__init__(*a, **k)

    def unavailable_reason(self) -> str:
        return 'server returned HTTP 401 (its reason: "Not authenticated")'

    def list_models(self) -> tuple[str, ...]:
        return ()


@pytest.fixture(scope="module")
def served() -> Any:
    import uvicorn
    from fastapi.testclient import TestClient

    import schedule_forensics.web.app as app_module
    import schedule_forensics.web.settings as settings_module
    from schedule_forensics.web.app import SessionState, create_app

    mp = pytest.MonkeyPatch()
    mp.setattr(settings_module, "_gateway_or_none", lambda cfg: _Refused(ENDPOINT, model="m"))
    mp.setattr(app_module, "GatewayBackend", _Refused)
    app = create_app(SessionState())
    with TestClient(app) as c:
        r = c.post(
            "/settings",
            data={
                "classification": "CLASSIFIED",
                "backend": "gateway",
                "model": "claude-opus-4.8-thinking-itar",
                "gateway_endpoint": ENDPOINT,
                "gateway_approved": "1",
            },
            follow_redirects=False,
        )
        assert r.status_code == 303
        c.get("/settings")  # consume the arming save's receipt: each theme starts clean
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    mp.undo()


_BOX = """(sel) => {
  const el = document.querySelector(sel); if (!el) return null;
  const r = el.getBoundingClientRect();
  return {w: r.width, h: r.height, top: r.top, bottom: r.bottom, left: r.left, right: r.right,
          hidden: !!el.closest('[hidden]'), text: el.textContent}; }"""


@pytest.mark.parametrize("theme", THEMES)
def test_the_receipt_and_the_version_chip_are_visible_after_save_and_gone_on_reload(
    served: str, theme: str
) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        ctx.add_init_script(f"try{{localStorage.setItem('sf-theme','{theme}')}}catch(e){{}}")
        page = ctx.new_page()
        page.goto(f"{served}/settings", wait_until="load")
        page.wait_for_selector("#backendSel")
        assert page.evaluate("() => document.documentElement.getAttribute('data-theme')") == theme
        assert page.evaluate(_BOX, "[data-receipt]") is None  # nothing before a save
        # the operator's action on the real form: paste the key into the GATEWAY field, Save
        page.fill("input[name=gateway_api_key]", KEY)
        with page.expect_navigation(wait_until="load"):
            page.click("form[action='/settings'] input[type=submit]")
        receipt = page.evaluate(_BOX, "[data-receipt]")
        assert receipt is not None and not receipt["hidden"], theme
        assert receipt["w"] > 0 and receipt["h"] > 0, (theme, receipt)
        assert "Gateway API key: replaced" in receipt["text"], receipt["text"]
        assert "25 characters now held" in receipt["text"]
        panel = page.evaluate(_BOX, ".panel")
        assert panel is not None
        assert panel["left"] <= receipt["left"] and receipt["right"] <= panel["right"], theme
        assert panel["top"] <= receipt["top"] and receipt["bottom"] <= panel["bottom"], theme
        # the tool's version sits on the same page, visible, and is the installed version
        chip = page.evaluate(_BOX, "[data-tool-version]")
        assert chip is not None and chip["w"] > 0 and chip["h"] > 0 and not chip["hidden"]
        assert chip["text"] == version("schedule-forensics")
        # the receipt carries the theme's notice tokens: a real border, not a bare div
        border = page.evaluate(
            "() => getComputedStyle(document.querySelector('[data-receipt]')).borderTopWidth"
        )
        assert border not in ("", "0px"), (theme, border)
        assert KEY not in page.content()
        # one-shot: a reload shows no receipt, and the placeholder now states the length
        page.reload(wait_until="load")
        assert page.evaluate(_BOX, "[data-receipt]") is None
        placeholder = page.get_attribute("input[name=gateway_api_key]", "placeholder") or ""
        assert "25 characters" in placeholder
        browser.close()
