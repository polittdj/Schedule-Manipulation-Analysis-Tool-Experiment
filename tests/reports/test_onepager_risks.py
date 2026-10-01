"""The One-Pager risk register reader (:mod:`schedule_forensics.reports.onepager_risks`).

ADR-0544 (LODESTAR 2.1). A risk workbook is A swimlane · B risk · C potential impact · D
probability · E date of occurrence, or any order a header row names. Every decision the reader
makes — which column a role came from, an inherited swimlane, a skipped row, a month-only date,
a converted unit, a probability it could not read — is pinned here by its sentence, and every
rule has a ``test_mutation_*`` twin that breaks the rule in memory and asserts the SAME checker
goes red (QC-1: a check that has never failed has proven nothing).

Oracles are typed literals; nothing is read off the module under test.

Red-first (2026-10-01): written before ``onepager_risks.py`` existed and observed to fail at
import (``ModuleNotFoundError``).
"""

from __future__ import annotations

import datetime as dt
import io
import re
import zipfile
from collections.abc import Callable, Iterable

import pytest

from schedule_forensics.reports import onepager_risks as mod
from schedule_forensics.reports.onepager_risks import (
    RISK_TEMPLATE_HEADER,
    RISK_TEMPLATE_ROWS,
    OnePagerRisk,
    RiskDoc,
    header_roles,
    impact_label,
    parse_risk_workbook,
    read_impact,
    read_probability,
    read_risk_sheet,
    read_risks,
    risk_keys,
    risk_label,
    risk_template,
    risk_when,
    risks_table,
    risks_tables,
)
from schedule_forensics.reports.xlsx import render_xlsx
from schedule_forensics.reports.xlsx_read import read_xlsx_numbered
from web.onepager_twin import twin_xlsx

# ── helpers ───────────────────────────────────────────────────────────────────────────────────

_SHUFFLED_HEADER = ("Swimlane", "Risk", "Date of occurrence", "Probability", "Impact (days)")
_SHUFFLED_ROW = ("Flight Manifests", "Engine slip", "3/15/2027", "High", 30)
_POSITIONAL_ROW = ("Flight Manifests", "Engine slip", 30, "High", "3/15/2027")


def _doc(rows: Iterable[tuple[object, ...]], source: str = "risks.xlsx") -> RiskDoc:
    """The register the reader builds from a twin workbook — the whole intake path."""
    sheets = read_xlsx_numbered(twin_xlsx(rows), max_columns=6, booleans_as_text=True)
    return parse_risk_workbook(sheets, source)


def _risk(**over: object) -> OnePagerRisk:
    base: dict[str, object] = {
        "lane": "Flight Manifests",
        "name": "Engine slip",
        "date": dt.date(2027, 3, 15),
        "impact_text": "30",
        "impact_days": 30,
        "prob": "high",
        "row": 2,
    }
    base.update(over)
    return OnePagerRisk(**base)  # type: ignore[arg-type]


def _one_shuffled(doc: RiskDoc) -> None:
    """THE checker for the header-driven read: one risk, every field from its named column."""
    assert len(doc.risks) == 1, (doc.problems, doc.notes)
    r = doc.risks[0]
    assert (r.lane, r.name, r.date) == ("Flight Manifests", "Engine slip", dt.date(2027, 3, 15))
    assert (r.impact_text, r.impact_days, r.prob, r.row) == ("30", 30, "high", 2)
    assert doc.problems == ()
    assert doc.notes == (
        "header (row 1): date of occurrence read from column C, potential impact from column E",
    )


# ── the header row drives the columns ─────────────────────────────────────────────────────────


def test_header_drives_columns_in_shuffled_order() -> None:
    _one_shuffled(_doc([_SHUFFLED_HEADER, _SHUFFLED_ROW]))


def test_mutation_header_unrecognised_breaks_shuffled_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Break ``header_roles`` so no row is a header: the columns fall back to positional and
    ``test_header_drives_columns_in_shuffled_order``'s checker goes red."""
    monkeypatch.setattr(mod, "header_roles", lambda cells: {})
    with pytest.raises(AssertionError):
        _one_shuffled(_doc([_SHUFFLED_HEADER, _SHUFFLED_ROW]))


