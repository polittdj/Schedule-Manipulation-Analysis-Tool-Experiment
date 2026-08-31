"""M3 (WP2) — the stepper / autoplay drivers, on a DRIVEN CLOCK.

The WP1 census (``test_ui_control_effect_census.py``) proved every stepper and autoplay control
EXISTS and carries an explicit ``WP2:M3`` deferral. This module discharges that deferral: it
DRIVES them and measures the effect. It is the second half of the WP1 lesson — a control that
is present, wired, and even flips its own button label can still move nothing (UI-01's grips
were 7x0px under passing byte-pins; ``test_trends_animation.py`` still pins these controls by
BYTES only, greping the served JS for ``sf-frame-prev`` and ``prefers-reduced-motion``).

Two oracles per control, and BOTH are required:

* **LABEL** — the caption element the stepper rewrites (``#volLabel``, ``#evoLabel``, the
  bow-wave's a11y caption, each ``.sf-frame-label``).
* **CHART** — a digest of the rendered chart. Deliberately DOM-shape-agnostic (tag + geometry
  attributes + inline style + leaf text over every descendant), because the animated surfaces
  are not all SVG: ``/evolution`` and ``/driving-path`` paint HTML-table Gantts and ``/trend``'s
  quality drill paints into ``#qualBars``/``#qualDrill``. An SVG-only digest reported three
  false "chart did not move" rows on the first probe run — a wrong oracle, not a defect.
  ``test_chart_digest_is_stable_and_sensitive`` proves the digest both HOLDS STILL across a
  no-op and MOVES on a real step; without that pin, every "chart moved" assertion below is
  unfalsifiable noise.

**The clock is driven, never slept on.** Autoplay runs on 1100-1800 ms timers; a wall-time wait
would make this module a 3-minute race (the WP1 sticky-scrollbar trap: a test that needs a lucky
wait is measuring a race, not a feature). Every autoplay assertion advances Playwright's fake
clock by exactly one interval. ``test_the_fake_clock_does_not_perturb_the_page`` pins that the
instrument does not change the artifact: the same page renders byte-identically with the clock
installed and without it.

What the first run of these drivers caught (both CONFIRMED-FIXED, see the ADR):

* **M3-01** — ``/mission``'s wall master never registered with the ADR-0275 coordinator.
  ``chartframe.js`` (which defines ``window.SFPlayAll``) is emitted by the layout AFTER
  ``<main>``, so ``mission.js`` — DOM script index 20 against chartframe's 24 — evaluated first
  and its ``if (window.SFPlayAll)`` guard silently skipped the registration. Hitting a chart's
  own Stop left the wall playing: precisely the symptom ADR-0275 was written to eliminate.
* **M3-02** — ``/curves``'s ``#sfPlayAll`` master never called ``register()`` at all.

``/trend`` was the only page where it worked, and only by accident: it registers from inside a
post-``fetch`` callback, by which time chartframe.js has loaded.
"""

from __future__ import annotations

import hashlib
import json
import socket
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app
from web.browser_chrome import chrome_kwargs

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests" / "fixtures" / "test_projects"
VERSIONS = [f"TP4_DataCenter_v{i}.xml" for i in range(1, 6)]
TARGET_UID = 26
N_VERSIONS = len(VERSIONS)

DP = f"/driving-path?source=11&target={TARGET_UID}"

#: A fixed instant for the fake clock. Real "now", not the epoch: ``clock.install()`` defaults to
#: 1970 and these pages draw a data-date line against the current date, so an epoch clock would
#: perturb the very geometry the digest measures.
CLOCK_TIME = "2026-08-31T12:00:00Z"


@dataclass(frozen=True)
class Stepper:
    """One Prev / Next / Play trio and the two things it must move."""

    name: str
    url: str
    prev: str
    next: str
    play: str
    label: str
    chart: str
    interval: int  # ms between autoplay beats, read from the module that owns the control


