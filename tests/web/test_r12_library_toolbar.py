"""Rank 12 toolbar/read-me sweep — the six Library/Setup pages wear the panel contract (ADR-0327).

The six pages (/margin, /workbench, /standards, /groups, /card/{name}, /wbs/{name}) were the
last data-visual pages with no ``panelkit.js`` include and no ``_panel_head``/``_shell_tools``
strip (ADR-0311 recorded the debt; ADR-0325/0326 cleared the two blockers). What this pins,
per hazard — the same standards the r11 module set:

* **the include** — ``panelkit.js`` exactly once per loaded page (two registered listeners
  toggle ``.is-big`` twice and net to nothing), matched in its cache-busted ``?v=`` form; and
  ABSENT on every empty-state branch, which renders no contract control at all (a script with
  nothing to drive is a dead promise — the r11 law);
* **every ⤓ destination is live** — each ``data-export`` on the six pages is fetched and must
  answer 200 with the ``PK`` zip magic. The collector also pins the expected COUNT per page,
  so the test cannot pass vacuously on a tree that renders no ⤓ at all;
* **the ⤓ that must NOT exist** — /groups (no covering export; a URL-preview scope can differ
  from the applied scope every export reads), /card (the KPI set is no workbook's sheet; the
  pivots panel is 1-of-4 covered — pointing there hands back less than the panel draws),
  /standards §2 Fuse + §3 SEM (no export carries those families), /margin's risk-sufficiency
  panel (its Zero-margin toggle is live state a STATIC ``data-export`` cannot follow — the
  round-10 defect class), and /workbench's head strip (its ribbon exports already ship as the
  panel's own labeled links — a glyph would duplicate the same URL inside one panel). Each
  absence assertion is paired with a presence assertion in the same chunk so it cannot pass
  vacuously against a renamed or dropped panel;
* **the read-me line** — every converted data-visual panel carries a muted explainer, and the
  panels that LACKED one (margin per-version table, card pivots, standards §1, the groups
  breakdown) are asserted by their new content, harvested from the render;
* **the promotion census** — the conversion decorated panels that were already ``.panel``
  (verified equal on the pre-change tree via ``git stash``: 7/2/5/5/3/3 on the module
  fixtures), so nothing new joins jarvis's broad ``.panel`` fight;
* **the loaded-terms gate WITH ITS CONTROL** — every visible string this round added is
  harvested from the render and run through ``introduces_loaded_terms``, after first proving
  the gate is alive;
* **the effect, in real chromium** — a ⛶ click on a converted panel measurably lifts it into
  the focus overlay (``getBoundingClientRect`` changes; ``position`` goes ``fixed``) and
  Escape restores it. One utility page (/margin) and one per-file drill (/card) are proven;
  all six share the same block-layout panels, base.css rules and delegated listener, and the
  include itself is pinned server-side on every page above.

The browser half skips cleanly where playwright/chromium are absent (runtime stays std-lib
only); the markup, export, census and gate halves always run.
"""

from __future__ import annotations

import datetime as dt
import html
import re
import socket
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.ai.citations import introduces_loaded_terms
from schedule_forensics.model.calendar import Calendar  # noqa: F401  (fixture parity import)
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import SessionState, create_app

REPO = Path(__file__).resolve().parents[2]
GOLD = REPO / "tests" / "fixtures" / "golden" / "project2_5"
# build-agnostic (TEST-01, ADR-0406): the FIRST vendored chromium, whatever build the
# container ships — a chromium bump must never silently skip this module again
_PW_CHROMES = sorted(Path("/opt/pw-browsers").glob("chromium*/chrome-linux/chrome"))
CHROME = _PW_CHROMES[0] if _PW_CHROMES else Path("/opt/pw-browsers/absent/chrome")

DAY = 480

# ── fixtures ──────────────────────────────────────────────────────────────────────────────────


def _t(uid: int, name: str, days: float, **kw: object) -> Task:
    return Task(unique_id=uid, name=name, duration_minutes=int(days * DAY), **kw)  # type: ignore[arg-type]


def _r(p: int, s: int) -> Relationship:
    return Relationship(predecessor_id=p, successor_id=s, type=RelationshipType.FS, lag_minutes=0)


