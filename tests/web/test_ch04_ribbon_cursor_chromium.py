"""ADR-0428 — the transition ribbon must not borrow a transition the cursor is not on.

``drawRibbon`` resolved its version pair with ``Math.max(1, cursor)``, so cursor 0 (the FIRST
loaded version) and cursor 1 (the second) both rendered ``PAIRS[0]``. Two consequences, both
found by walking the control in a browser rather than by reading the dataset:

1. **The opening click of Next changed nothing** — the ribbon was already showing the pair that
   the second position maps to, so the button read as dead.
2. **The baseline stated a transition that had not happened.** At cursor 1 the panel said
   "33 stayed / 1 left" over the label ``v1 → v2``, while the cursor was on v1 alone. The first
   loaded version has no predecessor; there is no transition INTO it. That is the same rule the
   rest of this page follows — a figure must belong to the population it is shown against
   (ADR-0420) — applied to a cursor position instead of a panel.

Everything else on the page was already correct: ``tests/web/test_ch04_stability_oracle.py``
proves the arithmetic against hand-computed answers. This is a presentation defect only, and it
predates the chapter band — ``/volatility`` mounts the same module and behaved identically, which
is why BOTH pages are asserted here.
"""

from __future__ import annotations

import gzip
import re
import socket
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from web.browser_chrome import chrome_kwargs

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests" / "fixtures" / "golden" / "fuse_hardfile"
VERSIONS = ("Hard_File", "Hard_File_updated", "Hard_File_updated2", "Hard_File_updated3")

# Chromium resolution is `tests/web/browser_chrome.py`'s single decision (ADR-0406, widened by
# ADR-0418): prefer a vendored binary, else let playwright resolve its own — the branch a CI
# runner takes. This module was FIRST WRITTEN pinning the vendored browser directory in a skipif,
# copied from a pattern ADR-0418 had already retired; `tests/guards/test_browser_resolver.py`
# caught it.
# That mattered: the guard against the ribbon defect would have SKIPPED on CI and never run where
# it counts.
pytest.importorskip("playwright", reason="playwright not installed (runtime stays stdlib-only)")

#: Reads the ribbon's own heading (the "from → to" line) plus the cursor's position label.
CURSOR_JS = """() => {
  const r = document.getElementById('volRibbon');
  const texts = [...r.querySelectorAll('svg text')].map(e => e.textContent.trim());
  const lab = document.getElementById('volLabel');
  return {
    cursor: lab ? lab.textContent.split('—')[0].trim() : '',
    heading: texts.length ? texts[texts.length - 1] : '',
    all: texts,
  };
}"""


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
    for _ in range(200):
        if server.started:
            break
        time.sleep(0.1)

    import urllib.request

    for name in VERSIONS:
        xml = gzip.decompress((GOLDEN / f"{name}.mspdi.xml.gz").read_bytes())
        boundary = "----sfboundary"
        body = (
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="files"; filename="{name}.mspdi.xml"\r\n'
                f"Content-Type: text/xml\r\n\r\n"
            ).encode()
            + xml
            + f"\r\n--{boundary}--\r\n".encode()
        )
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/upload",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        urllib.request.urlopen(req).read()

    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


@pytest.fixture
def browser() -> Any:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch(**chrome_kwargs())
        yield b
        b.close()


def _walk(page: Any) -> list[dict[str, Any]]:
    """Step the cursor to position 1, then capture every position in order."""
    for _ in range(6):
        if page.evaluate(CURSOR_JS)["cursor"].startswith("1 /"):
            break
        page.click("#volNext")
        page.wait_for_timeout(400)
    out = []
    for _ in range(4):
        out.append(page.evaluate(CURSOR_JS))
        page.click("#volNext")
        page.wait_for_timeout(500)
    return out


@pytest.mark.parametrize("route", ["/evolution", "/volatility"])
def test_each_cursor_position_shows_its_own_transition(
    served: str, browser: Any, route: str
) -> None:
    """The defect, stated as the thing that must not happen: two adjacent cursor positions
    rendering the SAME pair. Both pages mount the same module, so both are asserted."""
    page = browser.new_page(viewport={"width": 1500, "height": 1000})
    page.goto(f"{served}{route}", wait_until="networkidle")
    page.wait_for_timeout(1500)
    seen = _walk(page)

    headings = [s["heading"] for s in seen]
    assert len(seen) == 4, seen
    # positions 2..4 each name a DISTINCT transition
    assert len(set(headings[1:])) == 3, f"{route}: adjacent cursors repeat a pair: {headings}"
    # and the baseline is not one of them
    assert headings[0] not in headings[1:], (
        f"{route}: the baseline borrowed a later transition: {headings}"
    )
    page.close()


@pytest.mark.parametrize("route", ["/evolution", "/volatility"])
def test_the_baseline_version_states_that_it_has_no_predecessor(
    served: str, browser: Any, route: str
) -> None:
    """Cursor 1 is the first loaded file. There is no transition into it, so the panel must say
    so rather than print stayed/left figures for a change that did not occur."""
    page = browser.new_page(viewport={"width": 1500, "height": 1000})
    page.goto(f"{served}{route}", wait_until="networkidle")
    page.wait_for_timeout(1500)
    seen = _walk(page)
    baseline = seen[0]

    joined = " ".join(baseline["all"]).lower()
    assert "no preceding" in joined or "baseline" in joined, (
        f"{route}: the baseline does not say it has no predecessor: {baseline['all']}"
    )
    # The claim is that no FIGURE is stated, not that the words never occur — the baseline's own
    # copy legitimately says "what joined and left the path" as an instruction. Asserting on the
    # bare words made this test fail on its own explanatory sentence, which is a test defect, not
    # a product one. What must be absent is a count attached to one of those words.
    figures = re.findall(r"(?:stayed|joined|left)\s+\d+", joined)
    assert not figures, (
        f"{route}: the baseline printed {figures} for a transition that never happened: "
        f"{baseline['all']}"
    )
    page.close()


@pytest.mark.parametrize("route", ["/evolution", "/volatility"])
def test_stepping_forward_from_the_baseline_visibly_changes_the_panel(
    served: str, browser: Any, route: str
) -> None:
    """The operator-visible symptom: the first click of Next must DO something."""
    page = browser.new_page(viewport={"width": 1500, "height": 1000})
    page.goto(f"{served}{route}", wait_until="networkidle")
    page.wait_for_timeout(1500)
    for _ in range(6):
        if page.evaluate(CURSOR_JS)["cursor"].startswith("1 /"):
            break
        page.click("#volNext")
        page.wait_for_timeout(400)

    before = page.evaluate(CURSOR_JS)["all"]
    page.click("#volNext")
    page.wait_for_timeout(600)
    after = page.evaluate(CURSOR_JS)["all"]
    assert before != after, f"{route}: the first Next click changed nothing: {before}"
    page.close()