#: Every id'd stepper family the census defers to WP2:M3, with the container each one repaints.
STEPPERS = [
    Stepper(
        "cei", "/cei", "#prevSnap", "#nextSnap", "#autoPlay", "#ceiChart caption", "#ceiChart", 1600
    ),
    Stepper(
        "scurve",
        "/scurve",
        "#prevScurve",
        "#nextScurve",
        "#scurvePlay",
        "#scurveLabel",
        "#scurveChart",
        1600,
    ),
    Stepper(
        "drift",
        "/forecast",
        "#prevDrift",
        "#nextDrift",
        "#driftPlay",
        "#driftLabel",
        "#driftChart",
        1600,
    ),
    Stepper(
        "volatility",
        "/volatility",
        "#volPrev",
        "#volNext",
        "#volPlay",
        "#volLabel",
        "#volChurn",
        1600,
    ),
    Stepper(
        "performance",
        "/performance",
        "#perfPrev",
        "#perfNext",
        "#perfPlay",
        "#perfStep",
        "#perfGrid",
        1800,
    ),
    Stepper(
        "evolution",
        "/evolution",
        "#prevEvo",
        "#nextEvo",
        "#evoPlay",
        "#evoLabel",
        "#evoChart",
        1800,
    ),
    Stepper(
        "evolution-volatility",
        "/evolution",
        "#volPrev",
        "#volNext",
        "#volPlay",
        "#volLabel",
        "#volChurn",
        1600,
    ),
    Stepper(
        "trend-quality",
        "/trend",
        "#qualPrev",
        "#qualNext",
        "#qualPlay",
        "#qualLabel",
        "#qualBars",
        1600,
    ),
    Stepper("driving-path", DP, "#dpPrev", "#dpNext", "#dpPlay", "#dpLabel", "#dpChart", 1100),
]
STEPPER_IDS = [s.name for s in STEPPERS]


@dataclass(frozen=True)
class Master:
    """A page-level "Play all / Step all" that drives every per-chart stepper in lockstep."""

    name: str
    url: str
    play: str
    step: str
    interval: int


MASTERS = [
    Master("trend", "/trend", "#sfPlayAll", "#sfStepAll", 1600),
    Master("curves", "/curves", "#sfPlayAll", "#sfStepAll", 1600),
    Master("mission", "/mission", "#missionPlay", "#missionStep", 1600),
]
MASTER_IDS = [m.name for m in MASTERS]


# ── oracles ───────────────────────────────────────────────────────────────────────────────────

#: Shape-agnostic chart digest — see the module docstring. Geometry attributes cover SVG; inline
#: cssText and leaf text cover the HTML-table Gantts; ``class`` catches a re-styled state change.
_DIGEST_JS = """(sel) => {
  const box = document.querySelector(sel);
  if (!box) return "MISSING:" + sel;
  const out = [];
  box.querySelectorAll("*").forEach(el => {
    const a = n => el.getAttribute(n) || "";
    out.push(el.tagName + "|" + a("x") + "," + a("y") + "," + a("width") + "," + a("height") +
             "," + a("cx") + "," + a("cy") + "," + a("x1") + "," + a("y1") +
             "," + a("d").slice(0, 80) + "," + a("points").slice(0, 80) +
             "," + a("fill") + "," + a("class") +
             "|" + (el.style ? el.style.cssText : "") +
             "|" + (el.children.length ? "" : (el.textContent || "").slice(0, 60)));
  });
  return out.join(";");
}"""

_TEXT_JS = """(sel) => {
  const e = document.querySelector(sel);
  return e ? e.textContent.trim() : null;
}"""

