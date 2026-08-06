"""The /sra Float-exposure and Risk-flags bars drill, and drills offer EVERY task field.

ADR-0360 (operator 2026-08-06): hovering a segment names its count; clicking it lists the
exact activities it counts through the shared sf-drill grid; the grid's add-column list —
and therefore its Excel export — offers every task-level field the model carries verbatim
from the file (the ADR-0360 STANDARD_FIELDS widening from six fields to the full catalog)
plus every custom field present in the loaded files.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

REPO = Path(__file__).resolve().parents[2]
FIX = REPO / "tests" / "fixtures" / "test_projects"


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    xml = (FIX / "TP4_DataCenter_v1.xml").read_bytes()
    assert c.post("/upload", files={"files": ("TP4_v1.xml", xml, "text/xml")}).status_code == 200
    return c


def test_float_exposure_segments_carry_the_drill_hook_and_a_hover_tip(
    client: TestClient,
) -> None:
    html = client.get("/sra").text
    titles = re.findall(r'class="stack-seg sf-drill"[^>]*data-title="([^"]+)"', html)
    assert "Float exposure — Critical" in titles, "the Critical segment must drill"
    # the hover callout names the segment and its count, and says the click does something
    m = re.search(r'class="stack-seg sf-drill"[^>]*title="Critical: (\d+) — click to list', html)
    assert m, "the segment hover tip must carry the label, the count and the click affordance"
    # the drilled UID set is exactly the counted population
    uids = re.search(r'data-uids="([\d,]+)"[^>]*data-title="Float exposure — Critical"', html)
    assert uids and len(uids.group(1).split(",")) == int(m.group(1))


def test_the_drill_offers_every_model_field_and_exports_the_chosen_ones(
    client: TestClient,
) -> None:
    html = client.get("/sra").text
    uids = re.search(r'data-uids="([\d,]+)"[^>]*data-title="Float exposure — Critical"', html)
    assert uids is not None
    data = client.get(
        "/api/activities/drill",
        params={"file": "TP4_v1.xml", "uids": uids.group(1), "title": "t"},
    ).json()
    for field in (
        "Baseline Finish",
        "Total Slack (d)",
        "Deadline",
        "Notes",
        "Work (h)",
        "Manually Scheduled",
        "Outline Number",
    ):
        assert field in data["fields"], f"the drill must offer {field!r} as an addable column"
    # a value the fixture stores renders verbatim; one it does not stays None — never a 0
    row0 = data["rows"][0]["fields"]
    assert row0.get("Baseline Finish"), "the fixture stores baselines — the value must surface"
    assert row0.get("Total Slack (d)") is None, "no stored slack in the fixture — None, not 0"
    r = client.get(
        "/export/xlsx/activities-drill",
        params={
            "file": "TP4_v1.xml",
            "uids": uids.group(1),
            "cols": "Baseline Finish,Total Slack (d)",
            "title": "t",
        },
    )
    assert r.status_code == 200 and len(r.content) > 500
    assert b"Baseline Finish" in _workbook_bytes(r.content)


def _workbook_bytes(xlsx: bytes) -> bytes:
    import zipfile
    from io import BytesIO

    with zipfile.ZipFile(BytesIO(xlsx)) as zf:
        return b"".join(zf.read(n) for n in zf.namelist() if n.endswith(".xml"))