def test_header_in_positional_order_makes_no_column_note() -> None:
    doc = _doc([RISK_TEMPLATE_HEADER, _POSITIONAL_ROW])
    assert len(doc.risks) == 1 and doc.problems == () and doc.notes == ()


def test_header_roles_vocabulary_and_priority() -> None:
    assert header_roles(list(RISK_TEMPLATE_HEADER)) == {
        "lane": 0,
        "name": 1,
        "impact": 2,
        "prob": 3,
        "date": 4,
    }
    # the contract's words, each alone
    assert header_roles(["Lane", "Title", "Delay", "Likelihood", "When"]) == {
        "lane": 0,
        "name": 1,
        "impact": 2,
        "prob": 3,
        "date": 4,
    }
    assert header_roles(["Swim lane", "Risk name", "Duration", "Chance", "Occurs"]) == {
        "lane": 0,
        "name": 1,
        "impact": 2,
        "prob": 3,
        "date": 4,
    }
    # a cell naming two roles is the more specific one: "Risk impact" is the impact, not the name
    assert header_roles(["Swimlane", "Risk", "Risk impact"]) == {"lane": 0, "name": 1, "impact": 2}
    # the FIRST column claiming a role keeps it
    assert header_roles(["Risk", "Risk name", "Impact"]) == {"name": 0, "impact": 2}


def test_header_roles_refuses_a_data_row() -> None:
    """A first DATA row is never mistaken for the header: one whose date cell reads as a date,
    or that carries a bare number (an impact), even when its words look like a header."""
    assert header_roles(["Dallas lane", "Launch date slip", "x", "High", "6/1/27"]) == {}
    assert header_roles(["Dallas lane", "Launch date slip", "30", "High", ""]) == {}
    assert header_roles(["Only one role here", "x", "y"]) == {}
    doc = _doc([("Dallas lane", "Launch date slip", 30, "High", "6/1/27")])
    assert len(doc.risks) == 1 and doc.risks[0].name == "Launch date slip"


def test_mutation_header_roles_date_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without the date guard, the data row above IS read as a header (its words match two
    roles) and the register loses its only risk."""
    monkeypatch.setattr(mod, "parse_date", lambda text: None)
    assert header_roles(["Dallas lane", "Launch date slip", "x", "High", "6/1/27"]) != {}


def test_mutation_header_roles_number_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without the bare-number guard, a dateless data row carrying an impact IS a header."""
    monkeypatch.setattr(mod, "_NUMBER_RE", re.compile(r"(?!x)x"))
    assert header_roles(["Dallas lane", "Launch date slip", "30", "High", ""]) != {}


def test_header_missing_role_whose_column_is_claimed_is_absent() -> None:
    """A header with no probability column, whose column D is the date: the probability is
    NOT read from D positionally — it is absent, and every row says so."""
    doc = _doc([("Swimlane", "Risk", "Impact", "Date"), ("Dallas", "Range closure", 21, "5/10/27")])
    assert len(doc.risks) == 1
    assert doc.risks[0].prob == "unknown" and doc.risks[0].date == dt.date(2027, 5, 10)
    assert "row 2 (Dallas · Range closure): no probability — drawn as unknown" in doc.notes


# ── no header: positional A-E ─────────────────────────────────────────────────────────────────


def _one_positional(doc: RiskDoc) -> None:
    assert len(doc.risks) == 1, (doc.problems, doc.notes)
    r = doc.risks[0]
    assert (r.lane, r.name, r.date) == ("Flight Manifests", "Engine slip", dt.date(2027, 3, 15))
    assert (r.impact_text, r.impact_days, r.prob, r.row) == ("30", 30, "high", 1)
    assert doc.problems == () and doc.notes == ()


def test_no_header_reads_positional_columns() -> None:
    _one_positional(_doc([_POSITIONAL_ROW]))
    read = read_risk_sheet([list(map(str, _POSITIONAL_ROW))], None)
    assert read.header is None
    assert read.columns == {"lane": 0, "name": 1, "impact": 2, "prob": 3, "date": 4}


