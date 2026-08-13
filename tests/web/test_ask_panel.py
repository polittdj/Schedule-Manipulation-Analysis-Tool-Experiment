"""The Ask-the-AI panel (ADR-0392): no length limit, whole-workbook evidence, Excel export.

Three operator-reported defects, one panel:

1. with 31 versions loaded the model answered that it could see **two** — because the fact base it
   was handed described the newest version plus the latest pair, and nothing said otherwise;
2. the question box silently truncated at 500 characters, so a long forensic question reached the
   model as a fragment;
3. an answer could be read on screen and not exported — there was no route to get it into a report.
"""

from __future__ import annotations

import datetime as dt
import io
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.importers import parse_mspdi
from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"
_FIRST_DATA_DATE = dt.datetime(2026, 4, 15)  # inside golden Project5's own window


def _session(n: int) -> SessionState:
    """A session holding ``n`` synthetic monthly versions of the golden project."""
    st = SessionState()
    base = parse_mspdi(GOLDEN / "Project5.mspdi.xml")
    for i in range(n):
        label = f"IPMR_v{i + 1:02d}.mpp"
        st.schedules[label] = base.model_copy(
            update={
                "name": label,
                "source_file": label,
                "status_date": _FIRST_DATA_DATE + dt.timedelta(days=21 * i),
            }
        )
    return st


def _client(n: int) -> TestClient:
    return TestClient(create_app(_session(n)))


def _sheets(payload: bytes) -> dict[str, str]:
    """The workbook's sheet XML by sheet order (``sheet1``…) — the renderer writes inline
    strings, so a substring check against the sheet XML is a real content assertion."""
    zf = zipfile.ZipFile(io.BytesIO(payload))
    return {
        name.rsplit("/", 1)[-1].split(".")[0]: zf.read(name).decode()
        for name in zf.namelist()
        if name.startswith("xl/worksheets/")
    }


# --- 1. the whole workbook reaches the evidence ------------------------------------------------


def test_a_31_version_workbook_answers_with_31_version_evidence() -> None:
    """THE regression. Before ADR-0392 the shown facts named the newest version and the latest
    pair; a model reading them correctly reported it could see two files."""
    client = _client(31)
    resp = client.post("/api/ask", data={"question": "Is the project improving over time?"})
    assert resp.status_code == 200
    texts = [f["text"] for f in resp.json()["facts"]]
    assert any(
        t.startswith("WORKBOOK POPULATION: 31 schedule version(s) are loaded") for t in texts
    )
    assert any(t.startswith("S-CURVE SERIES across all 31 loaded version(s)") for t in texts)
    assert any(t.startswith("S-CURVE TREND across the 31 readable version(s)") for t in texts)
    assert any(t.startswith("SCHEDULE-LOGIC FINISH SERIES across 31 version(s)") for t in texts)
    series = next(t for t in texts if t.startswith("S-CURVE SERIES"))
    for i in range(1, 32):  # every loaded file carries a point in the series
        assert f"IPMR_v{i:02d}.mpp" in series


def test_a_single_version_session_gets_no_series_facts() -> None:
    """One file is not a series — the single-version facts already say which file they describe."""
    texts = [
        f["text"]
        for f in _client(1).post("/api/ask", data={"question": "How is it going?"}).json()["facts"]
    ]
    assert not any(t.startswith("WORKBOOK POPULATION") for t in texts)


# --- 2. no length limit ------------------------------------------------------------------------


def test_a_long_question_is_not_truncated() -> None:
    """The old ``[:500]`` cut the question mid-sentence and the model answered the fragment."""
    client = _client(2)
    tail = "AND FINALLY name the driving activity."
    question = "Why is the finish slipping? " + ("padding context. " * 400) + tail
    assert len(question) > 6000
    resp = client.post("/api/ask", data={"question": question})
    assert resp.status_code == 200
    record = client.app.state.session.last_ask  # type: ignore[attr-defined]
    assert record is not None
    assert record.question == question.strip()
    assert record.question.endswith(tail)
    assert len(record.question) == len(question.strip())


