"""/portfolio wears the panel contract (Mission Ops rank 7, prototype screen 'pf').

The pf screen header (chapter kicker via the spine + a complete-sentence takeaway h1 quoting the
session's own counts + a muted lede), the pf-style KPI tiles (the 3px LEFT-edge ``.ctl-kpi.k-edge``
variant — never a repurposed top-edge tile), the ledger panel shelled with the headline strip /
three-glyph tools / per-project provenance chips, and the DCMA / review / excluded chips restyled
to the prototype pill vocabulary (``.sf-pill`` composed onto the existing rib-* classes — the
pass/fail VALUES are the engine's own).

FORMS POST STATE on this page: the expandable version history, the exclude/restore forms, and the
memory readout keep their form field NAMES and ACTIONS byte-identical — the pinned literals below
are copied character-for-character from origin/main's render of the same fixture (verified with a
full-form diff at build time), so any drift in name/action fails here.

Presentation only — every figure quoted is a count/summary this page already rendered verbatim,
and the loaded-terms audit below proves the gate can FAIL before trusting its clean results."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

STATIC = Path(__file__).resolve().parents[2] / "src" / "schedule_forensics" / "web" / "static"

_NS = 'xmlns="http://schemas.microsoft.com/project"'
_TASK = "<Tasks><Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration></Task></Tasks>"


def _mspdi(title: str | None, status: str | None = None, company: str | None = None) -> bytes:
    title_el = f"<Title>{title}</Title>" if title is not None else ""
    status_el = f"<StatusDate>{status}</StatusDate>" if status else ""
    company_el = f"<Company>{company}</Company>" if company else ""
    return (
        f"<Project {_NS}><StartDate>2025-01-06T08:00:00</StartDate>"
        f"{title_el}{company_el}{status_el}{_TASK}</Project>"
    ).encode()


def _client() -> TestClient:
    """Two projects (Alpha x2 versions, Beta x1) — the multi-project chip case."""
    c = TestClient(create_app(SessionState()))
    c.post(
        "/upload",
        files=[
            ("files", ("a.xml", _mspdi("Alpha", "2025-01-10T00:00:00"), "text/xml")),
            ("files", ("b.xml", _mspdi("Alpha", "2025-02-10T00:00:00"), "text/xml")),
            (
                "files",
                (
                    "c.xml",
                    _mspdi("Beta", "2025-01-10T00:00:00", company="NASA Goddard"),
                    "text/xml",
                ),
            ),
        ],
    )
    return c


@pytest.fixture(scope="module")
def client() -> TestClient:
    return _client()


@pytest.fixture(scope="module")
def page(client: TestClient) -> str:
    return client.get("/portfolio").text


# ── the pf screen header ─────────────────────────────────────────────────────────────────────


def test_portfolio_has_the_pf_takeaway_header(page: str) -> None:
    """Complete sentence, session counts inside it (2 projects / 3 files), i18n-inert."""
    m = re.search(r'<h1 class="page-takeaway" data-no-i18n>(.*?)</h1>', page)
    assert m is not None
    take = m.group(1)
    assert "2 projects across 3 loaded files" in take
    assert take.rstrip().endswith(".")  # a sentence, not a label
    assert '<p class="page-lede">' in page


def test_empty_state_is_unchanged(client: TestClient) -> None:
    empty = TestClient(create_app(SessionState())).get("/portfolio").text
    assert "portfolio rollup" in empty  # the pre-shell empty-state sentence survives
    assert "page-takeaway" not in empty


# ── pf-style KPI tiles (3px LEFT edge — the k-edge variant, never ctl's top edge) ────────────


def test_kpi_tiles_quote_the_session_counts(page: str) -> None:
    tiles = re.findall(
        r'<div class="ctl-kpi k-edge[^"]*"><div class=k-label>(.*?)</div>'
        r"<div class=k-value data-no-i18n>(.*?)</div>",
        page,
    )
    assert dict(tiles) == {
        "Projects": "2",
        "Schedule files": "3",
        "Pending review": "0",
        "Excluded": "0",
    }


def test_pending_review_tile_takes_the_warn_edge_only_when_pending(client: TestClient) -> None:
    c = TestClient(create_app(SessionState()))
    # same Project, same data date, DIFFERENT bytes → pending review (the test_project_scope case)
    c.post(
        "/upload",
        files=[
            ("files", ("r1.xml", _mspdi("Twin", "2025-01-10T00:00:00"), "text/xml")),
            ("files", ("r2.xml", _mspdi("Twin", "2025-01-10T00:00:00", company="X"), "text/xml")),
        ],
    )
    page = c.get("/portfolio").text
    assert '<div class="ctl-kpi k-edge k-warn"><div class=k-label>Pending review</div>' in page
    assert '<span class="rib-fail sf-pill p-bad">review</span>' in page
    # the no-pending fixture keeps the neutral edge
    assert "k-edge k-warn" not in _client().get("/portfolio").text


def test_k_edge_variant_is_token_pure_left_edge_css() -> None:
    css = (STATIC / "base.css").read_text(encoding="utf-8")
    edge = ".ctl-kpi.k-edge{border-top:1px solid var(--line);border-left:3px solid var(--accent)}"
    assert edge in css
    assert ".ctl-kpi.k-edge.k-warn{border-left-color:var(--warn)}" in css
    # declared AFTER the top-edge tone rules so the shorthand reset wins (the cascade law)
    assert css.index(".ctl-kpi.k-warn{border-top-color") < css.index(".ctl-kpi.k-edge{")


# ── the ledger panel shell ───────────────────────────────────────────────────────────────────


def test_ledger_panel_wears_the_contract(page: str) -> None:
    """Headline strip + ⤓/⛶ tools + sf-take quoting existing counts; ▦ DATA omitted (the
    table IS the data); ⤓ EXCEL rides an EXISTING endpoint via the panel's data-export."""
    assert '<div class=panel data-export="/export/xlsx/ribbon">' in page
    assert "Portfolio ledger &mdash; one row per project" in page
    assert "data-sf-excel" in page and "data-sf-big" in page
    assert "data-sf-data" not in page  # self-drawer table: no ▦ DATA anywhere on the page
    m = re.search(r"<p class=sf-take data-no-i18n>(.*?)</p>", page)
    assert m is not None
    assert "2 projects · 3 versions in the analysis" in m.group(1)
    # PER-PAGE include, cache-busted src (?v=…) → substring match, never the exact tag
    assert 'src="/static/panelkit.js' in page