def test_mutation_positional_table(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        mod, "POSITIONAL", {"lane": 0, "name": 1, "impact": 4, "prob": 3, "date": 2}
    )
    with pytest.raises(AssertionError):
        _one_positional(_doc([_POSITIONAL_ROW]))


def test_row_numbers_are_the_rows_excel_shows() -> None:
    """A spacer row and the header are skipped, and the risk's row is its Excel row number."""
    doc = _doc([RISK_TEMPLATE_HEADER, (), (), _POSITIONAL_ROW])
    assert [r.row for r in doc.risks] == [4]


# ── swimlane inheritance ──────────────────────────────────────────────────────────────────────


def _inherited(doc: RiskDoc) -> None:
    assert [(r.lane, r.name) for r in doc.risks] == [
        ("Flight Manifests", "Engine slip"),
        ("Flight Manifests", "Second"),
    ]
    assert doc.notes == ("row 2: no swimlane name — placed under “Flight Manifests”",)


def test_missing_swimlane_inherits_the_one_above() -> None:
    _inherited(_doc([_POSITIONAL_ROW, ("", "Second", 5, "Low", "4/1/2027")]))


def test_missing_swimlane_with_none_above_is_skipped() -> None:
    doc = _doc([("", "Second", 5, "Low", "4/1/2027")])
    assert doc.risks == ()
    assert doc.problems == ("row 1: no swimlane name and none above it — skipped",)


def test_mutation_inherited_note(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mod, "INHERITED", "row {row}: swimlane assumed")
    with pytest.raises(AssertionError):
        _inherited(_doc([_POSITIONAL_ROW, ("", "Second", 5, "Low", "4/1/2027")]))


# ── a missing name ────────────────────────────────────────────────────────────────────────────


def _no_name(doc: RiskDoc) -> None:
    assert doc.risks == ()
    assert doc.problems == ("row 1 (Flight Manifests): no risk name — skipped",)


def test_missing_name_is_skipped_and_named() -> None:
    _no_name(_doc([("Flight Manifests", "", 30, "High", "3/15/2027")]))


def test_mutation_no_name_sentence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mod, "NO_NAME", "row {row}: unnamed")
    with pytest.raises(AssertionError):
        _no_name(_doc([("Flight Manifests", "", 30, "High", "3/15/2027")]))


# ── the date of occurrence ────────────────────────────────────────────────────────────────────


def _bad_dates(doc: RiskDoc) -> None:
    assert doc.risks == ()
    assert doc.problems == (
        "row 1 (Dallas · Range closure): unreadable date of occurrence “10/122/2027” — skipped",
        "row 2 (Dallas · Strike): no date of occurrence — skipped",
    )


def test_unreadable_or_missing_date_is_skipped_and_named() -> None:
    _bad_dates(
        _doc(
            [
                ("Dallas", "Range closure", 21, "Medium", "10/122/2027"),
                ("Dallas", "Strike", 21, "Medium", ""),
            ]
        )
    )