def test_the_question_box_is_an_unbounded_textarea() -> None:
    page = _client(2).get("/").text
    assert "<textarea id=askInput" in page
    assert "maxlength" not in page.split("id=askInput")[1][:400]
    assert "no length limit" in page


@pytest.mark.parametrize("url", ["/api/ask", "/api/ask/IPMR_v01.mpp"])
def test_an_empty_question_is_still_rejected(url: str) -> None:
    """Removing the cap must not remove the empty check."""
    assert _client(2).post(url, data={"question": "   "}).status_code == 422


# --- 3. the answer is exportable ---------------------------------------------------------------


def test_the_answer_and_its_evidence_export_to_excel() -> None:
    client = _client(31)
    question = "Look at the S-Curve for each of the 31 .mpp files. Is the project improving?"
    assert client.post("/api/ask", data={"question": question}).status_code == 200

    resp = client.get("/export/xlsx/ask")
    assert resp.status_code == 200
    assert "ask-the-ai.xlsx" in resp.headers["content-disposition"]
    sheets = _sheets(resp.content)
    assert len(sheets) == 3
    assert question in sheets["sheet1"]  # the question travels with the answer
    assert "AI can err" in sheets["sheet1"]  # the standing disclaimer rides the export
    assert "WORKBOOK POPULATION: 31 schedule version(s)" in sheets["sheet2"]
    for i in range(1, 32):
        assert f"IPMR_v{i:02d}.mpp" in sheets["sheet2"]
    assert "UniqueID" in sheets["sheet3"]  # every fact resolves to file + UID + activity


def test_the_export_names_a_missing_answer_rather_than_blanking_it() -> None:
    """Law 2 at the export boundary: with no live model the Answer cell says WHY it is empty."""
    client = _client(2)
    client.post("/api/ask", data={"question": "Anything?"})
    sheet = _sheets(client.get("/export/xlsx/ask").content)["sheet1"]
    assert "no model answer" in sheet
    assert "the cited facts sheet is the engine's own answer" in sheet


def test_the_driving_path_result_exports_too() -> None:
    """One output box, one export button — the engine result is exportable like the AI answer."""
    client = _client(2)
    uid = next(iter(client.app.state.session.schedules.values())).tasks[3].unique_id  # type: ignore[attr-defined]
    assert client.get(f"/api/driving-path?uid={uid}").status_code == 200
    sheet = _sheets(client.get("/export/xlsx/ask").content)["sheet1"]
    assert "Driving path (engine, no AI)" in sheet
    assert f"Driving path to UID {uid}" in sheet


def test_exporting_before_asking_is_a_clear_refusal_not_an_empty_file() -> None:
    resp = _client(2).get("/export/xlsx/ask")
    assert resp.status_code == 422
    assert "ask a question first" in resp.json()["error"]


def test_the_export_also_renders_as_word() -> None:
    client = _client(2)
    client.post("/api/ask", data={"question": "Anything?"})
    assert client.get("/export/docx/ask").status_code == 200
    assert client.get("/export/pdf/ask").status_code == 404  # unchanged format guard


def test_the_export_links_are_in_the_panel() -> None:
    page = _client(2).get("/").text
    assert "/export/xlsx/ask" in page and "/export/docx/ask" in page
    # hidden until an answer exists — the panel never offers a dead link
    assert "id=askExports class=ask-exports hidden" in page


def test_a_wipe_clears_the_recorded_exchange() -> None:
    """The record is session state and holds the operator's question; a wipe must take it."""
    st = _session(2)
    client = TestClient(create_app(st))
    client.post("/api/ask", data={"question": "Anything?"})
    assert st.last_ask is not None
    st.reset()
    assert st.last_ask is None
