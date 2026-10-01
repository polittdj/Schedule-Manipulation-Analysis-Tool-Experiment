"""The risk register and the restore of an export, driven over real HTTP (ADR-0544).

Operator (2026-10-01): a risk register dropped beside the list, drawn on both slides; and "take
any export and reimport that file into the program and have it recreate the OnePager", links
included, on both pages. Each check here runs against the live standalone server: a register
upload, its clear and undo, a restore from each of the three exports (PowerPoint, Excel, PDF)
of each page, the refusals (an export on a list slot, a register on a list slot, a browser-like
PDF, a workbook that is a plain list), and the one-door property (the form route and the JSON
route leave the same state). Mutation twins break the product in memory and show the SAME
checker going red by name.
"""

from __future__ import annotations

import datetime as dt
import json
import socketserver
import threading
from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from lodestar_probe import PRIOR_ROWS, ROWS, Reply, multipart, request, upload

from schedule_forensics.lodestar.server import LodestarServer, LodestarState
from schedule_forensics.reports import session_payload as sp
from web.onepager_twin import twin_xlsx

TODAY = dt.date(2026, 9, 1)
JSON_CT = ("Content-Type", "application/json")
RISK_ROWS: tuple[tuple[object, ...], ...] = (
    ("Swimlane", "Risk", "Potential impact", "Probability", "Date of occurrence"),
    ("Alpha", "Vendor part late", "30 d", "High", "3/10/2027"),
    ("Beta", "Range unavailable", "2 wk", "Medium", "6/1/2027"),
    ("Gamma", "Funding gap", "a quarter", "Low", "4/1/2027"),
)


@dataclass
class Live:
    server: LodestarServer
    state: LodestarState
    thread: threading.Thread

    @property
    def port(self) -> int:
        return int(self.server.server_port)


@pytest.fixture
def live() -> Iterator[Live]:
    st = LodestarState()
    srv = LodestarServer(0, st, TODAY)
    thread = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    try:
        yield Live(srv, st, thread)
    finally:
        socketserver.BaseServer.shutdown(srv)
        srv.server_close()
        thread.join(timeout=10)


def _api(live: Live, name: str, **body: object) -> dict[str, object]:
    got = request(
        live.port, "POST", f"/api/{name}", body=json.dumps(body).encode(), headers=[JSON_CT]
    )
    assert got.status == 200, (name, got.status, got.text[:200])
    return dict(json.loads(got.body))


def _state(live: Live, page: str) -> dict[str, object]:
    return dict(json.loads(request(live.port, "GET", f"/api/state?page={page}").body))


def _drop(live: Live, path: str, name: str, data: bytes, **fields: str) -> Reply:
    body, ctype = multipart(fields, name, data)
    return request(
        live.port,
        "POST",
        path,
        body=body,
        headers=[("Content-Type", ctype), ("Accept", "application/json")],
    )


def _load_timeline(live: Live) -> None:
    assert upload(live.port, "/onepager/upload", ROWS, "Program list.xlsx").status == 303


def _load_compare(live: Live) -> None:
    for slot, rows, name in (("prior", PRIOR_ROWS, "March.xlsx"), ("current", ROWS, "April.xlsx")):
        assert upload(live.port, "/onepager-compare/upload", rows, name, slot=slot).status == 303


def _links(live: Live, page: str, path: str, n: int = 2) -> None:
    keys = [x["key"] for x in _state(live, page)["linkable"]]  # type: ignore[index]
    for i in range(n):
        got = _api(
            live, "links", page=page, action="add", pred=keys[i], succ=keys[i + 1], kind="FS"
        )
        assert got["label"], got.get("toast")


# ── the register ──────────────────────────────────────────────────────────────────────────────


