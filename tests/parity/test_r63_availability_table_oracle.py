"""The file's own availability table as the oracle for a resource's capacity (ADR-0506, R-63).

Four goldens carry a resource availability table — Hard_File_updated2, Hard_File_updated3 and the
two 24-hour snapshots of the same programme — converted by the vendored MPXJ on 2026-07-09, when
the JVM's clock sat inside every table's FIRST row. Their ``<MaxUnits>`` scalars are that row
(1 / 0.5 / 0.25); their status dates (09-10, 10-12, 11-12) sit in later rows (2 / 1 / 0.5). The
apprentice's cost-rate table A changes on 2026-08-31 08:00 (10 → 30) and every status date is
after it, while the 07-09 scalar reads 10. Measured 2026-09-17 by converting the updated3
golden's own git blob under three frozen clocks: the 07-09 conversion reproduces the golden to
the second, and later clocks move exactly ``CurrentDate`` and the per-resource ``MaxUnits`` /
``OverAllocated`` / ``AvailableFrom`` / ``AvailableTo`` / ``StandardRate`` / ``OvertimeRate`` —
the 09-14 conversion's nine changed pairs are replayed verbatim below — while every table is
byte-identical.

Red first (pre-ADR-0506): every scalar case below reads the 07-09 clock's row; the daily
capacities read one unit in September; the apprentice's rate reads 10; the replayed conversion
imports a different resource table and a different loading.
"""

from __future__ import annotations

import datetime as dt
import gzip
import re
from functools import cache
from pathlib import Path

import pytest

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.resources import ResourceLoading, compute_resource_loading
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.schedule import Schedule

pytestmark = pytest.mark.parity

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"
UPDATED2 = "fuse_hardfile/Hard_File_updated2.mspdi.xml.gz"
UPDATED3 = "fuse_hardfile/Hard_File_updated3.mspdi.xml.gz"
UPDATED4 = "ssi_hardfile_24h_uid155/Hard_File_updated4_24h.mspdi.xml.gz"


def _text(rel: str) -> str:
    path = GOLDEN / rel
    raw = path.read_bytes()
    return gzip.decompress(raw).decode("utf-8") if path.suffix == ".gz" else raw.decode("utf-8")


@cache
def _load(rel: str) -> Schedule:
    return parse_mspdi_text(_text(rel), source_file=rel)


def _resource_block(text: str, uid: int) -> str:
    """The ``<Resource>…</Resource>`` element of ``uid`` in the golden's own text."""
    resources = re.search(r"<Resources>(.*?)</Resources>", text, re.S)
    assert resources is not None
    for block in re.findall(r"<Resource>(.*?)</Resource>", resources.group(1), re.S):
        if re.search(rf"<UID>{uid}</UID>", block):
            return block
    raise AssertionError(f"UID {uid} not in the resources of the golden")


def _scalar(text: str, uid: int, tag: str) -> str | None:
    block = _resource_block(text, uid)
    m = re.search(rf"\n {{12}}<{tag}>([^<]*)</{tag}>", block)  # the scalar sits at 12 spaces
    return None if m is None else m.group(1)


# --- max units: the table's row at the status date, never the 07-09 clock's row -----------------

CASES = [
    # (golden, resource UID, the golden's <MaxUnits> scalar, the table's row at the status date)
    pytest.param(UPDATED2, 1, "1", 2.0, id="updated2-customer-service-team"),
    pytest.param(UPDATED2, 3, "0.5", 1.0, id="updated2-technology-lead"),
    pytest.param(UPDATED3, 1, "1", 2.0, id="updated3-customer-service-team"),
    pytest.param(UPDATED3, 2, "1", 2.0, id="updated3-customer-service-lead"),
    pytest.param(UPDATED3, 3, "0.5", 1.0, id="updated3-technology-lead"),
    pytest.param(UPDATED3, 6, "0.25", 0.5, id="updated3-logistics-three-row-table"),
    pytest.param(UPDATED4, 1, "1", 2.0, id="updated4-customer-service-team"),
    pytest.param(UPDATED4, 2, "1", 2.0, id="updated4-customer-service-lead"),
    pytest.param(UPDATED4, 3, "0.5", 1.0, id="updated4-technology-lead"),
    pytest.param(UPDATED4, 6, "0.25", 0.5, id="updated4-logistics-three-row-table"),
]


@pytest.mark.parametrize(("rel", "uid", "scalar", "expected"), CASES)
def test_max_units_is_the_tables_row_at_the_status_date(
    rel: str, uid: int, scalar: str, expected: float
) -> None:
    """The premise is asserted with the claim: the golden's scalar IS the 07-09 row (so a reading
    of the scalar cannot pass), and the resource's max units is the row at the status date."""
    assert _scalar(_text(rel), uid, "MaxUnits") == scalar
    assert _load(rel).resource_by_id(uid).max_units == expected


