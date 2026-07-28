"""Chapter-05 group (/trend, /curves, /scurve) wears the merged panel contract — rank 9.

What this pins, per page:

* the **story header** — the chapter kicker comes from the spine, the ``page-takeaway`` h1 and
  the muted ``page-lede`` are built only where they were MISSING (/curves, /scurve; /trend
  already had ``_how_it_moved_header``);
* the **panel-head strips** (``.panel-head`` + ``h2`` + ``.prov-chip``) and one ``.sf-take``
  per chart panel, every figure quoted from what the page already renders;
* the **toolbar vocabulary** — panelkit.js's EXACT label strings, and ⤓ EXCEL only where an
  EXISTING export endpoint serves that visual (asserted **live**, never a dead link);
* the **animation survives** — the per-chart steppers, the quality drill stepper, the S-curve
  stepper and the page-level Play-all ids are all still present and unrenamed, and the chart
  hosts the steppers drive keep their ids.

Markup-level assertions only; the real-browser click proof lives in
``test_ch05_panelkit.py`` (a page can render the glyphs with no script to drive them — the
round-4 latent-gap lesson)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"

#: panelkit.js's exact strings — a page may only ever render these (or their toggled forms,
#: which panelkit writes at click time).
DATA_LABEL = "▦ DATA"
EXCEL_LABEL = "⤓ EXCEL"
ENLARGE_LABEL = "⛶ ENLARGE"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def _upload(client: TestClient, name: str) -> None:
    data = (GOLDEN / "project2_5" / f"{name}.mspdi.xml").read_bytes()
    assert (
        client.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")}).status_code
        == 200
    )


@pytest.fixture
def pair(client: TestClient) -> TestClient:
    _upload(client, "Project2")
    _upload(client, "Project5")
    return client


# ── /trend ────────────────────────────────────────────────────────────────────────────────


def test_trend_panels_wear_head_take_and_prov(pair: TestClient) -> None:
    page = pair.get("/trend").text
    for title in (
        "Version trend &mdash; 2 versions, oldest first (by data date)",
        "Trend charts",
        "Quality drill-down &amp; animation",
        "Schedule-quality trends",
        "Manipulation-trend signals (consecutive versions)",
        "Schedule margin burndown",
    ):
        assert f"<div class=panel-head><h2>{title}</h2>" in page, title
    # one takeaway per panel + the series provenance chip (first→last pair vocabulary)
    assert page.count("class=sf-take") == 6
    assert page.count("class=prov-chip") == 6
    assert (
        "v1→v2 · SOURCE: Project2.mspdi.xml → Project5.mspdi.xml · "
        "DD 2026-05-24 → 2026-08-27" in page
    )
    assert page.count("data-no-i18n>v1→v2") == 6  # filenames/dates never machine-translated


def test_trend_takes_quote_figures_the_page_already_renders(pair: TestClient) -> None:
    page = pair.get("/trend").text
    # the Net Finish Impact figure is the one already printed under the version table
    assert "Net Finish Impact across the series" in page and "-148 calendar days" in page
    assert "Across 2 versions the Net Finish Impact is" in page
    assert "-148 calendar days</b> &mdash; the project finish moved later" in page
    # the signal count matches the rows the table actually renders
    assert "manipulation-trend signals across 1 consecutive-version step." in page


def test_trend_toolbars_use_the_exact_contract_labels_and_live_exports(pair: TestClient) -> None:
    page = pair.get("/trend").text
    assert ENLARGE_LABEL in page and EXCEL_LABEL in page
    for legacy in ("⛶ Enlarge", "▦ Data"):
        assert legacy not in page, legacy
    # ⤓ EXCEL only where an EXISTING endpoint serves the panel — asserted live
    assert page.count('data-export="/export/xlsx/trend"') == 4
    assert 'data-export="/export/xlsx/margin"' in page
    assert pair.get("/export/xlsx/trend").status_code == 200
    assert pair.get("/export/xlsx/margin").status_code == 200
    # the manipulation-signal table has no endpoint of its own → no ⤓ there (never a dead link)
    signals = page.split("Manipulation-trend signals (consecutive versions)")[1]
    head = signals.split("</div>")[0]
    assert EXCEL_LABEL not in head
    assert ENLARGE_LABEL in head


def test_trend_animation_survives_the_conversion(pair: TestClient) -> None:
    page = pair.get("/trend").text
    assert "/static/panelkit.js" in page
    for ident in ("id=trendCharts", "id=qualPrev", "id=qualNext", "id=qualPlay", "id=qualMetric"):
        assert ident in page, ident
    assert 'id=trendCharts class="charts chart-host"' in page  # the stepper's chart host
    assert "id=marginBurndown" in page
    assert "/static/trend.js" in page and "/static/margin.js" in page


# ── /curves ───────────────────────────────────────────────────────────────────────────────


def test_curves_story_header_is_built_from_rendered_figures(pair: TestClient) -> None:
    page = pair.get("/curves").text
    assert 'class="page-takeaway"' in page and 'class="page-lede"' in page
    assert "2 versions of finish and start months on one shared 23-month axis" in page
    assert "the newest is Project5.mspdi.xml (data date 2026-08-27)" in page
    assert "CHAPTER 05" in page  # the kicker rides the spine, never re-implemented


def test_curves_panels_wear_head_take_prov_and_export(pair: TestClient) -> None:
    page = pair.get("/curves").text
    for title in (
        "Finishes &mdash; actual vs baseline by month",
        "DATA Date Finishes &mdash; actual-finish curve per version",
        "Slippage &mdash; start &amp; finish curves per version",
    ):
        assert f"<div class=panel-head><h2>{title}</h2>" in page, title
    assert page.count("class=sf-take") == 3
    assert page.count("class=prov-chip") == 3
    assert page.count('data-export="/export/xlsx/curves"') == 3
    assert pair.get("/export/xlsx/curves").status_code == 200
    # the takes quote the axis + version identity the page already draws
    assert "on the shared 23-month axis (Mar-26 &rarr; Jan-28)" in page
    assert "2 files on one fixed 23-month axis" in page


def test_curves_page_includes_panelkit_and_keeps_its_steppers(pair: TestClient) -> None:
    page = pair.get("/curves").text
    assert "/static/panelkit.js" in page  # the per-page include (proved by a click elsewhere)
    for ident in ("id=finishesChart", "id=dataDateChart", "id=slippageChart", "id=curvesHideDone"):
        assert ident in page, ident
    assert "/static/curves.js" in page


# ── /scurve ───────────────────────────────────────────────────────────────────────────────


def test_scurve_story_header_quotes_the_status_point_it_renders(pair: TestClient) -> None:
    page = pair.get("/scurve").text
    assert 'class="page-takeaway"' in page and 'class="page-lede"' in page
    # the h1, the panel take and the AI-interpretation prose all read the SAME status point
    assert "22% of the work has finished against 38% planned" in page
    assert "22% finished against 38% planned at its data date, over 126 activities." in page
    assert "<b>22%</b> of the work has finished versus" in page and "<b>38%</b> planned" in page


def test_scurve_panel_wears_the_contract_with_a_live_export(pair: TestClient) -> None:
    page = pair.get("/scurve").text
    assert "<div class=panel-head><h2>S-Curve &mdash; cumulative progress</h2>" in page
    assert "<h2>AI interpretation</h2>" in page  # heading text unchanged, now in a head strip
    assert page.count("class=sf-take") == 1  # the chart panel; the prose panel needs none
    assert page.count("class=prov-chip") == 2
    assert 'data-export="/export/xlsx/scurve"' in page
    assert ENLARGE_LABEL in page and EXCEL_LABEL in page
    assert DATA_LABEL not in page  # no drawer table on this visual — the /evm precedent
    assert pair.get("/export/xlsx/scurve").status_code == 200


def test_scurve_export_url_follows_the_tracked_uids(pair: TestClient) -> None:
    """The panel's ⤓ target must export what the page is SHOWING — tracked UIDs included."""
    page = pair.get("/scurve?uids=106,113").text
    assert 'data-export="/export/xlsx/scurve?uids=106%2C%20113"' in page
    assert pair.get("/export/xlsx/scurve?uids=106,113").status_code == 200


def test_scurve_animation_survives_the_conversion(pair: TestClient) -> None:
    page = pair.get("/scurve").text
    assert "/static/panelkit.js" in page
    for ident in ("id=prevScurve", "id=nextScurve", "id=scurvePlay", "id=scurveChart"):
        assert ident in page, ident
    assert "/static/scurve.js" in page


def test_single_version_pages_still_render(client: TestClient) -> None:
    """One loaded file: the series prov chip falls back to the single-file chip and the
    headers/takes stay grammatical (no '1 versions', no empty label)."""
    _upload(client, "Project5")
    curves = client.get("/curves").text
    assert "1 version of finish and start months" in curves
    assert "SOURCE: Project5.mspdi.xml · DD 2026-08-27" in curves
    assert "1 file on one fixed" in curves
    scurve = client.get("/scurve").text
    assert "SOURCE: Project5.mspdi.xml · DD 2026-08-27" in scurve
    assert "over 1 version." in scurve