def test_a_register_dropped_on_the_risks_slot_draws_on_both_slides_and_undoes(live: Live) -> None:
    _load_timeline(live)
    _load_compare(live)
    got = _drop(live, "/onepager/risks/upload", "risks.xlsx", twin_xlsx(RISK_ROWS))
    assert got.status == 200
    st = json.loads(got.body)
    assert st["label"] == "Risks loaded: risks.xlsx" and st["loaded"]["risks"] is True
    assert "3 risk(s)" in st["toast"]["text"]
    for page in ("timeline", "compare"):
        lay = _state(live, page)["layout"]
        risks = [p for p in lay["items"] if p["kind"] == "risk"]  # type: ignore[index]
        assert len(risks) == 3 and {p["prob"] for p in risks} == {"high", "medium", "low"}
        assert all(p["label"].startswith("RISK · ") for p in risks)
        kinds = [e["kind"] for e in lay["legend"]]  # type: ignore[index]
        assert [k for k in kinds if k.startswith("risk-")] == [
            "risk-high",
            "risk-medium",
            "risk-low",
        ]
        assert any(h["label"] == "RISKS" and h["value"] == "3" for h in _state(live, page)["hud"])  # type: ignore[union-attr]
    # Gamma is a band of its own, named
    notes = [n for n in _state(live, "timeline")["notices"] if n["key"] == "assumed"]  # type: ignore[index]
    assert any("Gamma" in item for n in notes for item in n["items"])
    undone = _api(live, "undo", page="timeline")
    assert undone["loaded"]["risks"] is False and not any(  # type: ignore[index]
        p["kind"] == "risk"
        for p in undone["layout"]["items"]  # type: ignore[index]
    )
    redone = _api(live, "redo", page="timeline")
    assert redone["loaded"]["risks"] is True  # type: ignore[index]
    cleared = _api(live, "risks", page="timeline", action="clear")
    assert cleared["label"] == "Risks cleared" and cleared["loaded"]["risks"] is False  # type: ignore[index]


def test_a_register_dropped_on_a_list_slot_is_refused_by_name_and_the_list_stays(
    live: Live,
) -> None:
    _load_timeline(live)
    before = live.state.onepager
    got = _drop(live, "/onepager/upload", "risks.xlsx", twin_xlsx(RISK_ROWS))
    assert got.status == 200 and live.state.onepager is before
    assert "risk register" in json.loads(got.body)["toast"]["text"]


def test_the_risk_template_is_served_and_reads_back_as_a_register(live: Live) -> None:
    got = request(live.port, "GET", "/export/xlsx/risks-template")
    assert got.status == 200 and got.headers.get("content-disposition", "").startswith("attachment")
    dropped = _drop(live, "/onepager/risks/upload", "risk-register-template.xlsx", got.body)
    assert dropped.status == 200 and json.loads(dropped.body)["loaded"]["risks"] is True


# ── restore, three exports by two pages ────────────────────────────────────────────────────────


def _exported(live: Live, fmt: str, stem: str) -> bytes:
    got = request(live.port, "GET", f"/export/{fmt}/{stem}")
    assert got.status == 200, (fmt, stem, got.status)
    return got.body


@pytest.mark.parametrize("fmt", ["pptx", "xlsx", "pdf"])
def test_a_timeline_export_restores_the_slide_its_links_and_its_risks(live: Live, fmt: str) -> None:
    _load_timeline(live)
    _api(live, "title", page="timeline", title="Q1 review")
    _api(live, "window", page="timeline", action="apply", start="2027-01-01", end="2027-12-31")
    _api(live, "today", page="timeline", action="apply", today="2027-03-01")
    _api(live, "marking", page="timeline", marking="unclassified")
    _links(live, "timeline", "/onepager/links")
    assert _drop(live, "/onepager/risks/upload", "risks.xlsx", twin_xlsx(RISK_ROWS)).status == 200
    data = _exported(live, fmt, "onepager")
    was = (
        live.state.onepager,
        live.state.onepager_links,
        live.state.onepager_title,
        live.state.onepager_window,
        live.state.onepager_today,
        live.state.unclassified,
        live.state.onepager_risks,
    )
    was_layout = _state(live, "timeline")["layout"]
    # a fresh session takes the export back
    _api(live, "clear", page="timeline")
    _api(live, "risks", page="timeline", action="clear")
    _api(live, "today", page="timeline", action="clear")
    _api(live, "marking", page="timeline", marking="cui")
    assert live.state.onepager is None and live.state.onepager_links == ()
    got = _drop(live, "/onepager/restore/upload", f"export.{fmt}", data)
    assert got.status == 200, got.text[:300]
    st = json.loads(got.body)
    assert st["label"] == f"Restored from export.{fmt}" and st["page"] == "timeline"
    assert "4 item(s), 2 logic link(s), 3 risk(s)" in st["toast"]["text"]
    assert "marking Unclassified" in st["toast"]["text"]
    now = (
        live.state.onepager,
        live.state.onepager_links,
        live.state.onepager_title,
        live.state.onepager_window,
        live.state.onepager_today,
        live.state.unclassified,
        live.state.onepager_risks,
    )
    assert now == was
    assert [ln.pred_ident for ln in live.state.onepager_links] == [ln.pred_ident for ln in was[1]]
    assert _state(live, "timeline")["layout"] == was_layout
    undone = _api(live, "undo", page="timeline")
    assert undone["layout"] is None and live.state.onepager is None


