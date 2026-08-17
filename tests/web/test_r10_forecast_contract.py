"""Chapter-09 /forecast (Where it lands) wears the merged panel contract — Ultracode round 10.

What this pins:

* the **five/six panel-head strips** (``.panel-head`` + the UNCHANGED h2 text + a ``.prov-chip``)
  and exactly one ``.sf-take`` per converted panel, with every figure a take quotes proven to be
  a value the page ALREADY renders verbatim (asserted by finding the same token elsewhere in the
  page, OUTSIDE every take — the Carnac cards, the Inputs table, the method cards, the drift
  table's own cells and the rollup's SPI(t) cells);
* the **toolbar vocabulary** — panelkit.js's EXACT strings, and ⤓ EXCEL emitted ONLY where a LIVE
  endpoint serves exactly that panel's data (asserted live, never a dead link):
  ``/export/xlsx/forecast`` on the cards / methods / drift panels, and
  ``/export/xlsx/field-forecast?field=…`` on the field-group panel. The methodology panel and the
  rollup panel deliberately carry NO ⤓ — the ruler also plots the data date and the baseline
  finish (no export column carries them) and ``compute_group_rollup`` has no endpoint at all;
  ▦ DATA is ABSENT everywhere (no panel ships an ``.sf-drawer``: the cards, the two method
  tables, the drift table and the group tables ARE their panels' data — the ``_shell_tools``
  home-shell precedent);
* the **include** — ``panelkit.js`` is a PER-PAGE include and must be present EXACTLY ONCE (two
  ``<script src>`` elements register two delegated listeners, so each click would toggle
  ``.is-big`` twice and net to nothing). Matched as a SUBSTRING: ``_page`` cache-busts static
  URLs to ``?v=<version>``. It is emitted OUTSIDE the drift branch, so a ONE-version session
  gets it too, and NOT on the empty-session guard, where there is no panel for it to drive;
* the **promotion census** — the conversion decorates panels that were already ``.panel``, so the
  panel count per state is pinned and nothing NEW joins jarvis's broad
  ``html[data-theme=jarvis] .panel`` fight;
* this page's own **HAZARD (standing requirement 4) — THE SHARED ``<form>``**. /forecast's only
  page-owned form lives in ``_field_forecast_panel``, and the SAME function renders it on /evm
  with ``action="/evm"``. ONE-CONVENTION LAW moved that form's ``<a class=btn-link>⇩ Excel</a>``
  into the head strip's ⤓ EXCEL rather than shipping two Excel controls, so the form is pinned
  BYTE-EXACT here — method, action, class, ``name=group_field``, the full option list with its
  ``selected`` marker, and the Compute button — in all FOUR states (/forecast, /forecast grouped,
  /evm, /evm grouped). The literals below are the origin/main bytes, and the ONLY permitted
  delta is the removed anchor;
* the **axis-caption freeze (standing requirement 5)** — ``drift.js`` is the only
  ``SFChartFrame.axisTitles`` call site reachable from /forecast and is not touched by this round
  at all; its call block is pinned byte-exact by md5, and ``#driftChart``/``.chart-host`` are
  proven un-moved and un-re-parented.

The real-browser proofs (the script actually loads, a real ⛶ click lands ``.is-big``, a real
⤓ EXCEL click downloads a real workbook, the drift chart still paints its captions, and the
contract classes paint in all four themes) live at the bottom of this module behind the usual
playwright / bundled-chromium skips — markup alone is not evidence (the round-4 lesson)."""

from __future__ import annotations

import hashlib
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
from schedule_forensics.engine.grouping import STANDARD_FIELDS
from schedule_forensics.web.app import SessionState, create_app
from web.browser_chrome import chrome_kwargs

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"
STATIC = Path(__file__).resolve().parents[2] / "src" / "schedule_forensics" / "web" / "static"

#: panelkit.js's exact strings — this page may only ever render these.
EXCEL_LABEL = "⤓ EXCEL"
ENLARGE_LABEL = "⛶ ENLARGE"
SHRINK_LABEL = "⛶ SHRINK"
DATA_LABEL = "▦ DATA"

