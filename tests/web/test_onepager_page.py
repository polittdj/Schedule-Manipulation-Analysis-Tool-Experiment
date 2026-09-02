"""The /onepager page through the app: intake, the decisions it shows, the exports (ADR-0446)."""

from __future__ import annotations

import datetime as dt
import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.reports.xlsx_read import read_xlsx
from schedule_forensics.web.app import SessionState, create_app
from schedule_forensics.web.i18n import catalog_for
from web.onepager_twin import TWIN_ROWS, twin_xlsx

TODAY = dt.date(2026, 9, 1)


@pytest.fixture
def state() -> SessionState:
    st = SessionState()
    st.onepager_today = TODAY
    return st


@pytest.fixture
def client(state: SessionState) -> TestClient:
    return TestClient(create_app(state))


def _upload(client: TestClient, data: bytes, name: str = "Politte_PowerPoint_FINAL.xlsx") -> str:
    r = client.post(
        "/onepager/upload",
        files={"file": (name, data, "application/octet-stream")},
        follow_redirects=False,
    )
    assert r.status_code == 303 and r.headers["location"] == "/onepager"
    return client.get("/onepager").text


def _layout_block(page: str) -> dict:
    m = re.search(r'<script id=opData type="application/json">(.*?)</script>', page, re.S)
    assert m, "the layout JSON block is missing"
    return json.loads(m.group(1))


def test_the_empty_page_explains_the_three_columns_and_offers_the_template(
    client: TestClient,
) -> None:
    page = client.get("/onepager").text
    assert "No list loaded" in page and "id=opDrop" in page and 'accept=".xlsx"' in page
    assert 'href="/export/xlsx/onepager-template"' in page and "/static/onepager.js" in page
    assert "opData" not in page  # nothing to paint yet
    t = client.get("/export/xlsx/onepager-template")
    assert t.status_code == 200 and t.headers["content-type"].endswith("spreadsheetml.sheet")
    rows = next(iter(read_xlsx(t.content).values()))
    assert any(r[:3] == ["Swimlane Name", "Task", "Date"] for r in rows if len(r) >= 3)


def test_upload_draws_the_slide_and_names_every_decision(client: TestClient) -> None:
    page = _upload(client, twin_xlsx(TWIN_ROWS))
    assert "Loaded 16 item(s) from Politte_PowerPoint_FINAL.xlsx; 1 row(s) skipped." in page
    assert "role=alert" in page  # a skipped row is reported as a failure, never a success
    assert "7 swimlanes, 6 milestones and 10 activities on one slide" in page
    assert "row 23" in page and "10/122/2026" in page and "Blue Origin On-Dock" in page
    assert "merged into" in page and "GRC-(MCaRR-2)" in page  # the spacing-variant swimlane
    assert "placed under" in page  # the row that inherited its swimlane
    lay = _layout_block(page)
    assert lay["title"] == "Politte PowerPoint FINAL" and len(lay["items"]) == 16
    assert lay["today_iso"] == "2026-09-01" and lay["today_x"] is not None
    assert len(lay["lanes"]) == 7 and lay["items"][0]["label"].endswith(")")
    # the panel contract: export wired, ▦ DATA drawer with the parsed rows, provenance chip
    assert 'data-export="/export/xlsx/onepager"' in page and "data-sf-data" in page
    assert "<div class=sf-drawer hidden>" in page and page.count("<tr><td>") == 16
    assert "SOURCE: Politte_PowerPoint_FINAL.xlsx · TODAY 2026-09-01" in page
    assert 'href="/export/pptx/onepager"' in page


def test_operator_text_never_becomes_markup(client: TestClient) -> None:
    hostile = (
        ("Swimlane Name", "Task", "Date"),
        ("<b>Lane</b> & co", "<script>alert(1)</script>", "1/1/2027 - 2/1/2027"),
        ("<b>Lane</b> & co", "<img src=x onerror=alert(2)>", "3/1/2027"),
    )
    page = _upload(client, twin_xlsx(hostile), "x<y>&z.xlsx")
    # no TAG can form: the raw "<" never reaches the HTML (entities) or the JSON (\u003c);
    # the attribute text itself survives inside the escaped JSON, inert
    assert "<script>alert(1)" not in page and "<img src=x" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page
    lay = _layout_block(page)
    assert lay["items"][0]["name"] == "<script>alert(1)</script>"  # the data is intact…
    assert "\\u003c" in re.search(
        r'id=opData type="application/json">(.*?)</script>', page, re.S
    ).group(1)  # …and inert
    pptx = client.get("/export/pptx/onepager")
    assert pptx.status_code == 200
    with zipfile.ZipFile(io.BytesIO(pptx.content)) as zf:
        ET.fromstring(zf.read("ppt/slides/slide1.xml"))  # well-formed under the hostile names


