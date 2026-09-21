"""Acumen Fuse's DCMA-09 is **two** metrics with **two** populations and a **field** numerator
(R-79, ADR-0520).

``9. Invalid Forecast Dates`` and ``9. Invalid Actual Dates`` are separate NASA-library metrics,
and the Bible declares their populations explicitly — in BOTH committed ``.aft`` snapshots, in
every ``Metric`` record, under ``PrimaryFilter``:

======================================  =============  ================  ===============
metric                                  IncludePlanned  IncludeInProgress  IncludeComplete
======================================  =============  ================  ===============
``9. Invalid Forecast Dates``           true           true              **false**
``9. Invalid Actual Dates``             **false**      true              true
======================================  =============  ================  ===============

— and says the same in prose ("Includes normal activities and milestones that are *planned or
in-progress*" / "*in-progress or complete*"). Both also carry ``IncludeNormal=true``,
``IncludeMilestone=true``, ``IncludeSummary=false``, i.e. the universal DCMA filter ADR-0280 /
ADR-0367 already scopes to, whose duration predicate is the Baseline Duration FIELD (ADR-0518).

The numerator is a count of **FIELDS**, and that is not an inference — the Bible's own Formula
SUMs two terms per activity, so an activity whose stored start *and* stored finish both precede
the data date with no actuals contributes **2**::

    SUM((((EarlyStart<ProjectTimeNow) * (ActualStart="")) +
         ((EarlyFinish<ProjectTimeNow) * (ActualFinish=""))) * 1)
    SUM(((ActualStart>ProjectTimeNow) + (ActualFinish>ProjectTimeNow)) * 1)

Large Test File2 displays **322** where the activities carrying at least one bad field are
**170** (ADR-0283's documented divergence, now resolved: Fuse is right, it is counting fields).

Measured: every count and every ratio Fuse displays for both tiles reproduces from the engine —
the forecast tile over the baselined-INCOMPLETE population, the actual tile over the baselined
STARTED-OR-COMPLETE population. The three denominators that discriminate, all on saves the repo
holds and has matched by measurement: Large Test File2 322 / **904** (the engine's every-baselined
1,568 prints 0.21 and every-incomplete 998 prints 0.32), Hard_File_updated2 30 / **58** (84 → 0.36)
and the 24-hour Hard_File 1 / **12** (82 → 0.01). ``Hard_File`` has NO started-or-complete
activity at all, and Fuse prints **N/A** for its Invalid Actual Dates tile — the empty population
carrying "no figure" exactly as ADR-0519 established.

**Two ribbons are excluded BY NAME, and by measurement, not by assertion.** "Large Test File vs
Large Test File2 - Acumen Fuse Analysis Quick Add Metrics" and "… - Acumen Fuse Quick Add
Metrics " read Large Test File2's forecast tile **0** where three other workbooks read 322. They
are not a second metric and not a second save. Measured over all 16 numbered tiles of both
projects: the restricted pair is **never higher**, is strictly LOWER on 8 (Large Test File)
and 11 (File2) of them (High Float 66 vs 814, Resources 66 vs 866, Missed Activities 4 vs
1,115), and is equal only where the whole-schedule value is 0 — except one equal NON-zero
tile, the project-level scalar ``13. CPLI`` (0.97 / 0.59), which an activity-population
filter cannot move. That is the signature of the same save under a restricted filter.
A filtered ribbon is not a whole-schedule oracle; this test asserts
that signature so the exclusion can never become a bare claim.

**UNVERIFIED, and pinned as such:** the corpus does not determine the completion-state boundary.
Three forecast-side rules (``is_incomplete`` / no actual finish / percent < 100) and six
actual-side rules all reproduce 16 of 16 Fuse tiles, and they disagree on **0** of the 8,190
activities in all 24 committed fixtures. The engine uses the repo's DCMA convention
(``is_incomplete``); what would settle it is a Fuse-scored save carrying a complete activity with
no actual start, or a started activity at 0 %.
"""

from __future__ import annotations

import gzip
import re
import zipfile
from decimal import ROUND_HALF_UP, Decimal
from functools import cache
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from schedule_forensics.engine.metrics import compute_dcma14
from schedule_forensics.engine.metrics._common import (
    activity_calendar_day_minutes,
    acumen_duration_field,
    is_incomplete,
    non_summary,
)
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.schedule import Schedule

REPO = Path(__file__).resolve().parents[2]
INTAKE = REPO / "00_REFERENCE_INTAKE"
ACUMEN = INTAKE / "acumen_v8.11.0"
FIXTURES = REPO / "tests" / "fixtures"

pytestmark = [
    pytest.mark.parity,
    pytest.mark.skipif(
        not INTAKE.exists(), reason="00_REFERENCE_INTAKE/ not present in this layout"
    ),
]

_M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

