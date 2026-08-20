"""Chapter-08 /resources (Who is overloaded) wears the merged panel contract — Ultracode round 10.

What this pins:

* the **panel-head strips** — four since operator 2026-08-20 (``.panel-head`` + h2 + a
  ``.prov-chip``)
  and exactly one ``.sf-take`` per converted panel, with every figure a take quotes proven to
  be a value the page ALREADY renders verbatim (asserted by finding the same token in the KPI
  cards / the roster's own row-1 cells / the ``<option>`` list, outside the take itself);
* the **toolbar vocabulary** — panelkit.js's EXACT strings, ⤓ EXCEL pointing at the EXISTING
  ``/export/xlsx/resources`` endpoint (asserted **live**, never a dead link) and carrying the
  RENDERED bucket (a week view must never hand back the month workbook — capacity scales with
  the working days in a bucket, so the wrong bucket is a presentation lie about engine numbers);
  ▦ DATA deliberately ABSENT (no panel ships an ``.sf-drawer``; the roster table and the KPI
  grid ARE their panels' data — the ``_shell_tools`` home-shell precedent);
* the **include** — ``panelkit.js`` is a PER-PAGE include and must be present EXACTLY ONCE (two
  ``<script src>`` elements register two delegated listeners, so each click would toggle
  ``.is-big`` twice and net to nothing). Matched as a SUBSTRING: ``_page`` cache-busts static
  URLs to ``?v=<version>``. It must NOT appear on either empty-state branch, where there is no
  panel for it to drive and ⤓ EXCEL would 422;
* the **promotion census** — the conversion decorates panels that were already ``.panel``, so
  the ``.panel`` count is unchanged and nothing NEW joins jarvis's broad
  ``html[data-theme=jarvis] .panel`` fight;
* this page's own **HAZARD (standing requirement 4)** — /resources carries BOTH page-own
  hazards at once: an embedded ``<script type="application/json" id=resData>`` payload and a
  GET ``<form>`` bucket selector. The payload is asserted BYTE-IDENTICAL to what the engine
  helper produces (a true byte-diff against the source of truth, not a re-parse), with no raw
  ``<`` surviving, at all three buckets; every ``<form>`` on the page is pinned byte-exact at
  all three buckets;
* the **first-paint regression this round fixes** — ``resources.js`` calls ``draw()``
  synchronously and ``draw()`` calls ``SFChartFrame.axisTitles``, but ``chartframe.js`` is
  emitted by ``_LAYOUT`` AFTER ``<main>``. Without ``defer`` the page threw
  ``SFChartFrame is not defined`` and rendered NO histogram until the operator touched the
  picker. The ``defer`` attribute is pinned here and proven in real chromium below;
* the **axis-caption freeze (standing requirement 5)** — ``resources.js`` is not touched by this
  round at all; its single ``SFChartFrame.axisTitles`` call site is pinned byte-exact.

The real-browser proofs (the script actually loads, a real ⛶ click lands ``.is-big``, a real
⤓ EXCEL click downloads a real workbook, the histogram paints on FIRST load, and the contract
classes paint in all four themes) live at the bottom of this module behind the usual
playwright / bundled-chromium skips — markup alone is not evidence (the round-4 lesson)."""

from __future__ import annotations

import hashlib
import html
import json
import re
import socket
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.ai.citations import introduces_loaded_terms
from schedule_forensics.web.app import SessionState, create_app
from web.browser_chrome import chrome_kwargs

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"

#: panelkit.js's exact strings — this page may only ever render these.
EXCEL_LABEL = "⤓ EXCEL"
ENLARGE_LABEL = "⛶ ENLARGE"
DATA_LABEL = "▦ DATA"

BUCKETS = ("day", "week", "month")


