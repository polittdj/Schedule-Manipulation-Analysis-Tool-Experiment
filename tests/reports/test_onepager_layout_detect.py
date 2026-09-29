"""Item 1 of the 2026-09-29 One-Pager request (ADR-0539): the intake's columns.

The operator: "The MS Excel format that will be dragged and dropped into the tool will have the
start date in column C and the Finish Date in Column D and Complete in Column E from now on." So a
sheet now reads A swimlane · B item · C START · D FINISH · E COMPLETE — and a sheet in the OLDER
layout (ADR-0446/0524: C one date or an ``A - B`` range, D a status word) still reads exactly as it
did, and SAYS it was read that way. What this file pins:

* the current layout: C == D is a milestone, C < D an activity, D alone or C alone a milestone; E
  is the status column, and every sentence about completion — the legend's check included — names
  column E (column D for an older sheet, nothing for a sheet with no status column);
* detection (:func:`~schedule_forensics.reports.onepager.detect_layout`) against every red-team
  attack in ADR-0539's table: only column D's header decides, by WHOLE words ("Pending", "Trend",
  "Overdue" and "Vendor" never read as a finish); column D's content decides otherwise, a mixed
  column by the majority with a note, a tie or an unreadable column by the older reading plus a
  NAMED problem carrying the remedy; the layout chosen at upload overrides all of it;
* the current layout's row rules (``_row_span``) and MS Project's pasted date forms — a weekday is
  CHECKED against its date, never just dropped;
* a regression guard: every committed One-Pager row set parses to the items, problems and notes
  the PRISTINE parser gave it (the expectations below were computed on the pristine tree 0b45eb2);
* mutation proofs: each load-bearing rule is broken inside a dedicated test, and the test's own
  checker is shown to go red by name.

Red-first (2026-09-29, this file run against the pristine tree 0b45eb2's ``src``): 65 of 80
red — every test of the new behaviour (the layout API and ``read_list`` did not exist; the MS
Project forms and ``TRUE`` read ``None`` / not complete), and the three dateless-first-row cases
XPASS(strict), because the pristine parser NAMED that row. 14 passed there, as they must: the 12
regression-guard cases (pinned from that tree), the weekday contradictions and ``FALSE`` (the
pristine reader already refused / read them). The two strict-xfail tests are src bugs this file
found — see their reasons.
"""

from __future__ import annotations

import datetime as dt
import io
import re
import zipfile
from collections.abc import Mapping, Sequence

import pytest

import schedule_forensics.reports.onepager as op
from schedule_forensics.reports.xlsx_read import read_xlsx_numbered
from web.onepager_twin import TWIN_ROWS, twin_xlsx

D = dt.date
TODAY = D(2027, 3, 1)  # a fixed date for every layout — never the clock
_Row = tuple[object, ...]
_Item = tuple[str, str, str, str, int, bool | None]
_CAP = 10 * 1024 * 1024


def _doc(
    rows: Sequence[_Row], *, omit_blank: bool = False, layout: str | None = None
) -> op.OnePagerDoc:
    """``rows`` written the way Excel writes a workbook, read by the numbered reader and parsed —
    the path an upload takes. ``layout`` forces a layout (the upload form's choice)."""
    sheets = read_xlsx_numbered(twin_xlsx(rows, omit_blank=omit_blank))
    if layout is None:  # the pristine signature — so the regression guard runs on both trees
        return op.parse_numbered_workbook(sheets, "list.xlsx")
    return op.parse_numbered_workbook(sheets, "list.xlsx", layout=layout)


def _items(doc: op.OnePagerDoc) -> tuple[_Item, ...]:
    return tuple(
        (it.lane, it.name, it.start.isoformat(), it.finish.isoformat(), it.row, it.complete)
        for it in doc.items
    )


# ── the current layout: A swimlane · B item · C start · D finish · E complete ───────────────

#: Every shape a row of the current layout takes, with a spacer row Excel leaves out of the file.
SF_ROWS: tuple[_Row, ...] = (
    ("Swimlane", "Task", "Start", "Finish", "Complete"),
    ("Alpha", "PDR", "3/1/2027", "3/1/2027", "Complete"),  # C == D: a milestone
    ("Alpha", "Build", "3/1/2027", "4/15/2027", "In Progress"),  # C < D: an activity
    (),
    ("Beta", "Ship", "", "5/1/2027", "Done"),  # only the finish: a milestone
    ("Beta", "Kickoff", "6/1/2027", "", ""),  # only the start: a milestone
    ("Beta", "Test", 46565, 46600, "Waiting on vendor"),  # Excel date cells (serials)
)
SF_ITEMS: tuple[_Item, ...] = (
    ("Alpha", "PDR", "2027-03-01", "2027-03-01", 2, True),
    ("Alpha", "Build", "2027-03-01", "2027-04-15", 3, False),
    ("Beta", "Ship", "2027-05-01", "2027-05-01", 5, True),
    ("Beta", "Kickoff", "2027-06-01", "2027-06-01", 6, False),
    ("Beta", "Test", "2027-06-27", "2027-08-01", 7, False),
)


def test_the_current_layout_reads_c_start_d_finish_e_complete() -> None:
    """C is the start, D the finish, E the status: equal dates or one date alone is a milestone,
    two different dates an activity; the sheet is plainly the current layout, so nothing is said
    about its layout, and E's unread word is named AS column E."""
    doc = _doc(SF_ROWS, omit_blank=True)
    assert doc.layout == op.START_FINISH
    assert doc.status_column == "E"
    assert _items(doc) == SF_ITEMS
    assert [it.milestone for it in doc.items] == [True, False, True, True, False]
    assert doc.problems == () and doc.notes == ()
    assert doc.layout_note == "" and op.layout_notes(doc) == []
    assert doc.completion_notes == (
        "column E “Waiting on vendor” (row 7): not a status read as complete — drawn as not "
        "complete",
    )


def test_the_legend_names_the_column_the_sheet_used_for_its_status() -> None:
    """``build_layout(status_column=...)``: the check's legend entry says ``Complete (column E)``
    for the current layout, ``Complete (column D)`` for an older sheet, and there is no check at
    all for a sheet with no status column."""
    current = _doc(SF_ROWS, omit_blank=True)
    older = _doc(LEGACY_ROWS)
    plain = _doc(tuple(r[:3] for r in LEGACY_ROWS))
    seen: dict[str, tuple[list[str], str]] = {}
    for tag, doc in (("current", current), ("older", older), ("plain", plain)):
        lay = op.build_layout(doc.items, TODAY, "t", status_column=doc.status_column)
        seen[tag] = ([e.label for e in lay.legend if e.kind == "done"], lay.status_label)
    assert seen == {
        "current": (["Complete (column E)"], "column E"),
        "older": (["Complete (column D)"], "column D"),
        "plain": ([], ""),
    }


def test_status_label_names_one_column_only_when_every_list_used_it() -> None:
    """No sentence names a column a list did not use: two lists that disagree are "the status
    column", and a list with none says nothing."""
    assert op.status_label(["E", "", "E"]) == "column E"
    assert op.status_label(["D"]) == "column D"
    assert op.status_label(["E", "D"]) == "the status column"
    assert op.status_label(["", ""]) == "" and op.status_label([]) == ""
    assert op.complete_legend("column E") == "Complete (column E)"
    assert op.complete_legend("") == "Complete"