#: the panel heading TEXT is unchanged by the conversion (the uppercase treatment is CSS), so
#: every existing content assertion keeps holding. Ungrouped 2-version /forecast, in order.
HEADINGS = (
    "Forecast cards &mdash; Commercial Construction",
    "Finish forecast &mdash; Commercial Construction",
    "How the forecasts are computed",
    "Forecast drift across versions",
    "Execution metrics by field group",
)
ROLLUP_HEADING = "Project rollup &mdash; recalculated from the group-weighted data points"

#: the four GLOBAL nav forms every page renders (action only — this module pins the page's OWN
#: form byte-exact and only guards that the global set neither grew nor shrank).
GLOBAL_FORM_ACTIONS = ["/session/wipe", "/target", "/target", "/language"]

#: the field <option> list the golden pair produces — BYTE-EXACT origin/main bytes. Pinning it
#: is what makes the form diff a real byte-diff rather than a re-render of whatever we emit.
#: The form's option list = the engine's own field catalog (ADR-0360 widened it from six
#: standard fields to the full task-level set) + the golden pair's two custom fields. Derived
#: from STANDARD_FIELDS so the pin follows the catalog while the byte-exactness claim — the
#: SAME form on both routes, selected marker included — keeps its full force.
FIELD_OPTIONS = (
    '<option value="">— pick a field —</option>'
    + "".join(f'<option value="{f}">{f}</option>' for f in STANDARD_FIELDS)
    + '<option value="Trace Log">Trace Log</option>'
    + '<option value="Driving Slack">Driving Slack</option>'
)


def _page_form(action: str, group_field: str = "") -> str:
    """The page's OWN form, byte-exact (origin/main bytes minus the one removed anchor)."""
    opts = FIELD_OPTIONS
    if group_field:
        opts = opts.replace(
            f'<option value="{group_field}">', f'<option value="{group_field}" selected>'
        )
    return (
        f"<form method=get action={action} class=viz-controls>\n"
        f"<label>Group by <select name=group_field data-no-i18n>{opts}</select></label>\n"
        "<button type=submit>Compute</button>\n"
        "</form>"
    )


@pytest.fixture
def client() -> TestClient:
    """Project2 + Project5 — the golden pair every /forecast test pins (2 versions ⇒ drift)."""
    c = TestClient(create_app(SessionState()))
    for name in ("Project5", "Project2"):
        data = (GOLDEN / f"{name}.mspdi.xml").read_bytes()
        assert (
            c.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")}).status_code
            == 200
        )
    return c


@pytest.fixture
def one_version() -> TestClient:
    c = TestClient(create_app(SessionState()))
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


def _strip_takes(page: str) -> str:
    return re.sub(r"<p class=sf-take data-no-i18n>.*?</p>", "", page, flags=re.S)


# ── the contract markup ────────────────────────────────────────────────────────────────────


def test_every_converted_panel_wears_head_chip_and_take(client: TestClient) -> None:
    page = client.get("/forecast").text
    for title in HEADINGS:
        assert f"<div class=panel-head><h2>{title}</h2>" in page, title
    # heading TEXT unchanged → the existing content assertions still hold
    assert "Forecast cards" in page and "Carnac" in page
    assert "Finish forecast" in page
    assert "Forecast drift across versions" in page

    assert page.count("<div class=panel-head>") == len(HEADINGS)
    assert page.count("<span class=prov-chip data-no-i18n>") == len(HEADINGS)
    assert len(_takes(page)) == len(HEADINGS)
    # every head / chip / take sits INSIDE a panel chunk, one of each per converted panel
    converted = [p for p in _panels(page) if "<div class=panel-head>" in p]
    assert len(converted) == len(HEADINGS)
    for chunk in converted:
        assert chunk.count("<div class=panel-head>") == 1
        assert chunk.count("<span class=prov-chip data-no-i18n>") == 1
        assert chunk.count("<p class=sf-take data-no-i18n>") == 1
        assert chunk.count("<div class=sf-tools data-noprint=1>") == 1