def test_mutation_unreadable_date(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every token a date: the unreadable row is no longer skipped and the checker is
    red by name."""
    monkeypatch.setattr(mod, "parse_date", lambda text: (dt.date(2027, 1, 1), dt.date(2027, 1, 1)))
    with pytest.raises(AssertionError):
        _bad_dates(
            _doc(
                [
                    ("Dallas", "Range closure", 21, "Medium", "10/122/2027"),
                    ("Dallas", "Strike", 21, "Medium", ""),
                ]
            )
        )


def _month_only(doc: RiskDoc) -> None:
    assert len(doc.risks) == 1 and doc.risks[0].date == dt.date(2027, 5, 1)
    assert doc.notes == (
        "row 1 (Dallas · Range closure): “05/2027” names a month, not a day — placed on its "
        "first day 5/1/27",
    )


def test_month_only_date_is_its_first_day_and_noted() -> None:
    _month_only(_doc([("Dallas", "Range closure", 21, "Medium", "05/2027")]))


def test_mutation_month_only_takes_the_first_day(monkeypatch: pytest.MonkeyPatch) -> None:
    """Swap the span the date reader hands back so its FIRST element is the month's last day:
    a reader that takes the first day of the span now places the risk on the 31st."""
    monkeypatch.setattr(mod, "parse_date", lambda text: (dt.date(2027, 5, 31), dt.date(2027, 5, 1)))
    with pytest.raises(AssertionError):
        _month_only(_doc([("Dallas", "Range closure", 21, "Medium", "05/2027")]))


def test_date_forms_the_list_reads() -> None:
    """An Excel serial, an ISO date and a two-digit year — ``parse_date``'s forms, reused."""
    doc = _doc(
        [
            ("A", "serial", 1, "High", 46565),
            ("A", "iso", 1, "High", "2027-06-27"),
            ("A", "short", 1, "High", "6/27/27"),
        ]
    )
    assert [r.date for r in doc.risks] == [dt.date(2027, 6, 27)] * 3


# ── the potential impact ──────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("text", "days", "unit"),
    [
        ("30", 30, ""),
        ("+30", 30, ""),
        ("-5", -5, ""),
        ("2.5", 3, ""),
        ("5 d", 5, "day"),
        ("5 day", 5, "day"),
        ("10 days", 10, "day"),
        ("30 cal d", 30, "day"),
        ("30 calendar days", 30, "day"),
        ("2 w", 14, "week"),
        ("3 wk", 21, "week"),
        ("3 wks", 21, "week"),
        ("1 week", 7, "week"),
        ("2 weeks", 14, "week"),
        ("2weeks", 14, "week"),
        ("1 mo", 30, "month"),
        ("2 mos", 60, "month"),
        ("1 month", 30, "month"),
        ("2 months", 60, "month"),
        ("2 Months.", 60, "month"),
        ("10 wd", None, ""),
        ("10 working days", None, ""),
        ("two weeks", None, ""),
        ("", None, ""),
    ],
)
def test_read_impact(text: str, days: int | None, unit: str) -> None:
    assert read_impact(text) == (days, unit)


def _units(doc: RiskDoc) -> None:
    assert [(r.impact_text, r.impact_days) for r in doc.risks] == [
        ("30", 30),
        ("3 wk", 21),
        ("2 weeks", 14),
        ("1 mo", 30),
        ("10 days", 10),
        ("10 working days", None),
        ("", None),
    ]
    assert doc.notes == (
        "row 6 (A · f): potential impact “10 working days” kept as typed — not read as calendar "
        "days",
        "row 7 (A · g): no potential impact",
        "potential impact in weeks converted at 7 calendar days per week (rows 2, 3)",
        "potential impact in months converted at 30 calendar days per month (row 4)",
    )


def test_impact_units_converted_and_noted_once_per_unit() -> None:
    _units(
        _doc(
            [
                ("A", "a", 30, "High", "1/1/27"),
                ("A", "b", "3 wk", "High", "1/1/27"),
                ("A", "c", "2 weeks", "High", "1/1/27"),
                ("A", "d", "1 mo", "High", "1/1/27"),
                ("A", "e", "10 days", "High", "1/1/27"),
                ("A", "f", "10 working days", "High", "1/1/27"),
                ("A", "g", "", "High", "1/1/27"),
            ]
        )
    )


def test_mutation_unit_table_wk_not_times_seven(monkeypatch: pytest.MonkeyPatch) -> None:
    """``wk`` no longer x7: "3 wk" reads as 3 and the units checker is red by name."""
    monkeypatch.setitem(mod.UNITS, "wk", (1, "week"))
    with pytest.raises(AssertionError):
        _units(
            _doc(
                [
                    ("A", "a", 30, "High", "1/1/27"),
                    ("A", "b", "3 wk", "High", "1/1/27"),
                    ("A", "c", "2 weeks", "High", "1/1/27"),
                    ("A", "d", "1 mo", "High", "1/1/27"),
                    ("A", "e", "10 days", "High", "1/1/27"),
                    ("A", "f", "10 working days", "High", "1/1/27"),
                    ("A", "g", "", "High", "1/1/27"),
                ]
            )
        )