# ── the older layout: still read, and named only when column D gave real evidence of it ──────

LEGACY_ROWS: tuple[_Row, ...] = (
    ("Swimlane", "Task", "Date", "Status"),
    ("Alpha", "Design Review", "1/15/2027", "Complete"),
    ("Alpha", "Build", "2/1/2027 - 4/1/2027", "In Progress"),
    ("Beta", "Ship", 46565, "Done"),
)
LEGACY_ITEMS: tuple[_Item, ...] = (
    ("Alpha", "Design Review", "2027-01-15", "2027-01-15", 2, True),
    ("Alpha", "Build", "2027-02-01", "2027-04-01", 3, False),
    ("Beta", "Ship", "2027-06-27", "2027-06-27", 4, True),
)


def _assert_reads_older(doc: op.OnePagerDoc, expected: tuple[_Item, ...]) -> None:
    """THE checker for an older sheet (the mutation test below breaks detection and requires
    this to go red): the older layout, D the status column, the older-layout sentence, every
    row read from C exactly, nothing skipped."""
    assert doc.layout == op.DATE_STATUS, doc.layout
    assert doc.status_column == "D"
    assert doc.layout_note == op.OLDER_LAYOUT_NOTE
    assert op.layout_notes(doc) == [op.OLDER_LAYOUT_NOTE]
    assert _items(doc) == expected
    assert doc.problems == ()


def test_an_older_sheet_reads_as_before_and_says_which_layout_it_got() -> None:
    _assert_reads_older(_doc(LEGACY_ROWS), LEGACY_ITEMS)


def test_the_older_layout_is_named_only_when_column_d_had_content() -> None:
    """A plain three-column list, or one whose column D is only a header, draws the same in
    either reading — so nothing is said about its layout and it has no status column."""
    for rows in (
        tuple(r[:3] for r in LEGACY_ROWS),
        (("Swimlane", "Task", "Date", "Status"), *(r[:3] for r in LEGACY_ROWS[1:])),
        TWIN_ROWS,
    ):
        doc = _doc(rows)
        assert doc.layout == op.DATE_STATUS
        assert doc.status_column == "" and doc.layout_note == "" and op.layout_notes(doc) == []
        assert {it.complete for it in doc.items} == {None}


#: ADR-0539's red-team headers: each flipped a legacy sheet (and skipped its rows) under PLAN v1.
ATTACK_HEADERS: tuple[tuple[str, ...], ...] = (
    ("Swimlane", "Task", "Date", "Status", "Comments"),  # a comment column in E
    ("Swimlane", "Task", "Start - Finish", "Status"),  # a range header in C
    ("Swimlane", "Task", "Date", "Status (Pending/Done)"),  # Pend-ING is not "end"
    ("Swimlane", "Task", "Date", "Trend"),  # Tr-END
    ("Swimlane", "Task", "Date", "Complete / Overdue"),  # Over-DUE
    ("Swimlane", "Task", "Date", "Vendor status"),  # V-END-or
)


@pytest.mark.parametrize("header", ATTACK_HEADERS, ids=lambda h: "|".join(h))
def test_no_header_attack_flips_an_older_sheet(header: tuple[str, ...]) -> None:
    rows = (
        header,
        ("Alpha", "Design Review", "1/15/2027", "Complete", "vendor late"),
        ("Alpha", "Build", "2/1/2027 - 4/1/2027", "Pending", "see the plan"),
    )
    _assert_reads_older(
        _doc(rows),
        (
            ("Alpha", "Design Review", "2027-01-15", "2027-01-15", 2, True),
            ("Alpha", "Build", "2027-02-01", "2027-04-01", 3, False),
        ),
    )


#: (column D's header, the one data row's D, the layout the header must yield) — each attack
#: header is paired with the D content that a SUBSTRING match would turn into the other layout,
#: and the controls prove a whole-word finish does decide on its own, against the content.
D_HEADER_CASES: tuple[tuple[str, str, str], ...] = (
    ("Status (Pending/Done)", "2/1/2027", "date-status"),  # the header decides, not the date
    ("Complete / Overdue", "2/1/2027", "date-status"),
    ("Vendor status", "2/1/2027", "date-status"),
    ("Trend", "Complete", "date-status"),  # the header says nothing; the status word decides
    ("Finish", "Complete", "start-finish"),  # control: a whole-word finish beats the content
    ("Due Date", "Complete", "start-finish"),
    ("End", "Complete", "start-finish"),
)


def _d_header_verdicts() -> dict[str, str]:
    out: dict[str, str] = {}
    for head, d, _want in D_HEADER_CASES:
        rows = [["Swimlane", "Task", "Date", head], ["Alpha", "Design Review", "1/15/2027", d]]
        out[head] = op.detect_layout(rows, 0).layout
    return out


def _assert_d_header_verdicts() -> None:
    assert _d_header_verdicts() == {head: want for head, _d, want in D_HEADER_CASES}


def test_column_d_s_header_decides_by_whole_words_only() -> None:
    assert (op.START_FINISH, op.DATE_STATUS) == ("start-finish", "date-status")
    _assert_d_header_verdicts()


def test_a_mixed_column_d_goes_to_the_majority_and_names_the_rows_that_do_not_fit() -> None:
    """ADR-0526's UNREAD fixture: one completion DATE typed into an older status column must not
    flip the sheet. Three status words and one date -> the older layout by majority, said, and the
    date row named by the status column's own rule; the mirror case reads the current layout and
    refuses the status word in D by name."""
    older = _doc(
        (
            ("Alpha", "Design Review", "1/15/2027", "Complete"),
            ("Alpha", "Build", "2/1/2027 - 4/1/2027", "Pending"),
            ("Alpha", "Test", "5/1/2027", "Done"),
            ("Alpha", "Ship", "6/1/2027", "6/3/2027"),
        )
    )
    assert older.layout == op.DATE_STATUS and older.status_column == "D"
    assert older.layout_note.startswith(
        "column D holds 1 date(s), 3 status word(s) and 0 other value(s) — read as the older "
        "C date-or-range · D status (the majority)"
    )
    assert "add the header row Swimlane · Task · Start · Finish · Complete" in older.layout_note
    assert [it.name for it in older.items] == ["Design Review", "Build", "Test", "Ship"]
    assert older.items[3].start == older.items[3].finish == dt.date(2027, 6, 1)
    assert older.completion_notes == (
        "column D “6/3/2027” (row 4): not a status read as complete — drawn as not complete",
    )
    current = _doc(
        (
            ("Alpha", "Design Review", "1/15/2027", "1/20/2027"),
            ("Alpha", "Build", "2/1/2027", "4/1/2027"),
            ("Alpha", "Test", "5/1/2027", "5/3/2027"),
            ("Alpha", "Ship", "6/1/2027", "Complete"),
        )
    )
    assert current.layout == op.START_FINISH
    assert "3 date(s), 1 status word(s)" in current.layout_note
    assert "(the majority)" in current.layout_note
    assert [it.name for it in current.items] == ["Design Review", "Build", "Test"]
    assert current.problems == (
        "row 4 (Alpha · Ship): column D holds “Complete”, a status word — in this layout column D "
        "is the finish date and the status belongs in column E; skipped",
    )


