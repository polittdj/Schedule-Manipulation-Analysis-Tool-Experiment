"""Shared importer utilities (M3): a loud error type + source-faithful parsing.

Both the MSPDI (MS Project XML) and XER (Primavera P6) importers convert the units
their source files record into the model's canonical axes:

* **Durations / lags → integer working minutes** (``480`` working minutes == one
  8-hour day; see :mod:`schedule_forensics.model.units`). MSPDI encodes spans as
  ISO-8601 ``PnDTnHnMnS``; XER encodes them as a decimal hour count. Both are
  converted with :class:`decimal.Decimal` + ``ROUND_HALF_UP`` so the same input
  always yields the same minute count (no binary-float drift — Law 2, fidelity).
* **Dates → :class:`datetime.datetime`** via ISO-8601, with the pre-1985 "not set"
  sentinel both tools write mapped to ``None`` (never a fabricated date).

A parse that cannot form a valid schedule raises :class:`ImporterError` — the model
is strict and closed, so malformed input fails loudly here rather than silently
dropping metadata.

The importer boundary is also where the engine's **offset-conversion precondition** is
enforced (:func:`anchored_project_start`, ADR-0310 §5): a ``project_start`` whose
time-of-day leaves no room for a full working day inside its own calendar day is
normalised to the calendar's modelled shift start, or the file is rejected when no
schedulable anchor exists. Downstream code may then assume the invariant holds instead
of each consumer re-deriving it.
"""

from __future__ import annotations

import datetime as dt
import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.task import ConstraintType
from schedule_forensics.model.units import MINUTES_PER_CALENDAR_DAY


class ImporterError(ValueError):
    """A source file could not be parsed into a valid :class:`Schedule`.

    Subclasses :class:`ValueError`; importers wrap lower-level parse failures and
    pydantic ``ValidationError`` in this type so callers get one clean, CUI-safe
    contract (the message names *what* is wrong, never the file's contents).
    """


#: Both MS Project and P6 write "no date" as a pre-1985 sentinel (year 0/1, or a
#: 1984 placeholder). A parsed datetime before this is treated as absent.
_MIN_REAL_YEAR = 1985

#: Constraints that require a date to be meaningful (and that the CPM engine acts on); a
#: real-world export sometimes carries one of these with the date cleared (a stale
#: leftover) — meaningless and unschedulable, so importers normalize it to ASAP. Shared
#: by the MSPDI and XER importers so the tolerance classes cannot drift apart.
DATE_REQUIRING_CONSTRAINTS = frozenset(
    {
        ConstraintType.SNET,
        ConstraintType.FNET,
        ConstraintType.SNLT,
        ConstraintType.FNLT,
        ConstraintType.MSO,
        ConstraintType.MFO,
    }
)

#: ISO-8601 duration grammar (``PnDTnHnMnS``); every component optional, decimals
#: allowed. MS Project task durations are almost always ``PT<h>H<m>M<s>S`` (working
#: hours); the ``D`` term is the calendar-day (24 h) component per ISO-8601.
_ISO_DURATION_RE = re.compile(
    r"^P(?:(?P<days>\d+(?:\.\d+)?)D)?"
    r"(?:T(?:(?P<hours>\d+(?:\.\d+)?)H)?"
    r"(?:(?P<minutes>\d+(?:\.\d+)?)M)?"
    r"(?:(?P<seconds>\d+(?:\.\d+)?)S)?)?$"
)

_MINUTES_PER_HOUR = Decimal(60)
_MINUTES_PER_ISO_DAY = Decimal(24 * 60)  # ISO-8601 "D" is a calendar (24 h) day


def parse_datetime(value: str | None) -> dt.datetime | None:
    """Parse an ISO-8601 datetime; ``None`` for missing/empty/sentinel values.

    MSPDI (``2025-01-06T08:00:00``) and XER (``2025-01-06 08:00``) datetimes are
    both ISO-8601, so :func:`datetime.datetime.fromisoformat` parses either. An
    unparseable or pre-1985 value is the source's "not set" marker → ``None``
    (these optional fields legitimately carry junk/sentinels; structural problems
    are raised elsewhere, not here).
    """
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.year < _MIN_REAL_YEAR:
        return None
    # some exports tag datetimes with an offset/Z; the working-time axis is wall-clock local,
    # and mixing aware + naive datetimes breaks comparisons downstream — keep the local time.
    return parsed.replace(tzinfo=None)


def _dec(group: str | None) -> Decimal:
    """A regex group (or ``None``) → exact :class:`Decimal` (``None``/empty → 0)."""
    return Decimal(group) if group else Decimal(0)