def test_rollup_panel_wears_the_contract_only_when_grouped(client: TestClient) -> None:
    grouped = client.get("/forecast?group_field=Resource").text
    assert f"<div class=panel-head><h2>{ROLLUP_HEADING}</h2>" in grouped
    assert grouped.count("<div class=panel-head>") == len(HEADINGS) + 1
    assert len(_takes(grouped)) == len(HEADINGS) + 1
    # ADR-0188's guard: the rollup must stay off an ungrouped page, and no take may leak it
    assert "Project rollup" not in client.get("/forecast").text


def test_provenance_chips_name_the_right_source(client: TestClient) -> None:
    page = client.get("/forecast").text
    chips = re.findall(r"<span class=prov-chip data-no-i18n>(.*?)</span>", page)
    # per-version panels chip the LATEST file; the series panels chip first→last
    assert chips.count("SOURCE: Project5.mspdi.xml · DD 2026-08-27") == 3
    assert (
        chips.count(
            "v1→v2 · SOURCE: Project2.mspdi.xml → Project5.mspdi.xml · DD 2026-05-24 → 2026-08-27"
        )
        == 2
    )
    assert len(chips) == len(HEADINGS)


def test_toolbar_is_the_exact_panelkit_vocabulary(client: TestClient) -> None:
    """Only panelkit's strings, and ⤓ EXCEL exactly where a data-export exists."""
    page = client.get("/forecast?group_field=Resource").text
    assert page.count(ENLARGE_LABEL) == len(HEADINGS) + 1  # ⛶ on every converted panel
    assert SHRINK_LABEL not in page  # the flipped label is JS-only, never server-rendered
    assert DATA_LABEL not in page  # no .sf-drawer exists on this page
    assert "sf-drawer" not in page
    # ⤓ EXCEL count == the number of panels carrying a data-export URL (never a dead glyph,
    # never a silent export). 4 = cards + methods + drift + the grouped field panel.
    exports = re.findall(r'<div class=panel data-export="([^"]+)"', page)
    assert page.count(EXCEL_LABEL) == len(exports) == 4
    assert exports.count("/export/xlsx/forecast") == 3
    assert exports.count("/export/xlsx/field-forecast?field=Resource") == 1
    # the two panels that deliberately ship WITHOUT ⤓ (no honest destination exists)
    for chunk in _panels(page):
        if "<h2>How the forecasts are computed</h2>" in chunk or f"<h2>{ROLLUP_HEADING}</h2>" in (
            chunk
        ):
            assert "data-export" not in chunk
            assert EXCEL_LABEL not in chunk
            assert ENLARGE_LABEL in chunk


def test_every_excel_destination_is_a_live_endpoint(client: TestClient) -> None:
    """Rank-3 law: never a dead link. Every ⤓ target answers 200, in both page states."""
    seen: set[str] = set()
    for path in ("/forecast", "/forecast?group_field=Resource", "/evm?group_field=Resource"):
        urls = set(re.findall(r'<div class=panel data-export="([^"]+)"', client.get(path).text))
        assert urls, path
        seen |= urls
    for url in sorted(seen):
        assert client.get(html.unescape(url)).status_code == 200, url
    assert "/export/xlsx/field-forecast?field=Resource" in seen


def test_ungrouped_field_panel_has_no_export_and_no_excel_glyph(client: TestClient) -> None:
    """/export/xlsx/field-forecast REQUIRES a field — an ungrouped ⤓ would be a 422."""
    assert client.get("/export/xlsx/field-forecast").status_code == 422
    assert client.get("/export/xlsx/field-forecast?field=").status_code == 404
    page = client.get("/forecast").text
    chunk = next(c for c in _panels(page) if "<h2>Execution metrics by field group</h2>" in c)
    assert "data-export" not in chunk
    assert EXCEL_LABEL not in chunk
    assert ENLARGE_LABEL in chunk
    assert "field-forecast" not in page  # no dead URL anywhere on the ungrouped page


# ── standing requirement 2: panelkit is a PER-PAGE include ─────────────────────────────────