#: the ONE page-own form on /resources, BYTE-EXACT per bucket (the bucket selector is a plain
#: GET so the server recomputes capacity at the chosen granularity — the panel conversion must
#: not have moved one character of it, incl. the ``selected`` marker and data-sf-autosubmit).
def _bucket_form(bucket: str) -> str:
    opts = "".join(
        f'<option value="{g}"{" selected" if g == bucket else ""}>{g.title()}</option>'
        for g in BUCKETS
    )
    return (
        '<form method=get action=/resources class=viz-controls style="display:inline-flex">'
        "<label>Bucket <select name=bucket data-no-i18n data-sf-autosubmit "
        f'title="Time-bucket the histogram by day, week or month">{opts}</select></label>'
        "</form>"
    )


#: the four GLOBAL nav forms every page renders (action + method only — this module pins the
#: page's OWN form byte-exact and only guards that the global set neither grew nor shrank).
GLOBAL_FORM_ACTIONS = ["/session/wipe", "/target", "/target", "/language"]


@pytest.fixture
def state() -> SessionState:
    return SessionState()


@pytest.fixture
def client(state: SessionState) -> TestClient:
    """Project5 — resource-loaded (32 resources / 164 assignments), the same fixture
    ``test_resources_view.py`` pins."""
    c = TestClient(create_app(state))
    data = (GOLDEN / "Project5.mspdi.xml").read_bytes()
    assert (
        c.post("/upload", files={"files": ("Project5.mspdi.xml", data, "text/xml")}).status_code
        == 200
    )
    return c


#: a panel OPEN tag — ``class=panel`` / ``class="panel …"``, but never ``class=panel-head``
#: (the negative lookahead is load-bearing: the head strip's own div would otherwise split a
#: panel in half and silently weaken every ordering assertion below).
_PANEL_OPEN = re.compile(r'<div class="?panel(?![-\w])')


def _panels(page: str) -> list[str]:
    """The page split into its panel chunks (sufficient here: this page never nests a panel)."""
    return _PANEL_OPEN.split(page)[1:]


def _takes(page: str) -> list[str]:
    return re.findall(r"<p class=sf-take data-no-i18n>(.*?)</p>", page, re.S)


# ── the conversion itself ──────────────────────────────────────────────────────────────────


def test_the_four_content_panels_wear_head_tools_prov_and_take(client: TestClient) -> None:
    # DELIBERATE re-baseline (operator 2026-08-20): the page gained a FOURTH shelled panel —
    # "Utilization by resource", the whole-roster peak-load view — so every 3-count moves to 4.
    page = client.get("/resources").text
    # the four headings keep their EXACT text (content assertions elsewhere depend on it)
    for title in (
        "Resource loading &amp; over-allocation",
        "Loading histogram",
        "Resource roster",
        "Utilization by resource",
    ):
        assert f"<h2>{title}" in page, title
    assert page.count("<div class=panel-head>") == 4
    assert page.count("<div class=sf-tools data-noprint=1>") == 4
    assert page.count("<span class=prov-chip data-no-i18n>") == 4
    assert len(_takes(page)) == 4
    # the chip names the file the panels are drawn from, and its data date
    assert "SOURCE: Project5.mspdi.xml · DD " in page
    # each converted panel carries head + take + prov, in that order, inside the SAME panel
    converted = [p for p in _panels(page) if "panel-head" in p]
    assert len(converted) == 4
    for p in converted:
        assert p.index("panel-head") < p.index("sf-take")
        assert "prov-chip" in p and "sf-tools" in p


def test_the_glyph_strip_is_exactly_the_real_ones(client: TestClient) -> None:
    """▦ DATA is deliberately absent: no panel ships an ``.sf-drawer``, so the glyph would be
    inert (panelkit.js returns silently). The roster table and the KPI grid ARE the data."""
    page = client.get("/resources").text
    assert page.count(EXCEL_LABEL) == 4
    assert page.count(ENLARGE_LABEL) == 4
    assert DATA_LABEL not in page
    assert "data-sf-data" not in page
    assert "sf-drawer" not in page
    # ⛶ is panel-scoped, and that is coherent: at most ONE chart lives in a converted panel
    # (the utilization panel renders plain rows — deliberately NOT a .chart-host, so
    # chartframe never bolts a zoom bar onto a div list)
    assert page.count("class=chart-host") == 1
    assert page.count("data-sf-big") == 4