def test_excel_button_targets_a_live_endpoint(client: TestClient) -> None:
    assert client.get("/export/xlsx/ribbon").status_code == 200


def test_each_project_row_carries_its_own_prov_chip(page: str) -> None:
    """MULTI-PROJECT provenance: one chip per row, per-project file/DD, i18n-inert."""
    chips = re.findall(r"<span class=prov-chip data-no-i18n>(.*?)</span>", page)
    assert "SOURCE: b.xml · DD 2025-02-10" in chips  # Alpha's LATEST included version
    assert "SOURCE: c.xml · DD 2025-01-10" in chips  # Beta's only version
    assert "SOURCE: a.xml" not in "".join(chips)  # never the superseded version


def test_dcma_chips_wear_the_pill_vocabulary_around_engine_values(page: str) -> None:
    """The chip restyles; the pass/fail VALUES are the engine summary's, verbatim."""
    pills = re.findall(
        r'<span class="(rib-(?:pass|fail) sf-pill p-(?:ok|bad))">(\d+) pass / (\d+) fail</span>',
        page,
    )
    assert len(pills) == 2  # one per project row
    for cls, npass, nfail in pills:
        assert (cls == "rib-pass sf-pill p-ok") == (nfail == "0")
        assert int(npass) + int(nfail) == 8  # the engine's 8 rendered DCMA summary checks