def test_panelkit_is_included_exactly_once_on_every_populated_state(
    client: TestClient, one_version: TestClient
) -> None:
    """Twice = two delegated listeners = every click toggles .is-big twice (net no-op)."""
    for c, path in (
        (client, "/forecast"),
        (client, "/forecast?group_field=Resource"),
        (one_version, "/forecast"),  # emitted OUTSIDE the drift branch
        (one_version, "/forecast?group_field=Resource"),
    ):
        page = c.get(path).text
        assert page.count("/static/panelkit.js") == 1, path  # substring: _page adds ?v=<ver>
        assert '<script src="/static/panelkit.js' in page, path
        assert page.count(ENLARGE_LABEL) >= 4, path


def test_single_version_gets_panelkit_but_no_drift_markup(one_version: TestClient) -> None:
    page = one_version.get("/forecast").text
    assert "/static/panelkit.js" in page
    # the existing single-version guarantees the include must not have disturbed
    assert "id=driftChart" not in page
    assert "/static/drift.js" not in page
    assert "Forecast drift" not in page
    assert page.count("<div class=panel-head>") == len(HEADINGS) - 1
    assert len(_takes(page)) == len(HEADINGS) - 1


def test_empty_session_emits_no_contract_markup(client: TestClient) -> None:
    c = TestClient(create_app(SessionState()))
    page = c.get("/forecast").text
    assert "Load at least one analyzable schedule" in page
    for token in ("panelkit.js", "panel-head", "sf-tools", "prov-chip", "sf-take", EXCEL_LABEL):
        assert token not in page, token


# ── Law 2: every take figure is ALREADY rendered verbatim on the page ──────────────────────

#: a figure a take may quote: a MM/DD/YYYY date, or a bare number (ints and decimals).
_FIGURE = re.compile(r"\d{2}/\d{2}/\d{4}|\d+(?:\.\d+)?")


def test_every_take_figure_is_already_on_the_page(client: TestClient) -> None:
    """No new arithmetic: each token a take prints must appear elsewhere in the page's OWN
    markup, outside every take — i.e. read from the same variable the visible markup reads."""
    for path in ("/forecast", "/forecast?group_field=Resource"):
        page = client.get(path).text
        rest = _strip_takes(page)
        takes = _takes(page)
        assert takes, path
        n_figs = 0
        for take in takes:
            text = html.unescape(re.sub(r"<[^>]+>", "", take))
            for fig in _FIGURE.findall(text):
                n_figs += 1
                assert fig in rest, (path, fig, text)
        assert n_figs >= 12, (path, n_figs)


def test_takes_quote_the_exact_cells_they_claim(client: TestClient) -> None:
    """The specific provenance of each figure — the cards, the Inputs table, the drift CPM
    column and the rollup SPI(t) cells (the golden pair's pinned values)."""
    page = client.get("/forecast?group_field=Resource").text
    takes = [html.unescape(re.sub(r"<[^>]+>", "", t)) for t in _takes(page)]
    cards, methods, explainer, drift, _fields, rollup = takes

    # V3 — the Carnac cards: "Tasks to complete" and "Latest finish (CPM)"
    assert cards == (
        "99 activities remain to complete, and the schedule logic places the latest "
        "finish on 01/25/2028."
    )
    assert "<div class=stat-value>99</div>" in page  # the card the 99 is read from
    assert "<div class=stat-value>01/25/2028</div>" in page

    # V4 — the Inputs table's own rows
    assert methods == (
        "27 activities are complete and 99 are still to go against a baseline finish of 07/09/2027."
    )
    for label, value in (
        ("Completed activities", "27"),
        ("To-go activities", "99"),
        ("Baseline (planned) finish", "07/09/2027"),
    ):
        assert f"<th scope=col>{label}</th><td>{value}</td>" in page, label

    # V5 — the method cards' own formula lines
    assert explainer == (
        "27 activities are done at 4.62 / month with 99 to go, and SPI(t) reads 0.47 — "
        "the inputs each method below turns into a date."
    )
    assert "(here 27 done at 4.62 / month, 99 to go)." in page
    assert "(here SPI(t) = 0.47)." in page

    # V6 — the drift table's own version labels and CPM column cells (dates only, no delta)
    assert drift == (
        "Across Project2.mspdi.xml to Project5.mspdi.xml the schedule-logic finish reads "
        "08/30/2027 then 01/25/2028."
    )
    assert "<tr><td>Project2.mspdi.xml</td><td>05/24/2026</td><td>08/30/2027</td>" in page
    assert "<tr><td>Project5.mspdi.xml</td><td>08/27/2026</td><td>01/25/2028</td>" in page

    # V7 — the field-group panel renders no aggregate anywhere, so its take quotes NO figure
    assert not _FIGURE.search(takes[4])

    # V8 — the rollup's two SPI(t) cells, verbatim
    assert rollup == "Rolled up from the groups, SPI(t) reads 0.25 against the top-down 0.47."
    assert "<td class=num><b>0.25</b></td>" in page
    assert "<td class=num>0.47</td>" in page