def _margin_version(status: str, margin_days: float) -> Schedule:
    """One synthetic monthly version with a named MARGIN buffer (the margin-suite fixture)."""
    return Schedule(
        name=status,
        source_file=f"{status}.mpp",
        project_start=dt.datetime(2026, 1, 5, 8, 0),
        status_date=dt.datetime.fromisoformat(status),
        tasks=(
            _t(1, "Work", 500),
            _t(2, "Schedule MARGIN: pre-delivery", margin_days),
            _t(3, "Deliver SV1", 0, is_milestone=True),
        ),
        relationships=(_r(1, 2), _r(2, 3)),
    )


_MARGINS = [("2026-02-27", 40), ("2026-03-31", 30), ("2026-04-30", 20), ("2026-05-29", 10)]


@pytest.fixture(scope="module")
def margin_client() -> TestClient:
    st = SessionState()
    for status, m in _MARGINS:
        v = _margin_version(status, m)
        st.schedules[v.source_file] = v
    return TestClient(create_app(st))


@pytest.fixture(scope="module")
def client() -> TestClient:
    """The golden Project2/Project5 pair — drives /workbench, /standards, /groups, /card, /wbs."""
    c = TestClient(create_app(SessionState()))
    for name in ("Project2.mspdi.xml", "Project5.mspdi.xml"):
        r = c.post("/upload", files={"files": (name, (GOLD / name).read_bytes(), "text/xml")})
        assert r.status_code == 200
    return c


GOLD_ROUTES = ("/workbench", "/standards", "/groups", "/card/Project5", "/wbs/Project5")


@pytest.fixture(scope="module")
def pages(client: TestClient, margin_client: TestClient) -> dict[str, str]:
    """Each page rendered once — every markup assertion reads the SAME bytes."""
    out = {r: client.get(r).text for r in GOLD_ROUTES}
    out["/margin"] = margin_client.get("/margin").text
    return out


# ── html helpers (the r11 vocabulary) ─────────────────────────────────────────────────────────

_PANEL_OPEN = re.compile(r'<(?:div|section)[^>]*\bclass="?[^">]*\bpanel(?![-\w])[^">]*"?[^>]*>')
_H = re.compile(r"<h[23][^>]*>(.*?)</h[23]>", re.S)
_CTRL_TAG = re.compile(r"<button[^>]*\bdata-sf-(?:big|excel|data)\b[^>]*>")
_EXPORT = re.compile(r'data-export="([^"]+)"')
_MUTED = re.compile(r"<p class=\"?muted\"?[^>]*>", re.S)
_INCLUDE = re.compile(r'<script src="/static/panelkit\.js\?v=[^"]+"></script>')


def _panels(page: str) -> list[str]:
    starts = [m.start() for m in _PANEL_OPEN.finditer(page)]
    bounds = [*starts, len(page)]
    return [page[bounds[i] : bounds[i + 1]] for i in range(len(starts))]


def _panel_titled(page: str, needle: str) -> str:
    hits = [c for c in _panels(page) if any(needle in h for h in _H.findall(c))]
    assert len(hits) == 1, f"{needle!r}: expected 1 panel, found {len(hits)}"
    return hits[0]


def _glyphs(chunk: str) -> set[str]:
    """The contract-control kinds a panel chunk renders (big/excel/data)."""
    return {
        m.group(0).split("data-sf-")[1].split()[0].rstrip(">") for m in _CTRL_TAG.finditer(chunk)
    }