_FORECAST = "9. Invalid Forecast Dates"
_ACTUAL = "9. Invalid Actual Dates"

_ALL = INTAKE / "AlltheProjects Analysis Report - Quick Add Metrics.xlsx"
_ANALYST_LTF = ACUMEN / "Large Test File vs Large Test File2 - Analyst Quick Add Metrics.xlsx"
_EXCEL_LTF = ACUMEN / "Large Test File vs Large Test File2 - MS Excel Quick Add Metrics .xlsx"
_UPD12 = ACUMEN / "Hard_File_update vs update2_Fuse - Analysis Report.xlsx"
_UPD23 = ACUMEN / "Hard_File_update2 vs update3_Fuse - Analysis Report.xlsx"
_HFUSE = ACUMEN / "Hard_File_Fuse - Fuse Analysis Report.xlsx"

_REV5 = "golden/ssi_hardfile_24h_uid155/Hard_File_updated3.mspdi.xml.gz"
_G24 = "golden/ssi_hardfile_24h_uid155/Hard_File_updated4_24h.mspdi.xml.gz"
_LTF = "golden/fuse_ltf/Large_Test_File.mspdi.xml.gz"
_LTF2 = "golden/fuse_ltf/Large_Test_File2.mspdi.xml.gz"
_H24 = "Hard_File_updated4 24 hour calendar"

#: (workbook, Fuse project label) → committed fixture. Only saves this repo HOLDS and that prior
#: units matched by MEASUREMENT (ADR-0516/0518/0519's `_WORKBOOKS`); the AlltheProjects labels
#: that unit measured to be LATER saves than the fixtures are corroboration for the RULE, never
#: engine oracles, and are listed in ``_RULE_ONLY`` below.
_SCORED: dict[tuple[Path, str], str] = {
    (_HFUSE, "Hard_File"): "golden/fuse_hardfile/Hard_File.mspdi.xml.gz",
    (_HFUSE, "Hard_File_updated"): "golden/fuse_hardfile/Hard_File_updated.mspdi.xml.gz",
    (_UPD12, "Hard_File_updated"): "golden/fuse_hardfile/Hard_File_updated.mspdi.xml.gz",
    (_UPD12, "Hard_File_updated2"): "golden/fuse_hardfile/Hard_File_updated2.mspdi.xml.gz",
    (_UPD23, "Hard_File_updated2"): "golden/fuse_hardfile/Hard_File_updated2.mspdi.xml.gz",
    (_UPD23, "Hard_File_updated3"): "golden/fuse_hardfile/Hard_File_updated3.mspdi.xml.gz",
    (_ALL, "EVM1"): "golden/evm/EVM1.mspdi.xml",
    (_ALL, "Hard_File"): "golden/fuse_hardfile/Hard_File.mspdi.xml.gz",
    (_ALL, "Hard_File_updated"): "golden/fuse_hardfile/Hard_File_updated.mspdi.xml.gz",
    (_ALL, "Hard_File_updated3"): _REV5,
    (_ALL, "Hard_File_updated3 2"): _REV5,
    (_ALL, _H24): _G24,
    (_ALL, f"{_H24} 2"): _G24,
    (_ALL, "Large Test File"): _LTF,
    (_ALL, "Large Test File 2"): _LTF,
    (_ALL, "Large Test File2"): _LTF2,
    (_ALL, "Large Test File2 2"): _LTF2,
    (_ALL, "Project2"): "golden/project2_5/Project2.mspdi.xml",
    (_ALL, "Project2 2"): "golden/project2_5/Project2.mspdi.xml",
    (_ALL, "Project2 3"): "golden/project2_5/Project2.mspdi.xml",
    (_ALL, "Project5_TAMPERED"): "golden/project2_5/Project5.mspdi.xml",
    (_ALL, "Project5_TAMPERED 2"): "golden/project2_5/Project5.mspdi.xml",
    (_ANALYST_LTF, "Large Test File"): _LTF,
    (_ANALYST_LTF, "Large Test File2"): _LTF2,
    (_EXCEL_LTF, "Large Test File"): _LTF,
    (_EXCEL_LTF, "Large Test File2"): _LTF2,
}

#: Fuse scored a LATER save than the repo holds (measured by ADR-0518/0519 on the float and
#: duration fields), so these corroborate the RULE from Fuse's own displayed cells and are never
#: asserted against the engine.
_RULE_ONLY = frozenset(
    {"EVM2", "Hard_File_updated2", *(f"TP4_DataCenter_v{n}" for n in range(1, 6))}
)

#: Excluded BY MEASUREMENT — a restricted-filter ribbon, not a whole-schedule oracle.
_RESTRICTED = (
    ACUMEN / "Large Test File vs Large Test File2 - Acumen Fuse Analysis Quick Add Metrics.xlsx",
    ACUMEN / "Large Test File vs Large Test File2 - Acumen Fuse Quick Add Metrics .xlsx",
)

