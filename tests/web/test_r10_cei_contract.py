"""Chapter-06 /cei (Bow Wave / CEI) wears the merged panel contract — Ultracode round 10.

What this pins:

* the **two panel-head strips** (``.panel-head`` + the unchanged h2 text + the series
  ``.prov-chip``) and one ``.sf-take`` per panel, every figure quoted from a value the page
  ALREADY renders verbatim (asserted by finding the same digits in the KPI strip, the
  finish-placement bar's foot and the CEI table's own cells);
* the **toolbar vocabulary** — panelkit.js's EXACT strings, ⤓ EXCEL pointing at the EXISTING
  ``/export/xlsx/cei`` endpoint (asserted **live**, never a dead link) and ▦ DATA deliberately
  ABSENT (neither panel ships an ``.sf-drawer``: the chart's ``.sr-only`` a11y table is
  injected by cei.js and the CEI panel's own table IS the data);
* the **include** — ``panelkit.js`` is a PER-PAGE include and must be present EXACTLY ONCE
  (two ``<script src>`` elements would register two delegated listeners and each click would
  toggle ``.is-big`` twice). Matched as a SUBSTRING: ``_page`` cache-busts every static URL;
* the **promotion census** — the conversion decorates the panels that already existed; the
  ``.panel`` count is unchanged (5 on this fixture pair), so nothing NEW joins jarvis's broad
  ``html[data-theme=jarvis] .panel`` fight;
* this page's own **HAZARD (standing requirement 4)** — /cei carries the ADR-0268 invariant in
  TWO forms (``POST /target`` for the state change, ``GET /cei`` for the display-only track
  set). Both are pinned BYTE-EXACT here, in all three render variants (plain / tracked /
  focused), and the GET-must-not-mutate rule is re-asserted;
* the **shared cei.js contract** — cei.js is also the /mission wall's chart script and reads
  six ids UNGUARDED; all of them must survive on both routes.

The real-browser click proof (the script actually loads and its delegated listener drives a
real ⛶ click) lives in ``test_r10_cei_panelkit.py`` — markup alone is not evidence."""

from __future__ import annotations

import html
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.ai.citations import introduces_loaded_terms
from schedule_forensics.engine.bow_wave import BowWave, SnapshotProfile
from schedule_forensics.web.app import SessionState, _cei_body, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"

#: panelkit.js's exact strings — this page may only ever render these.
EXCEL_LABEL = "⤓ EXCEL"
ENLARGE_LABEL = "⛶ ENLARGE"
DATA_LABEL = "▦ DATA"

#: the two /cei page forms, BYTE-EXACT (ADR-0268: Focus is a POST state change, the track set
#: is a display-only GET). The panel conversion must not have touched one character of either.
FOCUS_FORM = (
    "<form method=post action=/target class=viz-controls>\n"
    '<input type=hidden name=next_url value="/cei">\n'
    '<label>Target UID <input name=uid type=number min=1 value=""\n'
    'placeholder="UID"></label>\n'
    "<button type=submit>Focus</button>\n</form>"
)
TRACK_FORM = (
    "<form method=get action=/cei class=viz-controls>\n"
    '<label>Track UIDs <input id=ceiTrack name=uids data-no-i18n value=""\n'
    'placeholder="e.g. 155, 187, 411" size=28\n'
    'title="Up to 20 UniqueIDs (comma/space separated) marked on every snapshot of the '
    'animation — independent of the primary target"></label>\n'
    "<button type=submit>Track</button></form>"
)

#: every element id cei.js queries. The first five are read UNGUARDED (a rename throws and the
#: chart never paints); cei.js is shared with the /mission wall, so both routes are checked.
CEI_JS_IDS = ("ceiChart", "prevSnap", "nextSnap", "autoPlay", "snapLabel", "ceiTotals", "ceiTrack")


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def _upload(client: TestClient, name: str) -> None:
    data = (GOLDEN / f"{name}.mspdi.xml").read_bytes()
    assert (
        client.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")}).status_code
        == 200
    )


@pytest.fixture
def pair(client: TestClient) -> TestClient:
    _upload(client, "Project2")
    _upload(client, "Project5")
    return client


def _post_target(client: TestClient, uid: str) -> None:
    client.post(
        "/target",
        data={"uid": uid, "next_url": "/cei"},
        headers={"origin": "http://127.0.0.1"},
        follow_redirects=False,
    )


# ── the contract itself ───────────────────────────────────────────────────────────────────


def test_both_cei_panels_wear_head_tools_prov_and_take(pair: TestClient) -> None:
    page = pair.get("/cei").text
    for title in (
        "Bow Wave &mdash; Activity Finishes by month",
        "CEI &mdash; Current Execution Index",
    ):
        assert f"<div class=panel-head><h2>{title}</h2>" in page, title
    assert page.count("class=sf-take") == 2
    assert page.count("class=prov-chip") == 2
    assert page.count('data-export="/export/xlsx/cei"') == 2
    # the series provenance vocabulary (first→last pair), i18n-inert
    assert (
        "v1→v2 · SOURCE: Project2.mspdi.xml → Project5.mspdi.xml · "
        "DD 2026-05-24 → 2026-08-27" in page
    )
    assert page.count("data-no-i18n>v1→v2") == 2


