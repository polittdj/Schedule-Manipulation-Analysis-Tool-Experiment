"""/wbs wears the Claude Design "Library WBS Rollup" layout (ADR-0471), functionality unchanged —
the eighth page on the design.

The artboard (the v2 canvas's ``section[data-screen-label="Library WBS Rollup"]``, this time
EXECUTED over loopback HTTP in all four themes — ADR-0464's recipe with ``setScreen('wr')``):
kicker · headline ("Completion and earned schedule, pivoted by WBS.") · lede · ONE card whose head
line carries the project, the group/activity/percent counts, a "WBS FIELD" picker and ⤓ EXCEL ·
a seven-column table · a footnote · a "Segment Forecast →" footer. The page already IS that card,
in two verbatim panels (the completion pivot and the SPI(t)/Earned-Schedule pivot — the export's
two sheets); what the layout changes is the ORDER (the masthead leads, as on every page of the
family, where the pristine page put the Field-roles picker ABOVE its own takeaway) and, for a
per-file drill, the family's cursor strip as NAVIGATION (ADR-0470's rule): one LINK chip per
loaded version of the active project, the open version on, the ``vN · file · DD`` pill, served
only with two or more versions. The picker takes the family's options position, between the strip
and the card, byte-for-byte. Named omissions (ADR-0471): the mock's row click (the SPI bar drill
already opens the group; ``wbs.js`` is byte-frozen and the drill floor is a census pin — priced),
its %-complete bars and SPI(t) colour (an encoding inside a verbatim table, not a layout move),
its footnote (the ES panel's read-me line says it with the page's COUNT basis; the mock's
"duration-weighted" / "planned-to-date" wording contradicts the engine and "nothing leaves this
machine" is never a static sentence — ADR-0396), and the Continue footer (the chrome's spine).

Red-first (2026-09-07): the pristine page served no strip, no chips, no pill, and its takeaway
BELOW the picker.
"""

from __future__ import annotations

import datetime as dt
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.importers import to_json_text
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import SessionState, create_app
from web.test_ui_control_effect_census import _FAMILY

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"
CHIP = re.compile(r'<a class="cd-chip( on)?" data-idx="(\d+)" href="([^"]+)"[^>]*>v(\d+)</a>')
PILL = re.compile(r'<span class="muted cd-pill" data-no-i18n>([^<]+)</span>')

#: the design's order on the served page: masthead · strip · the picker · the two pivots · script
ORDER = (
    '<h1 class="page-takeaway"',
    "id=wbsCursor",
    'action="/fields/roles"',
    "Completion metrics by WBS",
    "SPI(t) &amp; Earned Schedule by WBS",
    "/static/wbs.js",
)


def _panels(page: str) -> int:
    """Elements carrying the `panel` CLASS — the promotion census the r12 sweep pins (4 here)."""

    class Count(HTMLParser):
        n = 0

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if "panel" in (dict(attrs).get("class") or "").split():
                self.n += 1

    parser = Count()
    parser.feed(page)
    return parser.n


def _client(*names: str) -> TestClient:
    client = TestClient(create_app(SessionState()))
    for name in names:
        data = (GOLDEN / f"{name}.mspdi.xml").read_bytes()
        resp = client.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")})
        assert resp.status_code == 200
    return client


@pytest.fixture(scope="module")
def pair() -> TestClient:
    return _client("Project2", "Project5")


def test_the_cursor_strip_serves_one_link_chip_per_version_with_the_open_one_on(
    pair: TestClient,
) -> None:
    page = pair.get("/wbs/Project5").text
    assert page.count("id=wbsCursor") == 1
    chips = CHIP.findall(page)
    assert [(idx, href, lab) for _on, idx, href, lab in chips] == [
        ("0", "/wbs/Project2", "1"),
        ("1", "/wbs/Project5", "2"),
    ]
    assert [on for on, *_rest in chips] == ["", " on"]  # oldest first; the open version on
    pill = PILL.search(page)
    assert pill and pill.group(1).startswith("v2 &middot; Project5.mspdi.xml &middot; DD ")