def test_with_no_evidence_in_d_a_status_column_e_decides_the_current_layout() -> None:
    """Column D empty everywhere: status words in E make it the current layout — else E's
    completion would be lost — and without them the older reading, which draws the same, is
    taken with nothing said."""
    rows = (
        ("Alpha", "Kickoff", "1/5/2027", "", "Complete"),
        ("Alpha", "Review", "2/1/2027 - 3/1/2027", "", "In Progress"),
    )
    doc = _doc(rows)
    assert (doc.layout, doc.status_column, doc.layout_note) == (op.START_FINISH, "E", "")
    assert _items(doc) == (
        ("Alpha", "Kickoff", "2027-01-05", "2027-01-05", 1, True),
        ("Alpha", "Review", "2027-02-01", "2027-03-01", 2, False),
    )
    bare = _doc(tuple(r[:3] for r in rows))
    assert (bare.layout, bare.status_column, bare.layout_note) == (op.DATE_STATUS, "", "")
    assert bare.problems == () and [it.complete for it in bare.items] == [None, None]


def test_placeholders_in_d_are_no_evidence_either_way() -> None:
    """``TBD``, ``N/A`` and a dash say nothing about the layout: an older column of one status
    word and three placeholders is unanimous (no majority sentence), and so is a current column
    of dates and a ``TBD`` — whose row is then refused by name, never guessed."""
    older = _doc(
        (
            ("Alpha", "Design", "1/5/2027", "Complete"),
            ("Alpha", "Build", "2/1/2027", "TBD"),
            ("Alpha", "Test", "3/1/2027", "N/A"),
            ("Alpha", "Ship", "4/1/2027", "-"),
        )
    )
    assert older.layout == op.DATE_STATUS and older.layout_note == op.OLDER_LAYOUT_NOTE
    assert older.problems == () and older.completion_notes == ()
    assert [it.complete for it in older.items] == [True, False, False, False]
    current = _doc(
        (("Alpha", "Design", "1/5/2027", "1/9/2027"), ("Alpha", "Build", "2/1/2027", "TBD"))
    )
    assert current.layout == op.START_FINISH and current.layout_note == ""
    assert current.problems == ("row 2 (Alpha · Build): unreadable finish date “TBD” — skipped",)


def test_a_headerless_older_sheet_with_owner_names_in_e_stays_older() -> None:
    """Five columns are not the current layout: owner names in E are no status, and D's status
    words decide."""
    rows = (
        ("Alpha", "Design Review", "1/15/2027", "Complete", "Bob Smith"),
        ("Alpha", "Build", "2/1/2027 - 4/1/2027", "In Progress", "Ana Diaz"),
    )
    _assert_reads_older(
        _doc(rows),
        (
            ("Alpha", "Design Review", "2027-01-15", "2027-01-15", 1, True),
            ("Alpha", "Build", "2027-02-01", "2027-04-01", 2, False),
        ),
    )


def test_a_first_row_with_a_blank_c_and_a_dated_d_is_data_not_a_header() -> None:
    """ADR-0539's refuted ``_is_header`` reuse: a finish-only first row whose names carry header
    words ("Lane", "Milestone") was eaten as a header. A header has no date in C OR D; nor is a
    first row a header because its E reads "Complete" when C holds a date."""
    doc = _doc(
        (
            ("Lane A", "Milestone 1", "", "1/1/2027", "Complete"),
            ("Lane A", "Activity 2", "2/1/2027", "3/1/2027", ""),
        )
    )
    assert doc.layout == op.START_FINISH and doc.problems == ()
    assert _items(doc) == (
        ("Lane A", "Milestone 1", "2027-01-01", "2027-01-01", 1, True),
        ("Lane A", "Activity 2", "2027-02-01", "2027-03-01", 2, False),
    )
    first_is_complete = _doc(
        (("Alpha", "Design", "1/1/2027", "2/1/2027", "Complete"), ("Alpha", "Build", "3/1/2027"))
    )
    assert [it.name for it in first_is_complete.items] == ["Design", "Build"]


_REMEDY = (
    "add the header row Swimlane · Task · Start · Finish · Complete, or choose the layout when "
    "you upload"
)


def test_a_column_d_of_words_the_reader_cannot_read_is_the_older_layout_with_the_words_named() -> (
    None
):
    """Review INTAKE-1 / INTAKE-2: in the current layout column D must be a finish DATE, so words
    the reader does not know (RAG colours, comments, owners) are evidence of the OLDER layout —
    never "undecided", and never a skipped row (every row is drawn; the words are named)."""
    doc = _doc(
        (("Alpha", "Design Review", "1/15/2027", "foo"), ("Alpha", "Build", "2/1/2027", "bar"))
    )
    assert doc.layout == op.DATE_STATUS
    assert doc.problems == ()
    assert doc.layout_note == op.OLDER_LAYOUT_NOTE
    assert [it.name for it in doc.items] == ["Design Review", "Build"]  # the rows still drawn
    assert len(doc.completion_notes) == 2 and "“foo”" in doc.completion_notes[0]


def test_a_tie_keeps_the_older_reading_and_says_so_in_a_note_never_a_skipped_row() -> None:
    """Review INTAKE-2: the undecided sentence is about the SHEET — it is the layout note, never
    counted among the skipped rows (no row was skipped)."""
    doc = _doc(
        (
            ("Alpha", "Design Review", "1/15/2027", "Complete"),
            ("Alpha", "Build", "2/1/2027", "3/1/27"),
        )
    )
    assert doc.layout == op.DATE_STATUS and doc.status_column == "D"
    assert doc.problems == ()
    assert doc.layout_note.startswith("column D holds 1 date(s), 1 status word(s)")
    assert "the layout could not be decided" in doc.layout_note and _REMEDY in doc.layout_note
    assert [it.start.isoformat() for it in doc.items] == ["2027-01-15", "2027-02-01"]


def test_the_layout_chosen_at_upload_overrides_detection() -> None:
    """Forced current on an older sheet: D's status word is refused naming column E. Forced older
    on a current sheet: D's finish is read as a status (and named as a word it could not read)."""
    forced_new = _doc(LEGACY_ROWS, layout=op.START_FINISH)
    assert forced_new.layout == op.START_FINISH
    assert forced_new.layout_note == "read as C start · D finish · E complete — chosen at upload"
    assert forced_new.items == ()  # every D is a status word: refused, row by row, by name
    assert len(forced_new.problems) == 3
    assert forced_new.problems[0] == (
        "row 2 (Alpha · Design Review): column D holds “Complete”, a status word — in this "
        "layout column D is the finish date and the status belongs in column E; skipped"
    )
    forced_old = _doc(SF_ROWS, omit_blank=True, layout=op.DATE_STATUS)
    assert forced_old.layout == op.DATE_STATUS and forced_old.status_column == "D"
    assert forced_old.layout_note == (
        "read as the older C date-or-range · D status — chosen at upload"
    )
    assert _items(forced_old)[1] == ("Alpha", "Build", "2027-03-01", "2027-03-01", 3, False)
    assert any("column D “4/15/2027” (row 3)" in n for n in forced_old.completion_notes)


