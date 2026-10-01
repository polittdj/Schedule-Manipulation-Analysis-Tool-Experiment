"""The One-Pager's RISK REGISTER: a second workbook whose rows are risks, not tasks (ADR-0544).

The operator keeps a plain workbook — column A the swimlane, B the risk's name, C its potential
durational impact, D its probability of occurrence (High / Medium / Low), E the date it would
occur — and wants each risk drawn on the One-Pager as a single moment, like a milestone but
unmistakably NOT one: an upward triangle in the probability's colour, labelled ``RISK · name
(m/d/yy)`` with the impact beside it. This module is the whole of that intake; the layout and
the painters only ever see :class:`OnePagerRisk`.

It reuses the list reader's own pieces rather than re-deciding them: the date forms come from
:func:`~schedule_forensics.reports.onepager.parse_date` (an Excel serial, ``m/d/yy``, ISO, a
spelled month, MS Project's pasted forms), the swimlane merge key is the list's
:func:`~schedule_forensics.reports.onepager._lane_key`, and the compact date is its
:func:`~schedule_forensics.reports.onepager.mdy` — so a risk lands in the SAME band as the tasks
whose swimlane is spelled a little differently, and its label dates read like theirs.

What this reader decides, and names (nothing is guessed silently — the list reader's rule):

* **Columns.** A header row (recognised by its words — swim / lane · risk / name / title · impact
  / duration / delay / days · probab / likelihood / chance · date / when / occur) binds each
  role to the column that names it, in any order; a role the header does not name keeps its
  positional column unless the header claimed that column for another role. Without a header
  the columns are positional A-E. One note names every role read from a column other than its
  positional one. The list reader's ``_is_header`` is NOT reused: its date guard sits on column
  C, which here holds the impact NUMBER, and its words fire on a lane called "Milestones".
* **Rows.** A missing swimlane inherits the one above (noted); no name, or no readable date of
  occurrence, skips the row (named). A month-only date (``05/2027``) is its FIRST day (noted):
  a risk is one moment, and the month's first day is the earliest it could land.
* **Impact.** A number alone is calendar days. ``d`` / ``day`` / ``days``, ``w`` / ``wk`` /
  ``week`` / ``weeks`` (x7) and ``mo`` / ``month`` / ``months`` (x30) are converted — x7 and x30
  are stated ONCE per unit in the notes, since a reader of the slide should know the "+21 cal d"
  was typed as three weeks. ``wd`` / ``working days`` / anything else is kept VERBATIM with
  ``impact_days=None`` (noted): converting working days needs a calendar the workbook does not
  carry, and a wrong number on a slide is worse than the operator's own words.
* **Probability.** ``high`` / ``h`` / ``hi`` / ``red``, ``medium`` / ``med`` / ``m`` /
  ``moderate`` / ``amber`` / ``yellow``, ``low`` / ``l`` / ``lo`` / ``green`` — case-insensitive,
  trailing text tolerated (``High (80%)``); anything else is ``unknown`` and NAMED by row, drawn
  in the neutral colour so the slide never promotes a guess to a colour.

Every risk carries a stable key (:func:`risk_keys`) — swimlane key + name + date, 16 hex of a
sha256 — the slide's ``data-key`` and the identity the session payload rebinds by.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from schedule_forensics.reports.onepager import _lane_key, mdy, parse_date
from schedule_forensics.reports.tableset import Cell, Table, TableSet
from schedule_forensics.reports.xlsx_read import XlsxError, read_xlsx_numbered

# ── vocabulary ────────────────────────────────────────────────────────────────────────────────

#: The probability values a risk may carry, in the order the legend lists them.
PROBS: tuple[str, ...] = ("high", "medium", "low", "unknown")
#: The word the page, the tables and the legend print for each.
PROB_NAMES: Mapping[str, str] = {
    "high": "High",
    "medium": "Medium",
    "low": "Low",
    "unknown": "Unknown",
}
#: The five roles a column can play.
ROLES: tuple[str, ...] = ("lane", "name", "impact", "prob", "date")
#: The role each positional column plays when the sheet has no header: A-E.
POSITIONAL: dict[str, int] = {"lane": 0, "name": 1, "impact": 2, "prob": 3, "date": 4}
#: How a note names a role.
ROLE_NAMES: Mapping[str, str] = {
    "lane": "swimlane",
    "name": "risk name",
    "impact": "potential impact",
    "prob": "probability",
    "date": "date of occurrence",
}
#: Header words per role, MOST SPECIFIC FIRST: a cell naming two roles ("Risk impact", "Lane
#: name", "Impact date") is the one listed earlier — the generic "name" / "risk" is last.
ROLE_WORDS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("prob", re.compile(r"probab|likelihood|chance", re.IGNORECASE)),
    ("date", re.compile(r"date|when|occur", re.IGNORECASE)),
    ("impact", re.compile(r"impact|duration|delay|days", re.IGNORECASE)),
    ("lane", re.compile(r"swim|lane", re.IGNORECASE)),
    ("name", re.compile(r"risk|name|title", re.IGNORECASE)),
)
#: Impact units: token -> (calendar days per unit, the unit's name for the note). A bare number
#: is calendar days already; any token not here keeps the cell verbatim.
UNITS: dict[str, tuple[int, str]] = {
    "d": (1, "day"),
    "day": (1, "day"),
    "days": (1, "day"),
    "w": (7, "week"),
    "wk": (7, "week"),
    "wks": (7, "week"),
    "week": (7, "week"),
    "weeks": (7, "week"),
    "mo": (30, "month"),
    "mos": (30, "month"),
    "month": (30, "month"),
    "months": (30, "month"),
}
#: Probability words: the leading word of the cell -> the probability.
PROB_WORDS: dict[str, str] = {
    "high": "high",
    "h": "high",
    "hi": "high",
    "red": "high",
    "medium": "medium",
    "med": "medium",
    "m": "medium",
    "moderate": "medium",
    "amber": "medium",
    "yellow": "medium",
    "low": "low",
    "l": "low",
    "lo": "low",
    "green": "low",
}
#: A number alone, or a number with an optional ``cal`` / ``calendar`` and a unit word.
_IMPACT_RE = re.compile(
    r"^([+-]?\d+(?:\.\d+)?)\s*(?:cal(?:endar)?\s*)?([a-z]+)?\.?$", re.IGNORECASE
)
_NUMBER_RE = re.compile(r"^[+-]?\d+(?:\.\d+)?$")
_WORD_RE = re.compile(r"^[a-z]+")

# ── the sentences (module constants so a mutation twin can break each by name) ───────────────

NO_ROWS = "the workbook has no rows"
INHERITED = "row {row}: no swimlane name — placed under “{lane}”"
NO_LANE = "row {row}: no swimlane name and none above it — skipped"
NO_NAME = "row {row} ({lane}): no risk name — skipped"
NO_DATE = "{where}: no date of occurrence — skipped"
BAD_DATE = "{where}: unreadable date of occurrence “{text}” — skipped"
MONTH_ONLY = "{where}: “{text}” names a month, not a day — placed on its first day {day}"
VERBATIM_IMPACT = "{where}: potential impact “{text}” kept as typed — not read as calendar days"
NO_IMPACT = "{where}: no potential impact"
UNIT_NOTE = (
    "potential impact in {unit}s converted at {factor} calendar days per {unit} "
    "({rows_word} {rows})"
)
BAD_PROB = "{where}: probability “{text}” is not High, Medium or Low — drawn as unknown"
NO_PROB = "{where}: no probability — drawn as unknown"
HEADER_NOTE = "header (row {row}): {moved}"


# ── the types ─────────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class OnePagerRisk:
    """One risk: a single moment on ``date`` in swimlane ``lane``.

    ``impact_text`` is the cell as typed (``""`` when blank); ``impact_days`` its calendar-day
    reading, ``None`` when it was kept verbatim or blank. ``prob`` is one of :data:`PROBS`.
    ``row`` is the Excel row. ``key`` is set by the document (:func:`risk_keys`); empty on a
    risk built by hand. ``start`` / ``finish`` / ``milestone`` let a risk stand where the layout
    expects an item-shaped moment (the window test, the data-date comparison)."""

    lane: str
    name: str
    date: dt.date
    impact_text: str
    impact_days: int | None
    prob: str
    row: int
    key: str = ""

    @property
    def start(self) -> dt.date:
        return self.date

    @property
    def finish(self) -> dt.date:
        return self.date

    @property
    def milestone(self) -> bool:
        return True


@dataclass(frozen=True)
class RiskDoc:
    """A parsed risk workbook: the risks, every row skipped (``problems``, by row and reason)
    and every assumption made (``notes``) — the list document's shape, so the page and the
    exports state them the same way. ``rows`` are the sheet's rows AS READ (Excel row number,
    cells), untouched: the session payload carries them so a restore re-parses the register
    through this same reader instead of trusting a stored reading."""

    source: str
    sheet: str
    risks: tuple[OnePagerRisk, ...]
    problems: tuple[str, ...]
    notes: tuple[str, ...]
    rows: tuple[tuple[int, tuple[str, ...]], ...] = ()


@dataclass(frozen=True)
class RiskSheetRead:
    """Everything one sheet's reading produced (:func:`read_risk_sheet`): the risks (unkeyed),
    the problems and notes, the header row's index (``None`` for none) and the column each
    role was read from (a role absent from the sheet is not in ``columns``)."""

    risks: list[OnePagerRisk]
    problems: list[str]
    notes: list[str]
    header: int | None
    columns: dict[str, int]


# ── the cell readers ──────────────────────────────────────────────────────────────────────────


def column_letter(index: int) -> str:
    """``0 -> A``: the letter a note names a column by (the reader caps at six columns)."""
    return chr(ord("A") + index)


def header_roles(cells: Sequence[str]) -> dict[str, int]:
    """The roles a HEADER row binds, role -> column index — ``{}`` when the row is not a header.

    A header names at least two roles by :data:`ROLE_WORDS` (the first column naming a role
    keeps it); a row holding a readable date or a bare number anywhere is DATA — a risk called
    "Launch date slip" in a lane called "Milestones" names two roles too, and is told apart only
    by the date and impact it carries."""
    found: dict[str, int] = {}
    for k, cell in enumerate(cells):
        text = cell.strip()
        if not text:
            continue
        if _NUMBER_RE.match(text) or parse_date(text) is not None:
            return {}
        for role, pattern in ROLE_WORDS:
            if pattern.search(text):
                found.setdefault(role, k)
                break
    return found if len(found) >= 2 else {}


def _half_up(value: float) -> int:
    """Round half AWAY from zero to a whole day (``2.5 -> 3``; Python's ``round`` is half-even)."""
    return math.floor(value + 0.5) if value >= 0 else -math.floor(-value + 0.5)


def read_impact(text: str) -> tuple[int | None, str]:
    """The impact cell -> ``(calendar days, unit)``: ``(30, "")`` for a bare number, ``(21,
    "week")`` for ``3 wk`` (the unit named so the note can state the conversion once), ``(None,
    "")`` for a blank cell or one kept verbatim (``10 wd``, ``two weeks``). A fraction rounds
    half-up to a whole day."""
    m = _IMPACT_RE.match(text.strip())
    if not m:
        return None, ""
    value = float(m.group(1))
    unit = (m.group(2) or "").lower()
    if not unit:
        return _half_up(value), ""
    if unit not in UNITS:
        return None, ""
    factor, name = UNITS[unit]
    return _half_up(value * factor), name


def read_probability(text: str) -> str:
    """The probability cell -> one of :data:`PROBS`: its LEADING word looked up in
    :data:`PROB_WORDS` (case-insensitive, trailing text tolerated — ``High (80%)``), else
    ``unknown``. A word is whole: ``Highest`` is not ``High``."""
    m = _WORD_RE.match(text.strip().casefold())
    if not m:
        return "unknown"
    return PROB_WORDS.get(m.group(0), "unknown")


# ── the sheet ─────────────────────────────────────────────────────────────────────────────────


def _bind_columns(header: Sequence[str] | None) -> tuple[dict[str, int], str]:
    """The column each role is read from, and the sentence naming the roles the header moved
    off their positional columns (``""`` when none moved, or there is no header)."""
    if header is None:
        return dict(POSITIONAL), ""
    named = header_roles(header)
    columns = dict(named)
    for role in ROLES:
        if role not in columns and POSITIONAL[role] not in named.values():
            columns[role] = POSITIONAL[role]
    # the moved roles in COLUMN order (C before E), as the eye reads the sheet
    off_place = sorted(
        (r for r in ROLES if r in columns and columns[r] != POSITIONAL[r]), key=columns.__getitem__
    )
    moved = [
        f"{ROLE_NAMES[role]} {'read ' if n == 0 else ''}from column {column_letter(columns[role])}"
        for n, role in enumerate(off_place)
    ]
    return columns, ", ".join(moved)


def read_risk_sheet(rows: list[list[str]], numbers: list[int] | None = None) -> RiskSheetRead:
    """One sheet's rows (every cell a string, as ``read_xlsx_numbered`` hands them) -> the risks
    and every decision, by row. ``numbers`` are the rows' Excel row numbers; without them a
    row's number is its position."""
    if numbers is not None and len(numbers) != len(rows):
        raise ValueError("one row number per row")
    stripped = [[c.strip() for c in row] for row in rows]
    content = [k for k, cells in enumerate(stripped) if any(cells)]
    header = content[0] if content and header_roles(stripped[content[0]]) else None
    columns, moved = _bind_columns(stripped[header] if header is not None else None)
    notes: list[str] = []
    problems: list[str] = []
    if header is not None and moved:
        i = numbers[header] if numbers is not None else header + 1
        notes.append(HEADER_NOTE.format(row=i, moved=moved))
    risks: list[OnePagerRisk] = []
    units: dict[str, list[int]] = {}
    lane = ""

    def cell(cells: list[str], role: str) -> str:
        at = columns.get(role)
        return cells[at] if at is not None and at < len(cells) else ""

    for k, cells in enumerate(stripped):
        i = numbers[k] if numbers is not None else k + 1
        if k == header or not any(cell(cells, role) for role in ROLES):
            continue  # the header, or a spacer row
        a = cell(cells, "lane")
        if a:
            lane = a
        elif lane:
            notes.append(INHERITED.format(row=i, lane=lane))
        else:
            problems.append(NO_LANE.format(row=i))
            continue
        name = cell(cells, "name")
        if not name:
            problems.append(NO_NAME.format(row=i, lane=lane))
            continue
        where = f"row {i} ({lane} · {name})"
        when = cell(cells, "date")
        if not when:
            problems.append(NO_DATE.format(where=where))
            continue
        span = parse_date(when)
        if span is None:
            problems.append(BAD_DATE.format(where=where, text=when))
            continue
        date = span[0]
        if span[0] != span[1]:
            notes.append(MONTH_ONLY.format(where=where, text=when, day=mdy(date)))
        impact = cell(cells, "impact")
        days, unit = read_impact(impact)
        if unit and _unit_factor(unit) != 1:
            units.setdefault(unit, []).append(i)
        elif days is None:
            notes.append(
                VERBATIM_IMPACT.format(where=where, text=impact)
                if impact
                else NO_IMPACT.format(where=where)
            )
        prob_text = cell(cells, "prob")
        prob = read_probability(prob_text)
        if prob == "unknown":
            notes.append(
                BAD_PROB.format(where=where, text=prob_text)
                if prob_text
                else NO_PROB.format(where=where)
            )
        risks.append(OnePagerRisk(lane, name, date, impact, days, prob, i))
    for unit, at in units.items():
        notes.append(
            UNIT_NOTE.format(
                unit=unit,
                factor=_unit_factor(unit),
                rows_word="rows" if len(at) > 1 else "row",
                rows=", ".join(str(n) for n in at),
            )
        )
    return RiskSheetRead(risks, problems, notes, header, columns)


def _unit_factor(name: str) -> int:
    """Calendar days per unit, by the unit's NAME (``week`` -> 7) — read from the table so a
    changed table changes the sentence with it."""
    for factor, unit_name in UNITS.values():
        if unit_name == name:
            return factor
    return 1


def parse_risk_workbook(sheets: Mapping[str, list[tuple[int, list[str]]]], source: str) -> RiskDoc:
    """``read_xlsx_numbered``'s sheets -> the register: the FIRST sheet with any content (a
    register is one sheet), every risk keyed over the whole sheet in sheet order."""
    for name, numbered in sheets.items():
        if any(any(cell.strip() for cell in cells) for _n, cells in numbered):
            read = read_risk_sheet([cells for _n, cells in numbered], [n for n, _c in numbered])
            return RiskDoc(
                source,
                name,
                tuple(keyed_risks(read.risks)),
                tuple(read.problems),
                tuple(read.notes),
                tuple((n, tuple(cells)) for n, cells in numbered),
            )
    return RiskDoc(source, "", (), (NO_ROWS,), ())


def read_risks(data: bytes, source: str, *, max_bytes: int) -> RiskDoc | str:
    """An uploaded workbook -> its register, or the sentence saying why not — the list upload's
    own rule (``web.onepager_actions.read_list``): only the size cap and a workbook the reader
    REFUSES (:class:`~schedule_forensics.reports.xlsx_read.XlsxError`) are sentences; anything
    else propagates. ``source`` is the workbook's name already cleaned by the caller (this
    module never imports the web layer: LODESTAR carries it verbatim)."""
    if len(data) > max_bytes:
        return f"Risks not loaded — file exceeds the {max_bytes // (1024 * 1024)} MB cap."
    try:
        sheets = read_xlsx_numbered(data, max_columns=6, booleans_as_text=True)
    except XlsxError as exc:
        return f"Could not read that file: {exc}"
    return parse_risk_workbook(sheets, source)


# ── keys ──────────────────────────────────────────────────────────────────────────────────────


def risk_keys(risks: Sequence[OnePagerRisk]) -> list[str]:
    """One stable key per risk, in order: sha256 of swimlane key (the layout's merge key) +
    name (whitespace collapsed, case folded) + ISO date, 16 hex — the risk's identity on the
    slide and in the session payload. Row, impact and probability are NOT part of it, so an
    edit to those keeps the risk's key; identical copies are told apart only by their order
    (the list's :func:`~schedule_forensics.reports.onepager.item_keys` rule for its own
    duplicates)."""
    seen: dict[str, int] = {}
    out: list[str] = []
    for r in risks:
        name = " ".join(r.name.split()).casefold()
        ident = f"{_lane_key(r.lane)}\x1f{name}\x1f{r.date.isoformat()}"
        n = seen[ident] = seen.get(ident, 0) + 1
        if n > 1:
            ident += f"\x1f#{n}"
        out.append(hashlib.sha256(ident.encode("utf-8")).hexdigest()[:16])
    return out


def keyed_risks(risks: Sequence[OnePagerRisk]) -> list[OnePagerRisk]:
    """``risks`` with every key set — their own where present, else derived over ``risks``."""
    if all(r.key for r in risks):
        return list(risks)
    return [r if r.key else replace(r, key=k) for r, k in zip(risks, risk_keys(risks), strict=True)]


# ── the slide's words ─────────────────────────────────────────────────────────────────────────


def risk_when(r: OnePagerRisk) -> str:
    """``m/d/yy`` — the risk's date as a label or a dropdown says it (the list's ``item_when``)."""
    return mdy(r.date)


def risk_label(r: OnePagerRisk) -> str:
    """``RISK · name (m/d/yy)`` — the label every painter draws; the ``RISK ·`` lead is what
    tells a reader this is not a task or a milestone."""
    return f"RISK · {r.name} ({risk_when(r)})"


def impact_label(r: OnePagerRisk) -> str:
    """The text after the label: ``impact +30 cal d`` when the days are known, ``impact: 10 wd``
    for an impact kept verbatim, ``""`` for none."""
    if r.impact_days is not None:
        return f"impact {r.impact_days:+d} cal d"
    return f"impact: {r.impact_text}" if r.impact_text else ""


# ── tables and the template ───────────────────────────────────────────────────────────────────


def risks_table(doc: RiskDoc) -> Table:
    """The register as the ▦ DATA / Excel table: one row per risk, the impact both as typed and
    in calendar days (``None`` when it was kept verbatim)."""
    rows: tuple[tuple[Cell, ...], ...] = tuple(
        (
            r.lane,
            r.name,
            r.date.isoformat(),
            r.impact_text,
            r.impact_days,
            PROB_NAMES[r.prob],
            r.row,
        )
        for r in doc.risks
    )
    return Table(
        "Risks",
        (
            "Swimlane",
            "Risk",
            "Date of occurrence",
            "Potential impact",
            "Impact (cal d)",
            "Probability",
            "Source row",
        ),
        rows,
    )


def risks_tables(doc: RiskDoc) -> tuple[Table, Table, Table]:
    """:func:`risks_table` plus the register's skipped rows and notes, titled apart from the
    list's own so an export carrying both never has two "Notes" sheets."""
    return (
        risks_table(doc),
        Table(
            "Skipped rows (risks)", ("Problem",), tuple((p,) for p in doc.problems) or (("none",),)
        ),
        Table("Notes (risks)", ("Note",), tuple((n,) for n in doc.notes) or (("none",),)),
    )


#: The header the template ships — every role named, in positional order, so the register is
#: read the same with or without it.
RISK_TEMPLATE_HEADER: tuple[str, ...] = (
    "Swimlane Name",
    "Risk",
    "Potential impact (days)",
    "Probability (High / Medium / Low)",
    "Date of occurrence",
)
#: Four example rows in the list template's swimlanes, one per probability (and a second
#: medium), impacts as bare calendar days — the template reads back with no problem and no note.
RISK_TEMPLATE_ROWS: tuple[tuple[Cell, ...], ...] = (
    ("Flight Manifests", "Engine qualification slips", 30, "High", "3/15/2027"),
    ("Dallas", "Lander test stand unavailable", 14, "Medium", "7/1/2027"),
    ("Dallas", "Range closure during campaign", 21, "Medium", "5/10/2027"),
    ("Crew Life", "MET vendor delivery late", 7, "Low", "1/20/2027"),
)


def risk_template() -> TableSet:
    """A fill-in workbook in the register's shape, the twin of the list template."""
    return TableSet(
        "POLARIS² — One-Pager risks",
        (Table("Risk register", RISK_TEMPLATE_HEADER, RISK_TEMPLATE_ROWS),),
    )
