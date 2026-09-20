"""Acumen Fuse's Forensic Analysis Report is a rounding oracle: every whole-day field is the exact
value rounded HALF-TO-EVEN, every day change is the difference of the ROUNDED fields, every
2-dp ratio is ToEven on the scaled value, and every date change is the calendar-day difference
truncated toward zero (R-04, ADR-0515).

R-04 read the 330 builtin ``round()`` sites outside ``engine/metrics`` as MF-08's residual — a
banker's-rounding defect at every displayed tie, to be swept toward ``round_half_up``. The
reference tool's own report refutes the premise on a population. The operator's three Forensic
Analysis Reports (the Large Test File pair and the two Hard_File pairs) print, per changed
activity, the field before, the change, a 2-dp ratio and the field after; against the goldens'
exact values (integer working minutes over the 480-minute day):

* **Original Duration / Remaining Duration / Total Float** — half-even reproduces every
  comparable row (LTF 752 / 773 / 1297); the half-day ties of both parities are present
  (20 / 11 / 262 on the first snapshot) and half-away-from-zero misses exactly the even-part
  ones (10 / 4 / 111), truncation more.
* **The change column is rounded(after) - rounded(before)**, never round(after - before):
  the two disagree on 81 LTF float rows and on Hard_File UID 37 (8.5 → 7 is shown -1, not -2).
* **The 2-dp ratio** (-change / before) is ToEven on the SCALED value (.NET ``Math.Round``):
  1/8 → 0.12, 9/8 → 1.12, 17/40 → 0.42 and 1/40 → 0.02 — half-up refuted on every one of the
  11 discriminating ties, and Python's own correctly-rounded ``round(0.025, 2) == 0.03`` shows
  the reference rounds the scaled double, not the exact decimal.
* **The Start / Finish change** is the calendar-day difference truncated toward zero
  (2,741 of 2,741 rows); floor, half-even and the date-part difference each miss hundreds.

Three float rows are NOT rounding: Hard_File UIDs 14 / 146 / 94 display the stored slack over
the ACTIVITY's own day (a 1440-minute task calendar, an elapsed duration, a 930-minute
calendar), not the project's 480 — named here, owned by the divisor row the ADR registers. One
duration row is the model's own minute grid: LTF2 UID 5267's file duration is PT107H59M36S
(13.4992 days, below the tie) and the integer-minute model carries 6,480 (exactly 13.5); Fuse's
13 is half-even on the file's seconds.

Absence semantics mirror ``test_fuse_total_float_field_oracle``: skip only when the intake dir
is absent; a named workbook that is missing FAILS.
"""

from __future__ import annotations

import collections
import datetime as dt
import gzip
import math
import re
import zipfile
from fractions import Fraction
from functools import cache
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.metrics._common import effective_total_float
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.schedule import Schedule

REPO = Path(__file__).resolve().parents[2]
INTAKE = REPO / "00_REFERENCE_INTAKE"
ACUMEN = INTAKE / "acumen_v8.11.0"
GOLDEN = REPO / "tests" / "fixtures" / "golden"

pytestmark = [
    pytest.mark.parity,
    pytest.mark.skipif(
        not INTAKE.exists(), reason="00_REFERENCE_INTAKE/ not present in this layout"
    ),
]

_M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_EPOCH = dt.datetime(1899, 12, 30)  # Excel's serial-date origin

Cell = str | int | float | bool | None

#: (workbook, golden before, golden after) — the three Forensic Analysis Reports the operator
#: delivered with a committed golden on both sides
_PAIRS: tuple[tuple[str, str, str], ...] = (
    (
        "Large Test File vs Large Test File2 - Acumen Forensic Analysis Report.xlsx",
        "fuse_ltf/Large_Test_File",
        "fuse_ltf/Large_Test_File2",
    ),
    (
        "Hard_File_updated vs update 2_ Forensic Analysis Report.xlsx",
        "fuse_hardfile/Hard_File_updated",
        "fuse_hardfile/Hard_File_updated2",
    ),
    (
        "Hard_File_updated2 vs update3 Forensic Analysis Report.xlsx",
        "fuse_hardfile/Hard_File_updated2",
        "fuse_hardfile/Hard_File_updated3",
    ),
)
_DAY_SHEETS = ("Original-Duration", "Remaining-Duration", "Total-Float")