def test_no_number_on_the_page_changed(client: TestClient, one_version: TestClient) -> None:
    """Law 2 as a standing guard: the pinned figures every existing /forecast test asserts are
    still exactly where they were, and the drift table still renders one cell per engine
    method for every loaded version."""
    page = client.get("/forecast").text
    for pinned in ("01/25/2028", "01/26/2028", "06/10/2028", "02/01/2029", "0.47"):
        assert pinned in page, pinned
    drift_rows = re.findall(r"<tr><td>(Project\d\.mspdi\.xml)</td>(.*?)</tr>", page)
    assert len(drift_rows) == 2
    for _name, rest in drift_rows:
        assert rest.count("<td>") == 5  # data date + one cell per engine forecast method
    # ── FIXED BY THE ROUND-10 LEAD (was: present on origin/main and on the round-9 merge-base).
    # The drift table used to declare FIVE <th> while every row emitted SIX cells: the engine
    # ships FOUR forecast methods (cpm, as_scheduled, rate, earned_schedule) and the row loop
    # writes one <td> per method, so "As-scheduled" had no header and every date from "CPM"
    # rightward was read under the WRONG header (the as-scheduled date sat under "Completion
    # rate", the rate under "Earned schedule", the earned-schedule date was unheaded). Measured
    # on the goldens before the fix:
    #   Project5 | 08/27/2026 | 01/25/2028 | 01/26/2028 | 06/10/2028 | 02/01/2029  vs 5 headers.
    # It changed no number — it MISLABELLED four columns on a testimony-facing page. The fix is
    # the one missing <th scope=col>As-scheduled</th>. Asserted STRUCTURALLY below (header count
    # == row cell count) so the pair can never drift apart again if the engine adds a method.
    header = re.search(r"<tr><th scope=col>Version</th>.*?</tr>", page, re.S)
    assert header is not None
    assert "<th scope=col>As-scheduled</th>" in header.group(0)
    assert header.group(0).count("<th") == 6
    for _name, rest in drift_rows:
        assert header.group(0).count("<th") == rest.count("<td>") + 1  # +1: the version <td>
    single = one_version.get("/forecast").text
    assert "SPI(t)" in single and "0.47" in single


# ── standing requirement 4: THIS page's hazard — the SHARED <form>, byte-exact ─────────────


@pytest.mark.parametrize(
    ("path", "action", "group_field"),
    [
        ("/forecast", "/forecast", ""),
        ("/forecast?group_field=Resource", "/forecast", "Resource"),
        ("/evm", "/evm", ""),
        ("/evm?group_field=Resource", "/evm", "Resource"),
    ],
)
def test_the_shared_form_is_byte_exact_in_all_four_states(
    client: TestClient, path: str, action: str, group_field: str
) -> None:
    """The ONE page-own form on /forecast is rendered by the SAME function /evm calls. The
    round's only form edit is the removal of the in-form ``<a class=btn-link>⇩ Excel</a>``
    (rewired into the head strip's ⤓ EXCEL — ONE-CONVENTION LAW); every other byte, incl. the
    option list and its ``selected`` marker, is pinned to the origin/main bytes here."""
    page = client.get(path).text
    forms = re.findall(r"<form\b.*?</form>", page, re.S)
    # the four global nav forms are untouched, and the page owns exactly one more
    assert [re.search(r'action="?([^"\s>]+)', f).group(1) for f in forms[:4]] == (  # type: ignore[union-attr]
        GLOBAL_FORM_ACTIONS
    )
    assert len(forms) == 5, [f[:80] for f in forms]
    assert forms[4] == _page_form(action, group_field)
    # the deleted anchor is gone from the WHOLE page (not merely moved out of the form) — the
    # page-level _export_bar keeps its own ⇩ Excel / ⇩ Word links (page scope, a different
    # affordance the ADR explicitly preserves), so this pins the FIELD-FORECAST anchor only.
    assert 'href="/export/xlsx/field-forecast' not in page
    assert "btn-link" not in forms[4]
    assert "<a " not in forms[4]
    if group_field:
        # ...and its job is now done by the head strip's ⤓ EXCEL, following the panel
        assert f'data-export="/export/xlsx/field-forecast?field={group_field}"' in page
        assert EXCEL_LABEL in page