def _visible(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


# ── (a) the include, exactly once per loaded page ─────────────────────────────────────────────


def test_panelkit_is_included_exactly_once_on_every_library_page(pages: dict[str, str]) -> None:
    for route, page in pages.items():
        assert page.count("/static/panelkit.js") == 1, route
        assert len(_INCLUDE.findall(page)) == 1, route


def test_panelkit_is_absent_on_every_empty_state() -> None:
    """The empty branches render a bare notice and NO contract control — the driver must not
    ship with nothing to drive (and none of the contract vocabulary may leak there)."""
    c = TestClient(create_app(SessionState()))
    for route in ("/margin", "/workbench", "/standards", "/groups"):
        page = c.get(route).text
        assert "/static/panelkit.js" not in page, route
        for token in ("panel-head", "sf-tools", "data-sf-big", "data-export"):
            assert token not in page, (route, token)


# ── (b) every ⤓ destination is live, and the counts pin the conversion ────────────────────────

#: data-export occurrences per page: 3 on /margin (burn-down, MET, per-version — all the ONE
#: margin workbook), 1 on /standards (the DCMA panel → the analysis workbook), 2 on /wbs (both
#: pivots → the WBS workbook), and ZERO on /workbench (links, not glyph), /groups and /card
#: (refused — see the module docstring). A pre-sweep tree renders zero everywhere, so the
#: count pins keep the liveness loop from passing vacuously.
EXPECTED_EXPORT_COUNTS = {
    "/margin": 3,
    "/workbench": 0,
    "/standards": 1,
    "/groups": 0,
    "/card/Project5": 0,
    "/wbs/Project5": 2,
}


def test_every_export_destination_is_live(
    pages: dict[str, str], client: TestClient, margin_client: TestClient
) -> None:
    for route, page in pages.items():
        urls = _EXPORT.findall(page)
        assert len(urls) == EXPECTED_EXPORT_COUNTS[route], (route, urls)
        fetcher = margin_client if route == "/margin" else client
        for url in set(urls):
            r = fetcher.get(html.unescape(url))
            assert r.status_code == 200, (route, url, r.status_code)
            assert r.content[:2] == b"PK", (route, url, "not a zip/xlsx payload")


# ── (c) toolbar anatomy, panel by panel ───────────────────────────────────────────────────────


def test_margin_panels_wear_the_contract(pages: dict[str, str]) -> None:
    page = pages["/margin"]
    for title in (
        "Margin &amp; Contingency Burn-Down",
        "Margin Erosion Trend (MET)",
        "Per-version figures",
    ):
        chunk = _panel_titled(page, title)
        assert _glyphs(chunk) == {"big", "excel"}, title
        assert "/export/xlsx/margin" in chunk, title
        assert "prov-chip" in chunk, title
    risk = _panel_titled(page, "Risk-based margin sufficiency")
    assert _glyphs(risk) == {"big"}, "risk panel must be ⛶-only (live-state toggle — no ⤓)"
    assert "data-export" not in risk
    # the operator CONTROLS are forms, not data visuals — no toolbar on either
    for needle in ("Gold-Rule margin requirement", "Figure 5-30 guideline band"):
        control = next(c for c in _panels(page) if needle in c)
        assert "sf-tools" not in control, needle


def test_workbench_panel_is_enlarge_only_with_its_links_intact(pages: dict[str, str]) -> None:
    page = pages["/workbench"]
    chunk = _panel_titled(page, "Metric Workbench")
    assert _glyphs(chunk) == {"big"}, "⤓ rides the panel's own labeled links, not the strip"
    assert "prov-chip" in chunk
    assert chunk.count('href="/export/xlsx/workbench"') == 1  # the pinned ribbon Excel link
    assert chunk.count('href="/export/docx/workbench"') == 1  # …and Word stays a capability


def test_standards_sections_split_covered_from_uncovered(pages: dict[str, str]) -> None:
    page = pages["/standards"]
    dcma = _panel_titled(page, "DCMA-14 point assessment")
    assert _glyphs(dcma) == {"big", "excel"}
    assert "/export/xlsx/analysis/" in dcma
    # take → read-me order: the counts line is the .sf-take, the anatomy line the muted read-me
    take_at = dcma.index("sf-take")
    readme_at = dcma.index("One row per DCMA-14 check")
    assert take_at < readme_at
    for title in ("Acumen-Fuse execution indices", "Schedule Execution Metrics (SEM)"):
        chunk = _panel_titled(page, title)
        assert _glyphs(chunk) == {"big"}, f"{title}: no export covers this family — ⛶ only"
        assert "data-export" not in chunk, title
        assert "prov-chip" in chunk, title


def test_groups_and_card_panels_are_enlarge_only(pages: dict[str, str], client: TestClient) -> None:
    # /groups, no filter: the Active-scope panel is deliberately a bare status NOTICE (no
    # toolbar — not a data visual); the preview scorecard is the page's data visual.
    page = pages["/groups"]
    assert "data-export" not in page, "the /groups ⤓ refusal is page-wide"
    notice = _panel_titled(page, "Active scope")
    assert "sf-tools" not in notice, "the no-filter notice branch must stay bare"
    preview = _panel_titled(page, "Preview &mdash; metric scorecard")
    assert _glyphs(preview) == {"big"}
    assert "prov-chip" in preview
    # /groups with a URL-preview filter: the Active-scope panel becomes the reach data visual
    filtered = client.get("/groups?field=Activity Type&value=Normal").text
    assert "data-export" not in filtered
    scope = _panel_titled(filtered, "Active scope")
    assert _glyphs(scope) == {"big"}
    assert "prov-chip" in scope
    assert "Per file" in scope  # the reach table is the panel's data
    # /card: both panels ⛶-only with this file's chip
    card = pages["/card/Project5"]
    assert "data-export" not in card, "the /card ⤓ refusal is page-wide"
    for title in ("Schedule card", "Makeup, status &amp; performance pivots"):
        chunk = _panel_titled(card, title)
        assert _glyphs(chunk) == {"big"}, title
        assert "prov-chip" in chunk, title


def test_wbs_panels_carry_the_workbook_export(pages: dict[str, str]) -> None:
    page = pages["/wbs/Project5"]
    for title in ("Completion metrics by WBS", "SPI(t) &amp; Earned Schedule by WBS"):
        chunk = _panel_titled(page, title)
        assert _glyphs(chunk) == {"big", "excel"}, title
        assert "/export/xlsx/wbs/Project5" in chunk, title
        assert "prov-chip" in chunk, title


# ── (d) the read-me line on every converted data visual ───────────────────────────────────────

#: the four panels that lacked ANY explainer before this round, asserted by their new content
NEW_READMES = {
    "/margin": "One row per loaded status date",
    "/card/Project5": "Four pivots of the same activity population",
    "/standards": "One row per DCMA-14 check",
}


def test_every_converted_panel_carries_a_muted_readme(pages: dict[str, str]) -> None:
    checks = {
        "/margin": (
            "Margin &amp; Contingency Burn-Down",
            "Margin Erosion Trend (MET)",
            "Per-version figures",
            "Risk-based margin sufficiency",
        ),
        "/workbench": ("Metric Workbench",),
        "/standards": (
            "DCMA-14 point assessment",
            "Acumen-Fuse execution indices",
            "Schedule Execution Metrics (SEM)",
        ),
        "/groups": ("Active scope", "Preview &mdash; metric scorecard"),
        "/card/Project5": ("Schedule card", "Makeup, status &amp; performance pivots"),
        "/wbs/Project5": ("Completion metrics by WBS", "SPI(t) &amp; Earned Schedule by WBS"),
    }
    for route, titles in checks.items():
        for title in titles:
            chunk = _panel_titled(pages[route], title)
            assert _MUTED.search(chunk), (route, title, "no muted read-me line")
    for route, needle in NEW_READMES.items():
        assert needle in pages[route], (route, "the NEW read-me content is missing")


def test_groups_breakdown_pivot_wears_head_tools_and_readme(client: TestClient) -> None:
    page = client.get("/groups?breakdown=Activity+Type").text
    chunk = _panel_titled(page, "Breakdown by Activity Type")
    assert _glyphs(chunk) == {"big"}
    assert "One row per distinct value" in chunk
    assert "data-export" not in chunk  # 200-value truncation → a partial export would lie


# ── (e) the promotion census ──────────────────────────────────────────────────────────────────

#: .panel count per page on THESE fixtures, verified equal on the pre-sweep tree (the sweep
#: decorates existing panels; it may not mint new ones for jarvis's broad rule to fight).
PANEL_CENSUS = {
    "/margin": 7,
    "/workbench": 2,
    "/standards": 5,
    "/groups": 5,
    "/card/Project5": 3,
    "/wbs/Project5": 3,
}


def test_promotion_census_no_new_panels(pages: dict[str, str]) -> None:
    for route, page in pages.items():
        assert len(_panels(page)) == PANEL_CENSUS[route], route


# ── (f) the loaded-terms gate, control first ──────────────────────────────────────────────────


def test_new_visible_strings_pass_the_loaded_terms_gate(pages: dict[str, str]) -> None:
    assert introduces_loaded_terms("", "deliberate concealed fraud") is True, "the gate is dead"
    harvested: list[str] = []
    for route, chunk_titles in (
        ("/margin", ("Per-version figures",)),
        ("/card/Project5", ("Makeup, status &amp; performance pivots",)),
        ("/standards", ("DCMA-14 point assessment",)),
    ):
        for title in chunk_titles:
            harvested.append(_visible(_panel_titled(pages[route], title)))
    harvested.append(_visible(_panel_titled(pages["/wbs/Project5"], "Completion metrics by WBS")))
    assert harvested and all(h for h in harvested)
    for text in harvested:
        assert introduces_loaded_terms("", text) is False, text[:120]


# ── (g) the effect, in real chromium ──────────────────────────────────────────────────────────


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = int(s.getsockname()[1])
    s.close()
    return port


@pytest.fixture(scope="module")
def served_margin() -> Any:
    pytest.importorskip("playwright", reason="playwright not installed (deliberate)")
    if not CHROME.exists():
        pytest.skip(f"bundled chromium not at {CHROME}")
    import uvicorn

    st = SessionState()
    for status, m in _MARGINS:
        v = _margin_version(status, m)
        st.schedules[v.source_file] = v
    app = create_app(st)
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


@pytest.fixture(scope="module")
def served_gold() -> Any:
    pytest.importorskip("playwright", reason="playwright not installed (deliberate)")
    if not CHROME.exists():
        pytest.skip(f"bundled chromium not at {CHROME}")
    import uvicorn

    app = create_app(SessionState())
    with TestClient(app) as c:
        for name in ("Project2.mspdi.xml", "Project5.mspdi.xml"):
            r = c.post("/upload", files={"files": (name, (GOLD / name).read_bytes(), "text/xml")})
            assert r.status_code == 200
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


def _prove_measured_enlarge(page: Any, panel_sel: str) -> None:
    """The r11 standard: a ⛶ click must CHANGE the panel's measured box (class flips are not
    proof — ADR-0304), lift it to a fixed overlay, and Escape must restore the original box."""
    assert page.evaluate(
        "() => [...document.scripts].some(s => s.src.includes('/static/panelkit.js'))"
    ), f"panelkit.js script element missing ({page.url})"
    rect_js = f"() => document.querySelector('{panel_sel}').getBoundingClientRect().toJSON()"
    before = page.evaluate(rect_js)
    btn = page.locator(f"{panel_sel} [data-sf-big]")
    assert btn.inner_text() == "⛶ ENLARGE"
    btn.click()
    page.wait_for_timeout(80)
    after = page.evaluate(rect_js)
    assert (before["width"], before["height"], before["y"]) != (
        after["width"],
        after["height"],
        after["y"],
    ), f"⛶ moved nothing on {page.url} — the r10 silent-rot defect"
    assert (
        page.evaluate(f"() => getComputedStyle(document.querySelector('{panel_sel}')).position")
        == "fixed"
    ), "block-layout panel did not lift into the focus overlay"
    page.keyboard.press("Escape")
    page.wait_for_timeout(80)
    restored = page.evaluate(rect_js)
    assert round(restored["width"]) == round(before["width"]), "Escape did not restore the panel"


def test_margin_enlarge_measurably_lifts_in_chromium(served_margin: str) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(CHROME))
        page = browser.new_page(viewport={"width": 1360, "height": 900})
        page.goto(served_margin + "/margin", wait_until="domcontentloaded")
        page.wait_for_selector("#marginBurndownChart", timeout=10000)
        sel = '.panel[data-export="/export/xlsx/margin"]:has(#marginBurndownChart)'
        _prove_measured_enlarge(page, sel)
        browser.close()