# ── the probability ───────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("text", "prob"),
    [
        ("High", "high"),
        ("HIGH", "high"),
        ("h", "high"),
        ("Hi", "high"),
        ("Red", "high"),
        ("High (80%)", "high"),
        ("high - likely", "high"),
        ("Medium", "medium"),
        ("Med", "medium"),
        ("m", "medium"),
        ("Moderate", "medium"),
        ("Amber", "medium"),
        ("Yellow", "medium"),
        ("Low", "low"),
        ("l", "low"),
        ("Lo", "low"),
        ("Green", "low"),
        ("low.", "low"),
        ("Likely", "unknown"),
        ("Highest", "unknown"),  # "high" followed by a letter is another word
        ("Hm", "unknown"),
        ("", "unknown"),
        ("80%", "unknown"),
    ],
)
def test_read_probability(text: str, prob: str) -> None:
    assert read_probability(text) == prob


def _probs(doc: RiskDoc) -> None:
    assert [r.prob for r in doc.risks] == ["high", "medium", "low", "medium", "unknown", "unknown"]
    assert doc.notes == (
        "row 5 (A · e): probability “Likely” is not High, Medium or Low — drawn as unknown",
        "row 6 (A · f): no probability — drawn as unknown",
    )


def test_unknown_probability_is_named_by_row() -> None:
    _probs(
        _doc(
            [
                ("A", "a", 1, "High", "1/1/27"),
                ("A", "b", 1, "med", "1/1/27"),
                ("A", "c", 1, "green", "1/1/27"),
                ("A", "d", 1, "Amber", "1/1/27"),
                ("A", "e", 1, "Likely", "1/1/27"),
                ("A", "f", 1, "", "1/1/27"),
            ]
        )
    )


def test_mutation_probability_words(monkeypatch: pytest.MonkeyPatch) -> None:
    """Drop "amber" from the word table: row 4 reads unknown, named, and the checker is red."""
    monkeypatch.delitem(mod.PROB_WORDS, "amber")
    with pytest.raises(AssertionError):
        _probs(
            _doc(
                [
                    ("A", "a", 1, "High", "1/1/27"),
                    ("A", "b", 1, "med", "1/1/27"),
                    ("A", "c", 1, "green", "1/1/27"),
                    ("A", "d", 1, "Amber", "1/1/27"),
                    ("A", "e", 1, "Likely", "1/1/27"),
                    ("A", "f", 1, "", "1/1/27"),
                ]
            )
        )


# ── keys ──────────────────────────────────────────────────────────────────────────────────────


def _keys_stable() -> None:
    a = _risk(row=2)
    b = _risk(row=9, lane="flight  manifests", impact_text="5", impact_days=5, prob="low")
    c = _risk(date=dt.date(2027, 3, 16))
    assert risk_keys([a]) == risk_keys([b]), "lane spelling, row, impact, probability: no effect"
    assert risk_keys([a]) != risk_keys([c]), "the date is part of the identity"
    assert risk_keys([a, a]) == [risk_keys([a])[0], risk_keys([a, a])[1]]
    assert len(set(risk_keys([a, a]))) == 2, "identical copies are told apart by order"
    assert all(len(k) == 16 and int(k, 16) >= 0 for k in risk_keys([a, b, c]))


def test_risk_keys_stable_across_spelling_row_and_position() -> None:
    _keys_stable()


def test_mutation_keys_lane_normalisation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mod, "_lane_key", lambda name: name)
    with pytest.raises(AssertionError):
        _keys_stable()


def test_document_risks_carry_their_keys() -> None:
    doc = _doc([_POSITIONAL_ROW, ("Dallas", "Range closure", 21, "Medium", "5/10/27")])
    assert [r.key for r in doc.risks] == risk_keys(doc.risks)
    assert len({r.key for r in doc.risks}) == 2


# ── the template reads back clean ─────────────────────────────────────────────────────────────


def _template_clean(doc: RiskDoc) -> None:
    assert doc.problems == () and doc.notes == ()
    assert len(doc.risks) == 4
    assert {r.prob for r in doc.risks} == {"high", "medium", "low"}
    assert all(r.impact_days is not None for r in doc.risks)