#: Every per-chart frame label that belongs to a bar which actually HAS a stepper. The
#: provenance-only bar (a single-file chart: ``sfCaption`` with no frames) carries a
#: ``.sf-frame-label`` and no Next — counting it made the first probe report a phantom
#: "1 of 3 labels stuck" on /curves and /mission.
_FRAME_LABELS_JS = """() => Array.prototype.filter.call(
    document.querySelectorAll(".sf-chart-controls"),
    b => b.querySelector(".sf-frame-next"))
  .map(b => {
    const l = b.querySelector(".sf-frame-label");
    return l ? l.textContent.trim() : "";
  })"""

#: The same stepped bars, each paired with a signature of THE CHART IT SITS ON. ``sfChartControls``
#: inserts the bar into the chart's own wrapper immediately before the ``<svg>``, so the sibling
#: svg is that bar's chart. Labels alone would let a trio pass while repainting nothing — the WP0
#: defect class again, one level down.
_FRAME_PAIRS_JS = """() => Array.prototype.filter.call(
    document.querySelectorAll(".sf-chart-controls"),
    b => b.querySelector(".sf-frame-next"))
  .map(b => {
    const l = b.querySelector(".sf-frame-label");
    const svg = b.parentElement && b.parentElement.querySelector("svg");
    let sig = "NO-SVG";
    if (svg) {
      const out = [];
      svg.querySelectorAll("*").forEach(el => {
        const a = n => el.getAttribute(n) || "";
        out.push(el.tagName + a("x") + "," + a("y") + "," + a("width") + "," + a("height") +
                 "," + a("d").slice(0, 60) + "," + a("points").slice(0, 60) +
                 "," + a("cx") + "," + a("cy") +
                 "," + (el.children.length ? "" : (el.textContent || "").slice(0, 40)));
      });
      sig = out.join(";");
    }
    return [l ? l.textContent.trim() : "", sig];
  })"""


def digest(page: Any, selector: str) -> str:
    raw = page.evaluate(_DIGEST_JS, selector)
    assert not raw.startswith("MISSING:"), f"chart container absent: {raw}"
    return hashlib.sha1(raw.encode()).hexdigest()


def text(page: Any, selector: str) -> str | None:
    value: str | None = page.evaluate(_TEXT_JS, selector)
    return value


def frame_labels(page: Any) -> list[str]:
    labels: list[str] = page.evaluate(_FRAME_LABELS_JS)
    return labels


def frame_pairs(page: Any) -> list[tuple[str, str]]:
    """(label, chart-signature) for every stepped bar — both halves of the trio's oracle."""
    raw: list[list[str]] = page.evaluate(_FRAME_PAIRS_JS)
    return [(lab, hashlib.sha1(sig.encode()).hexdigest()) for lab, sig in raw]


def snapshot(page: Any, s: Stepper) -> tuple[str | None, str]:
    return text(page, s.label), digest(page, s.chart)


# ── server + browser (the r11 idiom, as in the census) ────────────────────────────────────────


def _load(client: TestClient) -> None:
    files = [("files", (n, (FIXTURES / n).read_bytes(), "text/xml")) for n in VERSIONS]
    meta = json.dumps(
        [
            {"rel": f"TP4_DataCenter/{n}", "mtime": 1_700_000_000_000 + i * 86_400_000}
            for i, n in enumerate(VERSIONS)
        ]
    )
    assert client.post("/upload", files=files, data={"file_meta": meta}).status_code == 200
    assert (
        client.post("/target", data={"uid": str(TARGET_UID)}, follow_redirects=False).status_code
        == 303
    )


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


class Driven:
    """A page on a driven clock, with its pageerrors collected."""

    def __init__(self, ctx: Any, page: Any, errors: list[str]) -> None:
        self.ctx, self.page, self.errors = ctx, page, errors

    def beat(self, ms: int) -> None:
        """Advance the FAKE clock — never ``wait_for_timeout``, which is a wall-time sleep."""
        self.page.clock.run_for(ms)

    def close(self) -> None:
        self.ctx.close()