def test_card_enlarge_measurably_lifts_in_chromium(served_gold: str) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=str(CHROME))
        page = browser.new_page(viewport={"width": 1360, "height": 900})
        page.goto(served_gold + "/card/Project5", wait_until="domcontentloaded")
        page.wait_for_selector(".card-cols", timeout=10000)
        _prove_measured_enlarge(page, ".panel:has(.card-cols)")
        browser.close()


# ── (h) the codex-review round (PR #501): population-accurate chips + the target panel ────────
# Five bot findings, each verified against the code before acting (ADR-0327 addendum): the
# /margin and /workbench series chips were built from EVERY loaded version while their panels
# draw only the ANALYZABLE subset (_margin_dashboard_for / _workbench_versions both skip
# CPMError versions) — a chip could name a file that contributes nothing; the /groups
# breakdown and saved-group previews carried tools but no source attribution (an enlarged
# overlay hides the page's file picker); and _target_panel still rendered a bare h2 — the
# ADR's original consequence bullet claiming it "already rendered head-strip markup" was a
# MISREAD of the /path workspace head, caught by the external review.


def _cyclic_version(name: str, day: int) -> Schedule:
    """A dated but CPM-unsolvable version (1↔2 logic cycle) — the population the chips must
    NOT count or name (the coverage-suite `_cyclic` pattern)."""
    s = dt.datetime(2026, 6, day, 8, 0)
    f = dt.datetime(2026, 6, day + 1, 17, 0)
    return Schedule(
        name=name,
        source_file=f"{name}.xml",
        project_start=dt.datetime(2026, 6, 1),
        status_date=dt.datetime(2026, 6, day + 2),
        tasks=(
            _t(1, "A", 1, start=s, finish=f, baseline_finish=f),
            _t(2, "B", 1, start=s, finish=f, baseline_finish=f),
        ),
        relationships=(_r(1, 2), _r(2, 1)),
    )