def iso_duration_to_minutes(value: str | None) -> int:
    """Convert an ISO-8601 ``PnDTnHnMnS`` span to whole working minutes.

    ``None``/empty → ``0`` (a 0-minute, milestone-style span). The span is summed
    in :class:`~decimal.Decimal` and rounded ``ROUND_HALF_UP`` for determinism.
    MS Project encodes *working* hours in the span (``PT16H0M0S`` == 16 working
    hours == 960 minutes == 2 working days at 480/day). A non-ISO string raises
    :class:`ImporterError` (loud — never a silent 0).
    """
    if value is None:
        return 0
    text = value.strip()
    if not text:
        return 0
    match = _ISO_DURATION_RE.match(text)
    if match is None:
        raise ImporterError(f"unparseable ISO-8601 duration: {value!r}")
    total = (
        _dec(match["days"]) * _MINUTES_PER_ISO_DAY
        + _dec(match["hours"]) * _MINUTES_PER_HOUR
        + _dec(match["minutes"])
        + _dec(match["seconds"]) / _MINUTES_PER_HOUR
    )
    return int(total.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def hours_to_minutes(value: str | None) -> int:
    """Convert a decimal hour count (XER ``*_hr_cnt``) to whole working minutes.

    ``None``/empty → ``0``. The sign is preserved (a negative ``lag_hr_cnt`` is a
    lead). Rounded ``ROUND_HALF_UP`` in :class:`~decimal.Decimal`. A non-numeric
    string raises :class:`ImporterError`.
    """
    if value is None:
        return 0
    text = value.strip()
    if not text:
        return 0
    try:
        hours = Decimal(text)
    except InvalidOperation as exc:
        raise ImporterError(f"unparseable hour count: {value!r}") from exc
    if not hours.is_finite():
        return 0  # "NaN"/"Infinity" parse as Decimals but are data noise — same as empty
    return int((hours * _MINUTES_PER_HOUR).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def parse_float(value: str | None) -> float | None:
    """Parse an optional decimal number; ``None``/empty → ``None`` (never 0).

    ``"NaN"``/``"Infinity"`` are valid :class:`Decimal` constructions but poison
    every downstream sum/comparison — they are data noise and read as absent.
    """
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise ImporterError(f"unparseable number: {value!r}") from exc
    return float(number) if number.is_finite() else None


def weekday_from_source(day: int) -> int | None:
    """MSPDI/XER day-of-week (``1``=Sunday … ``7``=Saturday) → ``date.weekday()``
    (Mon=0 … Sun=6). Out-of-range values are data noise → ``None``."""
    return (day + 5) % 7 if 1 <= day <= 7 else None


def clock_minutes(value: str | None) -> int | None:
    """A wall-clock time-of-day (``HH:MM`` or ``HH:MM:SS``) → minutes since midnight.

    ``None`` for absent/garbage values (calendar fields legitimately carry noise; a bad
    working-time span must not sink the file). Seconds are dropped — working-time grids
    are minute-resolution.
    """
    if value is None:
        return None
    match = re.match(r"^(\d{1,2}):(\d{2})(?::\d{2})?$", value.strip())
    if match is None:
        return None
    hours, minutes = int(match.group(1)), int(match.group(2))
    if hours > 24 or minutes > 59:
        return None
    return hours * 60 + minutes


def working_time_span(start: str | None, finish: str | None) -> tuple[int, int] | None:
    """One working-time block as ``(from, to)`` minutes-from-midnight, ``None`` when unusable.

    A finish of ``00:00`` is the sources' end-of-day midnight (24:00) — P6 and MS Project both
    write it for any span that runs to midnight. That includes a **full 24-hour continuous day**,
    which both tools encode as ``00:00`` → ``00:00`` (a continuous-ops / "24 Hours" base calendar);
    it must read as the whole day (1440 min), not collapse to nothing — the earlier
    ``from_min > 0`` guard dropped exactly this case, so a 24h calendar fell back to the 8h/day
    default (audit H3/L8). A genuine zero-length or inverted span (``08:00`` → ``08:00``,
    ``12:00`` → ``08:00``) still returns ``None``.
    """
    from_min = clock_minutes(start)
    to_min = clock_minutes(finish)
    if from_min is None or to_min is None:
        return None
    if to_min == 0:
        to_min = 24 * 60
    if to_min <= from_min:
        return None
    return (from_min, to_min)


def working_span_minutes(start: str | None, finish: str | None) -> int:
    """Length of one working-time span (``08:00``→``12:00`` = 240), 0 when unusable."""
    span = working_time_span(start, finish)
    return 0 if span is None else span[1] - span[0]


def dominant_day_minutes(day_totals: list[int]) -> int | None:
    """The most common positive per-day working-minute total (ties → the larger).

    The engine models one contiguous working block per day, so a calendar whose days
    differ (e.g. a half-day Friday) is represented by its dominant day length —
    deterministic and documented (ADR-0028). ``None`` when no day has positive minutes.
    """
    positives = [m for m in day_totals if m > 0]
    if not positives:
        return None
    counts: dict[int, int] = {}
    for m in positives:
        counts[m] = counts.get(m, 0) + 1
    return max(counts, key=lambda m: (counts[m], m))


#: P6 stores calendar exception dates as Excel serial day numbers (days since 1899-12-30).
_EXCEL_EPOCH = dt.date(1899, 12, 30)


def excel_serial_to_date(serial: int) -> dt.date | None:
    """An Excel serial day number → :class:`datetime.date`; ``None`` outside 1985..2200
    (the same "not set"/noise window as :func:`parse_datetime`)."""
    try:
        day = _EXCEL_EPOCH + dt.timedelta(days=serial)
    except OverflowError:
        return None
    return day if _MIN_REAL_YEAR <= day.year <= 2200 else None


def clamped_percent_or_none(value: str | None) -> float | None:
    """Optional percent clamped to 0..100; absent stays ``None`` (same noise class as
    :func:`parse_percent` — an out-of-range physical % must not sink the file)."""
    parsed = parse_float(value)
    return None if parsed is None else min(100.0, max(0.0, parsed))


def parse_percent(value: str | None) -> float:
    """Parse a percent value, clamped to ``0..100``; ``None``/empty → ``0.0``.

    Real exports occasionally carry out-of-range percents (tool quirks, P6 round-trips);
    they are data noise, not corruption — clamp to the valid range rather than reject the
    whole file (the model still bounds-checks ``0 <= pct <= 100`` as the backstop).
    """
    parsed = parse_float(value)
    if parsed is None:
        return 0.0
    return min(100.0, max(0.0, parsed))


def modelled_shift_start(calendar: Calendar) -> int:
    """Minutes-from-midnight at which this calendar's working day begins.

    A calendar that declares intraday blocks carries the shift start directly (the earliest
    :attr:`Calendar.day_segments` start). A calendar with **no** segments is the legacy single
    contiguous block, which :meth:`Calendar.intraday_worked_minutes` already models as running
    from midnight — so ``0`` is *read from the existing model contract*, not invented here.
    ``Calendar`` has no dedicated shift-start field, and ADR-0310 deliberately did not add one.

    The *earliest* declared start is taken, so a wrap-around night shift (``((1320, 1440),
    (0, 360))``) resolves to midnight. That is not a reading of the shift's true start — the
    engine's single-contiguous-block model cannot represent a wrap-around at all (ADR-0028) —
    but it is the anchor that keeps the offset grid inside one calendar day, which is what this
    value is for.
    """
    return min((start for start, _ in calendar.day_segments), default=0)


def anchored_project_start(
    project_start: dt.datetime, calendar: Calendar, *, source: str
) -> tuple[dt.datetime, str | None]:
    """Enforce the offset-conversion precondition at the importer boundary (ADR-0310 §5).

    ``engine.cpm.offset_to_datetime`` lays each working day's minutes out contiguously from
    ``project_start``'s time-of-day. That model only holds while a full working day fits inside
    the calendar day it starts in — the declared supported domain is
    ``start_time_of_day + working_minutes_per_day <= MINUTES_PER_CALENDAR_DAY``. Outside it the
    intraday remainder crosses midnight and the returned instant's ``.date()`` can be a
    *non-working* day, breaking the offset ↔ datetime inverse property.

    Returns ``(project_start, note)``. Inside the domain the start is returned **unchanged** and
    ``note`` is ``None`` — every schedule in the committed corpus takes this path, so no computed
    or displayed number moves. Outside it the start is **normalised** to the calendar's modelled
    shift start on the same date and ``note`` describes the change for the operator. When even the
    shift start cannot fit a full working day the file is **rejected**: no anchor exists that the
    engine can schedule from, and loading it anyway would produce dates on non-working days with
    nothing on screen to say so.

    Sub-minute components are not part of the check: the engine's axis is integer minutes and
    :func:`engine.cpm.datetime_to_offset` reads ``hour * 60 + minute``, so this matches it exactly.
    """
    per_day = calendar.working_minutes_per_day
    start_tod = project_start.hour * 60 + project_start.minute
    if start_tod + per_day <= MINUTES_PER_CALENDAR_DAY:
        return project_start, None
    shift_start = modelled_shift_start(calendar)
    if shift_start + per_day > MINUTES_PER_CALENDAR_DAY:
        raise ImporterError(
            f"{source} cannot be scheduled: calendar {calendar.name!r} works {per_day} minutes "
            f"per day starting at {_hhmm(shift_start)}, which does not fit inside a 24-hour day. "
            "Correct the calendar's working times (or its hours per day) and re-export."
        )
    normalised = project_start.replace(
        hour=shift_start // 60, minute=shift_start % 60, second=0, microsecond=0
    )
    note = (
        f"Project start time normalised from {_hhmm(start_tod)} to {_hhmm(shift_start)} "
        f"on {project_start.date().isoformat()}: calendar {calendar.name!r} works {per_day} "
        f"minutes per day, so a working day beginning at {_hhmm(start_tod)} runs past midnight. "
        "Every activity keeps the same working day either way; what this corrects is a "
        "late-in-the-day instant spilling onto the FOLLOWING calendar date — which can be a "
        "weekend or a holiday. Times of day shown against computed dates shift accordingly."
    )
    return normalised, note


def _hhmm(minute_of_day: int) -> str:
    """``480`` → ``"08:00"``. Formatting only — never parses back."""
    return f"{minute_of_day // 60:02d}:{minute_of_day % 60:02d}"