#: the rows the rule does NOT decide, each with its mechanism (never excluded silently)
_DIVISOR_ROWS = {  # (workbook index, UID) -> the activity's own day length in minutes
    (1, 14): 1440,  # task calendar "24 Hours"
    (2, 14): 1440,
    (1, 94): 930,  # task calendar "Standard+Sat."
    (2, 146): 1440,  # an ELAPSED duration on the project calendar
}
_MINUTE_GRID_ROWS = {(0, 5267)}  # PT107H59M36S carried as 6,480 minutes


def _half_even(d: Fraction) -> int:
    return round(d)


def _half_away(d: Fraction) -> int:
    sign = -1 if d < 0 else 1
    return sign * math.floor(abs(d) + Fraction(1, 2))


def _trunc(d: Fraction) -> int:
    return int(d)


@cache
def _sheet(path: Path, name: str) -> list[list[Cell]]:
    """One sheet of an xlsx as rows of typed cells (std-lib only), parsing only that sheet."""
    with zipfile.ZipFile(path) as zf:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            for si in ET.fromstring(zf.read("xl/sharedStrings.xml")).findall(f"{_M}si"):
                shared.append("".join(t.text or "" for t in si.iter(f"{_M}t")))
        wb = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        targets = {r.get("Id"): r.get("Target") or "" for r in rels}
        sheets_el = wb.find(f"{_M}sheets")
        assert sheets_el is not None
        target = next(
            targets[s.get(f"{_R}id") or ""] for s in sheets_el if (s.get("name") or "") == name
        )
        target = target if target.startswith("xl/") else "xl/" + target.lstrip("/")
        rows: list[list[Cell]] = []
        for row in ET.fromstring(zf.read(target)).iter(f"{_M}row"):
            cells: list[Cell] = []
            for c in row.findall(f"{_M}c"):
                v = c.find(f"{_M}v")
                if v is None or v.text is None:
                    cells.append(None)
                    continue
                kind = c.get("t")
                if kind == "s":
                    cells.append(shared[int(v.text)])
                elif kind == "b":
                    cells.append(bool(int(v.text)))
                else:
                    try:
                        cells.append(
                            float(v.text) if "." in v.text or "E" in v.text else int(v.text)
                        )
                    except ValueError:
                        cells.append(v.text)
            rows.append(cells)
        return rows


def _grid(path: Path, name: str, *, ratio: bool) -> list[tuple[int, list[Cell]]]:
    """(UID, [before, change, ratio?, after]) per activity row of a change sheet, read
    POSITIONALLY: the 'before' column sits just left of the repeated after-project header, then
    the glyph, the change, the 2-dp ratio (a day sheet only — a date sheet has none) and the
    after value. A row with no after value (an activity absent from the second snapshot) is
    returned with ``None`` there, never with the ratio sliding into its place."""
    rows = _sheet(path, name)
    hdr = next(r for r in rows if r and r[0] == "#")
    id_i = hdr.index("ID")
    counts = collections.Counter(c for c in hdr if isinstance(c, str))
    after_name = next(c for c, k in counts.items() if k >= 3)
    a_cols = [i for i, c in enumerate(hdr) if c == after_name]
    b_i = a_cols[0] - 1
    after_i = b_i + (4 if ratio else 3)
    out: list[tuple[int, list[Cell]]] = []
    for r in rows[rows.index(hdr) + 1 :]:
        if len(r) <= b_i + 2 or r[id_i] in (None, ""):
            continue
        try:
            uid = int(str(r[id_i]))
        except ValueError:
            continue
        cells: list[Cell] = [r[b_i], r[b_i + 2]]
        if ratio:
            cells.append(r[b_i + 3] if len(r) > b_i + 3 else None)
        cells.append(r[after_i] if len(r) > after_i else None)
        out.append((uid, cells))
    return out


def _is_number(c: Cell) -> bool:
    return isinstance(c, (int, float)) and not isinstance(c, bool)


@cache
def _golden(name: str) -> Schedule:
    xml = gzip.decompress((GOLDEN / f"{name}.mspdi.xml.gz").read_bytes()).decode("utf-8")
    return parse_mspdi_text(xml, source_file=f"{name.split('/')[-1]}.mspdi.xml")


@cache
def _exact(name: str) -> dict[int, dict[str, Fraction]]:
    """Per UID: the three whole-day fields in exact working days on the PROJECT day — the
    quantity Fuse's field rounds (the divisor rows above are the measured exception)."""
    sch = _golden(name)
    cpm = compute_cpm(sch)
    mpd = sch.calendar.working_minutes_per_day
    tf = {u: t.total_float for u, t in cpm.timings.items()}
    out: dict[int, dict[str, Fraction]] = {}
    for t in sch.tasks:
        rem = t.remaining_duration_minutes
        if rem is None:
            rem = round(t.duration_minutes * (100.0 - t.percent_complete) / 100.0)
        eff = effective_total_float(t, tf.get(t.unique_id, 0))
        out[t.unique_id] = {
            "Original-Duration": Fraction(t.duration_minutes, mpd),
            "Remaining-Duration": Fraction(rem, mpd),
            "Total-Float": Fraction(str(eff)) / mpd,
        }
    return out


