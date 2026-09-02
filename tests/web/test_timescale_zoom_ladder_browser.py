"""The timescale must ADAPT ITS UNITS in both directions as the operator zooms (MS Project).

Operator 2026-09-02: "the timeline header should show like it does in MS Project and act
accordingly when the user zooms." ADR-0441 taught the header to PROMOTE units when zoomed far
out (a 12-year span fitted to one page shows Years/Quarters, never a picket fence). Nothing
demoted them when zoomed IN: at 30 px/day the configured Years/Quarters/Months stack painted
900-px-wide month bands — MS Project at that zoom shows Months/Weeks/Days. Measured on the
pre-fix tree (this file's FAIL-side tests were RED there): /analysis at ~30 px/day, bottom tier
= 143 month bands averaging ~915 px; /path at 32 px/day the same.

The oracle is the RENDERED band width of the finest tier (never the config, never inline
styles): a finest tier whose bands average more than ~4x a day's pixels has not demoted.
Coherence is pinned too — each tier must be strictly coarser than the one below it — and the
zoomed-OUT stack (ADR-0441's promotion) is re-pinned so the ladder cannot regress it.
"""

from __future__ import annotations

import json
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
FIXTURE = REPO / "tests" / "fixtures" / "test_projects" / "TP5_LongSpan_Synthetic.xml"
KEY = "TP5_LongSpan_Synthetic"


def _load(client: TestClient) -> None:
    files = [("files", (FIXTURE.name, FIXTURE.read_bytes(), "text/xml"))]
    meta = json.dumps([{"rel": FIXTURE.name, "mtime": 1_700_000_000_000}])
    assert client.post("/upload", files=files, data={"file_meta": meta}).status_code == 200


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
        _load(c)
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


# Every tier row of a scale, top → bottom: band count, labeled count, mean rendered width.
_TIERS = """(sel) => [...document.querySelectorAll(sel + ' .g-tier')].map(t => {
  const bs = [...t.querySelectorAll('.g-band')];
  const ws = bs.map(b => b.getBoundingClientRect().width);
  return {bands: bs.length, labeled: bs.filter(b => b.textContent.trim()).length,
          avg_w: ws.length ? ws.reduce((a, c) => a + c, 0) / ws.length : null,
          labels: bs.slice(0, 4).map(b => b.textContent)};
})"""


def _assert_coherent(tiers: list[dict[str, Any]]) -> None:
    """Each tier strictly coarser than the one below (fewer, wider bands); every tier labeled."""
    assert tiers, "no tier rows rendered"
    for i in range(len(tiers) - 1):
        assert tiers[i]["bands"] < tiers[i + 1]["bands"], (
            f"tier {i} not coarser than {i + 1}: {tiers}"
        )
    for t in tiers:
        assert t["labeled"] > 0, f"an unlabeled tier: {tiers}"


def _finest(tiers: list[dict[str, Any]]) -> dict[str, Any]:
    return tiers[-1]


def _open_analysis(browser: Any, served: str) -> Any:
    page = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
    page.goto(f"{served}/analysis/{KEY}", wait_until="load")
    page.wait_for_selector("#grid table.gantt-grid", timeout=30000)
    page.wait_for_timeout(600)
    return page


def _analysis_zoom_to(page: Any, px_per_day: float) -> None:
    # the page's own zoom model: #vizZoom carries px/day; the buttons step it and re-render
    page.evaluate(
        """(px) => { document.getElementById('vizZoom').value = String(px / 1.25); }""",
        px_per_day,
    )
    page.click("#zoomIn")  # stepZoom multiplies by 1.25 → exactly px_per_day, then renderGrid()
    page.wait_for_timeout(800)


# ── FAIL-side: zoomed IN, the stack must demote to Months / Weeks / Days ────────────────────


def test_analysis_zoomed_in_demotes_to_day_density(browser: Any, served: str) -> None:
    page = _open_analysis(browser, served)
    _analysis_zoom_to(page, 30)
    tiers = page.evaluate(_TIERS, "#grid .g-scale")
    fin = _finest(tiers)
    assert fin["avg_w"] is not None and fin["avg_w"] <= 30 * 1.5, (
        f"finest tier did not demote at 30 px/day — bands avg {fin['avg_w']:.0f}px: {tiers}"
    )
    _assert_coherent(tiers)
    assert len(tiers) == 3, f"MS Project shows three tiers at day density: {tiers}"
    page.context.close()


def test_path_zoomed_in_demotes_to_day_density(browser: Any, served: str) -> None:
    page = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
    page.goto(f"{served}/path", wait_until="load")
    page.wait_for_selector(".path-track", timeout=30000)
    page.evaluate(
        """() => { const z = document.getElementById('pathZoom'); z.value = '32';
                   z.dispatchEvent(new Event('input', {bubbles: true})); }"""
    )
    page.wait_for_timeout(900)
    tiers = page.evaluate(_TIERS, ".path-scale")
    fin = _finest(tiers)
    assert fin["avg_w"] is not None and fin["avg_w"] <= 32 * 1.5, (
        f"/path finest tier did not demote at 32 px/day — avg {fin['avg_w']:.0f}px: {tiers}"
    )
    _assert_coherent(tiers)
    page.context.close()


# ── PASS-side pins: the zoomed-OUT promotion (ADR-0441) is unchanged, and the ladder is
#    monotone — zooming in never yields COARSER units ─────────────────────────────────────────


def test_analysis_fitted_still_promotes_and_stays_coherent(browser: Any, served: str) -> None:
    page = _open_analysis(browser, served)
    page.click("#fitBtn")
    page.wait_for_timeout(800)
    tiers = page.evaluate(_TIERS, "#grid .g-scale")
    _assert_coherent(tiers)
    for t in tiers:
        assert t["avg_w"] >= 14, f"a sub-legible tier survived the fit: {tiers}"
    page.context.close()


def test_analysis_zoom_ladder_is_monotone(browser: Any, served: str) -> None:
    page = _open_analysis(browser, served)
    finest_counts = []
    for px in (2, 8, 30):
        _analysis_zoom_to(page, px)
        tiers = page.evaluate(_TIERS, "#grid .g-scale")
        _assert_coherent(tiers)
        finest_counts.append(_finest(tiers)["bands"])
    assert finest_counts[0] <= finest_counts[1] <= finest_counts[2], (
        f"zooming in coarsened the finest tier: {finest_counts}"
    )
    page.context.close()
