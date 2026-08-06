"""The ⤓ EXCEL export reuses the page's last SSI run (ADR-0360).

``/export/{fmt}/sra`` used to re-run the Monte-Carlo AND the full one-at-a-time sweep on
every click — measured at 140 s on the committed 2,125-task SRA schedule, during which the
browser shows nothing at all: the operator-reported "Export to Excel does nothing". When the
page has already run on identical inputs the export must hand back EXACTLY that result — which
is also a fidelity fix: the workbook now carries the run the operator is looking at (their
chosen iteration count included) instead of a silently different hardcoded-2000 re-run.

The reuse key is the full resolved-input identity; any input edit must invalidate it — served
stale numbers after an edit would be worse than the latency ever was.
"""

from __future__ import annotations

import zipfile
from io import BytesIO
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


def _workbook_text(content: bytes) -> str:
    with zipfile.ZipFile(BytesIO(content)) as zf:
        return "".join(
            zf.read(n).decode("utf-8", "replace")
            for n in zf.namelist()
            if n.startswith("xl/") and n.endswith(".xml")
        )


def test_export_hands_back_the_pages_last_run_not_a_rerun(client: TestClient) -> None:
    """After a 300-iteration page run, the workbook says 300 — and never the old 2000 default.

    Iteration counts render as numeric cells (``<v>300</v>``); the fixture's dates are shared
    STRINGS, so a bare ``>2000<`` numeric match can only come from a recomputed run."""
    assert client.get("/api/sra/ssi", params={"iterations": 300}).status_code == 200
    r = client.get("/export/xlsx/sra")
    assert r.status_code == 200
    text = _workbook_text(r.content)
    assert ">300<" in text, "the export did not reuse the page's 300-iteration run"
    assert ">2000<" not in text, "the export re-ran the model instead of reusing the page's run"


def test_an_input_edit_invalidates_the_reuse(client: TestClient) -> None:
    """Editing a Risk Ranking Factor after the run changes the reuse key, so the export must
    recompute (at its own 2000-iteration default) rather than serve the stale 300-run."""
    assert client.get("/api/sra/ssi", params={"iterations": 300}).status_code == 200
    assert client.post("/sra/factor", data={"uids": "2", "factor": 5}).status_code in (200, 303)
    r = client.get("/export/xlsx/sra")
    assert r.status_code == 200
    text = _workbook_text(r.content)
    assert ">2000<" in text, "an edited input must invalidate the cached run"
