"""A resource's capacity is the file's OWN availability table, resolved at the schedule's status
date — never the converter's wall clock (ADR-0506, R-63).

MS Project's ``MaxUnits`` is "the current row of the Resource Availability grid" — the row whose
Available From / Available To range contains the CURRENT date (Microsoft's own field reference for
``Resource.MaxUnits``). The vendored MPXJ 16.2.0 writer resolves that row at CONVERSION time
(``Resource.getMaxUnits`` → ``getCurrentAvailabilityTableEntry`` → ``LocalDateTime.now()``, read
off the bytecode), and so does ``AvailableFrom`` / ``AvailableTo``, ``OverAllocated`` (peak units
against that MaxUnits), ``StandardRate`` / ``OvertimeRate`` (cost-rate table A's current entry)
and ``CurrentDate``. Measured 2026-09-17 by converting ONE save — the Hard_File_updated3 golden's
own git blob — under three frozen clocks: 07-09 reproduces the committed golden to the second;
09-14 and 11-01 change exactly those elements (18 and 26 diff lines) while ``<Tasks>``,
``<Assignments>``, ``<Calendars>`` and every ``<AvailabilityPeriods>`` / ``<Rates>`` table are
byte-identical. The tables are the save's; the scalars are the clock's. So the importer reads
the tables at the schedule's own "now" (the status date, else the project start) and the loading
engine earns each working day's capacity from the row in force that day.

The two "conversions" below are one save carrying the two clocks' scalars — the measured shape
of that diff (the scalar elements only), not an invention.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.resources import compute_resource_loading
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model import Schedule
from schedule_forensics.model.resource import AvailabilityPeriod

#: the save's own table: one unit through March, two from 1 April (MS Project's NA start is
#: written as 1984-01-01, its NA end as 2049-12-31 23:59) — written LATER row first on purpose
_TABLE = (
    "<AvailabilityPeriods>"
    "<AvailabilityPeriod><AvailableFrom>2026-04-01T00:00:00</AvailableFrom>"
    "<AvailableTo>2049-12-31T23:59:00</AvailableTo><AvailableUnits>2</AvailableUnits>"
    "</AvailabilityPeriod>"
    "<AvailabilityPeriod><AvailableFrom>1984-01-01T00:00:00</AvailableFrom>"
    "<AvailableTo>2026-03-31T23:59:00</AvailableTo><AvailableUnits>1</AvailableUnits>"
    "</AvailabilityPeriod>"
    "</AvailabilityPeriods>"
)
#: the scalars a conversion made in MARCH carries (the clock inside the first row) …
_MARCH_SCALARS = (
    "<MaxUnits>1</MaxUnits><OverAllocated>1</OverAllocated>"
    "<AvailableTo>2026-03-31T23:59:00</AvailableTo>"
)
#: … and the same save's scalars from a conversion made in MAY (the clock inside the second)
_MAY_SCALARS = (
    "<MaxUnits>2</MaxUnits><OverAllocated>0</OverAllocated>"
    "<AvailableFrom>2026-04-01T00:00:00</AvailableFrom>"
)
#: cost-rate table A: 10 through 31 March, 30 from 1 April 08:00 (the save's own rate change)
_RATES_A = (
    "<Rates>"
    "<Rate><RatesFrom>1984-01-01T00:00:00</RatesFrom><RatesTo>2026-03-31T07:59:00</RatesTo>"
    "<RateTable>0</RateTable><StandardRate>10</StandardRate><StandardRateFormat>2"
    "</StandardRateFormat><OvertimeRate>15</OvertimeRate></Rate>"
    "<Rate><RatesFrom>2026-04-01T08:00:00</RatesFrom><RatesTo>2049-12-31T23:59:00</RatesTo>"
    "<RateTable>0</RateTable><StandardRate>30</StandardRate><StandardRateFormat>2"
    "</StandardRateFormat><OvertimeRate>45</OvertimeRate></Rate>"
    "</Rates>"
)
STATUS = "2026-04-15T17:00:00"


def _mspdi(
    *,
    status: str | None = STATUS,
    current: str = "2026-03-15T09:00:00",
    scalars: str = _MARCH_SCALARS,
    table: str = _TABLE,
    rates: str = "",
    rate_scalar: str = "<StandardRate>10</StandardRate>",
) -> str:
    """One save: a 40-working-day task from Monday 2 March 2026 (22 March days, 18 April days)
    booked to one crew at 100 %, so the load straddles the crew's 1 April availability change."""
    return (
        '<Project xmlns="http://schemas.microsoft.com/project">'
        "<StartDate>2026-03-02T08:00:00</StartDate>"
        + (f"<StatusDate>{status}</StatusDate>" if status else "")
        + f"<CurrentDate>{current}</CurrentDate>"
        "<Resources><Resource><UID>1</UID><Name>Crew</Name><Type>1</Type>"
        + scalars
        + rate_scalar
        + table
        + rates
        + "</Resource></Resources>"
        "<Tasks><Task><UID>1</UID><Name>Build</Name><Duration>PT320H0M0S</Duration>"
        "</Task></Tasks>"
        "<Assignments><Assignment><UID>1</UID><TaskUID>1</TaskUID><ResourceUID>1</ResourceUID>"
        "<Units>1</Units><Work>PT320H0M0S</Work></Assignment></Assignments>"
        "</Project>"
    )


def _crew(text: str) -> Schedule:
    sch = parse_mspdi_text(text, source_file="save.xml")
    assert [r.unique_id for r in sch.resources] == [1]
    return sch