def test_the_upload_reads_the_layout_choice_and_detects_otherwise() -> None:
    """``read_list`` (both programs' upload): ``auto`` or an unknown choice detects; the two
    layout names force, whatever their case or spacing."""
    from schedule_forensics.web.onepager_actions import read_list

    older, current = twin_xlsx(LEGACY_ROWS), twin_xlsx(SF_ROWS, omit_blank=True)
    got = {}
    for tag, data, choice in (
        ("older-auto", older, "auto"),
        ("older-unknown", older, "sideways"),
        ("older-forced-new", older, " Start-Finish "),
        ("current-auto", current, "auto"),
        ("current-forced-old", current, "DATE-STATUS"),
    ):
        doc = read_list(data, "list.xlsx", max_bytes=_CAP, layout=choice)
        assert isinstance(doc, op.OnePagerDoc), doc
        got[tag] = (doc.layout, doc.status_column, "chosen at upload" in doc.layout_note)
    assert got == {
        "older-auto": (op.DATE_STATUS, "D", False),
        "older-unknown": (op.DATE_STATUS, "D", False),
        "older-forced-new": (op.START_FINISH, "", True),
        "current-auto": (op.START_FINISH, "E", False),
        "current-forced-old": (op.DATE_STATUS, "D", True),
    }
    detected = read_list(current, "l.xlsx", max_bytes=_CAP)
    assert isinstance(detected, op.OnePagerDoc) and _items(detected) == SF_ITEMS


# ── the current layout's row rules ────────────────────────────────────────────────────────────

#: (case, C, D, the item's (start, finish) or None, the note or problem the row must carry)
ROW_RULES: tuple[tuple[str, str, str, tuple[str, str] | None, str], ...] = (
    ("both days", "1/1/2027", "2/1/2027", ("2027-01-01", "2027-02-01"), ""),
    ("a range alone in C", "1/1/2027 - 2/1/2027", "", ("2027-01-01", "2027-02-01"), ""),
    (
        "a range in C ending on D",
        "1/1/2027 - 2/1/2027",
        "2/1/2027",
        ("2027-01-01", "2027-02-01"),
        "the range in C ends on D's finish — read as 1/1/2027 - 2/1/2027",
    ),
    (
        "a range in D starting on C",
        "1/1/2027",
        "1/1/2027 - 2/1/2027",
        ("2027-01-01", "2027-02-01"),
        "the range in D starts on C's start — read as 1/1/2027 - 2/1/2027",
    ),
    (
        "a range in C that disagrees with D",
        "1/1/2027 - 2/1/2027",
        "3/1/2027",
        None,
        "column C holds the range “1/1/2027 - 2/1/2027” but column D the finish “3/1/2027” — two "
        "different finishes; put the start in C and the finish in D; skipped",
    ),
    (
        "a range in D that disagrees with C",
        "1/5/2027",
        "1/1/2027 - 2/1/2027",
        None,
        "two different starts; put the start in C and the finish in D; skipped",
    ),
    (
        "ranges in both",
        "1/1/2027 - 2/1/2027",
        "2/1/2027 - 3/1/2027",
        None,
        "date ranges in both C and D — put the start in C and the finish in D; skipped",
    ),
    (
        "a status word in D",
        "1/1/2027",
        "Complete",
        None,
        "column D holds “Complete”, a status word — in this layout column D is the finish date "
        "and the status belongs in column E; skipped",
    ),
    (
        "a status word in C",
        "Done",
        "2/1/2027",
        None,
        "column C holds “Done”, a status word — in this layout column C is the start date and "
        "the status belongs in column E; skipped",
    ),
    (
        "a month-only start alone",
        "Jan 2027",
        "",
        ("2027-01-01", "2027-01-31"),
        "“Jan 2027” names a month, not a day — drawn across the whole month",
    ),
    (
        "a month-only finish alone",
        "",
        "05/2027",
        ("2027-05-01", "2027-05-31"),
        "“05/2027” names a month, not a day — drawn across the whole month",
    ),
    (
        "swapped dates",
        "3/1/2027",
        "1/1/2027",
        ("2027-01-01", "2027-03-01"),
        "finish before start — dates swapped",
    ),
    (
        "an unreadable finish",
        "1/1/2027",
        "10/122/2026",
        None,
        "unreadable finish date “10/122/2026” — skipped",
    ),
    ("no dates at all", "", "", None, "no start or finish date — skipped"),
)


@pytest.mark.parametrize(
    ("case", "c", "d", "span", "said"), ROW_RULES, ids=[r[0] for r in ROW_RULES]
)
def test_a_row_of_the_current_layout_follows_the_row_rules(
    case: str, c: str, d: str, span: tuple[str, str] | None, said: str
) -> None:
    """Two dates never get picked between: a range in one cell agrees with the other cell or the
    row is refused, by row, with the fix; a status word in C or D is refused naming column E; a
    lone month and swapped dates are drawn and SAID."""
    doc = _doc((("Swimlane", "Task", "Start", "Finish", "Complete"), ("A", case, c, d, "")))
    assert doc.layout == op.START_FINISH
    where = f"row 2 (A · {case}): "
    if span is None:
        assert doc.items == ()
        assert len(doc.problems) == 1 and doc.problems[0].startswith(where), doc.problems
        assert doc.problems[0].endswith(said), doc.problems[0]
        return
    assert doc.problems == ()
    assert (doc.items[0].start.isoformat(), doc.items[0].finish.isoformat()) == span
    assert doc.notes == ((where + said,) if said else ())


# ── MS Project's pasted date forms ───────────────────────────────────────────────────────────

MSP_FORMS: tuple[tuple[str, tuple[D, D]], ...] = (
    ("Tue 9/1/26", (D(2026, 9, 1), D(2026, 9, 1))),
    ("Tuesday, 9/1/26", (D(2026, 9, 1), D(2026, 9, 1))),
    ("Wed 9/30/26", (D(2026, 9, 30), D(2026, 9, 30))),
    ("9/1/26 8:00 AM", (D(2026, 9, 1), D(2026, 9, 1))),
    ("Tue 9/1/26 5:00 PM", (D(2026, 9, 1), D(2026, 9, 1))),
    ("Sept 30, 2027", (D(2027, 9, 30), D(2027, 9, 30))),
    ("Sept. 30, 2027", (D(2027, 9, 30), D(2027, 9, 30))),
    ("Nov. 30, 2027", (D(2027, 11, 30), D(2027, 11, 30))),
)
#: A weekday that contradicts its date (or prefixes a whole month) — the token is unreadable,
#: never resolved by picking a side.
CONTRADICTIONS = ("Mon 9/1/26", "Fri 9/1/26 8:00 AM", "Sun Sept 30, 2027", "Tue Sep 2027")


@pytest.mark.parametrize(("text", "expected"), MSP_FORMS, ids=[t for t, _e in MSP_FORMS])
def test_ms_project_s_pasted_date_forms_read(text: str, expected: tuple[D, D]) -> None:
    assert op.parse_date(text) == expected


def _assert_weekday_contradictions_refused() -> None:
    assert {t: op.parse_date(t) for t in CONTRADICTIONS} == dict.fromkeys(CONTRADICTIONS)


def test_a_weekday_that_contradicts_its_date_is_unreadable() -> None:
    _assert_weekday_contradictions_refused()