@pytest.mark.parametrize("bucket", BUCKETS)
def test_excel_carries_the_rendered_bucket_and_is_a_live_endpoint(
    client: TestClient, bucket: str
) -> None:
    """Capacity scales with the working days in a bucket, so a week view handing back the
    month workbook would be a presentation lie about engine numbers."""
    page = client.get(f"/resources?bucket={bucket}").text
    urls = re.findall(r'<div class=panel data-export="([^"]+)"', page)
    assert urls == [f"/export/xlsx/resources?bucket={bucket}"] * 4, urls
    live = client.get(urls[0])
    assert live.status_code == 200
    assert live.content[:2] == b"PK", "not a real .xlsx"
    # and the hover text names the bucket actually on screen
    assert f"roster at the {bucket} bucket" in page


def test_panelkit_is_included_exactly_once(client: TestClient) -> None:
    """Two <script src> elements would register two delegated listeners, so every click would
    toggle .is-big twice (net no-op + a double label flip). Substring: _page cache-busts."""
    page = client.get("/resources").text
    assert page.count("/static/panelkit.js") == 1


def test_guard_branches_emit_no_panelkit_markup(client: TestClient) -> None:
    """Neither empty state may wear the toolbar: there is no panel for ⛶ to enlarge and
    ⤓ EXCEL would 422."""
    empty = TestClient(create_app(SessionState()))
    page = empty.get("/resources").text
    assert "Load a resource-loaded schedule" in page  # the pinned guard string
    for token in ("/static/panelkit.js", EXCEL_LABEL, ENLARGE_LABEL, "panel-head", "sf-take"):
        assert token not in page, token
    assert empty.get("/export/xlsx/resources").status_code == 422


def test_promotion_census_no_new_panel_joins_the_theme_fight(client: TestClient) -> None:
    """Standing requirement 1: an element that GAINS .panel joins hud.css's broad
    ``html[data-theme=jarvis] .panel`` rules (incl. the two 16px corner brackets). This
    conversion decorates panels that were ALREADY .panel — the count must not move."""
    page = client.get("/resources").text
    # 2 status-stack + 4 content + explainer + Ask the AI (measured identical in chromium;
    # the 4th content panel is the 2026-08-20 utilization view)
    assert len(_PANEL_OPEN.findall(page)) == 8
    # the contract classes appear ONLY inside panels
    assert page.count("panel-head") == 4


# ── Law 2: every quoted figure is already on the page ──────────────────────────────────────


@pytest.mark.parametrize("bucket", BUCKETS)
def test_takes_quote_only_figures_the_page_already_renders(client: TestClient, bucket: str) -> None:
    """No new arithmetic may enter the web layer. Every numeric token in every take must
    already appear in the page's OWN markup outside the takes — the KPI cards for the totals,
    roster ROW 1 for the per-resource figures."""
    page = client.get(f"/resources?bucket={bucket}").text
    takes = _takes(page)
    assert len(takes) == 4
    rest = page
    for t in takes:
        rest = rest.replace(t, "")
    for t in takes:
        for tok in re.findall(r"\d+(?:\.\d+)?", html.unescape(t)):
            assert tok in rest, f"take figure {tok!r} is not rendered anywhere else: {t!r}"