Cell = str | int | float | bool | None


def _col_index(ref: str) -> int:
    """``"P14"`` → 15 (Fuse's writer omits ``r`` on consecutive cells; ADR-0516 M10)."""
    n = 0
    for ch in ref:
        if not ch.isalpha():
            break
        n = n * 26 + (ord(ch.upper()) - 64)
    return n - 1


@cache
def _sheets(path: Path) -> tuple[tuple[str, tuple[tuple[Cell, ...], ...]], ...]:
    """Every sheet of an xlsx as rows of typed cells, column-addressed (std-lib only)."""
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        shared: list[str] = []
        if "xl/sharedStrings.xml" in names:
            for si in ET.fromstring(zf.read("xl/sharedStrings.xml")).findall(f"{_M}si"):
                shared.append("".join(t.text or "" for t in si.iter(f"{_M}t")))
        wb = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        targets = {r.get("Id"): r.get("Target") or "" for r in rels}
        out: list[tuple[str, tuple[tuple[Cell, ...], ...]]] = []
        sheets_el = wb.find(f"{_M}sheets")
        assert sheets_el is not None
        for s in sheets_el:
            target = targets[s.get(f"{_R}id") or ""]
            target = target if target.startswith("xl/") else "xl/" + target.lstrip("/")
            rows: list[tuple[Cell, ...]] = []
            for row in ET.fromstring(zf.read(target)).iter(f"{_M}row"):
                cells: list[Cell] = []
                for c in row.findall(f"{_M}c"):
                    ref = c.get("r")
                    if ref is not None:
                        while len(cells) < _col_index(ref):
                            cells.append(None)
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
                rows.append(tuple(cells))
            out.append((s.get("name") or "", tuple(rows)))
        return tuple(out)


@cache
def _ribbon(path: Path) -> tuple[dict[str, dict[str, Cell]], dict[str, dict[str, Cell]]]:
    """The 'Ribbon Analysis' sheet's two blocks (counts, then ratios): snapshot → {tile: value}.
    The header row is found by the DCMA-09 tile itself, so no per-workbook anchor is needed."""
    rows = dict(_sheets(path))["Ribbon Analysis"]
    header: tuple[Cell, ...] | None = None
    blocks: list[dict[str, dict[str, Cell]]] = [{}, {}]
    block = 0
    for r in rows:
        if _FORECAST in r:
            header = r
            continue
        if header is not None and r and r[0] == "Ribbons" and isinstance(r[1], str):
            if r[1] in blocks[0] and block == 0:
                block = 1
            blocks[block][r[1]] = {
                str(h): v for h, v in zip(header, r, strict=False) if isinstance(h, str)
            }
    return blocks[0], blocks[1]


@cache
def _fixture(rel: str) -> Schedule:
    path = FIXTURES / rel
    raw = path.read_bytes()
    if path.suffix == ".gz":
        raw = gzip.decompress(raw)
    return parse_mspdi_text(raw.decode("utf-8"), source_file=path.name)