def open_driven(browser: Any, base: str, url: str, *, reduced: bool = False) -> Driven:
    ctx = browser.new_context(
        viewport={"width": 1440, "height": 900},
        reduced_motion="reduce" if reduced else "no-preference",
    )
    page = ctx.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    # install BEFORE navigating: the fake timers are injected as an init script
    page.clock.install(time=CLOCK_TIME)
    page.goto(base + url, wait_until="networkidle")
    page.clock.run_for(1500)  # let load-time timers (deferred renders, frame mounts) fire
    return Driven(ctx, page, errors)


# ── instrument pins: the oracle and the clock must be trustworthy before anything uses them ───


def test_chart_digest_is_stable_and_sensitive(served: str, browser: Any) -> None:
    """The digest must HOLD STILL across a no-op and MOVE on a real step.

    Half of this pin is the important half. A digest that drifts on its own (an animation frame,
    a re-render on a timer, a random id) would make every "the chart moved" assertion below pass
    without proving anything — the green-test-that-cannot-fail defect this repo keeps paying for.
    """
    for s in STEPPERS:
        d = open_driven(browser, served, s.url)
        try:
            before = digest(d.page, s.chart)
            d.beat(400)  # time passes, nothing is touched
            assert digest(d.page, s.chart) == before, (
                f"{s.name}: the chart digest drifted with no interaction — it cannot be used "
                f"as an oracle for {s.chart}"
            )
            d.page.click(s.next)
            d.beat(100)
            assert digest(d.page, s.chart) != before, (
                f"{s.name}: the chart digest did not move when {s.next} stepped a frame — the "
                f"oracle is blind to this container ({s.chart})"
            )
        finally:
            d.close()


def test_the_fake_clock_does_not_perturb_the_page(served: str, browser: Any) -> None:
    """QC-1's never-mutate-the-instrument, executed: same render with and without fake timers."""
    real_ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    real = real_ctx.new_page()
    real.goto(served + "/cei", wait_until="networkidle")
    real.wait_for_timeout(800)
    real_digest = digest(real, "#ceiChart")
    real_label = text(real, "#ceiChart caption")
    real_ctx.close()

    d = open_driven(browser, served, "/cei")
    try:
        assert digest(d.page, "#ceiChart") == real_digest, (
            "the fake clock changed what the page renders — the instrument is perturbing the "
            "artifact it measures"
        )
        assert text(d.page, "#ceiChart caption") == real_label
    finally:
        d.close()


# ── the steppers ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("s", STEPPERS, ids=STEPPER_IDS)
def test_stepper_next_and_prev_move_both_the_label_and_the_chart(
    served: str, browser: Any, s: Stepper
) -> None:
    """Next advances label AND chart; Prev returns both to exactly where they were.

    Asserting the label alone would certify the WP0 defect class: a control that flips its own
    caption while the visual behind it stands still.
    """
    d = open_driven(browser, served, s.url)
    try:
        start = snapshot(d.page, s)
        d.page.click(s.next)
        d.beat(100)
        stepped = snapshot(d.page, s)
        assert stepped[0] != start[0], f"{s.name}: {s.next} left the label unchanged"
        assert stepped[1] != start[1], f"{s.name}: {s.next} left the chart unchanged"

        d.page.click(s.prev)
        d.beat(100)
        assert snapshot(d.page, s) == start, f"{s.name}: {s.prev} did not return to the frame"
        assert d.errors == [], f"{s.name}: page errors while stepping: {d.errors}"
    finally:
        d.close()


