"""The DOM leg of the operator-content census: a task name must never become an ELEMENT.

``tests/web/test_operator_content_escaping.py`` proves the SERVER never emits operator content
as markup. That is only half the question, and the smaller half. Most of this UI's data arrives
as JSON and is rendered by the vendored JS, and a JSON payload carrying ``<img …>`` verbatim is
*correct* — the string only becomes dangerous when a renderer hands it to ``innerHTML``. Nothing
in the source tells you which happened; only the DOM does.

So this asks the browser directly, with an oracle that cannot be satisfied by an escaped page:
after loading each page, count elements matching ``img[src="x"]``, elements carrying an
``onerror`` attribute, and table cells whose text is exactly the row-break marker. A name
rendered as text produces none of them; a name passed through ``innerHTML`` produces all three.

The vendored JS builds its DOM with ``createElement`` + ``textContent``, which is structurally
immune — so this guard is expected to stay green. That is precisely why it exists: the immunity
is a property of how the renderers are written today, nothing enforces it, and JS-01 (ADR-0416)
showed a client-side contract can rot silently while every server test stays green.

Vacuity defences, in the same spirit as the server census:

* the page list is COMPUTED from the live app, never hand-written;
* a non-success navigation FAILS the test rather than scoring as clean — the throwaway version
  of this probe hand-listed 28 pages, two of which were 404s that it read as "escaped"; and
* ``test_the_dom_oracle_has_teeth`` feeds the oracle a deliberately-injected document and
  requires it to fire, so a green run means it looked and saw nothing.
"""

from __future__ import annotations

import json
import re
import socket
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

# Chromium resolution is `tests/web/browser_chrome.py`'s single decision (ADR-0406, widened by
# ADR-0418): prefer a vendored binary, else let playwright resolve its own — the branch a CI
# runner takes. A module that pins `/opt/pw-browsers` itself SKIPS on CI, which is how 23 modules
# were orphaned; `tests/guards/test_browser_resolver.py` fails the build for pinning it here.
from web.browser_chrome import chrome_kwargs

pytest.importorskip("playwright", reason="playwright not installed (runtime stays stdlib-only)")

EXAMPLE = (
    Path(__file__).resolve().parents[2] / "src/schedule_forensics/web/examples/house_build.json"
)

RAW_TAG = "<img src=x onerror=SFPROBE>"
ROW_BREAK = "</td></tr><tr><td>SFROWBREAK</td></tr><tr><td>"

#: Routes that are not pages: a health probe, the schema, and a GET that streams a download
#: (navigating to it aborts with "Download is starting", which is not a rendering verdict).
_NOT_PAGES = ("/healthz", "/openapi.json", "/sra/ssi/save")

#: The verdict, evaluated in the page. Three independent symptoms of the same defect, so a
#: renderer that strips one attribute but keeps the element is still caught.
_DOM_PROBE = """() => ({
  imgs: document.querySelectorAll('img[src="x"]').length,
  onerror_attrs: [...document.querySelectorAll('*')].filter(e => e.hasAttribute('onerror')).length,
  broken_cells: [...document.querySelectorAll('td,th')]
      .filter(e => e.textContent.trim() === 'SFROWBREAK').length,
})"""


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = int(sock.getsockname()[1])
    sock.close()
    return port


def _poisoned() -> bytes:
    doc = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    doc["name"] = f"Project {RAW_TAG}"
    for i, task in enumerate(doc["tasks"]):
        task["name"] = f"{task['name']} {ROW_BREAK if i % 2 else RAW_TAG}"
        if task.get("resource_names"):
            task["resource_names"] = [f"{r} {RAW_TAG}" for r in task["resource_names"]]
    return json.dumps(doc).encode()


@pytest.fixture
def served() -> Any:
    """The app on a real port with a POISONED schedule loaded, plus its computed page list."""
    state = SessionState()
    app = create_app(state)
    with TestClient(app) as client:
        resp = client.post(
            "/upload", files={"files": ("probe.json", _poisoned(), "application/json")}
        )
        assert resp.status_code == 200, resp.text
    key = next(iter(state.schedules))

    pages: list[str] = []
    for route in app.routes:
        path = str(getattr(route, "path", ""))
        methods = getattr(route, "methods", set()) or set()
        if "GET" not in methods or path in _NOT_PAGES:
            continue
        if path.startswith(("/api", "/export", "/static", "/download")):
            continue
        params = re.findall(r"\{(\w+)\}", path)
        if any(p != "name" for p in params):
            continue
        pages.append(path.replace("{name}", key))

    import uvicorn

    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(150):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}", sorted(set(pages))
    server.should_exit = True


def test_no_rendered_page_turns_operator_content_into_elements(served: Any) -> None:
    base, pages = served
    from playwright.sync_api import sync_playwright

    offenders: list[tuple[str, dict[str, int]]] = []
    unreachable: list[tuple[str, Any]] = []
    with sync_playwright() as play:
        browser = play.chromium.launch(**chrome_kwargs())
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        for path in pages:
            resp = page.goto(base + path, wait_until="load", timeout=30000)
            if resp is None or resp.status >= 400:
                unreachable.append((path, resp.status if resp else "no response"))
                continue
            page.wait_for_timeout(1500)  # let the client renderers fetch and paint
            verdict = page.evaluate(_DOM_PROBE)
            if any(verdict.values()):
                offenders.append((path, verdict))
        browser.close()

    # A page that did not load is NOT evidence of escaping — say so instead of scoring it.
    assert not unreachable, f"pages did not render, so nothing was proven about them: {unreachable}"
    assert not offenders, f"operator content became DOM elements on: {offenders}"
    assert len(pages) >= 25, f"only {len(pages)} pages enumerated — the page census is broken"


def test_the_dom_oracle_has_teeth(served: Any) -> None:
    """Hand the oracle a document that DID inject, and require every symptom to fire.

    A synthetic positive control is the right instrument here: the product's renderers are
    immune by construction, so there is no product mutation available that the browser could
    observe without rewriting a vendored file. What must be proven is that the probe itself can
    distinguish an injected DOM from an escaped one — and that is exactly what this measures.
    """
    base, _pages = served
    from playwright.sync_api import sync_playwright

    with sync_playwright() as play:
        browser = play.chromium.launch(**chrome_kwargs())
        page = browser.new_page()
        page.goto(base + "/", wait_until="load", timeout=30000)
        escaped = page.evaluate(_DOM_PROBE)

        page.set_content("<div id=sink></div><div id=grid></div>")
        # The injection is modelled at the level a real renderer works at. Assigning to a
        # <td>'s own innerHTML would NOT reproduce the row break: the HTML parser discards
        # stray </td></tr> in that context, so the marker stays inside the original cell and
        # the symptom never fires. The corruption is only reachable when a renderer builds a
        # whole table STRING and assigns it to a container — which is how it would really
        # happen, and what this control therefore does.
        page.evaluate(
            """() => {
                const name = 'Task <img src=x onerror=SFPROBE>';
                const rows = 'Other </td></tr><tr><td>SFROWBREAK';
                document.getElementById('sink').innerHTML = name;
                document.getElementById('grid').innerHTML =
                    '<table><tr><td>' + rows + '</td></tr></table>';
            }"""
        )
        injected = page.evaluate(_DOM_PROBE)
        browser.close()

    assert not any(escaped.values()), f"the escaped dashboard already trips the oracle: {escaped}"
    assert injected["imgs"] >= 1, "the oracle cannot see an injected element"
    assert injected["onerror_attrs"] >= 1, "the oracle cannot see an injected event attribute"
    assert injected["broken_cells"] >= 1, "the oracle cannot see a corrupted table row"