def _shown(x: float) -> float:
    """Fuse's ribbon ratio cell: two decimals, half AWAY from zero (ADR-0519)."""
    return float(Decimal(repr(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _books_present() -> None:
    missing = [p.name for p in {k[0] for k in _SCORED} | set(_RESTRICTED) if not p.exists()]
    assert not missing, f"Fuse workbook(s) missing from the intake (Law 2 oracle): {missing}"


def _cells(book: Path, label: str, tile: str) -> tuple[Cell, Cell]:
    counts, ratios = _ribbon(book)
    return counts[label][tile], ratios[label][tile]


def _is_na(v: Cell) -> bool:
    return isinstance(v, str) and "N/A" in v


# ── the two tiles ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(("book", "label"), sorted(_SCORED, key=lambda k: (k[0].name, k[1])))
def test_fuses_two_dcma09_tiles_reproduce_from_the_engine(book: Path, label: str) -> None:
    """Every count AND every ratio Fuse displays, from the engine, on the save it scored."""
    _books_present()
    dcma = compute_dcma14(_fixture(_SCORED[(book, label)]), acumen_parity=True)
    for tile, key in ((_FORECAST, "DCMA09"), (_ACTUAL, "DCMA09_ACTUAL")):
        count, ratio = _cells(book, label, tile)
        r = dcma[key]
        where = f"{book.name} · {label} · {tile}"
        if _is_na(count) or _is_na(ratio):
            assert r.population == 0, f"{where}: Fuse prints N/A; engine pop {r.population}"
            continue
        assert r.count == count, f"{where}: engine {r.count} != Fuse {count}"
        assert r.population > 0, f"{where}: Fuse prints {ratio}; engine population is empty"
        assert _shown(r.count / r.population) == ratio, (
            f"{where}: engine {r.count}/{r.population} = "
            f"{_shown(r.count / r.population)} != Fuse {ratio}"
        )


def test_the_refuted_denominators_are_named_so_they_cannot_return() -> None:
    """The three populations that do NOT reproduce, each measured on a save the repo holds."""
    _books_present()
    for rel, forecast, refuted in (
        (_LTF2, 322, {"every baselined": 1568, "every incomplete": 998, "every activity": 1722}),
        (
            "golden/fuse_hardfile/Hard_File_updated2.mspdi.xml.gz",
            30,
            {"every baselined": 84, "every incomplete": 76, "every activity": 110},
        ),
        (_G24, 1, {"every baselined": 82, "every incomplete": 19, "every activity": 110}),
    ):
        sch = _fixture(rel)
        tasks = non_summary(sch)
        by_uid = {c.uid: c for c in sch.calendars}
        baselined = [
            t
            for t in tasks
            if acumen_duration_field(
                t.baseline_duration_minutes or 0, activity_calendar_day_minutes(sch, t, by_uid)
            )
            > 0
        ]
        measured = {
            "every baselined": len(baselined),
            "every incomplete": len([t for t in tasks if is_incomplete(t)]),
            "every activity": len(tasks),
        }
        assert measured == refuted, f"{rel}: population census moved: {measured}"
        want = _shown(forecast / len([t for t in baselined if is_incomplete(t)]))
        for name, n in refuted.items():
            assert _shown(forecast / n) != want, (
                f"{rel}: '{name}' ({n}) now reproduces {want} — the discriminator is gone"
            )


def test_the_numerator_counts_fields_not_activities() -> None:
    """Large Test File2's 322 is FIELDS; the activities carrying a bad field are 170."""
    _books_present()
    dcma = compute_dcma14(_fixture(_LTF2), acumen_parity=True)
    assert dcma["DCMA09"].count == 322
    assert len(dcma["DCMA09"].offender_uids) == 170, "the activity count must stay visible"


def test_the_two_restricted_ribbons_are_excluded_by_measurement_not_by_assertion() -> None:
    """They read 0 because they are the same save under a RESTRICTED filter: every count tile
    disagrees with the three whole-schedule ribbons while the project-level CPLI is identical."""
    _books_present()
    numbered = re.compile(r"^\d+[a-z]?\. ")
    good, _ = _ribbon(_ANALYST_LTF)
    for book in _RESTRICTED:
        counts, _ = _ribbon(book)
        for project, fewer in (("Large Test File", 8), ("Large Test File2", 11)):
            tiles = [t for t in good[project] if numbered.match(t)]
            assert len(tiles) == 16, f"{project}: {len(tiles)} numbered tiles, not 16"
            lower = 0
            for t in tiles:
                a, b = counts[project][t], good[project][t]
                if not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
                    continue  # "12. Critical Path Test" prints a glyph, not a number
                assert a <= b, (
                    f"{book.name} · {project} · {t}: the restricted ribbon reads HIGHER "
                    f"({a} > {b}) — it is not a subset, so re-diagnose the exclusion"
                )
                lower += a < b
            assert lower == fewer, f"{book.name} · {project}: {lower} tiles lower, expected {fewer}"
            # the one EQUAL non-zero tile is the project-level scalar, which a population
            # filter cannot move — that is what makes this the same save, not a second one
            assert counts[project]["13. CPLI"] == good[project]["13. CPLI"] != 0, (
                f"{book.name}: CPLI differs — this would be a different SAVE, not a filter"
            )
        assert counts["Large Test File2"][_FORECAST] == 0


def test_the_completion_state_rule_is_undetermined_by_this_corpus() -> None:
    """UNVERIFIED and pinned: the alternative completion-state rules are extensionally IDENTICAL
    on every committed fixture, so the corpus cannot choose between them (QC-1)."""
    paths = sorted(
        [*FIXTURES.glob("golden/**/*.mspdi.xml"), *FIXTURES.glob("golden/**/*.mspdi.xml.gz")]
    )
    seen = disagree = 0
    for p in paths:
        raw = p.read_bytes()
        raw = gzip.decompress(raw) if p.suffix == ".gz" else raw
        for t in non_summary(parse_mspdi_text(raw.decode("utf-8"), source_file=p.name)):
            seen += 1
            if len({is_incomplete(t), t.actual_finish is None, t.percent_complete < 100}) > 1:
                disagree += 1
            if len({t.actual_start is not None, t.percent_complete > 0}) > 1:
                disagree += 1
    assert seen > 5000, f"the census population collapsed to {seen}"
    assert disagree == 0, (
        f"{disagree} activities now DISCRIMINATE the completion-state rules — the choice is no "
        "longer arbitrary and ADR-0520's UNVERIFIED note must be re-measured"
    )
