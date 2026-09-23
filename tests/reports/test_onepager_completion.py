"""Column D of a One-Pager list says whether each item is COMPLETE (operator, 2026-09-22; ADR-0524).

The operator's own words: "use column D in the worksheets to determine if the task has completed or
not". Asked what column D holds, the operator answered: STATUS WORDS. So the reader is a word
reader, and it is honest about the words it does not know:

* a status that STARTS with a completion word — Complete, Completed, Done, Finished, Closed (or
  Closed Out) — is complete, whatever follows it ("Complete (late)", "Finished Late",
  "Completed 3/1/27"); so is Yes / Y / X / a check mark / Achieved / Met / Delivered / 100%;
* a negation is never complete ("Not Complete", "Not Yet Started", "Incomplete");
* every other word, a blank cell, a number or a date is NOT complete — and a word this reader
  does not recognise as either is NAMED, by value and sheet row, so the operator can see it;
* a sheet with nothing in column D has no completion at all (``None``), which is not the same as
  "nothing is complete" (``False``).

Those notes are the COMPARE page's: they never reach /onepager, which draws no completion.
Red-first (2026-09-22): written before column D was read, and observed to fail.
"""

from __future__ import annotations

import pytest

from schedule_forensics.reports.onepager import (
    OnePagerDoc,
    parse_numbered_workbook,
    parse_rows,
    parse_workbook,
    read_completion,
)
from schedule_forensics.reports.xlsx_read import read_xlsx, read_xlsx_numbered
from web.onepager_twin import TWIN_ROWS, twin_xlsx

DONE = [
    "Complete",
    "complete",
    "COMPLETED",
    "Completed.",
    "Done",
    "Finished",
    "Closed",
    "Closed Out",
    "Closed-out",
    "Complete (late)",
    "Finished Late",
    "Completed 3/1/27",
    "Complete - pending signoff",
    "Done ✓",
    "Yes",
    "Y",
    "x",
    "✓",
    "✔",
    "☑",
    "Achieved",
    "Met",
    "Delivered",
    "100%",
    "100 %",
    "100% Complete",
]
OPEN = [
    "",
    "   ",
    "Not Complete",
    "not completed",
    "Not Yet Complete",
    "Not Started",
    "Not Yet Started",
    "Incomplete",
    "In Progress",
    "In-Progress",
    "In Progress (50%)",
    "Started",
    "On Hold",
    "Late",
    "Delayed",
    "At Risk",
    "On Track",
    "Open",
    "Pending",
    "Planned",
    "Scheduled",
    "Ongoing",
    "Active",
    "Underway",
    "In Work",
    "WIP",
    "TBD",
    "No",
    "N",
    "N/A",
    "-",
    "—",
    "0%",
    "50%",
    "99%",
]
#: Not a completion status and not a known open one: drawn as not complete AND named. Numbers and
#: dates land here on purpose — the operator types words, and guessing a scale or reading a date
#: as "finished" (a forecast date is a date too) would be a fabrication.
UNREAD = [
    "Waiting on vendor",
    "Completely blocked",  # starts with the LETTERS of "complete" — the word boundary refuses it
    "Completion pending",
    "Finish",
    "1",
    "46310",
    "3/1/2027",
    "C",
    "OK",
]


@pytest.mark.parametrize("text", DONE)
def test_a_status_that_starts_with_a_completion_word_is_complete(text: str) -> None:
    assert read_completion(text) == (True, True)


@pytest.mark.parametrize("text", OPEN)
def test_a_negation_an_open_status_or_a_blank_is_not_complete(text: str) -> None:
    assert read_completion(text) == (False, True)


@pytest.mark.parametrize("text", UNREAD)
def test_a_value_the_reader_does_not_know_is_not_complete_and_is_flagged_unread(text: str) -> None:
    assert read_completion(text) == (False, False)


ROWS_WITH_D: list[list[str]] = [
    ["Swimlane", "Task", "Date", "Status"],
    ["Alpha", "Design Review", "1/15/2027", "Complete"],
    ["Alpha", "Build", "2/1/2027 - 4/1/2027", "In Progress"],
    ["Alpha", "Test", "5/1/2027", ""],
    ["Beta", "Ship", "6/1/2027", "Waiting on vendor"],
    ["Beta", "Launch", "7/1/2027", "Waiting on vendor"],
    ["Beta", "Close", "8/1/2027", "Finished Late"],
]


