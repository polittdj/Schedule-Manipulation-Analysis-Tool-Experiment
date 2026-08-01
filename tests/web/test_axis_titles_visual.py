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
#: ``/sra+run`` joined in ADR-0330 (batch 3c-ii): the SAME ``/sra`` route, but measured on its
#: OWN app instance (``served_sra``, the /margin precedent) with both Run buttons CLICKED. The
#: SSI and JCL panels render only on demand, and the golden pair cannot exercise them anyway —
#: its files carry no budgeted cost, so the JCL panel renders its honest "needs a cost-loaded
#: schedule" note and no #jclRun at all, and with no Best/Worst spread set the SSI S-curve
#: degenerates to a single point. ``served_sra`` loads a synthetic cost-loaded schedule with
#: real per-task spread so all four on-demand charts (SSI S-curve + histogram, JCL football +
#: cost S-curve) carry real data. The plain ``/sra`` cell above stays exactly what ADR-0329
#: measured (the golden pair's self-running CDF + histogram).
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
    "/sra+run",
)

#: On-demand panels per PAGES entry: (Run button, chart host) pairs. Each button is clicked on
#: every load and the host is then REQUIRED to grow a caption (a strict wait, never suppressed):
#: the page's self-running CDF/histogram captions would otherwise mask a dead clicked panel,
#: because "some captions rendered" cannot see which panel they came from.
CLICK_RUNS: dict[str, tuple[tuple[str, str], ...]] = {
    "/sra+run": (
        ("#ssiRun", "#ssiCharts"),
        ("#jclRun", "#jclCharts"),
    ),
}
#: The routes above are sentinels, not URLs — the real route each one loads.
REAL_ROUTE = {"/sra+run": "/sra"}
#: Per-route caption floors (same masking hazard): /sra+run must show ALL six charts' captions —
#: sra.js's self-run CDF + histogram (4) + the SSI pair (4) + the JCL pair (4) = 12.
MIN_CAPTIONS = {"/sra+run": 12}

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

