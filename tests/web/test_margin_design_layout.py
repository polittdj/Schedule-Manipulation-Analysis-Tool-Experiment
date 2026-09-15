"""/margin wears the Claude Design "Control Margin Dashboard" layout (ADR-0489), functionality
unchanged — the eleventh page on the design, the third and LAST Control screen.

The artboard (the v2 canvas's ``section[data-screen-label="Control Margin Dashboard"]``, EXECUTED
over loopback HTTP in all four themes — ADR-0464's recipe with ``setScreen('mg')``, zero page
errors; 1 h1 · 17 buttons · 3 inputs · 0 selects · 1 svg): kicker ``Control · Margin &
contingency`` · headline ("What buffer is left — and when it runs out.") · lede · an ⓘ callout
carrying the three-term glossary (margin / contingency / float) · a STATUS DATE chip row
(``v0``..``v5``) beside a GOLD RULE input, a ``Fig 5-30 band ON`` toggle and ``⤓ EXCEL`` · eight
KPI tiles · an accent-bordered take · a two-column grid: "Margin & contingency burn-down"
(▦ DATA · ⛶ PRESENT) beside "Margin erosion trend" (⛶ PRESENT) · a second two-column grid:
"Which activities ARE margin?" (five candidates, INFO buttons) beside "Is the margin sufficient?"
(a verdict pill, a coverage bar, WATCH / CORRECTIVE inputs) · a "Where it lands →" footer.

The mock's chips were DRIVEN on the executed canvas: clicking ``v0`` re-pointed every KPI tile
to that status date (``Effective margin 7 wd`` → ``44 wd``). That is a selector STATE, and the
operator's standing rule for these migrations is "don't modify any of the functionality" (§9) —
so the chips are ported as NAVIGATION (ADR-0470 / ADR-0475's form): one link per solvable
version to that version's analysis page, where its margin set is confirmed (the mock's "Which
activities ARE margin?" card lives there today, per version, and stays there). No chip is ``on``
— nothing on this page is one version's — and the family's pill names the version the takeaway
and the tiles already read.

What the layout changes: the glossary the burn-down panel carried becomes the masthead's callout
(a ``.cd-block``, never a ``.panel``); the strip follows it; the page's own export bar, rate form
and band form sit byte for byte in the options position; the two chart panels go VERBATIM into
the artboard's equal two-column grid (``cd-grid-11``); the risk panel and the per-version table
follow, full width, as before. The mock's "A flat or growing margin yields no zero-margin date —
the projection is suppressed rather than extrapolated backwards" is TRUE of the engine
(``margin_dashboard._erosion`` extrapolates only when ``slope < 0``) and becomes the erosion
panel's own read-me sentence, proven on a growing-margin fixture.

Named omissions (ADR-0489), each with its reason:
  * the chips as a KPI-tile SELECTOR — a new client-side state on a testimony surface; priced,
    never built blind inside a page migration (the tiles read the latest dated version, exactly
    as the takeaway does, and the pill says so).
  * the "Which activities ARE margin?" card — the confirm form is per version and lives on that
    version's /analysis page (its ``back`` field returns there); a per-version form on a
    cross-version page is a functionality change. The chips link to it instead.
  * the mock's ▦ DATA drawer — this page's contract refuses ▦ DATA (the per-version table IS the
    charts' data, rendered on the same page); the table stays its own panel.
  * the mock's "no second simulation" sentence and its "a separate toggle on the SRA workspace"
    caveat — both FALSE here: the sufficiency panel RUNS the seeded SRA on demand and carries
    the Fig 7-43 zero-margin toggle itself.
  * the mock's verdict pill / coverage bar / WATCH / CORRECTIVE inputs — the panel renders the
    verdict after the run, and the thresholds are the band form's own ``watch_pct`` / ``ca_pct``.
  * the GOLD RULE input and the ``Fig 5-30 band ON`` toggle in the chip row — the page's rate and
    band FORMS carry them, byte for byte, in the options position; the band is drawn whenever its
    dates are entered (there is no ON / OFF state to toggle).
  * the KPI tiles' sub-lines and colours, the mock's take block (the h1 already carries the
    figures), ``⛶ PRESENT`` (the r11 vocabulary is ⛶ ENLARGE), the kicker and the Continue footer
    (the chrome's spine), and every mock figure (KESTREL3, 7.33 wd / month, 2026-05-09).

Red-first (2026-09-14), on the pristine tree: no callout, no strip, no chips, no pill, no grid,
the glossary still inside the burn-down panel, no erosion disclosure.
"""

from __future__ import annotations

import datetime as dt
import re
from html.parser import HTMLParser

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import SessionState, create_app
from schedule_forensics.web.components import _export_bar
from schedule_forensics.web.margin import (
    _margin_band_control,
    _margin_rate_control,
    _margin_risk_panel,
)
from web.test_ui_control_effect_census import _FAMILY