def test_takes_quote_the_roster_row_the_chart_actually_opens_on(client: TestClient) -> None:
    """resources.js's ``selected()`` falls back to ``payload.resources[0]`` and the first
    ``<option>`` carries no ``selected``, so the chart opens on roster ROW 1 — which is what
    the histogram/roster takes name. Proven against the embedded payload, not re-derived."""
    page = client.get("/resources").text
    blob = page.split("id=resData>", 1)[1].split("</script>", 1)[0].replace("<\\/", "</")
    first = json.loads(blob)["resources"][0]
    name = html.escape(first["name"])
    hist, roster = _takes(page)[1], _takes(page)[2]  # util is [3] (rendered last)
    assert f"opens on {name} " in hist, hist
    assert f"largest first: {name} at " in roster, roster
    # the work-days figure is the roster row-1 cell, formatted identically
    days = f"{first['total_days']:g}"
    assert f"{days} work-days" in hist and f"{days} work-days" in roster
    # …and that cell really is printed in the roster table
    assert f"<td class=num>{days}</td>" in page


def test_takes_read_as_prose_when_nothing_is_over_allocated(
    client: TestClient, state: SessionState, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The zero-over-allocation branch must read as prose, never as a bare ``0`` — and it must
    still quote only figures the page renders. Driven by substituting the ENGINE RESULT (the
    engine itself is never touched): ``web/resources.py`` is the module whose code calls the
    helper (ADR-0379 moved the family out of app.py; patching app.py would no longer reach the
    page's own call — the ADR-0297 phase-1 trap)."""
    from schedule_forensics.engine.resources import (
        ResourceLoad,
        ResourceLoading,
        ResourcePeriod,
    )
    from schedule_forensics.web import resources as res_mod

    clean = ResourceLoading(
        periods=("2025-01", "2025-02"),
        resources=(
            ResourceLoad(
                resource_id=1,
                name="Crew A",
                type="work",
                max_units=1.0,
                total_work_minutes=960.0,
                task_count=2,
                peak_load_minutes=480.0,
                peak_period="2025-01",
                over_allocated_periods=(),
                series=(ResourcePeriod("2025-01", 480.0, 9600.0),),
            ),
        ),
        has_work=True,
        working_minutes_per_day=480,
    )
    monkeypatch.setattr(res_mod, "compute_resource_loading", lambda *a, **k: clean)
    page = client.get("/resources").text
    takes = _takes(page)
    assert len(takes) == 4
    for t in takes:
        assert (
            "none is over-allocated in any month" in t
            or "opens on Crew A" in t
            # the 2026-08-20 utilization panel's take is figure-free prose by design
            or "peak utilization against its OWN max units" in t
        )
    assert "0 of them are over-allocated" not in page
    # Law 2 still holds on this branch: every quoted figure is rendered elsewhere too
    rest = page
    for t in takes:
        rest = rest.replace(t, "")
    for t in takes:
        for tok in re.findall(r"\d+(?:\.\d+)?", html.unescape(t)):
            assert tok in rest, (tok, t)


# ── standing requirement 4: this page's own hazards ────────────────────────────────────────


@pytest.mark.parametrize("bucket", BUCKETS)
def test_embedded_json_payload_is_byte_identical_to_the_engine_helper(
    client: TestClient, state: SessionState, bucket: str
) -> None:
    """The CSP-safe ``<script type="application/json" id=resData>`` blob is the page's most
    fragile surface: resources.js splits on it and every drill row comes out of it. Assert the
    embedded bytes are EXACTLY what the helper emits from the same engine call — a real
    byte-diff against the source of truth, not a re-parse that could hide a rewrite."""
    from schedule_forensics.engine.resources import compute_resource_loading
    from schedule_forensics.web.app import _latest_solvable, _resource_loading_json

    page = client.get(f"/resources?bucket={bucket}").text
    embedded = page.split("id=resData>", 1)[1].split("</script>", 1)[0]

    chosen = _latest_solvable(state)
    assert chosen is not None
    _key, sch, cpm = chosen
    expected = _resource_loading_json(compute_resource_loading(sch, cpm, bucket), sch)

    assert (
        hashlib.md5(embedded.encode()).hexdigest() == hashlib.md5(expected.encode()).hexdigest()
    ), "the panel conversion changed the embedded payload"
    assert embedded == expected
    assert "<" not in embedded, "a raw '<' would break out of the JSON script block"
    payload = json.loads(embedded.replace("<\\/", "</"))
    assert payload["granularity"] == bucket
    assert payload["resources"], "the golden file is resource-loaded"


@pytest.mark.parametrize("bucket", BUCKETS)
def test_every_form_survives_byte_exact(client: TestClient, bucket: str) -> None:
    """The bucket selector is a GET side-effect-free control; the four nav forms are global.
    A toolbar change must not add, remove or reshape one of them."""
    page = client.get(f"/resources?bucket={bucket}").text
    forms = re.findall(r"<form[^>]*>.*?</form>", page, re.S)
    assert len(forms) == 5, [f[:60] for f in forms]
    actions = [re.search(r'action="?([^"\s>]+)', f).group(1) for f in forms]  # type: ignore[union-attr]
    assert actions == [*GLOBAL_FORM_ACTIONS, "/resources"]
    assert forms[-1] == _bucket_form(bucket), forms[-1]


def test_get_resources_never_mutates_the_session(client: TestClient) -> None:
    """The bucket form is a GET — rendering any bucket must leave the session untouched."""
    before = client.get("/resources").text
    for b in BUCKETS:
        client.get(f"/resources?bucket={b}")
    assert client.get("/resources").text == before


def test_every_id_resources_js_reads_survives(client: TestClient) -> None:
    page = client.get("/resources").text
    for el_id in ("resData", "resPick", "resChart", "resStatus", "resDrill"):
        assert f"id={el_id}" in page, el_id
    assert "name=bucket" in page


# ── the first-paint regression this round fixes ────────────────────────────────────────────


def test_resources_js_is_deferred_so_chartframe_exists_first(client: TestClient) -> None:
    """resources.js calls ``draw()`` synchronously and ``draw()`` calls
    ``SFChartFrame.axisTitles``, but ``chartframe.js`` is emitted by ``_LAYOUT`` AFTER
    ``<main>``. Without ``defer`` the page threw ``SFChartFrame is not defined`` and rendered
    NO histogram until the operator touched the picker (measured in chromium)."""
    page = client.get("/resources").text
    assert re.search(r'<script defer src="/static/resources\.js', page), (
        "resources.js must be deferred — see the module docstring"
    )
    # the layout really does load chartframe.js after <main>, which is WHY defer is required
    assert page.index("</main>") < page.index("/static/chartframe.js")


def test_axis_caption_call_site_is_untouched() -> None:
    """Standing requirement 5: the captions are finished. Round 10 touched no byte of
    resources.js; ADR-0319 later added the measured caption-yield BELOW the call site (the
    rotated period labels yield to the caption's live box — the caption never moves), so the
    whole-file digest was refreshed deliberately there. The LOAD-BEARING pins are unchanged:
    the call-site block digest and the two caption strings prove the axisTitles call itself
    is byte-identical.

    ADR-0342 did the same thing again, and for the same reason: it added the data-date marker
    (``SFGantt.dataDateLine``) immediately BELOW the call site, so the whole-file digest is
    refreshed here deliberately while the two load-bearing pins below are unchanged — verified,
    not assumed: the 11-line call-site block still hashes to the SAME
    ``6cd4b080306f47e19d71d1e8f18d8838`` it did before the change."""
    js = Path(__file__).resolve().parents[2] / "src/schedule_forensics/web/static/resources.js"
    raw = js.read_bytes()
    # operator 2026-08-20: drawUtil() (the whole-roster utilization panel) is appended
    # BELOW the pinned call-site block — same shape as the ADR-0319/0342 refreshes: the
    # whole-file digest moves deliberately, the 11-line call-site block digest must not.
    assert hashlib.md5(raw).hexdigest() == "e82a355573220b73587d4448fb281401"
    block = raw.decode().splitlines()[235:246]
    assert hashlib.md5("\n".join(block).encode()).hexdigest() == "6cd4b080306f47e19d71d1e8f18d8838"
    assert 'xLabel: "Period (" + UNIT + " commencing)",' in "\n".join(block)
    assert 'yLabel: "Work booked (working days)",' in "\n".join(block)


# ── standing requirement 3: the loaded-terms gate, with a control ──────────────────────────


def test_control_proves_the_loaded_terms_gate_can_fail() -> None:
    """A gate that never fires is unproven."""
    assert introduces_loaded_terms("", "deliberate concealed fraud") is True


@pytest.mark.parametrize("bucket", BUCKETS)
def test_resources_presentation_prose_introduces_no_loaded_terms(
    client: TestClient, bucket: str
) -> None:
    page = client.get(f"/resources?bucket={bucket}").text
    strings: list[str] = []
    strings += [html.unescape(t) for t in _takes(page)]
    strings += [html.unescape(t) for t in re.findall(r'<p class="page-lede">(.*?)</p>', page, re.S)]
    strings += [
        html.unescape(t)
        for t in re.findall(r"<span class=prov-chip data-no-i18n>(.*?)</span>", page, re.S)
    ]
    strings += [html.unescape(t) for t in re.findall(r'data-sf-excel title="([^"]*)"', page)]
    assert len(strings) >= 8, strings
    for s in strings:
        assert introduces_loaded_terms("", " ".join(s.split())) is False, s


# ── the real-browser proofs (markup alone is not evidence) ─────────────────────────────────

# Chromium resolution is `tests/web/browser_chrome.py`'s single decision (ADR-0406, widened
# by ADR-0418): prefer a vendored binary, else let playwright resolve its own — the branch a
# CI runner takes. This module used to pin `/opt/pw-browsers` and therefore SKIPPED on CI.


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
        data = (GOLDEN / "Project5.mspdi.xml").read_bytes()
        assert (
            c.post("/upload", files={"files": ("Project5.mspdi.xml", data, "text/xml")}).status_code
            == 200
        )
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(150):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


def test_histogram_paints_on_first_load_and_panelkit_drives_the_strip(served: str) -> None:
    """The round's real regression fix + standing requirement 2, in real chromium."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page(viewport={"width": 1400, "height": 950})
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        # never networkidle on this app (heartbeat/sysmon poll forever)
        page.goto(served + "/resources", wait_until="load")
        page.wait_for_selector("#resChart svg.res-svg", timeout=15000)

        assert errors == [], errors  # was ['SFChartFrame is not defined'] before the defer fix
        assert page.evaluate("()=>document.querySelectorAll('svg.res-svg').length") == 1
        captions = page.evaluate(
            "()=>[...document.querySelectorAll('#resChart text')]"
            ".map(t=>t.textContent).filter(t=>/^(Period|Work booked)/.test(t))"
        )
        assert captions == ["Period (month commencing)", "Work booked (working days)"], captions
        # chartframe's own zoom bar is a DIFFERENT vocabulary and must survive untouched
        assert page.evaluate("()=>document.querySelectorAll('.cf-frame').length") == 1
        assert page.evaluate(
            "()=>[...document.querySelectorAll('.cf-frame button')].map(x=>x.textContent.trim())"
        ) == ["\u2922", "\u2212", "\uff0b", "Reset"]  # chartframe's zoom bar, verbatim

        # panelkit.js genuinely loads here (cache-busted src → substring), exactly once
        assert (
            page.evaluate(
                "()=>[...document.scripts].filter(s=>s.src.includes('/static/panelkit.js')).length"
            )
            == 1
        )

        # ONE real click on the histogram panel's ⛶, read .is-big back off the panel
        btn = page.locator(".panel[data-export] [data-sf-big]").nth(1)
        assert btn.inner_text() == ENLARGE_LABEL
        btn.click()
        assert page.evaluate("()=>document.querySelectorAll('.panel.is-big').length") == 1
        assert btn.inner_text() == "⛶ SHRINK"
        assert btn.get_attribute("aria-pressed") == "true"
        assert page.evaluate("()=>document.querySelectorAll('svg.res-svg').length") == 1
        btn.click()
        assert page.evaluate("()=>document.querySelectorAll('.panel.is-big').length") == 0
        assert btn.inner_text() == ENLARGE_LABEL
        browser.close()


def test_excel_glyph_downloads_the_rendered_buckets_workbook(served: str) -> None:
    """⤓ EXCEL must produce a REAL workbook for the bucket on screen."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page(viewport={"width": 1400, "height": 950})
        page.goto(served + "/resources?bucket=week", wait_until="load")
        page.wait_for_selector("[data-sf-excel]", timeout=15000)
        assert (
            page.evaluate(
                "()=>[...document.querySelectorAll('.panel[data-export]')]"
                ".map(x=>x.getAttribute('data-export'))"
            )
            == ["/export/xlsx/resources?bucket=week"] * 4
        )
        with page.expect_download(timeout=20000) as dl:
            page.locator("[data-sf-excel]").nth(2).click()
        path = dl.value.path()
        assert dl.value.suggested_filename.endswith(".xlsx")
        assert Path(path).read_bytes()[:2] == b"PK"
        browser.close()


def test_four_theme_probe_reads_computed_styles(served: str) -> None:
    """Standing requirement 1: a defined token is not a painting token. Every class this page
    NEWLY applies must render visibly in all four themes — and the ⛶ click must land in each.
    jarvis's broad ``h2`` / ``button`` rules DO out-rank the contract (accent, uppercase, a
    ``// `` prefix, 11px); that is exactly what /scurve, /evm, /portfolio and /cei already
    ship on main, so it is the shipped convention and is asserted as such, not "fixed"."""
    from playwright.sync_api import sync_playwright

    probe = """
    () => {
      const g = (sel) => {
        const el = document.querySelector(sel);
        if (!el) return null;
        const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
        return {w: Math.round(r.width), h: Math.round(r.height), vis: cs.visibility,
                fs: cs.fontSize, color: cs.color, radius: cs.borderTopLeftRadius};
      };
      return {h2: g(".panel-head h2"), btn: g(".sf-tools button"),
              chip: g(".prov-chip"), take: g(".sf-take"), lede: g(".page-lede"),
              nTake: document.querySelectorAll(".sf-take").length,
              nChip: document.querySelectorAll(".prov-chip").length};
    }
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        for theme in ("console", "daylight", "apollo", "jarvis"):
            page = browser.new_page(viewport={"width": 1400, "height": 950})
            page.goto(served + "/resources", wait_until="load")
            page.evaluate(f"()=>document.documentElement.setAttribute('data-theme','{theme}')")
            page.wait_for_selector("#resChart svg.res-svg", timeout=15000)
            r = page.evaluate(probe)
            for name in ("h2", "btn", "chip", "take", "lede"):
                el = r[name]
                assert el is not None, f"{theme}: .{name} missing"
                assert el["vis"] == "visible", f"{theme}/{name}: {el}"
                assert el["w"] > 0 and el["h"] > 0, f"{theme}/{name}: {el}"
            assert r["nTake"] == 4 and r["nChip"] == 4, (theme, r)
            # the prov chip is the one class NO theme sheet touches — 8px mono, 9px pill
            assert r["chip"]["fs"] == "8px" and r["chip"]["radius"] == "9px", (theme, r["chip"])
            # each glyph+label stays on ONE line (no /performance-style two-line wrap here)
            assert r["btn"]["h"] < 24, (theme, r["btn"])
            # the click works in every theme (jarvis's scanline overlay is pointer-events:none)
            btn = page.locator(".panel[data-export] [data-sf-big]").nth(1)
            btn.click()
            assert page.evaluate("()=>document.querySelectorAll('.panel.is-big').length") == 1
            assert btn.inner_text() == "⛶ SHRINK"
            page.close()
        browser.close()