@pytest.fixture(scope="module")
def mixed_client() -> TestClient:
    """Four solvable margin versions PLUS one unsolvable (cycle) version — the chip's honest
    population is 4, the raw loaded count is 5."""
    st = SessionState()
    for status, m in _MARGINS:
        v = _margin_version(status, m)
        st.schedules[v.source_file] = v
    cyc = _cyclic_version("tangled", 20)
    st.schedules[cyc.source_file] = cyc
    return TestClient(create_app(st))


def test_series_chips_name_only_the_analyzable_population(mixed_client: TestClient) -> None:
    """The provenance chip must describe the population the panel actually draws — the
    solvable subset — never the raw loaded list (a chip naming a file that contributes no
    row/point/column misattributes the visual's source)."""
    margin = mixed_client.get("/margin").text
    for title in (
        "Margin &amp; Contingency Burn-Down",
        "Margin Erosion Trend (MET)",
        "Per-version figures",
    ):
        chunk = _panel_titled(margin, title)
        assert "v1→v4" in chunk, (title, "chip must span the 4 SOLVABLE versions, not 5")
        assert "tangled.xml" not in chunk, (title, "the unsolvable file contributes nothing")
    workbench = mixed_client.get("/workbench").text
    wb = _panel_titled(workbench, "Metric Workbench")
    assert "v1→v4" in wb, "workbench chip must match /api/workbench's solvable population"
    assert "tangled.xml" not in wb