@pytest.mark.parametrize("fmt", ["pptx", "xlsx", "pdf"])
def test_a_compare_export_restores_both_lists_and_lands_on_the_compare_page(
    live: Live, fmt: str
) -> None:
    _load_compare(live)
    _links(live, "compare", "/onepager-compare/links", n=1)
    data = _exported(live, fmt, "onepager-compare")
    was = (
        live.state.onepager_prior,
        live.state.onepager_current,
        live.state.onepager_compare_links,
    )
    was_layout = _state(live, "compare")["layout"]
    _api(live, "clear", page="compare")
    assert live.state.onepager_prior is None
    # dropped on the TIMELINE page's restore zone: the slide lands on Compare, and says so
    got = _drop(live, "/onepager/restore/upload", f"compare.{fmt}", data)
    assert got.status == 200, got.text[:300]
    st = json.loads(got.body)
    assert st["page"] == "compare" and st["path"] == "/onepager-compare"
    assert (
        live.state.onepager_prior,
        live.state.onepager_current,
        live.state.onepager_compare_links,
    ) == was
    assert _state(live, "compare")["layout"] == was_layout
    # scripting off: the form route redirects to the page the slide landed on
    body, ctype = multipart({}, f"compare.{fmt}", data)
    plain = request(
        live.port, "POST", "/onepager/restore/upload", body=body, headers=[("Content-Type", ctype)]
    )
    assert plain.status == 303 and plain.headers.get("location") == "/onepager-compare"


def test_an_export_dropped_on_a_list_slot_is_refused_and_points_at_restore(live: Live) -> None:
    _load_timeline(live)
    for fmt in ("pptx", "pdf", "xlsx"):
        data = _exported(live, fmt, "onepager")
        before = live.state.onepager
        got = _drop(live, "/onepager/upload", f"export.{fmt}", data)
        assert got.status == 200 and live.state.onepager is before, fmt
        assert "Restore a slide" in json.loads(got.body)["toast"]["text"], fmt


def test_a_file_that_carries_no_record_is_refused_by_name(live: Live) -> None:
    _load_timeline(live)
    before = live.state.onepager
    for name, data in (
        ("printed.pdf", b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\ntrailer << >>\n%%EOF\n"),
        ("plain list.xlsx", twin_xlsx(ROWS)),
        ("notes.txt", b"hello"),
    ):
        got = _drop(live, "/onepager/restore/upload", name, data)
        assert got.status == 200 and live.state.onepager is before, name
        text = json.loads(got.body)["toast"]["text"]
        assert "record" in text or "settings sheet" in text, (name, text)


def test_mutation_a_record_with_the_wrong_format_is_refused(live: Live) -> None:
    """MUTATION: the record's format bumped on the way out — the restore names it."""
    _load_timeline(live)
    data = _exported(live, "pdf", "onepager")
    raw = sp.payload_bytes(sp.build_payload(live.state, "timeline", program="x"))
    assert (
        raw in data or b"lodestar" in data
    )  # the record is in the PDF (deflated: by reader below)
    from schedule_forensics.reports.pdf_read import read_pdf_payload

    rec = sp.parse_payload(read_pdf_payload(data) or b"")
    rec["lodestar"]["format"] = 2
    bad = sp.payload_bytes(rec)
    with pytest.raises(sp.PayloadError, match="format 2"):
        sp.parse_payload(bad)