def _workbooks_present() -> None:
    missing = [wb for wb, _a, _b in _PAIRS if not (ACUMEN / wb).exists()]
    assert not missing, f"Forensic Analysis Report(s) missing from the intake (Law 2): {missing}"


@pytest.mark.parametrize("sheet", _DAY_SHEETS)
def test_every_whole_day_field_is_half_even_and_the_change_is_a_difference_of_rounded_fields(
    sheet: str,
) -> None:
    _workbooks_present()
    compared = 0
    ties = disc_ties = delta_disc = 0
    misses_even: list[tuple[int, int, float, float]] = []
    misses_away = misses_trunc = 0
    chg_of_rounded = chg_of_exact = 0
    for k, (wb, before_name, after_name) in enumerate(_PAIRS):
        before_days, after_days = _exact(before_name), _exact(after_name)
        for uid, cells in _grid(ACUMEN / wb, sheet, ratio=True):
            before_c, change_c, _ratio_c, after_c = cells
            if uid not in before_days or uid not in after_days:
                continue
            if not all(_is_number(c) for c in (before_c, change_c, after_c)):
                continue
            shown_before, shown_change, shown_after = (
                float(before_c),  # type: ignore[arg-type]
                float(change_c),  # type: ignore[arg-type]
                float(after_c),  # type: ignore[arg-type]
            )
            da, db = before_days[uid][sheet], after_days[uid][sheet]
            if (k, uid) in _DIVISOR_ROWS and sheet == "Total-Float":
                # the stored slack over the activity's OWN day reproduces Fuse's field — the
                # project day does not: the mechanism is the divisor, not the rounding
                own = _DIVISOR_ROWS[(k, uid)]
                sch_b, sch_a = _golden(before_name), _golden(after_name)
                mpd = sch_b.calendar.working_minutes_per_day
                exact_own = [
                    Fraction(str(effective_total_float(s.tasks_by_id[uid], 0))) / own
                    for s in (sch_b, sch_a)
                ]
                assert mpd == 480 and own != mpd
                assert [_half_even(x) for x in exact_own] == [shown_before, shown_after], (
                    k,
                    uid,
                )
                assert _half_even(da) != shown_before or _half_even(db) != shown_after
                continue
            if (k, uid) in _MINUTE_GRID_ROWS and sheet != "Total-Float":
                # the file's own seconds sit below the tie the integer-minute model lands on
                raw = gzip.decompress((GOLDEN / f"{after_name}.mspdi.xml.gz").read_bytes()).decode(
                    "utf-8"
                )
                task = re.search(rf"<Task>\s*<UID>{uid}</UID>.*?</Task>", raw, re.S)
                assert task is not None
                m = re.search(r"<Duration>PT(\d+)H(\d+)M(\d+)S</Duration>", task.group(0))
                assert m is not None
                seconds = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
                assert seconds == 107 * 3600 + 59 * 60 + 36 and db == Fraction(27, 2)
                assert _half_even(Fraction(seconds, 480 * 60)) == shown_after == 13
                continue
            compared += 1
            if _half_even(da) != shown_before or _half_even(db) != shown_after:
                misses_even.append((k, uid, float(da), float(db)))
            misses_away += _half_away(da) != shown_before or _half_away(db) != shown_after
            misses_trunc += _trunc(da) != shown_before or _trunc(db) != shown_after
            for d in (da, db):
                if d.denominator == 2:
                    ties += 1
                    disc_ties += _half_even(d) != _half_away(d)
            chg_of_rounded += (_half_even(db) - _half_even(da)) == shown_change
            chg_of_exact += _half_even(db - da) == shown_change
            delta_disc += (_half_even(db) - _half_even(da)) != _half_even(db - da)
    # the population, pinned so a parser or golden regression cannot shrink it silently
    assert (
        compared
        == {
            "Original-Duration": 752 - 1 + 31 + 24,
            "Remaining-Duration": 773 - 1 + 47 + 29,
            "Total-Float": 1297 + 39 + 100,
        }[sheet]
    ), (sheet, compared)
    assert not misses_even, f"{len(misses_even)} rows are not the half-even day: {misses_even[:8]}"
    # both parities of the half-day tie are present, so the rule is DECIDED, and the alternatives
    # the audit row weighed are refuted by name on this population
    assert ties >= {"Original-Duration": 30, "Remaining-Duration": 19, "Total-Float": 273}[sheet]
    assert (
        disc_ties >= {"Original-Duration": 14, "Remaining-Duration": 9, "Total-Float": 118}[sheet]
    )
    assert misses_away == disc_ties > 0, (sheet, misses_away, disc_ties)
    assert misses_trunc > misses_away
    # the change column is a difference of the ROUNDED fields, never the rounded exact difference
    assert chg_of_rounded == compared, (sheet, chg_of_rounded, compared)
    assert delta_disc > 0 and chg_of_exact == compared - delta_disc, (
        sheet,
        chg_of_exact,
        delta_disc,
    )