def test_the_glyph_strip_is_exactly_the_real_ones(pair: TestClient) -> None:
    page = pair.get("/cei").text
    assert page.count(EXCEL_LABEL) == 2 and page.count("data-sf-excel") == 2
    assert page.count(ENLARGE_LABEL) == 2 and page.count("data-sf-big") == 2
    # ▦ DATA is deliberately absent: neither panel ships an .sf-drawer, and panelkit returns
    # silently when the drawer is missing — a glyph that does nothing is the defect we avoid.
    assert DATA_LABEL not in page and "data-sf-data" not in page and "sf-drawer" not in page


def test_excel_glyph_points_at_a_live_endpoint(pair: TestClient) -> None:
    """⤓ EXCEL follows the panel's data-export; that URL must serve a real workbook."""
    assert 'data-export="/export/xlsx/cei"' in pair.get("/cei").text
    resp = pair.get("/export/xlsx/cei")
    assert resp.status_code == 200
    assert "spreadsheet" in resp.headers["content-type"]
    # the export takes NO uids parameter — the track set changes no exported number, so the
    # data-export URL must never claim to filter by it.
    assert "?uids=" not in pair.get("/cei?uids=106,113").text.split('data-export="')[1][:60]


def test_panelkit_is_included_exactly_once(pair: TestClient) -> None:
    """Standing requirement 2: emit the markup, ship the script — and only one copy of it."""
    page = pair.get("/cei").text
    assert "/static/panelkit.js" in page  # SUBSTRING: _page cache-busts the src to "?v=…"
    assert page.count("/static/panelkit.js") == 1  # two includes = two listeners = a no-op click
    assert pair.get("/static/panelkit.js").status_code == 200


def test_guard_page_emits_no_panelkit_markup(client: TestClient) -> None:
    """The <2-version guard bypasses _cei_body entirely: no glyphs, so no inert toolbar."""
    _upload(client, "Project2")
    page = client.get("/cei").text
    assert "at least two versions" in page
    assert ENLARGE_LABEL not in page and EXCEL_LABEL not in page
    assert "/static/panelkit.js" not in page


def test_promotion_census_no_new_panel_joins_the_theme_fight(pair: TestClient) -> None:
    """Standing requirement 1: an element that GAINS .panel joins jarvis's broad .panel rule.
    The conversion decorates the panels that already existed — the count is unchanged."""
    from html.parser import HTMLParser

    class Count(HTMLParser):
        n = 0

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if "panel" in set((dict(attrs).get("class") or "").split()):
                self.n += 1

    p = Count()
    p.feed(pair.get("/cei").text)
    assert p.n == 5  # measured on this fixture pair BEFORE the conversion (origin/main)


# ── the takeaways quote only figures the page already renders ─────────────────────────────


def test_takes_quote_only_figures_the_page_already_renders(pair: TestClient) -> None:
    page = pair.get("/cei").text
    assert "2 snapshots on one shared 18-month axis; the newest is Project5.mspdi.xml." in page
    assert (
        "Project5.mspdi.xml: CEI 1.00 in Jun-26 — 3 of 3 previously planned finishes "
        "actually landed." in page
    )
    # every digit above is rendered verbatim SOMEWHERE ELSE on this same page, by the markup
    # that owns it — the take re-reads, it never re-derives.
    assert "<div class=stat-value>2</div><div class=stat-label>Versions compared" in page
    assert "finishes across 18 months" in page  # the finish-placement bar's foot
    assert "<td>Project5.mspdi.xml</td>" in page  # the CEI table's Snapshot cell
    assert "<td>Jun-26</td>" in page  # its Period cell
    assert "class=pass>1.00" in page  # its CEI cell, same :.2f formatting
    assert "<div class=stat-value>3</div>" in page  # planned / finished that month


def test_takes_are_none_safe_and_quote_no_figure_when_nothing_is_scored() -> None:
    """_cei_body is called directly as a unit (a hand-built 1-snapshot wave). The takes must
    survive a missing CEI, and the no-score branch must quote no number it cannot source."""

    def profile(cei: float | None) -> SnapshotProfile:
        return SnapshotProfile(
            label="S",
            status_index=0,
            baselined=(0,),
            scheduled=(0,),
            finished=(0,),
            cei=cei,
            cei_period="May-26" if cei is not None else None,
            cei_planned=3 if cei is not None else None,
            cei_scheduled=0,
            cei_finished=0 if cei is not None else None,
        )

    body = _cei_body(BowWave(month_labels=("May-26",), snapshots=(profile(None),)))  # positional
    assert "S carries no comparable prior month, so no CEI is scored for it." in body
    assert "1 snapshots on one shared 1-month axis; the newest is S." in body
    body = _cei_body(BowWave(month_labels=("May-26",), snapshots=(profile(0.0),)))
    assert "S: CEI 0.00 in May-26 — 0 of 3 previously planned finishes actually landed." in body
    # a wave with nothing to profile still renders, quoting nothing
    empty = _cei_body(BowWave(month_labels=(), snapshots=()))
    assert empty.count("No snapshot could be profiled from the loaded versions.") == 2