def test_target_panel_wears_the_contract(client: TestClient) -> None:
    """The shared session-target focus panel joins the contract on all three render sites
    (/card, /wbs, /analysis): head strip + ⛶ + this file's chip, NO ⤓ (single-activity view;
    no export sheet carries its variance/flag cells). The absent-UID branch stays a bare
    notice. A FRESH client so the module's cached ``pages`` fixture is never target-polluted."""
    c = TestClient(create_app(SessionState()))
    for name in ("Project2.mspdi.xml", "Project5.mspdi.xml"):
        r = c.post("/upload", files={"files": (name, (GOLD / name).read_bytes(), "text/xml")})
        assert r.status_code == 200
    c.post("/target", data={"uid": "143", "next_url": "/"})
    for route in ("/card/Project5", "/wbs/Project5", "/analysis/Project5"):
        page = c.get(route).text
        chunk = _panel_titled(page, "Target activity")
        assert _glyphs(chunk) == {"big"}, (route, "target panel must carry ⛶ and only ⛶")
        assert "prov-chip" in chunk, (route, "target panel must attribute its file")
        assert "data-export" not in chunk, route
    c.post("/target", data={"uid": "999999", "next_url": "/"})
    absent = c.get("/card/Project5").text
    chunk = _panel_titled(absent, "Target activity UID 999999")
    assert "sf-tools" not in chunk, "the absent-UID NOTICE branch stays bare"


def test_groups_preview_pivots_carry_the_preview_file_chip(client: TestClient) -> None:
    """The breakdown and saved-group preview pivots are single-file data visuals whose
    enlarged overlay hides the page's file picker — each must carry the preview file's own
    chip, like the metric-scorecard preview beside them."""
    page = client.get("/groups?breakdown=Activity Type").text
    chunk = _panel_titled(page, "Breakdown by Activity Type")
    assert "prov-chip" in chunk and "SOURCE: Project5" in chunk
    # saved group: the saved-views mini fixture (model-carried group), rendered via the route
    from schedule_forensics.model.saved_view import GroupClause, SavedGroup

    st = SessionState()
    sch = _margin_version("2026-02-27", 40)
    grouped = Schedule(
        name=sch.name,
        source_file=sch.source_file,
        project_start=sch.project_start,
        status_date=sch.status_date,
        tasks=sch.tasks,
        relationships=sch.relationships,
        saved_groups=(
            SavedGroup(
                name="Milestones",
                clauses=(GroupClause(field="Milestone", field_enum="MILESTONE", ascending=True),),
            ),
        ),
    )
    st.schedules[grouped.source_file] = grouped
    c = TestClient(create_app(st))
    page = c.get("/groups", params={"saved_group": "Milestones"}).text
    chunk = _panel_titled(page, "Grouped preview")
    assert "prov-chip" in chunk and "SOURCE: 2026-02-27.mpp" in chunk