def test_an_ms_project_paste_reads_through_the_sheet_and_a_contradiction_is_named() -> None:
    doc = _doc(
        (
            ("Swimlane", "Task", "Start", "Finish", "Complete"),
            ("Alpha", "Pasted", "Tue 9/1/26 8:00 AM", "Fri 9/4/26 5:00 PM", ""),
            ("Alpha", "Mistyped", "Mon 9/1/26", "Fri 9/4/26", ""),
        )
    )
    assert _items(doc) == (("Alpha", "Pasted", "2026-09-01", "2026-09-04", 2, None),)
    assert doc.problems == (
        "row 3 (Alpha · Mistyped): unreadable start date “Mon 9/1/26” — skipped",
    )


@pytest.mark.parametrize(("text", "done"), [("TRUE", True), ("true", True), ("FALSE", False)])
def test_true_reads_complete_and_false_not(text: str, done: bool) -> None:
    assert op.read_completion(text) == (done, True)


def _with_boolean_cells(data: bytes, cells: Mapping[str, int]) -> bytes:
    """``data`` with each named cell rewritten as an Excel BOOLEAN cell (``t="b"``) — what Excel
    stores when TRUE or FALSE is typed into a cell (or a checkbox is ticked)."""
    src = zipfile.ZipFile(io.BytesIO(data))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
        for name in src.namelist():
            body = src.read(name)
            if name == "xl/worksheets/sheet1.xml":
                text = body.decode()
                for ref, value in cells.items():
                    text, n = re.subn(
                        rf'<c r="{ref}"[^>]*>.*?</c>',
                        f'<c r="{ref}" t="b"><v>{value}</v></c>',
                        text,
                    )
                    assert n == 1, ref
                body = text.encode()
            dst.writestr(name, body)
    return out.getvalue()


def test_an_excel_boolean_true_in_column_e_reads_complete() -> None:
    rows = (
        ("Swimlane", "Task", "Start", "Finish", "Complete"),
        ("Alpha", "Design Review", "1/15/2027", "1/15/2027", "placeholder"),
        ("Alpha", "Build", "2/1/2027", "4/1/2027", "placeholder"),
    )
    data = _with_boolean_cells(twin_xlsx(rows), {"E2": 1, "E3": 0})
    from schedule_forensics.web.onepager_actions import read_list

    # the path an upload takes (both servers call read_list)
    doc = read_list(data, "bool.xlsx", max_bytes=_CAP)
    assert isinstance(doc, op.OnePagerDoc)
    assert [it.complete for it in doc.items] == [True, False]
    assert doc.completion_notes == ()
    # the reader: the word Excel SHOWS only when asked — its default keeps the stored 1 / 0
    shown = read_xlsx_numbered(data, booleans_as_text=True)["Sheet1"]
    stored = read_xlsx_numbered(data)["Sheet1"]
    assert [cells[4] for _, cells in shown[1:]] == ["TRUE", "FALSE"]
    assert [cells[4] for _, cells in stored[1:]] == ["1", "0"]


@pytest.mark.parametrize(
    "rows",
    [
        (("Alpha", "Design Review", "", "Complete"), ("Alpha", "Build", "2/1/2027", "Pending")),
        (("Alpha", "Design Review", "TBD", "Done"), ("Alpha", "Build", "2/1/2027", "Pending")),
        (
            ("Alpha", "Design Review", "", "", "Complete"),
            ("Alpha", "Build", "2/1/2027", "3/1/2027", "Pending"),
        ),
    ],
    ids=["older-blank-c", "older-tbd-c", "current-no-dates"],
)
def test_a_dateless_first_data_row_is_named_never_swallowed_as_a_header(
    rows: tuple[_Row, ...],
) -> None:
    doc = _doc(rows)
    drawn = any(it.row == 1 for it in doc.items)
    named = [p for p in doc.problems if p.startswith("row 1 (Alpha · Design Review)")]
    assert drawn or named, (doc.items, doc.problems)


# ── the identity survives the move to the current layout ─────────────────────────────────────


def test_moving_an_older_sheet_to_the_current_layout_keeps_every_item_and_key() -> None:
    """The same list typed in each layout reads to the same items AND the same keys — so the
    operator's logic links survive re-typing an older sheet in the template (a repeated name is
    keyed with its dates, which are the same in both)."""
    older = _doc(COMPARE_PAGE_PRIOR_D, omit_blank=True)
    current = _doc(
        (
            ("Swimlane", "Task", "Start", "Finish", "Complete"),
            ("Alpha", "Design Review", "1/15/2027", "1/15/2027", "Complete"),
            ("Alpha", "Design Review", "5/15/2027", "", "Not Started"),
            ("Alpha", "Build", "2/1/2027", "4/1/2027", "In Progress"),
            (),
            ("Beta", "Reopened", "", "2/10/2027", "Complete"),
            ("Beta", "Dropped", "1/20/2027", "1/20/2027", "Complete"),
        ),
        omit_blank=True,
    )
    assert (older.layout, current.layout) == (op.DATE_STATUS, op.START_FINISH)
    assert _items(current) == _items(older)
    keys = [it.key for it in current.items]
    assert keys == [it.key for it in older.items]
    assert all(keys) and len(set(keys)) == len(keys)
    assert keys == op.item_keys(current.items)


# ── regression guard: every committed One-Pager row set reads as it did on the pristine tree ──