def test_the_two_dp_ratio_is_to_even_on_the_scaled_value() -> None:
    _workbooks_present()
    rows = disc = 0
    misses_scaled = misses_away = 0
    seen: dict[tuple[int, int], float] = {}
    for wb, before_name, _after_name in _PAIRS:
        for sheet in _DAY_SHEETS:
            for uid, cells in _grid(ACUMEN / wb, sheet, ratio=True):
                shown_before, shown_change, shown_ratio, _after = cells
                if uid not in _exact(before_name):
                    continue
                if not all(_is_number(c) for c in (shown_before, shown_change, shown_ratio)):
                    continue  # a 'q' row prints "(-n%)" as text — no numeric ratio
                if not shown_before or not float(shown_before).is_integer():
                    continue
                rows += 1
                fr = -Fraction(int(shown_change), int(shown_before))
                scaled = fr * 100
                to_even = round(scaled) / 100  # the scaled-ToEven rule, as a float
                misses_scaled += to_even != shown_ratio
                misses_away += _half_away(scaled) / 100 != shown_ratio
                if scaled.denominator == 2 and round(scaled) != _half_away(scaled):
                    disc += 1
                    seen[(int(shown_change), int(shown_before))] = float(shown_ratio)
    assert rows >= 1400, rows
    assert misses_scaled == 0, misses_scaled
    assert disc == 11 and misses_away == disc, (disc, misses_away)
    # the discriminating ties BY NAME: half-up would print 0.13 / 1.13 / 0.43 / 0.03
    assert seen[(1, 8)] == -0.12 and seen[(9, 8)] == -1.12
    assert seen[(17, 40)] == -0.42 and seen[(1, 40)] == -0.02
    # and 1/40 separates "ToEven on the scaled double" from Python's correctly-rounded round():
    # 0.025 is ABOVE the tie in binary, so round(0.025, 2) is 0.03 while Fuse shows 0.02
    assert round(0.025, 2) == 0.03 and round(0.025 * 100) / 100 == 0.02


@pytest.mark.parametrize("sheet", ("Start", "Finish"))
def test_the_date_change_is_the_calendar_day_difference_truncated_toward_zero(sheet: str) -> None:
    _workbooks_present()
    compared = fractional = 0
    misses = collections.Counter()
    for wb, before_name, after_name in _PAIRS:
        tb = _golden(before_name).tasks_by_id
        ta = _golden(after_name).tasks_by_id
        for uid, cells in _grid(ACUMEN / wb, sheet, ratio=False):
            shown_before, shown_change, shown_after = cells
            if uid not in tb or uid not in ta:
                continue
            if not all(_is_number(c) for c in (shown_before, shown_change, shown_after)):
                continue
            attr = sheet.lower()
            fa, fb = getattr(tb[uid], attr), getattr(ta[uid], attr)
            if fa is None or fb is None:
                continue
            compared += 1
            # the serials are the goldens' stored dates to the second
            for stored, shown in ((fa, shown_before), (fb, shown_after)):
                serial = (stored - _EPOCH).total_seconds() / 86400
                assert abs(serial - shown) < 1e-6, (sheet, uid)
            d = Fraction(int((fb - fa).total_seconds()), 86400)
            fractional += d.denominator != 1
            misses["trunc"] += _trunc(d) != shown_change
            misses["floor"] += math.floor(d) != shown_change
            misses["half_even"] += _half_even(d) != shown_change
            misses["date_part"] += (fb.date() - fa.date()).days != shown_change
    assert compared == {"Start": 1010 + 124 + 91, "Finish": 1283 + 130 + 103}[sheet]
    assert fractional > compared // 2  # most rows are sub-day, so the candidates separate
    assert misses["trunc"] == 0, misses
    assert min(misses["floor"], misses["half_even"], misses["date_part"]) > 0, misses