# --- the importer ------------------------------------------------------------------------------


def test_max_units_is_the_tables_units_at_the_status_date_not_the_converters_scalar() -> None:
    """The March conversion's ``<MaxUnits>`` says 1 (the clock's row). The status date is 15
    April, inside the second row: the resource's max units is 2, the save's own statement."""
    crew = _crew(_mspdi()).resources[0]
    assert crew.max_units == 2.0


def test_without_a_status_date_the_project_start_governs_the_table() -> None:
    """No status date → the project start (2 March) is the schedule's "now": row one, 1 unit —
    even though this conversion's scalar says 2 (a May clock)."""
    crew = _crew(_mspdi(status=None, scalars=_MAY_SCALARS, current="2026-05-20T09:00:00"))
    assert crew.resources[0].max_units == 1.0


def test_two_conversions_of_one_save_import_to_one_resource_and_one_loading() -> None:
    """The row's oracle: two operators converting one save a month apart get the SAME loading
    figures. The two texts differ only in the wall-clock artefacts the converter writes
    (``CurrentDate``, ``MaxUnits``, ``OverAllocated``, ``AvailableFrom`` / ``AvailableTo``)."""
    march = _crew(_mspdi())
    may = _crew(_mspdi(scalars=_MAY_SCALARS, current="2026-05-20T09:00:00"))
    assert march.resources[0] == may.resources[0]
    assert compute_resource_loading(march, compute_cpm(march)) == compute_resource_loading(
        may, compute_cpm(may)
    )


def test_the_table_rides_the_model_in_time_order_with_ms_projects_na_start_open() -> None:
    """The rows are written later-first in the XML; the model carries them in time order, and the
    1984-01-01 "NA" start reads as an open bound (the importers' shared pre-1985 sentinel)."""
    crew = _crew(_mspdi()).resources[0]
    assert crew.availability == (
        AvailabilityPeriod(
            available_from=None, available_to=dt.datetime(2026, 3, 31, 23, 59), units=1.0
        ),
        AvailabilityPeriod(
            available_from=dt.datetime(2026, 4, 1),
            available_to=dt.datetime(2049, 12, 31, 23, 59),
            units=2.0,
        ),
    )


def test_a_resource_without_a_table_keeps_the_files_scalar_max_units() -> None:
    """CONTROL (green on the pristine tree by construction): a resource the file writes no table
    for — the ordinary single-availability case, every golden but four — reads ``<MaxUnits>``
    exactly as before, and carries an empty table."""
    crew = _crew(_mspdi(table="", scalars="<MaxUnits>1.5</MaxUnits>")).resources[0]
    assert crew.max_units == 1.5
    assert crew.availability == ()


def test_a_table_row_without_units_states_nothing() -> None:
    """A row that names dates but no ``AvailableUnits`` is dropped, never read as zero capacity —
    the table keeps its one real row and that row governs."""
    table = (
        "<AvailabilityPeriods>"
        "<AvailabilityPeriod><AvailableFrom>2026-04-01T00:00:00</AvailableFrom>"
        "<AvailableTo>2049-12-31T23:59:00</AvailableTo></AvailabilityPeriod>"
        "<AvailabilityPeriod><AvailableFrom>1984-01-01T00:00:00</AvailableFrom>"
        "<AvailableTo>2026-03-31T23:59:00</AvailableTo><AvailableUnits>0.75</AvailableUnits>"
        "</AvailabilityPeriod>"
        "</AvailabilityPeriods>"
    )
    crew = _crew(_mspdi(table=table)).resources[0]
    assert [row.units for row in crew.availability] == [0.75]
    assert crew.max_units == 0.75  # 15 April is outside the one row; the latest begun row governs


def test_the_standard_rate_is_cost_rate_table_a_in_force_at_the_status_date() -> None:
    """The scalar ``<StandardRate>`` (10) is the March clock's entry; table A says 30 from
    1 April 08:00, and the status date is 15 April."""
    crew = _crew(_mspdi(rates=_RATES_A)).resources[0]
    assert crew.standard_rate == 30.0


def test_rate_table_b_rows_never_feed_the_standard_rate() -> None:
    """A resource whose only dated rows belong to table B (``RateTable`` 1) has no table-A row:
    the scalar governs, and table B's 99 is never read as the resource's rate."""
    rates_b = _RATES_A.replace("<RateTable>0</RateTable>", "<RateTable>1</RateTable>").replace(
        "<StandardRate>30</StandardRate>", "<StandardRate>99</StandardRate>"
    )
    crew = _crew(_mspdi(rates=rates_b)).resources[0]
    assert crew.standard_rate == 10.0


# --- the loading engine on the importer's output -----------------------------------------------


def test_capacity_per_bucket_is_the_tables_units_for_that_buckets_days() -> None:
    """Month buckets: March's 22 working days at one unit, April's 18 at two — read straight off
    the file's table, whichever clock converted it. A conversion made in May would have put two
    units in March as well (its scalar was 2); one made in March would have put one in April."""
    sch = _crew(_mspdi())
    rl = compute_resource_loading(sch, compute_cpm(sch), "month")
    caps = {p.period: p.capacity_minutes for p in rl.resources[0].series}
    assert caps == {"2026-03": 22 * 480 * 1.0, "2026-04": 18 * 480 * 2.0}
    assert rl.resources[0].max_units == 2.0  # the roster figure: the row at the status date
    assert rl.resources[0].max_units_declared is True