#: tests/web/test_onepager_compare_page.py CURRENT_ROWS (verbatim expression).
COMPARE_PAGE_CURRENT_ROWS: tuple[_Row, ...] = (
    *(
        row
        for row in (
            ("Flight Manifests", "Boots 1", 46595)
            if r[:2] == ("Flight Manifests", "Boots 1")
            else ("Dallas", "CDR", 46655)
            if r[:2] == ("Dallas", "CDR")
            else None
            if r[:2] == ("Crew Life", "MET Testing")
            else ("GRC- (MCaRR-2)", "TRR", "9/20/2026 - 10/4/2026")
            if r[:2] == ("GRC- (MCaRR-2)", "TRR")
            else r
            for r in TWIN_ROWS
        )
        if row is not None
    ),
    ("Flight Manifests", "Boots 3", "12/1/2028"),
)
#: tests/web/test_onepager_window_page.py CURRENT_ROWS (verbatim expression).
WINDOW_PAGE_CURRENT_ROWS: tuple[_Row, ...] = tuple(
    ("Flight Manifests", "Boots 1", "9/1/2027")
    if r[:2] == ("Flight Manifests", "Boots 1")
    else ("Crew Life", "MET On-Dock", "2/1/2027")
    if r[:2] == ("Crew Life", "MET On-Dock")
    else r
    for r in TWIN_ROWS
)
#: tests/web/test_onepager_compare_page.py PRIOR_D / CURRENT_D.
COMPARE_PAGE_PRIOR_D: tuple[_Row, ...] = (
    ("Swimlane", "Task", "Date", "Status"),
    ("Alpha", "Design Review", "1/15/2027", "Complete"),
    ("Alpha", "Design Review", "5/15/2027", "Not Started"),
    ("Alpha", "Build", "2/1/2027 - 4/1/2027", "In Progress"),
    (),
    ("Beta", "Reopened", "2/10/2027", "Complete"),
    ("Beta", "Dropped", "1/20/2027", "Complete"),
)
COMPARE_PAGE_CURRENT_D: tuple[_Row, ...] = (
    ("Swimlane", "Task", "Date", "Status"),
    ("Alpha", "Design Review", "1/15/2027", "Complete"),
    ("Alpha", "Design Review", "5/15/2027", "In Progress"),
    ("Alpha", "Build", "2/1/2027 - 4/20/2027", "Complete"),
    (),
    ("Beta", "Reopened", "2/10/2027", "In Progress"),
    ("Beta", "Brand new", "5/1/2027", "Waiting on vendor"),
)
#: tests/reports/test_onepager_compare.py PRIOR_ROWS / CURRENT_ROWS.
COMPARE_PRIOR_ROWS: tuple[_Row, ...] = (
    ("Swimlane Name", "Task", "Date"),
    ("Lane A", "Slips", "1/10/2027 - 3/1/2027"),
    ("Lane A", "Pulls in", "2/1/2027 - 6/30/2027"),
    ("Lane A", "Steady", "4/1/2027 - 5/1/2027"),
    ("Lane A", "Starts later", "5/1/2027 - 8/1/2027"),
    ("Lane A", "Old name", "7/7/2027"),
    ("Lane B", "Was a milestone", "9/9/2027"),
    ("Lane B", "Gone", "10/1/2027"),
    ("Lane B", "Twin", "11/1/2027"),
    ("Lane B", "Twin", "11/5/2027"),
    ("Lane B", "Moves lane", "12/1/2027"),
    ("Lane  A", "spaced  spelling", "1/1/2028"),
)
COMPARE_CURRENT_ROWS: tuple[_Row, ...] = (
    ("Swimlane Name", "Task", "Date"),
    ("Lane A", "Slips", "1/10/2027 - 3/31/2027"),
    ("Lane A", "Pulls in", "2/1/2027 - 6/15/2027"),
    ("Lane A", "Steady", "4/1/2027 - 5/1/2027"),
    ("Lane A", "Starts later", "5/15/2027 - 8/1/2027"),
    ("Lane A", "New name", "7/7/2027"),
    ("Lane A", "Brand new", "8/8/2027"),
    ("Lane B", "Was a milestone", "9/1/2027 - 9/30/2027"),
    ("Lane B", "Twin", "11/3/2027"),
    ("Lane C", "Moves lane", "12/1/2027"),
    ("Lane A", "Spaced Spelling", "1/1/2028"),
)
#: tests/reports/test_onepager_compare_repeats.py PRIOR_D / CURRENT_D (header-less).
REPEATS_PRIOR_D: tuple[_Row, ...] = (
    ("Alpha", "Design Review", "1/15/2027", "Complete"),
    ("Alpha", "Build", "2/1/2027 - 4/1/2027", "In Progress"),
    ("Alpha", "Reopened", "2/10/2027", "Complete"),
    ("Alpha", "Moved after done", "2/12/2027", "Done"),
    ("Beta", "Dropped when done", "1/20/2027", "Complete"),
    ("Beta", "Twin", "3/1/2027", "Complete"),
    ("Beta", "Twin", "4/1/2027", ""),
)
REPEATS_CURRENT_D: tuple[_Row, ...] = (
    ("Alpha", "Design Review", "1/15/2027", "Complete"),
    ("Alpha", "Build", "2/1/2027 - 4/20/2027", "Complete"),
    ("Alpha", "Reopened", "2/10/2027", "In Progress"),
    ("Alpha", "Moved after done", "2/20/2027", "Done"),
    ("Beta", "Brand new", "5/1/2027", "Complete"),
    ("Beta", "Twin", "3/1/2027", "Complete"),
    ("Beta", "Twin", "4/5/2027", "Waiting on vendor"),
)
#: tests/reports/test_onepager_completion.py ROWS_WITH_D.
COMPLETION_ROWS_WITH_D: tuple[_Row, ...] = (
    ("Swimlane", "Task", "Date", "Status"),
    ("Alpha", "Design Review", "1/15/2027", "Complete"),
    ("Alpha", "Build", "2/1/2027 - 4/1/2027", "In Progress"),
    ("Alpha", "Test", "5/1/2027", ""),
    ("Beta", "Ship", "6/1/2027", "Waiting on vendor"),
    ("Beta", "Launch", "7/1/2027", "Waiting on vendor"),
    ("Beta", "Close", "8/1/2027", "Finished Late"),
)
#: tests/reports/test_onepager.py (the check on the single-list slide).
ONEPAGER_CHECK_ROWS: tuple[_Row, ...] = (
    ("Swimlane", "Task", "Date", "Status"),
    ("A", "Wide finished bar", "1/5/2027 - 9/30/2027", "Complete"),
    ("A", "Open milestone", "3/1/2027", "In Progress"),
    ("B", "Done milestone at the edge", "12/20/2027", "Done"),
)

# ↓ computed on the PRISTINE tree 0b45eb2 (``parse_numbered_workbook`` over ``read_xlsx_numbered``
# of ``twin_xlsx(rows)``) — never by the parser under test; the guard passes on that tree too.
_TWIN_ITEMS: tuple[_Item, ...] = (
    ("Flight Manifests", "Boots 1", "2027-06-27", "2027-06-27", 3, None),
    ("Flight Manifests", "Boots 2", "2028-03-28", "2028-03-28", 4, None),
    ("Dallas", "Uncrewed Lander Campaign", "2027-04-20", "2027-06-20", 6, None),
    ("Dallas", "CDR", "2027-10-02", "2027-10-02", 7, None),
    ("Dallas", "Crewed Lander Campaign", "2028-03-15", "2028-07-10", 8, None),
    ("Crew Life", "MET Testing", "2026-12-01", "2027-04-15", 10, None),
    ("Crew Life", "MET On-Dock", "2026-10-15", "2026-10-15", 11, None),
    ("BobbySon", "Overall GTA Window", "2026-06-10", "2028-06-22", 13, None),
    ("BobbySon", "Stack No. 2 Testing", "2026-11-10", "2027-02-13", 14, None),
    (
        "GRC-Blue RR-6",
        "Screen Assembly, Design & Fabrication",
        "2026-05-01",
        "2026-11-30",
        16,
        None,
    ),
    ("GRC-Blue RR-6", "Build up, test, tear down", "2026-12-01", "2027-03-31", 17, None),
    ("GRC- (MCaRR-2)", "TRR", "2026-09-15", "2026-09-15", 19, None),
    ("GRC-(MCaRR-2)", "Life Testing", "2026-09-16", "2027-02-28", 20, None),
    ("GRC-MET Testing", "Prepare Test Rig", "2025-09-18", "2027-03-20", 22, None),
    ("GRC-MET Testing", "ECT Test", "2026-11-04", "2026-12-12", 24, None),
    ("GRC-MET Testing", "MET ATP for Hot-Fire", "2027-01-25", "2027-01-25", 25, None),
)
_TWIN_PROBLEM = (
    "row {n} (GRC-MET Testing · Blue Origin On-Dock): unreadable date “10/122/2026” — skipped"
)
_TWIN_NOTE = "row {n}: no swimlane name — placed under “GRC-MET Testing”"
_VENDOR = (
    "column D “Waiting on vendor” ({at}): not a status read as complete — drawn as not complete"
)