def test_a_chip_opens_that_versions_rollup_with_its_own_chip_on(pair: TestClient) -> None:
    page = pair.get("/wbs/Project2").text
    chips = CHIP.findall(page)
    assert [on for on, *_rest in chips] == [" on", ""]
    pill = PILL.search(page)
    assert pill and pill.group(1).startswith("v1 &middot; Project2.mspdi.xml")


def test_one_loaded_version_serves_no_strip() -> None:
    page = _client("Project5").get("/wbs/Project5").text
    assert "id=wbsCursor" not in page and "cd-chip" not in page


def test_chips_carry_no_id_and_no_family_word(pair: TestClient) -> None:
    page = pair.get("/wbs/Project5").text
    tags = re.findall(r"<a class=\"cd-chip[^>]*>", page)
    assert len(tags) == 2
    for tag in tags:
        assert " id=" not in tag and not re.search(_FAMILY, tag)
    strip = re.search(r'<div class="viz-controls cd-cursor" id=(\w+)>(.*?)</div>', page, re.S)
    assert strip and not re.search(_FAMILY, strip.group(1))  # the strip's own id is no stepper
    # the census recognises a family by id + className, so every class/id VALUE inside the strip
    # is what must stay clean (the raw markup cannot be: `<span` itself matches `pan(?!d)`)
    values = re.findall(r'(?:class|id)="?([^" >]+)"?', strip.group(2))
    assert values and not any(re.search(_FAMILY, v) for v in values), values


def test_the_masthead_leads_then_the_strip_the_picker_and_the_two_pivots(
    pair: TestClient,
) -> None:
    page = pair.get("/wbs/Project5").text
    missing = [mark for mark in ORDER if mark not in page]
    assert not missing, missing
    positions = [page.index(mark) for mark in ORDER]
    assert positions == sorted(positions), list(zip(ORDER, positions, strict=True))


def test_every_panel_figure_picker_and_export_survives_the_layout(pair: TestClient) -> None:
    page = pair.get("/wbs/Project5").text
    assert _panels(page) == 4  # Field roles · the completion pivot · the ES pivot · the Ask panel
    for text in (
        "Completion metrics by WBS &mdash; 22 groups",
        "SPI(t) &amp; Earned Schedule by WBS",
        "<th scope=col>Dur avg</th>",
        "<th scope=col>Earned schedule (wd)</th>",
        "id=wbsChart",
        "<select name=wbs data-no-i18n>",
        "(stored WBS column)",
    ):
        assert text in page, text
    assert page.count('data-export="/export/xlsx/wbs/Project5"') == 2  # ⤓ on both pivots (r12)
    assert page.count("/static/panelkit.js") == 1  # the r11 include, once, gated on a control
    assert page.count("<table class=wbs-table>") == 2


def test_the_no_groups_branch_keeps_the_picker_above_the_notice_and_wears_no_strip() -> None:
    template = Schedule(
        name="template",
        project_start=dt.datetime(2024, 1, 1, 8, 0),
        tasks=(Task(unique_id=0, name="Root", duration_minutes=0, is_summary=True),),
    )
    client = TestClient(create_app(SessionState()))
    files = {"files": ("template.json", to_json_text(template).encode(), "application/json")}
    assert client.post("/upload", files=files).status_code == 200
    page = client.get("/wbs/template").text
    notice = "no schedulable activities to break down by WBS"
    assert notice in page and 'action="/fields/roles"' in page
    assert page.index('action="/fields/roles"') < page.index(notice)  # the picker still leads
    assert "id=wbsCursor" not in page and "cd-chip" not in page
    assert _panels(page) == 3  # Field roles · the bare notice · the Ask panel
    assert "/static/panelkit.js" not in page  # a bare branch carries no contract control (r11)