def test_the_two_routes_render_byte_identical_form_internals(client: TestClient) -> None:
    """The shared panel must stay ONE panel: /evm and /forecast may differ only in the action."""
    f_form = _page_form("/forecast", "Resource")
    e_form = _page_form("/evm", "Resource")
    assert f_form.replace("action=/forecast", "action=") == e_form.replace("action=/evm", "action=")
    assert f_form in client.get("/forecast?group_field=Resource").text
    assert e_form in client.get("/evm?group_field=Resource").text


def test_the_grouped_tables_are_identical_on_both_routes(client: TestClient) -> None:
    """The form edit must not have moved one number in the panel's table, on either route."""

    def table(path: str) -> str:
        page = client.get(path).text
        m = re.search(r"<table class=hist-drill-table>.*?</table>", page, re.S)
        assert m, path
        return m.group(0)

    assert table("/forecast?group_field=Resource") == table("/evm?group_field=Resource")
    assert "<th scope=col>SEI (start)</th>" in table("/forecast?group_field=Resource")


# ── standing requirement 1: the promotion census ───────────────────────────────────────────


@pytest.mark.parametrize(
    ("path", "n_panels"),
    # 2 header status-stacks + the converted content panels + the Ask panel (+ the rollup)
    [("/forecast", 8), ("/forecast?group_field=Resource", 9)],
)
def test_promotion_census_no_element_newly_becomes_a_panel(
    client: TestClient, path: str, n_panels: int
) -> None:
    """Every visual this round decorates was ALREADY a ``.panel``, so nothing new enters
    jarvis's broad ``html[data-theme=jarvis] .panel`` rule (or its corner brackets). The panel
    count per state is pinned: a new ``.panel`` would move it."""
    page = client.get(path).text
    assert len(_panels(page)) == n_panels
    # the two chapter-header composition bars stay CHROME (24 _status_stack call sites across
    # the app and not one wears the contract) — they must not have been contracted here
    for chunk in _panels(page):
        if "status-stack" in chunk[:40]:
            assert "<div class=panel-head>" not in chunk
    assert page.count('<div class="panel status-stack">') == 2
    assert 'class="page-takeaway"' in page  # the header's own takeaway is untouched


# ── standing requirement 5: the axis captions are FROZEN ───────────────────────────────────

#: md5 of ``static/drift.js``'s 3-line SFChartFrame.axisTitles block — the ONE call site
#: reachable from /forecast. Baseline from the round-10 cross-cutting audit §E.1.
#:
#: The block is LOCATED BY CONTENT, not by a hard-coded line offset. It was `lines[132:135]`
#: until ADR-0342 added drift's data-date marker three lines above it: the caption was
#: byte-identical (this same md5 matched at the new offset) but the test failed anyway, because
#: it was pinning the caption's ADDRESS as well as its bytes. A freeze should fail when the
#: frozen thing changes, not when something above it moves. Same md5, same three lines, same
#: assertions — only the way the block is found is now robust.
DRIFT_AXIS_MD5 = "d7cd43e8092e02ef82449a52592578d6"