#: A header-less column D of status words plus one word the reader does not know is MIXED: the
#: older layout by the majority, and the page says so with the counts (worktree-only).
_MAJORITY_OLDER = (
    "column D holds 0 date(s), 6 status word(s) and 1 other value(s) — read as the older C "
    "date-or-range · D status (the majority); every row that does not fit is named below. To be "
    "certain, add the header row Swimlane · Task · Start · Finish · Complete, or choose the layout "
    "when you upload"
)


class Pinned:
    """One committed row set and what the pristine parser made of it. ``layout_note`` is the ONE
    worktree-only field: ``""`` (column D had no content — nothing to say), ``"older"`` (the
    older-layout sentence) or the literal majority sentence."""

    def __init__(
        self,
        rows: Sequence[_Row],
        items: tuple[_Item, ...],
        *,
        omit_blank: bool = False,
        problems: tuple[str, ...] = (),
        notes: tuple[str, ...] = (),
        completion_notes: tuple[str, ...] = (),
        layout_note: str = "",
    ) -> None:
        self.rows, self.items, self.omit_blank = rows, items, omit_blank
        self.problems, self.notes, self.completion_notes = problems, notes, completion_notes
        self.layout_note = layout_note


_TWIN_PROBLEMS = (_TWIN_PROBLEM.format(n=23),)
_TWIN_NOTES = (_TWIN_NOTE.format(n=25),)
PINNED: dict[str, Pinned] = {
    "twin": Pinned(TWIN_ROWS, _TWIN_ITEMS, problems=_TWIN_PROBLEMS, notes=_TWIN_NOTES),
    "twin-as-excel-writes-it": Pinned(
        TWIN_ROWS, _TWIN_ITEMS, omit_blank=True, problems=_TWIN_PROBLEMS, notes=_TWIN_NOTES
    ),
    "compare-page-current": Pinned(
        COMPARE_PAGE_CURRENT_ROWS,
        (
            ("Flight Manifests", "Boots 1", "2027-07-27", "2027-07-27", 3, None),
            ("Flight Manifests", "Boots 2", "2028-03-28", "2028-03-28", 4, None),
            ("Dallas", "Uncrewed Lander Campaign", "2027-04-20", "2027-06-20", 6, None),
            ("Dallas", "CDR", "2027-09-25", "2027-09-25", 7, None),
            ("Dallas", "Crewed Lander Campaign", "2028-03-15", "2028-07-10", 8, None),
            ("Crew Life", "MET On-Dock", "2026-10-15", "2026-10-15", 10, None),
            ("BobbySon", "Overall GTA Window", "2026-06-10", "2028-06-22", 12, None),
            ("BobbySon", "Stack No. 2 Testing", "2026-11-10", "2027-02-13", 13, None),
            (
                "GRC-Blue RR-6",
                "Screen Assembly, Design & Fabrication",
                "2026-05-01",
                "2026-11-30",
                15,
                None,
            ),
            ("GRC-Blue RR-6", "Build up, test, tear down", "2026-12-01", "2027-03-31", 16, None),
            ("GRC- (MCaRR-2)", "TRR", "2026-09-20", "2026-10-04", 18, None),
            ("GRC-(MCaRR-2)", "Life Testing", "2026-09-16", "2027-02-28", 19, None),
            ("GRC-MET Testing", "Prepare Test Rig", "2025-09-18", "2027-03-20", 21, None),
            ("GRC-MET Testing", "ECT Test", "2026-11-04", "2026-12-12", 23, None),
            ("GRC-MET Testing", "MET ATP for Hot-Fire", "2027-01-25", "2027-01-25", 24, None),
            ("Flight Manifests", "Boots 3", "2028-12-01", "2028-12-01", 25, None),
        ),
        problems=(_TWIN_PROBLEM.format(n=22),),
        notes=(_TWIN_NOTE.format(n=24),),
    ),
    "window-page-current": Pinned(
        WINDOW_PAGE_CURRENT_ROWS,
        tuple(
            ("Flight Manifests", "Boots 1", "2027-09-01", "2027-09-01", 3, None)
            if it[1] == "Boots 1"
            else ("Crew Life", "MET On-Dock", "2027-02-01", "2027-02-01", 11, None)
            if it[1] == "MET On-Dock"
            else it
            for it in _TWIN_ITEMS
        ),
        problems=_TWIN_PROBLEMS,
        notes=_TWIN_NOTES,
    ),
    "compare-page-prior-d": Pinned(
        COMPARE_PAGE_PRIOR_D,
        (
            ("Alpha", "Design Review", "2027-01-15", "2027-01-15", 2, True),
            ("Alpha", "Design Review", "2027-05-15", "2027-05-15", 3, False),
            ("Alpha", "Build", "2027-02-01", "2027-04-01", 4, False),
            ("Beta", "Reopened", "2027-02-10", "2027-02-10", 6, True),
            ("Beta", "Dropped", "2027-01-20", "2027-01-20", 7, True),
        ),
        omit_blank=True,
        layout_note="older",
    ),
    "compare-page-current-d": Pinned(
        COMPARE_PAGE_CURRENT_D,
        (
            ("Alpha", "Design Review", "2027-01-15", "2027-01-15", 2, True),
            ("Alpha", "Design Review", "2027-05-15", "2027-05-15", 3, False),
            ("Alpha", "Build", "2027-02-01", "2027-04-20", 4, True),
            ("Beta", "Reopened", "2027-02-10", "2027-02-10", 6, False),
            ("Beta", "Brand new", "2027-05-01", "2027-05-01", 7, False),
        ),
        omit_blank=True,
        completion_notes=(_VENDOR.format(at="row 7"),),
        layout_note="older",
    ),
    "compare-prior": Pinned(
        COMPARE_PRIOR_ROWS,
        (
            ("Lane A", "Slips", "2027-01-10", "2027-03-01", 2, None),
            ("Lane A", "Pulls in", "2027-02-01", "2027-06-30", 3, None),
            ("Lane A", "Steady", "2027-04-01", "2027-05-01", 4, None),
            ("Lane A", "Starts later", "2027-05-01", "2027-08-01", 5, None),
            ("Lane A", "Old name", "2027-07-07", "2027-07-07", 6, None),
            ("Lane B", "Was a milestone", "2027-09-09", "2027-09-09", 7, None),
            ("Lane B", "Gone", "2027-10-01", "2027-10-01", 8, None),
            ("Lane B", "Twin", "2027-11-01", "2027-11-01", 9, None),
            ("Lane B", "Twin", "2027-11-05", "2027-11-05", 10, None),
            ("Lane B", "Moves lane", "2027-12-01", "2027-12-01", 11, None),
            ("Lane  A", "spaced  spelling", "2028-01-01", "2028-01-01", 12, None),
        ),
    ),
    "compare-current": Pinned(
        COMPARE_CURRENT_ROWS,
        (
            ("Lane A", "Slips", "2027-01-10", "2027-03-31", 2, None),
            ("Lane A", "Pulls in", "2027-02-01", "2027-06-15", 3, None),
            ("Lane A", "Steady", "2027-04-01", "2027-05-01", 4, None),
            ("Lane A", "Starts later", "2027-05-15", "2027-08-01", 5, None),
            ("Lane A", "New name", "2027-07-07", "2027-07-07", 6, None),
            ("Lane A", "Brand new", "2027-08-08", "2027-08-08", 7, None),
            ("Lane B", "Was a milestone", "2027-09-01", "2027-09-30", 8, None),
            ("Lane B", "Twin", "2027-11-03", "2027-11-03", 9, None),
            ("Lane C", "Moves lane", "2027-12-01", "2027-12-01", 10, None),
            ("Lane A", "Spaced Spelling", "2028-01-01", "2028-01-01", 11, None),
        ),
    ),
    "repeats-prior-d": Pinned(
        REPEATS_PRIOR_D,
        (
            ("Alpha", "Design Review", "2027-01-15", "2027-01-15", 1, True),
            ("Alpha", "Build", "2027-02-01", "2027-04-01", 2, False),
            ("Alpha", "Reopened", "2027-02-10", "2027-02-10", 3, True),
            ("Alpha", "Moved after done", "2027-02-12", "2027-02-12", 4, True),
            ("Beta", "Dropped when done", "2027-01-20", "2027-01-20", 5, True),
            ("Beta", "Twin", "2027-03-01", "2027-03-01", 6, True),
            ("Beta", "Twin", "2027-04-01", "2027-04-01", 7, False),
        ),
        layout_note="older",
    ),
    "repeats-current-d": Pinned(
        REPEATS_CURRENT_D,
        (
            ("Alpha", "Design Review", "2027-01-15", "2027-01-15", 1, True),
            ("Alpha", "Build", "2027-02-01", "2027-04-20", 2, True),
            ("Alpha", "Reopened", "2027-02-10", "2027-02-10", 3, False),
            ("Alpha", "Moved after done", "2027-02-20", "2027-02-20", 4, True),
            ("Beta", "Brand new", "2027-05-01", "2027-05-01", 5, True),
            ("Beta", "Twin", "2027-03-01", "2027-03-01", 6, True),
            ("Beta", "Twin", "2027-04-05", "2027-04-05", 7, False),
        ),
        completion_notes=(_VENDOR.format(at="row 7"),),
        # no date in column D at all: the older layout by every count, nothing mixed to explain
        layout_note="older",
    ),
    "completion-rows-with-d": Pinned(
        COMPLETION_ROWS_WITH_D,
        (
            ("Alpha", "Design Review", "2027-01-15", "2027-01-15", 2, True),
            ("Alpha", "Build", "2027-02-01", "2027-04-01", 3, False),
            ("Alpha", "Test", "2027-05-01", "2027-05-01", 4, False),
            ("Beta", "Ship", "2027-06-01", "2027-06-01", 5, False),
            ("Beta", "Launch", "2027-07-01", "2027-07-01", 6, False),
            ("Beta", "Close", "2027-08-01", "2027-08-01", 7, True),
        ),
        completion_notes=(_VENDOR.format(at="rows 5, 6"),),
        layout_note="older",
    ),
    "onepager-check-rows": Pinned(
        ONEPAGER_CHECK_ROWS,
        (
            ("A", "Wide finished bar", "2027-01-05", "2027-09-30", 2, True),
            ("A", "Open milestone", "2027-03-01", "2027-03-01", 3, False),
            ("B", "Done milestone at the edge", "2027-12-20", "2027-12-20", 4, True),
        ),
        layout_note="older",
    ),
}


