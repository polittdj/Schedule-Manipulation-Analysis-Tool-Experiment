"""The tod + per_day == 1440 boundary is BLESSED, not repaired (ADR-0357).

ADR-0348 documented the residual and refused to guess; the operator's 24-hour reference
`.mpp` (2026-08-06) settled it: MS Project stores the RAW instant — finishes at T01:00:00 /
T02:00:00, successor handoffs instant-contiguous — and its MSPDI format has no way to write
"Fri 24:00" (zero midnight-spelled stored dates in the whole file; a day-boundary instant is
representable ONLY as next-day 00:00). So rendering a whole-day finish on a midnight-anchored
24-hour calendar as the NEXT day's 00:00 is MS Project's own convention; the intuitive
"Fri 23:59" repair would have CREATED a parity break. These pins freeze the blessed
convention so a future "fix" toward intuition fails loudly with the citation in hand.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.cpm import (
    datetime_to_offset,
    offset_to_datetime,
    offset_to_start_datetime,
)
from schedule_forensics.model.calendar import Calendar

#: A midnight-anchored 24-hour Mon-Fri calendar — exactly what ADR-0312's import
#: normalisation produces from a continuous-operations file with a non-midnight source start.
MON = dt.datetime(2025, 1, 6, 0, 0)  # a Monday
CAL24 = Calendar(name="24h", working_minutes_per_day=1440)


def test_whole_day_finishes_render_at_the_next_midnight_msp_convention() -> None:
    # end of Monday: the instant is representable only as Tuesday 00:00 (the oracle rule)
    assert offset_to_datetime(MON, 1440, CAL24) == dt.datetime(2025, 1, 7, 0, 0)
    # end of Friday, across the weekend: Saturday 00:00 — the raw instant, exactly as MS
    # Project would store it (its format cannot say "Fri 24:00")
    assert offset_to_datetime(MON, 5 * 1440, CAL24) == dt.datetime(2025, 1, 11, 0, 0)


def test_start_role_still_rolls_to_the_next_working_day_adr_0348() -> None:
    # the SAME boundary instant in a START role names the next working day's beginning —
    # Monday 00:00, not Saturday (the ADR-0348 split is unaffected by the blessing)
    assert offset_to_start_datetime(MON, 5 * 1440, CAL24) == dt.datetime(2025, 1, 13, 0, 0)


def test_the_inverse_property_holds_at_the_boundary() -> None:
    for minutes in (1440, 2880, 5 * 1440):
        assert datetime_to_offset(MON, offset_to_datetime(MON, minutes, CAL24), CAL24) == minutes