DAY = 480
DELIVER_UID = 3
CHIP = re.compile(r'<a class="cd-chip( on)?" data-idx="(\d+)" href="([^"]+)"[^>]*>v(\d+)</a>')
PILL = re.compile(r'<span class="muted cd-pill" data-no-i18n>([^<]+)</span>')
GRID_OPEN = '<div class="cd-grid cd-grid-11">'
CALLOUT_OPEN = '<div class="cd-block cd-callout">'
DISCLOSURE = (
    "A flat or growing margin yields no zero-margin date &mdash; the projection is suppressed "
    "rather than extrapolated backwards."
)

#: the design's order on the served page: masthead (takeaway · lede · the eight tiles) · the
#: glossary callout · the strip · the page's own options (export bar · rate form · band form) ·
#: the grid of the two chart panels · the risk panel · the per-version table · the page's script
ORDER = (
    "<div class=chapter-kicker",
    '<h1 class="page-takeaway"',
    '<p class="page-lede">',
    '<div class="ws-kpi">',
    CALLOUT_OPEN,
    "<details class=explain>",
    "id=marginCursor",
    '<div class="export-bar">',
    'name="rate"',
    'action="/margin/band"',
    GRID_OPEN,
    'id="marginBurndownChart"',
    'id="marginErosionChart"',
    "id=marginRiskRun",
    "Per-version figures",
    "id=marginDashData",
    "/static/margin_dashboard.js",
)

_MARGINS = [("2026-02-27", 40), ("2026-03-31", 30), ("2026-04-30", 20), ("2026-05-29", 10)]
_GROWING = [("2026-02-27", 10), ("2026-03-31", 20), ("2026-04-30", 30), ("2026-05-29", 40)]


def _t(uid: int, name: str, days: float, **kw: object) -> Task:
    return Task(unique_id=uid, name=name, duration_minutes=int(days * DAY), **kw)  # type: ignore[arg-type]


def _r(p: int, s: int) -> Relationship:
    return Relationship(predecessor_id=p, successor_id=s, type=RelationshipType.FS, lag_minutes=0)


def _version(status: str, margin_days: float) -> Schedule:
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


def _cyclic_version(name: str, day: int) -> Schedule:
    """A dated but CPM-unsolvable version (1↔2 logic cycle) — a version the strip must NOT
    name, exactly as the provenance chip does not (the r12 population rule)."""
    s = dt.datetime(2026, 6, day, 8, 0)
    f = dt.datetime(2026, 6, day + 1, 17, 0)
    return Schedule(
        name=name,
        source_file=f"{name}.xml",
        project_start=dt.datetime(2026, 6, 1),
        status_date=dt.datetime(2026, 6, day + 2),
        tasks=(_t(1, "A", 1, start=s, finish=f), _t(2, "B", 1, start=s, finish=f)),
        relationships=(_r(1, 2), _r(2, 1)),
    )


def _state(margins: list[tuple[str, float]], *extra: Schedule) -> SessionState:
    st = SessionState()
    for status, m in margins:
        v = _version(status, m)
        st.schedules[v.source_file] = v
    for v in extra:
        st.schedules[v.source_file] = v
    st.target_uid = DELIVER_UID
    return st


def _client(margins: list[tuple[str, float]], *extra: Schedule) -> TestClient:
    return TestClient(create_app(_state(margins, *extra)))


@pytest.fixture(scope="module")
def quad() -> TestClient:
    return _client(_MARGINS)


def _panels(page: str) -> int:
    """Elements carrying the `panel` CLASS — the promotion census the r12 sweep pins."""

    class Count(HTMLParser):
        n = 0

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if "panel" in (dict(attrs).get("class") or "").split():
                self.n += 1

    parser = Count()
    parser.feed(page)
    return parser.n


def _block(page: str, opener: str) -> tuple[str, int]:
    """A wrapper's exact extent, found by tracking ``div`` depth from its start tag (the
    ADR-0484 lesson: a slice that stops at the next panel's shell cannot see a panel pulled
    INSIDE the wrapper)."""
    start = page.index(opener)
    depth = 0
    for m in re.finditer(r"<div\b|</div>", page[start:]):
        depth += 1 if m.group().startswith("<div") else -1
        if depth == 0:
            return page[start : start + m.end()], start + m.end()
    raise AssertionError(f"{opener} never closes")


