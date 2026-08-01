"""The four-theme axis-caption pass, MEASURED in a real browser instead of eyeballed.

DESIGN-SYSTEM's Definition of Done asks for "captions legible in all four themes at 90-125%".
That was owed from ADR-0298 (2026-07-27b) through ADR-0302 and never done, because eyeballing
four themes x three scales x every chart page is ~100 screenshots nobody re-checks — the kind
of task that stays owed forever. Everything it actually asks is measurable, so this measures it:

* every caption RENDERS with a non-zero box and the ``.ch-at`` hook;
* ``font-size`` resolves to the ``--sf-fs-axis-title`` token's 11px;
* ``text-transform`` really is uppercase — the one property ADR-0298 called out as worth
  eyeballing, because CSS case-transforming an SVG ``<text>`` is not universally supported;
* the caption box sits INSIDE its chart's ``<svg>`` (not clipped at the edge);
* captions never overlap one another;
* caption-vs-background contrast clears a legibility floor in every theme.

**Geometry is measured per THEME, and that is not redundant.** The first version of this pass
factored the matrix — colour once per theme, geometry once per scale — on the reasoning that
themes only redefine colours. That is false: ``sf-themes.css`` gives apollo
``font-family:'IBM Plex Mono'``, so caption widths genuinely differ between themes, and apollo's
wider glyphs are exactly the case most likely to clip. The factoring assertion is kept below as
a recorded fact rather than deleted, because "themes only change colour" is the assumption a
future reader is most likely to re-make.

**Skips unless playwright + the bundled chromium are present.** Playwright is deliberately NOT a
project dependency: the tool is air-gapped and stdlib-only at runtime (Law 1), and CI has no
browser. To run this deliberately::

    pip install playwright
    python -m pytest tests/web/test_axis_titles_visual.py -q -s
"""

from __future__ import annotations