@pytest.mark.parametrize("s", STEPPERS, ids=STEPPER_IDS)
def test_stepper_wraps_through_every_loaded_version(served: str, browser: Any, s: Stepper) -> None:
    """N presses of Next visit N distinct frames and land back on the first.

    This is what makes the modulo real: a stepper clamped at the last version (or one that
    silently re-renders the same frame) fails on the distinct-frame count, not just the wrap.
    """
    d = open_driven(browser, served, s.url)
    try:
        seen = [snapshot(d.page, s)]
        for _ in range(N_VERSIONS):
            d.page.click(s.next)
            d.beat(60)
            seen.append(snapshot(d.page, s))
        labels = [lab for lab, _ in seen[:-1]]
        assert len(set(labels)) == N_VERSIONS, (
            f"{s.name}: {N_VERSIONS} presses produced {len(set(labels))} distinct frames: {labels}"
        )
        assert seen[-1] == seen[0], f"{s.name}: {N_VERSIONS} presses did not wrap to the start"
    finally:
        d.close()


@pytest.mark.parametrize("s", STEPPERS, ids=STEPPER_IDS)
def test_autoplay_advances_on_the_clock_and_pause_freezes_it(
    served: str, browser: Any, s: Stepper
) -> None:
    """Play beats the frame forward once per interval; Pause stops it dead.

    Every advance is a fake-clock ``run_for``. The pause half is the one that matters: a Play
    that starts a timer nothing can clear is the ADR-0275 symptom ("hit stop, it kept playing").
    """
    d = open_driven(browser, served, s.url)
    try:
        idle = text(d.page, s.play)
        d.page.click(s.play)
        d.beat(50)
        running = text(d.page, s.play)
        assert running != idle, f"{s.name}: {s.play} did not change its own label on start"

        beat0 = snapshot(d.page, s)
        d.beat(s.interval)
        beat1 = snapshot(d.page, s)
        assert beat1 != beat0, f"{s.name}: no advance after one {s.interval}ms beat"
        d.beat(s.interval)
        beat2 = snapshot(d.page, s)
        assert beat2 != beat1, f"{s.name}: autoplay stalled after a single beat"

        d.page.click(s.play)
        d.beat(50)
        assert text(d.page, s.play) == idle, f"{s.name}: {s.play} did not restore its idle label"
        paused = snapshot(d.page, s)
        d.beat(s.interval * 4)
        assert snapshot(d.page, s) == paused, (
            f"{s.name}: the chart kept advancing through four beats AFTER Pause — the timer "
            f"outlived the control that started it"
        )
        assert d.errors == [], f"{s.name}: page errors while auto-playing: {d.errors}"
    finally:
        d.close()


@pytest.mark.parametrize("s", STEPPERS, ids=STEPPER_IDS)
def test_autoplay_honours_reduced_motion_with_one_frame_and_no_timer(
    served: str, browser: Any, s: Stepper
) -> None:
    """Under prefers-reduced-motion, Play advances exactly one frame and starts NO timer."""
    d = open_driven(browser, served, s.url, reduced=True)
    try:
        before = snapshot(d.page, s)
        d.page.click(s.play)
        d.beat(60)
        after = snapshot(d.page, s)
        assert after != before, f"{s.name}: reduced-motion Play did not advance the single frame"
        d.beat(s.interval * 4)
        assert snapshot(d.page, s) == after, (
            f"{s.name}: reduced-motion Play started a timer anyway — four beats moved the chart"
        )
        assert d.errors == [], f"{s.name}: page errors under reduced motion: {d.errors}"
    finally:
        d.close()


def test_driving_path_autoplay_stops_at_the_last_version(served: str, browser: Any) -> None:
    """/driving-path's autoplay is the one that must NOT wrap: it rewinds, runs, and halts.

    ``driving_path.js`` restarts at version 1 on Play and clears its own timer once the newest
    version is reached — a deliberate difference from every other family's modulo.
    """
    d = open_driven(browser, served, DP)
    try:
        idle = text(d.page, "#dpPlay")
        d.page.click("#dpPlay")
        d.beat(50)
        assert text(d.page, "#dpPlay") != idle
        assert "1/5" in (text(d.page, "#dpLabel") or ""), "Play did not rewind to the first version"
        for _ in range(N_VERSIONS + 2):
            d.beat(1100)
        assert "5/5" in (text(d.page, "#dpLabel") or ""), "autoplay did not reach the last version"
        assert text(d.page, "#dpPlay") == idle, (
            "autoplay reached the last version but never restored its idle label — it did not "
            "stop itself"
        )
        assert d.errors == []
    finally:
        d.close()


