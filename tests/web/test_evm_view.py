"""EVM page (/evm) — schedule-based EVM always; cost indices gracefully N/A without cost.

The golden Project5 schedule is not cost-loaded, so SPI/CPI/TCPI must read NOT_APPLICABLE (never a
fabricated 0) while the Earned-Schedule / baseline-compliance metrics still compute. The engine math
is covered in tests/engine; this pins the page wiring + the adaptive cost behaviour.

Mission Ops rank 4 (ADR-0298): the Chapter-07 story header (kicker via the spine, takeaway h1
quoting the engine's own MetricResult figures, muted lede, ws-kpi strip) and the panel-contract
shells on the four metric tables (headline strip + prov chip + sf-take; toolbar = ⤓ EXCEL only
where a live export endpoint serves the panel's data, + ⛶ ENLARGE, and NO ▦ DATA — the tables
are their own data drawer).
"""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    data = (GOLDEN / "Project5.mspdi.xml").read_bytes()
    c.post("/upload", files={"files": ("Project5.mspdi.xml", data, "text/xml")})
    return c


def test_evm_in_nav(client: TestClient) -> None:
    """ADR-0425 moved /evm off the folded chapter-07 beat (`<a href="/evm">EVM</a>`) and onto the
    LIBRARY rail, so it renders as a full nav entry now. The page must still be reachable from the
    nav and still be labelled EVM — assert those two properties, not the old markup."""
    page = client.get("/").text
    assert '<a class="nav-chapter" href="/evm"' in page
    assert "<span class=ch-label>EVM</span>" in page


def test_evm_empty_session_prompts_load() -> None:
    c = TestClient(create_app(SessionState()))
    assert "Load an analyzable schedule" in c.get("/evm").text


def test_evm_page_shows_schedule_and_cost_panels(client: TestClient) -> None:
    page = client.get("/evm").text
    assert client.get("/evm").status_code == 200
    # the headline KPIs + each section
    for token in (
        "Earned Value Management",
        "SPI(t)",
        "Schedule performance",
        "Cost performance",
        "Baseline compliance",
        "Worst finish variances",
    ):
        assert token in page, token
    # the metric tables render (CEI on the schedule side, SPI on the cost side)
    assert "CEI (Finish)" in page and "SPI" in page


def test_evm_cost_indices_are_na_without_cost(client: TestClient) -> None:
    """Project5 carries no cost, so the cost indices must read N/A (never a fabricated value), with
    a clear note that the schedule isn't cost-loaded."""
    page = client.get("/evm").text
    assert "not cost-loaded" in page
    # the SPI/CPI/TCPI rows show the NOT_APPLICABLE status code, not a number
    assert "NA" in page


def test_evm_export_leaves_na_indices_blank_instead_of_writing_a_fabricated_zero(
    client: TestClient,
) -> None:
    """MF-02 (ADR-0411): the workbook must say what the screen says.

    `/evm` renders NA for Project5's cost indices and explains that NOT APPLICABLE "means
    the loaded file carries no cost data - that is a fact about the file, not a performance
    figure". The export guarded its cells on ``value is not None`` -- but ``_na_index``
    builds the NA result with ``value=0.0`` (its own docstring says "never a fabricated
    0"), so the guard NEVER fired and every cost index left the tool as 0.00, which an
    analyst reads as catastrophic cost performance. The workbook is the artefact that
    travels and gets quoted; it must not contradict the page (Law 2, and the design
    system's "missing shows an em dash, never a fabricated figure").
    """
    page = client.get("/evm").text
    assert "not cost-loaded" in page and "NA" in page  # the SCREEN is honest

    book = client.get("/export/xlsx/evm")
    assert book.status_code == 200
    archive = zipfile.ZipFile(io.BytesIO(book.content))
    sheet = next(n for n in archive.namelist() if "sheet1" in n)
    values = [v.decode() for v in re.findall(rb"<v>([^<]*)</v>", archive.read(sheet))]

    assert "0.0" not in values, f"the workbook fabricates a 0.0 where the page says NA: {values}"
    # ...and the genuinely computed figures still travel (the fix must blank NA cells only)
    assert "0.47" in values and "0.91" in values


def test_evm_page_explains_the_metrics_and_jcl(client: TestClient) -> None:
    page = client.get("/evm").text
    assert "What these EVM numbers mean" in page
    assert "Earned Schedule" in page and "How EVM relates to a JCL" in page


# ── Mission Ops rank 4: the Chapter-07 story header ────────────────────────────────────────


def test_evm_story_header_renders(client: TestClient) -> None:
    """Kicker (via the spine title map), takeaway h1, muted lede, and the ws-kpi strip."""
    page = client.get("/evm").text
    assert "CHAPTER 07 · HOW WE EXECUTE" in page
    assert 'class="page-takeaway"' in page
    assert 'class="page-lede"' in page
    assert '<div class="ws-kpi">' in page
    # the KPI strip quotes the existing EVM figures (labels pin the card set)
    for label in (
        "SPI(t) — Earned Schedule",
        "SPI(t) — Acumen",
        "BEI (throughput)",
        "SVt (working days)",
        "CPI (cost)",
        "TCPI (cost to-go)",
    ):
        assert label in page, label