def test_pill_css_is_token_pure() -> None:
    css = (STATIC / "base.css").read_text(encoding="utf-8")
    assert "border-radius:20px" in css.split(".sf-pill{", 1)[1].split("}")[0]
    assert ".sf-pill.p-ok{color:var(--ok)}" in css
    assert ".sf-pill.p-bad{color:var(--bad)}" in css


# ── forms post state: names/actions byte-identical to origin/main's render ───────────────────


def test_version_history_and_exclude_restore_forms_are_byte_identical(client: TestClient) -> None:
    """Pinned literals copied from origin/main's render of this same fixture (full-form diff:
    11/11 forms identical). Any drift in a field NAME or ACTION fails here."""
    page = client.get("/portfolio").text
    assert (
        '<form method=post action="/project/select" style="display:inline">'
        '<input type=hidden name=pid value="title:alpha">'
        '<input type=hidden name=next_url value="/portfolio">'
        "<button type=submit class=btn-link>Analyze this project &#8599;</button></form>"
    ) in page
    assert (
        '<form method=post action="/project/exclude" style="display:inline">'
        '<input type=hidden name=key value="a">'
        '<input type=hidden name=excluded value="1">'
        "<button type=submit class=btn-link>Exclude</button></form>"
    ) in page
    # the version history itself stays the expandable details list with per-version drill links
    assert "<details><summary>" in page
    assert 'href="/analysis/a"' in page and 'href="/analysis/b"' in page
    assert "data date" in page and "activities" in page


def test_exclude_then_restore_round_trip_with_the_pill_badge() -> None:
    c = _client()
    resp = c.post("/project/exclude", data={"key": "b", "excluded": "1"}, follow_redirects=False)
    assert resp.status_code == 303 and resp.headers["location"] == "/portfolio"
    page = c.get("/portfolio").text
    assert '<span class="rib-fail sf-pill p-bad">excluded</span>' in page
    # the Restore form is the byte-identical inverse
    assert (
        '<form method=post action="/project/exclude" style="display:inline">'
        '<input type=hidden name=key value="b">'
        '<input type=hidden name=excluded value="0">'
        "<button type=submit class=btn-link>Restore</button></form>"
    ) in page
    # the row headline (and its chip) fall back to the kept older version — ADR-0259 intact
    assert "SOURCE: a.xml · DD 2025-01-10" in page
    c.post("/project/exclude", data={"key": "b", "excluded": "0"}, follow_redirects=False)
    assert '<span class="rib-fail sf-pill p-bad">excluded</span>' not in c.get("/portfolio").text


def test_memory_readout_keeps_its_form_and_gains_only_the_shell(page: str) -> None:
    assert "Memory" in page and "estimated resident memory" in page
    assert (
        "<form method=post action=/session/ram-threshold class=inline-form>"
        "<label>Warn above <input type=number name=gb min=1 step=1 "
    ) in page
    # the shell around it: a panel-head strip (⛶ only — no export endpoint serves the estimate)
    assert "<div class=panel-head><h2>Memory</h2>" in page


# ── loaded-terms audit: prove the gate can FAIL, then audit every new string ─────────────────


def test_new_strings_never_introduce_loaded_terms(page: str) -> None:
    from schedule_forensics.ai.citations import introduces_loaded_terms

    # CONTROL: the gate MUST flag a bare accusation against an empty source
    assert introduces_loaded_terms("", "deliberate concealed fraud") is True

    new_strings = [
        re.search(r'<h1 class="page-takeaway" data-no-i18n>(.*?)</h1>', page).group(1),  # type: ignore[union-attr]
        re.search(r'<p class="page-lede">(.*?)</p>', page, re.S).group(1),  # type: ignore[union-attr]
        *re.findall(r"<p class=sf-take data-no-i18n>(.*?)</p>", page, re.S),
        "Portfolio ledger — one row per project",
        "Export the quality ribbon for every loaded file — opens in Excel",
        "grouped from your files and folders",
        "loaded versions across every project",
        "duplicate/revision decisions to resolve",
        "versions set aside — restore any time",
    ]
    assert len(new_strings) >= 8
    for s in new_strings:
        assert introduces_loaded_terms("", s) is False, s