def _assert_as_pristine(p: Pinned, doc: op.OnePagerDoc) -> None:
    assert _items(doc) == p.items
    assert (doc.problems, doc.notes, doc.completion_notes) == (
        p.problems,
        p.notes,
        p.completion_notes,
    )


@pytest.mark.parametrize("name", PINNED)
def test_every_committed_row_set_parses_exactly_as_on_the_pristine_tree(name: str) -> None:
    """Items (lane, name, start, finish, row, complete), skipped rows, notes and status notes —
    identical to the pristine parser's, so no older sheet the suite already knows draws, counts or
    names anything differently under the two-layout reader."""
    p = PINNED[name]
    _assert_as_pristine(p, _doc(p.rows, omit_blank=p.omit_blank))


@pytest.mark.parametrize("name", PINNED)
def test_every_committed_row_set_is_read_in_the_older_layout(name: str) -> None:
    """...and each is read in the older layout, stating so exactly when column D had content (a
    mixed header-less column by the majority, with its counts), with no layout problem."""
    p = PINNED[name]
    doc = _doc(p.rows, omit_blank=p.omit_blank)
    assert doc.layout == op.DATE_STATUS
    assert doc.status_column == ("D" if p.layout_note else "")
    assert doc.layout_note == (op.OLDER_LAYOUT_NOTE if p.layout_note == "older" else p.layout_note)
    assert not any("could not be decided" in x for x in doc.problems)


# ── mutation proofs: each load-bearing rule broken, and its checker observed to go red ───────


def test_mutation_detection_forced_to_the_current_layout_turns_the_checks_red(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If every sheet were read as C start · D finish (PLAN v1's failure), the older fixture
    mis-parses — its status words refused as finish dates — and BOTH the detection checker and
    the regression guard go red."""
    monkeypatch.setattr(op, "detect_layout", lambda rows, header: op.LayoutRead(op.START_FINISH))
    broken = _doc(LEGACY_ROWS)
    with pytest.raises(AssertionError):
        _assert_reads_older(broken, LEGACY_ITEMS)
    assert broken.items == ()
    assert len(broken.problems) == 3
    assert all("the status belongs in column E" in x for x in broken.problems)
    p = PINNED["compare-page-prior-d"]
    with pytest.raises(AssertionError):
        _assert_as_pristine(p, _doc(p.rows, omit_blank=p.omit_blank))


def test_mutation_a_substring_header_match_turns_the_header_check_red(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PLAN v1's substring rule: "Pending", "Trend", "Overdue" and "Vendor" then read as a
    finish — every attack case flips to the current layout and the header checker goes red."""
    monkeypatch.setattr(op, "_FINISH_HEAD_RE", re.compile(r"finish|end|due", re.IGNORECASE))
    flipped = _d_header_verdicts()
    for head, _d, want in D_HEADER_CASES:
        if want == op.DATE_STATUS:
            assert flipped[head] == op.START_FINISH, head
    with pytest.raises(AssertionError):
        _assert_d_header_verdicts()


class _AnyWeekday:
    """Every weekday name, at once: a date's weekday check that can never fail."""

    def __getitem__(self, _index: int) -> _AnyWeekday:
        return self

    def __eq__(self, _other: object) -> bool:
        return True

    def __ne__(self, _other: object) -> bool:
        return False

    __hash__ = object.__hash__


def test_mutation_a_weekday_dropped_unchecked_turns_the_contradiction_check_red(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the weekday were stripped without being checked, "Mon 9/1/26" (a Tuesday) would read
    as 9/1/26 — a contradiction resolved by picking a side — and the checker goes red."""
    monkeypatch.setattr(op, "_WEEKDAYS", _AnyWeekday())
    assert op.parse_date("Mon 9/1/26") == (D(2026, 9, 1), D(2026, 9, 1))
    with pytest.raises(AssertionError):
        _assert_weekday_contradictions_refused()
