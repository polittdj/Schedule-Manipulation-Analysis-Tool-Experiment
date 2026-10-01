"""The record every export carries, and the restore that reads it back (ADR-0544).

The operator (2026-10-01): "take any export and reimport that file into the program and have it
recreate the OnePager … If the PowerPoint has logic that has been previously established I want
that logic to be recreated". The record holds each list's rows AS READ, the links by key and by
identity, the risk register's rows and the settings; a restore puts them back THROUGH THE SAME
PARSERS a drop goes through — so the restored document is EQUAL (dataclass ==) to the exported
one, keys included, and every link resolves. The plan attack measured this over 53 sheet
variants (hand the rows to the parser; a rebuilt workbook mangled 3 of them).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any

import pytest

from schedule_forensics.reports import session_payload as sp
from schedule_forensics.reports.onepager import OnePagerDoc
from schedule_forensics.reports.onepager_links import Link
from schedule_forensics.reports.onepager_risks import RiskDoc, parse_risk_workbook
from schedule_forensics.reports.xlsx import render_xlsx
from schedule_forensics.reports.xlsx_read import read_xlsx_numbered
from schedule_forensics.web.onepager_actions import read_list
from web.onepager_twin import twin_xlsx

HEAD = ("Swimlane Name", "Task", "Start", "Finish", "Complete")
#: A list with every quirk the parser names: a spacer row, an inherited swimlane, a skipped row
#: (unreadable date), a repeated name (keys with dates), a month-only date, an unknown status word.
ROWS: tuple[tuple[object, ...], ...] = (
    HEAD,
    ("Alpha", "Design Review", "1/15/2027", "1/15/2027", "Complete"),
    ("", "Build", "2/1/2027", "4/15/2027", "In work"),
    (),
    ("Beta", "Test", "5/1/2027", "6/30/2027", ""),
    ("Beta", "Test", "7/1/2027", "7/15/2027", "Maybe"),
    ("Beta", "Ship", "soon", "", ""),
    ("Beta", "Review", "Jan 2028", "", ""),
)
PRIOR_ROWS: tuple[tuple[object, ...], ...] = (
    HEAD,
    ("Alpha", "Design Review", "1/15/2027", "1/15/2027", ""),
    ("Alpha", "Build", "2/1/2027", "3/31/2027", ""),
    ("Beta", "Test", "5/1/2027", "6/30/2027", ""),
)
RISK_ROWS: tuple[tuple[object, ...], ...] = (
    ("Swimlane", "Risk", "Potential impact", "Probability", "Date of occurrence"),
    ("Alpha", "Vendor part late", "30 d", "High", "3/10/2027"),
    ("Beta", "Range unavailable", "2 wk", "medium", "6/1/2027"),
    ("Beta", "Weather hold", "5", "Low", "7/20/2027"),
)


@dataclass
class Session:
    """A session double carrying the One-Pager attributes (what LODESTAR's state carries)."""

    onepager: OnePagerDoc | None = None
    onepager_title: str = ""
    onepager_msg: str | None = None
    onepager_is_error: bool = False
    onepager_today: dt.date | None = None
    onepager_window: tuple[dt.date, dt.date] | None = None
    onepager_prior: OnePagerDoc | None = None
    onepager_current: OnePagerDoc | None = None
    onepager_compare_title: str = ""
    onepager_compare_msg: str | None = None
    onepager_compare_is_error: bool = False
    onepager_compare_window: tuple[dt.date, dt.date] | None = None
    onepager_links: tuple[Link, ...] = ()
    onepager_compare_links: tuple[Link, ...] = ()
    onepager_links_msg: str | None = None
    onepager_links_is_error: bool = False
    onepager_compare_links_msg: str | None = None
    onepager_compare_links_is_error: bool = False
    onepager_cache: dict[str, Any] = field(default_factory=dict)
    onepager_risks: RiskDoc | None = None
    unclassified: bool = False


def _doc(rows: tuple[tuple[object, ...], ...], name: str, **kw: Any) -> OnePagerDoc:
    got = read_list(twin_xlsx(rows, **kw), name, max_bytes=10**8)
    assert not isinstance(got, str), got
    return got


def _risks() -> RiskDoc:
    sheets = read_xlsx_numbered(twin_xlsx(RISK_ROWS), max_columns=8, booleans_as_text=True)
    return parse_risk_workbook(sheets, "risks.xlsx")


def _timeline() -> Session:
    st = Session(onepager=_doc(ROWS, "Program list.xlsx", omit_blank=True))
    keys = [it.key for it in st.onepager.items]
    labels = {it.key: it.name for it in st.onepager.items}
    idents = sp.list_idents(st.onepager)
    st.onepager_links = (
        Link(
            keys[0],
            keys[1],
            "FS",
            labels[keys[0]],
            labels[keys[1]],
            idents[keys[0]],
            idents[keys[1]],
        ),
        Link(
            keys[1],
            keys[2],
            "SS",
            labels[keys[1]],
            labels[keys[2]],
            idents[keys[1]],
            idents[keys[2]],
        ),
    )
    st.onepager_title = "Program — Q1"
    st.onepager_window = (dt.date(2027, 1, 1), dt.date(2027, 12, 31))
    st.onepager_today = dt.date(2027, 3, 1)
    st.unclassified = True
    st.onepager_risks = _risks()
    return st


def _compare() -> Session:
    st = Session(
        onepager_prior=_doc(PRIOR_ROWS, "March.xlsx"),
        onepager_current=_doc(ROWS, "April.xlsx", omit_blank=True),
    )
    keys = [it.key for it in st.onepager_current.items]
    idents = sp.list_idents(st.onepager_current)
    st.onepager_compare_links = (
        Link(keys[0], keys[1], "FS", "a", "b", idents[keys[0]], idents[keys[1]]),
    )
    st.onepager_compare_title = ""
    return st


# ── the record ────────────────────────────────────────────────────────────────────────────────


def test_the_record_holds_the_rows_as_read_the_links_by_identity_and_the_settings() -> None:
    st = _timeline()
    rec = sp.build_payload(st, "timeline", program="LODESTAR 2.1.0", today=st.onepager_today)
    inner = rec["lodestar"]
    assert (
        inner["format"] == 1
        and inner["page"] == "timeline"
        and inner["program"] == "LODESTAR 2.1.0"
    )
    assert inner["title"] == "Program — Q1" and inner["window"] == ["2027-01-01", "2027-12-31"]
    assert inner["today"] == "2027-03-01" and inner["marking"] == "unclassified"
    rows = inner["lists"]["list"]["rows"]
    assert rows[0] == [1, list(HEAD)] and [n for n, _c in rows] == [1, 2, 3, 5, 6, 7, 8]
    assert rows[5] == [7, ["Beta", "Ship", "soon"]]  # the SKIPPED row travels too, as read
    assert inner["lists"]["list"]["source"] == "Program list.xlsx"
    assert [ln["kind"] for ln in inner["links"]] == ["FS", "SS"]
    assert len(inner["links"][0]["pred_ident"]) == 4
    assert inner["risks"]["source"] == "risks.xlsx" and len(inner["risks"]["rows"]) == 4
    assert "tasks" not in sp.payload_bytes(rec).decode()


def test_the_bytes_are_deterministic_and_parse_back_to_the_record() -> None:
    st = _timeline()
    rec = sp.build_payload(st, "timeline", program="p")
    a, b = sp.payload_bytes(rec), sp.payload_bytes(sp.build_payload(st, "timeline", program="p"))
    assert a == b and sp.parse_payload(a) == rec


@pytest.mark.parametrize(
    "bad,why",
    [
        (b"not json", "not JSON"),
        (b'{"other": 1}', "no LODESTAR slide"),
        (b'{"lodestar": {"format": 9, "page": "timeline", "lists": {}}}', "format 9"),
        (b'{"lodestar": {"format": 1, "page": "x", "lists": {}}}', "no page"),
        (
            b'{"lodestar": {"format": 1, "page": "timeline", '
            b'"lists": {"list": {"rows": [[1, "x"]]}}}}',
            "not rows",
        ),
    ],
)
def test_a_record_that_is_not_one_is_refused_by_name(bad: bytes, why: str) -> None:
    with pytest.raises(sp.PayloadError, match=why):
        sp.parse_payload(bad)


# ── the restore ───────────────────────────────────────────────────────────────────────────────


def test_a_restored_timeline_is_equal_to_the_exported_one_links_and_risks_included() -> None:
    st = _timeline()
    rec = sp.parse_payload(
        sp.payload_bytes(sp.build_payload(st, "timeline", program="p", today=st.onepager_today))
    )
    back = Session()
    got = sp.restore_payload(back, rec, risks_reader=parse_risk_workbook)
    assert got.page == "timeline" and got.counts == {
        "items": 5,
        "links": 2,
        "risks": 3,
        "not_drawn": 0,
    }
    assert back.onepager == st.onepager  # items, keys, problems, notes, rows — the whole document
    assert back.onepager.problems and back.onepager.notes and back.onepager.completion_notes
    assert back.onepager_links == st.onepager_links
    assert [ln.pred_ident for ln in back.onepager_links] == [
        ln.pred_ident for ln in st.onepager_links
    ]
    assert (back.onepager_title, back.onepager_window, back.onepager_today, back.unclassified) == (
        "Program — Q1",
        (dt.date(2027, 1, 1), dt.date(2027, 12, 31)),
        dt.date(2027, 3, 1),
        True,
    )
    assert back.onepager_risks == st.onepager_risks
    assert "Restored the Timeline slide from Program list.xlsx" in got.message


def test_a_restored_compare_is_equal_to_the_exported_one() -> None:
    st = _compare()
    rec = sp.build_payload(st, "compare", program="p")
    back = Session()
    got = sp.restore_payload(back, rec)
    assert got.page == "compare"
    assert back.onepager_prior == st.onepager_prior and back.onepager_current == st.onepager_current
    assert back.onepager_compare_links == st.onepager_compare_links
    assert back.onepager is None and back.onepager_risks is None


def test_a_link_whose_item_is_gone_is_kept_and_named_not_drawn() -> None:
    st = _timeline()
    rec = sp.build_payload(st, "timeline", program="p")
    rec["lodestar"]["links"].append(
        {
            "pred": "deadbeef",
            "succ": "feedface",
            "kind": "FS",
            "pred_label": "Gone",
            "succ_label": "Too",
            "pred_ident": ["gamma", "gone", "2027-01-01", "2027-01-01"],
            "succ_ident": [],
        }
    )
    back = Session()
    got = sp.restore_payload(back, rec)
    assert len(back.onepager_links) == 3 and got.counts["not_drawn"] == 1
    assert "1 link(s) name an item not in the list" in got.message


def test_a_link_re_binds_by_identity_when_its_key_changed_form() -> None:
    """The stored KEY is stale (another list's) but the identity names exactly one item."""
    st = _timeline()
    rec = sp.build_payload(st, "timeline", program="p")
    ln = rec["lodestar"]["links"][0]
    ln["pred"] = "0000000000000000"
    back = Session()
    sp.restore_payload(back, rec)
    assert back.onepager_links[0].pred == st.onepager_links[0].pred


def test_mutation_a_restore_that_renumbers_rows_is_caught() -> None:
    """MUTATION: the rows re-numbered by position (a rebuilt workbook with the spacer row lost)
    — the restored document is NOT equal: its row numbers, and so its notes, differ."""
    st = _timeline()
    rec = sp.build_payload(st, "timeline", program="p")
    rows = rec["lodestar"]["lists"]["list"]["rows"]
    rec["lodestar"]["lists"]["list"]["rows"] = [
        [i + 1, cells] for i, (_n, cells) in enumerate(rows)
    ]
    back = Session()
    sp.restore_payload(back, rec)
    assert back.onepager != st.onepager
    assert [it.row for it in back.onepager.items] != [it.row for it in st.onepager.items]


# ── the Excel carrier ─────────────────────────────────────────────────────────────────────────


def test_the_record_round_trips_through_the_export_workbooks_sheets() -> None:
    st = _timeline()
    rec = sp.build_payload(st, "timeline", program="p", today=st.onepager_today)
    from schedule_forensics.reports.tableset import TableSet

    data = render_xlsx(TableSet("x", tuple(sp.payload_tables(rec))))
    sheets = read_xlsx_numbered(data, max_columns=13)
    assert set(sheets) >= {
        sp.SETTINGS_SHEET,
        sp.LIST_SHEETS["list"],
        sp.LINKS_SHEET,
        sp.RISKS_SHEET,
    }
    again = sp.payload_from_sheets(sheets)
    back = Session()
    sp.restore_payload(back, again, risks_reader=parse_risk_workbook)
    assert back.onepager == st.onepager and back.onepager_links == st.onepager_links
    assert back.onepager_risks == st.onepager_risks
    assert (back.onepager_title, back.onepager_window, back.onepager_today) == (
        st.onepager_title,
        st.onepager_window,
        st.onepager_today,
    )
    # the list sheet is a droppable list in its own right, at the same row numbers
    sheet = {sp.LIST_SHEETS["list"]: sheets[sp.LIST_SHEETS["list"]]}
    from schedule_forensics.reports.onepager import parse_numbered_workbook

    dropped = parse_numbered_workbook(sheet, "Program list.xlsx")
    assert [it.row for it in dropped.items] == [it.row for it in st.onepager.items]
    assert [it.key for it in dropped.items] == [it.key for it in st.onepager.items]


def test_a_plain_list_workbook_is_not_a_record() -> None:
    sheets = read_xlsx_numbered(twin_xlsx(ROWS), max_columns=13)
    with pytest.raises(sp.PayloadError, match="no LODESTAR settings sheet"):
        sp.payload_from_sheets(sheets)


@pytest.mark.parametrize(
    "data,kind",
    [
        (b"%PDF-1.4 ...", "pdf"),
        (twin_xlsx(ROWS), "xlsx"),
        (b"PK\x03\x04junk", ""),
        (b"hello", ""),
    ],
)
def test_the_sniff_reads_the_bytes_never_the_name(data: bytes, kind: str) -> None:
    assert sp.sniff_export(data) == kind