def test_drift_axis_caption_call_site_is_byte_frozen() -> None:
    lines = (STATIC / "drift.js").read_text(encoding="utf-8").split("\n")
    start = next(i for i, ln in enumerate(lines) if "SFChartFrame.axisTitles(" in ln)
    block = "\n".join(lines[start : start + 3])
    assert "SFChartFrame.axisTitles(" in block
    assert 'xLabel: "Forecast finish date", yLabel: "Forecast method",' in block
    assert hashlib.md5(block.encode()).hexdigest() == DRIFT_AXIS_MD5
    # exactly one call site in the module, and this round adds none
    assert (STATIC / "drift.js").read_text(encoding="utf-8").count("axisTitles(") == 1


def test_the_chart_host_is_not_moved_wrapped_or_re_padded(client: TestClient) -> None:
    """The captions live inside ``#driftChart``; the conversion only adds markup ABOVE it."""
    page = client.get("/forecast").text
    assert "<div id=driftChart class=chart-host></div>" in page
    assert page.count("chart-host") == 1
    assert "/static/drift.js" in page
    for control in ("id=prevDrift", "id=nextDrift", "id=driftPlay", "locked date axis"):
        assert control in page, control
    assert "id=forecastRuler" in page and "chart-legend" in page


# ── standing requirement 3: the loaded-terms gate, with a control ──────────────────────────


def test_new_visible_strings_carry_no_loaded_terms_and_the_gate_fires() -> None:
    """A gate that never fires is unproven — the control runs in the SAME session."""
    assert introduces_loaded_terms("", "deliberate concealed fraud") is True


def test_no_new_string_on_the_page_introduces_a_loaded_term(client: TestClient) -> None:
    page = client.get("/forecast?group_field=Resource").text
    strings: list[str] = [html.unescape(re.sub(r"<[^>]+>", "", t)) for t in _takes(page)]
    strings += [
        html.unescape(t)
        for t in re.findall(r"<span class=prov-chip data-no-i18n>(.*?)</span>", page, re.S)
    ]
    strings += [html.unescape(t) for t in re.findall(r'data-sf-excel title="([^"]*)"', page)]
    strings += [ENLARGE_LABEL, SHRINK_LABEL, EXCEL_LABEL]
    assert len(strings) >= 16, strings
    for s in strings:
        assert introduces_loaded_terms("", " ".join(s.split())) is False, s
    assert introduces_loaded_terms("", "deliberate concealed fraud") is True  # the control


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
        for name in ("Project5", "Project2"):
            data = (GOLDEN / f"{name}.mspdi.xml").read_bytes()
            assert (
                c.post(
                    "/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")}
                ).status_code
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


def test_panelkit_loads_and_a_real_enlarge_click_lands_is_big(served: str) -> None:
    """Standing requirement 2 in real chromium: the script LOADS (once) and the click WORKS on
    every converted panel — the /evm round-4 defect was a complete toolbar that was inert."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page(viewport={"width": 1400, "height": 950})
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        # never networkidle on this app (heartbeat/sysmon poll forever)
        page.goto(served + "/forecast?group_field=Resource", wait_until="load")
        page.wait_for_selector("[data-sf-big]", timeout=15000)
        assert errors == [], errors
        assert (
            page.evaluate(
                "()=>[...document.scripts].filter(s=>s.src.includes('/static/panelkit.js')).length"
            )
            == 1
        )
        n = page.evaluate("()=>document.querySelectorAll('[data-sf-big]').length")
        assert n == 6, n
        for i in range(n):
            btn = page.locator("[data-sf-big]").nth(i)
            assert btn.inner_text() == ENLARGE_LABEL, i
            btn.click()
            assert page.evaluate("()=>document.querySelectorAll('.panel.is-big').length") == 1, i
            assert btn.inner_text() == SHRINK_LABEL, i
            assert btn.get_attribute("aria-pressed") == "true", i
            btn.click()
            assert page.evaluate("()=>document.querySelectorAll('.panel.is-big').length") == 0, i
            assert btn.inner_text() == ENLARGE_LABEL, i
        browser.close()


def test_drift_chart_still_paints_its_frozen_captions(served: str) -> None:
    """Standing requirement 5, measured: the conversion adds markup ABOVE #driftChart, and the
    axis captions inside it are unchanged and still painted. chartframe's own zoom bar (a
    DIFFERENT vocabulary) survives untouched beside the contract's ⛶."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page(viewport={"width": 1400, "height": 950})
        page.goto(served + "/forecast", wait_until="load")
        page.wait_for_selector("#driftChart svg", timeout=15000)
        captions = page.evaluate(
            "()=>[...document.querySelectorAll('#driftChart text')]"
            ".map(t=>t.textContent).filter(t=>/^(Forecast finish date|Forecast method)$/.test(t))"
        )
        assert sorted(captions) == ["Forecast finish date", "Forecast method"], captions
        boxes = page.evaluate(
            "()=>[...document.querySelectorAll('#driftChart text')]"
            ".filter(t=>/^(Forecast finish date|Forecast method)$/.test(t.textContent))"
            ".map(t=>{const b=t.getBoundingClientRect();"
            "return {w:Math.round(b.width),h:Math.round(b.height)};})"
        )
        assert all(b["w"] > 0 and b["h"] > 0 for b in boxes), boxes
        assert page.evaluate("()=>document.querySelectorAll('.cf-frame').length") == 1
        browser.close()