# ── the sf-frame trio: 138 id-less buttons across /trend, /curves and /mission ─────────────────


@pytest.mark.parametrize("url", ["/trend", "/curves", "/mission"])
def test_every_sf_frame_trio_steps_only_its_own_chart(served: str, browser: Any, url: str) -> None:
    """Each per-chart Next advances THAT bar's label and leaves its neighbours alone.

    The trio is id-less and shared by trend/curves/margin, so the census can only count it. This
    is what proves the count is 138 live controls rather than 138 rendered corpses — and the
    "neighbours alone" half is what separates a real per-chart stepper from a page-wide redraw.
    """
    d = open_driven(browser, served, url)
    try:
        bars = d.page.query_selector_all(".sf-chart-controls")
        stepped = [b for b in bars if b.query_selector(".sf-frame-next")]
        assert stepped, f"{url}: no framed charts found"
        for i, bar in enumerate(stepped):
            before = frame_pairs(d.page)
            nxt = bar.query_selector(".sf-frame-next")
            assert nxt is not None
            nxt.scroll_into_view_if_needed()
            nxt.click()
            d.beat(60)
            after = frame_pairs(d.page)
            moved = [j for j in range(len(before)) if before[j] != after[j]]
            assert moved == [i], (
                f"{url}: bar {i}'s Next moved frames {moved}, expected exactly [{i}] — a "
                f"per-chart stepper must not repaint its neighbours"
            )
            assert before[i][0] != after[i][0], f"{url}: bar {i}'s Next did not move its label"
            assert before[i][1] != after[i][1], (
                f"{url}: bar {i}'s Next moved its label but its chart did not repaint"
            )
            prev = bar.query_selector(".sf-frame-prev")
            assert prev is not None, f"{url}: bar {i} has a Next but no Prev"
            prev.scroll_into_view_if_needed()
            prev.click()
            d.beat(60)
            assert frame_pairs(d.page) == before, (
                f"{url}: bar {i}'s Prev did not return it to the frame Next left"
            )
        assert d.errors == [], f"{url}: page errors stepping the trio: {d.errors}"
    finally:
        d.close()


@pytest.mark.parametrize("url", ["/trend", "/curves", "/mission"])
def test_sf_frame_play_runs_on_the_clock_and_its_stop_halts_it(
    served: str, browser: Any, url: str
) -> None:
    """A per-chart ▶ Play beats on the clock, and its own Stop actually stops it."""
    d = open_driven(browser, served, url)
    try:
        bar = next(
            b
            for b in d.page.query_selector_all(".sf-chart-controls")
            if b.query_selector(".sf-frame-play")
        )
        play = bar.query_selector(".sf-frame-play")
        assert play is not None
        play.scroll_into_view_if_needed()
        idle = play.text_content()
        play.click()
        d.beat(50)
        assert play.text_content() != idle, f"{url}: per-chart Play did not change its label"
        before = frame_labels(d.page)
        d.beat(1600)
        assert frame_labels(d.page) != before, f"{url}: per-chart Play did not beat on the clock"

        play.click()
        d.beat(50)
        assert play.text_content() == idle, f"{url}: per-chart Stop did not restore its label"
        paused = frame_labels(d.page)
        d.beat(1600 * 4)
        assert frame_labels(d.page) == paused, (
            f"{url}: the per-chart chart kept animating after its own Stop"
        )
        assert d.errors == []
    finally:
        d.close()


# ── the page masters, and the ADR-0275 coordinator ────────────────────────────────────────────