def test_the_cursor_strip_serves_one_link_chip_per_version_and_none_is_on(quad: TestClient) -> None:
    page = quad.get("/margin").text
    assert page.count("id=marginCursor") == 1
    chips = CHIP.findall(page)
    assert [(idx, href, lab) for _on, idx, href, lab in chips] == [
        ("0", "/analysis/2026-02-27.mpp", "1"),
        ("1", "/analysis/2026-03-31.mpp", "2"),
        ("2", "/analysis/2026-04-30.mpp", "3"),
        ("3", "/analysis/2026-05-29.mpp", "4"),
    ], chips
    assert [on for on, *_rest in chips] == ["", "", "", ""]  # a link list has no selected state
    pill = PILL.search(page)
    # the version the takeaway and the tiles read — the LATEST dated one — not a selection
    assert pill and pill.group(1) == "v4 &middot; 2026-05-29.mpp &middot; DD 05/29/2026", pill
    strip, _end = _block(page, '<div class="viz-controls cd-cursor" id=marginCursor>')
    assert "opens that version&rsquo;s analysis page" in strip
    assert "nothing on this page is hidden behind a chip" in strip
    assert "the pill names the version the takeaway and the tiles read" in strip


def test_a_chip_opens_that_versions_analysis_page_with_its_margin_confirm_form(
    quad: TestClient,
) -> None:
    """The chip is NAVIGATION to where the margin set is confirmed, per version."""
    page = quad.get("/margin").text
    chips = CHIP.findall(page)
    assert len(chips) == 4, chips  # a loop over zero chips could never fail (the red run's lesson)
    for _on, _idx, href, lab in chips:
        key = href.rsplit("/", 1)[1]
        target = quad.get(href)
        assert target.status_code == 200, (href, target.status_code)
        body = target.text
        assert 'action="/margin/confirm"' in body, href
        assert f'<input type=hidden name=key value="{key}">' in body, href
        assert 'name=uid value="2" checked' in body, (href, "UID 2 is the named margin task")
        assert f"v{lab}" in page  # the label the chip carried


def test_the_strip_names_only_the_solvable_population_like_the_provenance_chip() -> None:
    """Four solvable versions plus one unsolvable (cycle) version: the chips are the FOUR the
    dashboard computes from — the provenance chip's population — never the raw loaded five."""
    page = _client(_MARGINS, _cyclic_version("tangled", 20)).get("/margin").text
    chips = CHIP.findall(page)
    assert [href for _on, _idx, href, _lab in chips] == [
        "/analysis/2026-02-27.mpp",
        "/analysis/2026-03-31.mpp",
        "/analysis/2026-04-30.mpp",
        "/analysis/2026-05-29.mpp",
    ], chips
    strip, _end = _block(page, '<div class="viz-controls cd-cursor" id=marginCursor>')
    assert "tangled" not in strip
    pill = PILL.search(page)
    assert pill and pill.group(1).startswith("v4 &middot; 2026-05-29.mpp"), pill
    assert page.count("v1→v4") == 3  # the three provenance chips agree with the strip


def test_one_loaded_version_serves_no_strip_but_the_callout_the_grid_and_both_charts() -> None:
    page = _client(_MARGINS[-1:]).get("/margin").text
    assert "id=marginCursor" not in page and "cd-chip" not in page and "cd-pill" not in page
    assert page.count(CALLOUT_OPEN) == 1 and page.count(GRID_OPEN) == 1
    assert 'id="marginBurndownChart"' in page and 'id="marginErosionChart"' in page


def test_chips_carry_no_id_and_no_family_word(quad: TestClient) -> None:
    """The M1 control census recognises a stepper by id + className; a link chip is neither."""
    page = quad.get("/margin").text
    tags = re.findall(r"<a class=\"cd-chip[^>]*>", page)
    assert len(tags) == 4
    for tag in tags:
        assert " id=" not in tag and not re.search(_FAMILY, tag), tag
    strip = re.search(r'<div class="viz-controls cd-cursor" id=(\w+)>(.*?)</div>', page, re.S)
    assert strip and not re.search(_FAMILY, strip.group(1))
    values = re.findall(r'(?:class|id)="?([^" >]+)"?', strip.group(2))
    assert values and not any(re.search(_FAMILY, v) for v in values), values


def test_the_masthead_leads_then_the_callout_the_strip_the_options_and_the_grid(
    quad: TestClient,
) -> None:
    page = quad.get("/margin").text
    missing = [mark for mark in ORDER if mark not in page]
    assert not missing, missing
    positions = [page.index(mark) for mark in ORDER]
    assert positions == sorted(positions), list(zip(ORDER, positions, strict=True))


def test_the_grid_holds_exactly_the_two_chart_panels_and_the_rest_stays_outside(
    quad: TestClient,
) -> None:
    page = quad.get("/margin").text
    assert page.count(GRID_OPEN) == 1
    grid, end = _block(page, GRID_OPEN)
    assert grid.count('<div class="panel" data-export="/export/xlsx/margin">') == 2
    assert 'id="marginBurndownChart"' in grid and 'id="marginErosionChart"' in grid
    assert grid.index('id="marginBurndownChart"') < grid.index('id="marginErosionChart"')
    for outside in ("id=marginRiskRun", "Per-version figures", 'name="rate"', "/margin/band"):
        assert outside not in grid, outside
    assert page.index("id=marginRiskRun") > end  # the risk panel follows the grid, outside it
    assert page.index("Per-version figures") > end