#: ADR-0331 — the probe also reports the INK under each caption and the caption's halo.
#: The original probe measured contrast against the resolved CSS *background* and overlap only
#: against sibling ``<text>``, so ``<rect>``/``<polyline>`` ink was invisible to both checks — which
#: is exactly how a caption printing at 1.05-1.54:1 over a histogram bar shipped green (ADR-0330's
#: charts). ``ink`` counts non-text shapes whose real rendered box overlaps the caption's; ``po`` /
#: ``stroke`` / ``sw`` report the halo that makes such a caption legible. Deliberately a bbox
#: sweep, NOT ``getIntersectionList``: its support and semantics differ between engines, and a
#: bounding-box overlap is the property being asserted anyway.
_PROBE = """() => {
  const out = [];
  document.querySelectorAll('text.ch-at').forEach(n => {
    const r = n.getBoundingClientRect(), cs = getComputedStyle(n);
    const svg = n.ownerSVGElement, sr = svg ? svg.getBoundingClientRect() : null;
    let bg = 'rgb(0,0,0)', el = svg || n;
    while (el) { const c = getComputedStyle(el).backgroundColor;
      if (c && !c.startsWith('rgba(0, 0, 0, 0)')) { bg = c; break; } el = el.parentElement; }
    let ink = 0;
    if (svg) {
      svg.querySelectorAll('rect,polyline,path,circle,line').forEach(s => {
        const b = s.getBoundingClientRect();
        if (!b.width && !b.height) return;
        if (Math.min(r.right, b.right) - Math.max(r.left, b.left) > 0 &&
            Math.min(r.bottom, b.bottom) - Math.max(r.top, b.top) > 0) ink++;
      });
    }
    out.push({text: n.textContent, x: Math.round(r.x), y: Math.round(r.y),
              w: Math.round(r.width), h: Math.round(r.height), fs: cs.fontSize,
              tt: cs.textTransform, fill: cs.fill || cs.color, bg,
              ink, po: cs.paintOrder, stroke: cs.stroke, sw: cs.strokeWidth,
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


def _png_pixels(data: bytes) -> tuple[int, int, list[tuple[int, int, int]]]:
    """Decode a Playwright screenshot to RGB pixels using the STANDARD LIBRARY only.

    Pillow is not a project dependency (Law 1 keeps the runtime stdlib-only, and the dev extra
    has no imaging stack), so the honest pixel check decodes the PNG itself: zlib for the IDAT
    stream plus the five PNG filter types. Screenshots are 8-bit RGB/RGBA, non-interlaced.
    """
    import struct
    import zlib

    pos, w, h, ctype, idat = 8, 0, 0, 6, b""
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        kind = data[pos + 4 : pos + 8]
        body = data[pos + 8 : pos + 8 + length]
        if kind == b"IHDR":
            w, h, depth, ctype = (*struct.unpack(">IIBB", body[:10]),)[:4]
            assert depth == 8 and ctype in (2, 6), (depth, ctype)
        elif kind == b"IDAT":
            idat += body
        elif kind == b"IEND":
            break
        pos += 12 + length

    chan = 4 if ctype == 6 else 3
    raw = zlib.decompress(idat)
    stride = w * chan
    out: list[tuple[int, int, int]] = []
    prev = bytearray(stride)
    at = 0
    for _ in range(h):
        filt = raw[at]
        line = bytearray(raw[at + 1 : at + 1 + stride])
        at += 1 + stride
        for i in range(stride):
            a = line[i - chan] if i >= chan else 0
            b = prev[i]
            c = prev[i - chan] if i >= chan else 0
            if filt == 1:
                line[i] = (line[i] + a) & 0xFF
            elif filt == 2:
                line[i] = (line[i] + b) & 0xFF
            elif filt == 3:
                line[i] = (line[i] + ((a + b) >> 1)) & 0xFF
            elif filt == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 0xFF
        for i in range(0, stride, chan):
            out.append((line[i], line[i + 1], line[i + 2]))
        prev = line
    return w, h, out


def _modal_color(px: list[tuple[int, int, int]]) -> tuple[float, float, float]:
    """The most common colour in a clip — the caption's REAL local backdrop. Glyph strokes are
    sparse relative to the box they sit in, so the mode is what the eye reads the text against.

    Quantising groups anti-aliased near-duplicates together, but the bucket CENTRE is not the
    colour: a pure-white backdrop buckets to 252 and scores 2.99:1 against console's ``--muted``
    where the true value is 3.07:1 — enough to fail a 3.0 floor on a correct render. So the mode
    picks the bucket and the returned colour is the true mean of the pixels inside it.
    """
    from collections import Counter, defaultdict

    buckets: defaultdict[tuple[int, int, int], list[tuple[int, int, int]]] = defaultdict(list)
    for r, g, b in px:
        buckets[(r // 8, g // 8, b // 8)].append((r, g, b))
    key, _ = Counter({k: len(v) for k, v in buckets.items()}).most_common(1)[0]
    hits = buckets[key]
    n = len(hits)
    return (
        sum(p[0] for p in hits) / n,
        sum(p[1] for p in hits) / n,
        sum(p[2] for p in hits) / n,
    )


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


@pytest.fixture(scope="module")
def served_sra() -> Any:
    """A third server for the CLICKED ``/sra+run`` cell (ADR-0330): a synthetic cost-loaded
    schedule (``budgeted_cost`` on every working task — the JCL panel's gate) with real
    per-task Best/Worst spread (``st.sra_bcwc`` — without it the SSI run is a point mass and
    the S-curve degenerates to one point), so the four on-demand charts chart for real. The
    values are arbitrary but ASYMMETRIC (worst further than best) so the deterministic finish
    sits inside the distribution, the football cloud spans all four quadrants, and the
    frontier renders."""
    import datetime as dt

    from schedule_forensics.model.relationship import Relationship, RelationshipType
    from schedule_forensics.model.schedule import Schedule
    from schedule_forensics.model.task import Task
    from schedule_forensics.web.app import SessionState, create_app

    day = 480
    sch = Schedule(
        name="SRA-Fixture",
        source_file="sra_fixture.mpp",
        project_start=dt.datetime(2026, 1, 5, 8, 0),
        tasks=(
            Task(unique_id=1, name="Design", duration_minutes=20 * day, budgeted_cost=50000.0),
            Task(unique_id=2, name="Build", duration_minutes=30 * day, budgeted_cost=120000.0),
            Task(unique_id=3, name="Test", duration_minutes=15 * day, budgeted_cost=40000.0),
            Task(unique_id=4, name="Deliver", duration_minutes=0, is_milestone=True),
        ),
        relationships=(
            Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.FS, lag_minutes=0),
            Relationship(predecessor_id=2, successor_id=3, type=RelationshipType.FS, lag_minutes=0),
            Relationship(predecessor_id=3, successor_id=4, type=RelationshipType.FS, lag_minutes=0),
        ),
    )
    st = SessionState()
    st.schedules[sch.source_file] = sch
    st.sra_bcwc = {1: (16 * day, 30 * day), 2: (24 * day, 45 * day), 3: (12 * day, 25 * day)}

    server, base = _serve(create_app(st))
    yield base
    server.should_exit = True


def test_captions_survive_every_theme_and_scale(
    served: str, served_margin: str, served_sra: str
) -> None:
    """The whole Definition-of-Done line, as one executable assertion."""
    from playwright.sync_api import sync_playwright

    problems: list[str] = []
    known_hit: set[tuple[str, str]] = set()
    measured = 0
    inked = 0
    geometry: dict[str, list[tuple[Any, ...]]] = {}

    def _base_for(route: str) -> str:
        if route == "/margin":
            return served_margin
        if route in CLICK_RUNS:
            return served_sra
        return served

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(CHROME))
        page = browser.new_page(viewport={"width": 1600, "height": 1100})
        page.goto(served + "/", wait_until="domcontentloaded")

        def load(route: str, theme: str, scale: str) -> list[dict[str, Any]]:
            base = _base_for(route)
            real = REAL_ROUTE.get(route, route)
            # localStorage is per-ORIGIN and /margin + /sra+run run on their own ports: land on
            # the target origin first, so the theme/scale below binds to the page being measured.
            if not page.url.startswith(base):
                page.goto(base + real, wait_until="domcontentloaded")
            page.evaluate(
                "([t,s])=>{localStorage.setItem('sf-theme',t);localStorage.setItem('sf-scale',s)}",
                [theme, scale],
            )
            # NEVER wait for networkidle: heartbeat.js polls every 3s and sysmon.js every 2s, so
            # the network never goes idle and every load would burn its full timeout.
            page.goto(base + real, wait_until="domcontentloaded")
            # On-demand panels: click every Run first (the fetches overlap), THEN require each
            # panel's captions. Strict, never suppressed — a clicked panel that renders no
            # caption must fail loudly here, not hide behind the page's self-run captions.
            for button, _host in CLICK_RUNS.get(route, ()):
                page.click(button, timeout=10000)
            for _button, host in CLICK_RUNS.get(route, ()):
                page.wait_for_selector(f"{host} text.ch-at", timeout=10000, state="attached")
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
                    floor = MIN_CAPTIONS.get(route, 0)
                    if len(caps) < floor:
                        problems.append(
                            f"{where}: only {len(caps)} of >= {floor} captions rendered"
                        )
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
                        # ADR-0331: the contrast above is measured against the CANVAS. That is only
                        # the colour actually behind the glyphs when nothing is drawn there — and
                        # on a bar/line chart something usually is. Where ink overlaps the caption,
                        # the halo is what keeps the canvas contrast true, so require it.
                        if c["ink"]:
                            inked += 1
                            if not str(c["po"]).startswith("stroke"):
                                problems.append(
                                    f"{label}: {c['ink']} ink shape(s) under it, paint-order="
                                    f"{c['po']!r} — the halo is not painted under the fill"
                                )
                            if str(c["stroke"]) in ("none", "") or not float(
                                str(c["sw"]).removesuffix("px") or 0
                            ):
                                problems.append(
                                    f"{label}: {c['ink']} ink shape(s) under it but no halo "
                                    f"(stroke={c['stroke']!r}, width={c['sw']!r})"
                                )
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
    # The ink check is only worth anything if ink is actually FOUND under captions. If a future
    # refactor stopped reporting it, every halo assertion above would pass vacuously.
    assert inked >= 20, (
        f"only {inked} caption renders had ink beneath them — the ADR-0331 halo check is not "
        "exercising anything; verify the probe still sweeps non-text shapes"
    )
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
    print(f"  caption renders with chart ink beneath them (halo required): {inked}")
    print(f"  pages whose caption geometry differs by theme (expected — apollo is mono): {varied}")


def test_the_degenerate_single_bin_histogram_is_still_legible(served: str) -> None:
    """The worst case for ADR-0331, and it needs no fixture of its own: run the SSI simulation on
    the GOLDEN pair, which carries no Best/Worst spread, so the engine returns a one-point S-curve
    and a ONE-BIN histogram (``engine/sra.py``'s documented ``hi == lo`` path). That single bar
    spans the whole plot, so it lies under BOTH captions at once — the shape that proves a caption
    can be buried by data no yield rule could ever move, because the bar IS the chart.

    Kept separate from the matrix above so it costs one page load rather than twelve — and it is
    where the check is made of PIXELS rather than of CSS. The matrix asserts the halo's computed
    style, which is cheap and did catch a real breakage; but "ink is under the caption, so the
    halo must be set" has an antecedent that is true on essentially every gridded chart, so on its
    own it decays into asserting that a stylesheet rule exists — the very ADR-0304 anti-pattern
    this file exists to avoid. Here we screenshot each caption and measure what the glyphs are
    ACTUALLY read against: the modal colour of the caption's own box. Without the halo that is the
    bar fill (~1.17:1); with it, the canvas (~3.07:1 in console, the slimmest theme).
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(CHROME))
        page = browser.new_page(viewport={"width": 1600, "height": 1100})
        page.goto(served + "/sra", wait_until="domcontentloaded")
        page.click("#ssiRun", timeout=10000)
        page.wait_for_selector("#ssiCharts text.ch-at", timeout=10000, state="attached")
        page.wait_for_timeout(200)
        caps = [c for c in page.evaluate(_PROBE) if c["ink"]]
        # Element screenshots, not a clipped page shot: these captions sit far below the fold and
        # `clip` is viewport-relative, so a page shot of their box is "outside the resulting
        # image". Handle screenshots scroll the node into view themselves.
        by_text = {c["text"]: c for c in caps}
        shots: dict[str, bytes] = {}
        for handle in page.query_selector_all("#ssiCharts text.ch-at"):
            label = (handle.text_content() or "").strip()
            if label in by_text:
                handle.scroll_into_view_if_needed()
                shots[label] = handle.screenshot()
        browser.close()

    assert caps, "no caption had ink beneath it — the degenerate case did not render as expected"
    assert shots, "no caption screenshots captured — the pixel check proved nothing"
    problems = []
    for c in caps:
        shot = shots.get(c["text"])
        if shot is None:
            continue
        _w, _h, px = _png_pixels(shot)
        backdrop = _modal_color(px)
        ratio = _contrast(_rgb(c["fill"]), backdrop)
        print(
            f"\n  “{c['text']}” over {c['ink']} ink shape(s): "
            f"reads against rgb{tuple(int(v) for v in backdrop)} at {ratio:.2f}:1"
        )
        if ratio < CONTRAST_FLOOR:
            problems.append(
                f"“{c['text']}”: measured {ratio:.2f}:1 against its REAL backdrop "
                f"rgb{tuple(int(v) for v in backdrop)} — below {CONTRAST_FLOOR}"
            )
    assert not problems, "caption illegible where it actually sits:\n  " + "\n  ".join(problems)