@pytest.mark.parametrize("m", MASTERS, ids=MASTER_IDS)
def test_master_step_all_advances_every_framed_chart_in_lockstep(
    served: str, browser: Any, m: Master
) -> None:
    """One press of Step all moves EVERY framed chart on the page, not merely the first."""
    d = open_driven(browser, served, m.url)
    try:
        before = frame_labels(d.page)
        assert before, f"{m.name}: no framed charts to step"
        d.page.click(m.step)
        d.beat(100)
        after = frame_labels(d.page)
        stuck = [i for i in range(len(before)) if before[i] == after[i]]
        assert not stuck, f"{m.name}: Step all left frames {stuck} behind (of {len(before)})"
        assert d.errors == [], f"{m.name}: page errors on Step all: {d.errors}"
    finally:
        d.close()


@pytest.mark.parametrize("m", MASTERS, ids=MASTER_IDS)
def test_master_play_all_beats_on_the_clock_and_pauses(
    served: str, browser: Any, m: Master
) -> None:
    """Play all advances every chart once per clock beat, and Pause all stops every one."""
    d = open_driven(browser, served, m.url)
    try:
        idle = text(d.page, m.play)
        d.page.click(m.play)
        d.beat(50)
        assert text(d.page, m.play) != idle, f"{m.name}: Play all did not change its own label"
        before = frame_labels(d.page)
        d.beat(m.interval)
        after = frame_labels(d.page)
        stuck = [i for i in range(len(before)) if before[i] == after[i]]
        assert not stuck, f"{m.name}: one clock beat left frames {stuck} behind"

        d.page.click(m.play)
        d.beat(50)
        assert text(d.page, m.play) == idle, f"{m.name}: Pause all did not restore its label"
        paused = frame_labels(d.page)
        d.beat(m.interval * 3)
        assert frame_labels(d.page) == paused, f"{m.name}: charts kept moving after Pause all"
        assert d.errors == []
    finally:
        d.close()


@pytest.mark.parametrize("m", MASTERS, ids=MASTER_IDS)
def test_master_is_registered_with_the_play_all_coordinator(
    served: str, browser: Any, m: Master
) -> None:
    """ADR-0275's registry must actually hold this master (M3-01 / M3-02).

    Asked of the coordinator directly rather than through a click, so a failure names the cause:
    ``SFPlayAll.stopAll()`` is the one thing every per-chart control ultimately calls. If the
    master keeps running through it, ``register()`` never happened — which is exactly what
    ``mission.js`` (evaluated before ``chartframe.js`` defines the registry) and ``curves.js``
    (which never called it) both did.
    """
    d = open_driven(browser, served, m.url)
    try:
        assert d.page.evaluate("() => !!window.SFPlayAll"), "the coordinator itself is missing"
        idle = text(d.page, m.play)
        d.page.click(m.play)
        d.beat(50)
        assert text(d.page, m.play) != idle, f"{m.name}: the master did not start"
        d.page.evaluate("() => window.SFPlayAll.stopAll()")
        d.beat(50)
        assert text(d.page, m.play) == idle, (
            f"{m.name}: SFPlayAll.stopAll() left the master's label reading "
            f"'{text(d.page, m.play)}' — the registry does not hold this master"
        )
        frozen = frame_labels(d.page)
        d.beat(m.interval * 3)
        assert frame_labels(d.page) == frozen, (
            f"{m.name}: SFPlayAll.stopAll() did not stop the master — it was never registered "
            f"with the ADR-0275 coordinator"
        )
        assert d.errors == []
    finally:
        d.close()