import contextlib
import socket
import threading
import time
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests" / "fixtures" / "golden" / "project2_5"
#: The image ships chromium 1194; a pip-installed playwright driver expects a newer build and a
#: bare ``launch()`` dies with "Executable doesn't exist". An explicit path is the whole fix.
CHROME = Path("/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

THEMES = ("console", "daylight", "apollo", "jarvis")
SCALES = ("0.9", "1", "1.25")
#: Pages the golden Project2/Project5 pair actually charts — plus ``/margin``, which that pair
#: CANNOT chart (its months need activities named "margin" and status-dated versions; the golden
#: pair correctly renders a "no data" note and NO chart, so measuring it there would prove
#: nothing). ``/margin`` joined in ADR-0325 (batch 3b-i) and is served from its OWN app instance
#: loaded with synthetic status-dated margin versions (``served_margin``) so both its charts
#: really render; ``_base_for`` routes it there.
#:
#: ``/resources`` joined in ADR-0319, which closed the debt this comment used to carry: after
#: round 10's ``defer`` made the histogram paint on load, applying the rules below measured a
#: REAL collision in 8 of 12 theme x scale combos — the X caption "Period (month commencing)"
#: parked over the last 40°-rotated month tick labels (console@1 by ~36x2px each; apollo@1 by
#: ~40x4px; everything else — font-size, uppercase, inside-svg, contrast — passed). The remedy
#: is ADR-0303's, applied where the collision is caused: ``resources.js`` measures the caption's
#: LIVE box after the append and REMOVES any rotated period label biting into it (2px margin),
#: so the caption never moves and apollo's wider mono glyphs are covered per-theme. This pass
#: is what proves that yield holds in all 12 combos.
#: ``/forecast`` joined in ADR-0303 batch 3a: drift.js's captions were attempted, reverted on
#: two measured collisions, and re-landed with the ADR-0303 clamps — this pass is what proves
#: those collisions stay closed.
#: ``/sra`` + ``/volatility`` joined in ADR-0329 (batch 3c-i). ``/sra`` self-runs its simulation
#: on page load (fetch /api/sra — 200 in ~1.4s on the golden pair with auto screening defaults,
#: well inside the 5s caption wait below), so its CDF + histogram captions render for real;
#: ``/volatility`` charts from its embedded blob immediately (the golden pair is 2 versions —
#: enough for every version-indexed chart). The tornado/gauge/leaderboard family renders no
#: caption and is deliberately not measured (recorded not-axis-charts, decision A1).
PAGES = (
    "/curves",
    "/scurve",
    "/cei",
    "/trend",
    "/forecast",
    "/resources",
    "/margin",
    "/sra",
    "/volatility",
)

#: Caption collisions accepted as debt. EMPTY, and it should stay that way — the entry below is
#: kept as a record of why, because the wrong diagnosis here cost a full round trip.
#:
#: Widening the overlap detector (from caption-vs-caption to caption-vs-EVERY-text) found two real
#: ones: ``/cei`` 14x6px and ``/trend`` 6x10px. They were first written down as "the Y caption sits
#: where the top gridline's label already is", which made the fix look like a placement-convention
#: change. Measured in the browser, that premise was false on both counts: on ``/cei`` the top
#: gridline label ``15`` clears the caption by 13px and the collision is with a first-month BAR
#: VALUE label; on ``/trend`` the colliding caption is the **X** caption, which no Y-placement rule
#: touches at all. Both are one thing — a data label parked in a caption's band — and ADR-0303
#: fixes them where they are caused, in ``cei.js`` and ``trend_drill.js``, by moving the LABEL.
KNOWN_COLLISIONS: set[tuple[str, str]] = set()

CONTRAST_FLOOR = 3.0
TOKEN_PX = 11.0

_PROBE = """() => {
  const out = [];
  document.querySelectorAll('text.ch-at').forEach(n => {
    const r = n.getBoundingClientRect(), cs = getComputedStyle(n);
    const svg = n.ownerSVGElement, sr = svg ? svg.getBoundingClientRect() : null;
    let bg = 'rgb(0,0,0)', el = svg || n;
    while (el) { const c = getComputedStyle(el).backgroundColor;
      if (c && !c.startsWith('rgba(0, 0, 0, 0)')) { bg = c; break; } el = el.parentElement; }
    out.push({text: n.textContent, x: Math.round(r.x), y: Math.round(r.y),
              w: Math.round(r.width), h: Math.round(r.height), fs: cs.fontSize,
              tt: cs.textTransform, fill: cs.fill || cs.color, bg,
              svg: sr ? {x: Math.round(sr.x), y: Math.round(sr.y),
                         w: Math.round(sr.width), h: Math.round(sr.height)} : null,
              siblings: svg ? [...svg.querySelectorAll('text')]
                .filter(o => o !== n && o.textContent.trim())
                .map(o => { const b = o.getBoundingClientRect();
                            return {text: o.textContent, x: Math.round(b.x), y: Math.round(b.y),
                                    w: Math.round(b.width), h: Math.round(b.height)}; }) : []});
  });
  return out;
}"""


def _luminance(rgb: tuple[float, float, float]) -> float:
    def chan(c: float) -> float:
        c /= 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (chan(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(fg: tuple[float, float, float], bg: tuple[float, float, float]) -> float:
    a, b = _luminance(fg), _luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def _rgb(s: str) -> tuple[float, float, float]:
    n = [float(x) for x in s.replace("rgba(", "").replace("rgb(", "").rstrip(")").split(",")[:3]]
    return (n[0], n[1], n[2])


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = int(s.getsockname()[1])
    s.close()
    return port


pytest.importorskip("playwright", reason="playwright not installed (deliberate: see module docs)")
pytestmark = pytest.mark.skipif(not CHROME.exists(), reason=f"bundled chromium not at {CHROME}")


def _serve(app: Any) -> Any:
    """Boot ``app`` on a free loopback port and yield the base URL (the browser needs
    same-origin /static, so a TestClient is not enough)."""
    import uvicorn

    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    return server, f"http://127.0.0.1:{port}"


@pytest.fixture(scope="module")
def served() -> Any:
    """A real HTTP server with the two golden versions loaded."""
    from fastapi.testclient import TestClient

    from schedule_forensics.web.app import SessionState, create_app

    app = create_app(SessionState())
    with TestClient(app) as c:
        for name in ("Project2", "Project5"):
            payload = (GOLDEN / f"{name}.mspdi.xml").read_bytes()
            r = c.post("/upload", files={"files": (f"{name}.mspdi.xml", payload, "text/xml")})
            assert r.status_code == 200, (name, r.status_code)

    server, base = _serve(app)
    yield base
    server.should_exit = True


@pytest.fixture(scope="module")
def served_margin() -> Any:
    """A second server whose versions ``/margin`` can actually chart: four status-dated
    versions with a margin activity eroding 40 → 10 wd (the same synthetic shape
    ``test_margin_dashboard_view.py`` pins), so the burn-down AND the erosion trend (2+
    dated points, a projected zero-margin date) both render their captions for real."""
    import datetime as dt

    from schedule_forensics.model.relationship import Relationship, RelationshipType
    from schedule_forensics.model.schedule import Schedule
    from schedule_forensics.model.task import Task
    from schedule_forensics.web.app import SessionState, create_app

    def version(status: str, margin_days: float) -> Schedule:
        day = 480
        return Schedule(
            name=status,
            source_file=f"{status}.mpp",
            project_start=dt.datetime(2026, 1, 5, 8, 0),
            status_date=dt.datetime.fromisoformat(status),
            tasks=(
                Task(unique_id=1, name="Work", duration_minutes=500 * day),
                Task(
                    unique_id=2,
                    name="Schedule MARGIN: pre-delivery",
                    duration_minutes=int(margin_days * day),
                ),
                Task(unique_id=3, name="Deliver SV1", duration_minutes=0, is_milestone=True),
            ),
            relationships=(
                Relationship(
                    predecessor_id=1, successor_id=2, type=RelationshipType.FS, lag_minutes=0
                ),
                Relationship(
                    predecessor_id=2, successor_id=3, type=RelationshipType.FS, lag_minutes=0
                ),
            ),
        )

    st = SessionState()
    for status, margin_days in (
        ("2026-02-27", 40),
        ("2026-03-31", 30),
        ("2026-04-30", 20),
        ("2026-05-29", 10),
    ):
        v = version(status, margin_days)
        st.schedules[v.source_file] = v
    st.target_uid = 3

    server, base = _serve(create_app(st))
    yield base
    server.should_exit = True


def test_captions_survive_every_theme_and_scale(served: str, served_margin: str) -> None:
    """The whole Definition-of-Done line, as one executable assertion."""
    from playwright.sync_api import sync_playwright

    problems: list[str] = []
    known_hit: set[tuple[str, str]] = set()
    measured = 0
    geometry: dict[str, list[tuple[Any, ...]]] = {}

    def _base_for(route: str) -> str:
        return served_margin if route == "/margin" else served

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(CHROME))
        page = browser.new_page(viewport={"width": 1600, "height": 1100})
        page.goto(served + "/", wait_until="domcontentloaded")

        def load(route: str, theme: str, scale: str) -> list[dict[str, Any]]:
            base = _base_for(route)
            # localStorage is per-ORIGIN and /margin runs on its own port: land on the target
            # origin first, so the theme/scale written below binds to the page being measured.
            if not page.url.startswith(base):
                page.goto(base + route, wait_until="domcontentloaded")
            page.evaluate(
                "([t,s])=>{localStorage.setItem('sf-theme',t);localStorage.setItem('sf-scale',s)}",
                [theme, scale],
            )
            # NEVER wait for networkidle: heartbeat.js polls every 3s and sysmon.js every 2s, so
            # the network never goes idle and every load would burn its full timeout.
            page.goto(base + route, wait_until="domcontentloaded")
            with contextlib.suppress(Exception):  # a page may legitimately chart nothing
                page.wait_for_selector("text.ch-at", timeout=5000, state="attached")
            page.wait_for_timeout(150)
            return list(page.evaluate(_PROBE))

        for theme in THEMES:
            for scale in SCALES:
                for route in PAGES:
                    caps = load(route, theme, scale)
                    where = f"{theme}@{scale} {route}"
                    if not caps:
                        problems.append(f"{where}: no captions rendered")
                        continue
                    if scale == "1":
                        geometry.setdefault(route, []).append(
                            tuple((c["text"], c["x"], c["y"], c["w"]) for c in caps)
                        )
                    for c in caps:
                        measured += 1
                        label = f"{where} “{c['text'][:34]}”"
                        if c["w"] <= 0 or c["h"] <= 0:
                            problems.append(f"{label}: zero-size box")
                        if c["tt"] != "uppercase":
                            problems.append(f"{label}: text-transform={c['tt']}")
                        got = float(c["fs"].removesuffix("px"))
                        if abs(got - TOKEN_PX) > 0.2:
                            problems.append(f"{label}: font-size {got}px, want {TOKEN_PX}px")
                        box = c["svg"]
                        if box:
                            if c["x"] < box["x"] - 1 or c["x"] + c["w"] > box["x"] + box["w"] + 1:
                                problems.append(f"{label}: clipped horizontally")
                            if c["y"] < box["y"] - 1 or c["y"] + c["h"] > box["y"] + box["h"] + 1:
                                problems.append(f"{label}: clipped vertically")
                        ratio = _contrast(_rgb(c["fill"]), _rgb(c["bg"]))
                        if ratio < CONTRAST_FLOOR:
                            problems.append(f"{label}: contrast {ratio:.2f}:1 < {CONTRAST_FLOOR}")
                        # against EVERY other text in the same svg — a caption colliding with a
                        # tick label or a row name is the likeliest real collision, and comparing
                        # captions only to captions cannot see it.
                        for other in c.get("siblings", []):
                            # Overlap must be REAL, not a rounding artefact: every coordinate is
                            # rounded to whole pixels above, which can manufacture a ~1px touch.
                            # Require a 2px bite on BOTH axes before calling it a collision.
                            dx = min(c["x"] + c["w"], other["x"] + other["w"]) - max(
                                c["x"], other["x"]
                            )
                            dy = min(c["y"] + c["h"], other["y"] + other["h"]) - max(
                                c["y"], other["y"]
                            )
                            if dx >= 2 and dy >= 2:
                                key = (route, c["text"])
                                if key in KNOWN_COLLISIONS:
                                    known_hit.add(key)
                                    continue
                                problems.append(
                                    f"{label}: overlaps “{other['text'][:30]}” by {dx}x{dy}px"
                                )
        browser.close()

    assert measured >= 100, f"only {measured} caption renders measured — the pass proved little"
    # The debt list may only shrink. An entry that no longer collides has been FIXED, and leaving
    # it listed would hide the next regression at that exact spot.
    stale = KNOWN_COLLISIONS - known_hit
    assert not stale, (
        f"these no longer collide — delete them from KNOWN_COLLISIONS: {sorted(stale)}"
    )
    assert not problems, f"{len(problems)} caption problem(s):\n  " + "\n  ".join(problems[:30])

    # Recorded, not asserted-away: geometry DOES vary by theme (apollo is IBM Plex Mono), which
    # is why every theme is measured above rather than one standing in for the rest.
    varied = [r for r, runs in geometry.items() if len(set(runs)) > 1]
    print(f"\n  measured {measured} caption renders, {len(THEMES)} themes x {len(SCALES)} scales")
    print(f"  pages whose caption geometry differs by theme (expected — apollo is mono): {varied}")