def test_template_reads_back_with_zero_problems() -> None:
    ts = risk_template()
    assert ts.tables[0].headers == RISK_TEMPLATE_HEADER
    assert RISK_TEMPLATE_HEADER == (
        "Swimlane Name",
        "Risk",
        "Potential impact (days)",
        "Probability (High / Medium / Low)",
        "Date of occurrence",
    )
    sheets = read_xlsx_numbered(render_xlsx(ts), max_columns=6, booleans_as_text=True)
    _template_clean(parse_risk_workbook(sheets, "template.xlsx"))


def test_mutation_template_row_breaks_the_read_back(monkeypatch: pytest.MonkeyPatch) -> None:
    bad = (*RISK_TEMPLATE_ROWS[:3], ("Dallas", "Bad date", 21, "Medium", "10/122/2027"))
    monkeypatch.setattr(mod, "RISK_TEMPLATE_ROWS", bad)
    sheets = read_xlsx_numbered(render_xlsx(risk_template()), max_columns=6, booleans_as_text=True)
    with pytest.raises(AssertionError):
        _template_clean(parse_risk_workbook(sheets, "template.xlsx"))


# ── an empty workbook ─────────────────────────────────────────────────────────────────────────


def _empty(doc: RiskDoc) -> None:
    assert doc.risks == () and doc.sheet == ""
    assert doc.problems == ("the workbook has no rows",)


def test_empty_workbook_sentence() -> None:
    _empty(_doc([()]))
    _empty(parse_risk_workbook({}, "risks.xlsx"))
    _empty(parse_risk_workbook({"Sheet1": [(1, ["", "", ""])]}, "risks.xlsx"))


def test_mutation_empty_sentence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mod, "NO_ROWS", "nothing here")
    with pytest.raises(AssertionError):
        _empty(_doc([()]))


def _rows_round_trip(doc: RiskDoc) -> None:
    """The document carries its rows AS READ, and re-parsing them gives the same document."""
    assert doc.rows == (
        (1, ("Swimlane", "Risk", "Date of occurrence", "Probability", "Impact (days)")),
        (2, ("Flight Manifests", "Engine slip", "3/15/2027", "High", "30")),
        (3, ("", "Second", "4/1/2027", "Low", "5")),
    )
    again = parse_risk_workbook({doc.sheet: [(n, list(c)) for n, c in doc.rows]}, doc.source)
    assert again == doc


def test_document_carries_its_rows_as_read_for_the_payload() -> None:
    _rows_round_trip(_doc([_SHUFFLED_HEADER, _SHUFFLED_ROW, ("", "Second", "4/1/2027", "Low", 5)]))