def test_excel_glyph_downloads_a_real_workbook(served: str) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page(viewport={"width": 1400, "height": 950})
        page.goto(served + "/forecast?group_field=Resource", wait_until="load")
        page.wait_for_selector("[data-sf-excel]", timeout=15000)
        assert page.evaluate(
            "()=>[...document.querySelectorAll('.panel[data-export]')]"
            ".map(x=>x.getAttribute('data-export'))"
        ) == [
            "/export/xlsx/forecast",
            "/export/xlsx/forecast",
            "/export/xlsx/forecast",
            "/export/xlsx/field-forecast?field=Resource",
        ]
        with page.expect_download(timeout=20000) as dl:
            page.locator("[data-sf-excel]").last.click()  # the field-group panel's ⤓
        path = dl.value.path()
        assert dl.value.suggested_filename.endswith(".xlsx")
        assert Path(path).read_bytes()[:2] == b"PK"
        browser.close()


def test_four_theme_probe_reads_computed_styles(served: str) -> None:
    """Standing requirement 1: a defined token is not a painting token. Every class this page
    NEWLY applies must render visibly in all four themes — and the ⛶ click must land in each.
    jarvis's broad ``h2`` / ``button`` rules DO out-rank the contract (accent, uppercase, a
    ``// `` prefix, 11px); that is exactly what /evm, /resources, /portfolio and /cei already
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
              chip: g(".prov-chip"), take: g(".sf-take"),
              nTake: document.querySelectorAll(".sf-take").length,
              nChip: document.querySelectorAll(".prov-chip").length,
              nTools: document.querySelectorAll(".sf-tools").length};
    }
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        for theme in ("console", "daylight", "apollo", "jarvis"):
            page = browser.new_page(viewport={"width": 1400, "height": 950})
            page.goto(served + "/forecast", wait_until="load")
            page.evaluate(f"()=>document.documentElement.setAttribute('data-theme','{theme}')")
            page.wait_for_selector("#driftChart svg", timeout=15000)
            r = page.evaluate(probe)
            for name in ("h2", "btn", "chip", "take"):
                el = r[name]
                assert el is not None, f"{theme}: .{name} missing"
                assert el["vis"] == "visible", f"{theme}/{name}: {el}"
                assert el["w"] > 0 and el["h"] > 0, f"{theme}/{name}: {el}"
            assert r["nTake"] == 5 and r["nChip"] == 5 and r["nTools"] == 5, (theme, r)
            # the prov chip is the one class NO theme sheet touches — 8px mono, 9px pill
            assert r["chip"]["fs"] == "8px" and r["chip"]["radius"] == "9px", (theme, r["chip"])
            # each glyph+label stays on ONE line (this page's heads are not mosaic tiles)
            assert r["btn"]["h"] < 24, (theme, r["btn"])
            # the click works in every theme (jarvis's scanline overlay is pointer-events:none)
            btn = page.locator("[data-sf-big]").first
            btn.click()
            assert page.evaluate("()=>document.querySelectorAll('.panel.is-big').length") == 1
            assert btn.inner_text() == SHRINK_LABEL
            page.close()
        browser.close()