@pytest.mark.parametrize("rel", [UPDATED2, UPDATED3, UPDATED4])
def test_the_apprentices_rate_is_cost_rate_table_a_at_the_status_date(rel: str) -> None:
    """UID 7 'Logistics Apprentice': 10 through 2026-08-31 07:59, 30 from 08:00; every status
    date is after the change and the 07-09 scalar reads 10."""
    assert _scalar(_text(rel), 7, "StandardRate") == "10"
    assert _load(rel).resource_by_id(7).standard_rate == 30.0


# --- capacity per day: the row in force THAT day ------------------------------------------------


def _day_caps(rel: str, uid: int) -> dict[dt.date, float]:
    sch = _load(rel)
    rl = compute_resource_loading(sch, compute_cpm(sch), "day")
    res = next(r for r in rl.resources if r.resource_id == uid)
    return {dt.date.fromisoformat(p.period): p.capacity_minutes for p in res.series}


def test_customer_service_teams_daily_capacity_is_one_unit_in_july_and_two_from_august() -> None:
    """updated3 UID 1 is booked from 07-08 to 12-10 across its 08-02 row change: every loaded day
    before 08-02 carries 480 minutes of capacity (one unit of an 8-hour day), every day from
    08-02 carries 960 — both sides present, the 07-09 scalar (1) nowhere in the later half."""
    caps = _day_caps(UPDATED3, 1)
    before = {d: c for d, c in caps.items() if d < dt.date(2026, 8, 2)}
    after = {d: c for d, c in caps.items() if d >= dt.date(2026, 8, 2)}
    assert before and after
    assert set(before.values()) == {480.0}
    assert set(after.values()) == {960.0}


def test_logistics_three_row_table_puts_half_a_unit_on_its_october_days() -> None:
    """updated3 UID 6: 0.25 through 10-07, 1 for 10-08 / 10-09, 0.5 from 10-10; its bookings run
    from 10-13, so every loaded day carries 240 minutes — the third row, not the first (120)
    and not the middle (480)."""
    caps = _day_caps(UPDATED3, 6)
    assert caps and min(caps) >= dt.date(2026, 10, 13)
    assert set(caps.values()) == {240.0}


# --- the replayed later conversion --------------------------------------------------------------

#: the 09-14 conversion of the SAME save, as measured: per resource, the 12-space scalar lines the
#: clock moved (``-`` → ``+``); the tables' own rows (20 spaces) are untouched by construction
_MEASURED_0914 = {
    1: [
        ("<MaxUnits>1</MaxUnits>", "<MaxUnits>2</MaxUnits>"),
        ("<OverAllocated>1</OverAllocated>", "<OverAllocated>0</OverAllocated>"),
        (
            "<AvailableTo>2026-08-01T23:59:00</AvailableTo>",
            "<AvailableFrom>2026-08-02T00:00:00</AvailableFrom>",
        ),
    ],
    3: [
        ("<MaxUnits>0.5</MaxUnits>", "<MaxUnits>1</MaxUnits>"),
        ("<OverAllocated>1</OverAllocated>", "<OverAllocated>0</OverAllocated>"),
        (
            "<AvailableTo>2026-08-10T23:59:00</AvailableTo>",
            "<AvailableFrom>2026-08-11T00:00:00</AvailableFrom>",
        ),
    ],
    7: [
        ("<StandardRate>10</StandardRate>", "<StandardRate>30</StandardRate>"),
        ("<OvertimeRate>15</OvertimeRate>", "<OvertimeRate>45</OvertimeRate>"),
    ],
}


def _replay_0914(text: str) -> str:
    """The golden as the 09-14 clock would have written it: each measured line replaced exactly
    once inside its resource block (loud if the golden no longer carries the line)."""
    assert text.count("<CurrentDate>2026-07-09T14:56:59</CurrentDate>") == 1
    out = text.replace(
        "<CurrentDate>2026-07-09T14:56:59</CurrentDate>",
        "<CurrentDate>2026-09-14T10:00:09</CurrentDate>",
    )
    for uid, pairs in _MEASURED_0914.items():
        block = _resource_block(out, uid)
        new_block = block
        for old, new in pairs:
            old_line, new_line = f"\n{' ' * 12}{old}", f"\n{' ' * 12}{new}"
            assert new_block.count(old_line) == 1, (uid, old)
            new_block = new_block.replace(old_line, new_line)
        assert out.count(block) == 1
        out = out.replace(block, new_block)
    return out


def _loading(sch: Schedule) -> ResourceLoading:
    return compute_resource_loading(sch, compute_cpm(sch), "month")


def test_the_09_14_conversions_wall_clock_artefacts_change_nothing_the_importer_reads() -> None:
    """The row's oracle on the real file: the golden (07-09) and the same save as the 09-14 clock
    wrote it import to the same resources and the same resource loading. The replay is asserted
    to have changed the text (the premise), and the premise is not vacuous: on the pristine
    importer the two texts disagree on UID 1 and 3's max units and UID 7's rate."""
    original = _text(UPDATED3)
    replayed = _replay_0914(original)
    assert replayed != original
    golden, later = (
        parse_mspdi_text(original, source_file="a"),
        parse_mspdi_text(replayed, source_file="b"),
    )
    assert golden.resources == later.resources
    assert _loading(golden) == _loading(later)
