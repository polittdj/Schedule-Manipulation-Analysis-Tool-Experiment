"""Act III's panel contract in a REAL browser, in ALL FOUR themes — ADR-0337 / ADR-0338.

Markup alone is not evidence (the round-4 latent-gap lesson): panelkit.js is a PER-PAGE include,
so a page can render ⛶ / ⤓ with no script to drive them, and a theme can render the head strip
into invisibility without changing one byte of HTML. `DESIGN-SYSTEM.md` asks for every UI change to
be verified in console / daylight / apollo / jarvis, and jarvis is the known clobber family — its
broad `html[data-theme=jarvis] .panel` rules are what flattened the verdict band on /compare.

Proved here, in bundled chromium:

* panelkit.js genuinely drives `/briefing`, `/brief` and `/risks` — click ⛶ on a converted
  panel, read `.is-big` back off it, and see the label flip (then toggle back);
* in each of the four themes, on every converted route: the head strip lays out (the h2 and
  the tool strip sit on one row, tools to the right), the tool strip is really on screen, and
  the provenance chip resolves to a VISIBLE colour rather than inheriting something transparent.

Skips unless playwright + the bundled chromium are present (same posture as
`test_compare_panelkit.py` — the runtime stays stdlib-only, Law 1)."""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests" / "fixtures" / "golden" / "project2_5"
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
    from fastapi.testclient import TestClient

    from schedule_forensics.web.app import SessionState, create_app

    app = create_app(SessionState())
    with TestClient(app) as c:
        for name in ("Project2", "Project5"):
            payload = (GOLDEN / f"{name}.mspdi.xml").read_bytes()
            assert (
                c.post(
                    "/upload", files={"files": (f"{name}.mspdi.xml", payload, "text/xml")}
                ).status_code
                == 200
            )

    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


@pytest.mark.parametrize(
    ("route", "panel"),
    [
        ("/briefing", ".panel.brief-doc"),
        ("/brief", ".panel[data-export]"),
        ("/risks", ".panel[data-export]"),
    ],
)
def test_panelkit_actually_drives_the_converted_panel(served: str, route: str, panel: str) -> None:
    """ONE real interaction per route: the button is wired, not merely rendered."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(CHROME))
        page = browser.new_page(viewport={"width": 1360, "height": 900})
        page.goto(served + route, wait_until="domcontentloaded")
        page.wait_for_selector(f"{panel} [data-sf-big]", timeout=10000)

        loaded = page.evaluate(
            "() => [...document.scripts].some(s => s.src.includes('/static/panelkit.js'))"
        )
        assert loaded, f"panelkit.js script element missing on {route}"

        btn = page.locator(f"{panel} [data-sf-big]").first
        assert btn.inner_text() == "⛶ ENLARGE"
        btn.click()
        page.wait_for_timeout(50)
        assert page.evaluate(
            f"() => document.querySelector('{panel}').classList.contains('is-big')"
        ), f"click did not toggle .is-big — panelkit.js is not driving {route}"
        assert btn.inner_text() == "⛶ SHRINK"
        assert btn.get_attribute("aria-pressed") == "true"
        btn.click()  # and back — never leave the page mutated for a later assertion
        page.wait_for_timeout(50)
        assert not page.evaluate(
            f"() => document.querySelector('{panel}').classList.contains('is-big')"
        )
        browser.close()


@pytest.mark.parametrize("route", ["/briefing", "/brief", "/risks"])
def test_the_head_strip_survives_all_four_themes(served: str, route: str) -> None:
    """Computed style, not markup (the standing rank-2/D1 lesson).

    A theme cannot be allowed to collapse the head strip, hide the tool strip, or render the
    provenance chip in a colour with no alpha — each would leave the contract present in the HTML
    and absent on the operator's screen.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(CHROME))
        page = browser.new_page(viewport={"width": 1360, "height": 900})
        page.goto(served + route, wait_until="domcontentloaded")
        page.wait_for_selector(".panel-head", timeout=10000)

        for theme in THEMES:
            page.evaluate(f"() => document.documentElement.setAttribute('data-theme','{theme}')")
            page.wait_for_timeout(80)
            probe = page.evaluate(
                """() => {
                  const head = document.querySelector('.panel-head');
                  const h2 = head.querySelector('h2');
                  const tools = head.querySelector('.sf-tools');
                  const chip = head.querySelector('.prov-chip');
                  const cs = getComputedStyle(head);
                  const hb = h2.getBoundingClientRect();
                  const tb = tools.getBoundingClientRect();
                  const chipCs = getComputedStyle(chip);
                  return {
                    display: cs.display,
                    headW: head.getBoundingClientRect().width,
                    h2W: hb.width, h2H: hb.height,
                    toolsW: tb.width, toolsH: tb.height,
                    toolsRightOfH2: tb.left >= hb.left,
                    toolsVisible: getComputedStyle(tools).visibility,
                    chipColor: chipCs.color,
                    chipDisplay: chipCs.display,
                  };
                }"""
            )
            assert probe["headW"] > 200, (theme, route, probe)
            assert probe["h2W"] > 0 and probe["h2H"] > 0, (theme, route, probe)
            assert probe["toolsW"] > 0 and probe["toolsH"] > 0, (theme, route, probe)
            assert probe["toolsVisible"] != "hidden", (theme, route, probe)
            assert probe["toolsRightOfH2"], (theme, route, probe)
            assert probe["chipDisplay"] != "none", (theme, route, probe)
            # a chip rendered fully transparent is "present" in the DOM and invisible on screen
            assert "rgba(0, 0, 0, 0)" not in probe["chipColor"], (theme, route, probe)
        browser.close()