def test_evm_header_quotes_the_engine_figures_verbatim(client: TestClient) -> None:
    """The takeaway h1 quotes the SAME figures the engine computes on this input (Law 2:
    presentation reads the parity-locked MetricResults verbatim — never a new number)."""
    from schedule_forensics.engine.metrics.dcma14 import compute_bei
    from schedule_forensics.engine.metrics.evm import compute_evm_indices
    from schedule_forensics.importers.mspdi import parse_mspdi

    sch = parse_mspdi(GOLDEN / "Project5.mspdi.xml")
    bei = compute_bei(sch)
    spi_t = compute_evm_indices(sch)["spi_t"]

    page = client.get("/evm").text
    m = re.search(r'<h1 class="page-takeaway"[^>]*>(.*?)</h1>', page)
    assert m, "takeaway h1 missing"
    h1 = m.group(1)
    assert f"BEI {bei.value:.2f}" in h1
    assert f"SPI(t) reads {round(spi_t.value, 2)}" in h1


def test_evm_empty_session_has_no_story_header() -> None:
    c = TestClient(create_app(SessionState()))
    page = c.get("/evm").text
    assert 'class="page-takeaway"' not in page
    assert "Load an analyzable schedule" in page


# ── Mission Ops rank 4: panel-contract shells on the four metric tables ────────────────────


def test_evm_panels_wear_the_contract_shell(client: TestClient) -> None:
    page = client.get("/evm").text
    for title in (
        "Schedule performance",
        "Cost performance",
        "Baseline compliance",
        "Worst finish variances",
    ):
        assert f"<div class=panel-head><h2>{title}</h2>" in page, title
    # provenance chip on each shelled panel, naming the file (i18n-inert). FIVE, not four:
    # /evm also hosts the SHARED "Execution metrics by field group" panel (_field_forecast_panel,
    # the same function /forecast calls), which wears the contract as of the round-10 /forecast
    # conversion — the four panels above plus that one.
    assert page.count("prov-chip") == 5
    assert "SOURCE: Project5.mspdi.xml" in page
    assert "<div class=panel-head><h2>Execution metrics by field group</h2>" in page
    # one takeaway line per shelled panel, quoting table figures
    assert page.count("<p class=sf-take data-no-i18n>") == 5


def test_evm_toolbar_is_excel_plus_enlarge_no_data_toggle(client: TestClient) -> None:
    """The tables ARE their own data drawer: ⛶ on all four shells, ⤓ only where a LIVE export
    serves the panel's data (worst-variance rows have no export endpoint → no dead link)."""
    page = client.get("/evm").text
    # 5 = the four metric shells + the SHARED field-group panel (see the test above). Its ⤓ is
    # deliberately absent while UNGROUPED: /export/xlsx/field-forecast REQUIRES a field (no
    # field → 422), so an ungrouped panel carries no data-export and gets no Excel glyph.
    assert page.count("⛶ ENLARGE") == 5
    assert page.count("⤓ EXCEL") == 3
    assert page.count("⤓ EXCEL") == len(re.findall(r'<div class=panel data-export="', page))
    assert "▦ DATA" not in page
    # schedule + cost panels export the existing EVM workbook; compliance panel exports the
    # per-schedule analysis workbook (its Baseline-compliance sheet)
    assert page.count('data-export="/export/xlsx/evm"') == 2
    assert 'data-export="/export/xlsx/analysis/Project5"' in page
    # the toolbar behavior script (delegated listeners — no inline handlers under strict CSP)
    assert "/static/panelkit.js" in page


def test_evm_excel_targets_are_live_endpoints(client: TestClient) -> None:
    """Every ⤓ EXCEL destination on the page answers 200 — never a dead link (rank-4 law)."""
    page = client.get("/evm").text
    urls = set(re.findall(r'data-export="([^"]+)"', page))
    assert urls, "no export URLs found on /evm"
    for url in urls:
        assert client.get(url).status_code == 200, url


def test_evm_threshold_legend_and_tips_kept_verbatim(client: TestClient) -> None:
    """The legend + explainer panels survive the reshell untouched (never remove visuals)."""
    page = client.get("/evm").text
    assert page.count("How these PASS / FAIL / N&#47;A results are scored") == 2
    assert "Two SPI(t) methods are shown" in page
    assert "What these EVM numbers mean" in page


def test_field_group_panel_renders_on_evm_and_forecast(client: TestClient) -> None:
    """The shared per-field group panel (ADR-0179) renders on BOTH routes (rank-4 risk note)."""
    for route in ("/evm", "/forecast"):
        page = client.get(route).text
        assert "Execution metrics by field group" in page, route