# ── the page's own hazard: the two ADR-0268 forms (standing requirement 4) ─────────────────


def test_both_cei_forms_survive_byte_exact_in_every_render_variant(pair: TestClient) -> None:
    plain = pair.get("/cei").text
    assert FOCUS_FORM in plain and TRACK_FORM in plain
    assert plain.count("<form") == 6  # 4 global nav forms + these 2 — none added, none lost

    tracked = pair.get("/cei?uids=106,113").text
    assert tracked.count("<form") == 6
    assert FOCUS_FORM.replace('value="/cei"', 'value="/cei?uids=106%2C%20113"') in tracked
    assert TRACK_FORM.replace('value=""', 'value="106, 113"') in tracked

    _post_target(pair, "6")
    focused = pair.get("/cei").text
    assert TRACK_FORM in focused
    # the focused variant adds exactly the conditional clear-focus button, nothing else
    assert (
        FOCUS_FORM.replace('value=""', 'value="6"').replace(
            "<button type=submit>Focus</button>\n</form>",
            "<button type=submit>Focus</button>\n"
            '<button class=linkbtn type=submit name=uid value="">clear focus</button></form>',
        )
        in focused
    )


def test_get_cei_still_never_mutates_the_session(pair: TestClient) -> None:
    """ADR-0268 re-asserted after the conversion: the GET is display-only, the POST is the
    state change (and still redirects back to /cei)."""
    st = pair.app.state.session  # type: ignore[attr-defined]
    pair.get("/cei?target=2")
    assert st.target_uid is None
    resp = pair.post(
        "/target",
        data={"uid": "2", "next_url": "/cei"},
        headers={"origin": "http://127.0.0.1"},
        follow_redirects=False,
    )
    assert resp.status_code == 303 and resp.headers["location"] == "/cei"
    assert st.target_uid == 2


# ── the shared cei.js consumer (the ids are read unguarded) ───────────────────────────────


def test_every_id_cei_js_reads_survives_on_both_of_its_routes(pair: TestClient) -> None:
    page = pair.get("/cei").text
    for ident in CEI_JS_IDS:
        assert f"id={ident}" in page, ident
    assert "id=ceiChart class=chart-host" in page  # chartframe's own zoom bar still attaches
    mission = pair.get("/mission").text
    for ident in ("ceiChart", "prevSnap", "nextSnap", "autoPlay", "snapLabel"):
        assert f'id="{ident}"' in mission or f"id={ident}" in mission, ident


# ── the prose asserts nothing the engine did not (standing requirement 3) ─────────────────


def test_control_proves_the_loaded_terms_gate_can_fail() -> None:
    """The audit below is only evidence if the SAME call flags a genuinely loaded string."""
    assert introduces_loaded_terms("", "deliberate concealed fraud") is True
    assert introduces_loaded_terms("", "CEI 1.00 in Jun-26 — 3 of 3 finishes landed.") is False


def test_cei_presentation_prose_introduces_no_loaded_terms(pair: TestClient) -> None:
    """Every server-authored takeaway / lede / take on /cei, harvested from the REAL render so
    a future edit is audited automatically (ADR-0132's gate, run over presentation prose)."""
    patterns = (
        re.compile(r"<p class=sf-take data-no-i18n>(.*?)</p>", re.S),
        re.compile(r'<h1 class="page-takeaway" data-no-i18n>(.*?)</h1>', re.S),
        re.compile(r'<p class="page-lede">(.*?)</p>', re.S),
        re.compile(r'<button type=button data-sf-excel title="(.*?)"', re.S),
    )
    page = pair.get("/cei").text
    strings = [
        " ".join(html.unescape(re.sub(r"<[^>]+>", " ", raw)).split())
        for pat in patterns
        for raw in pat.findall(page)
    ]
    assert len(strings) >= 6, strings  # 2 takes + h1 + lede + 2 export tooltips — never vacuous
    for text in strings:
        assert introduces_loaded_terms("", text) is False, text
    joined = " || ".join(strings)
    for fragment in (
        "2 snapshots on one shared 18-month axis",  # the bow-wave take
        "previously planned finishes actually landed",  # the CEI-table take
        "Where unfinished work sits against each snapshot's data date",  # the new lede
        "Export the bow-wave monthly finish profiles and the CEI table",  # ⤓ tooltip
        "Export the CEI table and the bow-wave monthly finish profiles",  # ⤓ tooltip
    ):
        assert fragment in joined, fragment


def test_the_pages_other_scaffolding_is_untouched(pair: TestClient) -> None:
    page = pair.get("/cei").text
    assert "/export/xlsx/cei" in page and "/export/docx/cei" in page  # the _export_bar pair
    assert "CHAPTER 06 · WORK PILING UP" in page and "Chapter 07" in page
    assert 'class="page-takeaway"' in page and 'class="page-lede"' in page
    assert "Latest scored month" in page and "Where the finishes sit" in page
    assert "/static/cei.js" in page