def test_column_d_marks_each_item_and_names_every_word_it_could_not_read() -> None:
    doc = parse_workbook({"List": ROWS_WITH_D}, "with_d.xlsx")
    got = {it.name: it.complete for it in doc.items}
    assert got == {
        "Design Review": True,
        "Build": False,
        "Test": False,  # a blank cell in a sheet that HAS a column D is "not complete"
        "Ship": False,
        "Launch": False,
        "Close": True,
    }
    assert doc.completion is True
    # one note per distinct unread value, with every row it sits on
    unread = [n for n in doc.completion_notes if "Waiting on vendor" in n]
    assert len(unread) == 1 and "rows 5, 6" in unread[0]
    assert "not complete" in unread[0]
    # the completion notes are NOT the parser's notes: /onepager renders doc.notes, and it draws
    # no completion, so a column-D sentence there would describe something it never shows
    assert not any("column D" in n for n in doc.notes)


def test_a_list_with_no_column_d_has_no_completion_at_all() -> None:
    doc = parse_workbook({"List": [r[:3] for r in ROWS_WITH_D]}, "three_cols.xlsx")
    assert {it.complete for it in doc.items} == {None}
    assert doc.completion is False and doc.completion_notes == ()
    # the twin (the ADR-0446 field shape) is a three-column list — nothing changes for it
    twin = parse_workbook(read_xlsx(twin_xlsx(TWIN_ROWS)), "twin.xlsx")
    assert {it.complete for it in twin.items} == {None} and twin.completion_notes == ()


def test_a_header_only_column_d_is_no_column_d() -> None:
    rows = [r[:3] + ([""] if i else ["Status"]) for i, r in enumerate(ROWS_WITH_D)]
    doc = parse_workbook({"List": rows}, "header_only.xlsx")
    assert {it.complete for it in doc.items} == {None} and doc.completion is False


def test_parse_rows_keeps_its_three_part_contract() -> None:
    items, problems, notes = parse_rows(ROWS_WITH_D)
    assert len(items) == 6 and problems == [] and notes == []
    assert [it.complete for it in items][:2] == [True, False]


# ── the TRUE sheet row: every row citation is the row Excel shows ──────────────────────────────


def test_the_numbered_workbook_cites_the_row_excel_shows_after_an_omitted_spacer() -> None:
    """The twin in Excel's shape (spacer rows absent). Counting ``<row>`` elements put Boots 1 on
    row 2 and the typo on row 16; Excel shows them on rows 3 and 23."""
    doc = parse_numbered_workbook(
        read_xlsx_numbered(twin_xlsx(TWIN_ROWS, omit_blank=True)), "twin.xlsx"
    )
    rows = {it.name: it.row for it in doc.items}
    assert rows["Boots 1"] == 3 and rows["CDR"] == 7 and rows["MET ATP for Hot-Fire"] == 25
    assert any(p.startswith("row 23 ") and "10/122/2026" in p for p in doc.problems)
    assert any(n.startswith("row 25: no swimlane name") for n in doc.notes)
    # and the same list through the counting reader is the defect this fixes
    counted = parse_workbook(read_xlsx(twin_xlsx(TWIN_ROWS, omit_blank=True)), "twin.xlsx")
    assert {it.name: it.row for it in counted.items}["Boots 1"] == 2


def test_the_numbered_workbook_matches_the_plain_one_when_no_row_is_omitted() -> None:
    plain = parse_workbook(read_xlsx(twin_xlsx(TWIN_ROWS)), "twin.xlsx")
    numbered = parse_numbered_workbook(read_xlsx_numbered(twin_xlsx(TWIN_ROWS)), "twin.xlsx")
    assert numbered == plain


def test_the_first_sheet_with_rows_is_read_even_behind_an_empty_first_sheet() -> None:
    """Numbers travel WITH their rows — never a parallel list that can fall out of step with the
    sheet parse_workbook picks."""
    sheets = {
        "Cover": [],
        "List": [(1, ["Swimlane", "Task", "Date"]), (4, ["Alpha", "Build", "1/1/2027"])],
    }
    doc = parse_numbered_workbook(sheets, "two_sheets.xlsx")
    assert doc.sheet == "List" and [(it.name, it.row) for it in doc.items] == [("Build", 4)]


def test_an_empty_workbook_is_named_not_blank() -> None:
    doc = parse_numbered_workbook({"Sheet1": []}, "empty.xlsx")
    assert doc == OnePagerDoc("empty.xlsx", "", (), ("the workbook has no rows",), ())