def test_the_glossary_is_the_mastheads_callout_and_no_longer_inside_the_burn_down_panel(
    quad: TestClient,
) -> None:
    page = quad.get("/margin").text
    assert page.count("<details class=explain>") == 1  # moved, never duplicated
    callout, _end = _block(page, CALLOUT_OPEN)
    assert "MARGIN vs CONTINGENCY vs FLOAT" in callout
    assert "<div class=panel" not in callout and 'class="panel' not in callout  # a block
    burndown = page[page.index(GRID_OPEN) : page.index('id="marginErosionChart"')]
    assert "<details" not in burndown


def test_every_panel_form_byte_id_and_export_survives_the_layout() -> None:
    st = _state(_MARGINS)
    page = TestClient(create_app(st)).get("/margin").text
    # rate · band · burn-down · erosion · risk · table · the chrome's Ask panel · the chrome's
    # analysis-endpoint banner (a target is set) — the callout is a block, not a panel
    assert _panels(page) == 8
    assert _export_bar("margin") in page
    assert _margin_rate_control(30.0) in page  # the rate form, byte for byte
    assert _margin_band_control(st) in page  # the band form, byte for byte
    assert _margin_risk_panel(st) in page  # the risk panel, byte for byte
    assert page.count('data-export="/export/xlsx/margin"') == 3
    assert page.count("data-sf-big") == 4 and page.count("data-sf-excel") == 3
    assert page.count("<div class=stat-card>") == 8
    for probe in (
        'id="marginBurndownChart"',
        'id="marginErosionChart"',
        "id=marginRiskRun",
        "id=marginRiskZero",
        "id=marginRiskStatus",
        "<div id=marginRisk>",
        "id=marginDashData",
        "<th scope=col>Status date</th>",
    ):
        assert page.count(probe) == 1, probe
    # the layout stamps a cache-busting ``?v=`` on static URLs, so the pin reads the prefix
    assert page.count('<script defer src="/static/margin_dashboard.js') == 1
    assert page.count("/static/panelkit.js") == 1
    assert "Effective margin to Deliver SV1 is 10 work days as of 05/29/2026" in page


def test_the_erosion_disclosure_is_true_of_the_engine_and_proven_on_a_growing_margin() -> None:
    """The mock's sentence may be said only because ``_erosion`` extrapolates only when the fit's
    slope is negative: a GROWING margin yields no zero-margin date, no marker, a ``—`` tile."""
    growing = _client(_GROWING)
    d = growing.get("/api/margin/dashboard").json()
    assert [m["effective_margin_wd"] for m in d["months"]] == [10.0, 20.0, 30.0, 40.0]
    assert d["zero_margin_date"] is None  # suppressed, not extrapolated backwards
    page = growing.get("/margin").text
    assert DISCLOSURE in page
    assert "<div class=stat-value>—</div><div class=stat-label>Zero-margin date</div>" in page
    assert "margin reaches zero around" not in page
    # the sentence is a statement of the RULE, so an eroding series carries it too — beside the
    # zero-margin date the rule then does produce
    eroding = _client(_MARGINS)
    assert eroding.get("/api/margin/dashboard").json()["zero_margin_date"] == "2026-06-29"
    body = eroding.get("/margin").text
    erosion = body[body.index("Margin Erosion Trend (MET)") : body.index('id="marginErosionChart"')]
    assert DISCLOSURE in erosion
    assert "margin reaches zero around 06/29/2026" in body


def test_the_mocks_selector_confirm_card_drawer_and_footer_are_not_ported(quad: TestClient) -> None:
    page = quad.get("/margin").text
    # grep the artifact FIRST (ADR-0484's lesson): every probe is a string the pristine page does
    # not carry, checked on the pristine render before this module was trusted
    for absent in (
        "Which activities ARE margin?",
        "no second simulation",
        "Margin is the earliest warning you get",  # the mock's footer; "Where it lands" is the
        "TRIPPED",  # chrome's own chapter link, so it can prove nothing here
        "Fig 5-30 band ON",
        "PRESENT",
        "▦ DATA",
        "zero-margin re-solve",
        "a separate toggle on the SRA workspace",
    ):
        assert absent not in page, absent
    # the true sentences the page keeps: the SRA RUNS on demand and carries the Fig 7-43 toggle
    assert "Runs the seeded SSI SRA" in page and "id=marginRiskZero" in page
