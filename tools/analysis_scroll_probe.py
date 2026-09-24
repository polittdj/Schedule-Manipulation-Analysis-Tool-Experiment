"""ADR-0458's /analysis scroll probe, committed (R-21, ADR-0530): frame times at operator scale.

ADR-0458 measured the /analysis scroll re-aim on "2,280 rows, two files of one project" with a
``requestAnimationFrame`` loop whose deltas were taken while the grid pane was wheel-scrolled
(40 x 300 px, 30 x 1,200 px, 30 x -600 px, 40 x 100 px) and while it was driven programmatically
(40 x 400 px every 40 ms — every step forces a re-aim), on a quiet box at 1600 x 1000. The probe
itself was never committed — its numbers (p95 83 ms after, "no sticky cells at all → 50") lived in
prose only, so R-21's settle criterion ("p95 ≤ 50 ms on the probe") had no instrument to run.
This is that instrument, reproducible: the same generator (``tests/web/scale_schedule.py``), the
same sequences, the same viewport. It is a measurement tool, not a test — nothing here asserts a
wall-clock (the box decides the number; ADR-0458 read p95 250 with three other chromiums alive).

Reading: "2,280 rows" is the PAGE's row count — the operator's IPMR is 2,301 activities — so each
of the two files carries 2,280 leaf tasks (the per-file split is not stated in ADR-0458; a
1,140 + 1,140 reading would halve the page and is not what the ADR's numbers describe).

    python tools/analysis_scroll_probe.py --runs 2 --links on,off [--query sfpane=1]

``--query`` appends a query string to the /analysis URL (the hook a flagged rendering path reads);
``--links`` toggles the page's own "links" checkbox before measuring; ``--strip-sticky`` is the
ADR's subtraction (un-stick every frozen cell first) — the floor, not a product mode. Output is
one row per sequence with p50 / p95 / max in ms, plus the box's load average so a busy-box
reading is labelled as one.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import statistics
import sys
import threading
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tests"))
sys.path.insert(0, str(REPO / "src"))

ROWS = 2280
VIEWPORT = {"width": 1600, "height": 1000}
WHEEL = (
    ("wheel 300 px", 300, 40),
    ("wheel 1,200 px", 1200, 30),
    ("wheel -600 px", -600, 30),
    ("wheel 100 px", 100, 40),
)
PROG_STEP, PROG_N, PROG_MS = 400, 40, 40

_RAF = """() => { window.__sfFrames = []; window.__sfLast = performance.now(); window.__sfOn = true;
  const tick = (t) => { if (!window.__sfOn) return; window.__sfFrames.push(t - window.__sfLast);
    window.__sfLast = t; requestAnimationFrame(tick); };
  requestAnimationFrame(tick); }"""
_STOP = """() => { window.__sfOn = false; const f = window.__sfFrames.slice(1);
  window.__sfFrames = []; return f; }"""
_STICKY = """() => document.querySelectorAll(
  '#grid td[style*=sticky], #grid th[style*=sticky]').length"""
_STRIP = """() => { document.querySelectorAll('#grid td[style*=sticky], #grid th[style*=sticky]')
  .forEach((c) => { c.style.position = ''; }); }"""
_PROG = """([step, n, ms]) => new Promise((res) => { const g = document.getElementById('grid');
  let i = 0; const id = setInterval(() => { g.scrollTop += step; if (++i >= n) { clearInterval(id);
  setTimeout(res, 120); } }, ms); })"""


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = int(s.getsockname()[1])
    s.close()
    return port


def _serve() -> tuple[str, str]:
    import uvicorn
    from fastapi.testclient import TestClient

    from schedule_forensics.web.app import SessionState, create_app
    from web.scale_schedule import generate_mspdi

    app = create_app(SessionState())
    with TestClient(app) as c:
        files = [
            ("files", ("scale_v1.xml", generate_mspdi(ROWS, seed=42).encode("utf-8"), "text/xml")),
            ("files", ("scale_v2.xml", generate_mspdi(ROWS, seed=43).encode("utf-8"), "text/xml")),
        ]
        meta = json.dumps(
            [
                {"rel": "scale_v1.xml", "mtime": 1_700_000_000_000},
                {"rel": "scale_v2.xml", "mtime": 1_700_000_100_000},
            ]
        )
        assert c.post("/upload", files=files, data={"file_meta": meta}).status_code == 200
        acts = c.get("/api/analysis/scale_v2").json()["activities"]
        assert len(acts) >= ROWS, len(acts)
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(150):
        if server.started:
            break
        time.sleep(0.1)
    return f"http://127.0.0.1:{port}", "scale_v2"


def _stats(frames: list[float]) -> tuple[float, float, float]:
    if not frames:
        return (0.0, 0.0, 0.0)
    q = statistics.quantiles(frames, n=20) if len(frames) >= 20 else sorted(frames)
    p95 = q[-1] if len(frames) >= 20 else frames[-1]
    return (statistics.median(frames), p95, max(frames))


def _measure(page: Any) -> list[tuple[str, tuple[float, float, float]]]:
    out: list[tuple[str, tuple[float, float, float]]] = []
    box = page.locator("#grid").bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    for label, dy, n in WHEEL:
        page.evaluate(_RAF)
        for _ in range(n):
            page.mouse.wheel(0, dy)
            page.wait_for_timeout(33)
        page.wait_for_timeout(120)
        out.append((label, _stats(page.evaluate(_STOP))))
    page.evaluate("() => { document.getElementById('grid').scrollTop = 0; }")
    page.wait_for_timeout(300)
    page.evaluate(_RAF)
    page.evaluate(_PROG, [PROG_STEP, PROG_N, PROG_MS])
    out.append((f"programmatic {PROG_STEP} px steps", _stats(page.evaluate(_STOP))))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--links", default="on", help="comma list of on/off")
    ap.add_argument("--query", default="", help="query string appended to the /analysis URL")
    ap.add_argument(
        "--strip-sticky",
        action="store_true",
        help="ADR-0458's subtraction: un-stick every frozen cell before measuring (the floor a "
        "frozen pane could reach on this box; the re-aim's freezeLike re-sticks entered rows)",
    )
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    from web.browser_chrome import chrome_kwargs

    base, key = _serve()
    print(f"box load average: {os.getloadavg()}  rows: {ROWS} x 2 files  viewport: {VIEWPORT}")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(**chrome_kwargs())
        for links in args.links.split(","):
            for run in range(1, args.runs + 1):
                page = browser.new_context(viewport=VIEWPORT).new_page()
                url = f"{base}/analysis/{key}" + (f"?{args.query}" if args.query else "")
                page.goto(url, wait_until="load")
                page.wait_for_selector("#grid table.gantt-grid", timeout=120000)
                page.wait_for_timeout(1500)
                cb = page.locator("#showLinks")
                if cb.count() and cb.is_checked() != (links == "on"):
                    cb.click()
                    page.wait_for_timeout(800)
                if args.strip_sticky:
                    page.evaluate(_STRIP)  # ADR-0458's subtraction: what the sticky cells cost
                sticky = page.evaluate(_STICKY)
                print(
                    f"\n== links {links} · run {run} · query {args.query!r}"
                    f" · strip {args.strip_sticky} · sticky cells {sticky}"
                )
                print(f"{'sequence':<28}{'p50':>8}{'p95':>8}{'max':>8}")
                for label, (p50, p95, mx) in _measure(page):
                    print(f"{label:<28}{p50:>8.0f}{p95:>8.0f}{mx:>8.0f}")
                page.context.close()
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