@pytest.mark.parametrize("m", MASTERS, ids=MASTER_IDS)
def test_a_real_click_on_a_chart_control_halts_the_master(
    served: str, browser: Any, m: Master
) -> None:
    """ADR-0275, end to end: touching a chart by hand takes manual control and the master halts.

    Driven with a REAL mouse click (``isTrusted`` true) — the coordinator deliberately ignores the
    master's own programmatic ``element.click()``, so an ``evaluate``-driven click would prove
    nothing here.
    """
    d = open_driven(browser, served, m.url)
    try:
        d.page.click(m.play)
        d.beat(50)
        playing = text(d.page, m.play)
        before = frame_labels(d.page)
        d.beat(m.interval)
        assert frame_labels(d.page) != before, f"{m.name}: master was not running to begin with"

        prev = d.page.query_selector(".sf-frame-prev")
        assert prev is not None, f"{m.name}: no per-chart control to take manual control with"
        prev.scroll_into_view_if_needed()
        prev.click()
        d.beat(50)
        assert text(d.page, m.play) != playing, (
            f"{m.name}: the master's own label still reads '{playing}' after a manual click on a "
            f"per-chart control"
        )
        halted = frame_labels(d.page)
        d.beat(m.interval * 3)
        assert frame_labels(d.page) == halted, (
            f"{m.name}: the master kept stepping the charts through three beats after a real "
            f"user click on a per-chart control (ADR-0275: 'hit stop, it kept playing')"
        )
        assert d.errors == []
    finally:
        d.close()


def test_the_masters_own_programmatic_beat_does_not_stop_the_master(
    served: str, browser: Any
) -> None:
    """The other half of ADR-0275: an untrusted ``.click()`` must NOT halt the master.

    Without this pin the coordinator could be "fixed" by stopping on every click — which would
    make Play all stop itself on its first beat, since that beat IS a programmatic click on the
    per-chart Next buttons.
    """
    d = open_driven(browser, served, "/trend")
    try:
        d.page.click("#sfPlayAll")
        d.beat(50)
        running = text(d.page, "#sfPlayAll")
        d.page.evaluate("() => document.querySelector('.sf-frame-next').click()")
        d.beat(50)
        assert text(d.page, "#sfPlayAll") == running, (
            "a programmatic (untrusted) click stopped the master — Play all would halt on its "
            "own first beat"
        )
        before = frame_labels(d.page)
        d.beat(1600)
        assert frame_labels(d.page) != before, "the master stopped beating after its own click"
        assert d.errors == []
    finally:
        d.close()


# ── the wall's embedded per-chart steppers ────────────────────────────────────────────────────

#: The dedicated-page steppers the Mission wall re-hosts as tiles. Each one is censused on
#: /mission separately from its own page, so each is driven here separately too.
WALL_STEPPERS = [
    ("#prevScurve", "#nextScurve", "#scurvePlay", "#scurveLabel"),
    ("#prevSnap", "#nextSnap", "#autoPlay", "#ceiChart caption"),
    ("#prevDrift", "#nextDrift", "#driftPlay", "#driftLabel"),
    ("#qualPrev", "#qualNext", "#qualPlay", "#qualLabel"),
    ("#prevEvo", "#nextEvo", "#evoPlay", "#evoLabel"),
]


def test_mission_wall_embedded_steppers_each_drive_their_own_tile(
    served: str, browser: Any
) -> None:
    """Every stepper the wall re-hosts steps its own tile there, not only on its own page."""
    d = open_driven(browser, served, "/mission")
    try:
        for prev, nxt, play, label in WALL_STEPPERS:
            start = text(d.page, label)
            assert start is not None, f"/mission: {label} is absent"
            d.page.click(nxt)
            d.beat(60)
            assert text(d.page, label) != start, f"/mission: {nxt} did not advance {label}"
            d.page.click(prev)
            d.beat(60)
            assert text(d.page, label) == start, f"/mission: {prev} did not return {label}"

            idle = text(d.page, play)
            d.page.click(play)
            d.beat(1800)
            assert text(d.page, label) != start, f"/mission: {play} did not beat {label} forward"
            d.page.click(play)
            d.beat(60)
            assert text(d.page, play) == idle, f"/mission: {play} did not restore its idle label"
        assert d.errors == [], f"/mission: page errors: {d.errors}"
    finally:
        d.close()