def test_the_powerpoint_export_is_the_same_slide(client: TestClient, state: SessionState) -> None:
    assert (
        client.get("/export/pptx/onepager").status_code == 422
    )  # nothing loaded: refused, not empty
    page = _upload(client, twin_xlsx(TWIN_ROWS))
    lay = _layout_block(page)
    r = client.get("/export/pptx/onepager")
    assert r.status_code == 200
    assert (
        r.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    assert (
        r.headers["content-disposition"] == 'attachment; filename="Politte_PowerPoint_FINAL.pptx"'
    )
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        slide = zf.read("ppt/slides/slide1.xml").decode()
    assert slide.count('name="Milestone: ') == sum(i["milestone"] for i in lay["items"])
    assert slide.count('name="Activity: ') == sum(not i["milestone"] for i in lay["items"])
    assert "Controlled Unclassified Information • CUI" in slide  # the page's own marking
    assert "Source: Politte_PowerPoint_FINAL.xlsx · 16 items · generated 2026-09-01" in slide


def test_the_excel_export_is_the_parsed_list(client: TestClient) -> None:
    assert client.get("/export/xlsx/onepager").status_code == 422
    _upload(client, twin_xlsx(TWIN_ROWS))
    r = client.get("/export/xlsx/onepager")
    assert (
        r.status_code == 200
        and 'filename="one-pager-list.xlsx"' in r.headers["content-disposition"]
    )
    sheets = read_xlsx(r.content)
    assert any("items" in name.lower() for name in sheets)
    assert any("10/122/2026" in c for rows in sheets.values() for row in rows for c in row)
    assert client.get("/export/docx/onepager").status_code == 200
    assert client.get("/export/pdf/onepager").status_code == 404


def test_title_and_clear(client: TestClient) -> None:
    _upload(client, twin_xlsx(TWIN_ROWS))
    r = client.post(
        "/onepager/title",
        data={"title": "  Artemis Integrated Master One-Pager  "},
        follow_redirects=False,
    )
    assert r.status_code == 303
    page = client.get("/onepager").text
    assert _layout_block(page)["title"] == "Artemis Integrated Master One-Pager"
    assert 'value="Artemis Integrated Master One-Pager"' in page
    pptx = client.get("/export/pptx/onepager")
    assert (
        'filename="Artemis_Integrated_Master_One-Pager.pptx"' in pptx.headers["content-disposition"]
    )
    assert client.post("/onepager/clear", follow_redirects=False).status_code == 303
    page = client.get("/onepager").text
    assert "List cleared." in page and "No list loaded" in page and "opData" not in page


def test_a_bad_file_and_a_list_with_no_usable_rows_are_refused_by_name(client: TestClient) -> None:
    page = _upload(client, b"not a workbook", "notes.xlsx")
    assert "Could not read that file" in page and "role=alert" in page and "No list loaded" in page
    only_bad = (
        ("Swimlane Name", "Task", "Date"),
        ("Lane", "Thing", "TBD"),
        ("Lane", "Other", "soon"),
    )
    page = _upload(client, twin_xlsx(only_bad), "bad.xlsx")
    assert "No usable rows in bad.xlsx" in page and "row 2" in page and "row 3" in page
    assert "opData" not in page


def test_the_nav_carries_the_page_on_the_library_rail(client: TestClient) -> None:
    home = client.get("/").text
    assert 'href="/onepager"' in home and "One-Pager Timeline" in home
    for lang in ("es", "fr", "de", "pt"):
        assert "One-Pager Timeline" in catalog_for(lang)


def test_the_page_kicker_resolves_and_the_upload_cap_is_enforced(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import schedule_forensics.web.app as app_mod

    monkeypatch.setattr(app_mod, "_MAX_UPLOAD_BYTES", 64)
    page = _upload(client, twin_xlsx(TWIN_ROWS))
    assert "exceeds the 0 MB cap" in page and "opData" not in page