def test_mutation_rows_as_read(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip the cells before they are kept: the rows are no longer the sheet's own, and the
    re-parse checker goes red (the blank swimlane cell is what the mutation drops)."""
    original = mod.read_risk_sheet

    def shorter(rows: list[list[str]], numbers: list[int] | None = None) -> mod.RiskSheetRead:
        for row in rows:
            if row and row[0] == "":
                row.pop(0)
        return original(rows, numbers)

    monkeypatch.setattr(mod, "read_risk_sheet", shorter)
    with pytest.raises(AssertionError):
        _rows_round_trip(
            _doc([_SHUFFLED_HEADER, _SHUFFLED_ROW, ("", "Second", "4/1/2027", "Low", 5)])
        )


def test_first_sheet_with_content_is_the_register() -> None:
    sheets = {"Cover": [(1, ["", ""])], "Risks": [(1, list(map(str, _POSITIONAL_ROW)))]}
    doc = parse_risk_workbook(sheets, "risks.xlsx")
    assert doc.sheet == "Risks" and len(doc.risks) == 1 and doc.source == "risks.xlsx"


# ── read_risks: the upload's sentences ────────────────────────────────────────────────────────


def test_read_risks_size_cap_sentence() -> None:
    data = twin_xlsx([_POSITIONAL_ROW])
    doc = read_risks(data, "risks.xlsx", max_bytes=len(data))
    assert isinstance(doc, RiskDoc) and doc.source == "risks.xlsx" and len(doc.risks) == 1
    assert read_risks(data, "risks.xlsx", max_bytes=len(data) - 1) == (
        "Risks not loaded — file exceeds the 0 MB cap."
    )
    assert read_risks(data, "risks.xlsx", max_bytes=2 * 1024 * 1024 - 1) != (
        "Risks not loaded — file exceeds the 1 MB cap."
    )
    big = b"x" * (2 * 1024 * 1024 + 1)
    assert read_risks(big, "r.xlsx", max_bytes=2 * 1024 * 1024) == (
        "Risks not loaded — file exceeds the 2 MB cap."
    )


def test_read_risks_unreadable_workbook_sentence() -> None:
    out = read_risks(b"not a workbook", "risks.xlsx", max_bytes=1024)
    assert isinstance(out, str) and out.startswith("Could not read that file: ")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("hello.txt", "x")
    out = read_risks(buf.getvalue(), "risks.xlsx", max_bytes=1024)
    assert isinstance(out, str) and out.startswith("Could not read that file: ")


# ── labels and tables ─────────────────────────────────────────────────────────────────────────


def _labels() -> None:
    assert risk_when(_risk()) == "3/15/27"
    assert risk_label(_risk()) == "RISK · Engine slip (3/15/27)"
    assert risk_label(_risk(date=dt.date(2028, 12, 1))) == "RISK · Engine slip (12/1/28)"
    assert impact_label(_risk()) == "impact +30 cal d"
    assert impact_label(_risk(impact_text="-5", impact_days=-5)) == "impact -5 cal d"
    assert impact_label(_risk(impact_text="10 wd", impact_days=None)) == "impact: 10 wd"
    assert impact_label(_risk(impact_text="", impact_days=None)) == ""


def test_risk_and_impact_labels() -> None:
    _labels()


def test_mutation_label_date(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mod, "mdy", lambda d: d.isoformat())
    with pytest.raises(AssertionError):
        _labels()


def test_risk_duck_types_as_a_moment() -> None:
    r = _risk()
    assert (r.start, r.finish, r.milestone) == (r.date, r.date, True)


def test_risks_table_shape() -> None:
    doc = _doc(
        [
            _POSITIONAL_ROW,
            ("Dallas", "Range closure", "10 wd", "", "5/10/27"),
        ]
    )
    t = risks_table(doc)
    assert t.title == "Risks"
    assert t.headers == (
        "Swimlane",
        "Risk",
        "Date of occurrence",
        "Potential impact",
        "Impact (cal d)",
        "Probability",
        "Source row",
    )
    assert t.rows == (
        ("Flight Manifests", "Engine slip", "2027-03-15", "30", 30, "High", 1),
        ("Dallas", "Range closure", "2027-05-10", "10 wd", None, "Unknown", 2),
    )
    tables = risks_tables(doc)
    assert [x.title for x in tables] == ["Risks", "Skipped rows (risks)", "Notes (risks)"]
    assert tables[1].rows == (("none",),)
    assert tables[2].rows == (
        (
            "row 2 (Dallas · Range closure): potential impact “10 wd” kept as typed — not read as "
            "calendar days",
        ),
        ("row 2 (Dallas · Range closure): no probability — drawn as unknown",),
    )


def test_risks_table_names_every_problem() -> None:
    doc = _doc([("Flight Manifests", "", 30, "High", "3/15/2027")])
    assert risks_tables(doc)[0].rows == ()
    assert risks_tables(doc)[1].rows == (("row 1 (Flight Manifests): no risk name — skipped",),)


# ── the std-lib-only law (LODESTAR carries this module verbatim) ───────────────────────────────


def test_module_imports_only_what_lodestar_may_carry() -> None:
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(mod))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names.append(node.module or "")
    allowed: Callable[[str], bool] = lambda n: (  # noqa: E731
        n.startswith("schedule_forensics.reports.")
        or n
        in {"datetime", "hashlib", "re", "math", "collections.abc", "dataclasses", "__future__"}
    )
    assert all(allowed(n) for n in names), names
